(ns sc2-bot.dashboard
  (:require
   [reagent.core :as r]
   [re-frame.core :as rf]
   [ajax.core :refer [GET POST]]
   [clojure.string :as str]))

;; --- Events ---

(rf/reg-event-db
 ::initialize-db
 (fn [_ _]
   {:win-rate 0.0
    :current-game nil
    :leaderboard []
    :loading? false
    :error nil}))

(rf/reg-event-fx
 ::fetch-history
 (fn [{:keys [db]} [_ player-id]]
   {:db (assoc db :loading? true)
    :http-xhrio {:method          :get
                 :uri             (str "/api/history/" player-id)
                 :response-format (ajax.core/json-response-format {:keywords? true})
                 :on-success      [::history-loaded]
                 :on-failure      [::api-error]}}))

(rf/reg-event-db
 ::history-loaded
 (fn [db [_ response]]
   (-> db
       (assoc :loading? false)
       (assoc :win-rate (:win_rate response))
       (assoc :leaderboard (:leaderboard response)))))

(rf/reg-event-db
 ::update-game-state
 (fn [db [_ game-state]]
   (assoc db :current-game game-state)))

(rf/reg-event-db
 ::api-error
 (fn [db [_ error]]
   (-> db
       (assoc :loading? false)
       (assoc :error (str "API Error: " (:status error))))))

;; --- Subscriptions ---

(rf/reg-sub
 ::win-rate
 (fn [db _]
   (get db :win-rate 0.0)))

(rf/reg-sub
 ::current-game
 (fn [db _]
   (get db :current-game)))

(rf/reg-sub
 ::leaderboard
 (fn [db _]
   (get db :leaderboard [])))

(rf/reg-sub
 ::loading?
 (fn [db _]
   (get db :loading? false)))

;; --- Components ---

(defn win-rate-panel []
  (let [win-rate (rf/subscribe [::win-rate])]
    (fn []
      [:div.panel.win-rate
       [:h2 "Win Rate"]
       [:div.rate-display
        [:span.percentage (str (js/Math.round (* @win-rate 100)) "%")]
        [:div.bar [:div.fill {:style {:width (str (* @win-rate 100) "%")}}]]]])))

(defn current-game-panel []
  (let [game (rf/subscribe [::current-game])]
    (fn []
      [:div.panel.current-game
       [:h2 "Current Game"]
       (if-let [g @game]
         [:div
          [:p "Game ID: " (:game-id g)]
          [:p "Race: " (:race g)]
          [:p "Minerals: " (:minerals g)]
          [:p "Vespene: " (:vespene g)]
          [:p "Supply: " (:supply-used g) "/" (:supply-cap g)]]
         [:p.no-game "No active game"])])))

(defn leaderboard-panel []
  (let [board (rf/subscribe [::leaderboard])]
    (fn []
      [:div.panel.leaderboard
       [:h2 "Leaderboard"]
       [:table
        [:thead [:tr [:th "Rank"] [:th "Player"] [:th "MMR"] [:th "Win Rate"]]]
        [:tbody
         (for [[idx entry] (map-indexed vector @board)]
           ^{:key (:player-id entry)}
           [:tr
            [:td (inc idx)]
            [:td (:name entry)]
            [:td (:mmr entry)]
            [:td (str (js/Math.round (* (:win-rate entry) 100)) "%")]])]]])))

(defn app []
  (rf/dispatch [::initialize-db])
  (rf/dispatch [::fetch-history "bot-player"])
  (fn []
    [:div.sc2-dashboard
     [:header [:h1 "SC2 Bot Dashboard"]]
     [:main
      [win-rate-panel]
      [current-game-panel]
      [leaderboard-panel]]]))

(defn ^:export init []
  (r/render [app] (.getElementById js/document "app")))
