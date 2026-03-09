# Project: lotto (LottoSpot — Spring Boot REST API)

## Stack
- Spring Boot 4.0.3 + Kotlin 2.2.21 + Java 21
- Build: Gradle with kotlin DSL (build.gradle.kts)
- Jakarta EE (jakarta.*) — NOT javax.*
- JPA: spring-boot-starter-data-jpa + MySQL (mysql-connector-j, runtimeOnly)
- Plugins: kotlin("plugin.spring"), kotlin("plugin.jpa") — both version 2.2.21

## Architecture
Clean layered architecture. Two parallel structures currently coexist:

```
com.example.lotto/
  # Legacy Todo API (in-memory, no JPA)
  model/          - Todo.kt
  dto/            - CreateTodoRequest, UpdateTodoRequest, TodoResponse
  repository/     - TodoRepository (interface) + InMemoryTodoRepository
  service/        - TodoService
  controller/     - TodoController (/api/todos)
  exception/      - TodoNotFoundException + GlobalExceptionHandler

  # LottoSpot domain (JPA, MySQL)
  domain/
    store/        - LottoStore.kt, LottoStoreRepository.kt
    winning/      - WinningHistory.kt, WinningHistoryRepository.kt
```

## JPA Entity Conventions
- Use `open class` (required for Hibernate proxies via allopen plugin)
- No `data class` for entities
- `@Column` with explicit snake_case name on every field
- `@Table(uniqueConstraints = [...])` for DB-level unique constraints
- LAZY fetch for all `@ManyToOne` associations

## Key Patterns
- `StoreDistanceProjection` interface for native query result mapping (Spring Data proxy)
- `LottoStore.updateScore(score)` mutates winScore + updatedAt atomically
- `findByStoreKey` used for upsert logic when syncing from external API
- `countByStoreIdAndWinRank` returns Int (not Long) to avoid caller-side casting

## DB / JPA Config
- ddl-auto: validate (schema managed via schema.sql, not Hibernate)
- DataSource credentials via env vars: DB_URL, DB_USERNAME, DB_PASSWORD
- show-sql=true (disable in production)

## Compiler Options
- `-Xjsr305=strict` for null safety with Spring annotations
- `-Xannotation-default-target=param-property` for Kotlin data class field annotations
