#!/usr/bin/env tclsh
# bot_automation.tcl
# Tcl automation layer for the StarCraft II Zerg bot manager.
# Handles process lifecycle (start / stop), health monitoring,
# automatic crash recovery, and live log monitoring.

package require Tcl 8.5

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
namespace eval cfg {
    variable bot_script  "python"              ;# interpreter
    variable bot_args    [list "run_bot.py"]   ;# script + extra args
    variable log_file    "bot.log"             ;# bot's stdout/stderr sink
    variable pid_file    "bot.pid"             ;# stores the running PID
    variable max_crashes 5                     ;# restart ceiling before giving up
    variable check_ms    3000                  ;# health-check interval (ms)
}

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
namespace eval state {
    variable pid        ""   ;# current bot process ID
    variable crashes    0    ;# consecutive crash count
    variable log_offset 0    ;# byte offset for incremental log reads
    variable running    0    ;# 1 while the monitor loop is active
}

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

# log_msg -- print a timestamped manager message to stdout.
proc log_msg {level msg} {
    set ts [clock format [clock seconds] -format "%Y-%m-%d %H:%M:%S"]
    puts "\[$ts\] \[$level\] $msg"
}

# ---------------------------------------------------------------------------
# Process management
# ---------------------------------------------------------------------------

# start_bot -- launches the bot as a child process and records its PID.
proc start_bot {} {
    if {$state::pid ne "" && [process_alive $state::pid]} {
        log_msg WARN "Bot is already running (PID $state::pid). Ignoring start request."
        return 0
    }

    set cmd [concat $cfg::bot_script $cfg::bot_args]
    log_msg INFO "Starting bot: $cmd"

    # Open bot process with stdout+stderr redirected to log_file.
    set state::pid [exec {*}$cmd >> $cfg::log_file 2>&1 &]

    # Persist PID to disk so external tools can find it.
    set fh [open $cfg::pid_file w]
    puts $fh $state::pid
    close $fh

    log_msg INFO "Bot started with PID $state::pid."
    return 1
}

# stop_bot -- sends SIGTERM to the bot process and clears state.
proc stop_bot {} {
    if {$state::pid eq ""} {
        log_msg WARN "No bot process recorded; nothing to stop."
        return
    }
    log_msg INFO "Stopping bot (PID $state::pid)."
    catch { exec kill $state::pid }
    set state::pid   ""
    set state::running 0
    catch { file delete $cfg::pid_file }
    log_msg INFO "Bot stopped."
}

# process_alive -- returns 1 if pid is a running process.
proc process_alive {pid} {
    # "kill -0" tests existence without sending a real signal.
    set rc [catch { exec kill -0 $pid } err]
    return [expr {$rc == 0}]
}

# ---------------------------------------------------------------------------
# Health monitoring & auto-restart
# ---------------------------------------------------------------------------

# monitor_health -- called on a timer; restarts the bot if it has died.
proc monitor_health {} {
    if {!$state::running} return

    if {$state::pid eq "" || ![process_alive $state::pid]} {
        incr state::crashes
        log_msg ERROR "Bot process gone (crash #$state::crashes)."

        if {$state::crashes >= $cfg::max_crashes} {
            log_msg ERROR "Crash limit ($cfg::max_crashes) reached. Giving up."
            set state::running 0
            return
        }

        log_msg INFO "Auto-restarting bot in 2 seconds..."
        after 2000 start_bot
    }

    # Schedule the next check.
    after $cfg::check_ms monitor_health
}

# ---------------------------------------------------------------------------
# Log monitoring (tail -f equivalent)
# ---------------------------------------------------------------------------

# parse_log -- reads new lines appended to the log file since the last call,
#              then categorises each line as ERROR, WARNING, or INFO.
proc parse_log {} {
    if {![file exists $cfg::log_file]} return

    set fh [open $cfg::log_file r]
    # Jump to where we left off last time.
    if {$state::log_offset > 0} {
        seek $fh $state::log_offset
    }

    set new_lines {}
    while {[gets $fh line] >= 0} {
        lappend new_lines $line
    }
    set state::log_offset [tell $fh]
    close $fh

    foreach line $new_lines {
        set level INFO
        if {[string match -nocase *ERROR*   $line]} { set level ERROR   }
        if {[string match -nocase *WARNING* $line]} { set level WARNING }
        if {[string match -nocase *CRITICAL* $line]}{ set level ERROR   }

        # Forward the classified line to our own log stream.
        log_msg $level "(bot) $line"
    }
}

# watch_log -- repeating timer that polls the log file for new content.
proc watch_log {} {
    if {!$state::running} return
    parse_log
    after 1000 watch_log
}

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

proc main {} {
    log_msg INFO "=== Zerg Bot Manager starting ==="
    set state::running 1
    set state::crashes 0
    set state::log_offset 0

    start_bot

    # Kick off the health-monitor and log-watcher loops.
    after $cfg::check_ms monitor_health
    after 500            watch_log

    # Run the Tcl event loop; Ctrl-C exits.
    vwait forever
}

# Handle clean shutdown on Ctrl-C.
proc handle_interrupt {} {
    log_msg INFO "Interrupt received. Shutting down."
    stop_bot
    exit 0
}
signal add SIGINT  handle_interrupt
signal add SIGTERM handle_interrupt

main
