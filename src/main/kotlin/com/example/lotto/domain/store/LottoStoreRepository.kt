package com.example.lotto.domain.store

import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.data.jpa.repository.Query
import org.springframework.data.repository.query.Param

/**
 * 주변 판매점 거리 + 스코어 조회 프로젝션.
 *
 * score 는 winning_history 를 JOIN 하여 조회 시점에 동적으로 계산한다.
 * - base_score = (1등횟수 × 10) + (2등횟수 × 3)
 * - recency_bonus = 최근 2년 이내 1등 이력 있으면 base_score × 0.5
 * - score = base_score + recency_bonus
 *
 * recentWinRound 는 해당 판매점의 가장 최근 1등 당첨 회차 번호를 반환한다.
 */
interface StoreWithScoreProjection {
    fun getId(): Long
    fun getName(): String
    fun getAddress(): String
    fun getLat(): Double
    fun getLng(): Double
    fun getPhone(): String?
    fun getIsOpen(): Int?
    fun getDistance(): Double
    fun getFirstWinCount(): Int
    fun getSecondWinCount(): Int
    fun getScore(): Double
    fun getRecentWinRound(): Int?
}

interface LottoStoreRepository : JpaRepository<LottoStore, Long> {

    /**
     * 주어진 좌표로부터 radius(미터) 이내의 판매점을 조회한다.
     * is_open != 0 조건으로 폐업 판매점을 제외하며,
     * winning_history 를 LEFT JOIN 하여 스코어를 동적으로 계산한다.
     *
     * POINT(lng, lat) 순서는 MySQL 공간 함수 규약(경도 먼저)을 따른다.
     */
    @Query(
        value = """
            SELECT
                s.id                                                            AS id,
                s.name                                                          AS name,
                s.address                                                       AS address,
                s.lat                                                           AS lat,
                s.lng                                                           AS lng,
                s.phone                                                         AS phone,
                s.is_open                                                       AS isOpen,
                ST_Distance_Sphere(POINT(s.lng, s.lat), POINT(:lng, :lat))      AS distance,
                COALESCE(SUM(CASE WHEN w.win_rank = 1 THEN 1 ELSE 0 END), 0)   AS firstWinCount,
                COALESCE(SUM(CASE WHEN w.win_rank = 2 THEN 1 ELSE 0 END), 0)   AS secondWinCount,
                GREATEST(
                    COALESCE(SUM(CASE WHEN w.win_rank = 1 THEN 10
                                     WHEN w.win_rank = 2 THEN 3
                                     ELSE 0 END), 0)
                    + CASE
                        WHEN MAX(CASE WHEN w.win_rank = 1
                                       AND w.win_date >= DATE_SUB(CURDATE(), INTERVAL 2 YEAR)
                                  THEN 1 ELSE 0 END) = 1
                        THEN COALESCE(SUM(CASE WHEN w.win_rank = 1 THEN 10
                                               WHEN w.win_rank = 2 THEN 3
                                               ELSE 0 END), 0) * 0.5
                        ELSE 0
                      END,
                    0
                )                                                               AS score,
                MAX(CASE WHEN w.win_rank = 1 THEN w.round ELSE NULL END)        AS recentWinRound
            FROM lotto_store s
            LEFT JOIN winning_history w ON w.store_id = s.id
            WHERE ST_Distance_Sphere(POINT(s.lng, s.lat), POINT(:lng, :lat)) <= :radius
              AND (s.is_open IS NULL OR s.is_open != 0)
            GROUP BY s.id, s.name, s.address, s.lat, s.lng, s.phone, s.is_open
            ORDER BY distance
            LIMIT :limit
        """,
        nativeQuery = true
    )
    fun findNearbyOrderByDistance(
        @Param("lat") lat: Double,
        @Param("lng") lng: Double,
        @Param("radius") radius: Int,
        @Param("limit") limit: Int
    ): List<StoreWithScoreProjection>

