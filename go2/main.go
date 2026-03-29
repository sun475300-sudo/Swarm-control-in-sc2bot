package main

import (
	"encoding/json"
	"math"
	"sync"
)

type Unit struct {
	ID     uint64  `json:"id"`
	Type   string  `json:"type"`
	Health float64 `json:"health"`
	Damage float64 `json:"damage"`
	X      float64 `json:"x"`
	Y      float64 `json:"y"`
}

type GameState struct {
	mu        sync.RWMutex
	Units     []Unit    `json:"units"`
	Resources Resources `json:"resources"`
	Enemy     []Unit    `json:"enemy"`
}

type Resources struct {
	Minerals int `json:"minerals"`
	Gas      int `json:"gas"`
	Supply   int `json:"supply"`
}

func NewGameState() *GameState {
	return &GameState{
		Units: make([]Unit, 0),
		Enemy: make([]Unit, 0),
	}
}

func (g *GameState) AddUnit(u Unit) {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.Units = append(g.Units, u)
}

func (g *GameState) CalculatePower() float64 {
	g.mu.RLock()
	defer g.mu.RUnlock()

	var power float64
	for _, u := range g.Units {
		power += u.Health * u.Damage
	}
	return power / 100.0
}

func (g *GameState) FindThreats() map[uint64]float64 {
	g.mu.RLock()
	defer g.mu.RUnlock()

	threats := make(map[uint64]float64)
	for _, u := range g.Units {
		nearby := 0
		for _, e := range g.Enemy {
			if distance(u, e) < 50.0 {
				nearby++
			}
		}
		threats[u.ID] = float64(nearby) * 10.0
	}
	return threats
}

func distance(a, b Unit) float64 {
	dx := a.X - b.X
	dy := a.Y - b.Y
	return math.Sqrt(dx*dx + dy*dy)
}

func (g *GameState) JSON() ([]byte, error) {
	g.mu.RLock()
	defer g.mu.RUnlock()
	return json.Marshal(g)
}

func main() {
	game := NewGameState()
	game.AddUnit(Unit{ID: 1, Type: "Drone", Health: 40, Damage: 5, X: 10, Y: 10})
	println("Power:", game.CalculatePower())
}
