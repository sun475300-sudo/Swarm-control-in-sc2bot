#!/usr/bin/env raku
# log_analyzer.raku
# Raku (Perl 6) advanced log analysis for the StarCraft II Zerg bot.
# Uses a named-capture Grammar to parse structured bot.log lines, then
# aggregates statistics: error/warning/info counts and average response time.

use v6;

# ---------------------------------------------------------------------------
# Grammar – parses lines emitted by run_bot.py
# Example log line:
#   [2026-03-30 14:05:22] [INFO ] response_time=0.045s Overlord sent to scout
# ---------------------------------------------------------------------------
grammar BotLogLine {
    # Top-level rule: a full log line.
    rule TOP {
        <timestamp> \s+ <level> \s+ <body>
    }

    # Timestamp in brackets: [YYYY-MM-DD HH:MM:SS]
    token timestamp {
        '[' $<date>=[\d ** 4 '-' \d ** 2 '-' \d ** 2]
        \s+
        $<time>=[\d ** 2 ':' \d ** 2 ':' \d ** 2]
        ']'
    }

    # Severity tag in brackets with optional padding: [INFO ], [ERROR], etc.
    token level {
        '[' $<tag>=[INFO|WARNING|ERROR|DEBUG|CRITICAL] \s* ']'
    }

    # Everything after the level; optionally starts with response_time=Xs.
    token body {
        [ 'response_time=' $<rt>=[\d+ ['.' \d+]?] 's' \s+ ]?
        $<message>=[\N+]
    }
}

# ---------------------------------------------------------------------------
# LogEntry – structured record produced by the grammar actions.
# ---------------------------------------------------------------------------
class LogEntry {
    has Str  $.timestamp;
    has Str  $.level;
    has Str  $.message;
    has Rat  $.response_time;   # 0 when not present in the line

    method Str {
        "[{$.level}] {$.timestamp}  rt={$.response_time}s  {$.message}"
    }
}

# ---------------------------------------------------------------------------
# parse-line -- attempts to match one log line and return a LogEntry.
# ---------------------------------------------------------------------------
sub parse-line(Str $line --> LogEntry) {
    my $m = BotLogLine.parse($line);
    return LogEntry unless $m;   # return type object (undefined) on parse failure

    my $rt = $m<body><rt> ?? $m<body><rt>.Rat !! 0.0;

    return LogEntry.new(
        timestamp     => ~$m<timestamp>,
        level         => ~$m<level><tag>,
        message       => ~$m<body><message>,
        response_time => $rt,
    );
}

# ---------------------------------------------------------------------------
# analyze-log -- reads a log file (or list of lines) and returns statistics.
# ---------------------------------------------------------------------------
sub analyze-log(@lines) {
    my Int $error_count   = 0;
    my Int $warning_count = 0;
    my Int $info_count    = 0;
    my Int $debug_count   = 0;
    my Int $parse_fail    = 0;

    my Rat @response_times;            # collect all recorded response times
    my     @error_messages;            # keep a sample of error lines

    for @lines -> $line {
        next if $line ~~ /^\s*$/;      # skip blank lines

        my $entry = parse-line($line);
        unless $entry.defined {
            $parse_fail++;
            next;
        }

        given $entry.level {
            when 'ERROR'    | 'CRITICAL' { $error_count++;   push @error_messages, $entry }
            when 'WARNING'               { $warning_count++  }
            when 'INFO'                  { $info_count++     }
            when 'DEBUG'                 { $debug_count++    }
        }

        if $entry.response_time > 0 {
            push @response_times, $entry.response_time;
        }
    }

    my Rat $avg_rt = @response_times
        ?? (@response_times.sum / @response_times.elems).Rat
        !! 0.0;

    my Rat $max_rt = @response_times ?? @response_times.max !! 0.0;

    return %(
        error_count      => $error_count,
        warning_count    => $warning_count,
        info_count       => $info_count,
        debug_count      => $debug_count,
        parse_failures   => $parse_fail,
        avg_response_time => $avg_rt,
        max_response_time => $max_rt,
        rt_samples       => +@response_times,
        error_messages   => @error_messages,
    );
}

# ---------------------------------------------------------------------------
# Demo: synthetic log lines that mimic real bot output
# ---------------------------------------------------------------------------
my @sample_log = (
    '[2026-03-30 14:00:01] [INFO ] response_time=0.012s Bot initialised, race=Zerg',
    '[2026-03-30 14:00:05] [INFO ] response_time=0.018s 12 workers created',
    '[2026-03-30 14:00:30] [INFO ] response_time=0.023s Spawning Pool construction started',
    '[2026-03-30 14:01:02] [WARNING] response_time=0.031s Mineral shortage detected: 45 minerals',
    '[2026-03-30 14:01:45] [INFO ] response_time=0.019s Overlord sent to scout',
    '[2026-03-30 14:02:10] [ERROR  ] response_time=0.250s Action queue overflow, clearing 8 stale commands',
    '[2026-03-30 14:02:55] [INFO ] response_time=0.021s Zergling x4 produced',
    '[2026-03-30 14:03:30] [WARNING] Supply blocked: supply_used=18 supply_cap=18',
    '[2026-03-30 14:04:00] [ERROR  ] response_time=0.312s Could not find valid expansion location',
    '[2026-03-30 14:04:45] [INFO ] response_time=0.015s Metabolic Boost research begun',
    '[2026-03-30 14:05:20] [DEBUG  ] unit_tag=0x4AF2 state=moving',
    '   ',   # blank line — should be skipped
    'malformed-line-no-brackets',   # should count as parse failure
);

my %stats = analyze-log(@sample_log);

say "=== Zerg Bot Log Analysis ===";
say "  Lines parsed OK  : { %stats<info_count> + %stats<warning_count> + %stats<error_count> + %stats<debug_count> }";
say "  Errors           : { %stats<error_count> }";
say "  Warnings         : { %stats<warning_count> }";
say "  Info             : { %stats<info_count> }";
say "  Debug            : { %stats<debug_count> }";
say "  Parse failures   : { %stats<parse_failures> }";
say "  Response samples : { %stats<rt_samples> }";
say sprintf("  Avg response time: %.3fs", %stats<avg_response_time>);
say sprintf("  Max response time: %.3fs", %stats<max_response_time>);

if %stats<error_messages>.elems > 0 {
    say "\n--- Error details ---";
    for @(%stats<error_messages>) -> $e {
        say "  " ~ $e.Str;
    }
}
