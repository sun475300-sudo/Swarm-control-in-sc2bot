// =============================================================
// SC2 Bot Combat Simulation — Carbon Language
// package SC2Bot api
// Demonstrates Carbon syntax: fn, var, let, match, class,
// Cpp interop, slice iteration, and return type inference.
// =============================================================

package SC2Bot api;

import Cpp library "combat_math.h";
import Core library "io";
import Core library "math";

// ── Enums ─────────────────────────────────────────────────────────────
enum UnitType {
  Zergling,
  Roach,
  Ravager,
  Hydralisk,
  Mutalisk,
  SiegeTank,
  Marine,
  Colossus,
  Stalker,
}

enum Race {
  Zerg,
  Terran,
  Protoss,
}

// ── Struct: CombatUnit ────────────────────────────────────────────────
class CombatUnit {
  var hp:        i32;
  var max_hp:    i32;
  var damage:    f32;
  var armor:     f32;
  var attack_spd: f32;   // attacks per second
  var range:     f32;
  var unit_type: UnitType;
  var race:      Race;
  var is_alive:  bool;

  fn Init[addr self: Self](
    t: UnitType, r: Race, h: i32, dmg: f32, arm: f32, spd: f32, rng: f32
  ) {
    self->unit_type  = t;
    self->race       = r;
    self->hp         = h;
    self->max_hp     = h;
    self->damage     = dmg;
    self->armor      = arm;
    self->attack_spd = spd;
    self->range      = rng;
    self->is_alive   = true;
  }

  // Effective DPS after armor reduction, minimum 0.5 damage per hit
  fn DPS[self: Self]() -> f32 {
    let raw_dmg: f32 = self.damage - self.armor;
    let eff_dmg: f32 = if raw_dmg > 0.5 { raw_dmg } else { 0.5 };
    return eff_dmg * self.attack_spd;
  }

  fn TakeDamage[addr self: Self](dmg: f32) {
    let reduced: f32 = dmg - self.armor;
    let actual: f32  = if reduced > 0.5 { reduced } else { 0.5 };
    self->hp = self->hp - actual as i32;
    if self->hp <= 0 {
      self->hp       = 0;
      self->is_alive = false;
    }
  }

  fn HpPercent[self: Self]() -> f32 {
    return (self.hp as f32) / (self.max_hp as f32) * 100.0;
  }
}

// ── Struct: SimResult ─────────────────────────────────────────────────
class SimResult {
  var attacker_wins:   bool;
  var rounds:          i32;
  var attacker_losses: i32;
  var defender_losses: i32;
  var avg_hp_remaining: f32;
  var total_damage_dealt: f32;
}

// ── Factory: default units ────────────────────────────────────────────
fn MakeZergling() -> CombatUnit {
  var u: CombatUnit;
  u.Init(UnitType.Zergling, Race.Zerg, 35, 5.0, 0.0, 1.4, 0.1);
  return u;
}

fn MakeRoach() -> CombatUnit {
  var u: CombatUnit;
  u.Init(UnitType.Roach, Race.Zerg, 145, 16.0, 1.0, 1.0, 4.0);
  return u;
}

fn MakeMarine() -> CombatUnit {
  var u: CombatUnit;
  u.Init(UnitType.Marine, Race.Terran, 45, 6.0, 0.0, 1.15, 5.0);
  return u;
}

fn MakeSiegeTank() -> CombatUnit {
  var u: CombatUnit;
  u.Init(UnitType.SiegeTank, Race.Terran, 175, 35.0, 1.0, 0.59, 13.0);
  return u;
}

fn MakeStalker() -> CombatUnit {
  var u: CombatUnit;
  u.Init(UnitType.Stalker, Race.Protoss, 80, 13.0, 1.0, 0.86, 6.0);
  return u;
}

// ── fn CalculateDPS: aggregate DPS for a group ────────────────────────
fn CalculateDPS(units: Slice(CombatUnit)) -> f32 {
  var total: f32 = 0.0;
  for (unit: CombatUnit in units) {
    if unit.is_alive {
      total = total + unit.DPS();
    }
  }
  return total;
}

