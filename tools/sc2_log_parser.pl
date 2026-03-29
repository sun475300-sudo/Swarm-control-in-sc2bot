#!/usr/bin/env perl
# P84: Perl - Text Processing & Log Analysis
# SC2 AI Bot - Log Parser & Pattern Matcher

use strict;
use warnings;
use v5.20;
use JSON::XS;
use Time::HiRes qw(gettimeofday tv_interval);
use File::Basename;
use Getopt::Long;

my %config = (
    verbose => 0,
    output_format => 'json',
    max_lines => 0,
);

GetOptions(
    'v|verbose' => \$config{verbose},
    'o|output=s' => \$config{output_format},
    'n|max=i' => \$config{max_lines},
    'h|help' => \&show_help,
) or die "Error in command line arguments\n";

sub show_help {
    print <<"EOF";
SC2 AI Bot Log Parser
Usage: $0 [options] <logfile>

Options:
    -v, --verbose       Verbose output
    -o, --output FORMAT Output format (json, csv, txt)
    -n, --max LINES     Maximum lines to process
    -h, --help          Show this help

Examples:
    $0 bot.log
    $0 -v -o csv bot.log
    $0 -n 1000 game.log
EOF
    exit;
}

my $logfile = shift @ARGV or show_help();

print "Processing: $logfile\n" if $config{verbose};

open my $fh, '<', $logfile or die "Cannot open $logfile: $!\n";

my @patterns = (
    {
        name => 'ERROR',
        regex => qr/ERROR|CRITICAL|EXCEPTION/i,
        severity => 'high',
    },
    {
        name => 'WARNING',
        regex => qr/WARN(ING)?|CAUTION/i,
        severity => 'medium',
    },
    {
        name => 'GAME_START',
        regex => qr/GAME.*START|MATCH.*BEGIN/i,
        severity => 'info',
    },
    {
        name => 'GAME_END',
        regex => qr/GAME.*(END|OVER)|MATCH.*(END|FINISH)/i,
        severity => 'info',
    },
    {
        name => 'UNIT_SPAWN',
        regex => qr/(SPAWN|CREATE).*\b(DRONE|ZERGLING|ROACH|HYDRALISK|MUTALISK)\b/i,
        severity => 'debug',
    },
    {
        name => 'COMBAT',
        regex => qr/COMBAT|ATTACK|ENGAGE/i,
        severity => 'debug',
    },
    {
        name => 'DECISION',
        regex => qr/DECISION|CHOOSING|SELECTED.*ACTION/i,
        severity => 'debug',
    },
    {
        name => 'RESOURCE',
        regex => qr/MINERAL|GAS|VESPENE|collect/i,
        severity => 'debug',
    },
    {
        name => 'PERFORMANCE',
        regex => qr/FPS|latency|ms|TICK/i,
        severity => 'info',
    },
);

my %stats = (
    total_lines => 0,
    errors => 0,
    warnings => 0,
    game_starts => 0,
    game_ends => 0,
    units_spawned => 0,
    combats => 0,
    patterns => {},
);

my @entries;

sub parse_timestamp {
    my $line = shift;
    if ($line =~ /(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[\.,]\d{3}|\d{2}:\d{2}:\d{2})/) {
        return $1;
    }
    return 'unknown';
}

sub analyze_line {
    my $line = shift;
    my %entry = (
        line => $line,
        timestamp => parse_timestamp($line),
        matched_patterns => [],
    );

    for my $pattern (@patterns) {
        if ($line =~ $pattern->{regex}) {
            push @{$entry{matched_patterns}}, $pattern->{name};
            $stats{patterns}{$pattern->{name}}++;
            
            $stats{errors}++ if $pattern->{name} eq 'ERROR';
            $stats{warnings}++ if $pattern->{name} eq 'WARNING';
            $stats{game_starts}++ if $pattern->{name} eq 'GAME_START';
            $stats{game_ends}++ if $pattern->{name} eq 'GAME_END';
            $stats{units_spawned}++ if $pattern->{name} eq 'UNIT_SPAWN';
            $stats{combats}++ if $pattern->{name} eq 'COMBAT';
        }
    }

    return \%entry;
}

my $t0 = [gettimeofday];
my $line_count = 0;

while (my $line = <$fh>) {
    last if $config{max_lines} && $line_count >= $config{max_lines};
    chomp $line;
    $line_count++;
    
    $stats{total_lines}++;
    
    my $entry = analyze_line($line);
    push @entries, $entry if @{$entry->{matched_patterns}} > 0;
    
    print "\rProcessed $line_count lines..." if $config{verbose} && $line_count % 100 == 0;
}

my $elapsed = tv_interval($t0);
close $fh;

print "\n\n" if $config{verbose};

my %report = (
    summary => {
        total_lines => $stats{total_lines},
        processing_time => sprintf("%.3f", $elapsed),
        lines_per_second => sprintf("%.0f", $stats{total_lines} / $elapsed),
    },
    counts => {
        errors => $stats{errors},
        warnings => $stats{warnings},
        game_starts => $stats{game_starts},
        game_ends => $stats{game_ends},
        units_spawned => $stats{units_spawned},
        combats => $stats{combats},
    },
    patterns => $stats{patterns},
    entries => \@entries,
);

if ($config{output_format} eq 'json') {
    print encode_json(\%report);
} elsif ($config{output_format} eq 'csv') {
    print "pattern,count\n";
    for my $pattern (sort { $stats{patterns}{$b} <=> $stats{patterns}{$a} } keys %{$stats{patterns}}) {
        print "$pattern,$stats{patterns}{$pattern}\n";
    }
} else {
    print "=" x 60, "\n";
    print "SC2 Bot Log Analysis Report\n";
    print "=" x 60, "\n";
    printf "Total Lines: %d\n", $stats{total_lines};
    printf "Processing Time: %.3fs\n", $elapsed;
    printf "Lines/Second: %.0f\n", $stats{total_lines} / $elapsed;
    print "-" x 60, "\n";
    print "Errors: $stats{errors}\n";
    print "Warnings: $stats{warnings}\n";
    print "Game Starts: $stats{game_starts}\n";
    print "Game Ends: $stats{game_ends}\n";
    print "Units Spawned: $stats{units_spawned}\n";
    print "Combats: $stats{combats}\n";
    print "=" x 60, "\n";
}

sub END {
    print STDERR "\nDone.\n" if $config{verbose};
}

1;

__END__

=head1 NAME

sc2_log_parser.pl - Parse and analyze SC2 AI Bot logs

=head1 SYNOPSIS

    perl sc2_log_parser.pl -v bot.log
    perl sc2_log_parser.pl -o csv bot.log > results.csv

=head1 DESCRIPTION

This script parses StarCraft II AI bot logs and extracts useful information
such as errors, warnings, game events, and performance metrics.

=cut
