import React, { useEffect, useState } from 'react'

const toastStyles = {
  wrapper: {
    position: 'fixed',
    bottom: '120px',
    left: '50%',
    transform: 'translateX(-50%)',
    zIndex: 9999,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '8px',
    pointerEvents: 'none',
  },
  toast: {
    background: 'rgba(19, 35, 55, 0.95)',
    border: '1px solid #243448',
    borderRadius: '24px',
    padding: '10px 20px',
    color: '#F0F4F8',
    fontSize: '14px',
    fontWeight: 500,
    backdropFilter: 'blur(12px)',
    boxShadow: '0 4px 24px rgba(0,0,0,0.4)',
    whiteSpace: 'nowrap',
    maxWidth: '320px',
    textAlign: 'center',
    transition: 'opacity 0.3s, transform 0.3s',
  },
  error: {
    background: 'rgba(220, 53, 69, 0.9)',
    border: '1px solid rgba(220, 53, 69, 0.5)',
  },
}

let globalShowToast = null

export function ToastProvider() {
  const [toasts, setToasts] = useState([])

  useEffect(() => {
    globalShowToast = (message, type = 'info', duration = 3000) => {
      const id = Date.now()
      setToasts((prev) => [...prev, { id, message, type }])
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id))
      }, duration)
    }
    return () => {
      globalShowToast = null
    }
  }, [])

  if (toasts.length === 0) return null

  return (
    <div style={toastStyles.wrapper}>
      {toasts.map((toast) => (
        <div
          key={toast.id}
          style={{
            ...toastStyles.toast,
            ...(toast.type === 'error' ? toastStyles.error : {}),
          }}
        >
          {toast.message}
        </div>
      ))}
    </div>
  )
}

export function showToast(message, type = 'info', duration = 3000) {
  if (globalShowToast) {
    globalShowToast(message, type, duration)
  }
}
