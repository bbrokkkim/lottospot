package com.example.lotto.api.store.dto

import com.example.lotto.domain.store.StoreWithScoreProjection
import com.example.lotto.domain.winning.WinningHistory
import kotlin.math.roundToInt

/**
 * 당첨 이력 단건 DTO (판매점 상세 포함용).
 */
data class WinHistoryDto(
    val round: Int,
    val winRank: Int,
    val winDate: String
)

/**
 * 판매점 상세 응답 DTO.
 * winHistory 는 최근 5건만 포함한다.
 */
data class StoreDetailResponse(
    val id: Long,
    val name: String,
    val address: String,
    val addressDetail: String?,
    val lat: Double,
    val lng: Double,
    val phone: String?,
    val isOpen: Boolean,
    val score: Int,
    val grade: String,
    val firstWinCount: Int,
    val secondWinCount: Int,
    val recentWinRound: Int?,
    val winHistory: List<WinHistoryDto>
)

fun StoreWithScoreProjection.toDetailResponse(histories: List<WinningHistory>): StoreDetailResponse {
    val scoreInt = getScore().roundToInt().coerceAtLeast(0)
    val grade = when {
        scoreInt >= 70 -> "GOLD"
        scoreInt >= 40 -> "SILVER"
        scoreInt >= 10 -> "BRONZE"
        else           -> "NORMAL"
    }
    return StoreDetailResponse(
        id             = getId(),
        name           = getName(),
        address        = getAddress(),
        addressDetail  = null,
        lat            = getLat(),
        lng            = getLng(),
        phone          = getPhone(),
        isOpen         = getIsOpen()?.let { it != 0 } ?: true,
        score          = scoreInt,
        grade          = grade,
        firstWinCount  = getFirstWinCount(),
        secondWinCount = getSecondWinCount(),
        recentWinRound = getRecentWinRound(),
        winHistory     = histories.map { h ->
            WinHistoryDto(
                round   = h.round,
                winRank = h.winRank,
                winDate = h.winDate.toString()
            )
        }
    )
}
