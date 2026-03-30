%=============================================================================
% constraint_solver.m
% SC2 Zerg Bot – Mercury Logic Programming Constraint Solver
%
% Uses Mercury's declarative type system and backtracking search to find
% optimal Zerg unit compositions that counter a given enemy army.
%
% Compile:  mmc --make constraint_solver
% Run:      ./constraint_solver
%=============================================================================

:- module constraint_solver.

:- interface.
:- import_module io.

% Main predicate – required by Mercury runtime
:- pred main(io::di, io::uo) is det.

%=============================================================================
:- implementation.
:- import_module list, int, string, float, solutions.

%-----------------------------------------------------------------------------
% TYPE DEFINITIONS
%-----------------------------------------------------------------------------

% All trainable Zerg combat units
:- type unit_type
    --->  zergling
        ; baneling
        ; roach
        ; ravager
        ; hydralisk
        ; lurker
        ; infestor
        ; corruptor
        ; brood_lord
        ; ultralisk.

% A composition is an ordered list of (unit_type, count) pairs
:- type unit_entry   == pair(unit_type, int).
:- type composition  == list(unit_entry).

% Mineral and vespene cost record
:- type cost
    --->  cost(minerals :: int, gas :: int).

%-----------------------------------------------------------------------------
% UNIT COSTS
% unit_cost(Unit, cost(Minerals, Gas))
%-----------------------------------------------------------------------------
:- pred unit_cost(unit_type::in, cost::out) is det.

unit_cost(zergling,   cost(25,  0)).
unit_cost(baneling,   cost(25, 25)).   % morph cost above zergling
unit_cost(roach,      cost(75, 25)).
unit_cost(ravager,    cost(25, 75)).   % morph cost above roach
unit_cost(hydralisk,  cost(100, 50)).
unit_cost(lurker,     cost(50, 100)).  % morph cost above hydralisk
unit_cost(infestor,   cost(100, 150)).
unit_cost(corruptor,  cost(150, 100)).
unit_cost(brood_lord, cost(150, 150)).
unit_cost(ultralisk,  cost(300, 200)).

%-----------------------------------------------------------------------------
% COUNTER RELATIONSHIPS
% counter_unit(Attacker, Defender)
% True when Attacker is an effective counter to Defender unit type.
%-----------------------------------------------------------------------------
:- pred counter_unit(unit_type::in, unit_type::out) is nondet.

% Zerglings are countered by banelings (splash vs. bio blob)
counter_unit(baneling,    zergling).   % baneling counters marine/ling blobs
counter_unit(baneling,    marine).     % enemy marines

% Roaches absorb armoured / stalker fire
counter_unit(roach,       stalker).
counter_unit(roach,       marauder).
counter_unit(roach,       immortal).   % only in sustained fights, not burst

% Ravagers snipe buildings and cyclones with corrosive bile
counter_unit(ravager,     cyclone).
counter_unit(ravager,     siegetank).

% Hydralisks are flexible anti-air/ground
counter_unit(hydralisk,   phoenix).
counter_unit(hydralisk,   mutalisk).
counter_unit(hydralisk,   void_ray).

% Lurkers shred bio and ground pushes
counter_unit(lurker,      marine).
counter_unit(lurker,      zealot).
counter_unit(lurker,      marauder).

% Infestors: neural parasite + fungal growth
counter_unit(infestor,    colossus).
counter_unit(infestor,    thor).

% Corruptors clear sky
counter_unit(corruptor,   carrier).
counter_unit(corruptor,   battlecruiser).
counter_unit(corruptor,   colossus).

% Brood Lords siege ground
counter_unit(brood_lord,  marine).
counter_unit(brood_lord,  zealot).
counter_unit(brood_lord,  roach).     % enemy roaches

% Ultralisks tank and cleave through bio
counter_unit(ultralisk,   marine).
counter_unit(ultralisk,   marauder).
counter_unit(ultralisk,   zergling).  % enemy zerglings (mirror)

