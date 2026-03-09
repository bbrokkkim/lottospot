"""
utils/geocode.py
주소 문자열을 위경도 좌표로 변환하는 유틸리티.

1차: 카카오 로컬 API (https://dapi.kakao.com/v2/local/search/address.json)
2차: 네이버 지오코딩 API (NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수)
변환 실패 시 None 반환, failed_geocode.log에 주소 기록.

사용 예:
    from utils.geocode import get_coords, batch_geocode
    lat, lng = get_coords("서울특별시 중구 세종대로 110") or (None, None)
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

logger = logging.getLogger(__name__)

KAKAO_API_KEY    = os.environ.get("KAKAO_API_KEY", "")
NAVER_CLIENT_ID  = os.environ.get("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "")

_KAKAO_URL  = "https://dapi.kakao.com/v2/local/search/address.json"
_NAVER_URL  = "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode"

# 요청 간 딜레이
_DELAY      = 0.1   # 일반 요청
_MAX_BACK   = 60.0  # 429 backoff 상한

# 실패 로그 경로 (crawler/ 기준)
_FAIL_LOG = Path(__file__).resolve().parent.parent.parent / "logs" / "failed_geocode.log"


def _log_failure(address: str, reason: str) -> None:
    """geocoding 실패 주소를 파일에 기록합니다."""
    _FAIL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(_FAIL_LOG, "a", encoding="utf-8") as f:
        f.write(f"{address}\t{reason}\n")


def _kakao_geocode(address: str) -> tuple[float, float] | None:
    """카카오 로컬 API로 주소를 좌표로 변환합니다."""
    if not KAKAO_API_KEY:
        return None

    headers = {
        "Authorization": f"KakaoAK {KAKAO_API_KEY}",
        "User-Agent": "LottoSpot-Crawler/1.0",
    }
    backoff = 1.0
    for attempt in range(5):
        try:
            resp = requests.get(
                _KAKAO_URL,
                headers=headers,
                params={"query": address, "size": 1},
                timeout=10,
            )
            if resp.status_code == 429:
                wait = min(backoff, _MAX_BACK)
                logger.warning("카카오 429. %.1f초 후 재시도 (%d/5)", wait, attempt + 1)
                time.sleep(wait)
                backoff *= 2
                continue
            if resp.status_code != 200:
                logger.debug("카카오 HTTP %d: %s", resp.status_code, address)
                return None

            docs = resp.json().get("documents", [])
            if not docs:
                return None

            lat = float(docs[0].get("y", 0))
            lng = float(docs[0].get("x", 0))
            if lat == 0.0 and lng == 0.0:
                return None

            time.sleep(_DELAY)
            return (lat, lng)

        except requests.exceptions.Timeout:
            logger.warning("카카오 타임아웃 (%d/5): %s", attempt + 1, address)
            time.sleep(min(backoff, _MAX_BACK))
            backoff *= 2
        except Exception as exc:
            logger.error("카카오 예외: %s / %s", exc, address)
            return None

    return None


def _naver_geocode(address: str) -> tuple[float, float] | None:
    """네이버 지오코딩 API 폴백."""
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        return None

    headers = {
        "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
        "X-NCP-APIGW-API-KEY":    NAVER_CLIENT_SECRET,
        "User-Agent": "LottoSpot-Crawler/1.0",
    }
    backoff = 1.0
    for attempt in range(3):
        try:
            resp = requests.get(
                _NAVER_URL,
                headers=headers,
                params={"query": address, "count": 1},
                timeout=10,
            )
            if resp.status_code == 429:
                wait = min(backoff, _MAX_BACK)
                logger.warning("네이버 429. %.1f초 후 재시도 (%d/3)", wait, attempt + 1)
                time.sleep(wait)
                backoff *= 2
                continue
            if resp.status_code != 200:
                logger.debug("네이버 HTTP %d: %s", resp.status_code, address)
                return None

            addresses = resp.json().get("addresses", [])
            if not addresses:
                return None

            lat = float(addresses[0].get("y", 0))
            lng = float(addresses[0].get("x", 0))
            if lat == 0.0 and lng == 0.0:
                return None

            time.sleep(_DELAY)
            return (lat, lng)

        except Exception as exc:
            logger.error("네이버 예외: %s / %s", exc, address)
            return None

    return None


def get_coords(address: str) -> tuple[float, float] | None:
    """
    주소를 (lat, lng)로 변환합니다.
    카카오 실패 시 네이버로 폴백하고, 둘 다 실패 시 None을 반환합니다.
    실패 주소는 failed_geocode.log에 기록됩니다.

    Parameters
    ----------
    address : str
        도로명주소 또는 지번주소

    Returns
    -------
    tuple[float, float] | None
        (위도, 경도) 또는 None
    """
    if not address or not address.strip():
        return None

    result = _kakao_geocode(address)
    if result:
        return result

    # 네이버 폴백
    result = _naver_geocode(address)
    if result:
        logger.debug("네이버 폴백 성공: %s", address)
        return result

    logger.warning("좌표 변환 실패: %s", address)
    _log_failure(address, "kakao+naver 모두 실패")
    return None


def batch_geocode(
    stores: list[dict],
    address_key: str = "address",
    lat_key: str = "lat",
    lng_key: str = "lng",
) -> tuple[int, int]:
    """
    좌표가 없는 판매점 목록에 대해 일괄 geocoding을 수행합니다.
    결과는 stores dict를 in-place 수정합니다.

    Parameters
    ----------
    stores : list[dict]
        판매점 dict 목록
    address_key : str
        주소 필드명
    lat_key : str
        위도 필드명
    lng_key : str
        경도 필드명

    Returns
    -------
    tuple[int, int]
        (성공 건수, 실패 건수)
    """
    targets = [s for s in stores if not s.get(lat_key) or not s.get(lng_key)]
    logger.info("geocoding 대상: %d건", len(targets))

    success = 0
    fail = 0
    for store in targets:
        address = store.get(address_key, "")
        result = get_coords(address)
        if result:
            store[lat_key] = result[0]
            store[lng_key] = result[1]
            success += 1
        else:
            store[lat_key] = None
            store[lng_key] = None
            fail += 1

    logger.info("geocoding 완료: 성공=%d / 실패=%d", success, fail)
    return success, fail
