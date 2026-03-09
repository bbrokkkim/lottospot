import React, { useEffect, useRef, useCallback } from 'react'

// 등급별 마커 설정
const GRADE_MARKER = {
  GOLD: { color: '#FFD700', size: 36, shadow: '#FFD700' },
  SILVER: { color: '#C0C0C0', size: 28, shadow: '#C0C0C0' },
  BRONZE: { color: '#CD7F32', size: 28, shadow: '#CD7F32' },
  NORMAL: { color: '#9E9E9E', size: 22, shadow: '#9E9E9E' },
}

/**
 * SVG 핀 마커 생성 (이미지 파일 없이 인라인 SVG)
 */
function createMarkerSVG(grade) {
  const cfg = GRADE_MARKER[grade] || GRADE_MARKER.NORMAL
  const size = cfg.size
  const isSpecial = grade === 'GOLD' || grade === 'SILVER' || grade === 'BRONZE'
  const pinHeight = Math.round(size * 1.3)

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${pinHeight}" viewBox="0 0 ${size} ${pinHeight}">
    <defs>
      <filter id="shadow-${grade}" x="-20%" y="-20%" width="140%" height="140%">
        <feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="${cfg.shadow}" flood-opacity="0.5"/>
      </filter>
    </defs>
    <!-- 핀 몸체 -->
    <path
      d="M${size / 2} 1
         C${size * 0.15} 1, 1 ${size * 0.35}, 1 ${size * 0.5}
         C1 ${size * 0.78}, ${size * 0.3} ${size * 0.9}, ${size / 2} ${pinHeight - 1}
         C${size * 0.7} ${size * 0.9}, ${size - 1} ${size * 0.78}, ${size - 1} ${size * 0.5}
         C${size - 1} ${size * 0.35}, ${size * 0.85} 1, ${size / 2} 1Z"
      fill="${cfg.color}"
      filter="url(#shadow-${grade})"
    />
    <!-- 내부 아이콘 -->
    ${isSpecial
      ? `<text x="${size / 2}" y="${size * 0.58}" text-anchor="middle" dominant-baseline="middle" font-size="${size * 0.38}" fill="${grade === 'GOLD' ? '#1A1100' : '#1A1A1A'}">★</text>`
      : `<circle cx="${size / 2}" cy="${size * 0.48}" r="${size * 0.18}" fill="white" opacity="0.5"/>`
    }
  </svg>`

  return svg
}

/**
 * 내 위치 마커 (파란 원형 + 펄스 애니메이션)
 */
function createMyLocationSVG() {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40">
    <defs>
      <radialGradient id="myPulse">
        <stop offset="0%" stop-color="#4A9EFF" stop-opacity="0.4"/>
        <stop offset="100%" stop-color="#4A9EFF" stop-opacity="0"/>
      </radialGradient>
    </defs>
    <circle cx="20" cy="20" r="18" fill="url(#myPulse)"/>
    <circle cx="20" cy="20" r="8" fill="#4A9EFF" stroke="white" stroke-width="2.5"/>
  </svg>`
}

/**
 * SVG 문자열 -> 카카오맵 MarkerImage
 */
function svgToMarkerImage(kakao, svgStr, width, height, offsetX, offsetY) {
  const encoded = encodeURIComponent(svgStr)
  const dataUrl = `data:image/svg+xml;charset=utf-8,${encoded}`
  const size = new kakao.maps.Size(width, height)
  const offset = new kakao.maps.Point(offsetX, offsetY)
  return new kakao.maps.MarkerImage(dataUrl, size, { offset })
}

const mapContainerStyle = {
  width: '100%',
  height: '100%',
  position: 'relative',
}

const currentLocationBtnStyle = {
  position: 'absolute',
  right: 16,
  bottom: 16,
  width: 44,
  height: 44,
  borderRadius: '50%',
  background: '#132337',
  border: '1px solid #243448',
  color: '#4A9EFF',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
  boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
  zIndex: 10,
  transition: 'background 0.15s',
}

function LocationIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 1v4M12 19v4M1 12h4M19 12h4" />
    </svg>
  )
}

