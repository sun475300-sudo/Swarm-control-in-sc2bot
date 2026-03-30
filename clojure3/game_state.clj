;; game_state.clj
;; Clojure immutable game-state management for a StarCraft II Zerg bot.
;; All state transitions produce new persistent data structures — nothing is
;; mutated in place.  A Clojure atom holds the canonical current state so that
;; the bot loop can swap! in updates atomically.

(ns sc2-bot.game-state)

;; ─────────────────────────────────────────────────────────────────────────────
;; Domain Records
;; ─────────────────────────────────────────────────────────────────────────────

(defrecord Economy
  [minerals         ; current mineral stockpile
   gas              ; current gas stockpile
   worker-count     ; number of drones alive
   base-count])     ; active hatcheries / nexii / CCs

(defrecord Army
  [supply           ; our total army supply
   tech-level       ; 1=Spawning Pool, 2=Lair, 3=Hive
   unit-counts])    ; map of unit-type -> count, e.g. {:zergling 12 :roach 6}

(defrecord Intel
  [enemy-supply     ; estimated enemy army supply
   enemy-bases      ; last known enemy base positions (vector of [x y])
   threats          ; vector of threat structs detected near our bases
   last-seen-time]) ; game-loop tick of last enemy sighting

(defrecord GameState
  [economy          ; Economy record
   army             ; Army record
   intel            ; Intel record
   game-time        ; elapsed seconds
   phase])          ; keyword: :early | :mid | :late

;; ─────────────────────────────────────────────────────────────────────────────
;; Factory / initial state
;; ─────────────────────────────────────────────────────────────────────────────

(defn initial-state
  "Return the canonical starting state for a new Zerg game."
  []
  (->GameState
    (->Economy 50 0 12 1)
    (->Army    0  1 {:drone 12})
    (->Intel   0  []  []  0)
    0
    :early))

;; Canonical atom — the bot's single source of truth.
(defonce bot-state (atom (initial-state)))

;; ─────────────────────────────────────────────────────────────────────────────
;; Pure state-update functions (all return new GameState)
;; ─────────────────────────────────────────────────────────────────────────────

(defn update-economy
  "Merge a map of economy deltas into the current state."
  [state deltas]
  (update state :economy merge deltas))

(defn add-units
  "Record production of new units.  `new-units` is a map {:unit-type count}."
  [state new-units]
  (-> state
      (update-in [:army :unit-counts]
                 (fn [counts]
                   (merge-with + counts new-units)))
      (update-in [:army :supply]
                 #(+ % (reduce + (vals new-units))))))

(defn update-intel
  "Merge new scouting data into the intel sub-record."
  [state scouting-data]
  (update state :intel merge scouting-data))

(defn advance-time
  "Bump the game timer by `delta-seconds` and recalculate phase."
  [state delta-seconds]
  (let [new-time (+ (:game-time state) delta-seconds)
        new-phase (cond
                    (< new-time 300)  :early   ; < 5 minutes
                    (< new-time 720)  :mid     ; 5–12 minutes
                    :else             :late)]
    (assoc state :game-time new-time :phase new-phase)))

;; ─────────────────────────────────────────────────────────────────────────────
;; Threat Analysis
;; ─────────────────────────────────────────────────────────────────────────────

(defn analyze-threat
  "Inspect intel and return a threat level keyword.
   :none | :probe-scout | :early-aggression | :all-in | :timing-attack"
  [state]
  (let [intel        (:intel state)
        enemy-supply (:enemy-supply intel)
        our-supply   (get-in state [:army :supply])
        ratio        (if (zero? our-supply) 99 (/ enemy-supply our-supply))
        threats      (:threats intel)]
    (cond
      (empty? threats)      :none
      (< ratio 0.5)         :probe-scout       ; tiny enemy force
      (< ratio 1.0)         :early-aggression  ; enemy is smaller but attacking
      (< ratio 1.5)         :timing-attack     ; even forces attacking
      :else                 :all-in)))          ; enemy has big army advantage

;; ─────────────────────────────────────────────────────────────────────────────
;; Strategic Recommendation Engine
;; ─────────────────────────────────────────────────────────────────────────────

(defn recommend-action
  "Given the current game state return a keyword recommendation for the bot loop.
   :macro | :expand | :tech-up | :defend | :attack | :all-in-response"
  [state]
  (let [econ         (:economy state)
        army         (:army state)
        threat       (analyze-threat state)
        phase        (:phase state)
        worker-count (:worker-count econ)
        minerals     (:minerals econ)
        base-count   (:base-count econ)
        army-supply  (:supply army)
        tech-level   (:tech-level army)]
    (cond
      ;; Emergencies first
      (= threat :all-in)           :all-in-response
      (= threat :timing-attack)    :defend

      ;; Phase-aware macro logic
      (and (= phase :early)
           (< worker-count 18))    :macro        ; build more drones

      (and (< base-count 3)
           (> minerals 350))       :expand       ; take a new base

      (and (< tech-level 3)
           (> (:gas econ) 200))    :tech-up      ; invest in upgrades

      (and (> army-supply 40)
           (> (/ army-supply
                 (max 1 (get-in state [:intel :enemy-supply]))) 1.2))
                                   :attack       ; army lead → push

      :else                        :macro)))     ; default: keep droning

;; ─────────────────────────────────────────────────────────────────────────────
;; Bot Loop Helpers
;; ─────────────────────────────────────────────────────────────────────────────

(defn tick!
  "Called each game step.  Applies `update-fn` to the global atom and returns
   the recommended action for this tick."
  [update-fn]
  (swap! bot-state update-fn)
  (recommend-action @bot-state))

;; ─────────────────────────────────────────────────────────────────────────────
;; Demo
;; ─────────────────────────────────────────────────────────────────────────────

(defn -main [& _args]
  (println "=== SC2 Zerg Game-State Manager (Clojure) ===")

  (let [s0 (initial-state)]
    (println "\nInitial state phase  :" (:phase s0))
    (println "Initial recommendation:" (recommend-action s0))

    ;; Simulate mid-game with an incoming attack
    (let [s1 (-> s0
                 (advance-time 480)
                 (update-economy {:minerals 500 :gas 250 :worker-count 28 :base-count 3})
                 (add-units {:roach 8 :zergling 16})
                 (update-intel {:enemy-supply 55
                                :threats [{:type :bio-ball :position [130 40]}]
                                :last-seen-time 480}))]
      (println "\nMid-game phase       :" (:phase s1))
      (println "Threat level         :" (analyze-threat s1))
      (println "Recommendation       :" (recommend-action s1)))))