    /**
     * findNearbyOrderByDistance 와 동일한 반경 필터이나 스코어 내림차순 정렬을 적용한다.
     */
    @Query(
        value = """
            SELECT
                s.id                                                            AS id,
                s.name                                                          AS name,
                s.address                                                       AS address,
                s.lat                                                           AS lat,
                s.lng                                                           AS lng,
                s.phone                                                         AS phone,
                s.is_open                                                       AS isOpen,
                ST_Distance_Sphere(POINT(s.lng, s.lat), POINT(:lng, :lat))      AS distance,
                COALESCE(SUM(CASE WHEN w.win_rank = 1 THEN 1 ELSE 0 END), 0)   AS firstWinCount,
                COALESCE(SUM(CASE WHEN w.win_rank = 2 THEN 1 ELSE 0 END), 0)   AS secondWinCount,
                GREATEST(
                    COALESCE(SUM(CASE WHEN w.win_rank = 1 THEN 10
                                     WHEN w.win_rank = 2 THEN 3
                                     ELSE 0 END), 0)
                    + CASE
                        WHEN MAX(CASE WHEN w.win_rank = 1
                                       AND w.win_date >= DATE_SUB(CURDATE(), INTERVAL 2 YEAR)
                                  THEN 1 ELSE 0 END) = 1
                        THEN COALESCE(SUM(CASE WHEN w.win_rank = 1 THEN 10
                                               WHEN w.win_rank = 2 THEN 3
                                               ELSE 0 END), 0) * 0.5
                        ELSE 0
                      END,
                    0
                )                                                               AS score,
                MAX(CASE WHEN w.win_rank = 1 THEN w.round ELSE NULL END)        AS recentWinRound
            FROM lotto_store s
            LEFT JOIN winning_history w ON w.store_id = s.id
            WHERE ST_Distance_Sphere(POINT(s.lng, s.lat), POINT(:lng, :lat)) <= :radius
              AND (s.is_open IS NULL OR s.is_open != 0)
            GROUP BY s.id, s.name, s.address, s.lat, s.lng, s.phone, s.is_open
            ORDER BY score DESC
            LIMIT :limit
        """,
        nativeQuery = true
    )
    fun findNearbyOrderByScore(
        @Param("lat") lat: Double,
        @Param("lng") lng: Double,
        @Param("radius") radius: Int,
        @Param("limit") limit: Int
    ): List<StoreWithScoreProjection>

    /**
     * 판매점 상세 조회 - 스코어 포함.
     */
    @Query(
        value = """
            SELECT
                s.id                                                            AS id,
                s.name                                                          AS name,
                s.address                                                       AS address,
                s.lat                                                           AS lat,
                s.lng                                                           AS lng,
                s.phone                                                         AS phone,
                s.is_open                                                       AS isOpen,
                0.0                                                             AS distance,
                COALESCE(SUM(CASE WHEN w.win_rank = 1 THEN 1 ELSE 0 END), 0)   AS firstWinCount,
                COALESCE(SUM(CASE WHEN w.win_rank = 2 THEN 1 ELSE 0 END), 0)   AS secondWinCount,
                GREATEST(
                    COALESCE(SUM(CASE WHEN w.win_rank = 1 THEN 10
                                     WHEN w.win_rank = 2 THEN 3
                                     ELSE 0 END), 0)
                    + CASE
                        WHEN MAX(CASE WHEN w.win_rank = 1
                                       AND w.win_date >= DATE_SUB(CURDATE(), INTERVAL 2 YEAR)
                                  THEN 1 ELSE 0 END) = 1
                        THEN COALESCE(SUM(CASE WHEN w.win_rank = 1 THEN 10
                                               WHEN w.win_rank = 2 THEN 3
                                               ELSE 0 END), 0) * 0.5
                        ELSE 0
                      END,
                    0
                )                                                               AS score,
                MAX(CASE WHEN w.win_rank = 1 THEN w.round ELSE NULL END)        AS recentWinRound
            FROM lotto_store s
            LEFT JOIN winning_history w ON w.store_id = s.id
            WHERE s.id = :storeId
            GROUP BY s.id, s.name, s.address, s.lat, s.lng, s.phone, s.is_open
        """,
        nativeQuery = true
    )
    fun findByIdWithScore(@Param("storeId") storeId: Long): StoreWithScoreProjection?
}
