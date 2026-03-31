-- Phase 454: StarRocks - SC2 MPP Analytical Data Warehouse
-- External tables, materialized views, colocate joins, player ranking.

-- ============================================================
-- Database setup
-- ============================================================

CREATE DATABASE IF NOT EXISTS sc2_warehouse;
USE sc2_warehouse;

-- ============================================================
-- Internal tables (Duplicate Key model for analytics)
-- ============================================================

CREATE TABLE IF NOT EXISTS games (
    game_id       VARCHAR(64)  NOT NULL,
    player_id     VARCHAR(64)  NOT NULL,
    opponent_id   VARCHAR(64),
    player_race   VARCHAR(16),
    opponent_race VARCHAR(16),
    map_name      VARCHAR(128),
    result        VARCHAR(8),
    apm           INT,
    mmr           INT,
    duration_sec  INT,
    played_at     DATETIME
)
DUPLICATE KEY(game_id, player_id)
DISTRIBUTED BY HASH(player_id) BUCKETS 8
PROPERTIES (
    "replication_num" = "1",
    "colocate_with" = "sc2_group"
);

CREATE TABLE IF NOT EXISTS players (
    player_id    VARCHAR(64)  NOT NULL,
    name         VARCHAR(128),
    race         VARCHAR(16),
    current_mmr  INT,
    peak_mmr     INT,
    total_games  INT,
    win_rate     DOUBLE,
    updated_at   DATETIME
)
UNIQUE KEY(player_id)
DISTRIBUTED BY HASH(player_id) BUCKETS 8
PROPERTIES (
    "replication_num" = "1",
    "colocate_with" = "sc2_group"
);

CREATE TABLE IF NOT EXISTS unit_stats (
    game_id    VARCHAR(64) NOT NULL,
    player_id  VARCHAR(64) NOT NULL,
    unit_name  VARCHAR(64),
    count_made INT,
    count_lost INT,
    game_date  DATE
)
DUPLICATE KEY(game_id, player_id, unit_name)
DISTRIBUTED BY HASH(player_id) BUCKETS 8;

-- ============================================================
-- External table: S3 replay archive
-- ============================================================

CREATE EXTERNAL TABLE IF NOT EXISTS ext_replay_archive (
    game_id       VARCHAR(64),
    replay_path   VARCHAR(512),
    file_size_mb  DOUBLE,
    uploaded_at   DATETIME
)
ENGINE = broker
PROPERTIES (
    "broker_name" = "hdfs_broker",
    "path" = "s3a://sc2-replays/archive/",
    "format" = "parquet",
    "hadoop.fs.s3a.access.key" = "${AWS_ACCESS_KEY}",
    "hadoop.fs.s3a.secret.key" = "${AWS_SECRET_KEY}"
);

-- ============================================================
-- Materialized View 1: Player ranking by win rate and MMR
-- ============================================================

CREATE MATERIALIZED VIEW mv_player_ranking
REFRESH ASYNC EVERY (INTERVAL 30 MINUTE)
AS
SELECT
    p.player_id,
    p.name,
    p.race,
    p.current_mmr,
    p.total_games,
    p.win_rate,
    RANK() OVER (ORDER BY p.current_mmr DESC)   AS mmr_rank,
    RANK() OVER (ORDER BY p.win_rate DESC)       AS winrate_rank,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY g.apm) AS median_apm
FROM players p
JOIN games g USING (player_id)
GROUP BY p.player_id, p.name, p.race, p.current_mmr, p.total_games, p.win_rate;

-- ============================================================
-- Materialized View 2: Build order frequency (top units by race)
-- ============================================================

CREATE MATERIALIZED VIEW mv_build_order_frequency
REFRESH ASYNC EVERY (INTERVAL 1 HOUR)
AS
SELECT
    g.player_race,
    u.unit_name,
    SUM(u.count_made)                                       AS total_made,
    SUM(u.count_lost)                                       AS total_lost,
    ROUND(SUM(u.count_made)::DOUBLE / NULLIF(COUNT(DISTINCT g.game_id), 0), 2) AS avg_per_game,
    COUNT(DISTINCT g.game_id)                               AS games_count
FROM unit_stats u
JOIN games g USING (game_id, player_id)
GROUP BY g.player_race, u.unit_name
ORDER BY total_made DESC;

-- ============================================================
-- Cross-game performance analysis query
-- ============================================================

SELECT
    g.player_race,
    g.opponent_race,
    COUNT(*)                                                AS matchups,
    SUM(CASE WHEN g.result = 'win' THEN 1 ELSE 0 END)      AS wins,
    ROUND(AVG(CASE WHEN g.result = 'win' THEN 1.0 ELSE 0 END), 4) AS win_rate,
    AVG(g.apm)                                             AS avg_apm,
    AVG(g.duration_sec) / 60.0                            AS avg_duration_min
FROM games g
WHERE played_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY g.player_race, g.opponent_race
ORDER BY matchups DESC;

-- ============================================================
-- Colocate join: player stats with recent games (no shuffle)
-- ============================================================

SELECT
    p.name,
    p.race,
    p.current_mmr,
    g.map_name,
    g.result,
    g.apm,
    g.played_at
FROM players p
JOIN games g ON p.player_id = g.player_id  -- colocated, same bucket
WHERE g.played_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
  AND p.current_mmr > 4000
ORDER BY g.played_at DESC
LIMIT 100;
