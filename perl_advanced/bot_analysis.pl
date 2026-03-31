#!/usr/bin/env perl
# Phase 559: Perl Advanced
# SC2 Bot game log analysis with Perl regex, hashes, OOP

use strict;
use warnings;
use POSIX qw(floor);
use List::Util qw(max min sum reduce);
use Scalar::Util qw(looks_like_number);

# ─────────────────────────────────────────────
# OOP via bless
# ─────────────────────────────────────────────

package SC2Bot::State;

sub new {
    my ($class, %args) = @_;
    return bless {
        minerals   => $args{minerals}   // 50,
        gas        => $args{gas}        // 0,
        supply     => $args{supply}     // 12,
        max_supply => $args{max_supply} // 14,
        workers    => $args{workers}    // 12,
        army       => $args{army}       // 0,
        frame      => $args{frame}      // 0,
        hatcheries => $args{hatcheries} // 1,
        threat     => $args{threat}     // 0.0,
    }, $class;
}

sub can_afford {
    my ($self, $min, $gas) = @_;
    $gas //= 0;
    return $self->{minerals} >= $min && $self->{gas} >= $gas;
}

sub supply_full {
    my $self = shift;
    return $self->{supply} >= $self->{max_supply} - 1;
}

sub phase {
    my $self = shift;
    my $f = $self->{frame};
    return 'opening'   if $f < 1344;
    return 'early'     if $f < 3360;
    return 'mid'       if $f < 6720;
    return 'late';
}

sub clone {
    my $self = shift;
    return bless { %$self }, ref $self;
}

package SC2Bot::Strategy;

my %UNIT_COSTS = (
    drone     => { minerals => 50,  gas => 0,  supply => 1 },
    zergling  => { minerals => 25,  gas => 0,  supply => 1 },
    roach     => { minerals => 75,  gas => 25, supply => 2 },
    hydralisk => { minerals => 100, gas => 50, supply => 2 },
    overlord  => { minerals => 100, gas => 0,  supply => 0 },
);

sub new {
    my ($class, %args) = @_;
    return bless {
        worker_cap => $args{worker_cap} // 22,
        army_unit  => $args{army_unit}  // 'zergling',
    }, $class;
}

sub decide {
    my ($self, $state) = @_;

    return 'defend'   if $state->{threat} > 0.6;
    return 'overlord' if $state->supply_full && $state->can_afford(100);
    return 'drone'    if $state->{workers} < $self->{worker_cap}
                      && $state->can_afford(50);
    return 'expand'   if $state->{minerals} >= 300
                      && $state->{hatcheries} < 3;

    my $unit = $self->{army_unit};
    my $cost = $UNIT_COSTS{$unit};
    return $unit if $cost && $state->can_afford($cost->{minerals}, $cost->{gas});
    return 'wait';
}

sub apply {
    my ($self, $state, $action) = @_;
    my $s = $state->clone;

    if (my $cost = $UNIT_COSTS{$action}) {
        return $s unless $s->can_afford($cost->{minerals}, $cost->{gas});
        $s->{minerals} -= $cost->{minerals};
        $s->{gas}      -= $cost->{gas};
        $s->{supply}   += $cost->{supply};
        $s->{workers}++ if $action eq 'drone';
        $s->{max_supply} += 8 if $action eq 'overlord';
        $s->{army} += $cost->{supply}
            unless $action =~ /^(drone|overlord)$/;
    }
    elsif ($action eq 'expand' && $s->{minerals} >= 300) {
        $s->{minerals}   -= 300;
        $s->{hatcheries}++;
        $s->{workers} += 4;
    }
    return $s;
}

package SC2Bot::Simulator;

sub new {
    my ($class, %args) = @_;
    return bless {
        state    => SC2Bot::State->new(),
        strategy => SC2Bot::Strategy->new(%args),
        history  => [],
    }, $class;
}

sub tick {
    my $self = shift;
    my $s = $self->{state};
    my $income = floor($s->{workers} * 8 / 10);
    $s->{minerals} += $income;
    $s->{frame}++;
    $s->{threat} = List::Util::min(1.0, $s->{threat} + 0.0001);
}

sub step {
    my $self = shift;
    $self->tick;
    my $action = $self->{strategy}->decide($self->{state});
    $self->{state} = $self->{strategy}->apply($self->{state}, $action);
    push @{$self->{history}}, { %{$self->{state}} };
}

sub run {
    my ($self, $n) = @_;
    $self->step for 1..$n;
    return $self;
}

sub analytics {
    my $self = shift;
    my @h = @{$self->{history}};
    return {
        avg_minerals => (sum map { $_->{minerals} } @h) / @h,
        max_workers  => max(map { $_->{workers}  } @h),
        max_army     => max(map { $_->{army}     } @h),
        final_frame  => $h[-1]{frame},
    };
}

package main;

print "Phase 559: Perl Advanced — SC2 Bot Analysis\n\n";

# Run multiple strategies
my %strategies = (
    aggressive => { army_unit => 'zergling',  worker_cap => 16 },
    eco        => { army_unit => 'hydralisk', worker_cap => 28 },
    balanced   => { army_unit => 'roach',     worker_cap => 22 },
);

for my $name (sort keys %strategies) {
    my $sim = SC2Bot::Simulator->new(%{$strategies{$name}});
    $sim->run(1500);
    my $s = $sim->{state};
    printf "  [%-12s] Frame:%-6d Min:%-6d Workers:%-4d Army:%-4d\n",
        $name, $s->{frame}, $s->{minerals}, $s->{workers}, $s->{army};
}

# Regex-based log parser demo
my @log_lines = (
    "[0001500] minerals=450 gas=0 supply=35/54 workers=22 army=18 action=roach",
    "[0001800] minerals=200 gas=100 supply=40/62 workers=25 army=24 action=hydralisk",
    "[0002000] minerals=800 gas=50  supply=44/62 workers=28 army=30 action=expand",
);

print "\nLog parsing demo:\n";
for my $line (@log_lines) {
    if ($line =~ /\[(\d+)\].*minerals=(\d+).*workers=(\d+).*army=(\d+).*action=(\w+)/) {
        printf "  Frame:%-6d Min:%-6d Workers:%-4d Army:%-4d Action:%s\n",
            $1, $2, $3, $4, $5;
    }
}

# Analytics
my $sim = SC2Bot::Simulator->new(army_unit => 'roach', worker_cap => 22);
$sim->run(2000);
my $stats = $sim->analytics;
print "\nAnalytics (2000 frames):\n";
printf "  Avg minerals: %.1f\n", $stats->{avg_minerals};
printf "  Max workers:  %d\n",   $stats->{max_workers};
printf "  Max army:     %d\n",   $stats->{max_army};
