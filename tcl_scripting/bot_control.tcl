#!/usr/bin/env tclsh
# Phase 560: Tcl Scripting
# SC2 Bot control scripting in Tcl (event loop, namespace, proc)

package require Tcl 8.6

# ─────────────────────────────────────────────
# Namespace: SC2Bot
# ─────────────────────────────────────────────

namespace eval SC2Bot {
    # Default initial state (dict)
    proc init_state {} {
        return [dict create \
            minerals   50 \
            gas        0  \
            supply     12 \
            max_supply 14 \
            workers    12 \
            army       0  \
            frame      0  \
            hatcheries 1  \
            threat     0.0 \
        ]
    }

    # Unit costs table
    variable unit_costs
    array set unit_costs {
        drone,minerals     50
        drone,gas          0
        drone,supply       1
        zergling,minerals  25
        zergling,gas       0
        zergling,supply    1
        roach,minerals     75
        roach,gas          25
        roach,supply       2
        hydralisk,minerals 100
        hydralisk,gas      50
        hydralisk,supply   2
        overlord,minerals  100
        overlord,gas       0
        overlord,supply    0
    }

    proc can_afford {state minerals {gas 0}} {
        set m [dict get $state minerals]
        set g [dict get $state gas]
        return [expr {$m >= $minerals && $g >= $gas}]
    }

    proc supply_full {state} {
        set sup [dict get $state supply]
        set max [dict get $state max_supply]
        return [expr {$sup >= $max - 1}]
    }

    proc decide {state} {
        set threat  [dict get $state threat]
        set workers [dict get $state workers]
        set min     [dict get $state minerals]
        set hatch   [dict get $state hatcheries]

        if {$threat > 0.6} { return "defend" }
        if {[supply_full $state] && [can_afford $state 100]} {
            return "overlord"
        }
        if {$workers < 22 && [can_afford $state 50]} {
            return "drone"
        }
        if {$min >= 300 && $hatch < 3} {
            return "expand"
        }
        if {[can_afford $state 75 25]} {
            return "roach"
        }
        if {[can_afford $state 25]} {
            return "zergling"
        }
        return "wait"
    }

    proc apply_action {state action} {
        variable unit_costs
        switch -- $action {
            "drone" - "zergling" - "roach" - "hydralisk" - "overlord" {
                set mc $unit_costs($action,minerals)
                set gc $unit_costs($action,gas)
                set sc $unit_costs($action,supply)
                if {![can_afford $state $mc $gc]} { return $state }
                dict set state minerals [expr {[dict get $state minerals] - $mc}]
                dict set state gas      [expr {[dict get $state gas] - $gc}]
                dict set state supply   [expr {[dict get $state supply] + $sc}]
                switch -- $action {
                    "drone"    { dict set state workers [expr {[dict get $state workers] + 1}] }
                    "overlord" { dict set state max_supply [expr {[dict get $state max_supply] + 8}] }
                    default    { dict set state army [expr {[dict get $state army] + $sc}] }
                }
            }
            "expand" {
                if {[dict get $state minerals] < 300} { return $state }
                dict set state minerals   [expr {[dict get $state minerals] - 300}]
                dict set state hatcheries [expr {[dict get $state hatcheries] + 1}]
                dict set state workers    [expr {[dict get $state workers] + 4}]
            }
        }
        return $state
    }

    proc tick {state} {
        set income [expr {int([dict get $state workers] * 8 / 10)}]
        dict set state minerals [expr {[dict get $state minerals] + $income}]
        dict set state frame    [expr {[dict get $state frame] + 1}]
        set new_threat [expr {min(1.0, [dict get $state threat] + 0.0001)}]
        dict set state threat $new_threat
        return $state
    }

    proc step {state} {
        set state [tick $state]
        set action [decide $state]
        return [apply_action $state $action]
    }

    proc simulate {state n} {
        set history {}
        for {set i 0} {$i < $n} {incr i} {
            set state [step $state]
            lappend history $state
        }
        return [list state $state history $history]
    }

    proc print_state {state} {
        puts [format "Frame:%-6d Min:%-6d Workers:%-4d Army:%-4d Supply:%d/%d" \
            [dict get $state frame] \
            [dict get $state minerals] \
            [dict get $state workers] \
            [dict get $state army] \
            [dict get $state supply] \
            [dict get $state max_supply]]
    }
}

# ─────────────────────────────────────────────
# Event-driven simulation via after
# ─────────────────────────────────────────────

namespace eval SC2Bot::EventLoop {
    variable state
    variable frame_count
    variable max_frames

    proc start {initial n} {
        variable state
        variable frame_count
        variable max_frames
        set state $initial
        set frame_count 0
        set max_frames $n
        schedule_tick
        vwait done
    }

    proc schedule_tick {} {
        after 0 [namespace code tick_handler]
    }

    proc tick_handler {} {
        variable state
        variable frame_count
        variable max_frames
        set state [SC2Bot::step $state]
        incr frame_count
        if {$frame_count >= $max_frames} {
            set [namespace parent]::done 1
        } else {
            schedule_tick
        }
    }
}

# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

puts "Phase 560: Tcl Scripting — SC2 Bot Control"
puts ""

# Basic simulation
set initial [SC2Bot::init_state]
set result [SC2Bot::simulate $initial 2000]
set final_state [dict get $result state]

SC2Bot::print_state $final_state

# Multi-strategy comparison
puts "\nStrategy comparison (1000 frames):"
foreach strategy {aggressive eco balanced} {
    set s [SC2Bot::init_state]
    # Modify strategy by adjusting initial parameters
    if {$strategy eq "aggressive"} {
        dict set s workers 8  ;# fewer drones
    } elseif {$strategy eq "eco"} {
        dict set s minerals 200  ;# head start
    }
    set res [SC2Bot::simulate $s 1000]
    set fs [dict get $res state]
    puts [format "  \[%-12s\] Min:%-6d Workers:%-4d Army:%-4d" \
        $strategy \
        [dict get $fs minerals] \
        [dict get $fs workers] \
        [dict get $fs army]]
}
