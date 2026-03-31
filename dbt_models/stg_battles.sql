-- dbt_models/stg_battles.sql
-- Staging model: clean and type-cast raw_battles source data

{{
    config(
        materialized='view',
        tags=['sc2', 'staging']
    )
}}

with source as (

    select * from {{ source('sc2_raw', 'raw_battles') }}

),

staged as (

    select
        -- identifiers
        cast(game_id      as varchar)   as game_id,

        -- matchup normalised to uppercase (ZvT / ZvZ / ZvP)
        upper(trim(matchup))            as matchup,

        -- result flag
        case
            when lower(trim(result)) = 'win'  then true
            when lower(trim(result)) = 'loss' then false
            else null
        end                             as is_win,

        -- timing
        cast(duration_sec as integer)   as duration_sec,
        cast(game_date    as date)      as game_date,

        -- economy
        cast(minerals_used as integer)  as minerals_used,
        cast(gas_used      as integer)  as gas_used,

        -- combat
        cast(army_value    as integer)  as army_value,
        cast(units_lost    as integer)  as units_lost,
        cast(units_killed  as integer)  as units_killed,
        cast(supply_peak   as integer)  as supply_peak,

        -- build
        trim(build_order)               as build_order,

        -- metadata
        current_timestamp               as dbt_updated_at

    from source
    where game_id is not null
      and matchup is not null

)

select * from staged
