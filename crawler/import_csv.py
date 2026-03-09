"""
import_csv.py
재정경제부 CSV → 카카오 지오코딩 → DB 적재

실행:
  python import_csv.py                  # 전체 (시간 소요)
  python import_csv.py --limit 100      # 앞 100건만 테스트
  python import_csv.py --skip-geocode   # 좌표 변환 없이 (이미 geocoded.json 있을 때)
"""
import argparse, csv, json, logging, os, sys, time
from pathlib import Path
import requests, pymysql
from dotenv import load_dotenv

_DIR = Path(__file__).resolve().parent
load_dotenv(_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
log = logging.getLogger(__name__)

CSV_PATH     = _DIR.parent / "재정경제부_온라인복권 판매점 주소_20250607.csv"
GEOCODED_OUT = _DIR.parent / "data" / "geocoded_stores.json"
FAIL_LOG     = _DIR.parent / "logs" / "failed_geocode.log"

KAKAO_KEY    = os.getenv("KAKAO_API_KEY")
DB_CFG = dict(host=os.getenv("DB_HOST","localhost"), port=int(os.getenv("DB_PORT",3306)),
              user=os.getenv("DB_USER","root"), password=os.getenv("DB_PASS","12341234"),
              database=os.getenv("DB_NAME","lottospot"), charset="utf8mb4")


def geocode(address: str) -> tuple[float, float] | None:
    """카카오 로컬 API로 주소 → (lat, lng) 변환."""
    try:
        r = requests.get(
            "https://dapi.kakao.com/v2/local/search/address.json",
            headers={"Authorization": f"KakaoAK {KAKAO_KEY}"},
            params={"query": address},
            timeout=5,
        )
        docs = r.json().get("documents", [])
        if docs:
            return float(docs[0]["y"]), float(docs[0]["x"])
        # 주소 검색 실패 시 키워드 검색 폴백
        r2 = requests.get(
            "https://dapi.kakao.com/v2/local/search/keyword.json",
            headers={"Authorization": f"KakaoAK {KAKAO_KEY}"},
            params={"query": address},
            timeout=5,
        )
        docs2 = r2.json().get("documents", [])
        if docs2:
            return float(docs2[0]["y"]), float(docs2[0]["x"])
    except Exception as e:
        log.warning("geocode error %s: %s", address, e)
    return None


def load_csv(limit: int | None) -> list[dict]:
    rows = []
    with open(CSV_PATH, encoding="euc-kr") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if limit and i >= limit:
                break
            rows.append({
                "name":    row.get("상호", "").strip(),
                "address": row.get("도로명주소", "").strip() or row.get("지번주소", "").strip(),
            })
    return rows


def run_geocoding(rows: list[dict]) -> list[dict]:
    GEOCODED_OUT.parent.mkdir(parents=True, exist_ok=True)
    FAIL_LOG.parent.mkdir(parents=True, exist_ok=True)

    results, failed = [], []
    total = len(rows)
    for i, row in enumerate(rows, 1):
        coord = geocode(row["address"])
        if coord:
            results.append({**row, "lat": coord[0], "lng": coord[1]})
        else:
            failed.append(row["address"])
            log.warning("[%d/%d] 실패: %s", i, total, row["address"])

        if i % 50 == 0:
            log.info("[%d/%d] 진행 중... 성공=%d 실패=%d", i, total, len(results), len(failed))
            GEOCODED_OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2))

        time.sleep(0.12)  # 카카오 API 속도 제한 대응

    GEOCODED_OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    if failed:
        with open(FAIL_LOG, "w", encoding="utf-8") as f:
            f.write("\n".join(failed))
    log.info("지오코딩 완료: 성공=%d / 실패=%d", len(results), len(failed))
    return results


def insert_db(stores: list[dict]):
    conn = pymysql.connect(**DB_CFG)
    cur = conn.cursor()

    # 기존 데이터 초기화
    cur.execute("SET FOREIGN_KEY_CHECKS=0")
    cur.execute("TRUNCATE TABLE winning_history")
    cur.execute("TRUNCATE TABLE lotto_store")
    cur.execute("SET FOREIGN_KEY_CHECKS=1")
    conn.commit()

    sql = """
        INSERT INTO lotto_store
            (name, address, lat, lng, location, is_open, created_at, updated_at)
        VALUES (%s, %s, %s, %s, ST_GeomFromText(%s, 4326), 1, NOW(), NOW())
    """
    batch = [
        (s["name"], s["address"], s["lat"], s["lng"], f"POINT({s['lat']} {s['lng']})")
        for s in stores
    ]
    cur.executemany(sql, batch)
    conn.commit()
    log.info("DB 적재 완료: %d건", len(batch))
    cur.close()
    conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="처리할 최대 건수")
    parser.add_argument("--skip-geocode", action="store_true", help="이미 geocoded.json 있으면 재사용")
    args = parser.parse_args()

    rows = load_csv(args.limit)
    log.info("CSV 로드: %d건", len(rows))

    if args.skip_geocode and GEOCODED_OUT.exists():
        log.info("기존 geocoded.json 재사용")
        stores = json.loads(GEOCODED_OUT.read_text())
    else:
        stores = run_geocoding(rows)

    if not stores:
        log.error("지오코딩 결과 없음")
        sys.exit(1)

    insert_db(stores)
    log.info("완료! 총 %d개 판매점 적재", len(stores))


if __name__ == "__main__":
    main()
