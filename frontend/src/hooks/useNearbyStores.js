import { useState, useEffect, useRef, useCallback } from 'react'
import { fetchNearbyStores } from '../api/stores'

const DEBOUNCE_MS = 500

/**
 * 주변 판매점 목록을 가져오는 훅.
 * lat/lng/radius/sort 변경 시 500ms 디바운스 후 API 호출.
 */
export function useNearbyStores({ lat, lng, radius = 1000, sort = 'distance', limit = 50 }) {
  const [stores, setStores] = useState([])
  const [totalCount, setTotalCount] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  const timerRef = useRef(null)
  const abortRef = useRef(null)

  const load = useCallback(async (params) => {
    // 이전 요청 취소
    if (abortRef.current) {
      abortRef.current.abort()
    }
    const controller = new AbortController()
    abortRef.current = controller

    setIsLoading(true)
    setError(null)

    try {
      const data = await fetchNearbyStores(params)
      if (!controller.signal.aborted) {
        setStores(data.stores || [])
        setTotalCount(data.totalCount || 0)
      }
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(err.message || '판매점 정보를 불러오지 못했습니다.')
      }
    } finally {
      if (!controller.signal.aborted) {
        setIsLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    if (lat == null || lng == null) return

    if (timerRef.current) {
      clearTimeout(timerRef.current)
    }

    timerRef.current = setTimeout(() => {
      load({ lat, lng, radius, sort, limit })
    }, DEBOUNCE_MS)

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [lat, lng, radius, sort, limit, load])

  const refetch = useCallback(() => {
    if (lat == null || lng == null) return
    load({ lat, lng, radius, sort, limit })
  }, [lat, lng, radius, sort, limit, load])

  return { stores, totalCount, isLoading, error, refetch }
}
