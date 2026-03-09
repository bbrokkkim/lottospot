import React, { useEffect, useRef, useState, useCallback } from 'react'
import { GradeBadge } from '../common/GradeBadge'
import { useStoreDetail } from '../../hooks/useStoreDetail'

const GRADE_LABEL = {
  GOLD: '명당 1등급',
  SILVER: '명당 2등급',
  BRONZE: '명당 3등급',
  NORMAL: '일반 판매점',
}

const GRADE_COLOR = {
  GOLD: '#FFD700',
  SILVER: '#C0C0C0',
  BRONZE: '#CD7F32',
  NORMAL: '#9E9E9E',
}

const RANK_LABEL = { 1: '1등', 2: '2등', 3: '3등' }

function formatDistance(meters) {
  if (meters == null) return ''
  if (meters < 1000) return `${Math.round(meters)}m`
  return `${(meters / 1000).toFixed(1)}km`
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return dateStr.replace(/-/g, '.')
}

function CloseIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}

function DirectionIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="3 11 22 2 13 21 11 13 3 11" />
    </svg>
  )
}

const styles = {
  overlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0,0,0,0.5)',
    zIndex: 400,
    backdropFilter: 'blur(2px)',
  },
  sheet: (visible) => ({
    position: 'fixed',
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 500,
    background: '#132337',
    borderRadius: '20px 20px 0 0',
    maxHeight: '80vh',
    overflowY: 'auto',
    transform: visible ? 'translateY(0)' : 'translateY(100%)',
    transition: 'transform 0.35s cubic-bezier(0.32, 0.72, 0, 1)',
    boxShadow: '0 -8px 32px rgba(0,0,0,0.5)',
  }),
  handle: {
    display: 'flex',
    justifyContent: 'center',
    paddingTop: 12,
    paddingBottom: 8,
    cursor: 'grab',
  },
  handleBar: {
    width: 36,
    height: 4,
    borderRadius: 2,
    background: '#243448',
  },
  headerRow: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    padding: '0 16px 16px',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    flex: 1,
    minWidth: 0,
  },
  nameBlock: {
    flex: 1,
    minWidth: 0,
  },
  name: {
    fontSize: 18,
    fontWeight: 700,
    color: '#F0F4F8',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  address: {
    fontSize: 12,
    color: '#8FA3B8',
    marginTop: 4,
    lineHeight: 1.4,
  },
  distance: {
    fontSize: 12,
    color: '#4A9EFF',
    marginTop: 2,
    fontFamily: 'DM Mono, monospace',
  },
  closeBtn: {
    color: '#8FA3B8',
    padding: 8,
    borderRadius: '50%',
    background: '#1A2E45',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  divider: {
    height: 1,
    background: '#243448',
    margin: '0 16px',
  },
  scoreSection: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '14px 16px',
  },
  scoreLabel: {
    fontSize: 13,
    color: '#8FA3B8',
    fontWeight: 500,
  },
  scoreRight: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
  },
  scoreValue: (grade) => ({
    fontSize: 28,
    fontWeight: 800,
    color: GRADE_COLOR[grade] || '#F0F4F8',
    fontFamily: 'DM Mono, monospace',
    lineHeight: 1,
  }),
  gradePill: (grade) => ({
    padding: '4px 10px',
    borderRadius: 20,
    fontSize: 12,
    fontWeight: 600,
    color: GRADE_COLOR[grade] || '#F0F4F8',
    background: `${GRADE_COLOR[grade] || '#9E9E9E'}22`,
    border: `1px solid ${GRADE_COLOR[grade] || '#9E9E9E'}44`,
  }),
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 1,
    background: '#243448',
    margin: '0 16px',
    borderRadius: 12,
    overflow: 'hidden',
  },
  statCell: {
    background: '#1A2E45',
    padding: '14px 16px',
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  statLabel: {
    fontSize: 11,
    color: '#8FA3B8',
    fontWeight: 500,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  statValue: {
    fontSize: 22,
    fontWeight: 700,
    color: '#F0F4F8',
    fontFamily: 'DM Mono, monospace',
    lineHeight: 1,
  },
  statUnit: {
    fontSize: 12,
    color: '#8FA3B8',
    marginLeft: 2,
    fontWeight: 400,
  },
  infoSection: {
    padding: '14px 16px',
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
  },
  infoRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  infoLabel: {
    fontSize: 13,
    color: '#8FA3B8',
    fontWeight: 500,
  },
  infoValue: {
    fontSize: 13,
    color: '#F0F4F8',
    fontWeight: 500,
    textAlign: 'right',
    fontFamily: 'DM Mono, monospace',
  },
  openBadge: (isOpen) => ({
    padding: '3px 10px',
    borderRadius: 12,
    fontSize: 12,
    fontWeight: 600,
    color: isOpen ? '#22C55E' : '#EF4444',
    background: isOpen ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
  }),
  historySection: {
    padding: '0 16px 8px',
  },
  historyTitle: {
    fontSize: 12,
    color: '#8FA3B8',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginBottom: 8,
  },
  historyItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '8px 0',
    borderBottom: '1px solid #1A2E45',
  },
  historyRound: {
    fontSize: 13,
    color: '#F0F4F8',
    fontFamily: 'DM Mono, monospace',
    fontWeight: 500,
  },
  historyRank: (rank) => ({
    padding: '2px 8px',
    borderRadius: 10,
    fontSize: 11,
    fontWeight: 700,
    color: rank === 1 ? '#0D1B2A' : '#F0F4F8',
    background: rank === 1 ? '#FFD700' : rank === 2 ? '#C0C0C0' : '#CD7F32',
  }),
  historyDate: {
    fontSize: 12,
    color: '#8FA3B8',
    fontFamily: 'DM Mono, monospace',
  },
  footer: {
    padding: '16px',
    paddingBottom: 'max(16px, env(safe-area-inset-bottom))',
  },
  directionBtn: {
    width: '100%',
    height: 48,
    borderRadius: 12,
    background: 'linear-gradient(135deg, #FFD700, #FFA500)',
    color: '#0D1B2A',
    fontSize: 15,
    fontWeight: 700,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    cursor: 'pointer',
    border: 'none',
    boxShadow: '0 4px 16px rgba(255,215,0,0.3)',
    transition: 'opacity 0.15s',
  },
  skeletonLine: (w) => ({
    height: 14,
    width: w || '100%',
    borderRadius: 7,
    background: 'linear-gradient(90deg, #1A2E45 25%, #243448 50%, #1A2E45 75%)',
    backgroundSize: '200% 100%',
    animation: 'shimmer 1.5s infinite',
  }),
}

