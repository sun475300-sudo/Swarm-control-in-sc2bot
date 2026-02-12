# -*- coding: utf-8 -*-
"""
Harassment System Extension for Combat Manager

Adds intelligent worker harassment with automatic retreat and return mechanics.
"""

# Add this to the end of combat_manager.py

    # ============================================================================
    # HARASSMENT SYSTEM (Worker Targeting + Retreat/Return Logic)
    # ============================================================================

    def __init_harassment_state(self):
        """Initialize harassment tracking state."""
        if not hasattr(self, 'harassment_state'):
            self.harassment_state = {
                'active_units': set(),      # Currently harassing (unit tags)
                'retreating_units': set(),  # Retreating to safety (unit tags)
                'healing_units': set(),     # Healing at base (unit tags)
                'last_retreat_time': 0,     # Cooldown tracking
                'retreat_cooldown': 660,    # 30 seconds (22 frames/sec * 30)
            }

    async def _harass_workers(self, harassment_units, enemy_workers, iteration):
        """
        Execute worker harassment with intelligent targeting and retreat logic.
        
        Args:
            harassment_units: Mutalisks or Zerglings assigned to harassment
            enemy_workers: Enemy worker units
            iteration: Current game iteration
        """
        if not harassment_units or not enemy_workers:
            return

        # Initialize state if needed
        self.__init_harassment_state()

        game_time = getattr(self.bot, 'time', 0)

        for unit in harassment_units:
            # Check if unit should retreat
            nearby_threats = self.bot.enemy_units.closer_than(8, unit.position)
            if self._should_retreat_from_harassment(unit, nearby_threats):
                # Mark as retreating
                self.harassment_state['active_units'].discard(unit.tag)
                self.harassment_state['retreating_units'].add(unit.tag)
                self.harassment_state['last_retreat_time'] = iteration

                # Retreat to nearest base
                if hasattr(self.bot, 'townhalls') and self.bot.townhalls.exists:
                    safe_pos = self.bot.townhalls.closest_to(unit).position
                    self.bot.do(unit.move(safe_pos))
                    
                    if iteration % 100 == 0:
                        self.logger.info(f"[{int(game_time)}s] Harassment unit retreating (HP: {unit.health}/{unit.health_max})")
                continue

            # Active harassment - target workers
            if unit.tag in self.harassment_state['active_units'] or unit.tag not in self.harassment_state['retreating_units']:
                self.harassment_state['active_units'].add(unit.tag)
                
                # Find closest worker
                if enemy_workers:
                    target = enemy_workers.closest_to(unit)
                    
                    # Attack if not already attacking
                    if not unit.is_attacking:
                        self.bot.do(unit.attack(target))

    def _should_retreat_from_harassment(self, unit, enemy_threats):
        """
        Determine if a harassment unit should retreat.
        
        Retreat Conditions:
        - HP < 40% (critical health)
        - Outnumbered by anti-air threats (for Mutalisks)
        - Surrounded by multiple enemies
        
        Args:
            unit: The harassment unit
            enemy_threats: Nearby enemy units
            
        Returns:
            bool: True if unit should retreat
        """
        # Health-based retreat
        hp_percent = unit.health / unit.health_max if unit.health_max > 0 else 0
        if hp_percent < 0.4:
            return True

        # Threat-based retreat
        if not enemy_threats:
            return False

        try:
            from sc2.ids.unit_typeid import UnitTypeId
            
            # For Mutalisks: retreat if facing anti-air
            if unit.type_id == UnitTypeId.MUTALISK:
                anti_air = enemy_threats.filter(lambda e: e.can_attack_air)
                if len(anti_air) >= 3:  # 3+ anti-air units
                    return True

            # For Zerglings: retreat if outnumbered 2:1
            if unit.type_id == UnitTypeId.ZERGLING:
                if len(enemy_threats) >= 6:  # 6+ enemies
                    return True

        except ImportError:
            pass

        return False

    async def _return_harassment_units(self, harassment_units, target_position, iteration):
        """
        Return harassment units to combat zone after healing.
        
        Return Conditions:
        - HP > 80% (fully healed)
        - Cooldown elapsed (30 seconds since last retreat)
        - No immediate threats
        
        Args:
            harassment_units: Units ready to return
            target_position: Target harassment location
            iteration: Current game iteration
        """
        if not harassment_units:
            return

        # Initialize state if needed
        self.__init_harassment_state()

        game_time = getattr(self.bot, 'time', 0)
        cooldown_elapsed = (iteration - self.harassment_state['last_retreat_time']) > self.harassment_state['retreat_cooldown']

        for unit in harassment_units:
            # Check if unit is in retreating or healing state
            if unit.tag not in self.harassment_state['retreating_units'] and unit.tag not in self.harassment_state['healing_units']:
                continue

            # Check return conditions
            hp_percent = unit.health / unit.health_max if unit.health_max > 0 else 0
            
            if hp_percent > 0.8 and cooldown_elapsed:
                # Ready to return
                self.harassment_state['retreating_units'].discard(unit.tag)
                self.harassment_state['healing_units'].discard(unit.tag)
                self.harassment_state['active_units'].add(unit.tag)

                # Return to harassment
                self.bot.do(unit.attack(target_position))
                
                if iteration % 100 == 0:
                    self.logger.info(f"[{int(game_time)}s] Harassment unit returning to combat (HP: {unit.health}/{unit.health_max})")
            elif hp_percent > 0.8:
                # Healed but cooldown not elapsed - mark as healing
                self.harassment_state['retreating_units'].discard(unit.tag)
                self.harassment_state['healing_units'].add(unit.tag)

    def _find_harass_target(self):
        """
        Find best harassment target (enemy workers or isolated buildings).
        
        Returns:
            Position of harassment target or None
        """
        try:
            from sc2.ids.unit_typeid import UnitTypeId
            
            # Priority 1: Enemy workers
            enemy_workers = self.bot.enemy_units.filter(lambda u: u.type_id in {
                UnitTypeId.SCV, UnitTypeId.PROBE, UnitTypeId.DRONE
            })
            
            if enemy_workers:
                # Target workers near enemy bases
                if hasattr(self.bot, 'enemy_start_locations') and self.bot.enemy_start_locations:
                    enemy_base = self.bot.enemy_start_locations[0]
                    workers_near_base = enemy_workers.closer_than(20, enemy_base)
                    if workers_near_base:
                        return workers_near_base.center
                return enemy_workers.center

            # Priority 2: Isolated tech buildings
            tech_buildings = self.bot.enemy_structures.filter(lambda s: s.type_id in {
                UnitTypeId.TWILIGHTCOUNCIL, UnitTypeId.TEMPLARARCHIVE, UnitTypeId.DARKSHRINE,
                UnitTypeId.FUSIONCORE, UnitTypeId.GHOSTACADEMY,
                UnitTypeId.INFESTATIONPIT, UnitTypeId.ULTRALISKCAVERN, UnitTypeId.SPIRE
            })
            
            if tech_buildings:
                return tech_buildings.first.position

            # Fallback: Enemy base
            if hasattr(self.bot, 'enemy_start_locations') and self.bot.enemy_start_locations:
                return self.bot.enemy_start_locations[0]

        except ImportError:
            pass

        return None
