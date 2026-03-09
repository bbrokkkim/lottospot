---
name: spring-conventions
description: LottoSpot Spring Boot + Kotlin 코딩 컨벤션. backend-builder가 코드 작성 시 항상 참조.
---

# Spring Boot + Kotlin 컨벤션

## 표준 응답 래퍼
```kotlin
data class ApiResponse<T>(
    val success: Boolean,
    val data: T?,
    val message: String?
) {
    companion object {
        fun <T> ok(data: T) = ApiResponse(true, data, null)
        fun <T> error(message: String) = ApiResponse<T>(false, null, message)
    }
}
```

## 컨트롤러 패턴
```kotlin
@RestController
@RequestMapping("/api/stores")
class StoreController(private val storeService: StoreService) {

    @GetMapping("/nearby")
    fun getNearby(
        @RequestParam lat: Double,
        @RequestParam lng: Double,
        @RequestParam(defaultValue = "1000") radius: Int,
        @RequestParam(defaultValue = "20") limit: Int
    ): ResponseEntity<ApiResponse<List<StoreDto>>> =
        ResponseEntity.ok(ApiResponse.ok(storeService.findNearby(lat, lng, radius, limit)))
}
```

## DTO + 변환
```kotlin
data class StoreDto(
    val id: Long,
    val name: String,
    val address: String?,
    val lat: Double?,
    val lng: Double?,
    val distance: Int?,
    val firstWinCount: Int,
    val secondWinCount: Int
)

fun LottoStore.toDto(distance: Int? = null) = StoreDto(
    id = id, name = name, address = address,
    lat = lat, lng = lng, distance = distance,
    firstWinCount = firstWinCount, secondWinCount = secondWinCount
)
```

## 거리 기반 쿼리
```kotlin
@Query("""
    SELECT *, ST_Distance_Sphere(POINT(lng, lat), POINT(:lng, :lat)) AS distance
    FROM lotto_store
    WHERE ST_Distance_Sphere(POINT(lng, lat), POINT(:lng, :lat)) <= :radius
      AND lat IS NOT NULL AND lng IS NOT NULL
    ORDER BY distance
    LIMIT :limit
""", nativeQuery = true)
fun findNearby(
    @Param("lat") lat: Double,
    @Param("lng") lng: Double,
    @Param("radius") radius: Int,
    @Param("limit") limit: Int
): List<StoreDistanceProjection>

interface StoreDistanceProjection {
    fun getId(): Long
    fun getName(): String
    fun getLat(): Double?
    fun getLng(): Double?
    fun getDistance(): Double
    fun getFirstWinCount(): Int
    fun getSecondWinCount(): Int
}
```

## Redis 캐싱
```kotlin
@Cacheable(value = ["ranking"], key = "#region + ':' + #limit")
fun getRanking(region: String, limit: Int): List<StoreDto> { ... }

@CacheEvict(value = ["ranking"], allEntries = true)
@Scheduled(cron = "0 0 * * * *")
fun evictRankingCache() { }
```

## 예외 처리
```kotlin
@RestControllerAdvice
class GlobalExceptionHandler {
    @ExceptionHandler(IllegalArgumentException::class)
    fun handleBadRequest(e: IllegalArgumentException) =
        ResponseEntity.badRequest().body(ApiResponse.error<Nothing>(e.message ?: "잘못된 요청"))
}
```

## build.gradle.kts
```kotlin
plugins {
    kotlin("plugin.spring") version "..."
    kotlin("plugin.jpa") version "..."
}

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("org.springframework.boot:spring-boot-starter-data-redis")
    implementation("org.springframework.boot:spring-boot-starter-cache")
    implementation("org.springdoc:springdoc-openapi-starter-webmvc-ui:2.3.0")
    implementation("com.fasterxml.jackson.module:jackson-module-kotlin")
    implementation("org.jetbrains.kotlin:kotlin-reflect")
    runtimeOnly("com.mysql:mysql-connector-j")
}
```

## JPA + Kotlin 주의사항
- Entity는 `open class` 필요 → `plugin.jpa`가 자동 처리
- `data class`는 Entity로 사용 금지 (equals/hashCode 문제)
- `!!` 연산자 최소화, `?: throw` 패턴 사용
