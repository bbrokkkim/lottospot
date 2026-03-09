package com.example.lotto.domain.winning

import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.data.jpa.repository.Query
import org.springframework.data.repository.query.Param

interface WinningHistoryRepository : JpaRepository<WinningHistory, Long> {

    /**
     * 특정 판매점의 최근 당첨 이력을 최신 순으로 조회한다.
     * 판매점 상세 화면에서 최근 N건을 표시하는 데 사용한다.
     */
    @Query(
        """
        SELECT w FROM WinningHistory w
        WHERE w.store.id = :storeId
        ORDER BY w.winDate DESC, w.round DESC
        """
    )
    fun findRecentByStoreId(
        @Param("storeId") storeId: Long,
        limit: org.springframework.data.domain.Pageable
    ): List<WinningHistory>
}
