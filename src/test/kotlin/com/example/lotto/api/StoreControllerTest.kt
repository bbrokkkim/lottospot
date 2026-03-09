package com.example.lotto.api

import com.example.lotto.api.store.StoreController
import com.example.lotto.api.store.dto.NearbyStoreDto
import com.example.lotto.api.store.dto.NearbyStoresResponse
import com.example.lotto.api.store.dto.StoreDetailResponse
import com.example.lotto.exception.GlobalExceptionHandler
import com.example.lotto.exception.InvalidParameterException
import com.example.lotto.exception.StoreNotFoundException
import com.example.lotto.service.StoreService
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.DisplayName
import org.junit.jupiter.api.Test
import org.mockito.BDDMockito.given
import org.mockito.kotlin.any
import org.mockito.kotlin.eq
import org.mockito.kotlin.mock
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.get
import org.springframework.test.web.servlet.setup.MockMvcBuilders

@DisplayName("StoreController 단위 테스트 (standaloneSetup)")
class StoreControllerTest {

    private lateinit var mockMvc: MockMvc
    private lateinit var storeService: StoreService

    @BeforeEach
    fun setUp() {
        storeService = mock()
        mockMvc = MockMvcBuilders
            .standaloneSetup(StoreController(storeService))
            .setControllerAdvice(GlobalExceptionHandler())
            .build()
    }

    // -----------------------------------------------------------------------
    // /api/stores/nearby
    // -----------------------------------------------------------------------

    @Test
    @DisplayName("GET /api/stores/nearby - 정상 요청은 200 과 표준 응답 포맷을 반환한다")
    fun `nearby returns 200 with standard format`() {
        val storeDto = NearbyStoreDto(
            id             = 1L,
            name           = "행운복권방",
            address        = "서울시 강남구 테헤란로 123",
            lat            = 37.5123456,
            lng            = 127.1234567,
            distance       = 300,
            score          = 87,
            grade          = "GOLD",
            firstWinCount  = 5,
            secondWinCount = 12,
            recentWinRound = 1098,
            isOpen         = true
        )
        val response = NearbyStoresResponse(stores = listOf(storeDto), totalCount = 1)
        given(storeService.findNearby(any(), any(), any(), any(), any())).willReturn(response)

        mockMvc.get("/api/stores/nearby") {
            param("lat", "37.5")
            param("lng", "127.0")
        }.andExpect {
            status { isOk() }
            jsonPath("$.success") { value(true) }
            jsonPath("$.message") { value("OK") }
            jsonPath("$.data.totalCount") { value(1) }
            jsonPath("$.data.stores[0].name") { value("행운복권방") }
            jsonPath("$.data.stores[0].grade") { value("GOLD") }
            jsonPath("$.data.stores[0].firstWinCount") { value(5) }
        }
    }

    @Test
    @DisplayName("GET /api/stores/nearby - lat 누락 시 400 반환")
    fun `nearby missing lat returns 400`() {
        mockMvc.get("/api/stores/nearby") {
            param("lng", "127.0")
        }.andExpect {
            status { isBadRequest() }
            jsonPath("$.success") { value(false) }
        }
    }

    @Test
    @DisplayName("GET /api/stores/nearby - 서비스에서 InvalidParameterException 발생 시 400 반환")
    fun `nearby invalid parameter returns 400`() {
        given(storeService.findNearby(any(), any(), any(), any(), any()))
            .willThrow(InvalidParameterException("lat 은 33.0 ~ 38.9 범위여야 합니다"))

        mockMvc.get("/api/stores/nearby") {
            param("lat", "99.0")
            param("lng", "127.0")
        }.andExpect {
            status { isBadRequest() }
            jsonPath("$.success") { value(false) }
            jsonPath("$.message") { value("lat 은 33.0 ~ 38.9 범위여야 합니다") }
        }
    }

    @Test
    @DisplayName("GET /api/stores/nearby - sort=score 파라미터를 정상 처리한다")
    fun `nearby with sort=score returns 200`() {
        val response = NearbyStoresResponse(stores = emptyList(), totalCount = 0)
        given(storeService.findNearby(any(), any(), any(), any(), eq("score"))).willReturn(response)

        mockMvc.get("/api/stores/nearby") {
            param("lat", "37.5")
            param("lng", "127.0")
            param("sort", "score")
        }.andExpect {
            status { isOk() }
            jsonPath("$.data.totalCount") { value(0) }
        }
    }

    // -----------------------------------------------------------------------
    // /api/stores/{id}
    // -----------------------------------------------------------------------

    @Test
    @DisplayName("GET /api/stores/{id} - 존재하는 판매점은 200 반환")
    fun `getById returns 200 for existing store`() {
        val detail = StoreDetailResponse(
            id             = 1L,
            name           = "행운복권방",
            address        = "서울시 강남구 테헤란로 123",
            addressDetail  = null,
            lat            = 37.5123456,
            lng            = 127.1234567,
            phone          = "02-1234-5678",
            isOpen         = true,
            score          = 87,
            grade          = "GOLD",
            firstWinCount  = 5,
            secondWinCount = 12,
            recentWinRound = 1098,
            winHistory     = emptyList()
        )
        given(storeService.findById(1L)).willReturn(detail)

        mockMvc.get("/api/stores/1").andExpect {
            status { isOk() }
            jsonPath("$.success") { value(true) }
            jsonPath("$.data.id") { value(1) }
            jsonPath("$.data.grade") { value("GOLD") }
        }
    }

    @Test
    @DisplayName("GET /api/stores/{id} - 존재하지 않는 판매점은 404 반환")
    fun `getById returns 404 for missing store`() {
        given(storeService.findById(999L)).willThrow(StoreNotFoundException(999L))

        mockMvc.get("/api/stores/999").andExpect {
            status { isNotFound() }
            jsonPath("$.success") { value(false) }
        }
    }
}
