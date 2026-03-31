// Phase 402: Tauri - SC2 Bot Desktop Management App
// Tauri v2 desktop application for StarCraft II bot control

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Arc;
use tauri::{Manager, State, WebviewWindowBuilder};
use tokio::sync::Mutex;

// ============================================================
// State
// ============================================================

#[derive(Debug, Default)]
pub struct BotState {
    pub is_running: bool,
    pub current_map: String,
    pub wins: u32,
    pub losses: u32,
    pub mmr: i32,
    pub pid: Option<u32>,
}

pub struct AppState(pub Arc<Mutex<BotState>>);

// ============================================================
// Tauri Commands
// ============================================================

#[tauri::command]
async fn get_bot_status(state: State<'_, AppState>) -> Result<serde_json::Value, String> {
    let bot = state.0.lock().await;
    Ok(serde_json::json!({
        "is_running": bot.is_running,
        "current_map": bot.current_map,
        "wins": bot.wins,
        "losses": bot.losses,
        "mmr": bot.mmr,
        "win_rate": if bot.wins + bot.losses > 0 {
            bot.wins as f64 / (bot.wins + bot.losses) as f64
        } else {
            0.0
        },
        "pid": bot.pid,
    }))
}

#[tauri::command]
async fn start_bot(
    map_name: String,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let mut bot = state.0.lock().await;

    if bot.is_running {
        return Err("Bot is already running".to_string());
    }

    bot.is_running = true;
    bot.current_map = map_name.clone();
    bot.pid = Some(12345); // placeholder PID

    println!("[Tauri] Bot started on map: {}", map_name);
    Ok(format!("Bot started on {}", map_name))
}

#[tauri::command]
async fn stop_bot(state: State<'_, AppState>) -> Result<String, String> {
    let mut bot = state.0.lock().await;

    if !bot.is_running {
        return Err("Bot is not running".to_string());
    }

    bot.is_running = false;
    bot.current_map = String::new();
    bot.pid = None;

    println!("[Tauri] Bot stopped");
    Ok("Bot stopped successfully".to_string())
}

#[tauri::command]
async fn get_replay_list() -> Result<Vec<serde_json::Value>, String> {
    // In production, scan the SC2 replays directory
    let replays = vec![
        serde_json::json!({
            "filename": "2026-03-31_ZvT_Equilibrium.SC2Replay",
            "result": "Win",
            "map": "Equilibrium LE",
            "duration_seconds": 423,
            "mmr_change": 18,
        }),
        serde_json::json!({
            "filename": "2026-03-30_ZvP_SiteDelta.SC2Replay",
            "result": "Loss",
            "map": "Site Delta LE",
            "duration_seconds": 612,
            "mmr_change": -15,
        }),
        serde_json::json!({
            "filename": "2026-03-30_ZvZ_Gresvan.SC2Replay",
            "result": "Win",
            "map": "Gresvan LE",
            "duration_seconds": 287,
            "mmr_change": 21,
        }),
    ];
    Ok(replays)
}

// ============================================================
// Main
// ============================================================

fn main() {
    let bot_state = AppState(Arc::new(Mutex::new(BotState {
        is_running: false,
        current_map: String::new(),
        wins: 42,
        losses: 18,
        mmr: 4850,
        pid: None,
    })));

    tauri::Builder::default()
        .manage(bot_state)
        .invoke_handler(tauri::generate_handler![
            get_bot_status,
            start_bot,
            stop_bot,
            get_replay_list,
        ])
        .setup(|app| {
            // Main window
            let _main_window = WebviewWindowBuilder::new(
                app,
                "main",
                tauri::WebviewUrl::App("index.html".into()),
            )
            .title("SC2 Bot Manager")
            .inner_size(1200.0, 800.0)
            .build()?;

            // Floating overlay window
            let _overlay = WebviewWindowBuilder::new(
                app,
                "overlay",
                tauri::WebviewUrl::App("overlay.html".into()),
            )
            .title("SC2 Live Overlay")
            .inner_size(320.0, 200.0)
            .always_on_top(true)
            .decorations(false)
            .transparent(true)
            .build()?;

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running Tauri application");
}
