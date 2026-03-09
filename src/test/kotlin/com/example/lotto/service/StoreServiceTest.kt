package com.example.lotto.service

import com.example.lotto.domain.store.LottoStoreRepository
import com.example.lotto.domain.store.StoreWithScoreProjection
import com.example.lotto.api.store.dto.NearbyStoresResponse
import com.example.lotto.domain.winning.WinningHistoryRepository
import com.example.lotto.exception.InvalidParameterException
import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.databind.SerializationFeature
import com.fasterxml.jackson.module.kotlin.kotlinModule
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.DisplayName
import org.junit.jupiter.api.Test
import org.mockito.BDDMockito.given
import org.mockito.kotlin.any
import org.mockito.kotlin.eq
import org.mockito.kotlin.mock
import org.mockito.kotlin.never
import org.mockito.kotlin.verify
import org.springframework.data.redis.core.RedisTemplate
import org.springframework.data.redis.core.ValueOperations

@DisplayName("StoreService 단위 테스트")
class StoreServiceTest {

    private lateinit var lottoStoreRepository: LottoStoreRepository
    private lateinit var winningHistoryRepository: WinningHistoryRepository
    private lateinit var redisTemplate: RedisTemplate<String, Any>
    private lateinit var valueOps: ValueOperations<String, Any>
    private lateinit var objectMapper: ObjectMapper
    private lateinit var storeService: StoreService

    @BeforeEach
    fun setUp() {
        lottoStoreRepository     = mock()
        winningHistoryRepository = mock()
        redisTemplate            = mock()
        valueOps                 = mock()
        objectMapper             = ObjectMapper()
            .registerModule(kotlinModule())
            .findAndRegisterModules()
            .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS)

        given(redisTemplate.opsForValue()).willReturn(valueOps)
        given(valueOps.get(any<String>())).willReturn(null)

