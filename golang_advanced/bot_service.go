// Phase 546: Go Advanced
// SC2 Bot microservice with goroutines, channels, generics

package main

import (
	"context"
	"fmt"
	"math"
	"math/rand"
	"sync"
	"time"
)

// ─────────────────────────────────────────────
// Domain types
// ─────────────────────────────────────────────

type Race int

const (
	Zerg Race = iota
	Terran
	Protoss
)

type UnitType string

const (
	Drone     UnitType = "drone"
	Zergling  UnitType = "zergling"
	Roach     UnitType = "roach"
	Hydralisk UnitType = "hydralisk"
	Mutalisk  UnitType = "mutalisk"
	Overlord  UnitType = "overlord"
)

type Resources struct {
	Minerals  int
	Gas       int
	Supply    int
	MaxSupply int
}

func (r Resources) CanAfford(min, gas int) bool {
	return r.Minerals >= min && r.Gas >= gas
}

func (r Resources) SupplyFull() bool {
	return r.Supply >= r.MaxSupply-1
}

type ArmyState struct {
	MySupply    int
	EnemySupply int
	ThreatLevel float64
}

type GameState struct {
	Resources  Resources
	Army       ArmyState
	Workers    int
	Frame      int
	Hatcheries int
	EnemyRace  Race
}

func NewGameState(enemy Race) GameState {
	return GameState{
		Resources:  Resources{50, 0, 12, 14},
		Army:       ArmyState{0, 0, 0.0},
		Workers:    12,
		Frame:      0,
		Hatcheries: 1,
		EnemyRace:  enemy,
	}
}

// ─────────────────────────────────────────────
// Generics: Result type
// ─────────────────────────────────────────────

type Result[T any] struct {
	Value T
	Err   error
}

func Ok[T any](v T) Result[T]  { return Result[T]{Value: v} }
func Err[T any](e error) Result[T] { return Result[T]{Err: e} }

// ─────────────────────────────────────────────
// Generics: Optional/Maybe
// ─────────────────────────────────────────────

type Option[T any] struct {
	value  T
	isSome bool
}

func Some[T any](v T) Option[T]   { return Option[T]{value: v, isSome: true} }
func None[T any]() Option[T]      { return Option[T]{} }
func (o Option[T]) Unwrap() T     { return o.value }
func (o Option[T]) IsSome() bool  { return o.isSome }

// ─────────────────────────────────────────────
// Decision engine
// ─────────────────────────────────────────────

type Action interface{ actionTag() }
type TrainUnitAction struct{ Unit UnitType }
type ExpandAction struct{}
type AttackAction struct{ X, Y float32 }
type DefendAction struct{}
type WaitAction struct{}

func (TrainUnitAction) actionTag() {}
func (ExpandAction) actionTag()    {}
func (AttackAction) actionTag()    {}
func (DefendAction) actionTag()    {}
func (WaitAction) actionTag()      {}

var unitCosts = map[UnitType][3]int{
	Drone:     {50, 0, 1},
	Zergling:  {25, 0, 1},
	Roach:     {75, 25, 2},
	Hydralisk: {100, 50, 2},
	Mutalisk:  {100, 100, 2},
	Overlord:  {100, 0, 0},
}

func decide(s GameState) Action {
	res := s.Resources

	switch {
	case s.Army.ThreatLevel > 0.6:
		return DefendAction{}
	case res.SupplyFull() && res.CanAfford(100, 0):
		return TrainUnitAction{Overlord}
	case s.Workers < 22 && res.CanAfford(50, 0):
		return TrainUnitAction{Drone}
	case res.Minerals >= 300 && s.Hatcheries < 3:
		return ExpandAction{}
	}

	switch s.EnemyRace {
	case Terran:
		if res.CanAfford(100, 50) {
			return TrainUnitAction{Hydralisk}
		}
	case Protoss:
		if res.CanAfford(75, 25) {
			return TrainUnitAction{Roach}
		}
	}
	if res.CanAfford(25, 0) {
		return TrainUnitAction{Zergling}
	}
	return WaitAction{}
}

func tick(s GameState) GameState {
	income := s.Workers * 8 / 10
	s.Resources.Minerals += income
	s.Frame++
	s.Army.ThreatLevel = math.Min(1.0, s.Army.ThreatLevel+0.0001)
	return s
}

