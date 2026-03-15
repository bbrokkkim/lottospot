-- -----------------------------------------------------------------------
-- LottoSpot DDL  (MySQL 8.0 기준)
-- spring.sql.init.mode=never 이므로 이 파일은 참조용이며
-- 실제 스키마 적용은 DBA 또는 flyway 로 수동 실행한다.
-- -----------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS lotto_store (
    id             BIGINT          AUTO_INCREMENT PRIMARY KEY,
    store_key      VARCHAR(50)     NOT NULL,
    name           VARCHAR(100)    NOT NULL,
    address        VARCHAR(255),
    address_detail VARCHAR(100),
    lat            DECIMAL(10, 7),
    lng            DECIMAL(10, 7),
    location       POINT           SRID 4326,
    sido           VARCHAR(20),
    sigungu        VARCHAR(30),
    phone          VARCHAR(20),
    is_open        TINYINT(1)      DEFAULT 1,
    created_at     DATETIME        NOT NULL DEFAULT NOW(),
    updated_at     DATETIME        NOT NULL DEFAULT NOW(),
    UNIQUE INDEX uk_store_key (store_key),
    SPATIAL INDEX idx_location (location)
);

-- -----------------------------------------------------------------------
-- 스키마 변경 이력 (기존 DB에 수동 적용)
-- ALTER TABLE lotto_store ADD COLUMN store_key VARCHAR(50) NOT NULL DEFAULT '' AFTER id;
-- ALTER TABLE lotto_store ADD UNIQUE INDEX uk_store_key (store_key);
-- ALTER TABLE lotto_store ADD COLUMN sido VARCHAR(20) AFTER lng;
-- ALTER TABLE lotto_store ADD COLUMN sigungu VARCHAR(30) AFTER sido;
-- ALTER TABLE lotto_store MODIFY COLUMN lat DECIMAL(10,7) NULL;
-- ALTER TABLE lotto_store MODIFY COLUMN lng DECIMAL(10,7) NULL;
-- ALTER TABLE lotto_store MODIFY COLUMN location POINT NULL;
-- ALTER TABLE lotto_store MODIFY COLUMN address VARCHAR(255) NULL;
-- ALTER TABLE lotto_store MODIFY COLUMN created_at DATETIME NOT NULL DEFAULT NOW();
-- ALTER TABLE lotto_store MODIFY COLUMN updated_at DATETIME NOT NULL DEFAULT NOW();
-- -----------------------------------------------------------------------

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
