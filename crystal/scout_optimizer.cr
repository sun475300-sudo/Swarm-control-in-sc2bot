# scout_optimizer.cr
# Crystal fast scout path calculator for a StarCraft II Zerg bot.
# Computes an efficient scout route through enemy expansion locations using
# a nearest-neighbour heuristic — O(n²) but fast enough for ≤ 30 target sites
# given Crystal's compiled performance characteristics.

# ─────────────────────────────────────────────────────────────────────────────
# Data Structures
# ─────────────────────────────────────────────────────────────────────────────

# A map coordinate in SC2 game units.
struct Point
  property x : Float64
  property y : Float64

  def initialize(@x : Float64, @y : Float64)
  end

  # Euclidean distance to another point.
  def distance_to(other : Point) : Float64
    dx = @x - other.x
    dy = @y - other.y
    Math.sqrt(dx * dx + dy * dy)
  end

  def to_s : String
    "(#{ @x.round(1) }, #{ @y.round(1) })"
  end
end

# A single waypoint in the scout route with metadata.
struct Waypoint
  property location  : Point
  property label     : String    # e.g. "Natural", "Third Base", "Hidden Proxy"
  property priority  : Int32     # 1 = must-check, 2 = situational, 3 = low

  def initialize(@location : Point, @label : String, @priority : Int32 = 1)
  end
end

# The computed scout path: an ordered list of waypoints with total distance.
class ScoutPath
  property waypoints     : Array(Waypoint)
  property total_distance : Float64

  def initialize(@waypoints : Array(Waypoint), @total_distance : Float64)
  end

  # Human-readable route summary for logging / UI.
  def to_s : String
    lines = ["Scout path (total distance: #{ @total_distance.round(1) } units):"]
    @waypoints.each_with_index do |wp, i|
      lines << "  #{ i + 1 }. #{ wp.label } @ #{ wp.location } [priority #{ wp.priority }]"
    end
    lines.join('\n')
  end

  # Total estimated travel time in seconds at a given unit speed (u/s).
  def estimated_time(speed : Float64 = 3.75) : Float64
    @total_distance / speed
  end
end

# ─────────────────────────────────────────────────────────────────────────────
# Scout Path Calculator
# ─────────────────────────────────────────────────────────────────────────────

class ScoutOptimizer
  # Maximum distance to consider two overlapping bases as a single cluster.
  CLUSTER_THRESHOLD = 8.0

  # Compute the optimal scout path from `start` visiting all `targets`.
  # High-priority waypoints are sorted to the front before the greedy pass.
  def calculate_optimal_path(start : Point, targets : Array(Waypoint)) : ScoutPath
    return ScoutPath.new([] of Waypoint, 0.0) if targets.empty?

    # Sort by priority first (1 before 2 before 3) so critical spots come early.
    sorted = targets.sort_by(&.priority)

    visited   = [] of Waypoint
    remaining = sorted.dup
    current   = start
    total     = 0.0

    # Nearest-neighbour greedy traversal.
    until remaining.empty?
      nearest = find_nearest(current, remaining)
      total += current.distance_to(nearest.location)
      visited  << nearest
      remaining.delete(nearest)
      current = nearest.location
    end

    ScoutPath.new(visited, total)
  end

  # Suggest the best initial scouting target given the start position and
  # a list of possible enemy start locations.
  def initial_scout_target(start : Point, enemy_starts : Array(Point)) : Point
    enemy_starts.min_by { |pt| start.distance_to(pt) }
  end

  # Filter out waypoints that are too close together (de-duplicate clusters).
  def deduplicate_targets(targets : Array(Waypoint)) : Array(Waypoint)
    result = [] of Waypoint
    targets.each do |candidate|
      too_close = result.any? do |existing|
        existing.location.distance_to(candidate.location) < CLUSTER_THRESHOLD
      end
      result << candidate unless too_close
    end
    result
  end

  private def find_nearest(from : Point, candidates : Array(Waypoint)) : Waypoint
    candidates.min_by { |wp| from.distance_to(wp.location) }
  end
end

# ─────────────────────────────────────────────────────────────────────────────
# Demo / Self-test
# ─────────────────────────────────────────────────────────────────────────────

puts "=== SC2 Zerg Scout Optimizer (Crystal) ==="

optimizer = ScoutOptimizer.new

# Bot's Zerg starting position (bottom-left spawn on a typical 2-player map).
zerg_start = Point.new(33.0, 30.0)

# Candidate scouting targets with priorities.
targets = [
  Waypoint.new(Point.new(130.0, 128.0), "Enemy Main Base",   1),
  Waypoint.new(Point.new(113.0, 115.0), "Enemy Natural Exp", 1),
  Waypoint.new(Point.new( 80.0,  70.0), "Map Centre Watch",  2),
  Waypoint.new(Point.new( 50.0, 110.0), "Third Base Site A", 2),
  Waypoint.new(Point.new(100.0,  40.0), "Third Base Site B", 2),
  Waypoint.new(Point.new( 20.0,  80.0), "Hidden Proxy Spot", 3),
  Waypoint.new(Point.new( 65.0,  65.0), "Gold Expansion",    3),
]

# Remove any duplicate locations.
deduped = optimizer.deduplicate_targets(targets)
puts "Targets after dedup: #{ deduped.size } / #{ targets.size }"

# Calculate the scout route.
path = optimizer.calculate_optimal_path(zerg_start, deduped)
puts "\n#{ path }"
puts "\nEstimated scout time @ 3.75 u/s: #{ path.estimated_time.round(1) }s"
puts "Estimated scout time @ 5.00 u/s: #{ path.estimated_time(5.0).round(1) }s"

# Show the best first target if multiple spawns are possible.
possible_spawns = [
  Point.new(130.0, 128.0),
  Point.new( 33.0, 128.0),
  Point.new(130.0,  30.0),
]
best_first = optimizer.initial_scout_target(zerg_start, possible_spawns)
puts "\nBest first enemy spawn to check: #{ best_first }"
