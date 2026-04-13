#!/usr/bin/perl
# Phase 190: Perl

sub calculate_swarm_damage {
    my ($count) = @_;
    return $count * 5;
}

print calculate_swarm_damage(10), "\n";
