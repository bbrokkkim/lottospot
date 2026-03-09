import { useState, useEffect, useCallback } from 'react'

// GPS 권한 거부 시 서울 기본값
const DEFAULT_POSITION = {
  lat: 37.5665,
  lng: 126.9780,
}

/**
 * GPS 현재 위치를 반환하는 훅.
 * 권한 거부 또는 오류 시 서울 중심(37.5665, 126.9780)을 기본값으로 사용.
 */
export function useGeolocation() {
  const [position, setPosition] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isDefault, setIsDefault] = useState(false)

  const requestLocation = useCallback(() => {
    setIsLoading(true)
    setError(null)

    if (!navigator.geolocation) {
      setPosition(DEFAULT_POSITION)
      setIsDefault(true)
      setIsLoading(false)
      setError('이 브라우저에서는 위치 서비스를 지원하지 않습니다.')
      return
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setPosition({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
        })
        setIsDefault(false)
        setIsLoading(false)
      },
      (err) => {
        let message = '위치를 가져올 수 없습니다.'
        if (err.code === err.PERMISSION_DENIED) {
          message = '위치 권한이 거부되었습니다. 서울 기본 위치를 사용합니다.'
        } else if (err.code === err.POSITION_UNAVAILABLE) {
          message = '위치 정보를 사용할 수 없습니다. 서울 기본 위치를 사용합니다.'
        } else if (err.code === err.TIMEOUT) {
          message = '위치 요청 시간이 초과되었습니다. 서울 기본 위치를 사용합니다.'
        }
        setPosition(DEFAULT_POSITION)
        setIsDefault(true)
        setError(message)
        setIsLoading(false)
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 30000,
      },
    )
  }, [])

  useEffect(() => {
    requestLocation()
  }, [requestLocation])

  return { position, isLoading, error, isDefault, refetch: requestLocation }
}
