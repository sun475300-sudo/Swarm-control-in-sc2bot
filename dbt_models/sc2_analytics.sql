-- Phase 578: dbt Models
-- SC2 Bot Analytics — dbt Model Definitions
-- All models in one file, separated by section comments.
-- Deploy individual blocks as separate .sql files in models/ subdirectories.
-- Jinja templating: {{ ref('...') }}, {{ config(...) }}, {{ source(...) }}
-- ============================================================


-- ============================================================
-- STAGING LAYER
-- models/staging/stg_games.sql
-- ============================================================

{{
  config(
    materialized = 'view',
    schema       = 'staging',
    tags         = ['sc2', 'staging', 'games'],
    description  = 'Staging view for raw SC2 game records. Casts types and applies naming conventions.'
  )
}}

/*
  Docs block — used by dbt docs generate
  {% docs stg_games %}
  Staging model for the sc2_games source table.
  Applies type casting, renames columns to snake_case, and removes
  records without a valid game_id.
  {% enddocs %}
*/

with source as (

    select * from {{ source('sc2_raw', 'games') }}

),

renamed as (

    select
        cast(game_id        as varchar(64))  as game_id,
        cast(played_at      as timestamp)    as played_at,
        cast(map_name       as varchar(128)) as map_name,
        upper(trim(race))                    as race,            -- 'TERRAN','ZERG','PROTOSS'
        upper(trim(opponent_race))           as opponent_race,
        lower(trim(result))                  as result,          -- 'win','loss','draw'
        cast(duration_seconds as integer)    as duration_seconds,
        cast(apm              as integer)    as apm,
        cast(is_ladder        as boolean)    as is_ladder,
        cast(league_tier      as varchar(32)) as league_tier,
        current_timestamp                    as _loaded_at

    from source

),

validated as (

    select *
    from renamed
    where game_id is not null
      and result   in ('win', 'loss', 'draw')
      and race     in ('TERRAN', 'ZERG', 'PROTOSS')
      and duration_seconds > 0

)

select * from validated


-- ============================================================
-- STAGING LAYER
-- models/staging/stg_replays.sql
-- ============================================================

{{
  config(
    materialized = 'view',
    schema       = 'staging',
    tags         = ['sc2', 'staging', 'replays'],
    description  = 'Staging view for SC2 replay telemetry records.'
  )
}}

with source as (

    select * from {{ source('sc2_raw', 'replays') }}

),

cast_types as (

    select
        cast(replay_id              as varchar(64))  as replay_id,
        cast(game_id                as varchar(64))  as game_id,
        cast(minerals_collected     as integer)      as minerals_collected,
        cast(gas_collected          as integer)      as gas_collected,
        cast(army_supply_peak       as integer)      as army_supply_peak,
        cast(workers_created        as integer)      as workers_created,
        cast(structures_built       as integer)      as structures_built,
        cast(units_lost             as integer)      as units_lost,
        cast(units_killed           as integer)      as units_killed,
        cast(inject_efficiency      as numeric(5,4)) as inject_efficiency,
        cast(first_attack_time_s    as integer)      as first_attack_time_s,
        cast(expansion_count        as integer)      as expansion_count,
        current_timestamp                            as _loaded_at

    from source

),

deduplicated as (

    select *,
        row_number() over (
            partition by game_id
            order by _loaded_at desc
        ) as _row_num

    from cast_types

)

select * from deduplicated
where _row_num = 1


-- ============================================================
-- INTERMEDIATE LAYER
-- models/intermediate/int_game_metrics.sql
-- ============================================================

{{
  config(
    materialized = 'table',
    schema       = 'intermediate',
    tags         = ['sc2', 'intermediate', 'metrics'],
    description  = 'Joined game + replay data with derived economy and combat metrics.'
  )
}}

with games as (

    select * from {{ ref('stg_games') }}

),

replays as (

    select * from {{ ref('stg_replays') }}

),

