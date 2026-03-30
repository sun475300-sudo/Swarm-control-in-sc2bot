# strategy_hooks.janet
# Janet (Lisp dialect) hot-reloadable strategy scripting for the SC2 Zerg bot.
# Janet is lightweight and embeddable, making it ideal for live strategy tweaks
# without recompiling the main Python bot.
#
# Usage: load this file from Python via janet.run() or a cffi bridge.

# ---------------------------------------------------------------------------
# Constants – tuneable thresholds for strategic decisions
# ---------------------------------------------------------------------------
(def MIN-ARMY-SUPPLY   16)   # minimum supply before attacking
(def SAFE-DEFEND-RATIO 0.7)  # our_army / enemy_army ratio considered "safe"
(def TIMING-WINDOW     4.5)  # minutes: ideal ling-bane all-in window
(def EXPAND-MINERAL-THRESHOLD 400) # minerals at which expansion is preferred

# ---------------------------------------------------------------------------
# evaluate-position
# Reads a game-state table and returns one of:
#   :attack  :defend  :expand  :macro
# ---------------------------------------------------------------------------
(defn evaluate-position
  "Given a state struct with keys :our-supply :enemy-supply :minerals
   :bases :tech-complete, recommend a high-level strategic posture."
  [state]
  (let [our-sup   (state :our-supply)
        enm-sup   (state :enemy-supply)
        minerals  (state :minerals)
        bases     (state :bases)
        ratio     (if (> enm-sup 0)
                    (/ our-sup enm-sup)
                    999)]

    (cond
      # If we're way ahead on army, push immediately
      (> ratio 1.4)          :attack

      # Enemy is much stronger – turtle and rebuild
      (< ratio SAFE-DEFEND-RATIO) :defend

      # We have excess minerals and few bases – expand
      (and (> minerals EXPAND-MINERAL-THRESHOLD) (< bases 3)) :expand

      # Default: keep macroing
      :else                   :macro)))

# ---------------------------------------------------------------------------
# recommend-units
# Returns a priority-ordered tuple of unit keywords based on enemy composition.
# enemy-comp is a table like {:marines 10 :marauders 5 :tanks 2}
# ---------------------------------------------------------------------------
(defn recommend-units
  "Counter-composition advisor. Returns a vector of unit keywords
   ordered by production priority."
  [enemy-comp]
  (let [bio    (+ (get enemy-comp :marines   0)
                  (get enemy-comp :marauders 0))
        mech   (+ (get enemy-comp :tanks     0)
                  (get enemy-comp :thors     0)
                  (get enemy-comp :cyclones  0))
        air    (+ (get enemy-comp :vikings   0)
                  (get enemy-comp :liberators 0)
                  (get enemy-comp :banshees  0))
        stalks (+ (get enemy-comp :stalkers  0)
                  (get enemy-comp :immortals 0))]

    (cond
      # Heavy bio -> banelings shred marines
      (> bio 12)   [:zergling :baneling :roach]

      # Mech -> roach-ravager with corrosive bile
      (> mech 4)   [:roach :ravager :lurker]

      # Air threat -> hydralisk + corruptors
      (> air 5)    [:hydralisk :corruptor :queen]

      # Gateway / armored -> roach-hydra
      (> stalks 6) [:roach :hydralisk :infestor]

      # Default balanced composition
      :else        [:roach :hydralisk :zergling])))

# ---------------------------------------------------------------------------
# calc-attack-timing
# Returns the recommended attack time (in game-minutes as a float).
# tech-buildings: number of key tech structures completed (lair, den, etc.)
# army-supply:    current army supply count
# ---------------------------------------------------------------------------
(defn calc-attack-timing
  "Estimate the optimal timing attack window.
   Earlier timings reward aggression; late timings favour full tech."
  [tech-buildings army-supply]
  (let [# Base window shifts earlier with more completed tech
        base-time  (- TIMING-WINDOW (* 0.3 tech-buildings))
        # More army supply pushes window slightly later (wait for critical mass)
        supply-adj (if (< army-supply MIN-ARMY-SUPPLY)
                     (/ (- MIN-ARMY-SUPPLY army-supply) 10.0)
                     0)
        # Clamp result between 3.0 and 9.0 game-minutes
        raw        (+ base-time supply-adj)]
    (max 3.0 (min 9.0 raw))))

# ---------------------------------------------------------------------------
# Self-test (runs when file is executed directly)
# ---------------------------------------------------------------------------
(comment
  (def test-state {:our-supply 40 :enemy-supply 28 :minerals 250 :bases 2 :tech-complete true})
  (print "Position: " (evaluate-position test-state))   # => :attack

  (def test-enemy {:marines 14 :marauders 4})
  (print "Units: "    (recommend-units test-enemy))     # => [:zergling :baneling :roach]

  (print "Timing: "   (calc-attack-timing 2 20)))       # => ~4.2 minutes
