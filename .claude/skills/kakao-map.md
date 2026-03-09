---
name: kakao-map
description: 카카오맵 SDK v3 도메인 지식. 지도 초기화, 마커 생성, 현재 위치 연동 패턴. frontend-builder가 지도 관련 코드 작성 시 참조.
---

# 카카오맵 SDK v3

## 스크립트 로드
```html
<script type="text/javascript"
  src="//dapi.kakao.com/v2/maps/sdk.js?appkey=${VITE_KAKAO_MAP_KEY}&libraries=services">
</script>
```
- `libraries=services` — 주소 검색, 좌표 변환 사용 시 필요
- React에서는 `index.html`에 넣거나 동적 로드

## 지도 초기화
```js
const container = document.getElementById('map')
const options = {
  center: new kakao.maps.LatLng(37.5665, 126.9780), // 서울 기본값
  level: 5
}
const map = new kakao.maps.Map(container, options)
```

## 현재 위치 이동
```js
navigator.geolocation.getCurrentPosition(
  ({ coords }) => {
    const position = new kakao.maps.LatLng(coords.latitude, coords.longitude)
    map.setCenter(position)
  },
  () => { /* 권한 거부 시 폴백: 서울 중심 유지 */ }
)
```

## 마커 생성
```js
// 기본 마커
const marker = new kakao.maps.Marker({
  position: new kakao.maps.LatLng(lat, lng),
  map
})

// 커스텀 이미지 마커 (명당용 골드 별)
const goldImage = new kakao.maps.MarkerImage(
  '/icons/star-gold.png',
  new kakao.maps.Size(36, 36),
  { offset: new kakao.maps.Point(18, 36) }
)
const goldMarker = new kakao.maps.Marker({
  position: new kakao.maps.LatLng(lat, lng),
  image: goldImage,
  map
})
```

## 마커 클릭 이벤트
```js
kakao.maps.event.addListener(marker, 'click', () => {
  // 하단 시트 열기 등
})
```

## React에서 SDK 로드 타이밍
```js
// kakao 객체가 window에 붙기 전에 접근하면 에러
// window.kakao?.maps 로 null 체크 필수
useEffect(() => {
  if (!window.kakao?.maps) return
  // 지도 초기화
}, [])
```

## 주의사항
- `VITE_KAKAO_MAP_KEY` 환경변수 사용 (하드코딩 금지)
- 지도 컨테이너 div는 반드시 고정 높이 필요 (height: 100% 단독 사용 불가)
- SDK 로드 완료 전 `kakao.maps` 접근 시 에러 → null 체크 필수
