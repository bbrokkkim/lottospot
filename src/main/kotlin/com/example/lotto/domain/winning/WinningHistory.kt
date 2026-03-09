package com.example.lotto.domain.winning

import com.example.lotto.domain.store.LottoStore
import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.FetchType
import jakarta.persistence.GeneratedValue
import jakarta.persistence.GenerationType
import jakarta.persistence.Id
import jakarta.persistence.JoinColumn
import jakarta.persistence.ManyToOne
import jakarta.persistence.Table
import jakarta.persistence.UniqueConstraint
import java.time.LocalDate
import java.time.LocalDateTime

/**
 * 판매점별 로또 당첨 이력 엔티티.
 *
 * win_rank 는 1등(10점) 또는 2등(3점)만 저장한다.
 * (store_id, round, win_rank) 유니크 제약으로 중복 적재를 방지한다.
 */
@Entity
@Table(
    name = "winning_history",
    uniqueConstraints = [
        UniqueConstraint(
            name = "uk_store_round_rank",
            columnNames = ["store_id", "round", "win_rank"]
        )
    ]
)
open class WinningHistory(

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    val id: Long = 0,

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "store_id", nullable = false)
    val store: LottoStore,

    @Column(name = "round", nullable = false)
    val round: Int,

    /**
     * 당첨 등수. 1 = 1등, 2 = 2등.
     */
    @Column(name = "win_rank", nullable = false)
    val winRank: Int,

    @Column(name = "win_date", nullable = false)
    val winDate: LocalDate,

    @Column(name = "created_at", nullable = false)
    val createdAt: LocalDateTime = LocalDateTime.now()
)
