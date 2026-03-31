% Phase 552: Prolog Logic Programming
% SC2 Bot goal-directed planning with Prolog inference engine

:- module(sc2_bot, [
    decide/2,
    can_afford/3,
    simulate/3,
    optimal_build_order/2
]).

% ─────────────────────────────────────────────
% Unit costs: unit_cost(+Unit, -Minerals, -Gas, -Supply)
% ─────────────────────────────────────────────

unit_cost(drone,     50,  0,  1).
unit_cost(zergling,  25,  0,  1).
unit_cost(roach,     75,  25, 2).
unit_cost(hydralisk, 100, 50, 2).
unit_cost(mutalisk,  100, 100, 2).
unit_cost(ultralisk, 300, 200, 6).
unit_cost(queen,     150, 0,  2).
unit_cost(overlord,  100, 0,  0).

% ─────────────────────────────────────────────
% Resource predicates
% ─────────────────────────────────────────────

can_afford(Minerals, Gas, state(M, G, _, _, _, _, _)) :-
    M >= Minerals,
    G >= Gas.

supply_full(state(_, _, Supply, MaxSupply, _, _, _)) :-
    Supply >= MaxSupply - 1.

supply_available(state(_, _, Supply, MaxSupply, _, _, _)) :-
    Supply < MaxSupply - 1.

% ─────────────────────────────────────────────
% State: state(Minerals, Gas, Supply, MaxSupply, Workers, Army, Frame)
% ─────────────────────────────────────────────

initial_state(state(50, 0, 12, 14, 12, 0, 0)).

% ─────────────────────────────────────────────
% Decision rules (ordered by priority)
% ─────────────────────────────────────────────

% Priority 1: Threat → Defend (if we have army)
decide(State, defend) :-
    State = state(_, _, _, _, _, Army, _),
    Army > 0,
    threat_level(State, T),
    T > 0.6,
    !.

% Priority 2: Supply blocked
decide(State, train(overlord)) :-
    supply_full(State),
    can_afford(100, 0, State),
    !.

% Priority 3: Worker saturation
decide(State, train(drone)) :-
    State = state(_, _, _, _, Workers, _, _),
    Workers < 22,
    can_afford(50, 0, State),
    !.

% Priority 4: Expand when rich
decide(State, expand) :-
    State = state(Minerals, _, _, _, _, _, _),
    Minerals >= 300,
    !.

% Priority 5: Build army
decide(State, train(roach)) :-
    can_afford(75, 25, State),
    !.

decide(State, train(zergling)) :-
    can_afford(25, 0, State),
    !.

decide(_, wait).

% ─────────────────────────────────────────────
% Threat level (mock)
% ─────────────────────────────────────────────

threat_level(state(_, _, _, _, _, _, Frame), T) :-
    T is min(1.0, Frame * 0.0001).

% ─────────────────────────────────────────────
% Economy tick
% ─────────────────────────────────────────────

tick(state(M, G, S, MS, W, A, F), state(M2, G, S, MS, W, A, F2)) :-
    Income is W * 8 // 10,
    M2 is M + Income,
    F2 is F + 1.

% ─────────────────────────────────────────────
% Apply action
% ─────────────────────────────────────────────

apply(train(Unit), State, NewState) :-
    unit_cost(Unit, MCost, GCost, SCost),
    can_afford(MCost, GCost, State),
    !,
    State = state(M, G, S, MS, W, A, Fr),
    M2 is M - MCost,
    G2 is G - GCost,
    S2 is S + SCost,
    (Unit = drone    -> W2 is W + 1,  MS2 = MS,      A2 = A  ; true),
    (Unit = overlord -> W2 = W,       MS2 is MS + 8, A2 = A  ; true),
    (Unit \= drone, Unit \= overlord ->
        W2 = W, MS2 = MS, A2 is A + SCost ; true),
    NewState = state(M2, G2, S2, MS2, W2, A2, Fr).

apply(expand, State, NewState) :-
    can_afford(300, 0, State),
    !,
    State = state(M, G, S, MS, W, A, Fr),
    M2 is M - 300,
    W2 is W + 4,
    NewState = state(M2, G, S, MS, W2, A, Fr).

apply(_, State, State).  % wait / defend

% ─────────────────────────────────────────────
% Simulation step
% ─────────────────────────────────────────────

step(S0, S2) :-
    tick(S0, S1),
    decide(S1, Action),
    apply(Action, S1, S2).

% ─────────────────────────────────────────────
% Simulate N frames
% ─────────────────────────────────────────────

simulate(State, 0, State) :- !.
simulate(S0, N, SN) :-
    N > 0,
    step(S0, S1),
    N1 is N - 1,
    simulate(S1, N1, SN).

% ─────────────────────────────────────────────
% Build order planning (generate optimal sequence)
% ─────────────────────────────────────────────

% Units needed for a given goal
goal_requires(ling_flood, [zergling, zergling, zergling, zergling, zergling]).
goal_requires(roach_push, [roach, roach, roach, roach]).
goal_requires(muta_harass, [mutalisk, mutalisk, mutalisk]).
goal_requires(eco_build, [drone, drone, drone, drone, drone, drone]).

% Check if we can achieve unit sequence given resources
feasible_sequence([], state(M, G, S, MS, _, _, _)) :-
    M >= 0, G >= 0, S =< MS.

feasible_sequence([Unit|Rest], State) :-
    unit_cost(Unit, MC, GC, SC),
    can_afford(MC, GC, State),
    State = state(M, G, S, MS, W, A, Fr),
    M2 is M - MC, G2 is G - GC, S2 is S + SC,
    NewState = state(M2, G2, S2, MS, W, A, Fr),
    feasible_sequence(Rest, NewState).

optimal_build_order(Goal, Sequence) :-
    goal_requires(Goal, Sequence),
    initial_state(Init),
    % Simulate 500 frames to accumulate resources
    simulate(Init, 500, RichState),
    feasible_sequence(Sequence, RichState).

% ─────────────────────────────────────────────
% Main query (run with: swipl -g main -t halt bot_planner.pl)
% ─────────────────────────────────────────────

main :-
    write('Phase 552: Prolog Logic — SC2 Bot Planner'), nl,
    initial_state(Init),
    simulate(Init, 2000, Final),
    Final = state(Minerals, Gas, Supply, MaxSupply, Workers, Army, Frame),
    format("Frame:~w | Minerals:~w | Workers:~w | Army:~w | Supply:~w/~w~n",
           [Frame, Minerals, Workers, Army, Supply, MaxSupply]),
    nl,
    write('Checking build orders:'), nl,
    forall(
        member(Goal, [ling_flood, roach_push, eco_build]),
        (
            (optimal_build_order(Goal, _) ->
                format("  [~w] FEASIBLE~n", [Goal])
            ;
                format("  [~w] NOT FEASIBLE~n", [Goal])
            )
        )
    ).

:- initialization(main, main).
