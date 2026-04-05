# Phase 197: Nim
proc calculateSwarmDamage*(count: int): int =
  result = count * 5

when isMainModule:
  echo calculateSwarmDamage(10)
