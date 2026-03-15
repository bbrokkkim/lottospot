"""
collect_stores.py
동행복권 공식 사이트에서 전국 로또 판매점 목록을 수집하고 DB에 적재합니다.

수집 흐름:
  1. GET https://www.dhlottery.co.kr/prchsplcsrch/selectLtShp.do
     시도별 판매점 목록 JSON 파싱 (좌표 포함)
  2. Store 테이블 UPSERT (store_key 기준)
  3. Redis nearby:* 캐시 무효화

실행 방법:
  # 전체 수집 (DB 적재 포함)
  python collect_stores.py

  # 테스트 모드: 서울만, 1페이지(100건), DB 적재 없음
  python collect_stores.py --test

  # 특정 시도만 수집
  python collect_stores.py --sido 경기

  # DB 적재 없이 JSON 파일만 저장
  python collect_stores.py --no-db
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# -------------------------------------------------------------------
# 경로 설정
# -------------------------------------------------------------------
_CRAWLER_DIR  = Path(__file__).resolve().parent
_PROJECT_ROOT = _CRAWLER_DIR.parent
_DATA_DIR     = _PROJECT_ROOT / "data"
_SAMPLE_OUT   = _DATA_DIR / "sample_stores.json"
_RAW_OUT      = _DATA_DIR / "raw_stores.json"

load_dotenv(_CRAWLER_DIR / ".env")

# -------------------------------------------------------------------
# 로거
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# 동행복권 API 상수
# -------------------------------------------------------------------
_DH_HOME_URL  = "https://www.dhlottery.co.kr/prchsplcsrch/home"
_DH_API_URL   = "https://www.dhlottery.co.kr/prchsplcsrch/selectLtShp.do"
_DH_HEADERS   = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer":         _DH_HOME_URL,
    "Accept":          "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "X-Requested-With": "XMLHttpRequest",
}

# 시도명 목록 (API가 한글 이름을 그대로 사용)
_SIDO_LIST = [
    "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
    "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
]

_REQUEST_DELAY      = 1.0   # 요청 간 최소 대기 (초) — CLAUDE.md 규칙
_MAX_BACKOFF        = 64.0  # 429 exponential backoff 상한 (초)
_RECORDS_PER_PAGE   = 100   # 페이지당 수집 건수


# -------------------------------------------------------------------
# 세션 (쿠키 유지용)
# -------------------------------------------------------------------

def _create_session() -> requests.Session:
    """홈 페이지 방문으로 쿠키를 획득한 세션을 반환합니다."""
    session = requests.Session()
    session.headers.update(_DH_HEADERS)
    try:
        resp = session.get(_DH_HOME_URL, timeout=15, allow_redirects=True)
        logger.info("홈 페이지 방문 완료 (status=%d)", resp.status_code)
    except Exception as exc:
        logger.warning("홈 페이지 방문 실패 (쿠키 없이 진행): %s", exc)
    time.sleep(1.0)
    return session


# -------------------------------------------------------------------
# API 요청 헬퍼
# -------------------------------------------------------------------

def _get_with_retry(
    session: requests.Session,
    params: dict,
    max_retries: int = 5,
) -> dict | None:
    """
    selectLtShp.do GET 요청을 재시도 로직과 함께 실행합니다.
    성공 시 JSON dict 반환, 실패 시 None 반환.
    """
    backoff = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            resp = session.get(
                _DH_API_URL,
                params=params,
                timeout=20,
            )

            if resp.status_code == 429:
                wait = min(backoff, _MAX_BACKOFF)
                logger.warning("429 Too Many Requests. %.0f초 후 재시도 (%d/%d)", wait, attempt, max_retries)
                time.sleep(wait)
                backoff *= 2
                continue

            resp.raise_for_status()
            return resp.json()

        except requests.exceptions.Timeout:
            logger.warning("타임아웃 (%d/%d)", attempt, max_retries)
            time.sleep(min(backoff, _MAX_BACKOFF))
            backoff *= 2
        except requests.exceptions.RequestException as exc:
            logger.warning("요청 실패 (%d/%d): %s", attempt, max_retries, exc)
            time.sleep(min(backoff, _MAX_BACKOFF))
            backoff *= 2
        except Exception as exc:
            logger.error("예상치 못한 오류: %s", exc)
            return None

    logger.error("최대 재시도 초과")
    return None


# -------------------------------------------------------------------
# JSON 파싱
# -------------------------------------------------------------------

def _parse_response(data: dict, sido: str) -> list[dict]:
    """
    selectLtShp.do JSON 응답에서 판매점 목록을 파싱합니다.

    응답 구조:
    {
      "list": [
        {
          "ltShpId": "판매점ID",
          "conmNm": "판매점명",
          "bplcRdnmDaddr": "도로명주소",
          "shpLat": 37.5665,
          "shpLot": 126.9780,
          "tm1BplcLctnAddr": "서울",     // 시도
          "tm2BplcLctnAddr": "중구",     // 시군구
          "shpTelno": "02-1234-5678",
          "slrOperSttsCd": "01"          // 운영상태
        }, ...
      ],
      "totalCount": 1234
    }
    """
    stores = []
    inner = data.get("data") or {}
    if isinstance(inner, dict):
        items = inner.get("list") or inner.get("ltShpList") or []
    else:
        items = inner if isinstance(inner, list) else []
    for item in items:
        store_key = str(item.get("ltShpId", "")).strip()
        name      = str(item.get("conmNm", "")).strip()
        address   = str(item.get("bplcRdnmDaddr", "")).strip()
        phone     = str(item.get("shpTelno", "")).strip()
        sigungu   = str(item.get("tm2BplcLctnAddr", "")).strip()
        sido_raw  = str(item.get("tm1BplcLctnAddr", sido)).strip()

        lat = item.get("shpLat")
        lng = item.get("shpLot")

        try:
            lat = float(lat) if lat else None
            lng = float(lng) if lng else None
        except (ValueError, TypeError):
            lat, lng = None, None

        if not name:
            continue

        if not store_key:
            import hashlib
            store_key = hashlib.md5(f"{sido_raw}_{name}_{address}".encode()).hexdigest()[:12]

        stores.append({
            "store_key": store_key,
            "name":      name,
            "address":   address,
            "lat":       lat,
            "lng":       lng,
            "sido":      sido_raw or sido,
            "sigungu":   sigungu,
            "phone":     phone,
        })

    return stores


# -------------------------------------------------------------------
# 시도별 수집
# -------------------------------------------------------------------

def _collect_sido(
    session: requests.Session,
    sido: str,
    limit: int | None = None,
) -> list[dict]:
    """특정 시도의 전체 판매점을 페이지 단위로 수집합니다."""
    stores: list[dict] = []
    page = 1

    logger.info("[%s] 수집 시작", sido)

    while True:
        params = {
            "l645LtNtslYn":      "N",
            "l520LtNtslYn":      "N",
            "st5LtNtslYn":       "N",
            "st10LtNtslYn":      "N",
            "st20LtNtslYn":      "N",
            "cpexUsePsbltyYn":   "N",
            "pageNum":           page,
            "recordCountPerPage": limit if limit and limit < _RECORDS_PER_PAGE else _RECORDS_PER_PAGE,
            "pageCount":         5,
            "srchCtpvNm":        sido,
            "srchSggNm":         "",
            "_":                 int(time.time() * 1000),
        }

        data = _get_with_retry(session, params)
        if data is None:
            logger.error("[%s] 페이지 %d 요청 실패", sido, page)
            break

        parsed = _parse_response(data, sido)
        if not parsed:
            logger.debug("[%s] 페이지 %d 결과 없음. 수집 종료", sido, page)
            break

        stores.extend(parsed)

        inner = data.get("data") or {}
        total_count = (inner.get("total") if isinstance(inner, dict) else 0) or 0
        total_pages = (total_count + _RECORDS_PER_PAGE - 1) // _RECORDS_PER_PAGE if total_count else page
        logger.info("[%s] 페이지 %d/%d 완료: %d건 파싱, 누적 %d건", sido, page, total_pages, len(parsed), len(stores))

        if limit and len(stores) >= limit:
            break
        if page >= total_pages or len(parsed) < _RECORDS_PER_PAGE:
            break

        page += 1
        time.sleep(_REQUEST_DELAY)

    logger.info("[%s] 수집 완료: %d건", sido, len(stores))
    return stores


# -------------------------------------------------------------------
# 메인 수집 파이프라인
# -------------------------------------------------------------------

def collect_all_stores(
    sido_filter: str | None = None,
    test_mode: bool = False,
) -> list[dict]:
    """전국(또는 특정 시도) 로또 판매점을 수집합니다."""
    session = _create_session()

    target_sidos = [sido_filter] if sido_filter else (["서울"] if test_mode else _SIDO_LIST)
    limit = _RECORDS_PER_PAGE if test_mode else None

    all_stores: list[dict] = []
    seen_keys: set[str] = set()
    error_count = 0

    for sido in target_sidos:
        try:
            stores = _collect_sido(session, sido, limit=limit)
            for s in stores:
                key = s["store_key"]
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_stores.append(s)
        except Exception as exc:
            logger.error("[%s] 수집 중 예외: %s", sido, exc)
            error_count += 1

        if len(target_sidos) > 1:
            time.sleep(_REQUEST_DELAY)

    logger.info("전체 수집 완료: %d건 (오류 시도: %d)", len(all_stores), error_count)
    return all_stores


# -------------------------------------------------------------------
# Redis 캐시 무효화
# -------------------------------------------------------------------

def _invalidate_redis_cache() -> None:
    import os
    try:
        import redis
    except ImportError:
        logger.warning("redis 패키지 없음. 캐시 무효화 건너뜀.")
        return

    try:
        r = redis.Redis(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=int(os.environ.get("REDIS_PORT", 6379)),
            db=int(os.environ.get("REDIS_DB", 0)),
            password=os.environ.get("REDIS_PASSWORD") or None,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        r.ping()
        cursor, deleted = 0, 0
        while True:
            cursor, keys = r.scan(cursor=cursor, match="nearby:*", count=200)
            if keys:
                r.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break
        logger.info("Redis 캐시 무효화 완료: %d개 키 삭제", deleted)
    except Exception as exc:
        logger.warning("Redis 무효화 실패 (무시): %s", exc)


# -------------------------------------------------------------------
# 진입점
# -------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="동행복권 로또 판매점 수집기")
    parser.add_argument("--test",  action="store_true", help="테스트 모드: 서울 1페이지만, DB 적재 없음")
    parser.add_argument("--sido",  type=str, default=None, help=f"시도 필터 (예: 경기, 부산 ...)")
    parser.add_argument("--no-db", action="store_true", help="DB 적재 건너뜀")
    parser.add_argument("--output", type=str, default=None, help="결과 JSON 저장 경로")
    args = parser.parse_args()

    if args.sido and args.sido not in _SIDO_LIST:
        logger.error("알 수 없는 시도명: %s (가능한 값: %s)", args.sido, ", ".join(_SIDO_LIST))
        sys.exit(1)

    logger.info("판매점 수집 시작 | sido=%s | test=%s | no_db=%s", args.sido, args.test, args.no_db)

    # 1. 수집
    stores = collect_all_stores(sido_filter=args.sido, test_mode=args.test)
    if not stores:
        logger.error("수집된 판매점이 없습니다.")
        sys.exit(1)

    logger.info("수집 건수: %d건", len(stores))

    # 2. JSON 저장
    out_path = Path(args.output) if args.output else (_SAMPLE_OUT if args.test else _RAW_OUT)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(stores, f, ensure_ascii=False, indent=2)
    logger.info("JSON 저장 완료: %s", out_path)

    # 3. DB 적재
    db_loaded = 0
    if not args.test and not args.no_db:
        try:
            from db_loader import load_stores
            db_loaded = load_stores(stores)
        except Exception as exc:
            logger.error("DB 적재 실패: %s", exc)

        _invalidate_redis_cache()
    else:
        reason = "테스트 모드" if args.test else "--no-db 옵션"
        logger.info("%s: DB 적재 건너뜁니다.", reason)

    # 최종 보고
    geo_ok = sum(1 for s in stores if s.get("lat") and s.get("lng"))
    logger.info("=" * 50)
    logger.info("수집 완료 보고")
    logger.info("  수집 건수   : %d", len(stores))
    logger.info("  좌표 포함   : %d건 / %d건", geo_ok, len(stores))
    if not args.test and not args.no_db:
        logger.info("  DB 적재 건수: %d", db_loaded)
    logger.info("  저장 경로   : %s", out_path)
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
