% P103: Erlang - Concurrent Telecom-Grade AI Processing
% Highly reliable distributed AI decision system

-module(game_ai).
-export([start/0, game_loop/0, analyze_units/1]).

-record(unit, {id, type, health, position}).
-record(state, {units=[], resources={0,0,0}, enemy=[]}).

start() ->
    io:format("Starting Erlang AI System~n"),
    Pid = spawn(fun game_loop/0),
    register(ai_server, Pid),
    Pid.

game_loop() ->
    receive
        {update_state, Units} ->
            Decision = make_decision(Units),
            io:format("Decision: ~p~n", [Decision]),
            game_loop();
        {get_status, From} ->
            From ! {status, running},
            game_loop();
        stop -> 
            io:format("Stopping AI~n")
    after 1000 ->
        game_loop()
    end.

make_decision(Units) ->
    Power = calculate_power(Units),
    if Power > 500 -> attack;
       Power > 200 -> defend;
       true -> expand
    end.

calculate_power([]) -> 0;
calculate_power([H|T]) ->
    HP = H#unit.health,
    (HP div 10) + calculate_power(T).

analyze_units(Units) ->
    lists:map(fun(U) -> 
        #{id => U#unit.id, type => U#unit.type, threat => classify_threat(U)} 
    end, Units).

classify_threat(U) when U#unit.health > 100 -> high;
classify_threat(_) -> low.
