#!/usr/bin/env julia

using Pkg
Pkg.activate(@__DIR__)

using DrWatson
@quickactivate

using Flux
using Statistics
using Random
using Dates
using JSON
using CSV
using DataFrames

include("src/HyperparameterOptimizer.jl")
using .HyperparameterOptimizer

function generate_experiment_log(method::String, result::OptimizationResult)
    log_entry = Dict(
        "method" => method,
        "timestamp" => string(result.timestamp),
        "learning_rate" => result.config.learning_rate,
        "batch_size" => result.config.batch_size,
        "hidden_dim" => result.config.hidden_dim,
        "dropout" => result.config.dropout,
        "lstm_layers" => result.config.lstm_layers,
        "fitness" => result.fitness,
        "iterations" => result.iterations
    )
    return log_entry
end

function save_results(results::Vector{Dict}, filename::String)
    df = DataFrame(results)
    CSV.write(filename, df)
    println("Results saved to $filename")
end

function main()
    println("\n" * "="^70)
    println("🎮 StarCraft II AI - Hyperparameter Optimization Suite")
    println("="^70 * "\n")
    
    all_results = Dict{String, Vector{Dict}}()
    
    println("▶ Running Genetic Algorithm Search...")
    ga_result = genetic_search(population_size=30, generations=50)
    all_results["genetic"] = [generate_experiment_log("genetic", ga_result)]
    print_result(ga_result)
    
    println("\n▶ Running Random Search (baseline)...")
    rs_result = random_search(iterations=200)
    all_results["random"] = [generate_experiment_log("random", rs_result)]
    print_result(rs_result)
    
    println("\n▶ Running Bayesian Optimization...")
    bo_result = bayesian_optimize(iterations=40)
    all_results["bayesian"] = [generate_experiment_log("bayesian", bo_result)]
    print_result(bo_result)
    
    println("\n▶ Running Grid Search...")
    lr_range = [0.001, 0.005, 0.01]
    bs_range = [32, 64, 128]
    hd_range = [128, 256, 512]
    grid_results = grid_search(lr_range, bs_range, hd_range)
    all_results["grid"] = [generate_experiment_log("grid", r) for r in grid_results[1:5]]
    println("Top 5 grid search results:")
    for (i, r) in enumerate(grid_results[1:5])
        println("  $i. Fitness=$(round(r.fitness, digits=4)) | lr=$(r.config.learning_rate) | bs=$(r.config.batch_size) | hd=$(r.config.hidden_dim)")
    end
    
    output_dir = mkpath(joinpath(@__DIR__, "output"))
    timestamp = Dates.format(now(), "yyyy-mm-dd_HHMMSS")
    
    save_results(all_results["genetic"], joinpath(output_dir, "genetic_$timestamp.csv"))
    save_results(all_results["random"], joinpath(output_dir, "random_$timestamp.csv"))
    save_results(all_results["bayesian"], joinpath(output_dir, "bayesian_$timestamp.csv"))
    
    best_overall = argmax([ga_result, rs_result, bo_result], by=r->r.fitness)
    best_method = ["genetic", "random", "bayesian"][argmax([ga_result.fitness, rs_result.fitness, bo_result.fitness])]
    
    println("\n" * "="^70)
    println("🏆 BEST OVERALL: $best_method")
    println("="^70)
    print_result(best_overall)
    
    summary = Dict(
        "experiment_date" => string(now()),
        "methods_tested" => ["genetic", "random", "bayesian", "grid"],
        "best_method" => best_method,
        "best_config" => Dict(
            "learning_rate" => best_overall.config.learning_rate,
            "batch_size" => best_overall.config.batch_size,
            "hidden_dim" => best_overall.config.hidden_dim,
            "dropout" => best_overall.config.dropout,
            "lstm_layers" => best_overall.config.lstm_layers
        ),
        "best_fitness" => best_overall.fitness
    )
    
    open(joinpath(output_dir, "summary_$timestamp.json"), "w") do f
        JSON.print(f, summary, 4)
    end
    
    println("\n✅ Optimization complete! Results saved to $(output_dir)")
end

if abspath(PROGRAM_FILE) == @__FILE__
    main()
end