        storeService = StoreService(
            lottoStoreRepository     = lottoStoreRepository,
            winningHistoryRepository = winningHistoryRepository,
            redisTemplate            = redisTemplate,
            objectMapper             = objectMapper
        )
    }

    // -----------------------------------------------------------------------
    // 좌표 유효성 검증
    // -----------------------------------------------------------------------

    @Test
    @DisplayName("lat 이 범위를 벗어나면 InvalidParameterException 을 던진다")
    fun `lat out of range throws InvalidParameterException`() {
        assertThatThrownBy {
            storeService.findNearby(lat = 39.0, lng = 127.0)
        }.isInstanceOf(InvalidParameterException::class.java)
            .hasMessageContaining("lat")
    }

    @Test
    @DisplayName("lng 이 범위를 벗어나면 InvalidParameterException 을 던진다")
    fun `lng out of range throws InvalidParameterException`() {
        assertThatThrownBy {
            storeService.findNearby(lat = 37.5, lng = 133.0)
        }.isInstanceOf(InvalidParameterException::class.java)
            .hasMessageContaining("lng")
    }

    @Test
    @DisplayName("허용되지 않은 radius 이면 InvalidParameterException 을 던진다")
    fun `invalid radius throws InvalidParameterException`() {
        assertThatThrownBy {
            storeService.findNearby(lat = 37.5, lng = 127.0, radius = 1500)
        }.isInstanceOf(InvalidParameterException::class.java)
            .hasMessageContaining("radius")
    }

    @Test
    @DisplayName("허용되지 않은 sort 이면 InvalidParameterException 을 던진다")
    fun `invalid sort throws InvalidParameterException`() {
        assertThatThrownBy {
            storeService.findNearby(lat = 37.5, lng = 127.0, sort = "name")
        }.isInstanceOf(InvalidParameterException::class.java)
            .hasMessageContaining("sort")
    }

    // -----------------------------------------------------------------------
    // 정상 조회
    // -----------------------------------------------------------------------

    @Test
    @DisplayName("sort=distance 이면 findNearbyOrderByDistance 를 호출한다")
    fun `sort distance calls findNearbyOrderByDistance`() {
        given(
            lottoStoreRepository.findNearbyOrderByDistance(
                lat = 37.5, lng = 127.0, radius = 1000, limit = 20
            )
        ).willReturn(emptyList())

        val result = storeService.findNearby(lat = 37.5, lng = 127.0, sort = "distance")

        verify(lottoStoreRepository).findNearbyOrderByDistance(37.5, 127.0, 1000, 20)
        verify(lottoStoreRepository, never()).findNearbyOrderByScore(any(), any(), any(), any())
        assertThat(result.totalCount).isEqualTo(0)
    }

    @Test
    @DisplayName("sort=score 이면 findNearbyOrderByScore 를 호출한다")
    fun `sort score calls findNearbyOrderByScore`() {
        given(
            lottoStoreRepository.findNearbyOrderByScore(
                lat = 37.5, lng = 127.0, radius = 1000, limit = 20
            )
        ).willReturn(listOf(buildProjection()))

        val result = storeService.findNearby(lat = 37.5, lng = 127.0, sort = "score")

        verify(lottoStoreRepository).findNearbyOrderByScore(37.5, 127.0, 1000, 20)
        assertThat(result.totalCount).isEqualTo(1)
    }

    // -----------------------------------------------------------------------
    // 스코어 / 등급 계산
    // -----------------------------------------------------------------------

    @Test
    @DisplayName("score >= 70 이면 grade = GOLD")
    fun `score 70 or above is GOLD`() {
        val projection = buildProjection(score = 70.0, firstWinCount = 5, secondWinCount = 7)
        given(
            lottoStoreRepository.findNearbyOrderByDistance(any(), any(), any(), any())
        ).willReturn(listOf(projection))

        val result = storeService.findNearby(lat = 37.5, lng = 127.0)

        assertThat(result.stores.first().grade).isEqualTo("GOLD")
    }

    @Test
    @DisplayName("score 40 ~ 69 이면 grade = SILVER")
    fun `score 40 to 69 is SILVER`() {
        val projection = buildProjection(score = 45.0)
        given(
            lottoStoreRepository.findNearbyOrderByDistance(any(), any(), any(), any())
        ).willReturn(listOf(projection))

        val result = storeService.findNearby(lat = 37.5, lng = 127.0)

        assertThat(result.stores.first().grade).isEqualTo("SILVER")
    }

    @Test
    @DisplayName("score 10 ~ 39 이면 grade = BRONZE")
    fun `score 10 to 39 is BRONZE`() {
        val projection = buildProjection(score = 13.0)
        given(
            lottoStoreRepository.findNearbyOrderByDistance(any(), any(), any(), any())
        ).willReturn(listOf(projection))

        val result = storeService.findNearby(lat = 37.5, lng = 127.0)

        assertThat(result.stores.first().grade).isEqualTo("BRONZE")
    }

    @Test
    @DisplayName("score < 10 이면 grade = NORMAL")
    fun `score below 10 is NORMAL`() {
        val projection = buildProjection(score = 3.0)
        given(
            lottoStoreRepository.findNearbyOrderByDistance(any(), any(), any(), any())
        ).willReturn(listOf(projection))

        val result = storeService.findNearby(lat = 37.5, lng = 127.0)

        assertThat(result.stores.first().grade).isEqualTo("NORMAL")
    }

    // -----------------------------------------------------------------------
    // 캐시 키 패턴
    // -----------------------------------------------------------------------

    @Test
    @DisplayName("같은 좌표(소수 2자리 기준)면 동일 캐시 키를 생성한다")
    fun `same 2dp coordinate generates same cache key`() {
        given(
            lottoStoreRepository.findNearbyOrderByDistance(any(), any(), any(), any())
        ).willReturn(emptyList())

        storeService.findNearby(lat = 37.50, lng = 127.00)
        verify(valueOps).set(
            eq("nearby:37.50:127.00:1000:distance"),
            any<NearbyStoresResponse>(),
            any<java.time.Duration>()
        )
    }

    // -----------------------------------------------------------------------
    // 헬퍼
    // -----------------------------------------------------------------------

    private fun buildProjection(
        id: Long             = 1L,
        name: String         = "행운복권방",
        address: String      = "서울시 강남구 테헤란로 123",
        lat: Double          = 37.5123456,
        lng: Double          = 127.1234567,
        distance: Double     = 300.0,
        firstWinCount: Int   = 0,
        secondWinCount: Int  = 0,
        score: Double        = 0.0,
        recentWinRound: Int? = null,
        isOpen: Int          = 1
    ): StoreWithScoreProjection = object : StoreWithScoreProjection {
        override fun getId()             = id
        override fun getName()           = name
        override fun getAddress()        = address
        override fun getLat()            = lat
        override fun getLng()            = lng
        override fun getPhone(): String? = null
        override fun getIsOpen(): Int    = isOpen
        override fun getDistance()       = distance
        override fun getFirstWinCount()  = firstWinCount
        override fun getSecondWinCount() = secondWinCount
        override fun getScore()          = score
        override fun getRecentWinRound() = recentWinRound
    }
}
