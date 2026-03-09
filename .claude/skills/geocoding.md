---
name: geocoding
description: 카카오 로컬 API를 이용한 주소→좌표 변환 패턴. data-collector가 판매점 주소 변환 시 참조.
---

# 카카오 로컬 API — 주소→좌표 변환

## 엔드포인트
```
GET https://dapi.kakao.com/v2/local/search/address.json
```

## 요청
```python
import requests

def get_coords(address: str, api_key: str) -> tuple[float, float] | None:
    headers = {"Authorization": f"KakaoAK {api_key}"}
    params = {"query": address}
    res = requests.get(
        "https://dapi.kakao.com/v2/local/search/address.json",
        headers=headers,
        params=params
    )
    documents = res.json().get("documents", [])
    if not documents:
        return None
    doc = documents[0]
    return float(doc["y"]), float(doc["x"])  # (위도, 경도)
```

## 응답 구조
```json
{
  "documents": [{
    "address_name": "서울 중구 세종대로 110",
    "x": "126.9780",   // 경도 (lng)
    "y": "37.5665"     // 위도 (lat)
  }]
}
```
- `x` = 경도(lng), `y` = 위도(lat) — 순서 헷갈리기 쉬움

## 실패 케이스 처리
```python
def get_coords_safe(address: str, api_key: str) -> tuple[float, float] | None:
    try:
        result = get_coords(address, api_key)
        if result:
            return result
        # 도로명 실패 시 지번 주소로 재시도
        return get_coords(address.split("(")[0].strip(), api_key)
    except Exception:
        return None  # 실패한 판매점은 lat/lng = NULL로 저장
```

## Rate Limit
- 일 300,000건 (무료 기준)
- 초당 10건 권장 → `time.sleep(0.1)` 적용

## 환경변수
- `KAKAO_API_KEY` (REST API 키, 카카오 개발자 콘솔에서 발급)
- 카카오맵 SDK 키(앱 키)와 별개임 주의
