;; Wicked Zerg - Battle Simulation
;; Phase 142: Clojure v2

(ns game-ai.battle-sim
  (:require [clojure.math.numeric-tower :as math]))

(defn calculate-swarm-damage [count]
  (* count 5))

(defn swarm-formation [center-x center-y count radius]
  (for [i (range count)]
    (let [angle (* 2 Math/PI i count)]
      [(+ center-x (* radius (Math/cos angle)))
       (+ center-y (* radius (Math/sin angle)))])))

(defn unit-strength [health damage armor]
  (let [effective (* damage (/ health 100))]
    (* effective (- 1 (* armor 0.01)))))

(defn battle-outcome [attackers defenders]
  (let [attack-power (reduce + (map #(apply unit-strength %) attackers))
        defense-power (reduce + (map #(apply unit-strength %) defenders))]
    (> attack-power defense-power)))

(defn calculate-threats [our-positions enemy-positions]
  (let [distances (for [o our-positions
                        e enemy-positions]
                    (math/sqrt (+ (Math/pow (- (first o) (first e)) 2)
                                  (Math/pow (- (second o) (second e)) 2))))]
    (count #(> 10 %) distances)))

(println "Battle Simulation Initialized - Clojure v2")
