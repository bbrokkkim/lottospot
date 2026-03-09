import React, { useState } from 'react'

const styles = {
  container: {
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
    background: '#1A2E45',
    border: '1px solid #243448',
    borderRadius: '12px',
    padding: '0 12px',
    height: 44,
  },
  icon: {
    color: '#8FA3B8',
    marginRight: 8,
    flexShrink: 0,
    display: 'flex',
    alignItems: 'center',
  },
  input: {
    flex: 1,
    background: 'none',
    color: '#F0F4F8',
    fontSize: 14,
    lineHeight: '20px',
  },
  clearButton: {
    color: '#8FA3B8',
    padding: '4px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: '#243448',
    width: 20,
    height: 20,
    flexShrink: 0,
  },
}

function SearchIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  )
}

function ClearIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}

export function SearchBar({ onSearch }) {
  const [value, setValue] = useState('')

  const handleChange = (e) => {
    setValue(e.target.value)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && value.trim()) {
      onSearch?.(value.trim())
    }
  }

  const handleClear = () => {
    setValue('')
  }

  return (
    <div style={styles.container}>
      <span style={styles.icon}>
        <SearchIcon />
      </span>
      <input
        style={styles.input}
        type="text"
        placeholder="주소 또는 판매점명 검색..."
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        aria-label="판매점 검색"
      />
      {value && (
        <button style={styles.clearButton} onClick={handleClear} aria-label="검색어 지우기">
          <ClearIcon />
        </button>
      )}
    </div>
  )
}