func applyAction(s GameState, action Action) GameState {
	switch a := action.(type) {
	case TrainUnitAction:
		cost, ok := unitCosts[a.Unit]
		if !ok { return s }
		if !s.Resources.CanAfford(cost[0], cost[1]) { return s }
		s.Resources.Minerals -= cost[0]
		s.Resources.Gas -= cost[1]
		if a.Unit == Drone {
			s.Workers++
		} else if a.Unit == Overlord {
			s.Resources.MaxSupply += 8
		} else {
			s.Army.MySupply += cost[2]
		}
		s.Resources.Supply += cost[2]
	case ExpandAction:
		if s.Resources.CanAfford(300, 0) {
			s.Resources.Minerals -= 300
			s.Hatcheries++
			s.Workers += 4
		}
	}
	return s
}

func step(s GameState) GameState {
	s = tick(s)
	return applyAction(s, decide(s))
}

// ─────────────────────────────────────────────
// Concurrent multi-game runner
// ─────────────────────────────────────────────

type GameResult struct {
	GameID    int
	FinalState GameState
	Duration  time.Duration
}

func runGame(ctx context.Context, id int, frames int, race Race) GameResult {
	start := time.Now()
	s := NewGameState(race)
	for i := 0; i < frames; i++ {
		select {
		case <-ctx.Done():
			return GameResult{GameID: id, FinalState: s, Duration: time.Since(start)}
		default:
			s = step(s)
		}
	}
	return GameResult{GameID: id, FinalState: s, Duration: time.Since(start)}
}

func runTournament(n int, framesPerGame int) []GameResult {
	races := []Race{Zerg, Terran, Protoss}
	results := make([]GameResult, n)

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	var wg sync.WaitGroup
	ch := make(chan GameResult, n)

	for i := 0; i < n; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			race := races[id%len(races)]
			result := runGame(ctx, id, framesPerGame, race)
			ch <- result
		}(i)
	}

	go func() {
		wg.Wait()
		close(ch)
	}()

	i := 0
	for r := range ch {
		results[i] = r
		i++
	}
	return results[:i]
}

// ─────────────────────────────────────────────
// Pipeline with channels
// ─────────────────────────────────────────────

func generateStates(ctx context.Context, initial GameState, n int) <-chan GameState {
	out := make(chan GameState, 10)
	go func() {
		defer close(out)
		s := initial
		for i := 0; i < n; i++ {
			select {
			case <-ctx.Done():
				return
			case out <- s:
				s = step(s)
			}
		}
	}()
	return out
}

func filterHighThreat(ctx context.Context, in <-chan GameState) <-chan GameState {
	out := make(chan GameState, 10)
	go func() {
		defer close(out)
		for s := range in {
			select {
			case <-ctx.Done():
				return
			default:
				if s.Army.ThreatLevel > 0.3 {
					out <- s
				}
			}
		}
	}()
	return out
}

// ─────────────────────────────────────────────
// Main
// ─────────────────────────────────────────────

func main() {
	fmt.Println("Phase 546: Go Advanced — SC2 Bot Service")

	// Single game simulation
	rand.Seed(42)
	s := NewGameState(Terran)
	for i := 0; i < 2000; i++ {
		s = step(s)
	}
	fmt.Printf("Frame:%d | Minerals:%d | Workers:%d | Army:%d | Supply:%d/%d\n",
		s.Frame, s.Resources.Minerals, s.Workers, s.Army.MySupply,
		s.Resources.Supply, s.Resources.MaxSupply)

	// Tournament (concurrent)
	fmt.Println("\nRunning 8-game tournament...")
	results := runTournament(8, 1000)
	for _, r := range results {
		s := r.FinalState
		fmt.Printf("  Game %d: frame=%d minerals=%d army=%d (%.2fms)\n",
			r.GameID, s.Frame, s.Resources.Minerals, s.Army.MySupply,
			float64(r.Duration.Microseconds())/1000)
	}

	// Channel pipeline
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	initial := NewGameState(Protoss)
	states := generateStates(ctx, initial, 500)
	threats := filterHighThreat(ctx, states)
	count := 0
	for range threats {
		count++
	}
	fmt.Printf("\nHigh-threat frames (out of 500): %d\n", count)
}
