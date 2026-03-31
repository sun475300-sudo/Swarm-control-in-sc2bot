%%%-------------------------------------------------------------------
%%% @doc SC2 Bot OTP Supervisor Tree
%%% Manages all SC2 bot worker processes with one_for_one strategy.
%%%-------------------------------------------------------------------
-module(sc2_supervisor).
-behaviour(supervisor).

-export([start_link/0]).
-export([init/1]).

%% Child process API exports
-export([start_game_server/1, stop_game_server/1]).

-define(SERVER, ?MODULE).

%%====================================================================
%% API functions
%%====================================================================

start_link() ->
    supervisor:start_link({local, ?SERVER}, ?MODULE, []).

start_game_server(GameId) ->
    ChildSpec = #{
        id       => {game_server, GameId},
        start    => {sc2_game_server, start_link, [GameId]},
        restart  => temporary,
        shutdown => 5000,
        type     => worker,
        modules  => [sc2_game_server]
    },
    supervisor:start_child(?SERVER, ChildSpec).

stop_game_server(GameId) ->
    supervisor:terminate_child(?SERVER, {game_server, GameId}),
    supervisor:delete_child(?SERVER, {game_server, GameId}).

%%====================================================================
%% Supervisor callbacks
%%====================================================================

init([]) ->
    SupFlags = #{
        strategy  => one_for_one,
        intensity => 5,
        period    => 10
    },
    ChildSpecs = [
        #{
            id       => game_server,
            start    => {sc2_game_server, start_link, []},
            restart  => permanent,
            shutdown => 5000,
            type     => worker,
            modules  => [sc2_game_server]
        },
        #{
            id       => economy_worker,
            start    => {sc2_economy_worker, start_link, []},
            restart  => permanent,
            shutdown => 5000,
            type     => worker,
            modules  => [sc2_economy_worker]
        },
        #{
            id       => combat_worker,
            start    => {sc2_combat_worker, start_link, []},
            restart  => permanent,
            shutdown => 5000,
            type     => worker,
            modules  => [sc2_combat_worker]
        },
        #{
            id       => scout_worker,
            start    => {sc2_scout_worker, start_link, []},
            restart  => permanent,
            shutdown => 5000,
            type     => worker,
            modules  => [sc2_scout_worker]
        }
    ],
    {ok, {SupFlags, ChildSpecs}}.

%%====================================================================
%% gen_server example: sc2_game_server callbacks
%%====================================================================

-module(sc2_game_server).
-behaviour(gen_server).

-export([start_link/0, get_state/0, update_state/1]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2]).

start_link() ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, [], []).

get_state() ->
    gen_server:call(?MODULE, get_state).

update_state(NewState) ->
    gen_server:cast(?MODULE, {update_state, NewState}).

init([]) ->
    InitialState = #{
        minerals => 50,
        vespene  => 0,
        supply   => 12,
        units    => [],
        game_id  => undefined
    },
    {ok, InitialState}.

handle_call(get_state, _From, State) ->
    {reply, {ok, State}, State};
handle_call(_Request, _From, State) ->
    {reply, ok, State}.

handle_cast({update_state, NewState}, _State) ->
    {noreply, NewState};
handle_cast(_Msg, State) ->
    {noreply, State}.

handle_info(_Info, State) ->
    {noreply, State}.

terminate(_Reason, _State) ->
    ok.