joined as (

    select
        g.game_id,
        g.played_at,
        g.map_name,
        g.race,
        g.opponent_race,
        g.result,
        g.duration_seconds,
        g.apm,
        g.is_ladder,
        g.league_tier,

        r.minerals_collected,
        r.gas_collected,
        r.army_supply_peak,
        r.workers_created,
        r.structures_built,
        r.units_lost,
        r.units_killed,
        r.inject_efficiency,
        r.first_attack_time_s,
        r.expansion_count,

        -- Derived metrics
        case when g.result = 'win' then 1 else 0 end                     as is_win,

        -- Resource efficiency: resources per second
        round(
            (r.minerals_collected + r.gas_collected)::numeric
            / nullif(g.duration_seconds, 0), 2
        )                                                                 as resources_per_second,

        -- Combat ratio
        round(
            r.units_killed::numeric
            / nullif(r.units_lost, 0), 3
        )                                                                 as kill_loss_ratio,

        -- Economy index (workers × expand count normalized by duration)
        round(
            (r.workers_created * (1 + r.expansion_count))::numeric
            / nullif(g.duration_seconds / 60.0, 0), 2
        )                                                                 as economy_index,

        -- Aggression flag: first attack before 5 minutes
        r.first_attack_time_s < 300                                       as is_early_aggression

    from games g
    left join replays r
        on g.game_id = r.game_id

)

select * from joined


-- ============================================================
-- FACT LAYER
-- models/marts/fct_matchup_stats.sql
-- ============================================================

{{
  config(
    materialized = 'table',
    schema       = 'marts',
    indexes      = [
      {'columns': ['race', 'opponent_race'], 'unique': false},
      {'columns': ['map_name'], 'unique': false}
    ],
    tags         = ['sc2', 'fact', 'matchup'],
    description  = 'Aggregated win/loss statistics by race matchup and map.'
  )
}}

with base as (

    select * from {{ ref('int_game_metrics') }}

),

matchup_agg as (

    select
        race,
        opponent_race,
        map_name,

        count(*)                                            as total_games,
        sum(is_win)                                         as wins,
        sum(1 - is_win)                                     as losses,

        round(avg(is_win::numeric), 4)                      as win_rate,

        round(avg(duration_seconds) / 60.0, 2)             as avg_duration_min,
        round(avg(apm), 1)                                  as avg_apm,
        round(avg(resources_per_second), 2)                 as avg_resources_ps,
        round(avg(kill_loss_ratio), 3)                      as avg_kl_ratio,
        round(avg(economy_index), 2)                        as avg_economy_index,

        sum(case when is_early_aggression then 1 else 0 end) as early_aggression_games,
        round(
            avg(case when is_early_aggression then is_win::numeric end), 4
        )                                                   as early_aggr_win_rate,

        -- Rolling 20-game win rate using window function
        round(
            avg(is_win::numeric) over (
                partition by race, opponent_race
                order by min(played_at)
                rows between 19 preceding and current row
            ), 4
        )                                                   as rolling_20_win_rate,

        min(played_at)                                      as first_game_at,
        max(played_at)                                      as last_game_at

    from base
    group by race, opponent_race, map_name

)

select
    {{ dbt_utils.generate_surrogate_key(['race', 'opponent_race', 'map_name']) }} as matchup_map_sk,
    *
from matchup_agg


-- ============================================================
-- FACT LAYER
-- models/marts/fct_build_order_performance.sql
-- ============================================================

{{
  config(
    materialized = 'incremental',
    schema       = 'marts',
    unique_key   = 'build_slot_id',
    on_schema_change = 'sync_all_columns',
    tags         = ['sc2', 'fact', 'build_order'],
    description  = 'Win rate analysis broken down by game duration bracket (build order proxy).'
  )
}}

with metrics as (

    select * from {{ ref('int_game_metrics') }}

    {% if is_incremental() %}
    -- Only process new records on incremental runs
    where played_at > (select max(played_at) from {{ this }})
    {% endif %}

),

bracketed as (

    select *,
        case
            when duration_seconds < 300  then '01_early_all_in_0_5min'
            when duration_seconds < 600  then '02_early_aggression_5_10min'
            when duration_seconds < 900  then '03_mid_game_10_15min'
            when duration_seconds < 1200 then '04_late_mid_15_20min'
            when duration_seconds < 1800 then '05_macro_20_30min'
            else                              '06_ultra_macro_30min_plus'
        end                                                   as duration_bracket,

        -- Supply army tier
        case
            when army_supply_peak < 50  then 'low'
            when army_supply_peak < 120 then 'medium'
            when army_supply_peak < 180 then 'high'
            else                             'maxed'
        end                                                   as army_tier

    from metrics

),

