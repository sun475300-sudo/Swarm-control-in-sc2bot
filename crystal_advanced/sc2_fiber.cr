require "json"

# --- Data Models ---

record GameState,
  game_id:     String,
  minerals:    Int32,
  vespene:     Int32,
  supply_used: Int32,
  supply_cap:  Int32,
  tick:        Int64 do
  include JSON::Serializable
end

record ReplayAnalysis,
  game_id:    String,
  win_rate:   Float64,
  avg_apm:    Int32,
  key_events: Array(String) do
  include JSON::Serializable
end

# --- Channel types for inter-fiber communication ---

alias GameEventChannel   = Channel(String)
alias AnalysisChannel    = Channel(ReplayAnalysis)
alias ResultChannel      = Channel(GameState)

# --- Fetch game state (simulated async) ---

def fetch_game_state(game_id : String) : GameState
  sleep 0.05
  GameState.new(
    game_id:     game_id,
    minerals:    300,
    vespene:     150,
    supply_used: 24,
    supply_cap:  44,
    tick:        Time.utc.to_unix_ms
  )
end

# --- Analyze replay (simulated heavy computation) ---

def analyze_replay(path : String) : ReplayAnalysis
  sleep 0.1
  ReplayAnalysis.new(
    game_id:    path,
    win_rate:   0.64,
    avg_apm:    188,
    key_events: ["Early pool", "Ling flood at 3:30", "Base trade"]
  )
end

# --- Game event producer fiber ---

def start_event_producer(channel : GameEventChannel, game_id : String)
  spawn do
    events = ["unit_created", "resource_update", "unit_killed", "resource_update", "game_ended"]
    events.each do |event|
      sleep 0.05
      channel.send("#{game_id}:#{event}")
    end
    channel.close
  end
end

# --- Game event consumer fiber ---

def start_event_consumer(channel : GameEventChannel, result_ch : Channel(Int32))
  spawn do
    count = 0
    while (event = channel.receive?)
      count += 1
      puts "  [consumer] #{event}"
    end
    result_ch.send(count)
  end
end

# --- Parallel replay analysis using spawn ---

def analyze_replays_parallel(paths : Array(String)) : Array(ReplayAnalysis)
  ch = AnalysisChannel.new(paths.size)

  paths.each do |path|
    spawn do
      result = analyze_replay(path)
      ch.send(result)
    end
  end

  paths.size.times.map { ch.receive }.to_a
end

# --- Main ---

puts "SC2 Crystal Fiber Bot starting..."

# 1. Parallel game state fetches via fibers
state_channels = Array(ResultChannel).new
game_ids       = ["game-001", "game-002", "game-003"]

game_ids.each do |gid|
  ch = ResultChannel.new(1)
  state_channels << ch
  spawn do
    state = fetch_game_state(gid)
    ch.send(state)
  end
end

states = state_channels.map(&.receive)
puts "Fetched #{states.size} game states:"
states.each { |s| puts "  #{s.game_id}: #{s.minerals} minerals, #{s.supply_used}/#{s.supply_cap} supply" }

# 2. Parallel replay analysis
puts "\nAnalyzing replays in parallel..."
replays  = ["r1.SC2Replay", "r2.SC2Replay", "r3.SC2Replay"]
analyses = analyze_replays_parallel(replays)
avg_win  = analyses.sum(&.win_rate) / analyses.size
puts "Analyzed #{analyses.size} replays, avg win rate: #{(avg_win * 100).round(1)}%"

# 3. Event bus via Channel
puts "\nStreaming game events:"
event_ch  = GameEventChannel.new(10)
result_ch = Channel(Int32).new(1)

start_event_producer(event_ch, "game-001")
start_event_consumer(event_ch, result_ch)

total_events = result_ch.receive
puts "Total events processed: #{total_events}"

puts "\nDone."