function SkeletonLoader() {
  return (
    <>
      <style>{`@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }`}</style>
      <div style={{ padding: '0 16px 20px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={styles.skeletonLine('60%')} />
        <div style={styles.skeletonLine('40%')} />
        <div style={{ height: 1, background: '#243448', margin: '4px 0' }} />
        <div style={styles.skeletonLine('80%')} />
        <div style={styles.skeletonLine('50%')} />
      </div>
    </>
  )
}

export function StoreBottomSheet({ store: previewStore, onClose }) {
  const [visible, setVisible] = useState(false)
  const { store: detailStore, isLoading } = useStoreDetail(previewStore?.id ?? null)

  // 상세 데이터 있으면 사용, 없으면 미리보기(목록) 데이터 사용
  const store = detailStore || previewStore

  useEffect(() => {
    if (previewStore) {
      const id = requestAnimationFrame(() => setVisible(true))
      return () => cancelAnimationFrame(id)
    } else {
      setVisible(false)
    }
  }, [previewStore])

  const handleClose = useCallback(() => {
    setVisible(false)
    setTimeout(onClose, 350)
  }, [onClose])

  const handleDirections = useCallback(() => {
    if (!store) return
    const url = `https://map.kakao.com/link/to/${encodeURIComponent(store.name)},${store.lat},${store.lng}`
    window.open(url, '_blank', 'noopener,noreferrer')
  }, [store])

  if (!previewStore) return null

  return (
    <>
      <div style={styles.overlay} onClick={handleClose} aria-hidden="true" />
      <div
        style={styles.sheet(visible)}
        role="dialog"
        aria-label={`${store?.name || ''} 상세 정보`}
        aria-modal="true"
      >
        {/* 드래그 핸들 */}
        <div style={styles.handle} onClick={handleClose}>
          <div style={styles.handleBar} />
        </div>

        {/* 헤더 */}
        <div style={styles.headerRow}>
          <div style={styles.headerLeft}>
            {store && <GradeBadge grade={store.grade} size="lg" />}
            <div style={styles.nameBlock}>
              <div style={styles.name}>{store?.name || '...'}</div>
              <div style={styles.address}>{store?.address || ''}</div>
              {store?.distance != null && (
                <div style={styles.distance}>현재 위치에서 {formatDistance(store.distance)}</div>
              )}
            </div>
          </div>
          <button style={styles.closeBtn} onClick={handleClose} aria-label="닫기">
            <CloseIcon />
          </button>
        </div>

        {isLoading && !detailStore ? (
          <SkeletonLoader />
        ) : (
          <>
            {/* 명당 스코어 */}
            <div style={styles.divider} />
            <div style={styles.scoreSection}>
              <span style={styles.scoreLabel}>명당 스코어</span>
              <div style={styles.scoreRight}>
                <span style={styles.scoreValue(store?.grade)}>{store?.score ?? '-'}</span>
                <span style={{ ...styles.scoreValue(store?.grade), fontSize: 14 }}>점</span>
                {store?.grade && (
                  <span style={styles.gradePill(store.grade)}>
                    {GRADE_LABEL[store.grade]}
                  </span>
                )}
              </div>
            </div>

            {/* 당첨 통계 */}
            <div style={styles.divider} />
            <div style={{ padding: '14px 16px' }}>
              <div style={styles.statsGrid}>
                <div style={styles.statCell}>
                  <span style={styles.statLabel}>1등 당첨</span>
                  <span style={styles.statValue}>
                    {store?.firstWinCount ?? 0}
                    <span style={styles.statUnit}>회</span>
                  </span>
                </div>
                <div style={styles.statCell}>
                  <span style={styles.statLabel}>2등 당첨</span>
                  <span style={styles.statValue}>
                    {store?.secondWinCount ?? 0}
                    <span style={styles.statUnit}>회</span>
                  </span>
                </div>
              </div>
            </div>

            {/* 기타 정보 */}
            <div style={styles.divider} />
            <div style={styles.infoSection}>
              {store?.recentWinRound != null && (
                <div style={styles.infoRow}>
                  <span style={styles.infoLabel}>최근 당첨</span>
                  <span style={styles.infoValue}>
                    {store.recentWinRound}회
                    {store.recentWinDate ? ` (${formatDate(store.recentWinDate)})` : ''}
                  </span>
                </div>
              )}
              {store?.phone && (
                <div style={styles.infoRow}>
                  <span style={styles.infoLabel}>전화번호</span>
                  <a
                    href={`tel:${store.phone}`}
                    style={{ ...styles.infoValue, color: '#4A9EFF', textDecoration: 'none' }}
                  >
                    {store.phone}
                  </a>
                </div>
              )}
              <div style={styles.infoRow}>
                <span style={styles.infoLabel}>영업 상태</span>
                {store?.isOpen != null ? (
                  <span style={styles.openBadge(store.isOpen)}>
                    {store.isOpen ? '운영 중' : '영업 종료'}
                  </span>
                ) : (
                  <span style={{ ...styles.infoValue, color: '#8FA3B8' }}>정보 없음</span>
                )}
              </div>
            </div>

            {/* 최근 당첨 이력 */}
            {detailStore?.winHistory?.length > 0 && (
              <>
                <div style={styles.divider} />
                <div style={styles.historySection}>
                  <div style={{ padding: '14px 0 8px' }}>
                    <div style={styles.historyTitle}>최근 당첨 이력</div>
                    {detailStore.winHistory.map((h, i) => (
                      <div key={i} style={styles.historyItem}>
                        <span style={styles.historyRound}>{h.round}회</span>
                        <span style={styles.historyRank(h.winRank)}>{RANK_LABEL[h.winRank] || `${h.winRank}등`}</span>
                        <span style={styles.historyDate}>{formatDate(h.winDate)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}

            {/* 길찾기 버튼 */}
            <div style={styles.footer}>
              <button style={styles.directionBtn} onClick={handleDirections}>
                <DirectionIcon />
                길찾기
              </button>
            </div>
          </>
        )}
      </div>
    </>
  )
}
