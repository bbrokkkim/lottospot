import React from 'react'

const GRADE_CONFIG = {
  GOLD: { label: '금', bg: '#FFD700', color: '#1A1100', icon: '★' },
  SILVER: { label: '은', bg: '#C0C0C0', color: '#1A1A1A', icon: '★' },
  BRONZE: { label: '동', bg: '#CD7F32', color: '#1A0D00', icon: '★' },
  NORMAL: { label: '일반', bg: '#3A4A5A', color: '#9E9E9E', icon: '●' },
}

export function GradeBadge({ grade, size = 'md' }) {
  const config = GRADE_CONFIG[grade] || GRADE_CONFIG.NORMAL
  const sizes = {
    sm: { width: 28, height: 28, fontSize: 11 },
    md: { width: 36, height: 36, fontSize: 14 },
    lg: { width: 44, height: 44, fontSize: 18 },
  }
  const s = sizes[size] || sizes.md

  return (
    <div
      style={{
        width: s.width,
        height: s.height,
        borderRadius: '50%',
        background: config.bg,
        color: config.color,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: s.fontSize,
        fontWeight: 700,
        flexShrink: 0,
        boxShadow: `0 2px 8px ${config.bg}66`,
      }}
      title={config.label}
    >
      {config.icon}
    </div>
  )
}

export { GRADE_CONFIG }
