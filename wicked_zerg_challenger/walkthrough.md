# Commander Learning System Guide

The bot now features a centralized **"Brain"** (`commander_knowledge.json`) that allows you to teach it new strategies without writing Python code.

## 1. How to "Teach" the Bot

All strategic knowledge is stored in:
`wicked_zerg_challenger/commander_knowledge.json`

### A. Adding a New Build Order
To add a new build (e.g., "13 Pool Rush"), simple add an entry to the `build_orders` section:

```json
"13_POOL_RUSH": {
  "name": "13 Pool Rush",
  "description": "Aggressive Zergling Rush",
  "steps": [
    {"supply": 13, "action": "build", "unit_type": "SPAWNINGPOOL", "description": "13 Pool"},
    {"supply": 12, "action": "train", "unit_type": "ZERGLING", "description": "Lings"}
  ]
}
```

### B. Changing Unit Compositions
To adjust how the bot fights against Terran, edit `unit_ratios`:

```json
"Terran": {
  "mid": {
    "zergling": 0.1,  // Lesslings
    "roach": 0.5,     // More Roaches
    "hydra": 0.4      // More Hydras
  }
}
```

The bot will automatically read this file on startup.

## 2. Components

- **KnowledgeManager**: Reads the JSON file.
- **BuildOrderSystem**: Asks KnowledgeManager for the build steps.
- **StrategyManager**: Asks KnowledgeManager for unit ratios.

### Micro & Combat Logic (New)
- **Micro Focus Mode**: During combat (detected by `IntelManager`), the bot accelerates its micro-control update rate by **400%** (12 frames -> 3 frames).
- **Anti-Clumping**: Units now actively repel from Splash Damage dealers (Thor, Archon, Mine) using an enhanced Potential Field force.
