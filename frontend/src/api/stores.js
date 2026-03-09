import client from './client'

/**
 * 주변 판매점 조회
 * @param {Object} params
 * @param {number} params.lat - WGS84 위도
 * @param {number} params.lng - WGS84 경도
 * @param {number} [params.radius=1000] - 반경 (500 | 1000 | 2000 | 3000)
 * @param {number} [params.limit=20] - 최대 결과 수
 * @param {string} [params.sort='distance'] - 정렬 ('distance' | 'score')
 */
export async function fetchNearbyStores({ lat, lng, radius = 1000, limit = 20, sort = 'distance' }) {
  const response = await client.get('/api/stores/nearby', {
    params: { lat, lng, radius, limit, sort },
  })
  return response.data
}

/**
 * 판매점 상세 조회
 * @param {number} id - 판매점 ID
 */
export async function fetchStoreDetail(id) {
  const response = await client.get(`/api/stores/${id}`)
  return response.data
}
