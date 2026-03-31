-- Phase 453: RisingWave - SC2 Streaming SQL Analytics
-- Materialized views with incremental computation from Kafka sources.

-- ============================================================
-- Sources: Kafka topics for SC2 game events
-- ============================================================

CREATE SOURCE sc2_game_events (
    game_id       VARCHAR,
    player_id     VARCHAR,
    player_race   VARCHAR,
    event_type    VARCHAR,   -- 'game_end', 'unit_created', 'building_started'
    result        VARCHAR,   -- 'win', 'loss', 'draw'
    apm           INT,
    mmr           INT,
    duration_sec  INT,
    map_name      VARCHAR,
    unit_name     VARCHAR,
    event_time    TIMESTAMPTZ
)
WITH (
    connector = 'kafka',
    topic = 'sc2-game-events',
    properties.bootstrap.server = 'localhost:9092',
    scan.startup.mode = 'earliest'
) FORMAT PLAIN ENCODE JSON;

CREATE SOURCE sc2_unit_events (
    game_id    VARCHAR,
    player_id  VARCHAR,
    unit_name  VARCHAR,
    event_type VARCHAR,   -- 'created', 'died'
    x          INT,
    y          INT,
    event_time TIMESTAMPTZ
)
WITH (
    connector = 'kafka',
    topic = 'sc2-unit-events',
    properties.bootstrap.server = 'localhost:9092',
    scan.startup.mode = 'earliest'
) FORMAT PLAIN ENCODE JSON;

-- ============================================================
-- Materialized View 1: Live Win Rate per Race (5-minute window)
-- ============================================================

CREATE MATERIALIZED VIEW live_win_rate AS
SELECT
    player_race,
    COUNT(*) FILTER (WHERE result = 'win')  AS wins,
    COUNT(*) FILTER (WHERE result = 'loss') AS losses,
    COUNT(*)                                AS total_games,
    ROUND(
        COUNT(*) FILTER (WHERE result = 'win')::NUMERIC / NULLIF(COUNT(*), 0),
        4
    ) AS win_rate,
    window_start,
    window_end
FROM TUMBLE(
    sc2_game_events,
    event_time,
    INTERVAL '5 minutes'
)
WHERE event_type = 'game_end'
GROUP BY player_race, window_start, window_end;

-- ============================================================
-- Materialized View 2: Current MMR Trend per Player (1-hour sliding)
-- ============================================================

CREATE MATERIALIZED VIEW current_mmr_trend AS
SELECT
    player_id,
    AVG(mmr)                       AS avg_mmr,
    MIN(mmr)                       AS min_mmr,
    MAX(mmr)                       AS max_mmr,
    LAST_VALUE(mmr) OVER (
        PARTITION BY player_id ORDER BY event_time
    )                              AS latest_mmr,
    COUNT(*)                       AS games_in_window,
    window_start,
    window_end
FROM HOP(
    sc2_game_events,
    event_time,
    INTERVAL '15 minutes',
    INTERVAL '1 hour'
)
WHERE event_type = 'game_end'
GROUP BY player_id, window_start, window_end;

-- ============================================================
-- Materialized View 3: Unit Survival Rate per Unit Type
-- ============================================================

CREATE MATERIALIZED VIEW unit_survival_rate AS
WITH unit_stats AS (
    SELECT
        unit_name,
        COUNT(*) FILTER (WHERE event_type = 'created') AS created_count,
        COUNT(*) FILTER (WHERE event_type = 'died')    AS died_count,
        window_start,
        window_end
    FROM TUMBLE(
        sc2_unit_events,
        event_time,
        INTERVAL '10 minutes'
    )
    GROUP BY unit_name, window_start, window_end
)
SELECT
    unit_name,
    created_count,
    died_count,
    ROUND(
        1.0 - (died_count::NUMERIC / NULLIF(created_count, 0)),
        4
    ) AS survival_rate,
    window_start,
    window_end
FROM unit_stats
WHERE created_count > 0
ORDER BY survival_rate DESC;

-- ============================================================
-- Materialized View 4: Build Order Frequency Analysis
-- ============================================================

CREATE MATERIALIZED VIEW build_order_frequency AS
SELECT
    player_race,
    unit_name  AS first_tech_unit,
    COUNT(*)   AS frequency,
    ROUND(
        COUNT(*)::NUMERIC / SUM(COUNT(*)) OVER (PARTITION BY player_race),
        4
    ) AS relative_frequency,
    window_start,
    window_end
FROM TUMBLE(
    sc2_unit_events,
    event_time,
    INTERVAL '30 minutes'
)
JOIN sc2_game_events USING (game_id, player_id)
WHERE sc2_unit_events.event_type = 'created'
GROUP BY player_race, unit_name, window_start, window_end;

-- ============================================================
-- Sink: Write win rate results back to Kafka
-- ============================================================

CREATE SINK sc2_win_rate_sink
FROM live_win_rate
WITH (
    connector = 'kafka',
    topic = 'sc2-win-rates',
    properties.bootstrap.server = 'localhost:9092'
) FORMAT PLAIN ENCODE JSON;
