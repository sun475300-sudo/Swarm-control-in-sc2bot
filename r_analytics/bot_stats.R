#!/usr/bin/env Rscript
# Phase 558: R Analytics
# SC2 Bot game data statistical analysis

suppressPackageStartupMessages({
  # Optional packages (loaded with graceful fallback)
  tryCatch(library(dplyr), error = function(e) NULL)
  tryCatch(library(ggplot2), error = function(e) NULL)
})

cat("Phase 558: R Analytics — SC2 Bot Game Statistics\n\n")

# ─────────────────────────────────────────────
# Game simulation in R
# ─────────────────────────────────────────────

simulate_game <- function(n_frames = 2000, seed = 42) {
  set.seed(seed)

  state <- list(
    minerals   = 50L,
    gas        = 0L,
    supply     = 12L,
    max_supply = 14L,
    workers    = 12L,
    army       = 0L,
    frame      = 0L,
    hatcheries = 1L,
    threat     = 0.0
  )

  history <- vector("list", n_frames)

  decide <- function(s) {
    supply_ratio <- s$supply / max(1, s$max_supply)
    if (s$threat > 0.6)                              return("defend")
    if (supply_ratio >= 0.95 && s$minerals >= 100)   return("overlord")
    if (s$workers < 22 && s$minerals >= 50)          return("drone")
    if (s$minerals >= 300 && s$hatcheries < 3)       return("expand")
    if (s$minerals >= 75 && s$gas >= 25)             return("roach")
    if (s$minerals >= 25)                            return("zergling")
    return("wait")
  }

  apply_action <- function(s, action) {
    switch(action,
      drone = {
        if (s$minerals >= 50) {
          s$minerals <- s$minerals - 50L
          s$workers  <- s$workers + 1L
          s$supply   <- s$supply + 1L
        }
      },
      zergling = {
        if (s$minerals >= 25) {
          s$minerals <- s$minerals - 25L
          s$army     <- s$army + 1L
          s$supply   <- s$supply + 1L
        }
      },
      roach = {
        if (s$minerals >= 75 && s$gas >= 25) {
          s$minerals <- s$minerals - 75L
          s$gas      <- s$gas - 25L
          s$army     <- s$army + 2L
          s$supply   <- s$supply + 2L
        }
      },
      overlord = {
        if (s$minerals >= 100) {
          s$minerals   <- s$minerals - 100L
          s$max_supply <- s$max_supply + 8L
        }
      },
      expand = {
        if (s$minerals >= 300) {
          s$minerals   <- s$minerals - 300L
          s$hatcheries <- s$hatcheries + 1L
          s$workers    <- s$workers + 4L
        }
      }
    )
    s
  }

  for (i in seq_len(n_frames)) {
    # Tick
    income     <- as.integer(state$workers * 8 / 10)
    state$minerals <- state$minerals + income
    state$frame    <- state$frame + 1L
    state$threat   <- min(1.0, state$threat + 0.0001)

    # Decide & apply
    action <- decide(state)
    state  <- apply_action(state, action)

    history[[i]] <- as.data.frame(state)
  }

  dplyr_available <- requireNamespace("dplyr", quietly = TRUE)
  if (dplyr_available) {
    do.call(rbind, history)
  } else {
    do.call(rbind, lapply(history, as.data.frame))
  }
}

# ─────────────────────────────────────────────
# Run simulations for multiple strategies
# ─────────────────────────────────────────────

cat("Running simulations...\n")
df <- simulate_game(n_frames = 2000)

# Basic stats
cat("\n=== Final State ===\n")
final <- tail(df, 1)
cat(sprintf("Frame:    %d\n", final$frame))
cat(sprintf("Minerals: %d\n", final$minerals))
cat(sprintf("Workers:  %d\n", final$workers))
cat(sprintf("Army:     %d\n", final$army))
cat(sprintf("Supply:   %d/%d\n", final$supply, final$max_supply))

cat("\n=== Economy Statistics ===\n")
cat(sprintf("Avg minerals: %.1f\n", mean(df$minerals)))
cat(sprintf("Max workers:  %d\n", max(df$workers)))
cat(sprintf("Max army:     %d\n", max(df$army)))
cat(sprintf("Min minerals: %d\n", min(df$minerals)))

# Growth rate analysis
frames_sampled <- df[seq(1, nrow(df), by = 200), ]
cat("\n=== Economy Trajectory (every 200 frames) ===\n")
cat(sprintf("%-8s %-10s %-10s %-10s\n", "Frame", "Minerals", "Workers", "Army"))
for (i in seq_len(nrow(frames_sampled))) {
  row <- frames_sampled[i, ]
  cat(sprintf("%-8d %-10d %-10d %-10d\n",
    row$frame, row$minerals, row$workers, row$army))
}

# ─────────────────────────────────────────────
# Statistical tests
# ─────────────────────────────────────────────

cat("\n=== Statistical Analysis ===\n")

# Mineral accumulation rate (linear model)
model <- lm(minerals ~ frame, data = df)
coef_ <- coef(model)
cat(sprintf("Mineral growth rate: %.2f minerals/frame\n", coef_["frame"]))

# Correlation analysis
cat(sprintf("Correlation workers~minerals: %.3f\n",
  cor(df$workers, df$minerals)))
cat(sprintf("Correlation army~frame:       %.3f\n",
  cor(df$army, df$frame)))

# T-test: early vs late game minerals
early <- df[df$frame <= 1000, "minerals"]
late  <- df[df$frame > 1000,  "minerals"]
test  <- t.test(early, late)
cat(sprintf("\nEarly vs Late minerals:\n"))
cat(sprintf("  Early mean: %.1f | Late mean: %.1f\n",
  mean(early), mean(late)))
cat(sprintf("  t-test p-value: %.6f\n", test$p.value))

# ─────────────────────────────────────────────
# Multi-game Monte Carlo
# ─────────────────────────────────────────────

cat("\n=== Monte Carlo (10 games) ===\n")
results <- lapply(1:10, function(seed) {
  g <- simulate_game(n_frames = 500, seed = seed)
  tail(g, 1)
})
mc_df <- do.call(rbind, results)
cat(sprintf("Avg final minerals: %.1f\n", mean(mc_df$minerals)))
cat(sprintf("Avg final army:     %.1f\n", mean(mc_df$army)))
cat(sprintf("Avg final workers:  %.1f\n", mean(mc_df$workers)))
cat(sprintf("Std dev minerals:   %.1f\n", sd(mc_df$minerals)))
