package main

import "testing"

func TestCalculateSwarmDamage(t *testing.T) {
	if calculateSwarmDamage(10) != 50 {
		t.Error("Expected 50")
	}
}
