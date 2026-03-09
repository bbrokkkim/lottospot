import { useState, useEffect } from 'react'
import { fetchStoreDetail } from '../api/stores'

/**
 * 판매점 상세 정보를 가져오는 훅.
 * storeId가 null이면 요청하지 않음.
 */
export function useStoreDetail(storeId) {
  const [store, setStore] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (storeId == null) {
      setStore(null)
      return
    }

    let cancelled = false
    setIsLoading(true)
    setError(null)

    fetchStoreDetail(storeId)
      .then((data) => {
        if (!cancelled) setStore(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || '상세 정보를 불러오지 못했습니다.')
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [storeId])

  return { store, isLoading, error }
}
