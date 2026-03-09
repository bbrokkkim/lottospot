package com.example.lotto.api.store

import com.example.lotto.api.store.dto.ApiResponse
import com.example.lotto.api.store.dto.NearbyStoresResponse
import com.example.lotto.api.store.dto.StoreDetailResponse
import com.example.lotto.service.StoreService
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.RestController

/**
 * 판매점 관련 REST 엔드포인트.
 *
 * 모든 응답은 { success, message, data } 표준 포맷을 따른다.
 * 파라미터 유효성 검증은 StoreService 에서 담당하며,
 * 검증 실패 시 InvalidParameterException → GlobalExceptionHandler → 400 응답으로 변환된다.
 */
@RestController
@RequestMapping("/api/stores")
class StoreController(
    private val storeService: StoreService
) {

    /**
     * 현재 위치 기준 반경 내 판매점 목록을 반환한다.
     *
     * GET /api/stores/nearby?lat=37.5&lng=127.0&radius=1000&limit=20&sort=distance
     *
     * @param lat    기준 위도 (필수, 33.0 ~ 38.9)
     * @param lng    기준 경도 (필수, 124.0 ~ 132.0)
     * @param radius 검색 반경 미터 (선택, 기본 1000, 허용값: 500/1000/2000/3000)
     * @param limit  최대 반환 개수 (선택, 기본 20, 최대 50)
     * @param sort   정렬 기준 (선택, 기본 "distance", 허용값: "distance"/"score")
     */
    @GetMapping("/nearby")
    fun getNearby(
        @RequestParam lat: Double,
        @RequestParam lng: Double,
        @RequestParam(defaultValue = "1000") radius: Int,
        @RequestParam(defaultValue = "20")   limit: Int,
        @RequestParam(defaultValue = "distance") sort: String
    ): ResponseEntity<ApiResponse<NearbyStoresResponse>> {
        val data = storeService.findNearby(
            lat    = lat,
            lng    = lng,
            radius = radius,
            limit  = limit,
            sort   = sort
        )
        return ResponseEntity.ok(ApiResponse.ok(data))
    }

    /**
     * 판매점 상세 정보를 반환한다. 당첨 이력 최근 5건 포함.
     *
     * GET /api/stores/{id}
     */
    @GetMapping("/{id}")
    fun getById(
        @PathVariable id: Long
    ): ResponseEntity<ApiResponse<StoreDetailResponse>> {
        val data = storeService.findById(id)
        return ResponseEntity.ok(ApiResponse.ok(data))
    }
}