agg as (

    select
        race,
        opponent_race,
        duration_bracket,
        army_tier,

        count(*)                              as total_games,
        sum(is_win)                           as wins,
        round(avg(is_win::numeric), 4)        as win_rate,
        round(avg(apm), 1)                    as avg_apm,
        round(avg(army_supply_peak), 1)       as avg_army_supply,
        round(avg(economy_index), 2)          as avg_economy_index,
        round(avg(kill_loss_ratio), 3)        as avg_kl_ratio,
        round(stddev(duration_seconds), 1)    as stddev_duration,
        current_timestamp                     as calculated_at

    from bracketed
    group by race, opponent_race, duration_bracket, army_tier

)

select
    {{ dbt_utils.generate_surrogate_key(
        ['race', 'opponent_race', 'duration_bracket', 'army_tier']
    ) }}                                     as build_slot_id,
    *
from agg


-- ============================================================
-- DIMENSION LAYER
-- models/marts/dim_maps.sql
-- ============================================================

{{
  config(
    materialized = 'table',
    schema       = 'marts',
    tags         = ['sc2', 'dimension', 'maps'],
    description  = 'Dimension table for SC2 map metadata and derived performance attributes.'
  )
}}

with map_games as (

    select
        map_name,
        count(*)                                 as total_games,
        round(avg(is_win::numeric), 4)           as overall_win_rate,
        round(avg(duration_seconds) / 60.0, 2)  as avg_game_duration_min,
        round(avg(army_supply_peak), 1)          as avg_army_peak,
        round(avg(resources_per_second), 2)      as avg_resources_ps,
        min(played_at)                           as first_seen_at,
        max(played_at)                           as last_seen_at

    from {{ ref('int_game_metrics') }}
    group by map_name

),

map_attributes as (

    select
        map_name,
        -- Infer map characteristics from aggregate behaviour
        case
            when avg_game_duration_min < 8  then 'rush_favored'
            when avg_game_duration_min < 15 then 'aggressive'
            when avg_game_duration_min < 20 then 'balanced'
            else                                 'macro_favored'
        end                                       as map_style,

        case
            when overall_win_rate >= 0.6  then 'strong'
            when overall_win_rate >= 0.45 then 'neutral'
            else                               'weak'
        end                                       as bot_performance_tier,

        total_games,
        overall_win_rate,
        avg_game_duration_min,
        avg_army_peak,
        avg_resources_ps,
        first_seen_at,
        last_seen_at

    from map_games

)

select
    {{ dbt_utils.generate_surrogate_key(['map_name']) }} as map_sk,
    *
from map_attributes
order by overall_win_rate desc


-- ============================================================
-- DIMENSION LAYER
-- models/marts/dim_strategies.sql
-- ============================================================

{{
  config(
    materialized = 'table',
    schema       = 'marts',
    tags         = ['sc2', 'dimension', 'strategy'],
    description  = 'Derived strategy dimension based on economy/army/timing signatures.'
  )
}}

with game_metrics as (

    select * from {{ ref('int_game_metrics') }}

),

strategy_classification as (

    select
        game_id,
        race,
        opponent_race,
        is_win,

        -- Strategy label derived from observable signatures
        case
            when is_early_aggression
                 and army_supply_peak > 80         then 'early_all_in'
            when is_early_aggression
                 and army_supply_peak <= 80        then 'cheese_rush'
            when not is_early_aggression
                 and economy_index > 8
                 and expansion_count >= 3          then 'macro_economy'
            when not is_early_aggression
                 and army_supply_peak > 150        then 'army_timing_attack'
            when inject_efficiency > 0.85
                 and workers_created > 70          then 'drone_heavy_economy'
            else                                        'standard_play'
        end                                        as strategy_label,

        economy_index,
        inject_efficiency,
        kill_loss_ratio,
        army_supply_peak,
        expansion_count

    from game_metrics

),

strategy_agg as (

    select
        race,
        opponent_race,
        strategy_label,

        count(*)                              as total_games,
        sum(is_win)                           as wins,
        round(avg(is_win::numeric), 4)        as win_rate,
        round(avg(economy_index), 2)          as avg_economy_index,
        round(avg(inject_efficiency), 4)      as avg_inject_efficiency,
        round(avg(kill_loss_ratio), 3)        as avg_kl_ratio,
        round(avg(army_supply_peak), 1)       as avg_army_peak,

        -- Rank strategy by win rate within race matchup
        rank() over (
            partition by race, opponent_race
            order by avg(is_win::numeric) desc
        )                                     as win_rate_rank

    from strategy_classification
    group by race, opponent_race, strategy_label

)

