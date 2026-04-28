#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze why high tech units are not being produced"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger("AnalyzeTechUnitProduction")

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


def analyze_tech_unit_issues():
    """Analyze potential issues with tech unit production"""

    logger.info("=" * 70)
    logger.info("High Tech Unit Production Analysis")
    logger.info("=" * 70)

    logger.info("\n[1] Tech Building Construction Requirements")
    logger.info("-" * 70)
    logger.info("Roach Warren:")
    logger.info("  - Requirements: Spawning Pool (optional), game time > 180s")
    logger.info("  - Cost: 150 minerals, 0 gas")
    logger.info("  - Location: production_resilience.py (Line 526, 552, 565)")

    logger.info("\nHydralisk Den:")
    logger.info("  - Requirements: Lair or Hive (MANDATORY!), game time > 240s")
    logger.info("  - Cost: 100 minerals, 100 gas")
    logger.info("  - Location: production_resilience.py (Line 541, 578)")
    logger.warning("  - WARNING: Without Lair, Hydralisk Den cannot produce Hydralisks!")

    logger.info("\nLair:")
    logger.info("  - Requirements: Spawning Pool ready, Hatchery ready, game time > 120s")
    logger.info("  - Cost: 150 minerals, 100 gas")
    logger.info("  - Location: production_manager.py (Line 2850-2880)")
    logger.warning("  - WARNING: Gas income check required (extractor + vespene >= 50)")

    logger.info("\n[2] Tech Unit Production Conditions")
    logger.info("-" * 70)
    logger.info("Roach Production:")
    logger.info("  - Requirements: Roach Warren ready, can_afford(ROACH), supply_left >= 2")
    logger.info("  - Cost: 75 minerals, 25 gas")
    logger.info("  - Location: production_manager.py (Line 2997-3006)")

    logger.info("\nHydralisk Production:")
    logger.info("  - Requirements: Hydralisk Den ready + Lair exists, can_afford(HYDRALISK), supply_left >= 2")
    logger.info("  - Cost: 100 minerals, 50 gas")
    logger.info("  - Location: production_manager.py (Line 2986-2995)")
    logger.warning("  - WARNING: Without Lair, Hydralisk Den cannot produce Hydralisks!")

    logger.info("\n[3] Potential Issues")
    logger.info("-" * 70)
    logger.error("1. Lair Upgrade Failure:")
    logger.info("   - Gas shortage (100 gas required)")
    logger.info("   - Extractor not built or no workers assigned")
    logger.info("   - Spawning Pool not completed")
    logger.info("   - Hatchery might be morphing")

    logger.info("\n2. Emergency Flush Logic Only Produces Zerglings:")
    logger.info("   - production_resilience.py (Line 60-108): Forces Zergling production when minerals > 500")
    logger.info("   - production_manager.py (Line 1443-1502): _flush_resources() prioritizes Zerglings")
    logger.info("   - PROBLEM: Tech unit production opportunities may be blocked by Zergling production")

    logger.info("\n3. Resource Shortage:")
    logger.info("   - Hydralisk: 100M + 50G required")
    logger.info("   - Roach: 75M + 25G required")
    logger.info("   - Insufficient gas income prevents tech unit production")

    logger.info("\n4. Supply Shortage:")
    logger.info("   - supply_left < 2 prevents tech unit production")
    logger.info("   - Overlord production delay causes supply block")

    logger.info("\n5. Tech Building Construction Order Issue:")
    logger.info("   - Hydralisk Den built without Lair")
    logger.info("   - Hydralisk Den exists but cannot produce without Lair")

    logger.info("\n6. Production Priority Issue:")
    logger.info("   - Zergling production may have higher priority than tech units")
    logger.info("   - production_manager.py (Line 3014-3016): Zergling production before tech units")

    logger.info("\n[4] Solutions")
    logger.info("-" * 70)
    logger.info("1. Strengthen Lair Upgrade:")
    logger.info("   - Improve gas income check logic")
    logger.info("   - Increase Extractor construction priority")
    logger.error("   - Add retry logic for failed Lair upgrades")

    logger.info("\n2. Improve Emergency Flush Logic:")
    logger.info("   - Produce tech units when tech buildings are ready")
    logger.info("   - Include Roach/Hydralisk in addition to Zerglings")

    logger.info("\n3. Improve Tech Building Construction Order:")
    logger.info("   - Verify Lair construction first")
    logger.info("   - Strengthen Lair existence check before Hydralisk Den construction")

    logger.info("\n4. Adjust Production Priority:")
    logger.info("   - Prioritize tech unit production when tech buildings are ready")
    logger.info("   - Increase tech unit production priority over Zerglings")

    logger.info("\n" + "=" * 70)
    logger.info("Analysis Complete")
    logger.info("=" * 70)


if __name__ == "__main__":
    analyze_tech_unit_issues()