%-----------------------------------------------------------------------------
% SOLVE_COMPOSITION
% solve_composition(+EnemyUnits, +MineralBudget, -BestComposition)
%
% Finds a list of (unit_type, count) pairs whose total mineral cost
% does not exceed MineralBudget, and which covers at least one counter
% relationship for each enemy unit type in EnemyUnits.
%
% The solver generates all valid compositions via backtracking and
% picks the one that covers the most enemy units.
%-----------------------------------------------------------------------------
:- pred solve_composition(list(unit_type)::in, int::in, composition::out)
    is det.

solve_composition(EnemyUnits, Budget, Best) :-
    % Enumerate all compositions that fit the budget
    solutions(
        (pred(Comp::out) is nondet :-
            candidate_composition(EnemyUnits, Budget, Comp)),
        AllComps),
    (
        AllComps = [H | T],
        list.foldl(pick_better(EnemyUnits), T, H, Best)
    ;
        AllComps = [],
        Best = []   % fallback: no valid composition found
    ).

% candidate_composition generates one valid composition via backtracking
:- pred candidate_composition(list(unit_type)::in, int::in, composition::out)
    is nondet.

candidate_composition(Enemies, Budget, Comp) :-
    % Try each unit type as the primary pick
    member(Unit, [roach, hydralisk, zergling, baneling,
                  lurker, corruptor, infestor, ultralisk]),
    unit_cost(Unit, cost(MCost, _)),
    MCost =< Budget,
    Count = Budget / MCost,
    Count > 0,
    Comp = [Unit - Count],
    % Require at least one counter relationship to be satisfied
    some_counter_covered(Unit, Enemies).

% some_counter_covered(Unit, Enemies): Unit counters at least one enemy
:- pred some_counter_covered(unit_type::in, list(unit_type)::in) is semidet.

some_counter_covered(Unit, Enemies) :-
    member(Enemy, Enemies),
    counter_unit(Unit, Enemy).

% pick_better: fold helper – keep the composition covering more enemy units
:- pred pick_better(list(unit_type)::in,
                    composition::in, composition::in, composition::out) is det.

pick_better(Enemies, Candidate, Current, Winner) :-
    score_composition(Candidate, Enemies, ScoreC),
    score_composition(Current,   Enemies, ScoreCur),
    ( ScoreC > ScoreCur -> Winner = Candidate ; Winner = Current ).

% score_composition: count how many enemy types are countered by composition
:- pred score_composition(composition::in, list(unit_type)::in, int::out)
    is det.

score_composition([], _, 0).
score_composition([Unit - _ | Rest], Enemies, Score) :-
    score_composition(Rest, Enemies, RestScore),
    aggregate_all(count,
        (member(Enemy, Enemies), counter_unit(Unit, Enemy)),
        Covered),
    Score = RestScore + Covered.

%-----------------------------------------------------------------------------
% PRETTY PRINTING
%-----------------------------------------------------------------------------
:- pred print_composition(composition::in, io::di, io::uo) is det.

print_composition([], !IO) :-
    io.write_string("  (no composition found)\n", !IO).
print_composition([Unit - Count | Rest], !IO) :-
    unit_cost(Unit, cost(Min, Gas)),
    Total = Min * Count,
    io.format("  %-14s x%2d  (min: %4d | gas: %3d | total min: %5d)\n",
              [s(string(Unit)), i(Count), i(Min), i(Gas), i(Total)], !IO),
    print_composition(Rest, !IO).

%-----------------------------------------------------------------------------
% MAIN – demonstration run
%-----------------------------------------------------------------------------
main(!IO) :-
    io.write_string("=== SC2 Zerg Constraint Solver ===\n\n", !IO),

    % Scenario 1: bio-heavy Terran
    Enemies1 = [marine, marauder, siegetank],
    io.write_string("Enemy comp: marine / marauder / siege-tank\n", !IO),
    solve_composition(Enemies1, 900, Comp1),
    print_composition(Comp1, !IO),
    io.nl(!IO),

    % Scenario 2: Protoss air
    Enemies2 = [carrier, void_ray, colossus],
    io.write_string("Enemy comp: carrier / void-ray / colossus\n", !IO),
    solve_composition(Enemies2, 750, Comp2),
    print_composition(Comp2, !IO),
    io.nl(!IO),

    io.write_string("=== Done ===\n", !IO).
