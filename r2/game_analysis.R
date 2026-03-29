# P117: R v2 - Advanced Statistical Analysis
library(ggplot2)

Unit <- function(id, health, damage, x, y) {
  list(id = id, health = health, damage = damage, x = x, y = y)
}

calculate_power <- function(units) {
  sum(sapply(units, function(u) u$health * u$damage)) / 100
}

find_threats <- function(units) {
  threats <- list()
  for (u in units) {
    nearby <- sum(sapply(units, function(e) {
      if (e$id != u$id && distance(u, e) < 50) 1 else 0
    }))
    threats[[as.character(u$id)]] <- nearby * 10
  }
  threats
}

distance <- function(a, b) {
  sqrt((a$x - b$x)^2 + (a$y - b$y)^2)
}

combat_simulation <- function(n_units, n_steps) {
  units <- lapply(1:n_units, function(i) {
    Unit(i, runif(1, 30, 100), runif(1, 5, 20), runif(1, 0, 100), runif(1, 0, 100))
  })
  
  power_history <- numeric(n_steps)
  for (step in 1:n_steps) {
    power_history[step] <- calculate_power(units)
  }
  
  data.frame(step = 1:n_steps, power = power_history)
}

plot_battle_trend <- function(history) {
  ggplot(history, aes(x = step, y = power)) +
    geom_line(color = "blue") +
    labs(title = "Battle Power Over Time", x = "Time Step", y = "Combat Power")
}

units <- list(Unit(1, 40, 5, 10, 10), Unit(2, 80, 10, 20, 20))
cat("Power:", calculate_power(units), "\n")
