package com.example.lotto.domain.store

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.GeneratedValue
import jakarta.persistence.GenerationType
import jakarta.persistence.Id
import jakarta.persistence.Table
import java.time.LocalDateTime

/**
 * 로또 판매점 엔티티.
 *
 * location 컬럼(POINT, SRID 4326)은 JPA 가 직접 매핑하지 않으며,
 * 거리 계산은 native query 의 ST_Distance_Sphere 로 처리한다.
 * is_open = 0 인 폐업 판매점은 조회에서 제외한다.
 */
@Entity
@Table(name = "lotto_store")
open class LottoStore(

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    val id: Long = 0,

    @Column(name = "name", nullable = false, length = 100)
    val name: String,

    @Column(name = "address", nullable = false, length = 255)
    val address: String,

    @Column(name = "address_detail", length = 100)
    val addressDetail: String? = null,

    @Column(name = "lat", nullable = false)
    val lat: Double,

    @Column(name = "lng", nullable = false)
    val lng: Double,

    @Column(name = "phone", length = 20)
    val phone: String? = null,

    /**
     * 영업 여부. null 은 미확인, 0 은 폐업, 1 은 영업중.
     * 조회 시 is_open != 0 조건으로 폐업 판매점을 제외한다.
     */
    @Column(name = "is_open")
    val isOpen: Int? = 1,

    @Column(name = "created_at", nullable = false)
    val createdAt: LocalDateTime = LocalDateTime.now(),

    @Column(name = "updated_at", nullable = false)
    var updatedAt: LocalDateTime = LocalDateTime.now()
)
