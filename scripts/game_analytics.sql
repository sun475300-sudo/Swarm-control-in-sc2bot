-- StarCraft II AI Analytics Dashboard - SQL Schema
-- P78: Game Data Analysis Dashboard

-- Drop existing objects
DROP TABLE IF EXISTS game_events CASCADE;
DROP TABLE IF EXISTS unit_positions CASCADE;
DROP TABLE IF EXISTS resource_gathering CASCADE;
DROP TABLE IF EXISTS combat_stats CASCADE;
DROP TABLE IF EXISTS match_history CASCADE;
DROP TABLE IF EXISTS player_profiles CASCADE;
DROP TABLE IF EXISTS replay_metadata CASCADE;
DROP TABLE IF EXISTS decision_logs CASCADE;
DROP VIEW IF EXISTS unit_composition_summary CASCADE;
DROP VIEW IF EXISTS game_timeline CASCADE;
DROP VIEW IF EXISTS combat_effectiveness CASCADE;
DROP VIEW IF EXISTS economic_analysis CASCADE;
DROP FUNCTION IF EXISTS calculate_damage_dealt CASCADE;
DROP FUNCTION IF EXISTS update_match_stats CASCADE;

-- Player Profiles
CREATE TABLE player_profiles (
    player_id SERIAL PRIMARY KEY,
    player_name VARCHAR(64) NOT NULL UNIQUE,
    race VARCHAR(16) NOT NULL CHECK (race IN ('ZERG', 'TERRAN', 'PROTOSS', 'RANDOM')),
    mmr INTEGER DEFAULT 0,
    games_played INTEGER DEFAULT 0,
    games_won INTEGER DEFAULT 0,
    win_rate DECIMAL(5,2) GENERATED ALWAYS AS (
        CASE WHEN games_played > 0 
             THEN (games_won::DECIMAL / games_played) * 100 
             ELSE 0 
        END
    ) STORED,
    avg_game_duration_seconds INTEGER,
    favorite_build VARCHAR(128),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_player_mmr ON player_profiles(mmr DESC);
CREATE INDEX idx_player_winrate ON player_profiles(win_rate DESC);

-- Replay Metadata
CREATE TABLE replay_metadata (
    replay_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id INTEGER REFERENCES player_profiles(player_id),
    map_name VARCHAR(256),
    map_size VARCHAR(32),
    game_speed VARCHAR(16) DEFAULT 'FASTER',
    game_duration_frames INTEGER,
    game_duration_seconds INTEGER GENERATED ALWAYS AS (game_duration_frames / 22.4) STORED,
    game_result VARCHAR(8) CHECK (game_result IN ('WIN', 'LOSS', 'DRAW')),
    opponent_race VARCHAR(16),
    opponent_name VARCHAR(64),
    opponent_mmr INTEGER,
    game_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    replay_file_path VARCHAR(512),
    api_version VARCHAR(32),
    ladder_season INTEGER
);

CREATE INDEX idx_replay_date ON replay_metadata(game_date DESC);
CREATE INDEX idx_replay_result ON replay_metadata(game_result);

-- Unit Positions (time-series data)
CREATE TABLE unit_positions (
    position_id BIGSERIAL PRIMARY KEY,
    replay_id UUID REFERENCES replay_metadata(replay_id),
    frame_number INTEGER NOT NULL,
    unit_id INTEGER NOT NULL,
    unit_type VARCHAR(32) NOT NULL,
    unit_name VARCHAR(64),
    position_x FLOAT NOT NULL,
    position_y FLOAT NOT NULL,
    health DECIMAL(6,2),
    health_max DECIMAL(6,2),
    energy DECIMAL(6,2),
    mineral_cost INTEGER,
    vespene_cost INTEGER,
    is_visible BOOLEAN DEFAULT TRUE,
    owner_player_id INTEGER,
    weapon_cooldown_frames INTEGER,
    is_burrowed BOOLEAN DEFAULT FALSE,
    cached_position GEOGRAPHY(POINT, 4326)
);

CREATE INDEX idx_position_replay ON unit_positions(replay_id);
CREATE INDEX idx_position_frame ON unit_positions(frame_number);
CREATE INDEX idx_position_type ON unit_positions(unit_type);
CREATE INDEX idx_position_player ON unit_positions(owner_player_id);
CREATE INDEX idx_position_time ON unit_positions(replay_id, frame_number);

-- Game Events (discrete events)
CREATE TABLE game_events (
    event_id BIGSERIAL PRIMARY KEY,
    replay_id UUID REFERENCES replay_metadata(replay_id),
    frame_number INTEGER NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    event_data JSONB,
    source_unit_id INTEGER,
    target_unit_id INTEGER,
    location_x FLOAT,
    location_y FLOAT,
    mineral_cost INTEGER,
    vespene_cost INTEGER,
    supply_used DECIMAL(4,1),
    supply_provided DECIMAL(4,1),
    game_time_seconds INTEGER GENERATED ALWAYS AS (frame_number / 22.4) STORED
);

CREATE INDEX idx_event_replay ON game_events(replay_id);
CREATE INDEX idx_event_type ON game_events(event_type);
CREATE INDEX idx_event_time ON game_events(frame_number);
CREATE INDEX idx_event_data ON game_events USING GIN(event_data);

-- Resource Gathering
CREATE TABLE resource_gathering (
    gather_id BIGSERIAL PRIMARY KEY,
    replay_id UUID REFERENCES replay_metadata(replay_id),
    frame_number INTEGER NOT NULL,
    player_id INTEGER REFERENCES player_profiles(player_id),
    minerals_current INTEGER NOT NULL,
    vespene_current INTEGER NOT NULL,
    minerals_collection_rate DECIMAL(7,2),
    vespene_collection_rate DECIMAL(7,2),
    workers_active INTEGER,
    workers_idle INTEGER,
    bases_owned INTEGER,
    gas_geysers_used INTEGER,
    supply_used DECIMAL(4,1),
    supply_cap DECIMAL(4,1),
    army_supply DECIMAL(4,1),
    worker_supply DECIMAL(4,1)
);

CREATE INDEX idx_gather_replay ON resource_gathering(replay_id);
CREATE INDEX idx_gather_time ON resource_gathering(frame_number);

-- Combat Stats
CREATE TABLE combat_stats (
    combat_id BIGSERIAL PRIMARY KEY,
    replay_id UUID REFERENCES replay_metadata(replay_id),
    frame_number INTEGER NOT NULL,
    attacker_id INTEGER,
    defender_id INTEGER,
    damage_dealt DECIMAL(8,2),
    damage_taken DECIMAL(8,2),
    attacker_unit_type VARCHAR(32),
    defender_unit_type VARCHAR(32,
    attack_type VARCHAR(32),
    result VARCHAR(16) CHECK (result IN ('KILL', 'DAMAGE', 'MISS', 'EVADE')),
    is_critical BOOLEAN DEFAULT FALSE,
    distance_between FLOAT,
    position_x FLOAT,
    position_y FLOAT
);

CREATE INDEX idx_combat_replay ON combat_stats(replay_id);
CREATE INDEX idx_combat_units ON combat_stats(attacker_id, defender_id);

-- Decision Logs (AI decision tracking)
CREATE TABLE decision_logs (
    decision_id BIGSERIAL PRIMARY KEY,
    replay_id UUID REFERENCES replay_metadata(replay_id),
    frame_number INTEGER NOT NULL,
    decision_type VARCHAR(64) NOT NULL,
    decision_score DECIMAL(8,4),
    chosen_action JSONB,
    alternative_actions JSONB,
    state_embedding VECTOR(128),
    policy_probs JSONB,
    game_phase VARCHAR(32),
    strategic_importance DECIMAL(3,2),
    execution_time_ms INTEGER
);

CREATE INDEX idx_decision_replay ON decision_logs(replay_id);
CREATE INDEX idx_decision_type ON decision_logs(decision_type);
CREATE INDEX idx_decision_time ON decision_logs(frame_number);
CREATE INDEX idx_decision_state ON decision_logs USING HNSW(state_embedding vector_cosine_ops);

-- VIEWS

-- Unit Composition Summary
CREATE VIEW unit_composition_summary AS
SELECT 
    rm.replay_id,
    rm.game_result,
    up.unit_type,
    COUNT(*) as unit_count,
    AVG(up.health) as avg_health,
    AVG(up.health_max) as avg_max_health,
    COUNT(DISTINCT up.unit_id) as unique_units,
    MIN(up.frame_number) as first_spawn_frame,
    MAX(up.frame_number) as last_seen_frame
FROM replay_metadata rm
JOIN unit_positions up ON rm.replay_id = up.replay_id
GROUP BY rm.replay_id, rm.game_result, up.unit_type;

-- Game Timeline
CREATE VIEW game_timeline AS
WITH event_aggregates AS (
    SELECT 
        replay_id,
        frame_number,
        event_type,
        COUNT(*) as event_count,
        COUNT(DISTINCT source_unit_id) as units_involved,
        SUM(mineral_cost) as total_minerals,
        SUM(vespene_cost) as total_gas,
        SUM(supply_used) as total_supply_used
    FROM game_events
    WHERE event_data IS NOT NULL
    GROUP BY replay_id, frame_number, event_type
)
SELECT 
    replay_id,
    frame_number,
    game_duration_seconds,
    event_type,
    event_count,
    units_involved,
    total_minerals,
    total_gas,
    total_supply_used,
    LAG(event_count) OVER w as prev_event_count,
    SUM(event_count) OVER w as cumulative_events
FROM event_aggregates
WINDOW w AS (PARTITION BY replay_id ORDER BY frame_number);

-- Combat Effectiveness
CREATE VIEW combat_effectiveness AS
SELECT 
    rm.replay_id,
    rm.game_result,
    cs.attacker_unit_type,
    cs.defender_unit_type,
    COUNT(*) as total_attacks,
    SUM(cs.damage_dealt) as total_damage,
    AVG(cs.damage_dealt) as avg_damage,
    COUNT(CASE WHEN cs.result = 'KILL' THEN 1 END) as kills,
    AVG(CASE WHEN cs.result = 'KILL' THEN 1.0 ELSE 0.0 END) as kill_rate,
    AVG(cs.distance_between) as avg_distance
FROM combat_stats cs
JOIN replay_metadata rm ON cs.replay_id = rm.replay_id
GROUP BY rm.replay_id, rm.game_result, cs.attacker_unit_type, cs.defender_unit_type;

-- Economic Analysis
CREATE VIEW economic_analysis AS
SELECT 
    rm.replay_id,
    rm.game_result,
    rg.frame_number,
    rg.game_duration_seconds,
    rg.minerals_current,
    rg.vespene_current,
    rg.minerals_collection_rate,
    rg.vespene_collection_rate,
    rg.workers_active,
    rg.bases_owned,
    rm.game_duration_seconds as total_game_time,
    LAG(rg.minerals_current) OVER w as prev_minerals,
    LAG(rg.vespene_current) OVER w as prev_vespene
FROM resource_gathering rg
JOIN replay_metadata rm ON rg.replay_id = rm.replay_id
WINDOW w AS (PARTITION BY rg.replay_id ORDER BY rg.frame_number);

-- FUNCTIONS

-- Calculate damage dealt by unit type
CREATE OR REPLACE FUNCTION calculate_damage_dealt(
    p_replay_id UUID,
    p_unit_type VARCHAR
) RETURNS DECIMAL AS $$
DECLARE
    v_total DECIMAL;
BEGIN
    SELECT COALESCE(SUM(damage_dealt), 0)
    INTO v_total
    FROM combat_stats
    WHERE replay_id = p_replay_id 
      AND attacker_unit_type = p_unit_type;
    
    RETURN v_total;
END;
$$ LANGUAGE plpgsql;

-- Update match statistics
CREATE OR REPLACE FUNCTION update_match_stats(
    p_replay_id UUID,
    p_game_result VARCHAR
) RETURNS VOID AS $$
DECLARE
    v_player_id INTEGER;
    v_duration INTEGER;
BEGIN
    SELECT player_id, game_duration_seconds
    INTO v_player_id, v_duration
    FROM replay_metadata
    WHERE replay_id = p_replay_id;
    
    IF v_player_id IS NULL THEN
        RETURN;
    END IF;
    
    UPDATE player_profiles
    SET 
        games_played = games_played + 1,
        games_won = games_won + CASE WHEN p_game_result = 'WIN' THEN 1 ELSE 0 END,
        avg_game_duration_seconds = (
            SELECT AVG(game_duration_seconds) 
            FROM replay_metadata 
            WHERE player_id = v_player_id
        ),
        updated_at = CURRENT_TIMESTAMP
    WHERE player_id = v_player_id;
END;
$$ LANGUAGE plpgsql;

-- Trigger for auto-updating player stats
CREATE TRIGGER trigger_update_stats
AFTER INSERT ON replay_metadata
FOR EACH ROW
EXECUTE FUNCTION update_match_stats(replay_id, game_result);

-- MATERIALIZED VIEW for fast analytics
CREATE MATERIALIZED VIEW mv_unit_winrates AS
SELECT 
    up.unit_type,
    COUNT(*) as total_spawns,
    COUNT(CASE WHEN rm.game_result = 'WIN' THEN 1 END) as wins,
    COUNT(CASE WHEN rm.game_result = 'LOSS' THEN 1 END) as losses,
    CASE 
        WHEN COUNT(*) > 0 
        THEN (COUNT(CASE WHEN rm.game_result = 'WIN' THEN 1 END)::DECIMAL / COUNT(*)) * 100
        ELSE 0 
    END as win_rate,
    AVG(up.health) as avg_survival_health
FROM unit_positions up
JOIN replay_metadata rm ON up.replay_id = rm.replay_id
GROUP BY up.unit_type;

CREATE UNIQUE INDEX idx_mv_unit_winrates ON mv_unit_winrates(unit_type);

-- Partitioning example (for large datasets)
-- ALTER TABLE unit_positions SET (
--    timescaledb.transaction_compression='ON',
--    timescaledb.compress_segmentby='replay_id'
-- );
-- SELECT add_continuous_aggregate_policy('unit_composition_summary',
--    start_offset => INTERVAL '1 week',
--    end_offset => INTERVAL '1 hour',
--    schedule_interval => INTERVAL '1 hour');

-- Sample queries for dashboard

-- 1. Win rate by unit composition
-- SELECT unit_type, win_rate FROM mv_unit_winrates ORDER BY total_spawns DESC LIMIT 10;

-- 2. Resource timing analysis
-- SELECT game_duration_seconds, minerals_collection_rate, vespene_collection_rate
-- FROM economic_analysis
-- WHERE frame_number IN (0, 1100, 2200, 3300, 4400)
-- ORDER BY game_duration_seconds;

-- 3. Combat effectiveness heatmap
-- SELECT attacker_unit_type, defender_unit_type, avg_damage, kill_rate
-- FROM combat_effectiveness
-- WHERE total_attacks > 10
-- ORDER BY avg_damage DESC;

-- 4. Decision quality over time
-- SELECT 
--     game_phase,
--     decision_type,
--     AVG(decision_score) as avg_score,
--     AVG(execution_time_ms) as avg_exec_time
-- FROM decision_logs
-- GROUP BY game_phase, decision_type
-- ORDER BY game_phase, avg_score DESC;
