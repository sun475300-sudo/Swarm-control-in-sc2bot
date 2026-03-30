// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/IERC721Metadata.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

/// @title SC2 Ladder Tournament — Zerg AI Bot League
/// @notice On-chain ELO ladder with NFT achievement minting for top 3 players
contract LadderTournament is Ownable {
    using Counters for Counters.Counter;

    // -----------------------------------------------------------------------
    // Data structures
    // -----------------------------------------------------------------------

    struct Player {
        address wallet;
        uint32  wins;
        uint32  losses;
        int32   elo_rating;
        bool    registered;
    }

    // -----------------------------------------------------------------------
    // State
    // -----------------------------------------------------------------------

    mapping(address => Player) public players;
    address[]                  private playerList;

    Counters.Counter private _tokenIdCounter;

    // ELO constants
    int32 constant K_FACTOR       = 32;
    int32 constant BASE_ELO       = 1200;
    int32 constant ELO_SCALE      = 400;

    // -----------------------------------------------------------------------
    // Events
    // -----------------------------------------------------------------------

    event PlayerRegistered(address indexed player, int32 initialElo);
    event MatchRecorded(address indexed winner, address indexed loser, int32 eloChange);
    event AchievementMinted(address indexed recipient, uint256 tokenId, uint8 rank);

    // -----------------------------------------------------------------------
    // Registration
    // -----------------------------------------------------------------------

    function registerPlayer() external {
        require(!players[msg.sender].registered, "Already registered");
        players[msg.sender] = Player({
            wallet:     msg.sender,
            wins:       0,
            losses:     0,
            elo_rating: BASE_ELO,
            registered: true
        });
        playerList.push(msg.sender);
        emit PlayerRegistered(msg.sender, BASE_ELO);
    }

    // -----------------------------------------------------------------------
    // Match recording
    // -----------------------------------------------------------------------

    function recordMatch(address winner, address loser) external onlyOwner {
        require(players[winner].registered && players[loser].registered, "Unregistered player");
        int32 delta = calculateElo(players[winner].elo_rating, players[loser].elo_rating);
        players[winner].elo_rating += delta;
        players[loser].elo_rating  -= delta;
        players[winner].wins       += 1;
        players[loser].losses      += 1;
        emit MatchRecorded(winner, loser, delta);
    }

    // -----------------------------------------------------------------------
    // ELO calculation
    // -----------------------------------------------------------------------

    function calculateElo(int32 winnerElo, int32 loserElo) public pure returns (int32) {
        // Expected score for winner: E = 1 / (1 + 10^((loserElo-winnerElo)/400))
        // Approximated with integer math; delta = K * (1 - E)
        int32 diff     = loserElo - winnerElo;
        int32 expected = int32(1000) / (int32(1) + int32(10) ** uint32(diff > 0 ? diff : -diff) / ELO_SCALE + 1);
        int32 delta    = K_FACTOR * (int32(1000) - expected) / int32(1000);
        return delta < 1 ? int32(1) : delta;
    }

    // -----------------------------------------------------------------------
    // Leaderboard — returns top N addresses sorted by ELO (bubble sort)
    // -----------------------------------------------------------------------

    function getLeaderboard(uint256 topN) external view returns (address[] memory ranked) {
        uint256 len = playerList.length;
        address[] memory tmp = new address[](len);
        for (uint256 i = 0; i < len; i++) tmp[i] = playerList[i];

        // Bubble sort descending by ELO
        for (uint256 i = 0; i < len; i++) {
            for (uint256 j = 0; j + 1 < len - i; j++) {
                if (players[tmp[j]].elo_rating < players[tmp[j + 1]].elo_rating) {
                    (tmp[j], tmp[j + 1]) = (tmp[j + 1], tmp[j]);
                }
            }
        }

        uint256 n = topN < len ? topN : len;
        ranked = new address[](n);
        for (uint256 i = 0; i < n; i++) ranked[i] = tmp[i];
    }

    // -----------------------------------------------------------------------
    // NFT minting for top 3 (owner calls after season ends)
    // -----------------------------------------------------------------------

    function mintAchievementNFT(address recipient, uint8 rank) external onlyOwner {
        require(rank >= 1 && rank <= 3, "Rank must be 1-3");
        uint256 tokenId = _tokenIdCounter.current();
        _tokenIdCounter.increment();
        // Actual ERC721 mint delegated to external NFT contract; emit event here
        emit AchievementMinted(recipient, tokenId, rank);
    }
}
