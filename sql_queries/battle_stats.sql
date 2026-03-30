-- SC2 Zerg Bot Battle Statistics Queries
-- Tracks win/loss records, unit performance, and build order efficiency

-- Win rate by matchup (ZvT, ZvP, ZvZ)
SELECT
    matchup,
    COUNT(*) AS total_games,
    SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) AS wins,
    ROUND(100.0 * SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) AS win_rate_pct
FROM battle_results
GROUP BY matchup
ORDER BY win_rate_pct DESC;

-- Unit loss analysis per game (average supply lost by unit type)
SELECT
    unit_type,
    COUNT(*) AS total_losses,
    ROUND(AVG(game_minute), 2) AS avg_death_minute,
    SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) AS losses_in_wins,
    SUM(CASE WHEN result = 'LOSS' THEN 1 ELSE 0 END) AS losses_in_losses
FROM unit_loss_log ul
JOIN battle_results br ON ul.game_id = br.game_id
GROUP BY unit_type
ORDER BY total_losses DESC;

-- Build order timing stats: hatch-first vs. pool-first
SELECT
    build_order_name,
    COUNT(*) AS games_played,
    ROUND(AVG(game_duration_seconds) / 60.0, 1) AS avg_game_minutes,
    ROUND(100.0 * SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) AS win_rate_pct
FROM battle_results
GROUP BY build_order_name
ORDER BY win_rate_pct DESC;

-- Recent 30-game performance trend
SELECT
    game_date,
    result,
    matchup,
    opponent_name,
    game_duration_seconds / 60 AS game_minutes,
    build_order_name
FROM battle_results
ORDER BY game_date DESC
LIMIT 30;

-- Drone saturation timing vs. win correlation
SELECT
    CASE
        WHEN drone_saturation_time_sec < 300  THEN 'Fast (<5 min)'
        WHEN drone_saturation_time_sec < 480  THEN 'Normal (5-8 min)'
        ELSE 'Slow (>8 min)'
    END AS saturation_bucket,
    COUNT(*) AS games,
    ROUND(100.0 * SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) AS win_rate_pct
FROM battle_results
WHERE drone_saturation_time_sec IS NOT NULL
GROUP BY saturation_bucket
ORDER BY win_rate_pct DESC;
