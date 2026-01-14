BEGIN;

DROP TABLE IF EXISTS dino_refs CASCADE;
DROP TABLE IF EXISTS servers CASCADE;

CREATE TABLE dino_refs
(
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(255) UNIQUE NOT NULL,
    href         TEXT                NOT NULL,
    page_name    TEXT                NOT NULL,
    scraped_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dino_name ON dino_refs (name);

CREATE TABLE servers
(
    id             BIGINT UNIQUE PRIMARY KEY,
    channel_id     BIGINT,
    scheduled_time TIME,
    time_zone      VARCHAR(30),
    added_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    edited_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_server_id ON servers (id);

COMMIT;