select
    {{ dbt_utils.generate_surrogate_key(['race', 'opponent_race', 'strategy_label']) }} as strategy_sk,
    *
from strategy_agg
order by race, opponent_race, win_rate_rank


-- ============================================================
-- DBT TESTS
-- tests/sc2_analytics_tests.yml
-- (Embed as YAML comment for reference — copy to tests/ directory)
-- ============================================================

/*
version: 2

models:
  - name: stg_games
    description: "Staging layer for raw SC2 game records"
    columns:
      - name: game_id
        description: "Unique identifier for each game"
        tests:
          - unique
          - not_null
      - name: result
        tests:
          - not_null
          - accepted_values:
              values: ['win', 'loss', 'draw']
      - name: race
        tests:
          - accepted_values:
              values: ['TERRAN', 'ZERG', 'PROTOSS']
      - name: duration_seconds
        tests:
          - not_null
          - dbt_utils.expression_is_true:
              expression: "duration_seconds > 0"

  - name: stg_replays
    columns:
      - name: replay_id
        tests:
          - unique
          - not_null
      - name: game_id
        tests:
          - not_null
          - relationships:
              to: ref('stg_games')
              field: game_id
      - name: inject_efficiency
        tests:
          - dbt_utils.expression_is_true:
              expression: "inject_efficiency between 0 and 1"

  - name: int_game_metrics
    columns:
      - name: game_id
        tests:
          - unique
          - not_null
      - name: is_win
        tests:
          - accepted_values:
              values: [0, 1]

  - name: fct_matchup_stats
    columns:
      - name: matchup_map_sk
        tests:
          - unique
          - not_null
      - name: win_rate
        tests:
          - dbt_utils.expression_is_true:
              expression: "win_rate between 0 and 1"
      - name: total_games
        tests:
          - dbt_utils.expression_is_true:
              expression: "total_games >= 0"

  - name: fct_build_order_performance
    columns:
      - name: build_slot_id
        tests:
          - unique
          - not_null

  - name: dim_maps
    columns:
      - name: map_sk
        tests:
          - unique
          - not_null
      - name: map_name
        tests:
          - unique
          - not_null
      - name: bot_performance_tier
        tests:
          - accepted_values:
              values: ['strong', 'neutral', 'weak']

  - name: dim_strategies
    columns:
      - name: strategy_sk
        tests:
          - unique
          - not_null
      - name: strategy_label
        tests:
          - not_null
          - accepted_values:
              values:
                - 'early_all_in'
                - 'cheese_rush'
                - 'macro_economy'
                - 'army_timing_attack'
                - 'drone_heavy_economy'
                - 'standard_play'

sources:
  - name: sc2_raw
    description: "Raw SC2 game and replay data ingested from object storage"
    database: sc2_warehouse
    schema: raw
    tables:
      - name: games
        description: "Raw game result records from SC2 API or replay parser"
        freshness:
          warn_after: {count: 24, period: hour}
          error_after: {count: 48, period: hour}
        loaded_at_field: _loaded_at
        columns:
          - name: game_id
            tests: [unique, not_null]
      - name: replays
        description: "Detailed telemetry extracted from .SC2Replay files"
        columns:
          - name: replay_id
            tests: [unique, not_null]
*/


-- ============================================================
-- DBT PROJECT DOCUMENTATION
-- (Reference block — embed in schema.yml)
-- ============================================================

/*
  SC2 Analytics dbt Project — Model Lineage
  ==========================================

  Sources
    └─ sc2_raw.games
    └─ sc2_raw.replays

  Staging
    ├─ stg_games          (view)   ← sc2_raw.games
    └─ stg_replays        (view)   ← sc2_raw.replays

  Intermediate
    └─ int_game_metrics   (table)  ← stg_games + stg_replays

  Marts / Facts
    ├─ fct_matchup_stats           (table)       ← int_game_metrics
    └─ fct_build_order_performance (incremental) ← int_game_metrics

  Marts / Dimensions
    ├─ dim_maps       (table) ← int_game_metrics
    └─ dim_strategies (table) ← int_game_metrics

  Refresh schedule (recommended):
    - Staging views    : always live
    - Intermediate     : every 1 hour
    - Fact tables      : every 6 hours
    - Dimension tables : daily
    - Incremental fact : every 30 minutes
*/
