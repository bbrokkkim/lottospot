import React, { useState, useCallback, useEffect, useRef } from 'react'
import { KakaoMap } from '../components/map/KakaoMap'
import { StoreBottomSheet } from '../components/map/StoreBottomSheet'
import { StoreListPanel } from '../components/map/StoreListPanel'
import { RadiusFilter } from '../components/map/RadiusFilter'
import { SearchBar } from '../components/map/SearchBar'
import { ToastProvider, showToast } from '../components/common/Toast'
import { useGeolocation } from '../hooks/useGeolocation'
import { useNearbyStores } from '../hooks/useNearbyStores'

// 판매점 목록 패널 높이 상태
const PANEL_HEIGHT = {
  COLLAPSED: 56,        // 탭바만 보임 (거리순|명당순 탭)
  HALF: 260,            // 절반
  FULL: '60vh',         // 전체
}

const styles = {
  root: {
    position: 'fixed',
    inset: 0,
    display: 'flex',
    flexDirection: 'column',
    background: '#0D1B2A',
    overflow: 'hidden',
  },
  appBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '12px 16px',
    paddingTop: 'max(12px, env(safe-area-inset-top))',
    background: '#0D1B2A',
    borderBottom: '1px solid #243448',
    flexShrink: 0,
    zIndex: 10,
  },
  appBarTitle: {
    fontSize: 18,
    fontWeight: 800,
    color: '#F0F4F8',
    letterSpacing: '-0.3px',
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  goldDot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    background: '#FFD700',
    boxShadow: '0 0 8px #FFD700',
    display: 'inline-block',
  },
  searchWrapper: {
    padding: '8px 16px',
    background: '#0D1B2A',
    borderBottom: '1px solid #243448',
    flexShrink: 0,
    zIndex: 10,
  },
  mapArea: {
    flex: 1,
    position: 'relative',
    minHeight: 0,
  },
  bottomArea: {
    flexShrink: 0,
    display: 'flex',
    flexDirection: 'column',
    background: '#132337',
    zIndex: 20,
  },
  listPanelWrapper: (height) => ({
    height: typeof height === 'string' ? height : `${height}px`,
    overflow: 'hidden',
    transition: 'height 0.3s cubic-bezier(0.32, 0.72, 0, 1)',
    display: 'flex',
    flexDirection: 'column',
  }),
  swipeHandle: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    padding: '8px 0 4px',
    cursor: 'pointer',
    flexShrink: 0,
    background: '#132337',
  },
  swipeHandleBar: {
    width: 36,
    height: 4,
    borderRadius: 2,
    background: '#243448',
  },
  locationBanner: {
    position: 'absolute',
    top: 8,
    left: '50%',
    transform: 'translateX(-50%)',
    zIndex: 50,
    background: 'rgba(13, 27, 42, 0.92)',
    border: '1px solid #243448',
    borderRadius: 20,
    padding: '6px 14px',
    fontSize: 12,
    color: '#8FA3B8',
    backdropFilter: 'blur(8px)',
    whiteSpace: 'nowrap',
    pointerEvents: 'none',
  },
  mapOverlayInfo: {
    position: 'absolute',
    top: 8,
    left: 16,
    zIndex: 50,
    display: 'flex',
    gap: 6,
    pointerEvents: 'none',
  },
  legendPill: (color) => ({
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    padding: '4px 8px',
    borderRadius: 12,
    background: 'rgba(13,27,42,0.85)',
    border: '1px solid #243448',
    backdropFilter: 'blur(8px)',
    fontSize: 11,
    color: '#F0F4F8',
    fontWeight: 500,
  }),
  legendDot: (color) => ({
    width: 8,
    height: 8,
    borderRadius: '50%',
    background: color,
    boxShadow: `0 0 4px ${color}`,
  }),
}

// 패널 높이 순환
const PANEL_STATES = ['COLLAPSED', 'HALF', 'FULL']

