\ Wicked Zerg - Battle Simulation
\ Phase 124: Forth

variable unit-count
variable total-damage

: battle-sim ( units -- damage )
  0 swap
  begin @ while
    5 + swap @ swap
  repeat
  drop
;

: calculate-swarm-damage ( n -- damage )
  5 *
;

: swarm-formation ( center-x center-y count radius -- )
  >r >r ( count )
  0 do
    r@ ( 2*pi* i / count ) fsin
    r> ( radius ) f*
    fswap
    r@ ( 2*pi* i / count ) fcos
    r> ( radius ) f*
    fswap
    ( x y )  f. f. cr
  loop
  rdrop rdrop
;

: unit-strength ( health damage armor -- strength )
  >r >r * r> 100 / 
  r> 100 / 1 swap - *
;

: battle-outcome ( attack-power defense-power -- flag )
  >
;
