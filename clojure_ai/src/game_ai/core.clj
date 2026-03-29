;; P95: Clojure - Functional AI Decision System
;; Uses persistent data structures for immutable game state

(ns game-ai.core
  (:require [clojure.core.async :as async]))

(def game-state (atom {:units []
                       :resources {:minerals 0 :gas 0 :supply 0}
                       :enemy-units []
                       :game-time 0}))

(defn update-units [state units]
  (assoc state :units units))

(defn analyze-threats [units enemy-units]
  (map (fn [unit]
         {:unit unit
          :threat-level (calculate-threat unit enemy-units)
          :recommended-action (decide-action unit enemy-units)})
       units))

(defn calculate-threat [unit enemies]
  (let [nearby-enemies (filter #(near? unit %) enemies)]
    (if (empty? nearby-enemies)
      :low
      (case (count nearby-enemies)
        1 :medium
        2 :high
        :critical))))

(defn decide-action [unit enemies]
  (let [threat (calculate-threat unit enemies)]
    (case threat
      :low :harvest
      :medium :engage
      :high :flee
      :critical :desperate)))

(defn game-loop []
  (let [ch (async/chan)]
    (async/go-loop []
      (when-let [msg (async/<! ch)]
        (swap! game-state update-units (:units msg))
        (recur)))
    ch))

(defn -main [& args]
  (println "Starting Clojure AI Decision System...")
  (game-loop))
