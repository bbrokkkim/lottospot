"""
collect_stores.py
동행복권 공식 사이트에서 전국 로또 판매점 목록을 수집하고 DB에 적재합니다.

수집 흐름:
  1. POST https://dhlottery.co.kr/store.do?method=sellerInfo645Result
     지역(시도) 코드별 판매점 목록 수집
  2. 카카오 로컬 API로 주소 -> 좌표 변환
  3. Store 테이블 UPSERT (store_key 기준)
  4. Redis nearby:* 캐시 무효화

실행 방법:
  # 전체 수집 (DB 적재 포함)
  python collect_stores.py

  # 테스트 모드: 샘플 10건 수집, data/sample_stores.json 저장, DB 적재 없음
  # 동행복권 서버 접근 불가 시 내장 모의 데이터를 사용합니다.
  python collect_stores.py --test

  # 특정 시도만 수집
  python collect_stores.py --sido 서울

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
_LOG_DIR      = _PROJECT_ROOT / "logs"
_SAMPLE_OUT   = _DATA_DIR / "sample_stores.json"
_RAW_OUT      = _DATA_DIR / "raw_stores.json"
_FAIL_LOG     = _LOG_DIR / "failed_geocode.log"

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
_DH_BASE_URL = "https://dhlottery.co.kr/store.do"
_DH_METHOD   = "sellerInfo645Result"
_DH_HEADERS  = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer":      "https://dhlottery.co.kr/store.do?method=sellerInfo645",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin":       "https://dhlottery.co.kr",
}

# 시도 코드 매핑 (동행복권 기준)
_SIDO_MAP: dict[str, str] = {
    "서울": "01",
    "경기": "02",
    "부산": "03",
    "강원": "04",
    "충북": "05",
    "충남": "06",
    "전북": "07",
    "전남": "08",
    "경북": "09",
    "경남": "10",
    "제주": "11",
    "인천": "12",
    "광주": "13",
    "대전": "14",
    "울산": "15",
    "대구": "16",
    "세종": "17",
}

_REQUEST_DELAY = 1.0   # 요청 간 최소 대기 (초)
_MAX_BACKOFF   = 64.0  # 429 exponential backoff 상한 (초)
_CONN_TIMEOUT  = 8     # 연결 타임아웃 (초) — 생존 여부 확인용


# -------------------------------------------------------------------
# 엔드포인트 생존 확인
# -------------------------------------------------------------------

def _check_endpoint_alive(timeout: int = _CONN_TIMEOUT) -> bool:
    """
    동행복권 서버에 연결 가능한지 빠르게 확인합니다.
    HEAD 요청 실패 시 False 반환.
    """
    try:
        resp = requests.head(
            "https://dhlottery.co.kr/",
            headers={"User-Agent": _DH_HEADERS["User-Agent"]},
            timeout=timeout,
            allow_redirects=True,
        )
        return resp.status_code < 500
    except Exception:
        return False


# -------------------------------------------------------------------
# 모의(Mock) 샘플 데이터 — 서버 접근 불가 시 테스트 전용
# -------------------------------------------------------------------

_MOCK_STORES: list[dict] = [
    {
        "store_key": "11111001",
        "name": "행운복권방",
        "address": "서울특별시 중구 세종대로 110",
        "address_detail": "1층",
        "phone": "02-1234-5678",
        "is_open": 1,
        "lat": 37.5663,
        "lng": 126.9779,
        "sido": "서울",
        "sigungu": "중구",
    },
    {
        "store_key": "11111002",
        "name": "로또나라",
        "address": "서울특별시 강남구 테헤란로 152",
        "address_detail": "",
        "phone": "02-9876-5432",
        "is_open": 1,
        "lat": 37.5000,
        "lng": 127.0360,
        "sido": "서울",
        "sigungu": "강남구",
    },
    {
        "store_key": "11111003",
        "name": "복권천국",
        "address": "서울특별시 마포구 와우산로 94",
        "address_detail": "",
        "phone": "02-3333-7777",
        "is_open": 1,
        "lat": 37.5510,
        "lng": 126.9240,
        "sido": "서울",
        "sigungu": "마포구",
    },
    {
        "store_key": "11111004",
        "name": "대박복권",
        "address": "서울특별시 송파구 올림픽로 300",
        "address_detail": "",
        "phone": "02-4444-8888",
        "is_open": 1,
        "lat": 37.5147,
        "lng": 127.1060,
        "sido": "서울",
        "sigungu": "송파구",
    },
    {
        "store_key": "11111005",
        "name": "행복로또",
        "address": "서울특별시 노원구 동일로 1321",
        "address_detail": "",
        "phone": "02-5555-9999",
        "is_open": 1,
        "lat": 37.6541,
        "lng": 127.0633,
        "sido": "서울",
        "sigungu": "노원구",
    },
    {
        "store_key": "11111006",
        "name": "황금복권",
        "address": "서울특별시 서초구 반포대로 201",
        "address_detail": "B1",
        "phone": "02-6666-1010",
        "is_open": 1,
        "lat": 37.5040,
        "lng": 127.0050,
        "sido": "서울",
        "sigungu": "서초구",
    },
    {
        "store_key": "11111007",
        "name": "희망복권방",
        "address": "서울특별시 은평구 연서로 365",
        "address_detail": "",
        "phone": "02-7777-2020",
        "is_open": 1,
        "lat": 37.6102,
        "lng": 126.9224,
        "sido": "서울",
        "sigungu": "은평구",
    },
    {
        "store_key": "11111008",
        "name": "미래복권",
        "address": "서울특별시 동대문구 왕산로 222",
        "address_detail": "",
        "phone": "02-8888-3030",
        "is_open": 1,
        "lat": 37.5800,
        "lng": 127.0530,
        "sido": "서울",
        "sigungu": "동대문구",
    },
    {
        "store_key": "11111009",
        "name": "기쁨복권",
        "address": "서울특별시 성북구 아리랑로 19",
        "address_detail": "",
        "phone": "02-9999-4040",
        "is_open": 1,
        "lat": 37.5960,
        "lng": 127.0190,
        "sido": "서울",
        "sigungu": "성북구",
    },
    {
        "store_key": "11111010",
        "name": "천운복권",
        "address": "서울특별시 영등포구 여의대로 24",
        "address_detail": "",
        "phone": "02-1010-5050",
        "is_open": 1,
        "lat": 37.5214,
        "lng": 126.9244,
        "sido": "서울",
        "sigungu": "영등포구",
    },
]


# -------------------------------------------------------------------
# HTTP 요청 헬퍼
# -------------------------------------------------------------------

def _post_with_retry(url: str, data: dict, max_retries: int = 5) -> dict | None:
    """
    POST 요청을 재시도 로직과 함께 실행합니다.
    429 에러 시 exponential backoff, 그 외 실패 시 최대 max_retries회 재시도.
    """
    backoff = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(
                url,
                headers=_DH_HEADERS,
                data=data,
                timeout=15,
            )
            if resp.status_code == 429:
                wait = min(backoff, _MAX_BACKOFF)
                logger.warning("429 Too Many Requests. %.0f초 후 재시도 (%d/%d)",
                               wait, attempt, max_retries)
                time.sleep(wait)
                backoff *= 2
                continue

            resp.raise_for_status()

            content_type = resp.headers.get("Content-Type", "")
            if "json" in content_type:
                return resp.json()

            logger.warning("JSON이 아닌 응답 수신 (Content-Type: %s)", content_type)
            logger.debug("응답 앞부분: %s", resp.text[:300])
            return None

        except requests.exceptions.Timeout:
            logger.warning("타임아웃 (%d/%d)", attempt, max_retries)
            time.sleep(min(backoff, _MAX_BACKOFF))
            backoff *= 2
        except requests.exceptions.RequestException as exc:
            logger.warning("요청 실패 (%d/%d): %s", attempt, max_retries, exc)
            time.sleep(min(backoff, _MAX_BACKOFF))
            backoff *= 2

    logger.error("최대 재시도 초과 (url=%s)", url)
    return None


# -------------------------------------------------------------------
# 동행복권 판매점 파싱
# -------------------------------------------------------------------

def _parse_store_item(item: dict, sido_name: str) -> dict | None:
    """
    동행복권 API 응답의 단일 판매점 항목을 표준 dict로 변환합니다.

    확인된 동행복권 응답 필드:
        SELLER_ID2, SELLER_NAME, ADDRESS, TEL_NO, SIGUNGU_NM
    폴백 키도 함께 처리합니다.
    """
    store_key = str(
        item.get("SELLER_ID2") or item.get("sellerId") or item.get("id") or ""
    ).strip()
    name = (
        item.get("SELLER_NAME") or item.get("sellerName") or item.get("name") or ""
    ).strip()

    if not store_key or not name:
        return None

    address = (item.get("ADDRESS") or item.get("address") or "").strip()
    phone   = (item.get("TEL_NO") or item.get("phone") or item.get("tel") or "").strip()
    sigungu = (item.get("SIGUNGU_NM") or item.get("sigungu") or "").strip()

    return {
        "store_key":      store_key,
        "name":           name,
        "address":        address,
        "address_detail": "",
        "phone":          phone,
        "is_open":        1,
        "lat":            None,
        "lng":            None,
        "sido":           sido_name,
        "sigungu":        sigungu,
    }


def _collect_sido(sido_name: str, sido_code: str,
                  limit: int | None = None) -> list[dict]:
    """
    특정 시도의 전체 판매점을 페이지 단위로 수집합니다.

    Parameters
    ----------
    sido_name : str
        시도명 (예: '서울')
    sido_code : str
        동행복권 시도 코드 (예: '01')
    limit : int | None
        최대 수집 건수. None이면 전체 수집.

    Returns
    -------
    list[dict]
        표준화된 판매점 dict 목록
    """
    stores: list[dict] = []
    page = 1

    logger.info("[%s] 수집 시작 (코드=%s)", sido_name, sido_code)

    while True:
        if limit and len(stores) >= limit:
            break

        payload = {
            "method":     _DH_METHOD,
            "searchType": 3,
            "sltSIDO2":   sido_code,
            "sltGUGUN2":  "0",
            "nowPage":    page,
        }

        data = _post_with_retry(f"{_DH_BASE_URL}?method={_DH_METHOD}", payload)

        if data is None:
            logger.error("[%s] 페이지 %d 요청 실패", sido_name, page)
            break

        items = (
            data.get("arrSellerInfo")
            or data.get("sellerList")
            or data.get("list")
            or []
        )

        if not items:
            logger.debug("[%s] 페이지 %d에 데이터 없음, 수집 종료", sido_name, page)
            break

        for item in items:
            if limit and len(stores) >= limit:
                break
            parsed = _parse_store_item(item, sido_name)
            if parsed:
                stores.append(parsed)

        page_info   = data.get("pageInfo") or data.get("paginationInfo") or {}
        total_pages = int(
            page_info.get("totalPage")
            or page_info.get("totalPageCount")
            or 1
        )
        logger.debug("[%s] 페이지 %d/%d, 누적=%d건",
                     sido_name, page, total_pages, len(stores))

        if page >= total_pages:
            break

        page += 1
        time.sleep(_REQUEST_DELAY)

    logger.info("[%s] 수집 완료: %d건", sido_name, len(stores))
    return stores


# -------------------------------------------------------------------
# 메인 수집 파이프라인
# -------------------------------------------------------------------

def collect_all_stores(
    sido_filter: str | None = None,
    test_mode: bool = False,
) -> list[dict]:
    """
    전국(또는 특정 시도) 로또 판매점을 수집합니다.

    테스트 모드에서 동행복권 서버 접근이 불가능할 경우
    내장 모의(Mock) 데이터 10건을 반환합니다.

    Parameters
    ----------
    sido_filter : str | None
        시도명 필터 (예: '서울'). None이면 전체 시도 수집.
    test_mode : bool
        True이면 서울 1개 시도, 최대 10건만 수집.

    Returns
    -------
    list[dict]
        중복 제거된 판매점 dict 목록
    """
    # 테스트 모드에서 엔드포인트 생존 여부 먼저 확인
    if test_mode:
        logger.info("엔드포인트 생존 확인 중 (timeout=%ds)...", _CONN_TIMEOUT)
        alive = _check_endpoint_alive()
        if not alive:
            logger.warning(
                "동행복권 서버에 연결할 수 없습니다. "
                "테스트 모드: 내장 모의 데이터 %d건을 사용합니다.",
                len(_MOCK_STORES),
            )
            return list(_MOCK_STORES)

    target_sidos = (
        [(sido_filter, _SIDO_MAP[sido_filter])]
        if sido_filter and sido_filter in _SIDO_MAP
        else list(_SIDO_MAP.items())
    )

    if test_mode:
        target_sidos = [("서울", "01")]

    all_stores: list[dict] = []
    seen_keys: set[str] = set()

    for sido_name, sido_code in target_sidos:
        limit  = 10 if test_mode else None
        stores = _collect_sido(sido_name, sido_code, limit=limit)

        for s in stores:
            key = s["store_key"]
            if key not in seen_keys:
                seen_keys.add(key)
                all_stores.append(s)

        if not test_mode:
            time.sleep(_REQUEST_DELAY)

    # 실제 수집 실패 시 테스트 모드에서 모의 데이터로 폴백
    if not all_stores and test_mode:
        logger.warning("실제 수집 결과가 없습니다. 모의 데이터로 폴백합니다.")
        return list(_MOCK_STORES)

    logger.info("전체 수집 완료: %d건 (중복 제거 후)", len(all_stores))
    return all_stores


# -------------------------------------------------------------------
# Redis 캐시 무효화
# -------------------------------------------------------------------

def _invalidate_redis_cache() -> None:
    """
    Redis의 nearby:* 패턴 키를 삭제합니다.
    Redis 연결 실패 시 경고만 출력하고 크롤러는 정상 종료합니다.
    """
    import os
    try:
        import redis
    except ImportError:
        logger.warning("redis 패키지가 없어 캐시 무효화를 건너뜁니다.")
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

        logger.info("Redis 캐시 무효화 완료: %d개 키 삭제 (패턴=nearby:*)", deleted)

    except Exception as exc:
        logger.warning("Redis 캐시 무효화 실패 (무시하고 계속): %s", exc)


# -------------------------------------------------------------------
# JSON 저장
# -------------------------------------------------------------------

def save_json(stores: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(stores, f, ensure_ascii=False, indent=2)
    logger.info("JSON 저장 완료: %s (%d건)", path, len(stores))


# -------------------------------------------------------------------
# 진입점
# -------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="동행복권 로또 판매점 수집기",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--test", action="store_true",
        help=(
            "테스트 모드: 최대 10건 수집, data/sample_stores.json 저장, DB 적재 없음. "
            "서버 접근 불가 시 내장 모의 데이터를 사용합니다."
        ),
    )
    parser.add_argument(
        "--sido", type=str, default=None,
        help=f"시도 필터 (선택값: {', '.join(_SIDO_MAP.keys())})",
    )
    parser.add_argument(
        "--no-db", action="store_true",
        help="DB 적재 건너뜀 (JSON 파일만 저장)",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="결과 JSON 저장 경로 (기본값: data/raw_stores.json 또는 data/sample_stores.json)",
    )
    args = parser.parse_args()

    if args.sido and args.sido not in _SIDO_MAP:
        logger.error("알 수 없는 시도명: %s (가능한 값: %s)",
                     args.sido, ", ".join(_SIDO_MAP.keys()))
        sys.exit(1)

    logger.info("판매점 수집 시작 | sido=%s | test=%s | no_db=%s",
                args.sido, args.test, args.no_db)

    # 1. 수집
    stores = collect_all_stores(
        sido_filter=args.sido,
        test_mode=args.test,
    )

    if not stores:
        logger.error("수집된 판매점이 없습니다.")
        sys.exit(1)

    # 2. 좌표 변환 (카카오 API -> 네이버 폴백)
    geo_success = 0
    geo_fail    = 0
    try:
        from utils.geocode import batch_geocode
        geo_success, geo_fail = batch_geocode(stores)
    except Exception as exc:
        logger.error("geocoding 오류 (건너뜀): %s", exc)

    # 3. JSON 저장
    out_path = Path(args.output) if args.output else (
        _SAMPLE_OUT if args.test else _RAW_OUT
    )
    save_json(stores, out_path)

    # 4. DB 적재 (테스트 모드 또는 --no-db 시 건너뜀)
    db_loaded = 0
    if not args.test and not args.no_db:
        try:
            from utils.db import upsert_stores
            db_loaded = upsert_stores(stores)
        except Exception as exc:
            logger.error("DB 적재 실패: %s", exc)

        # 5. Redis 캐시 무효화
        _invalidate_redis_cache()
    else:
        reason = "테스트 모드" if args.test else "--no-db 옵션"
        logger.info("%s: DB 적재 및 캐시 무효화를 건너뜁니다.", reason)

    # 최종 보고
    logger.info("=" * 50)
    logger.info("수집 완료 보고")
    logger.info("  수집 건수     : %d", len(stores))
    logger.info("  좌표 변환 성공: %d", geo_success)
    logger.info("  좌표 변환 실패: %d", geo_fail)
    if geo_success + geo_fail > 0:
        rate = geo_success / (geo_success + geo_fail) * 100
        logger.info("  좌표 성공률   : %.1f%%", rate)
    if not args.test and not args.no_db:
        logger.info("  DB 적재 건수  : %d", db_loaded)
    logger.info("  저장 경로     : %s", out_path)
    if geo_fail > 0:
        logger.info("  실패 로그     : %s", _FAIL_LOG)
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
