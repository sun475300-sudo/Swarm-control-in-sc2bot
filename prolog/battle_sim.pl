% Wicked Zerg - Battle Simulation
% Phase 128: Prolog

battle_sim(Units, Damage) :-
    length(Units, Count),
    Damage is Count * 5.

calculate_swarm_damage(Count, Damage) :-
    Damage is Count * 5.

swarm_formation(CenterX, CenterY, Count, Radius, Positions) :-
    findall((X, Y),
            (between(0, Count, I),
             Angle is 2 * pi * I / Count,
             X is CenterX + Radius * cos(Angle),
             Y is CenterY + Radius * sin(Angle)),
            Positions).

unit_strength(Health, Damage, Armor, Strength) :-
    Effective is Damage * Health / 100,
    Strength is Effective * (1 - Armor * 0.01).

battle_outcome(Attackers, Defenders, AttackerWins) :-
    maplist(unit_strength, Attackers, AttackPowers),
    maplist(unit_strength, Defenders, DefensePowers),
    sumlist(AttackPowers, TotalAttack),
    sumlist(DefensePowers, TotalDefense),
    AttackerWins is TotalAttack > TotalDefense.

distance((X1, Y1), (X2, Y2), Dist) :-
    Dist is sqrt((X1 - X2) ^ 2 + (Y1 - Y2) ^ 2).

min_distance(Point, Points, MinDist) :-
    maplist(distance(Point), Points, Dists),
    min_list(Dists, MinDist).

calculate_threats(OurPositions, EnemyPositions, ThreatCount) :-
    maplist(min_distance(OurPositions), EnemyPositions, MinDists),
    include(<(10), MinDists, Threats),
    length(Threats, ThreatCount).
