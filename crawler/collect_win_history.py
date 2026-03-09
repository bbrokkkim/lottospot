"""
collect_win_history.py
동행복권에서 로또 6/45 1등/2등 당첨 판매점 이력을 수집하고 DB에 적재합니다.

수집 흐름:
  1. GET https://www.dhlottery.co.kr/store.do?method=topStore&pageGubun=L645
     회차별 당첨 판매점 HTML 파싱 (BeautifulSoup)
  2. 판매점명+주소로 store 테이블에서 store_key 매칭
  3. win_history 테이블에 INSERT IGNORE

실행 방법:
  # 최근 200회차 수집 (기본)
  python collect_win_history.py

  # 특정 범위 수집
  python collect_win_history.py --start-round 1000 --end-round 1100

  # 테스트 모드: 최근 3회차만 수집, DB 적재 없음
  python collect_win_history.py --test

  # DB 적재 없이 JSON만 저장
  python collect_win_history.py --no-db
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# -------------------------------------------------------------------
# 경로 설정
# -------------------------------------------------------------------
_CRAWLER_DIR  = Path(__file__).resolve().parent
_PROJECT_ROOT = _CRAWLER_DIR.parent
_DATA_DIR     = _PROJECT_ROOT / "data"
_LOG_DIR      = _PROJECT_ROOT / "logs"
_WIN_OUT      = _DATA_DIR / "raw_win_history.json"

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
# 동행복권 당첨 판매점 API 상수
# -------------------------------------------------------------------
_DH_TOP_STORE_URL = (
    "https://www.dhlottery.co.kr/store.do"
    "?method=topStore&pageGubun=L645"
)
_DH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.dhlottery.co.kr/store.do?method=topStore&pageGubun=L645",
}

_REQUEST_DELAY = 1.0   # 요청 간 최소 대기 (초)
_MAX_BACKOFF   = 64.0
_DEFAULT_RANGE = 200   # 기본 수집 회차 수

# 로또 6/45 첫 회차 추첨일: 2002-12-07 (1회차)
# 매주 토요일 추첨. 대략 최신 회차를 서버에서 확인하거나 계산으로 추정.
_FIRST_DRAW_DATE = date(2002, 12, 7)


# -------------------------------------------------------------------
# HTTP 유틸
# -------------------------------------------------------------------

def _get_with_retry(url: str, params: dict | None = None,
                    max_retries: int = 5) -> str | None:
    """
    GET 요청을 재시도 로직과 함께 실행합니다.
    성공 시 응답 HTML 문자열 반환, 실패 시 None 반환.
    """
    backoff = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(
                url,
                headers=_DH_HEADERS,
                params=params,
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
            resp.encoding = "euc-kr"
            return resp.text

        except requests.exceptions.Timeout:
            logger.warning("타임아웃 (%d/%d)", attempt, max_retries)
            time.sleep(min(backoff, _MAX_BACKOFF))
            backoff *= 2
        except requests.exceptions.RequestException as exc:
            logger.warning("요청 실패 (%d/%d): %s", attempt, max_retries, exc)
            time.sleep(min(backoff, _MAX_BACKOFF))
            backoff *= 2

    logger.error("최대 재시도 초과: %s", url)
    return None


# -------------------------------------------------------------------
# 최신 회차 조회
# -------------------------------------------------------------------

def _get_latest_round() -> int:
    """
    동행복권 topStore 페이지에서 현재 수집 가능한 최신 회차를 파악합니다.
    파싱 실패 시 날짜 계산으로 추정합니다.
    """
    html = _get_with_retry(_DH_TOP_STORE_URL)
    if html:
        soup = BeautifulSoup(html, "lxml")
        # 회차 선택 드롭다운 또는 텍스트에서 최신 회차 파싱
        # <select name="drwNo"> 또는 텍스트 패턴 "제 NNN회"
        select = soup.find("select", {"name": "drwNo"})
        if select:
            options = select.find_all("option")
            if options:
                # 첫 번째 옵션이 최신 회차
                try:
                    return int(options[0].get("value", 0))
                except (ValueError, TypeError):
                    pass

        # 텍스트 파싱 폴백
        import re
        match = re.search(r"제\s*(\d+)\s*회", html)
        if match:
            return int(match.group(1))

    # 날짜 계산 추정: 2002-12-07이 1회차, 매주 토요일
    today = date.today()
    delta = (today - _FIRST_DRAW_DATE).days
    estimated = delta // 7 + 1
    logger.warning("최신 회차 파싱 실패. 날짜 기반 추정값 사용: %d회차", estimated)
    return estimated


# -------------------------------------------------------------------
# 당첨 판매점 파싱
# -------------------------------------------------------------------

def _parse_win_table(html: str, round_no: int) -> list[dict]:
    """
    topStore 페이지 HTML에서 당첨 판매점 테이블을 파싱합니다.

    Parameters
    ----------
    html : str
        동행복권 topStore 페이지 HTML
    round_no : int
        해당 회차 번호

    Returns
    -------
    list[dict]
        당첨 정보 dict 목록:
        {round, rank, store_name, address, win_date, store_key(None)}
    """
    soup = BeautifulSoup(html, "lxml")
    results: list[dict] = []

    # 당첨 발표일 파싱 시도
    import re
    win_date_str = None
    date_pattern = re.compile(r"(\d{4})[.\-](\d{1,2})[.\-](\d{1,2})")
    date_match = date_pattern.search(html[:2000])
    if date_match:
        y, m, d = date_match.groups()
        try:
            win_date_str = f"{y}-{int(m):02d}-{int(d):02d}"
        except Exception:
            win_date_str = None

    # 1등/2등 테이블 탐색
    # 동행복권 topStore 페이지 구조:
    #   <table> ... <tbody> <tr> <td>등수</td> <td>상호명</td> <td>주소</td> ...
    # rank 별로 별도 섹션이 있을 수 있음.
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue

            # 등수 파싱 (1등 or 2등)
            rank_text = cols[0].get_text(strip=True)
            rank: int | None = None
            if "1등" in rank_text or rank_text == "1":
                rank = 1
            elif "2등" in rank_text or rank_text == "2":
                rank = 2

            if rank is None:
                continue

            store_name = cols[1].get_text(strip=True) if len(cols) > 1 else ""
            address    = cols[2].get_text(strip=True) if len(cols) > 2 else ""

            if not store_name:
                continue

            results.append({
                "round":      round_no,
                "rank":       rank,
                "store_name": store_name,
                "address":    address,
                "win_date":   win_date_str,
                "store_key":  None,   # DB 매칭 후 채워짐
            })

    return results


def _fetch_round_winners(round_no: int) -> list[dict]:
    """
    특정 회차의 1등/2등 당첨 판매점을 수집합니다.

    Parameters
    ----------
    round_no : int
        수집할 회차 번호

    Returns
    -------
    list[dict]
        당첨 정보 dict 목록
    """
    params = {"drwNo": round_no}
    html = _get_with_retry(_DH_TOP_STORE_URL, params=params)
    if html is None:
        logger.warning("회차 %d: HTML 수신 실패", round_no)
        return []

    records = _parse_win_table(html, round_no)
    logger.debug("회차 %d: %d건 파싱", round_no, len(records))
    return records


# -------------------------------------------------------------------
# store_key 매칭
# -------------------------------------------------------------------

def _match_store_keys(records: list[dict]) -> list[dict]:
    """
    store_name + address로 DB store 테이블에서 store_key를 조회합니다.
    매칭 실패 시 store_key는 None으로 남깁니다.
    DB 연결 실패 시 원본 records를 그대로 반환합니다.
    """
    if not records:
        return records

    try:
        from utils.db import get_connection
    except ImportError:
        logger.warning("utils.db 임포트 실패, store_key 매칭 건너뜀")
        return records

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                for rec in records:
                    # 1차: 이름 + 주소 완전 일치
                    cur.execute(
                        "SELECT store_key FROM store "
                        "WHERE name = %(name)s AND address = %(address)s LIMIT 1",
                        {"name": rec["store_name"], "address": rec["address"]},
                    )
                    row = cur.fetchone()
                    if row:
                        rec["store_key"] = row["store_key"]
                        continue

                    # 2차: 이름만 일치
                    cur.execute(
                        "SELECT store_key FROM store WHERE name = %(name)s LIMIT 1",
                        {"name": rec["store_name"]},
                    )
                    row = cur.fetchone()
                    if row:
                        rec["store_key"] = row["store_key"]

    except Exception as exc:
        logger.warning("store_key 매칭 중 DB 오류 (건너뜀): %s", exc)

    matched = sum(1 for r in records if r.get("store_key"))
    logger.info("store_key 매칭: %d/%d건", matched, len(records))
    return records


# -------------------------------------------------------------------
# 메인 수집 파이프라인
# -------------------------------------------------------------------

def collect_win_history(
    start_round: int | None = None,
    end_round: int | None = None,
    test_mode: bool = False,
) -> list[dict]:
    """
    동행복권에서 로또 당첨 판매점 이력을 수집합니다.

    Parameters
    ----------
    start_round : int | None
        수집 시작 회차. None이면 (end_round - DEFAULT_RANGE + 1).
    end_round : int | None
        수집 종료 회차. None이면 최신 회차.
    test_mode : bool
        True이면 최근 3회차만 수집.

    Returns
    -------
    list[dict]
        당첨 이력 dict 목록
    """
    latest = _get_latest_round()
    logger.info("최신 회차: %d", latest)

    if test_mode:
        end   = latest
        start = max(1, latest - 2)   # 최근 3회차
    else:
        end   = end_round if end_round else latest
        start = start_round if start_round else max(1, end - _DEFAULT_RANGE + 1)

    logger.info("수집 범위: %d ~ %d회차 (%d회차)", start, end, end - start + 1)

    all_records: list[dict] = []

    for rnd in range(end, start - 1, -1):
        records = _fetch_round_winners(rnd)
        all_records.extend(records)

        if rnd != start:
            time.sleep(_REQUEST_DELAY)

    logger.info("HTML 파싱 완료: %d건", len(all_records))

    # store_key 매칭
    all_records = _match_store_keys(all_records)

    return all_records


# -------------------------------------------------------------------
# JSON 저장
# -------------------------------------------------------------------

def save_json(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    logger.info("JSON 저장 완료: %s (%d건)", path, len(records))


# -------------------------------------------------------------------
# Redis 캐시 무효화
# -------------------------------------------------------------------

def _invalidate_redis_cache() -> None:
    """nearby:* Redis 캐시를 무효화합니다. 실패해도 크롤러는 정상 종료."""
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
        logger.info("Redis 캐시 무효화: %d개 키 삭제", deleted)
    except Exception as exc:
        logger.warning("Redis 무효화 실패 (무시): %s", exc)


# -------------------------------------------------------------------
# 진입점
# -------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="동행복권 로또 당첨이력 수집기",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--test", action="store_true",
        help="테스트 모드: 최근 3회차만 수집, DB 적재 없음",
    )
    parser.add_argument(
        "--start-round", type=int, default=None,
        help="수집 시작 회차 (기본값: end_round - 200 + 1)",
    )
    parser.add_argument(
        "--end-round", type=int, default=None,
        help="수집 종료 회차 (기본값: 최신 회차)",
    )
    parser.add_argument(
        "--no-db", action="store_true",
        help="DB 적재 건너뜀 (JSON 파일만 저장)",
    )
    parser.add_argument(
        "--output", type=str, default=str(_WIN_OUT),
        help=f"결과 JSON 저장 경로 (기본값: {_WIN_OUT})",
    )
    args = parser.parse_args()

    logger.info("당첨이력 수집 시작 | test=%s | start=%s | end=%s | no_db=%s",
                args.test, args.start_round, args.end_round, args.no_db)

    # 1. 수집
    records = collect_win_history(
        start_round=args.start_round,
        end_round=args.end_round,
        test_mode=args.test,
    )

    if not records:
        logger.warning("수집된 당첨이력이 없습니다.")
        sys.exit(0)

    # 2. JSON 저장
    save_json(records, Path(args.output))

    # 3. DB 적재
    db_loaded = 0
    if not args.test and not args.no_db:
        # store_key가 있는 레코드만 DB 적재
        valid = [r for r in records if r.get("store_key")]
        skipped = len(records) - len(valid)
        if skipped > 0:
            logger.warning("store_key 미매칭으로 %d건 DB 적재 건너뜀", skipped)

        try:
            from utils.db import insert_win_history
            db_loaded = insert_win_history(valid)
        except Exception as exc:
            logger.error("DB 적재 실패: %s", exc)

        # 4. Redis 캐시 무효화
        _invalidate_redis_cache()
    else:
        reason = "테스트 모드" if args.test else "--no-db 옵션"
        logger.info("%s: DB 적재 및 캐시 무효화를 건너뜁니다.", reason)

    # 최종 보고
    matched = sum(1 for r in records if r.get("store_key"))
    rank1   = sum(1 for r in records if r.get("rank") == 1)
    rank2   = sum(1 for r in records if r.get("rank") == 2)

    logger.info("=" * 50)
    logger.info("수집 완료 보고")
    logger.info("  수집 건수     : %d", len(records))
    logger.info("  1등 당첨      : %d건", rank1)
    logger.info("  2등 당첨      : %d건", rank2)
    logger.info("  store_key 매칭: %d건 / %d건", matched, len(records))
    if not args.test and not args.no_db:
        logger.info("  DB 적재 건수  : %d", db_loaded)
    logger.info("  저장 경로     : %s", args.output)
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
