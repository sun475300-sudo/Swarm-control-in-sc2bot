%% rule_engine.pl
%% Prolog v2 rule-based strategy engine for StarCraft II Zerg bot
%% Phase 132 - declarative rules for counter selection and attack timing
%% Supports best_counter/2 and attack_timing/2 queries from the Python bot.

:- module(rule_engine, [
    best_counter/2,
    attack_timing/2,
    counter/2,
    unit_supply/2,
    unit_dps/2
]).

% ---------------------------------------------------------------------------
% Facts: supply cost per unit (some are 0.5 but Prolog uses rationals)
% ---------------------------------------------------------------------------

unit_supply(zergling,  0.5).
unit_supply(baneling,  0.5).
unit_supply(roach,     2).
unit_supply(ravager,   3).
unit_supply(hydralisk, 2).
unit_supply(lurker,    3).
unit_supply(mutalisk,  2).
unit_supply(corruptor, 2).
unit_supply(ultralisk, 6).
unit_supply(brood_lord, 4).

% DPS ratings (approximate, ground vs ground unless noted)
unit_dps(zergling,   9.0).
unit_dps(baneling,  35.0).   % explosive burst vs bio
unit_dps(roach,     13.0).
unit_dps(ravager,   18.0).
unit_dps(hydralisk, 25.0).
unit_dps(lurker,    40.0).   % burrowed siege DPS per lurker
unit_dps(mutalisk,  18.0).   % multi-target bounce adds effective DPS
unit_dps(corruptor, 14.0).   % anti-air
unit_dps(ultralisk, 59.0).   % cleave included
unit_dps(brood_lord, 20.0).  % siege ranged, creates broodlings

% ---------------------------------------------------------------------------
% Facts: counter relationships (counter(Enemy, OurUnit))
% Read as: "OurUnit is an effective counter to Enemy"
% ---------------------------------------------------------------------------

% Terran bio counters
counter(marine,    baneling).    % banelings shred bio balls
counter(marauder,  roach).       % roach armor counters marauder slow
counter(medivac,   corruptor).   % anti-air priority target
counter(siege_tank, ravager).    % bile breaks sieged tanks
counter(hellion,   roach).       % roach survives hellion AoE

% Protoss counters
counter(zealot,    roach).       % roach kites zealots safely
counter(stalker,   hydralisk).   % hydralisks outrange and outDPS stalkers
counter(immortal,  brood_lord).  % broodlords avoid immortal hardened shield
counter(colossus,  corruptor).   % corruptors shred colossus from air
counter(high_templar, zergling). % zerglings force psionic storms to spread
counter(archon,    lurker).      % lurkers punish slow archon movement
counter(carrier,   corruptor).   % anti-capital ship

% Zerg mirror counters
counter(roach,     ravager).     % bile outranges roach
counter(mutalisk,  hydralisk).   % hydras shred mutalisks
counter(brood_lord, corruptor).  % corruptors specifically target BLs
counter(zergling,  baneling).    % banelings counter enemy ling floods

% ---------------------------------------------------------------------------
% Rules: best_counter/2
% best_counter(+Enemy, -OurUnit)
% Finds the best Zerg unit to counter the given enemy unit type.
% If multiple counters exist, returns the one with highest DPS.
% ---------------------------------------------------------------------------

best_counter(Enemy, BestCounter) :-
    % Collect all valid counters with their DPS ratings
    findall(DPS-Unit,
        (counter(Enemy, Unit), unit_dps(Unit, DPS)),
        Pairs),
    Pairs \= [],          % fail cleanly if no counter is known
    % Sort descending by DPS and pick the top entry
    msort(Pairs, Sorted),
    last(Sorted, _BestDPS-BestCounter).

% Fallback: if no specific counter known, default to roach (safe generalist)
best_counter(_UnknownEnemy, roach).

% ---------------------------------------------------------------------------
% Facts: tech buildings that signal attack timing
% tech_building(Building, TimingMinutes, AttackUnit)
% ---------------------------------------------------------------------------

tech_building(spawning_pool,    3.5,  zergling).
tech_building(roach_warren,     4.5,  roach).
tech_building(hydralisk_den,    6.0,  hydralisk).
tech_building(baneling_nest,    4.0,  baneling).
tech_building(spire,            7.0,  mutalisk).
tech_building(lurker_den,       9.0,  lurker).
tech_building(ultralisk_cavern, 11.0, ultralisk).

% ---------------------------------------------------------------------------
% Rules: attack_timing/2
% attack_timing(+TechBuilding, -Timing)
% Returns expected attack time (minutes from game start) for a given
% tech building sighting. Useful for predicting enemy build orders.
% ---------------------------------------------------------------------------

attack_timing(Building, timing(Mins, Unit)) :-
    tech_building(Building, Mins, Unit).

% ---------------------------------------------------------------------------
% Utility: list_all_counters/1 — debugging helper
% list_all_counters(+Enemy) prints all known counters for that enemy
% ---------------------------------------------------------------------------

list_all_counters(Enemy) :-
    format("Counters for ~w:~n", [Enemy]),
    forall(
        counter(Enemy, Unit),
        (unit_dps(Unit, DPS),
         format("  ~w  (DPS: ~2f)~n", [Unit, DPS]))
    ).

% ---------------------------------------------------------------------------
% Example queries (run in swipl):
%   ?- best_counter(marine, C).          % C = baneling
%   ?- best_counter(stalker, C).         % C = hydralisk
%   ?- attack_timing(lurker_den, T).     % T = timing(9.0, lurker)
%   ?- list_all_counters(zealot).
% ---------------------------------------------------------------------------
