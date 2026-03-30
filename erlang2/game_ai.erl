%% Wicked Zerg - Battle Simulation
%% Phase 143: Erlang v2

-module(game_ai).
-export([calculate_swarm_damage/1, swarm_formation/4, unit_strength/3, battle_outcome/2]).

calculate_swarm_damage(Count) ->
    Count * 5.

swarm_formation(CenterX, CenterY, Count, Radius) ->
    [begin
        Angle = 2 * math:pi() * I / Count,
        {CenterX + Radius * math:cos(Angle), CenterY + Radius * math:sin(Angle)}
     end || I <- lists:seq(0, Count-1)].

unit_strength(Health, Damage, Armor) ->
    Effective = Damage * Health / 100,
    Effective * (1 - Armor * 0.01).

battle_outcome(Attackers, Defenders) ->
    AttackPower = lists:sum([unit_strength(H, D, A) || {H, D, A} <- Attackers]),
    DefensePower = lists:sum([unit_strength(H, D, A) || {H, D, A} <- Defenders]),
    AttackPower > DefensePower.
