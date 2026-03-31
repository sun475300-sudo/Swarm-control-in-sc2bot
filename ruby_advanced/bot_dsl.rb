#!/usr/bin/env ruby
# frozen_string_literal: true
# Phase 548: Ruby Advanced
# SC2 Bot DSL with metaprogramming, fibers, and pattern matching

# ─────────────────────────────────────────────
# Strategy DSL using class-level macros
# ─────────────────────────────────────────────

module SC2Bot
  module DSL
    def self.included(base)
      base.extend(ClassMethods)
      base.instance_variable_set(:@rules, [])
      base.instance_variable_set(:@transitions, [])
    end

    module ClassMethods
      def rule(name, &condition)
        @rules << { name: name, condition: condition }
      end

      def transition(from:, to:, when: nil, &block)
        @transitions << {
          from: from,
          to:   to,
          when: binding.local_variable_get(:when),
          action: block,
        }
      end

      def rules      = @rules
      def transitions = @transitions
    end

    def evaluate_rules(state)
      self.class.rules.filter_map do |rule|
        rule[:name] if rule[:condition].call(state)
      end
    end

    def transition_to(from_phase, state)
      self.class.transitions.find do |t|
        t[:from] == from_phase &&
          (t[:when].nil? || t[:when].call(state))
      end&.then do |t|
        t[:action]&.call(state)
        t[:to]
      end || from_phase
    end
  end
end

# ─────────────────────────────────────────────
# Game state as struct
# ─────────────────────────────────────────────

GameState = Struct.new(
  :minerals, :gas, :supply, :max_supply,
  :workers, :army, :frame, :hatcheries,
  :threat, :enemy_race,
  keyword_init: true
) do
  def supply_ratio = supply.to_f / [max_supply, 1].max
  def can_afford?(m, g = 0) = minerals >= m && gas >= g
  def under_threat? = threat > 0.6
  def phase
    case frame
    when 0...1344  then :opening
    when 1344...3360 then :early
    when 3360...6720 then :mid
    else :late
    end
  end
end

# ─────────────────────────────────────────────
# Bot strategy with DSL
# ─────────────────────────────────────────────

class ZergStrategy
  include SC2Bot::DSL

  UNIT_COSTS = {
    drone:     { minerals: 50,  gas: 0,  supply: 1 },
    zergling:  { minerals: 25,  gas: 0,  supply: 1 },
    roach:     { minerals: 75,  gas: 25, supply: 2 },
    hydralisk: { minerals: 100, gas: 50, supply: 2 },
    mutalisk:  { minerals: 100, gas: 100, supply: 2 },
    overlord:  { minerals: 100, gas: 0,  supply: 0 },
  }.freeze

  rule(:under_threat)  { |s| s.under_threat? }
  rule(:supply_full)   { |s| s.supply_ratio >= 0.95 }
  rule(:need_workers)  { |s| s.workers < 22 }
  rule(:can_expand)    { |s| s.minerals >= 300 && s.hatcheries < 3 }
  rule(:can_attack)    { |s| s.army >= 20 && !s.under_threat? }

  transition(from: :early, to: :mid, when: ->(s) { s.workers >= 18 })
  transition(from: :mid,   to: :late, when: ->(s) { s.hatcheries >= 2 })

  def decide(state)
    active_rules = evaluate_rules(state)
    res = state

    if active_rules.include?(:under_threat)
      :defend
    elsif active_rules.include?(:supply_full) && res.can_afford?(100)
      [:train, :overlord]
    elsif active_rules.include?(:need_workers) && res.can_afford?(50)
      [:train, :drone]
    elsif active_rules.include?(:can_expand)
      :expand
    elsif res.can_afford?(75, 25)
      case res.enemy_race
      when :terran  then [:train, :hydralisk]
      when :protoss then [:train, :roach]
      else               [:train, :zergling]
      end
    else
      :wait
    end
  end
end

# ─────────────────────────────────────────────
# Economy simulator
# ─────────────────────────────────────────────

class EconomySimulator
  attr_reader :state, :history

  def initialize(enemy_race: :terran)
    @state = GameState.new(
      minerals: 50, gas: 0, supply: 12, max_supply: 14,
      workers: 12, army: 0, frame: 0, hatcheries: 1,
      threat: 0.0, enemy_race: enemy_race
    )
    @strategy = ZergStrategy.new
    @history  = []
  end

  def tick
    income = @state.workers * 8 / 10
    @state = @state.dup
    @state.minerals += income
    @state.frame    += 1
    @state.threat    = [@state.threat + 0.0001, 1.0].min
    @history << @state.dup
    self
  end

  def apply_action(action)
    case action
    in [:train, unit]
      cost = ZergStrategy::UNIT_COSTS[unit]
      return self unless cost && @state.can_afford?(cost[:minerals], cost[:gas])
      @state = @state.dup
      @state.minerals -= cost[:minerals]
      @state.gas      -= cost[:gas]
      if unit == :drone
        @state.workers += 1
      elsif unit == :overlord
        @state.max_supply += 8
      else
        @state.army += cost[:supply]
      end
      @state.supply += cost[:supply]
    in :expand
      return self unless @state.can_afford?(300)
      @state = @state.dup
      @state.minerals   -= 300
      @state.hatcheries += 1
      @state.workers    += 4
    else
      # wait/defend — no change
    end
    self
  end

  def step
    tick
    action = @strategy.decide(@state)
    apply_action(action)
    self
  end

  def run(frames)
    frames.times { step }
    self
  end

  def report
    s = @state
    "Frame:#{s.frame} | Minerals:#{s.minerals} | Workers:#{s.workers} | " \
      "Army:#{s.army} | Supply:#{s.supply}/#{s.max_supply} | Phase:#{s.phase}"
  end
end

# ─────────────────────────────────────────────
# Fiber-based coroutine game loop
# ─────────────────────────────────────────────

def create_bot_fiber(enemy_race: :protoss)
  sim = EconomySimulator.new(enemy_race: enemy_race)
  Fiber.new do
    loop do
      sim.step
      Fiber.yield(sim.state)
    end
  end
end

# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

puts "Phase 548: Ruby Advanced — SC2 Bot DSL"

sim = EconomySimulator.new(enemy_race: :terran)
sim.run(2000)
puts sim.report

# Analytics with Enumerable
minerals_over_time = sim.history.map(&:minerals)
puts "\nMinerals stats:"
puts "  Min: #{minerals_over_time.min}"
puts "  Max: #{minerals_over_time.max}"
puts "  Avg: #{minerals_over_time.sum.to_f / minerals_over_time.size}"

# Fiber demo
bot_fiber = create_bot_fiber(enemy_race: :zerg)
10.times do |i|
  state = bot_fiber.resume
  puts "  Fiber step #{i+1}: minerals=#{state.minerals}" if (i+1) % 3 == 0
end

# Ruby pattern matching
state = sim.state
result = case state
in { minerals: (500..) }
  "Rich — consider expanding"
in { threat: (0.5..) }
  "Threatened — defend!"
in { workers: (..16) }
  "Need more workers"
else
  "Normal economy"
end
puts "\nStrategy advisor: #{result}"
