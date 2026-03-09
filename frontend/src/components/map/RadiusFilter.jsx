import React from 'react'

const RADIUS_OPTIONS = [
  { value: 500, label: '500m' },
  { value: 1000, label: '1km' },
  { value: 2000, label: '2km' },
  { value: 3000, label: '3km' },
]

const styles = {
  container: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '8px 16px',
    background: '#132337',
    borderTop: '1px solid #243448',
  },
  label: {
    fontSize: 12,
    color: '#8FA3B8',
    fontWeight: 500,
    marginRight: 4,
    flexShrink: 0,
  },
  optionsRow: {
    display: 'flex',
    gap: 6,
    flex: 1,
  },
  option: (isActive) => ({
    flex: 1,
    height: 32,
    borderRadius: 20,
    fontSize: 13,
    fontWeight: isActive ? 700 : 500,
    color: isActive ? '#0D1B2A' : '#8FA3B8',
    background: isActive ? '#FFD700' : '#1A2E45',
    border: isActive ? 'none' : '1px solid #243448',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: isActive ? '0 2px 8px #FFD70066' : 'none',
  }),
}

export function RadiusFilter({ radius, onChange }) {
  return (
    <div style={styles.container}>
      <span style={styles.label}>반경</span>
      <div style={styles.optionsRow}>
        {RADIUS_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            style={styles.option(radius === opt.value)}
            onClick={() => onChange(opt.value)}
            aria-pressed={radius === opt.value}
            aria-label={`반경 ${opt.label}`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  )
}
