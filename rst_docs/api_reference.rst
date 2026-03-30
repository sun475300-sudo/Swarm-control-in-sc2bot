ZergCommander Bot API Reference
================================

.. contents:: Table of Contents
   :depth: 3
   :local:

Overview
--------

The ZergCommander bot exposes a Python API built on top of `python-sc2 (burnysc2)`.
All public classes and functions are documented here. The system is designed around
an async event loop; most methods are coroutines invoked by the SC2 game step callback.

Installation
~~~~~~~~~~~~

.. code-block:: bash

   pip install burnysc2==5.0.12 numpy scipy loguru
   git clone https://github.com/sc2ai/zergcommander.git
   cd zergcommander && python run.py

Core Module: ``src.zerg_commander``
-------------------------------------

.. py:class:: ZergCommander(sc2.BotAI)

   Main bot class. Inherits from ``sc2.BotAI`` and implements all game-step logic.

   .. py:method:: async on_step(iteration: int) -> None

      Called every game step (~22.4 frames per second at normal speed).
      Dispatches to economy, production, and combat managers.

      :param iteration: Zero-based game step counter.

   .. py:method:: async on_unit_destroyed(unit_tag: int) -> None

      Triggered when any unit on the map dies. Used to update threat maps
      and adjust build-order weights.

      :param unit_tag: SC2 unit tag of the destroyed unit.

   .. py:method:: async on_building_construction_complete(unit: sc2.Unit) -> None

      Fires when a building finishes construction. Triggers next build-order
      step and queues tech unlocks.

Economy Manager: ``src.economy_manager``
------------------------------------------

.. py:class:: EconomyManager

   Controls worker production, expansion decisions, and resource allocation.

   .. py:method:: async manage_workers() -> None

      Produces drones up to ``max_workers`` per base. Calls
      :meth:`assign_idle_workers` when drones are idle.

   .. py:method:: async expand_if_needed() -> None

      Evaluates mineral saturation and bank size against thresholds defined in
      ``toml_config/bot_config.toml``. Issues expand command if conditions met.

   .. py:method:: get_saturation_ratio(hatchery: sc2.Unit) -> float

      Returns mineral saturation ratio for a given hatchery.

      :param hatchery: The hatchery unit to evaluate.
      :returns: Float in range ``[0.0, 1.0]`` representing saturation.

      .. code-block:: python

         ratio = economy.get_saturation_ratio(self.townhalls.first)
         if ratio > 0.85:
             await self.expand()

Combat Manager: ``src.combat_manager``
----------------------------------------

.. py:class:: CombatManager

   Handles army movements, attack waves, and micro-management.

   .. py:attribute:: attack_threshold: int
      :value: 20

      Minimum army supply before initiating an attack.

   .. py:method:: async execute_attack(target: sc2.Point2) -> None

      Moves entire attack force toward ``target``. Activates Lurker burrow,
      Infestor Fungal Growth, and Ravager Bile abilities automatically.

      :param target: Map coordinates to attack.

   .. py:method:: async micro_unit(unit: sc2.Unit, enemies: sc2.Units) -> None

      Per-unit micro logic. Implements kite-back for low-HP Roaches,
      Zergling surrounds, and Baneling rolling micro.

      :param unit: The unit to micro.
      :param enemies: Nearby enemy units.

Creep Manager: ``src.creep_manager``
--------------------------------------

.. py:class:: CreepManager

   Manages Queen creep spread and tumor placement for map control.

   .. py:method:: async spread_creep(queens: sc2.Units) -> None

      Assigns idle Queens to drop creep tumors along optimal highway paths.
      Uses a greedy graph traversal from the Creep Propagation Graph (CPG).

   .. py:method:: get_creep_coverage() -> float

      Returns the fraction of walkable map tiles currently covered by creep.

      :returns: Float in range ``[0.0, 1.0]``.

Configuration Reference
-----------------------

.. list-table:: Key Configuration Files
   :header-rows: 1
   :widths: 30 20 50

   * - File
     - Format
     - Purpose
   * - ``yaml_config/sc2_strategy.yaml``
     - YAML
     - Build orders, unit ratios, timing windows
   * - ``toml_config/bot_config.toml``
     - TOML
     - Runtime settings, aggression levels
   * - ``json_config/unit_data.json``
     - JSON
     - Unit stats for combat simulation

Changelog
---------

**v2.0.0** (2026-03-30)
   - Added Lurker micro and burrow management
   - Implemented Creep Propagation Graph
   - Reactive Build-Order Engine with sigmoid priority scoring
   - Docker deployment support

**v1.5.0** (2025-11-15)
   - Infestor Fungal Growth integration
   - ZvP Hydra-Lurker build order added
