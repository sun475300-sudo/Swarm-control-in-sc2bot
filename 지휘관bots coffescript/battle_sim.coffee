# Wicked Zerg - Battle Simulation
# Phase 130: CoffeeScript

class BattleUnit
  constructor: (@unitType, @x, @y, @health = 100, @damage = 5, @armor = 0) ->

  getStrength: ->
    effective = @damage * @health / 100
    effective * (1 - @armor * 0.01)

battleSim = (units) ->
  units.reduce ((acc, unit) -> acc + 5), 0

calculateSwarmDamage = (count) ->
  count * 5

swarmFormation = (centerX, centerY, count, radius) ->
  positions = []
  for i in [0...count]
    angle = 2 * Math.PI * i / count
    x = centerX + radius * Math.cos(angle)
    y = centerY + radius * Math.sin(angle)
    positions.push { x, y }
  positions

unitStrength = (health, damage, armor) ->
  effective = damage * health / 100
  effective * (1 - armor * 0.01)

battleOutcome = (attackers, defenders) ->
  attackPower = attackers.reduce ((sum, u) -> sum + unitStrength(u.health, u.damage, u.armor)), 0
  defensePower = defenders.reduce ((sum, u) -> sum + unitStrength(u.health, u.damage, u.armor)), 0
  attackPower > defensePower

calculateThreats = (ourPositions, enemyPositions) ->
  threats = 0
  for ourPos in ourPositions
    minDist = Infinity
    for enemyPos in enemyPositions
      dist = Math.sqrt Math.pow(ourPos.x - enemyPos.x, 2) + Math.pow(ourPos.y - enemyPos.y, 2)
      minDist = dist if dist < minDist
    threats++ if minDist < 10
  threats

module.exports = { BattleUnit, battleSim, calculateSwarmDamage, swarmFormation, unitStrength, battleOutcome, calculateThreats }
