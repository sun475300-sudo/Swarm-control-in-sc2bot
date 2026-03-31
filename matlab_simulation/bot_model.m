%% Phase 557: MATLAB Simulation
% SC2 Bot economy and combat simulation using MATLAB
% Demonstrates numerical simulation, matrix ops, and visualization

function bot_model()
    fprintf('Phase 557: MATLAB Simulation — SC2 Bot Economy\n\n');

    %% Economy simulation
    state = init_state();
    history = simulate_economy(state, 2000);
    print_results(history(end));
    plot_economy(history);

    %% Combat analysis
    combat_analysis();
end

%% ─────────────────────────────────────────────
%% Game state struct
%% ─────────────────────────────────────────────

function s = init_state()
    s.minerals   = 50;
    s.gas        = 0;
    s.supply     = 12;
    s.max_supply = 14;
    s.workers    = 12;
    s.army       = 0;
    s.frame      = 0;
    s.hatcheries = 1;
    s.threat     = 0.0;
end

%% ─────────────────────────────────────────────
%% Simulation
%% ─────────────────────────────────────────────

function history = simulate_economy(init, n_frames)
    history = repmat(init, n_frames + 1, 1);
    s = init;

    for i = 1:n_frames
        s = tick(s);
        action = decide(s);
        s = apply_action(s, action);
        history(i + 1) = s;
    end
end

function s = tick(s)
    income = floor(s.workers * 8 / 10);
    s.minerals = s.minerals + income;
    s.frame = s.frame + 1;
    s.threat = min(1.0, s.threat + 0.0001);
end

function action = decide(s)
    supply_ratio = s.supply / max(1, s.max_supply);

    if s.threat > 0.6
        action = 'defend';
    elseif supply_ratio >= 0.95 && s.minerals >= 100
        action = 'overlord';
    elseif s.workers < 22 && s.minerals >= 50
        action = 'drone';
    elseif s.minerals >= 300 && s.hatcheries < 3
        action = 'expand';
    elseif s.minerals >= 75 && s.gas >= 25
        action = 'roach';
    elseif s.minerals >= 25
        action = 'zergling';
    else
        action = 'wait';
    end
end

function s = apply_action(s, action)
    switch action
        case 'drone'
            if s.minerals >= 50
                s.minerals = s.minerals - 50;
                s.workers = s.workers + 1;
                s.supply = s.supply + 1;
            end
        case 'zergling'
            if s.minerals >= 25
                s.minerals = s.minerals - 25;
                s.army = s.army + 1;
                s.supply = s.supply + 1;
            end
        case 'roach'
            if s.minerals >= 75 && s.gas >= 25
                s.minerals = s.minerals - 75;
                s.gas = s.gas - 25;
                s.army = s.army + 2;
                s.supply = s.supply + 2;
            end
        case 'overlord'
            if s.minerals >= 100
                s.minerals = s.minerals - 100;
                s.max_supply = s.max_supply + 8;
            end
        case 'expand'
            if s.minerals >= 300
                s.minerals = s.minerals - 300;
                s.hatcheries = s.hatcheries + 1;
                s.workers = s.workers + 4;
            end
    end
end

%% ─────────────────────────────────────────────
%% Combat analysis (matrix ops)
%% ─────────────────────────────────────────────

function combat_analysis()
    fprintf('\nCombat Analysis:\n');

    % Unit stats: [DPS, HP, Range, Supply]
    % Rows: Zergling, Roach, Hydralisk, Mutalisk, Ultralisk
    units = [
        8.9,  35,  0, 1;  % Zergling
        10.0, 145, 4, 2;  % Roach
        15.6, 90,  5, 2;  % Hydralisk
        9.0,  120, 3, 2;  % Mutalisk
        59.6, 500, 1, 6;  % Ultralisk
    ];

    unit_names = {'Zergling', 'Roach', 'Hydralisk', 'Mutalisk', 'Ultralisk'};
    n = size(units, 1);

    % DPS matrix
    dps_matrix = zeros(n, n);
    for i = 1:n
        for j = 1:n
            range_bonus = 1.0;
            if units(i, 3) > units(j, 3)
                range_bonus = 1.1;
            end
            dps_matrix(i, j) = units(i, 1) * range_bonus;
        end
    end

    fprintf('DPS Matrix:\n');
    fprintf('%12s ', unit_names{:});
    fprintf('\n');
    for i = 1:n
        fprintf('%-12s', unit_names{i});
        fprintf('%12.1f ', dps_matrix(i, :));
        fprintf('\n');
    end

    % Army compositions comparison
    my_army     = [5, 3, 4, 0, 0];  % zerlings, roaches, hydras
    enemy_army  = [0, 5, 5, 0, 0];  % roaches, hydras

    my_dps    = my_army    * units(:, 1);
    enemy_dps = enemy_army * units(:, 1);
    my_hp     = my_army    * units(:, 2);
    enemy_hp  = enemy_army * units(:, 2);

    fprintf('\nMy DPS:     %.1f  HP: %d\n', my_dps, my_hp);
    fprintf('Enemy DPS:  %.1f  HP: %d\n', enemy_dps, enemy_hp);

    if my_dps > enemy_dps * 1.2
        fprintf('Battle outcome: WIN\n');
    elseif enemy_dps > my_dps * 1.2
        fprintf('Battle outcome: LOSS\n');
    else
        fprintf('Battle outcome: DRAW\n');
    end
end

%% ─────────────────────────────────────────────
%% Report
%% ─────────────────────────────────────────────

function print_results(s)
    fprintf('Final state:\n');
    fprintf('  Frame:    %d\n', s.frame);
    fprintf('  Minerals: %d\n', s.minerals);
    fprintf('  Workers:  %d\n', s.workers);
    fprintf('  Army:     %d\n', s.army);
    fprintf('  Supply:   %d/%d\n', s.supply, s.max_supply);
    fprintf('  Hatches:  %d\n', s.hatcheries);
end

function plot_economy(history)
    % This would generate plots in MATLAB environment
    % Extracting arrays for potential visualization
    frames   = [history.frame];
    minerals = [history.minerals];
    workers  = [history.workers];
    army     = [history.army];

    fprintf('\nEconomy trajectory (sampled every 200 frames):\n');
    fprintf('%-8s %-10s %-10s %-10s\n', 'Frame', 'Minerals', 'Workers', 'Army');
    for i = 1:200:length(frames)
        fprintf('%-8d %-10d %-10d %-10d\n', ...
            frames(i), minerals(i), workers(i), army(i));
    end
end

%% Entry point
bot_model();
