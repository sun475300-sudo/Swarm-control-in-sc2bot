-- Phase 407: ClickHouse - SC2 Bot Analytics
-- ClickHouse OLAP schema and analytics queries for StarCraft II game statistics

-- ============================================================
-- Database
-- ============================================================

CREATE DATABASE IF NOT EXISTS sc2_analytics;

USE sc2_analytics;

-- ============================================================
-- Table: games (MergeTree)
-- One row per completed game
-- ============================================================

CREATE TABLE IF NOT EXISTS games
(
    game_id        UInt64,
    played_at      DateTime,
    map            LowCardinality(String),
    player_race    LowCardinality(String),
    opponent_race  LowCardinality(String),
    result         Enum8('Win' = 1, 'Loss' = 0),
    duration_sec   UInt16,
    apm            UInt16,
    mmr_before     Int16,
    mmr_after      Int16,
    mmr_change     Int8,
    game_loop      UInt32,
    supply_peak    UInt8,
    worker_peak    UInt8,
    army_value_max UInt32
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(played_at)
ORDER BY (played_at, player_race, opponent_race)
TTL played_at + INTERVAL 2 YEAR;

-- ============================================================
-- Table: unit_events (ReplacingMergeTree)
-- Unit creation and death events de-duplicated by event_id
-- ============================================================

CREATE TABLE IF NOT EXISTS unit_events
(
    event_id    UInt64,
    game_id     UInt64,
    game_loop   UInt32,
    event_time  DateTime,
    event_type  Enum8('created' = 1, 'died' = 2, 'morphed' = 3),
    unit_type   LowCardinality(String),
    team        Enum8('player' = 1, 'enemy' = 2),
    x           Float32,
    y           Float32,
    killer      LowCardinality(String) DEFAULT ''
)
ENGINE = ReplacingMergeTree(event_time)
PARTITION BY toYYYYMM(event_time)
ORDER BY (game_id, game_loop, event_id);

-- ============================================================
-- Table: player_stats (AggregatingMergeTree)
-- Pre-aggregated stats per player_race x opponent_race x map
-- ============================================================

CREATE TABLE IF NOT EXISTS player_stats
(
    player_race   LowCardinality(String),
    opponent_race LowCardinality(String),
    map           LowCardinality(String),
    stat_date     Date,
    wins_count    AggregateFunction(sum, UInt64),
    games_count   AggregateFunction(count, UInt64),
    avg_apm       AggregateFunction(avg, Float64),
    avg_duration  AggregateFunction(avg, Float64),
    mmr_change    AggregateFunction(sum, Int64)
)
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(stat_date)
ORDER BY (stat_date, player_race, opponent_race, map);

-- ============================================================
-- Materialized View: player_stats_mv
-- Auto-aggregates from games table inserts
-- ============================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS player_stats_mv
TO player_stats
AS
SELECT
    player_race,
    opponent_race,
    map,
    toDate(played_at)                        AS stat_date,
    sumState(toUInt64(result = 'Win'))        AS wins_count,
    countState()                             AS games_count,
    avgState(toFloat64(apm))                 AS avg_apm,
    avgState(toFloat64(duration_sec))        AS avg_duration,
    sumState(toInt64(mmr_change))            AS mmr_change
FROM games
GROUP BY player_race, opponent_race, map, stat_date;

-- ============================================================
-- Query 1: Win rate by race by map by time period
-- ============================================================

SELECT
    player_race,
    opponent_race,
    map,
    toStartOfWeek(played_at)                  AS week,
    countIf(result = 'Win')                   AS wins,
    count()                                   AS total,
    round(countIf(result = 'Win') / count() * 100, 1) AS win_rate_pct,
    avg(mmr_change)                           AS avg_mmr_delta
FROM games
WHERE played_at >= now() - INTERVAL 90 DAY
GROUP BY player_race, opponent_race, map, week
ORDER BY week DESC, win_rate_pct DESC;

-- ============================================================
-- Query 2: APM distribution histogram
-- ============================================================

SELECT
    multiIf(
        apm < 100, '< 100',
        apm < 150, '100-150',
        apm < 200, '150-200',
        apm < 250, '200-250',
        apm < 300, '250-300',
        '>= 300'
    )                    AS apm_bucket,
    count()              AS game_count,
    round(avg(apm), 1)   AS avg_apm_in_bucket,
    round(countIf(result = 'Win') / count() * 100, 1) AS win_rate_pct
FROM games
GROUP BY apm_bucket
ORDER BY min(apm);

-- ============================================================
-- Query 3: Build order frequency analysis
-- Most common first 5 units built per race matchup
-- ============================================================

SELECT
    g.player_race,
    g.opponent_race,
    u.unit_type,
    count()                                           AS times_built,
    round(countIf(g.result = 'Win') / count() * 100, 1) AS unit_win_rate_pct,
    avg(u.game_loop)                                  AS avg_build_loop
FROM unit_events u
JOIN games g ON u.game_id = g.game_id
WHERE u.event_type = 'created'
  AND u.team = 'player'
  AND u.game_loop <= 2240   -- first 2 minutes of game
GROUP BY g.player_race, g.opponent_race, u.unit_type
HAVING count() >= 10
ORDER BY g.player_race, g.opponent_race, times_built DESC;

-- ============================================================
-- Query 4: MMR progression over time
-- ============================================================

SELECT
    toDate(played_at)   AS game_date,
    max(mmr_after)      AS peak_mmr,
    min(mmr_after)      AS low_mmr,
    avg(mmr_after)      AS avg_mmr,
    sum(mmr_change)     AS daily_mmr_delta,
    count()             AS games_played
FROM games
GROUP BY game_date
ORDER BY game_date;

-- ============================================================
-- Query 5: Top units by kill participation
-- ============================================================

SELECT
    unit_type,
    team,
    countIf(event_type = 'created') AS spawned,
    countIf(event_type = 'died')    AS died,
    countIf(killer != '')           AS kills,
    round(countIf(event_type = 'died') /
          nullIf(countIf(event_type = 'created'), 0) * 100, 1) AS mortality_pct
FROM unit_events
GROUP BY unit_type, team
ORDER BY spawned DESC
LIMIT 20;
