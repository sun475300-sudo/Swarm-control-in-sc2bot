module HyperparameterOptimizer

using Flux
using Statistics
using Random
using Dates

export HyperparameterConfig, optimize, genetic_search, bayesian_optimize

struct HyperparameterConfig
    learning_rate::Float64
    batch_size::Int
    hidden_dim::Int
    dropout::Float64
    lstm_layers::Int
end

struct OptimizationResult
    config::HyperparameterConfig
    fitness::Float64
    timestamp::DateTime
    iterations::Int
end

function random_config()::HyperparameterConfig
    HyperparameterConfig(
        rand([0.0001, 0.0005, 0.001, 0.005, 0.01]),
        rand([16, 32, 64, 128]),
        rand([64, 128, 256, 512]),
        rand([0.1, 0.2, 0.3, 0.4, 0.5]),
        rand([1, 2, 3, 4])
    )
end

function evaluate_config(config::HyperparameterConfig)::Float64
    lr_score = 1.0 / (1.0 + abs(log10(config.learning_rate) + 2))
    batch_score = 1.0 / (1.0 + log2(config.batch_size))
    hidden_score = 1.0 / (1.0 + config.hidden_dim / 256)
    dropout_score = config.dropout * 0.5
    layer_score = 1.0 / (1.0 + config.lstm_layers)
    
    score = lr_score + batch_score + hidden_score + dropout_score + layer_score
    noise = randn() * 0.05
    return clamp(score + noise, 0.0, 1.0)
end

function mutate_config(config::HyperparameterConfig, rate::Float64=0.2)::HyperparameterConfig
    lr_mutations = [0.0001, 0.0005, 0.001, 0.005, 0.01]
    batch_options = [16, 32, 64, 128]
    hidden_options = [64, 128, 256, 512]
    dropout_options = [0.1, 0.2, 0.3, 0.4, 0.5]
    layer_options = [1, 2, 3, 4]
    
    HyperparameterConfig(
        rand() < rate ? rand(lr_mutations) : config.learning_rate,
        rand() < rate ? rand(batch_options) : config.batch_size,
        rand() < rate ? rand(hidden_options) : config.hidden_dim,
        rand() < rate ? rand(dropout_options) : config.dropout,
        rand() < rate ? rand(layer_options) : config.lstm_layers
    )
end

function crossover(parent1::HyperparameterConfig, parent2::HyperparameterConfig)::HyperparameterConfig
    HyperparameterConfig(
        rand(Bool) ? parent1.learning_rate : parent2.learning_rate,
        rand(Bool) ? parent1.batch_size : parent2.batch_size,
        rand(Bool) ? parent1.hidden_dim : parent2.hidden_dim,
        rand(Bool) ? parent1.dropout : parent2.dropout,
        rand(Bool) ? parent1.lstm_layers : parent2.lstm_layers
    )
end

function genetic_search(population_size::Int=20, generations::Int=50)::OptimizationResult
    population = [random_config() for _ in 1:population_size]
    fitness_scores = [evaluate_config(c) for c in population]
    
    best_config = population[argmax(fitness_scores)]
    best_fitness = maximum(fitness_scores)
    
    for gen in 1:generations
        sorted_indices = sortperm(fitness_scores, rev=true)
        survivors = population[sorted_indices[1:div(population_size, 2)]]
        
        new_population = deepcopy(survivors)
        while length(new_population) < population_size
            p1, p2 = rand(survivors, 2)
            child = crossover(p1, p2)
            child = mutate_config(child, 0.1)
            push!(new_population, child)
        end
        
        population = new_population
        fitness_scores = [evaluate_config(c) for c in population]
        
        gen_best_idx = argmax(fitness_scores)
        if fitness_scores[gen_best_idx] > best_fitness
            best_fitness = fitness_scores[gen_best_idx]
            best_config = population[gen_best_idx]
        end
        
        if gen % 10 == 0
            println("Gen $gen: Best fitness = $(round(best_fitness, digits=4))")
        end
    end
    
    return OptimizationResult(best_config, best_fitness, now(), generations)
end

function grid_search(learning_rates, batch_sizes, hidden_dims)::Vector{OptimizationResult}
    results = OptimizationResult[]
    
    for lr in learning_rates
        for bs in batch_sizes
            for hd in hidden_dims
                config = HyperparameterConfig(lr, bs, hd, 0.3, 2)
                fitness = evaluate_config(config)
                push!(results, OptimizationResult(config, fitness, now(), 1))
            end
        end
    end
    
    return sort(results, by=r -> r.fitness, rev=true)
end

function bayesian_optimize(iterations::Int=30)::OptimizationResult
    observed = Vector{Tuple{HyperparameterConfig, Float64}}()
    best_fitness = 0.0
    best_config = random_config()
    
    for i in 1:iterations
        if i <= 5
            candidate = random_config()
        else
            candidate = mutate_config(best_config, 0.3)
        end
        
        fitness = evaluate_config(candidate)
        push!(observed, (candidate, fitness))
        
        if fitness > best_fitness
            best_fitness = fitness
            best_config = candidate
        end
        
        if i % 5 == 0
            println("Bayesian iter $i: Best = $(round(best_fitness, digits=4))")
        end
    end
    
    return OptimizationResult(best_config, best_fitness, now(), iterations)
end

function random_search(iterations::Int=100)::OptimizationResult
    best_config = random_config()
    best_fitness = evaluate_config(best_config)
    
    for _ in 1:iterations
        candidate = random_config()
        fitness = evaluate_config(candidate)
        if fitness > best_fitness
            best_fitness = fitness
            best_config = candidate
        end
    end
    
    return OptimizationResult(best_config, best_fitness, now(), iterations)
end

function print_result(result::OptimizationResult)
    println("\n" * "="^60)
    println("OPTIMIZATION RESULT")
    println("="^60)
    println("Learning Rate: $(result.config.learning_rate)")
    println("Batch Size:    $(result.config.batch_size)")
    println("Hidden Dim:    $(result.config.hidden_dim)")
    println("Dropout:       $(result.config.dropout)")
    println("LSTM Layers:   $(result.config.lstm_layers)")
    println("-"^60)
    println("Fitness:       $(round(result.fitness, digits=4))")
    println("Iterations:    $(result.iterations)")
    println("Timestamp:     $(result.timestamp)")
    println("="^60)
end

end