export function KakaoMap({ center, stores, selectedStoreId, onSelectStore, onMoveEnd }) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const markersRef = useRef([])
  const myMarkerRef = useRef(null)
  const isInitializedRef = useRef(false)

  // 카카오맵 초기화
  useEffect(() => {
    if (!containerRef.current || isInitializedRef.current) return

    const appKey = window.__KAKAO_APP_KEY__
    if (!appKey || appKey === '%VITE_KAKAO_MAP_KEY%') {
      console.error('[KakaoMap] KAKAO_APP_KEY 가 설정되지 않았습니다.')
      return
    }

    const initMap = () => {
      const kakao = window.kakao
      kakao.maps.load(() => {
        const options = {
          center: new kakao.maps.LatLng(center.lat, center.lng),
          level: 5,
        }
        const map = new kakao.maps.Map(containerRef.current, options)
        mapRef.current = map
        isInitializedRef.current = true

        kakao.maps.event.addListener(map, 'idle', () => {
          const c = map.getCenter()
          onMoveEnd?.({ lat: c.getLat(), lng: c.getLng() })
        })
      })
    }

    if (window.kakao?.maps) {
      initMap()
      return
    }

    const script = document.createElement('script')
    script.src = `//dapi.kakao.com/v2/maps/sdk.js?appkey=${appKey}&libraries=clusterer&autoload=false`
    script.onload = initMap
    script.onerror = () => console.error('[KakaoMap] 카카오맵 SDK 로드 실패')
    document.head.appendChild(script)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // 중심 좌표 변경 시 지도 이동
  useEffect(() => {
    const map = mapRef.current
    if (!map || !center) return
    const kakao = window.kakao
    const latLng = new kakao.maps.LatLng(center.lat, center.lng)
    map.setCenter(latLng)
  }, [center])

  // 내 위치 마커 갱신
  useEffect(() => {
    const map = mapRef.current
    const kakao = window.kakao
    if (!map || !kakao?.maps || !center) return

    if (myMarkerRef.current) {
      myMarkerRef.current.setMap(null)
    }

    kakao.maps.load(() => {
      const svg = createMyLocationSVG()
      const image = svgToMarkerImage(kakao, svg, 40, 40, 20, 20)
      const marker = new kakao.maps.Marker({
        map,
        position: new kakao.maps.LatLng(center.lat, center.lng),
        image,
        zIndex: 5,
        title: '내 위치',
      })
      myMarkerRef.current = marker
    })
  }, [center])

  // 판매점 마커 갱신
  useEffect(() => {
    const map = mapRef.current
    const kakao = window.kakao
    if (!map || !kakao?.maps) return

    kakao.maps.load(() => {
      // 기존 마커 제거
      markersRef.current.forEach((m) => m.setMap(null))
      markersRef.current = []

      stores.forEach((store) => {
        const grade = store.grade || 'NORMAL'
        const cfg = GRADE_MARKER[grade] || GRADE_MARKER.NORMAL
        const size = cfg.size
        const pinHeight = Math.round(size * 1.3)

        const svg = createMarkerSVG(grade)
        const image = svgToMarkerImage(kakao, svg, size, pinHeight, size / 2, pinHeight)

        const marker = new kakao.maps.Marker({
          map,
          position: new kakao.maps.LatLng(store.lat, store.lng),
          image,
          title: store.name,
          zIndex: grade === 'GOLD' ? 4 : grade === 'SILVER' ? 3 : grade === 'BRONZE' ? 2 : 1,
        })

        kakao.maps.event.addListener(marker, 'click', () => {
          onSelectStore?.(store)
        })

        markersRef.current.push(marker)
      })
    })
  }, [stores, onSelectStore])

  // 선택된 마커 강조 (스케일 업) - 간단히 구현
  useEffect(() => {
    // 선택 강조는 바텀시트로 처리하므로 별도 마커 조작 없음
  }, [selectedStoreId])

  const handleCurrentLocation = useCallback(() => {
    if (!navigator.geolocation || !mapRef.current) return
    const kakao = window.kakao
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const latLng = new kakao.maps.LatLng(pos.coords.latitude, pos.coords.longitude)
        mapRef.current.setCenter(latLng)
        mapRef.current.setLevel(4)
      },
      () => {
        // 권한 거부 등 무시
      },
    )
  }, [])

  return (
    <div style={mapContainerStyle}>
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
      <button
        style={currentLocationBtnStyle}
        onClick={handleCurrentLocation}
        aria-label="현재 위치로 이동"
        title="현재 위치"
      >
        <LocationIcon />
      </button>
    </div>
  )
}
