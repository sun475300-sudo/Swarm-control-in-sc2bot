# StarCraft II AI Bot - Statistical Analysis
# P82: R Language - Game Analytics & Visualization

library(ggplot2)
library(dplyr)
library(tidyr)
library(lubridate)
library(scales)
library(jsonlite)

# Load game data
load_game_data <- function(filepath = "data/games.json") {
  if (!file.exists(filepath)) {
    return(data.frame())
  }
  fromJSON(filepath)
}

# Analyze win rates by matchup
analyze_matchups <- function(data) {
  data %>%
    group_by(opponent_race, result) %>%
    summarise(count = n(), .groups = "drop") %>%
    pivot_wider(names_from = result, values_from = count, values_fill = 0) %>%
    mutate(
      total = WIN + LOSS,
      win_rate = WIN / total * 100
    ) %>%
    arrange(desc(win_rate))
}

# Analyze timing patterns
analyze_timing <- function(data) {
  data %>%
    mutate(
      game_minutes = duration_frames / (22.4 * 60),
      timing_bucket = cut(game_minutes, 
                           breaks = c(0, 5, 10, 15, 20, 30, Inf),
                           labels = c("0-5min", "5-10min", "10-15min", 
                                     "15-20min", "20-30min", "30+min"))
    ) %>%
    group_by(timing_bucket, result) %>%
    summarise(games = n(), .groups = "drop")
}

# Analyze unit composition effectiveness
analyze_unit_composition <- function(data) {
  data %>%
    unnest(unit_composition) %>%
    group_by(unit_type, result) %>%
    summarise(
      games = n(),
      avg_count = mean(count),
      .groups = "drop"
    ) %>%
    pivot_wider(names_from = result, values_from = c(games, avg_count), values_fill = 0)
}

# Plot win rate by matchup
plot_matchup_winrates <- function(data) {
  matchup_data <- analyze_matchups(data)
  
  ggplot(matchup_data, aes(x = opponent_race, y = win_rate, fill = win_rate)) +
    geom_bar(stat = "identity") +
    geom_text(aes(label = sprintf("%.1f%%", win_rate)), vjust = -0.5) +
    scale_fill_gradient(low = "#ff6b6b", high = "#51cf66") +
    labs(
      title = "Win Rate by Matchup",
      x = "Opponent Race",
      y = "Win Rate (%)"
    ) +
    theme_minimal() +
    ylim(0, 100)
}

# Plot game timing distribution
plot_timing_distribution <- function(data) {
  timing_data <- analyze_timing(data)
  
  ggplot(timing_data, aes(x = timing_bucket, y = games, fill = result)) +
    geom_bar(stat = "identity", position = "dodge") +
    scale_fill_manual(values = c("WIN" = "#51cf66", "LOSS" = "#ff6b6b")) +
    labs(
      title = "Game Duration Distribution",
      x = "Game Length (minutes)",
      y = "Number of Games"
    ) +
    theme_minimal() +
    theme(axis.text.x = element_text(angle = 45))
}

# Plot APM trends
plot_apm_trends <- function(data) {
  ggplot(data, aes(x = game_number, y = apm, color = result)) +
    geom_line() +
    geom_smooth(method = "loess") +
    scale_color_manual(values = c("WIN" = "#51cf66", "LOSS" = "#ff6b6b")) +
    labs(
      title = "APM Trends Over Games",
      x = "Game Number",
      y = "Actions Per Minute"
    ) +
    theme_minimal()
}

# Generate summary statistics
generate_summary <- function(data) {
  list(
    total_games = nrow(data),
    win_rate = sum(data$result == "WIN") / nrow(data) * 100,
    avg_game_duration = mean(data$duration_frames / 22.4 / 60),
    avg_apm = mean(data$apm),
    most_common_opponent = data$opponent_race %>% table() %>% names() %>% first(),
    best_matchup = analyze_matchups(data) %>% filter(win_rate == max(win_rate)) %>% pull(opponent_race)
  )
}

# Export analysis results
export_results <- function(data, output_dir = "analysis/output") {
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
  
  # Save CSV files
  write.csv(analyze_matchups(data), 
             file.path(output_dir, "matchup_analysis.csv"), 
             row.names = FALSE)
  write.csv(analyze_timing(data), 
             file.path(output_dir, "timing_analysis.csv"), 
             row.names = FALSE)
  
  # Save plots
  ggsave("matchup_winrates.png", plot_matchup_winrates(data), 
         path = output_dir, width = 8, height = 6)
  ggsave("timing_distribution.png", plot_timing_distribution(data), 
         path = output_dir, width = 10, height = 6)
  ggsave("apm_trends.png", plot_apm_trends(data), 
         path = output_dir, width = 10, height = 6)
  
  # Save summary
  summary <- generate_summary(data)
  write_json(summary, file.path(output_dir, "summary.json"), pretty = TRUE)
  
  cat("Analysis exported to:", output_dir, "\n")
}

# Main execution
main <- function() {
  cat("📊 SC2 AI Bot - Statistical Analysis\n")
  cat("=" * 50, "\n")
  
  data <- load_game_data()
  
  if (nrow(data) == 0) {
    cat("No data found. Using sample data...\n")
    set.seed(42)
    data <- data.frame(
      game_id = 1:100,
      opponent_race = sample(c("Terran", "Zerg", "Protoss"), 100, replace = TRUE),
      result = sample(c("WIN", "LOSS"), 100, replace = TRUE, prob = c(0.3, 0.7)),
      duration_frames = rnorm(100, mean = 10000, sd = 3000),
      apm = rnorm(100, mean = 150, sd = 30),
      unit_composition = NA
    )
  }
  
  cat("\n📈 Summary Statistics:\n")
  summary <- generate_summary(data)
  print(summary)
  
  cat("\n🎯 Generating visualizations...\n")
  export_results(data)
  
  cat("\n✅ Analysis complete!\n")
}

main()
