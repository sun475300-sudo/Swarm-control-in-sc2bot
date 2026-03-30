# @version ^0.3.10
# @title SC2 Battle Record — Immutable Zerg match history
# @notice Stores ZvT / ZvZ / ZvP results on-chain; provides win-rate queries.

# -----------------------------------------------------------------------
# Structs
# -----------------------------------------------------------------------

struct BattleResult:
    player1:  address
    player2:  address
    winner:   address
    matchup:  String[4]    # "ZvT" | "ZvZ" | "ZvP"
    duration: uint256      # seconds
    timestamp: uint256

# -----------------------------------------------------------------------
# Storage
# -----------------------------------------------------------------------

battles: DynArray[BattleResult, 10000]
battle_count: uint256

# -----------------------------------------------------------------------
# Events
# -----------------------------------------------------------------------

event BattleRecorded:
    battle_id: indexed(uint256)
    winner:    indexed(address)
    matchup:   String[4]
    duration:  uint256

# -----------------------------------------------------------------------
# External functions
# -----------------------------------------------------------------------

@external
def record_battle(
    player1:  address,
    player2:  address,
    winner:   address,
    matchup:  String[4],
    duration: uint256
):
    """Record an immutable battle result."""
    assert winner == player1 or winner == player2, "Winner must be a participant"
    assert len(matchup) == 3, "Matchup must be ZvT, ZvZ, or ZvP"

    result: BattleResult = BattleResult({
        player1:   player1,
        player2:   player2,
        winner:    winner,
        matchup:   matchup,
        duration:  duration,
        timestamp: block.timestamp
    })
    self.battles.append(result)

    battle_id: uint256 = self.battle_count
    self.battle_count += 1

    log BattleRecorded(battle_id, winner, matchup, duration)

@view
@external
def get_win_rate(player: address) -> (uint256, uint256):
    """Returns (wins, total_games) for the given player."""
    wins:  uint256 = 0
    total: uint256 = 0

    for b in self.battles:
        if b.player1 == player or b.player2 == player:
            total += 1
            if b.winner == player:
                wins += 1

    return wins, total

@view
@external
def get_battle(battle_id: uint256) -> BattleResult:
    """Returns the battle result at the given index."""
    assert battle_id < self.battle_count, "Battle ID out of range"
    return self.battles[battle_id]

@view
@external
def total_battles() -> uint256:
    return self.battle_count
