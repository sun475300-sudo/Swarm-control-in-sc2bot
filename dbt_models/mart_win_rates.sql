-- dbt_models/mart_win_rates.sql
-- Mart model: matchup win rates, unit costs, and build timing statistics

{{
    config(
        materialized='table',
        tags=['sc2', 'mart']
    )
}}

-- -----------------------------------------------------------------------
-- CTE 1: Matchup-level win rates
-- -----------------------------------------------------------------------
with matchup_rates as (

    select
        matchup,
        count(*)                                            as total_games,
        sum(case when is_win then 1 else 0 end)             as wins,
        round(
            100.0 * sum(case when is_win then 1 else 0 end)
                  / nullif(count(*), 0),
            2
        )                                                   as win_rate_pct,
        round(avg(duration_sec), 1)                         as avg_duration_sec

    from {{ ref('stg_battles') }}
    where matchup in ('ZVT', 'ZVZ', 'ZVP')
    group by matchup

),

-- -----------------------------------------------------------------------
-- CTE 2: Unit / resource cost efficiency
-- -----------------------------------------------------------------------
unit_costs as (

    select
        matchup,
        round(avg(minerals_used), 0)                        as avg_minerals,
        round(avg(gas_used),      0)                        as avg_gas,
        round(avg(army_value),    0)                        as avg_army_value,
        round(
            avg(
                case
                    when (minerals_used + gas_used) > 0
                    then cast(army_value as float)
                         / (minerals_used + gas_used)
                    else null
                end
            ),
            4
        )                                                   as avg_resource_efficiency,
        round(
            avg(
                case
                    when units_lost > 0
                    then cast(units_killed as float) / units_lost
                    else cast(units_killed as float)
                end
            ),
            2
        )                                                   as avg_kd_ratio

    from {{ ref('stg_battles') }}
    group by matchup

),

-- -----------------------------------------------------------------------
-- CTE 3: Build order timing statistics (top builds only, >= 5 games)
-- -----------------------------------------------------------------------
build_timing as (

    select
        matchup,
        build_order,
        count(*)                                            as games_played,
        round(
            100.0 * sum(case when is_win then 1 else 0 end)
                  / nullif(count(*), 0),
            2
        )                                                   as build_win_rate_pct,
        round(avg(duration_sec), 1)                         as avg_game_length_sec,
        round(avg(supply_peak),  1)                         as avg_supply_peak,
        row_number() over (
            partition by matchup
            order by
                100.0 * sum(case when is_win then 1 else 0 end)
                      / nullif(count(*), 0) desc,
                count(*) desc
        )                                                   as build_rank

    from {{ ref('stg_battles') }}
    group by matchup, build_order
    having count(*) >= 5

)

-- -----------------------------------------------------------------------
-- Final join: one row per matchup enriched with top-1 build stats
-- -----------------------------------------------------------------------
select
    mr.matchup,
    mr.total_games,
    mr.wins,
    mr.win_rate_pct,
    mr.avg_duration_sec,
    uc.avg_minerals,
    uc.avg_gas,
    uc.avg_army_value,
    uc.avg_resource_efficiency,
    uc.avg_kd_ratio,
    bt.build_order                  as best_build_order,
    bt.build_win_rate_pct           as best_build_win_rate_pct,
    bt.avg_game_length_sec          as best_build_avg_length_sec,
    bt.avg_supply_peak              as best_build_avg_supply

from matchup_rates  mr
left join unit_costs    uc on mr.matchup = uc.matchup
left join build_timing  bt on mr.matchup = bt.matchup and bt.build_rank = 1

order by mr.win_rate_pct desc
