import React from 'react'
import { GradeBadge, GRADE_CONFIG } from '../common/GradeBadge'

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    background: '#132337',
    borderTop: '1px solid #243448',
    flex: 1,
    minHeight: 0,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '10px 16px',
    borderBottom: '1px solid #243448',
    flexShrink: 0,
  },
  tabs: {
    display: 'flex',
    gap: 4,
  },
  tab: (isActive) => ({
    height: 30,
    padding: '0 12px',
    borderRadius: 15,
    fontSize: 13,
    fontWeight: isActive ? 700 : 500,
    color: isActive ? '#FFD700' : '#8FA3B8',
    background: isActive ? 'rgba(255, 215, 0, 0.12)' : 'none',
    cursor: 'pointer',
    transition: 'all 0.2s',
    border: isActive ? '1px solid rgba(255,215,0,0.3)' : '1px solid transparent',
  }),
  countText: {
    fontSize: 12,
    color: '#8FA3B8',
    fontWeight: 500,
  },
  list: {
    flex: 1,
    overflowY: 'auto',
  },
  item: (isSelected) => ({
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '12px 16px',
    cursor: 'pointer',
    borderBottom: '1px solid #1A2E45',
    background: isSelected ? 'rgba(255,215,0,0.06)' : 'transparent',
    transition: 'background 0.15s',
    borderLeft: isSelected ? '3px solid #FFD700' : '3px solid transparent',
  }),
  itemContent: {
    flex: 1,
    minWidth: 0,
  },
  itemName: {
    fontSize: 14,
    fontWeight: 600,
    color: '#F0F4F8',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  itemMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginTop: 3,
  },
  itemDistance: {
    fontSize: 12,
    color: '#8FA3B8',
    fontFamily: 'DM Mono, monospace',
  },
  itemWin: {
    fontSize: 12,
    color: '#FFD700',
    fontWeight: 500,
  },
  itemRight: {
    textAlign: 'right',
    flexShrink: 0,
  },
  itemScore: {
    fontSize: 18,
    fontWeight: 700,
    color: '#FFD700',
    fontFamily: 'DM Mono, monospace',
  },
  itemScoreLabel: {
    fontSize: 10,
    color: '#8FA3B8',
    marginTop: 1,
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '40px 20px',
    color: '#8FA3B8',
    gap: 8,
  },
  emptyIcon: {
    fontSize: 32,
    marginBottom: 4,
  },
  emptyText: {
    fontSize: 14,
    fontWeight: 500,
    textAlign: 'center',
  },
  emptySubtext: {
    fontSize: 12,
    textAlign: 'center',
    color: '#4A6278',
  },
  loadingRow: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    padding: '24px',
    color: '#8FA3B8',
    fontSize: 13,
    gap: 8,
  },
}

function formatDistance(meters) {
  if (meters == null) return ''
  if (meters < 1000) return `${Math.round(meters)}m`
  return `${(meters / 1000).toFixed(1)}km`
}

function LoadingSpinner() {
  return (
    <div style={styles.loadingRow}>
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="#8FA3B8"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{ animation: 'spin 1s linear infinite' }}
      >
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
        <path d="M21 12a9 9 0 1 1-6.219-8.56" />
      </svg>
      불러오는 중...
    </div>
  )
}

export function StoreListPanel({ stores, totalCount, isLoading, sort, onSortChange, selectedId, onSelectStore }) {
  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.tabs}>
          <button
            style={styles.tab(sort === 'distance')}
            onClick={() => onSortChange('distance')}
          >
            거리순
          </button>
          <button
            style={styles.tab(sort === 'score')}
            onClick={() => onSortChange('score')}
          >
            명당순
          </button>
        </div>
        <span style={styles.countText}>
          {isLoading ? '검색 중...' : `총 ${totalCount}개 결과`}
        </span>
      </div>

      <div style={styles.list}>
        {isLoading && stores.length === 0 ? (
          <LoadingSpinner />
        ) : stores.length === 0 ? (
          <div style={styles.emptyState}>
            <div style={styles.emptyIcon}>📍</div>
            <div style={styles.emptyText}>주변에 판매점이 없습니다</div>
            <div style={styles.emptySubtext}>반경을 넓혀서 다시 검색해보세요</div>
          </div>
        ) : (
          stores.map((store) => (
            <div
              key={store.id}
              style={styles.item(selectedId === store.id)}
              onClick={() => onSelectStore(store)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && onSelectStore(store)}
              aria-label={`${store.name} 선택`}
            >
              <GradeBadge grade={store.grade} size="md" />
              <div style={styles.itemContent}>
                <div style={styles.itemName}>{store.name}</div>
                <div style={styles.itemMeta}>
                  <span style={styles.itemDistance}>{formatDistance(store.distance)}</span>
                  {store.firstWinCount > 0 && (
                    <span style={styles.itemWin}>1등 {store.firstWinCount}회</span>
                  )}
                </div>
              </div>
              <div style={styles.itemRight}>
                <div style={styles.itemScore}>{store.score}</div>
                <div style={styles.itemScoreLabel}>점수</div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
