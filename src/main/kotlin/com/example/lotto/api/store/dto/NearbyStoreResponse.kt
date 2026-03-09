package com.example.lotto.api.store.dto

import com.example.lotto.domain.store.StoreWithScoreProjection
import kotlin.math.roundToInt

/**
 * 주변 판매점 단건 응답 DTO.
 *
 * grade 는 score 를 기준으로 4단계로 분류한다.
 *   GOLD   >= 70
 *   SILVER >= 40
 *   BRONZE >= 10
 *   NORMAL < 10
 */
data class NearbyStoreDto(
    val id: Long,
    val name: String,
    val address: String,
    val lat: Double,
    val lng: Double,
    val distance: Int,
    val score: Int,
    val grade: String,
    val firstWinCount: Int,
    val secondWinCount: Int,
    val recentWinRound: Int?,
    val isOpen: Boolean
)

/**
 * /api/stores/nearby 응답의 data 필드.
 */
data class NearbyStoresResponse(
    val stores: List<NearbyStoreDto>,
    val totalCount: Int
)

/**
 * StoreWithScoreProjection → NearbyStoreDto 변환 확장 함수.
 */
fun StoreWithScoreProjection.toNearbyStoreDto(): NearbyStoreDto {
    val scoreInt = getScore().roundToInt().coerceAtLeast(0)
    val grade = when {
        scoreInt >= 70 -> "GOLD"
        scoreInt >= 40 -> "SILVER"
        scoreInt >= 10 -> "BRONZE"
        else           -> "NORMAL"
    }
    return NearbyStoreDto(
        id             = getId(),
        name           = getName(),
        address        = getAddress(),
        lat            = getLat(),
        lng            = getLng(),
        distance       = getDistance().roundToInt(),
        score          = scoreInt,
        grade          = grade,
        firstWinCount  = getFirstWinCount(),
        secondWinCount = getSecondWinCount(),
        recentWinRound = getRecentWinRound(),
        isOpen         = getIsOpen()?.let { it != 0 } ?: true
    )
}
