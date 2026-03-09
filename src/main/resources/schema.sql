-- -----------------------------------------------------------------------
-- LottoSpot DDL  (MySQL 8.0 기준)
-- spring.sql.init.mode=never 이므로 이 파일은 참조용이며
-- 실제 스키마 적용은 DBA 또는 flyway 로 수동 실행한다.
-- -----------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS lotto_store (
    id             BIGINT          AUTO_INCREMENT PRIMARY KEY,
    name           VARCHAR(100)    NOT NULL,
    address        VARCHAR(255)    NOT NULL,
    address_detail VARCHAR(100),
    lat            DECIMAL(10, 7)  NOT NULL,
    lng            DECIMAL(10, 7)  NOT NULL,
    location       POINT           NOT NULL SRID 4326,
    phone          VARCHAR(20),
    is_open        TINYINT(1)      DEFAULT 1,
    created_at     DATETIME        NOT NULL,
    updated_at     DATETIME        NOT NULL,
    SPATIAL INDEX idx_location (location)
);

CREATE TABLE IF NOT EXISTS winning_history (
    id         BIGINT    AUTO_INCREMENT PRIMARY KEY,
    store_id   BIGINT    NOT NULL,
    round      INT       NOT NULL,
    win_rank   TINYINT   NOT NULL,   -- 1: 1등(10점), 2: 2등(3점)
    win_date   DATE      NOT NULL,
    created_at DATETIME  NOT NULL,
    CONSTRAINT fk_wh_store        FOREIGN KEY (store_id) REFERENCES lotto_store (id),
    CONSTRAINT uk_store_round_rank UNIQUE (store_id, round, win_rank),
    INDEX idx_store_rank_date (store_id, win_rank, win_date)
);

-- -----------------------------------------------------------------------
-- 명당 스코어 계산 참고 쿼리
--
-- base_score = (1등횟수 × 10) + (2등횟수 × 3)
-- recency_bonus: 최근 2년 이내 1등 이력 있으면 base_score × 0.5 추가
-- -----------------------------------------------------------------------