// ── fn AliveCount ─────────────────────────────────────────────────────
fn AliveCount(units: Slice(CombatUnit)) -> i32 {
  var count: i32 = 0;
  for (unit: CombatUnit in units) {
    if unit.is_alive {
      count = count + 1;
    }
  }
  return count;
}

// ── fn AverageHp ──────────────────────────────────────────────────────
fn AverageHp(units: Slice(CombatUnit)) -> f32 {
  var total: f32 = 0.0;
  var alive: i32 = 0;
  for (unit: CombatUnit in units) {
    if unit.is_alive {
      total = total + unit.HpPercent();
      alive = alive + 1;
    }
  }
  return if alive > 0 { total / (alive as f32) } else { 0.0 };
}

// ── fn SimulateCombat: main simulation loop ───────────────────────────
fn SimulateCombat(
  attackers: Slice(CombatUnit),
  defenders: Slice(CombatUnit)
) -> SimResult {
  let MAX_ROUNDS: i32 = 500;
  var round: i32 = 0;
  var total_damage: f32 = 0.0;

  // Simulate in 1-second ticks until one side is eliminated
  while round < MAX_ROUNDS {
    let a_alive: i32 = AliveCount(attackers);
    let d_alive: i32 = AliveCount(defenders);

    if a_alive == 0 or d_alive == 0 {
      break;
    }

    // Compute DPS for each side
    let a_dps: f32 = CalculateDPS(attackers);
    let d_dps: f32 = CalculateDPS(defenders);

    // Distribute damage evenly among alive targets (simplified model)
    if d_alive > 0 {
      let dmg_each: f32 = a_dps / (d_alive as f32);
      for (var def: CombatUnit in defenders) {
        if def.is_alive {
          def.TakeDamage(dmg_each);
          total_damage = total_damage + dmg_each;
        }
      }
    }

    if a_alive > 0 {
      let dmg_each: f32 = d_dps / (a_alive as f32);
      for (var att: CombatUnit in attackers) {
        if att.is_alive {
          att.TakeDamage(dmg_each);
        }
      }
    }

    round = round + 1;
  }

  let final_a: i32 = AliveCount(attackers);
  let final_d: i32 = AliveCount(defenders);

  var result: SimResult;
  result.attacker_wins    = final_a > 0 and final_d == 0;
  result.rounds           = round;
  result.attacker_losses  = match attackers.size() - final_a as i32 {
    n => n
  };
  result.defender_losses  = match defenders.size() - final_d as i32 {
    n => n
  };
  result.avg_hp_remaining  = AverageHp(attackers);
  result.total_damage_dealt = total_damage;
  return result;
}

// ── fn PrintResult ────────────────────────────────────────────────────
fn PrintResult(r: SimResult) {
  Core.IO.Print("=== Combat Simulation Result ===\n");
  Core.IO.Print("Winner: ");
  if r.attacker_wins {
    Core.IO.Print("Attacker\n");
  } else {
    Core.IO.Print("Defender\n");
  }
  Core.IO.Print("Rounds: {0}\n", r.rounds);
  Core.IO.Print("Attacker losses: {0}\n", r.attacker_losses);
  Core.IO.Print("Defender losses: {0}\n", r.defender_losses);
  Core.IO.Print("Avg HP remaining: {0:.1}%\n", r.avg_hp_remaining);
  Core.IO.Print("Total damage dealt: {0:.1}\n", r.total_damage_dealt);
}

// ── Entry point ───────────────────────────────────────────────────────
fn Run() {
  // ZvT scenario: 8 Roaches vs 6 Marines + 1 Siege Tank
  var attackers: Array(CombatUnit, 8);
  for (var i: i32 = 0; i < 8; ++i) {
    attackers[i] = MakeRoach();
  }

  var defenders: Array(CombatUnit, 7);
  for (var i: i32 = 0; i < 6; ++i) {
    defenders[i] = MakeMarine();
  }
  defenders[6] = MakeSiegeTank();

  let result: SimResult = SimulateCombat(attackers, defenders);
  PrintResult(result);
}
