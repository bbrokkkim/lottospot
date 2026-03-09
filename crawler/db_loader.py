"""
db_loader.py
MySQL에 복권판매점 및 당첨이력 데이터를 적재하는 모듈.
판매점은 store_key 기준 UPSERT, 당첨이력은 INSERT IGNORE 처리합니다.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Generator

import pymysql
import pymysql.cursors
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# 환경변수에서 DB 접속 정보 로드
_DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", 3306)),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASS", ""),
    "db": os.environ.get("DB_NAME", "lottospot"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": False,
}

# 배치 처리 단위
_BATCH_SIZE = 100

# UPSERT SQL: store_key 기준 중복 시 최신 데이터로 갱신
_UPSERT_STORE_SQL = """
INSERT INTO lotto_store (store_key, name, address, lat, lng, sido, sigungu, updated_at)
VALUES (%(store_key)s, %(name)s, %(address)s, %(lat)s, %(lng)s, %(sido)s, %(sigungu)s, NOW())
ON DUPLICATE KEY UPDATE
    name       = VALUES(name),
    address    = VALUES(address),
    lat        = VALUES(lat),
    lng        = VALUES(lng),
    sido       = VALUES(sido),
    sigungu    = VALUES(sigungu),
    updated_at = NOW()
"""

# INSERT IGNORE SQL: (store_id, round, win_rank) 중복 시 무시
_INSERT_WINNING_SQL = """
INSERT IGNORE INTO winning_history (store_id, round, win_rank, win_date)
VALUES (%(store_id)s, %(round)s, %(win_rank)s, %(win_date)s)
"""

# store_key → id 조회 SQL
_SELECT_STORE_ID_SQL = "SELECT id FROM lotto_store WHERE store_key = %(store_key)s"


@contextmanager
def _get_connection() -> Generator[pymysql.connections.Connection, None, None]:
    """DB 커넥션 컨텍스트 매니저."""
    conn = pymysql.connect(**_DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _chunked(lst: list, size: int):
    """리스트를 size 단위로 나눠 yield합니다."""
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


def load_stores(stores: list[dict]) -> int:
    """
    lotto_store 테이블에 판매점 목록을 UPSERT합니다.

    Parameters
    ----------
    stores : list[dict]
        아래 키를 포함하는 dict 목록:
        - store_key (str): 판매점 고유 ID
        - name (str): 상호명
        - address (str | None): 주소
        - lat (float | None): 위도
        - lng (float | None): 경도
        - sido (str | None): 시도
        - sigungu (str | None): 시군구

    Returns
    -------
    int
        처리된 총 레코드 수
    """
    if not stores:
        logger.info("적재할 판매점 데이터가 없습니다.")
        return 0

    # 필수 키 보정: 없는 키는 None으로 채움
    required_keys = ["store_key", "name", "address", "lat", "lng", "sido", "sigungu"]
    normalized: list[dict] = []
    for store in stores:
        row = {k: store.get(k) for k in required_keys}
        if not row["store_key"] or not row["name"]:
            logger.warning("store_key 또는 name이 없는 레코드 건너뜀: %s", store)
            continue
        normalized.append(row)

    total = 0
    with _get_connection() as conn:
        with conn.cursor() as cur:
            for batch in _chunked(normalized, _BATCH_SIZE):
                cur.executemany(_UPSERT_STORE_SQL, batch)
                total += len(batch)
                logger.debug("판매점 UPSERT 배치 완료: %d건 누적", total)

    logger.info("판매점 적재 완료: 총 %d건", total)
    return total


def load_winning(records: list[dict]) -> int:
    """
    winning_history 테이블에 당첨이력을 INSERT IGNORE합니다.
    store_key를 store_id(FK)로 자동 변환합니다.

    Parameters
    ----------
    records : list[dict]
        아래 키를 포함하는 dict 목록:
        - store_key (str): 판매점 고유 ID (자동으로 store_id로 변환)
        - round (int): 회차
        - win_rank (int): 당첨 등수 (1~5)
        - win_date (str | None): 당첨일 (YYYY-MM-DD 형식)

    Returns
    -------
    int
        삽입 시도한 총 레코드 수 (중복 제외 후 실제 삽입 수와 다를 수 있음)
    """
    if not records:
        logger.info("적재할 당첨이력 데이터가 없습니다.")
        return 0

    total = 0
    with _get_connection() as conn:
        with conn.cursor() as cur:
            # store_key → store_id 매핑 캐시
            id_cache: dict[str, int | None] = {}

            for batch in _chunked(records, _BATCH_SIZE):
                # 배치 내 고유 store_key 조회
                for rec in batch:
                    key = rec.get("store_key")
                    if key and key not in id_cache:
                        cur.execute(_SELECT_STORE_ID_SQL, {"store_key": key})
                        row = cur.fetchone()
                        id_cache[key] = row["id"] if row else None

                # store_id 치환 및 유효 레코드 필터링
                normalized = []
                for rec in batch:
                    store_id = id_cache.get(rec.get("store_key"))
                    if store_id is None:
                        logger.warning(
                            "store_key에 해당하는 판매점 없음, 건너뜀: %s",
                            rec.get("store_key"),
                        )
                        continue
                    normalized.append(
                        {
                            "store_id": store_id,
                            "round": rec.get("round"),
                            "win_rank": rec.get("win_rank"),
                            "win_date": rec.get("win_date"),
                        }
                    )

                if normalized:
                    cur.executemany(_INSERT_WINNING_SQL, normalized)
                    total += len(normalized)
                    logger.debug("당첨이력 INSERT 배치 완료: %d건 누적", total)

    logger.info("당첨이력 적재 완료: 총 %d건 시도", total)
    return total


def update_coordinates(store_key: str, lat: float, lng: float) -> bool:
    """
    특정 판매점의 좌표를 업데이트합니다.

    Parameters
    ----------
    store_key : str
        판매점 고유 ID
    lat : float
        위도
    lng : float
        경도

    Returns
    -------
    bool
        업데이트 성공 여부
    """
    sql = "UPDATE lotto_store SET lat = %(lat)s, lng = %(lng)s WHERE store_key = %(store_key)s"
    try:
        with _get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, {"store_key": store_key, "lat": lat, "lng": lng})
                return cur.rowcount > 0
    except Exception as exc:
        logger.error("좌표 업데이트 실패 (store_key=%s): %s", store_key, exc)
        return False


def fetch_null_coordinate_stores() -> list[dict]:
    """
    좌표(lat, lng)가 NULL인 판매점 목록을 조회합니다.

    Returns
    -------
    list[dict]
        store_key, address 필드를 포함하는 dict 목록
    """
    sql = "SELECT store_key, address FROM lotto_store WHERE lat IS NULL OR lng IS NULL"
    try:
        with _get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                return cur.fetchall()
    except Exception as exc:
        logger.error("NULL 좌표 판매점 조회 실패: %s", exc)
        return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")
    # 연결 테스트
    try:
        with _get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 AS ping")
                print("DB 연결 성공:", cur.fetchone())
    except Exception as e:
        print(f"DB 연결 실패: {e}")
