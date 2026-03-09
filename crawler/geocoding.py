"""
geocoding.py
주소 문자열을 (lat, lng) 좌표로 변환하는 모듈.
카카오 로컬 API를 사용하며, 실패 시 None을 반환합니다.
"""

from __future__ import annotations

import logging
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

KAKAO_API_KEY = os.environ.get("KAKAO_API_KEY", "")
KAKAO_ADDRESS_URL = "https://dapi.kakao.com/v2/local/search/address.json"

# 요청 간 기본 딜레이 (초)
_DEFAULT_DELAY = 0.1
# 429 에러 시 exponential backoff 최대 대기 시간 (초)
_MAX_BACKOFF = 60.0


def _build_headers() -> dict[str, str]:
    return {
        "Authorization": f"KakaoAK {KAKAO_API_KEY}",
        "User-Agent": "LottoSpot-Crawler/1.0",
    }


def get_coordinates(address: str) -> tuple[float, float] | None:
    """
    주소 문자열을 (lat, lng) 튜플로 변환합니다.

    Parameters
    ----------
    address : str
        도로명주소 또는 지번주소 문자열

    Returns
    -------
    tuple[float, float] | None
        (위도, 경도) 튜플. 변환 실패 시 None 반환.
    """
    if not address or not address.strip():
        return None

    if not KAKAO_API_KEY:
        logger.warning("KAKAO_API_KEY 환경변수가 설정되지 않았습니다.")
        return None

    backoff = 1.0
    max_retries = 5

    for attempt in range(max_retries):
        try:
            response = requests.get(
                KAKAO_ADDRESS_URL,
                headers=_build_headers(),
                params={"query": address, "size": 1},
                timeout=10,
            )

            if response.status_code == 429:
                wait = min(backoff, _MAX_BACKOFF)
                logger.warning(
                    "카카오 API 429 Too Many Requests. %.1f초 후 재시도 (시도 %d/%d)",
                    wait,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(wait)
                backoff *= 2
                continue

            if response.status_code != 200:
                logger.error(
                    "카카오 API 오류: HTTP %d / 주소: %s",
                    response.status_code,
                    address,
                )
                return None

            data = response.json()
            documents = data.get("documents", [])
            if not documents:
                logger.debug("좌표 변환 결과 없음: %s", address)
                return None

            doc = documents[0]
            lat = float(doc.get("y", 0))
            lng = float(doc.get("x", 0))

            if lat == 0.0 and lng == 0.0:
                logger.debug("좌표 값이 0,0 입니다: %s", address)
                return None

            time.sleep(_DEFAULT_DELAY)
            return (lat, lng)

        except requests.exceptions.Timeout:
            logger.warning("카카오 API 타임아웃: %s (시도 %d/%d)", address, attempt + 1, max_retries)
            time.sleep(min(backoff, _MAX_BACKOFF))
            backoff *= 2

        except requests.exceptions.RequestException as exc:
            logger.error("카카오 API 요청 예외: %s / 주소: %s", exc, address)
            return None

        except (KeyError, ValueError, TypeError) as exc:
            logger.error("카카오 API 응답 파싱 오류: %s / 주소: %s", exc, address)
            return None

    logger.error("카카오 API 최대 재시도 초과: %s", address)
    return None


def batch_geocode(
    stores: list[dict],
    address_key: str = "address",
    lat_key: str = "lat",
    lng_key: str = "lng",
) -> list[dict]:
    """
    좌표가 없는 판매점 목록에 대해 일괄 geocoding을 수행합니다.

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
    list[dict]
        좌표가 채워진 판매점 목록 (in-place 수정 후 반환)
    """
    targets = [s for s in stores if not s.get(lat_key) or not s.get(lng_key)]
    logger.info("geocoding 대상: %d건", len(targets))

    success = 0
    for store in targets:
        address = store.get(address_key, "")
        result = get_coordinates(address)
        if result:
            store[lat_key] = result[0]
            store[lng_key] = result[1]
            success += 1
        else:
            store[lat_key] = None
            store[lng_key] = None

    logger.info("geocoding 완료: %d/%d건 성공", success, len(targets))
    return stores


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")
    test_address = "서울특별시 중구 세종대로 110"
    result = get_coordinates(test_address)
    print(f"주소: {test_address}")
    print(f"좌표: {result}")
