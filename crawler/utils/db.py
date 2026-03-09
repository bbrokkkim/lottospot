"""
utils/db.py
MySQL 연결 및 Store / WinHistory UPSERT 유틸리티.

사용 예:
    from utils.db import upsert_stores, insert_win_history, get_connection
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Generator

import pymysql
import pymysql.cursors
from dotenv import load_dotenv

# .env는 crawler/ 디렉토리 기준
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

logger = logging.getLogger(__name__)

_DB_CONFIG: dict = {
    "host":     os.environ.get("DB_HOST", "localhost"),
    "port":     int(os.environ.get("DB_PORT", 3306)),
    "user":     os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASS", ""),
    "db":       os.environ.get("DB_NAME", "lottospot"),
    "charset":  "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": False,
}

_BATCH_SIZE = 200

# -------------------------------------------------------
# Store UPSERT
# store_key = 동행복권 내부 ID (UNIQUE KEY)
# -------------------------------------------------------
_SQL_UPSERT_STORE = """
INSERT INTO store
    (store_key, name, address, address_detail, lat, lng, phone, is_open,
     created_at, updated_at)
VALUES
    (%(store_key)s, %(name)s, %(address)s, %(address_detail)s,
     %(lat)s, %(lng)s, %(phone)s, %(is_open)s,
     NOW(), NOW())
ON DUPLICATE KEY UPDATE
    name           = VALUES(name),
    address        = VALUES(address),
    address_detail = VALUES(address_detail),
    lat            = COALESCE(VALUES(lat), lat),
    lng            = COALESCE(VALUES(lng), lng),
    phone          = VALUES(phone),
    is_open        = VALUES(is_open),
    updated_at     = NOW()
"""

# WinHistory INSERT IGNORE
# UNIQUE KEY: (store_id, round, rank)
_SQL_INSERT_WIN = """
INSERT IGNORE INTO win_history (store_id, round, rank, win_date)
SELECT s.id, %(round)s, %(rank)s, %(win_date)s
FROM   store s
WHERE  s.store_key = %(store_key)s
LIMIT  1
"""

# store_key -> store.id 조회
_SQL_GET_STORE_ID = "SELECT id FROM store WHERE store_key = %(store_key)s LIMIT 1"

# 좌표 NULL 판매점 조회
_SQL_NULL_COORD = "SELECT store_key, address FROM store WHERE lat IS NULL OR lng IS NULL"

# 좌표 UPDATE
_SQL_UPDATE_COORD = """
UPDATE store SET lat = %(lat)s, lng = %(lng)s, updated_at = NOW()
WHERE  store_key = %(store_key)s
"""


@contextmanager
def get_connection() -> Generator[pymysql.connections.Connection, None, None]:
    """DB 커넥션 컨텍스트 매니저 (예외 시 rollback)."""
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
    for i in range(0, len(lst), size):
        yield lst[i: i + size]


def upsert_stores(stores: list[dict]) -> int:
    """
    Store 테이블에 판매점 목록을 UPSERT합니다.

    Parameters
    ----------
    stores : list[dict]
        필수 키: store_key, name
        선택 키: address, address_detail, lat, lng, phone, is_open

    Returns
    -------
    int
        처리한 레코드 수
    """
    if not stores:
        return 0

    required = ["store_key", "name", "address", "address_detail",
                "lat", "lng", "phone", "is_open"]
    rows = []
    for s in stores:
        if not s.get("store_key") or not s.get("name"):
            logger.warning("store_key/name 누락, 건너뜀: %s", s)
            continue
        rows.append({k: s.get(k) for k in required})

    total = 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            for batch in _chunked(rows, _BATCH_SIZE):
                cur.executemany(_SQL_UPSERT_STORE, batch)
                total += len(batch)

    logger.info("Store UPSERT 완료: %d건", total)
    return total


def insert_win_history(records: list[dict]) -> int:
    """
    WinHistory 테이블에 당첨 이력을 INSERT IGNORE합니다.

    Parameters
    ----------
    records : list[dict]
        필수 키: store_key, round, rank
        선택 키: win_date (YYYY-MM-DD)

    Returns
    -------
    int
        삽입 시도한 레코드 수
    """
    if not records:
        return 0

    total = 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            for batch in _chunked(records, _BATCH_SIZE):
                cur.executemany(_SQL_INSERT_WIN, batch)
                total += len(batch)

    logger.info("WinHistory INSERT 완료: %d건 시도", total)
    return total


def fetch_null_coord_stores() -> list[dict]:
    """좌표가 NULL인 판매점의 store_key, address 목록을 반환합니다."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(_SQL_NULL_COORD)
                return list(cur.fetchall())
    except Exception as exc:
        logger.error("NULL 좌표 조회 실패: %s", exc)
        return []


def update_coord(store_key: str, lat: float, lng: float) -> bool:
    """특정 판매점의 좌표를 업데이트합니다."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(_SQL_UPDATE_COORD,
                            {"store_key": store_key, "lat": lat, "lng": lng})
                return cur.rowcount > 0
    except Exception as exc:
        logger.error("좌표 업데이트 실패 (store_key=%s): %s", store_key, exc)
        return False
