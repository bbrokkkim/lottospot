package com.example.lotto.service

import com.example.lotto.api.store.dto.NearbyStoreDto
import com.example.lotto.api.store.dto.NearbyStoresResponse
import com.example.lotto.api.store.dto.StoreDetailResponse
import com.example.lotto.api.store.dto.toDetailResponse
import com.example.lotto.api.store.dto.toNearbyStoreDto
import com.example.lotto.domain.store.LottoStoreRepository
import com.example.lotto.domain.winning.WinningHistoryRepository
import com.example.lotto.exception.InvalidParameterException
import com.example.lotto.exception.StoreNotFoundException
import com.fasterxml.jackson.databind.ObjectMapper
import org.slf4j.LoggerFactory
import org.springframework.data.domain.PageRequest
import org.springframework.data.redis.core.RedisTemplate
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.time.Duration

/**
 * 판매점 관련 비즈니스 로직 서비스.
 *
 * - 좌표/파라미터 유효성 검증
 * - MySQL native query 를 통한 주변 판매점 + 동적 스코어 조회
 * - Redis Cache-Aside 패턴 적용 (TTL 5분)
 */
@Service
@Transactional(readOnly = true)
class StoreService(
    private val lottoStoreRepository: LottoStoreRepository,
    private val winningHistoryRepository: WinningHistoryRepository,
    private val redisTemplate: RedisTemplate<String, Any>,
    private val objectMapper: ObjectMapper
) {
    private val log = LoggerFactory.getLogger(javaClass)

    companion object {
        private val ALLOWED_RADIUS = setOf(500, 1000, 2000, 3000)
        private val ALLOWED_SORT   = setOf("distance", "score")
        private const val NEARBY_CACHE_TTL_MINUTES = 5L
        private const val DETAIL_CACHE_TTL_MINUTES = 10L

        private const val LAT_MIN = 33.0
        private const val LAT_MAX = 38.9
        private const val LNG_MIN = 124.0
        private const val LNG_MAX = 132.0
    }

    /**
     * 주변 판매점 목록을 조회한다.
     *
     * @param lat    기준 위도 (WGS84, 33.0 ~ 38.9)
     * @param lng    기준 경도 (WGS84, 124.0 ~ 132.0)
     * @param radius 검색 반경 미터 (허용값: 500/1000/2000/3000, 기본 1000)
     * @param limit  최대 반환 개수 (기본 20, 최대 50)
     * @param sort   정렬 기준 ("distance" 또는 "score", 기본 "distance")
     */
    fun findNearby(
        lat: Double,
        lng: Double,
        radius: Int = 1000,
        limit: Int = 20,
        sort: String = "distance"
    ): NearbyStoresResponse {
        validateCoordinates(lat, lng)
        validateRadius(radius)
        validateSort(sort)
        val safeLimit = limit.coerceIn(1, 50)

        val cacheKey = buildNearbyCacheKey(lat, lng, radius, sort)
        val cached = getFromCache<NearbyStoresResponse>(cacheKey)
        if (cached != null) {
            log.debug("Cache hit: {}", cacheKey)
            return cached
        }

        val projections = when (sort) {
            "score" -> lottoStoreRepository.findNearbyOrderByScore(lat, lng, radius, safeLimit)
            else    -> lottoStoreRepository.findNearbyOrderByDistance(lat, lng, radius, safeLimit)
        }
        val stores = projections.map { it.toNearbyStoreDto() }
        val response = NearbyStoresResponse(stores = stores, totalCount = stores.size)

        putToCache(cacheKey, response, Duration.ofMinutes(NEARBY_CACHE_TTL_MINUTES))
        return response
    }

    /**
     * 판매점 상세를 조회한다. 당첨 이력 최근 5건을 포함한다.
     *
     * @param storeId 판매점 PK
     */
    fun findById(storeId: Long): StoreDetailResponse {
        val cacheKey = "store:detail:$storeId"
        val cached = getFromCache<StoreDetailResponse>(cacheKey)
        if (cached != null) {
            log.debug("Cache hit: {}", cacheKey)
            return cached
        }

        val projection = lottoStoreRepository.findByIdWithScore(storeId)
            ?: throw StoreNotFoundException(storeId)

        val histories = winningHistoryRepository.findRecentByStoreId(
            storeId = storeId,
            limit   = PageRequest.of(0, 5)
        )
        val response = projection.toDetailResponse(histories)

        putToCache(cacheKey, response, Duration.ofMinutes(DETAIL_CACHE_TTL_MINUTES))
        return response
    }

    // -----------------------------------------------------------------------
    // private helpers
    // -----------------------------------------------------------------------

    private fun validateCoordinates(lat: Double, lng: Double) {
        if (lat < LAT_MIN || lat > LAT_MAX) {
            throw InvalidParameterException("lat 은 ${LAT_MIN} ~ ${LAT_MAX} 범위여야 합니다. 입력값: $lat")
        }
        if (lng < LNG_MIN || lng > LNG_MAX) {
            throw InvalidParameterException("lng 은 ${LNG_MIN} ~ ${LNG_MAX} 범위여야 합니다. 입력값: $lng")
        }
    }

    private fun validateRadius(radius: Int) {
        if (radius !in ALLOWED_RADIUS) {
            throw InvalidParameterException("radius 허용값: ${ALLOWED_RADIUS.sorted()}. 입력값: $radius")
        }
    }

    private fun validateSort(sort: String) {
        if (sort !in ALLOWED_SORT) {
            throw InvalidParameterException("sort 허용값: $ALLOWED_SORT. 입력값: $sort")
        }
    }

    /**
     * 캐시 키 형식: nearby:{lat_2dp}:{lng_2dp}:{radius}:{sort}
     * 소수점 2자리로 반올림하여 미세한 좌표 차이로 캐시가 분산되는 것을 방지한다.
     */
    private fun buildNearbyCacheKey(lat: Double, lng: Double, radius: Int, sort: String): String {
        val latKey = "%.2f".format(lat)
        val lngKey = "%.2f".format(lng)
        return "nearby:$latKey:$lngKey:$radius:$sort"
    }

    private inline fun <reified T> getFromCache(key: String): T? {
        return try {
            val value = redisTemplate.opsForValue().get(key) ?: return null
            objectMapper.convertValue(value, T::class.java)
        } catch (e: Exception) {
            log.warn("Redis read failed for key={}: {}", key, e.message)
            null
        }
    }

    private fun putToCache(key: String, value: Any, ttl: Duration) {
        try {
            redisTemplate.opsForValue().set(key, value, ttl)
        } catch (e: Exception) {
            log.warn("Redis write failed for key={}: {}", key, e.message)
        }
    }
}
