#!/usr/bin/env julia
# Phase 63: Julia ML Experiments for SC2 Swarm Control
# Reinforcement Learning Policy Gradient with REINFORCE

using LinearAlgebra
using Statistics
using Random

struct PolicyNetwork
    W1::Matrix{Float64}
    b1::Vector{Float64}
    W2::Matrix{Float64}
    b2::Vector{Float64}
end

function PolicyNetwork(input_dim::Int, hidden_dim::Int, output_dim::Int)
    PolicyNetwork(
        randn(hidden_dim, input_dim) * sqrt(2.0 / input_dim),
        zeros(hidden_dim),
        randn(output_dim, hidden_dim) * sqrt(2.0 / hidden_dim),
        zeros(output_dim)
    )
end

function forward(policy::PolicyNetwork, state::Vector{Float64})
    hidden = tanh.(policy.W1 * state .+ policy.b1)
    logits = policy.W2 * hidden .+ policy.b2
    probs = softmax(logits)
    return probs
end

function softmax(x::Vector{Float64})
    x_max = maximum(x)
    exp_x = exp.(x .- x_max)
    return exp_x ./ sum(exp_x)
end

function select_action(policy::PolicyNetwork, state::Vector{Float64})
    probs = forward(policy, state)
    action = sample(Categorical(probs))
    return action, probs[action]
end

using Distributions

mutable struct ReplayBuffer
    states::Vector{Vector{Float64}}
    actions::Vector{Int}
    rewards::Vector{Float64}
    log_probs::Vector{Float64}
end

ReplayBuffer() = ReplayBuffer([], [], [], [])

function push!(buffer::ReplayBuffer, state, action, reward, log_prob)
    push!(buffer.states, state)
    push!(buffer.actions, action)
    push!(buffer.rewards, reward)
    push!(buffer.log_probs, log_prob)
end

function compute_returns(rewards::Vector{Float64}, gamma::Float64 = 0.99)
    returns = Float64[]
    G = 0.0
    for r in reverse(rewards)
        G = r + gamma * G
        pushfirst!(returns, G)
    end
    return returns
end

function update!(policy::PolicyNetwork, buffer::ReplayBuffer, optimizer; gamma::Float64 = 0.99, entropy_coef::Float64 = 0.01)
    if isempty(buffer.states)
        return 0.0
    end
    
    states = hcat(buffer.states...)
    actions = buffer.actions
    returns = compute_returns(buffer.rewards, gamma)
    
    returns = (returns .- mean(returns)) ./ (std(returns) + 1e-8)
    
    total_loss = 0.0
    for i in eachindex(actions)
        probs = forward(policy, states[:, i])
        log_prob = log(probs[actions[i]] + 1e-8)
        entropy = -sum(p -> p * log(p + 1e-8), probs)
        
        loss = -log_prob * returns[i] - entropy_coef * entropy
        total_loss += loss
    end
    
    return total_loss / length(actions)
end

function simulate_game(policy::PolicyNetwork)
    Random.seed!(rand(UInt64))
    
    state = randn(8) .* 10.0
    
    available_actions = ["drone", "overlord", "zergling", "roach", "hydralisk", "ling_bane", "hydra_roach"]
    
    total_reward = 0.0
    game_steps = 100
    
    for step in 1:game_steps
        action_idx, log_prob = select_action(policy, state)
        
        reward = 0.0
        
        if step % 10 == 0
            reward += 1.0
        end
        
        if rand() < 0.1
            reward += 5.0
        elseif rand() < 0.2
            reward -= 2.0
        end
        
        state = state + randn(8) * 0.5
        state = clamp.(state, -50.0, 50.0)
        
        total_reward += reward
    end
    
    return total_reward
end

function train(n_episodes::Int = 1000)
    input_dim = 8
    hidden_dim = 64
    output_dim = 7
    
    policy = PolicyNetwork(input_dim, hidden_dim, output_dim)
    
    best_reward = -Inf
    recent_rewards = Float64[]
    
    println("Starting RL Training with REINFORCE...")
    println("State dim: $input_dim, Hidden: $hidden_dim, Actions: $output_dim")
    
    for episode in 1:n_episodes
        buffer = ReplayBuffer()
        
        state = randn(8) .* 10.0
        total_reward = 0.0
        
        for step in 1:100
            action_idx, log_prob = select_action(policy, state)
            
            reward = randn() + 1.0
            if rand() < 0.1
                reward += 5.0
            elseif rand() < 0.2
                reward -= 2.0
            end
            
            push!(buffer, state, action_idx, reward, log_prob)
            
            state = state + randn(8) * 0.5
            state = clamp.(state, -50.0, 50.0)
            
            total_reward += reward
        end
        
        loss = update!(policy, buffer, nothing)
        
        push!(recent_rewards, total_reward)
        if length(recent_rewards) > 100
            popfirst!(recent_rewards)
        end
        
        if total_reward > best_reward
            best_reward = total_reward
        end
        
        if episode % 100 == 0
            avg_reward = mean(recent_rewards)
            println("Episode $episode | Reward: $(round(total_reward, 2)) | Avg(100): $(round(avg_reward, 2)) | Best: $(round(best_reward, 2))")
        end
    end
    
    return policy, recent_rewards
end

function analyze_combat_state(my_units::Matrix{Float64}, enemy_units::Matrix{Float64})
    my_power = sum(eachrow(my_units) do row
        hp, max_hp, dmg, range = row
        (hp / max_hp) * dmg * range
    end)
    
    enemy_power = sum(eachrow(enemy_units) do row
        hp, max_hp, dmg, range = row
        (hp / max_hp) * dmg * range
    end)
    
    if enemy_power > 0
        advantage = my_power / enemy_power
    else
        advantage = my_power
    end
    
    return (
        my_power = my_power,
        enemy_power = enemy_power,
        advantage = advantage,
        recommendation = advantage > 1.2 ? "ATTACK" : advantage < 0.8 ? "RETREAT" : "HOLD"
    )
end

function generate_state_features(game_state::Dict)
    return [
        game_state["my_supply"] / 200.0,
        game_state["enemy_supply"] / 200.0,
        game_state["my_units_count"] / 100.0,
        game_state["enemy_units_count"] / 100.0,
        game_state["my_tech_level"] / 3.0,
        game_state["map_control"] / 1.0,
        game_state["resource_advantage"] / 1000.0,
        game_state["game_progress"] / 600.0,
    ]
end

println("\n" * "="^60)
println("SC2 SWARM CONTROL - JULIA ML EXPERIMENTS")
println("="^60)

policy, rewards = train(1000)

println("\n" * "="^60)
println("Training Complete! Running Combat Analysis...")
println("="^60)

my_units = [
    50.0 100.0 10.0 5.0
    80.0 100.0 12.0 6.0
    30.0 50.0 8.0 4.0
]

enemy_units = [
    45.0 100.0 11.0 5.0
    60.0 100.0 9.0 4.0
]

result = analyze_combat_state(my_units, enemy_units)
println("Combat Analysis Result:")
println("  My Power: $(round(result.my_power, 2))")
println("  Enemy Power: $(round(result.enemy_power, 2))")
println("  Advantage: $(round(result.advantage, 2))")
println("  Recommendation: $(result.recommendation)")
