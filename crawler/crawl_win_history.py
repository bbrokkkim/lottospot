"""
crawl_win_history.py
동행복권 당첨 판매점 조회 API를 크롤링하여 winning_history 테이블에 적재합니다.

실행:
  python3 crawl_win_history.py                      # 전체 (1~현재 회차)
  python3 crawl_win_history.py --start 1100         # 특정 회차부터
  python3 crawl_win_history.py --start 1150 --end 1163  # 범위 지정
  python3 crawl_win_history.py --test               # 최신 3회차만 테스트

API:
  GET /wnprchsplcsrch/selectLtWnShp.do
  params: srchWnShpRnk(1|2), srchLtEpsd(회차), srchShpLctn(지역, 빈값=전국)
  응답: {data: {list: [{ltShpId, shpNm, shpAddr, shpLat, shpLot, wnShpRnk, region}]}}
"""
import argparse
import logging
import os
import time
from datetime import date, timedelta

import pymysql
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://www.dhlottery.co.kr"
API_PATH = "/wnprchsplcsrch/selectLtWnShp.do"
ROUND_1_DATE = date(2002, 12, 7)  # 1회차 날짜

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": f"{BASE_URL}/wnprchsplcsrch/home",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# Tor 프록시 (직접 연결 실패 시 자동 사용)
TOR_PROXIES = {
    "http": "socks5h://127.0.0.1:9050",
    "https": "socks5h://127.0.0.1:9050",
}

def _setup_proxy():
    """직접 연결 먼저 시도, 실패하면 Tor 사용."""
    try:
        r = requests.get(BASE_URL + "/wnprchsplcsrch/home",
                         headers=HEADERS, timeout=8)
        if r.status_code == 200:
            log.info("직접 연결 성공 (Tor 불필요)")
            return
    except Exception:
        pass
    log.info("직접 연결 실패 → Tor 프록시 사용")
    SESSION.proxies.update(TOR_PROXIES)

_setup_proxy()


def get_current_round() -> int:
    """오늘 기준 최신 회차 계산."""
    today = date.today()
    days = (today - ROUND_1_DATE).days
    return days // 7 + 1


def round_to_date(rnd: int) -> str:
    return (ROUND_1_DATE + timedelta(weeks=rnd - 1)).isoformat()


def fetch_winners(rnd: int, rank: int, retries: int = 3) -> list[dict]:
    """특정 회차/등수 당첨 판매점 목록 조회."""
    for attempt in range(retries):
        try:
            r = SESSION.get(
                BASE_URL + API_PATH,
                params={"srchWnShpRnk": rank, "srchLtEpsd": rnd, "srchShpLctn": ""},
                timeout=15,
            )
            if r.status_code != 200:
                log.warning("[%d회/%d등] HTTP %d", rnd, rank, r.status_code)
                time.sleep(2)
                continue

            body = r.json()
            lst = body.get("data", {}).get("list", [])
            return lst

        except requests.Timeout:
            log.warning("[%d회/%d등] 타임아웃 (시도 %d/%d)", rnd, rank, attempt + 1, retries)
            time.sleep(5)
        except Exception as e:
            log.warning("[%d회/%d등] 에러: %s", rnd, rank, e)
            time.sleep(2)
    return []


def match_store(cur, item: dict) -> int | None:
    """
    dhlottery 판매점 → lotto_store.id 매칭.
    1) 좌표 반경 50m 이내 + 이름 유사
    2) 주소 포함 + 이름 일치
    3) 이름만 일치 (최근접)
    """
    lat = item.get("shpLat")
    lng = item.get("shpLot")
    name = (item.get("shpNm") or "").strip()
    addr = (item.get("shpAddr") or "").strip()

    # 1) 좌표 매칭 (50m 이내)
    if lat and lng:
        try:
            lat_f, lng_f = float(lat), float(lng)
            cur.execute(
                """
                SELECT id, name FROM lotto_store
                WHERE ST_Distance_Sphere(
                    location,
                    ST_GeomFromText(%s, 4326)
                ) < 50
                ORDER BY ST_Distance_Sphere(location, ST_GeomFromText(%s, 4326))
                LIMIT 1
                """,
                (f"POINT({lat_f} {lng_f})", f"POINT({lat_f} {lng_f})"),
            )
            row = cur.fetchone()
            if row:
                return row[0]
        except Exception:
            pass

    # 2) 이름 + 주소 매칭
    if name and addr:
        addr_keyword = addr[:15]  # 앞 15자로 비교
        cur.execute(
            "SELECT id FROM lotto_store WHERE name = %s AND address LIKE %s LIMIT 1",
            (name, f"%{addr_keyword}%"),
        )
        row = cur.fetchone()
        if row:
            return row[0]

    # 3) 이름만 매칭
    if name:
        cur.execute("SELECT id FROM lotto_store WHERE name = %s LIMIT 1", (name,))
        row = cur.fetchone()
        if row:
            return row[0]

    return None


def crawl(start_round: int, end_round: int):
    conn = pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASS", "12341234"),
        database=os.getenv("DB_NAME", "lottospot"),
        charset="utf8mb4",
    )
    cur = conn.cursor()

    insert_sql = """
        INSERT IGNORE INTO winning_history (store_id, round, win_rank, win_date, created_at)
        VALUES (%s, %s, %s, %s, NOW())
    """

    total_inserted = 0
    total_no_match = 0
    batch = []

    log.info("%d~%d회차 크롤링 시작", start_round, end_round)

    for rnd in range(start_round, end_round + 1):
        win_date = round_to_date(rnd)

        for rank in [1, 2]:
            winners = fetch_winners(rnd, rank)

            if not winners and rnd % 10 == 0:
                log.info("[%d회/%d등] 결과 없음", rnd, rank)

            for item in winners:
                store_id = match_store(cur, item)
                if store_id:
                    batch.append((store_id, rnd, rank, win_date))
                else:
                    total_no_match += 1
                    log.debug("[%d회/%d등] 매칭 실패: %s / %s", rnd, rank, item.get("shpNm"), item.get("shpAddr"))

            time.sleep(0.3)  # API 속도 제한 대응

        # 50회차마다 일괄 저장
        if batch and rnd % 50 == 0:
            cur.executemany(insert_sql, batch)
            conn.commit()
            total_inserted += len(batch)
            log.info("[%d회] 중간 저장: 누적 %d건 (매칭실패 %d건)", rnd, total_inserted, total_no_match)
            batch = []

    # 나머지 저장
    if batch:
        cur.executemany(insert_sql, batch)
        conn.commit()
        total_inserted += len(batch)

    log.info("완료: 총 %d건 삽입, %d건 매칭 실패", total_inserted, total_no_match)
    cur.close()
    conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1, help="시작 회차 (기본 1)")
    parser.add_argument("--end", type=int, default=None, help="끝 회차 (기본 최신 회차)")
    parser.add_argument("--test", action="store_true", help="최신 3회차만 테스트")
    args = parser.parse_args()

    current = get_current_round()
    log.info("현재 최신 회차: %d", current)

    if args.test:
        start, end = current - 2, current
    else:
        start = args.start
        end = args.end or current

    crawl(start, end)


if __name__ == "__main__":
    main()
