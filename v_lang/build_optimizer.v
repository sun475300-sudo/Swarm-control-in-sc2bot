// build_optimizer.v
// V language build order optimizer for StarCraft II Zerg bot.
// Evaluates a sequence of build steps against a resource budget,
// filters out unaffordable actions, and returns an optimized build order.

module main

// BuildStep represents a single construction or training action.
struct BuildStep {
	name    string  // e.g. "Spawning Pool", "Zergling", "Overlord"
	mineral int     // mineral cost
	gas     int     // vespene gas cost
	supply  int     // supply consumed (negative = provided, e.g. Overlord)
	time    f64     // build time in seconds (game time)
}

// BuildBudget tracks the current resource state of the bot.
struct BuildBudget {
mut:
	minerals      int // current mineral bank
	gas           int // current vespene gas bank
	supply_used   int // supply currently consumed
	supply_cap    int // maximum supply available
	elapsed_time  f64 // seconds elapsed in the game
}

// BuildResult holds the output of the optimizer.
struct BuildResult {
	steps         []BuildStep
	total_mineral int
	total_gas     int
	total_time    f64
	skipped       int // number of steps skipped due to resource/supply constraints
}

// can_afford returns true if the budget can cover the cost of a step.
fn can_afford(budget BuildBudget, step BuildStep) bool {
	if budget.minerals < step.mineral {
		return false
	}
	if budget.gas < step.gas {
		return false
	}
	// Supply check: only fail if the step consumes supply and we are at cap.
	// Steps with negative supply (e.g. Overlord) are always allowed.
	if step.supply > 0 && (budget.supply_used + step.supply) > budget.supply_cap {
		return false
	}
	return true
}

// apply_step deducts costs and advances the budget after a step is scheduled.
fn apply_step(mut budget BuildBudget, step BuildStep) {
	budget.minerals    -= step.mineral
	budget.gas         -= step.gas
	budget.supply_used += step.supply   // negative supply (Overlord) reduces used count
	budget.elapsed_time += step.time
}

// optimize_build_order filters and reorders BuildSteps so that only steps
// affordable within the running budget are kept, in the order they appear.
// Steps that cannot be afforded at their original position are skipped.
fn optimize_build_order(steps []BuildStep, budget BuildBudget) BuildResult {
	mut b        := budget
	mut accepted := []BuildStep{}
	mut skipped  := 0

	for step in steps {
		if can_afford(b, step) {
			apply_step(mut b, step)
			accepted << step
		} else {
			// Log the skipped step for diagnostic purposes.
			eprintln('[optimizer] skipped "${step.name}": need ${step.mineral}m/${step.gas}g supply+${step.supply}, have ${b.minerals}m/${b.gas}g cap=${b.supply_cap}')
			skipped++
		}
	}

	// Compute aggregate statistics for the accepted plan.
	mut total_mineral := 0
	mut total_gas     := 0
	mut total_time    := f64(0)
	for s in accepted {
		total_mineral += s.mineral
		total_gas     += s.gas
		total_time    += s.time
	}

	return BuildResult{
		steps:         accepted
		total_mineral: total_mineral
		total_gas:     total_gas
		total_time:    total_time
		skipped:       skipped
	}
}

fn main() {
	// Example Zerg opening build order (12-pool into ling-speed).
	steps := [
		BuildStep{ name: 'Drone x6',        mineral: 300, gas: 0,  supply:  6, time: 42.0 },
		BuildStep{ name: 'Overlord',         mineral: 100, gas: 0,  supply: -8, time: 18.0 },
		BuildStep{ name: 'Drone x3',         mineral: 150, gas: 0,  supply:  3, time: 21.0 },
		BuildStep{ name: 'Spawning Pool',    mineral: 200, gas: 0,  supply:  0, time: 46.0 },
		BuildStep{ name: 'Extractor',        mineral:  75, gas: 0,  supply:  0, time: 21.0 },
		BuildStep{ name: 'Zergling x4',      mineral: 200, gas: 0,  supply:  4, time: 24.0 },
		BuildStep{ name: 'Metabolic Boost',  mineral: 100, gas: 100, supply: 0, time: 110.0 },
	]

	// Starting budget: 12-pool timing (roughly 50-drone minerals by 12 supply).
	budget := BuildBudget{
		minerals:     500
		gas:          150
		supply_used:  12
		supply_cap:   18
		elapsed_time: 0.0
	}

	result := optimize_build_order(steps, budget)

	println('=== Optimized Build Order ===')
	for i, s in result.steps {
		println('  ${i+1:2}. ${s.name:-20} | ${s.mineral:4}m ${s.gas:3}g | ${s.time:6.1f}s')
	}
	println('-----------------------------')
	println('  Total cost : ${result.total_mineral}m / ${result.total_gas}g')
	println('  Total time : ${result.total_time:.1f}s')
	println('  Skipped    : ${result.skipped} step(s)')
}