export default function MapPage() {
  const { position, isLoading: geoLoading, error: geoError, isDefault } = useGeolocation()
  const [mapCenter, setMapCenter] = useState(null)
  const [radius, setRadius] = useState(1000)
  const [sort, setSort] = useState('distance')
  const [selectedStore, setSelectedStore] = useState(null)
  const [panelState, setPanelState] = useState('HALF')

  // GPS 위치가 확정되면 지도 중심으로 설정
  useEffect(() => {
    if (position && !mapCenter) {
      setMapCenter(position)
    }
  }, [position, mapCenter])

  // GPS 오류 토스트
  useEffect(() => {
    if (geoError) {
      showToast(geoError, 'info')
    }
  }, [geoError])

  const { stores, totalCount, isLoading: storesLoading, error: storesError } = useNearbyStores({
    lat: mapCenter?.lat,
    lng: mapCenter?.lng,
    radius,
    sort,
    limit: 50,
  })

  // API 오류 토스트
  useEffect(() => {
    if (storesError) {
      showToast(storesError, 'error')
    }
  }, [storesError])

  const handleMapMoveEnd = useCallback((center) => {
    setMapCenter(center)
  }, [])

  const handleSelectStore = useCallback((store) => {
    setSelectedStore(store)
  }, [])

  const handleCloseBottomSheet = useCallback(() => {
    setSelectedStore(null)
  }, [])

  const handlePanelToggle = useCallback(() => {
    setPanelState((prev) => {
      const idx = PANEL_STATES.indexOf(prev)
      return PANEL_STATES[(idx + 1) % PANEL_STATES.length]
    })
  }, [])

  const getPanelHeight = () => {
    if (panelState === 'COLLAPSED') return PANEL_HEIGHT.COLLAPSED
    if (panelState === 'HALF') return PANEL_HEIGHT.HALF
    return PANEL_HEIGHT.FULL
  }

  // 스와이프 제스처 (터치)
  const touchStartY = useRef(null)
  const handleTouchStart = useCallback((e) => {
    touchStartY.current = e.touches[0].clientY
  }, [])
  const handleTouchEnd = useCallback((e) => {
    if (touchStartY.current == null) return
    const diff = touchStartY.current - e.changedTouches[0].clientY
    if (Math.abs(diff) < 30) return
    setPanelState((prev) => {
      const idx = PANEL_STATES.indexOf(prev)
      if (diff > 0) {
        // 위로 스와이프 -> 패널 확장
        return PANEL_STATES[Math.min(idx + 1, PANEL_STATES.length - 1)]
      } else {
        // 아래로 스와이프 -> 패널 축소
        return PANEL_STATES[Math.max(idx - 1, 0)]
      }
    })
    touchStartY.current = null
  }, [])

  if (geoLoading && !mapCenter) {
    return (
      <div style={{ ...styles.root, alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: '#8FA3B8', fontSize: 14, textAlign: 'center', lineHeight: 2 }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>📍</div>
          위치를 확인하는 중입니다...
        </div>
      </div>
    )
  }

  return (
    <div style={styles.root}>
      <ToastProvider />

      {/* 앱바 */}
      <header style={styles.appBar}>
        <div style={styles.appBarTitle}>
          <span style={styles.goldDot} />
          내 주변 명당
        </div>
        <div style={{ fontSize: 12, color: '#8FA3B8' }}>
          {isDefault ? '서울 기본 위치' : '내 위치'}
        </div>
      </header>

      {/* 검색바 */}
      <div style={styles.searchWrapper}>
        <SearchBar onSearch={(q) => showToast(`"${q}" 검색은 준비 중입니다.`)} />
      </div>

      {/* 지도 영역 */}
      <main style={styles.mapArea}>
        {mapCenter && (
          <KakaoMap
            center={mapCenter}
            stores={stores}
            selectedStoreId={selectedStore?.id}
            onSelectStore={handleSelectStore}
            onMoveEnd={handleMapMoveEnd}
          />
        )}

        {/* 지도 위 범례 */}
        <div style={styles.mapOverlayInfo}>
          {[
            { label: '금', color: '#FFD700' },
            { label: '은', color: '#C0C0C0' },
            { label: '동', color: '#CD7F32' },
          ].map(({ label, color }) => (
            <div key={label} style={styles.legendPill(color)}>
              <span style={styles.legendDot(color)} />
              {label}
            </div>
          ))}
        </div>
      </main>

      {/* 하단 패널 */}
      <div style={styles.bottomArea}>
        {/* 반경 필터 */}
        <RadiusFilter radius={radius} onChange={setRadius} />

        {/* 스와이프 핸들 */}
        <div
          style={styles.swipeHandle}
          onClick={handlePanelToggle}
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
          role="button"
          aria-label="목록 패널 높이 조절"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && handlePanelToggle()}
        >
          <div style={styles.swipeHandleBar} />
        </div>

        {/* 판매점 목록 */}
        <div style={styles.listPanelWrapper(getPanelHeight())}>
          <StoreListPanel
            stores={stores}
            totalCount={totalCount}
            isLoading={storesLoading}
            sort={sort}
            onSortChange={setSort}
            selectedId={selectedStore?.id}
            onSelectStore={handleSelectStore}
          />
        </div>
      </div>

      {/* 판매점 상세 바텀시트 */}
      {selectedStore && (
        <StoreBottomSheet
          store={selectedStore}
          onClose={handleCloseBottomSheet}
        />
      )}
    </div>
  )
}
