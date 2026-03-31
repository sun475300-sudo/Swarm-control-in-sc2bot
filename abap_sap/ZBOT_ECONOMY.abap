*&---------------------------------------------------------------------*
*& Phase 556: ABAP SAP
*& SC2 Bot economy analytics in ABAP — SAP integration pattern
*&---------------------------------------------------------------------*
REPORT zbot_economy.

*─────────────────────────────────────────────
* Data types
*─────────────────────────────────────────────

TYPES:
  BEGIN OF ty_game_state,
    minerals   TYPE i,
    gas        TYPE i,
    supply     TYPE i,
    max_supply TYPE i,
    workers    TYPE i,
    army       TYPE i,
    frame      TYPE i,
    hatcheries TYPE i,
  END OF ty_game_state.

TYPES:
  BEGIN OF ty_unit_cost,
    unit_type TYPE c LENGTH 15,
    minerals  TYPE i,
    gas       TYPE i,
    supply    TYPE i,
  END OF ty_unit_cost.

TYPES: ty_unit_costs TYPE STANDARD TABLE OF ty_unit_cost
    WITH KEY unit_type.

*─────────────────────────────────────────────
* Constants
*─────────────────────────────────────────────

CONSTANTS:
  c_drone     TYPE c LENGTH 15 VALUE 'DRONE          ',
  c_zergling  TYPE c LENGTH 15 VALUE 'ZERGLING       ',
  c_roach     TYPE c LENGTH 15 VALUE 'ROACH          ',
  c_hydra     TYPE c LENGTH 15 VALUE 'HYDRALISK      ',
  c_overlord  TYPE c LENGTH 15 VALUE 'OVERLORD       '.

*─────────────────────────────────────────────
* Class definition
*─────────────────────────────────────────────

CLASS lcl_sc2_bot DEFINITION.
  PUBLIC SECTION.
    METHODS:
      constructor,
      tick,
      decide
        RETURNING VALUE(rv_action) TYPE string,
      apply_action
        IMPORTING iv_action TYPE string,
      simulate
        IMPORTING iv_frames TYPE i,
      print_state.

  PRIVATE SECTION.
    DATA: ms_state TYPE ty_game_state,
          mt_costs TYPE ty_unit_costs.

    METHODS:
      init_costs,
      can_afford
        IMPORTING iv_minerals TYPE i
                  iv_gas      TYPE i
        RETURNING VALUE(rv_can) TYPE abap_bool,
      supply_full
        RETURNING VALUE(rv_full) TYPE abap_bool.
ENDCLASS.

CLASS lcl_sc2_bot IMPLEMENTATION.

  METHOD constructor.
    ms_state-minerals   = 50.
    ms_state-gas        = 0.
    ms_state-supply     = 12.
    ms_state-max_supply = 14.
    ms_state-workers    = 12.
    ms_state-army       = 0.
    ms_state-frame      = 0.
    ms_state-hatcheries = 1.
    CALL METHOD init_costs.
  ENDMETHOD.

  METHOD init_costs.
    DATA: ls_cost TYPE ty_unit_cost.
    ls_cost-unit_type = c_drone.     ls_cost-minerals = 50.
    ls_cost-gas = 0. ls_cost-supply = 1.
    INSERT ls_cost INTO TABLE mt_costs.
    ls_cost-unit_type = c_zergling.  ls_cost-minerals = 25.
    ls_cost-gas = 0. ls_cost-supply = 1.
    INSERT ls_cost INTO TABLE mt_costs.
    ls_cost-unit_type = c_roach.     ls_cost-minerals = 75.
    ls_cost-gas = 25. ls_cost-supply = 2.
    INSERT ls_cost INTO TABLE mt_costs.
    ls_cost-unit_type = c_hydra.     ls_cost-minerals = 100.
    ls_cost-gas = 50. ls_cost-supply = 2.
    INSERT ls_cost INTO TABLE mt_costs.
    ls_cost-unit_type = c_overlord.  ls_cost-minerals = 100.
    ls_cost-gas = 0. ls_cost-supply = 0.
    INSERT ls_cost INTO TABLE mt_costs.
  ENDMETHOD.

  METHOD can_afford.
    rv_can = abap_false.
    IF ms_state-minerals >= iv_minerals AND
       ms_state-gas >= iv_gas.
      rv_can = abap_true.
    ENDIF.
  ENDMETHOD.

  METHOD supply_full.
    rv_full = abap_false.
    IF ms_state-supply >= ms_state-max_supply - 1.
      rv_full = abap_true.
    ENDIF.
  ENDMETHOD.

  METHOD tick.
    DATA: lv_income TYPE i.
    lv_income = ms_state-workers * 8 / 10.
    ADD lv_income TO ms_state-minerals.
    ADD 1 TO ms_state-frame.
  ENDMETHOD.

  METHOD decide.
    IF supply_full( ) = abap_true AND
       can_afford( iv_minerals = 100 iv_gas = 0 ) = abap_true.
      rv_action = 'OVERLORD'.
    ELSEIF ms_state-workers < 22 AND
           can_afford( iv_minerals = 50 iv_gas = 0 ) = abap_true.
      rv_action = 'DRONE'.
    ELSEIF ms_state-minerals >= 300 AND ms_state-hatcheries < 3.
      rv_action = 'EXPAND'.
    ELSEIF can_afford( iv_minerals = 75 iv_gas = 25 ) = abap_true.
      rv_action = 'ROACH'.
    ELSEIF can_afford( iv_minerals = 25 iv_gas = 0 ) = abap_true.
      rv_action = 'ZERGLING'.
    ELSE.
      rv_action = 'WAIT'.
    ENDIF.
  ENDMETHOD.

  METHOD apply_action.
    CASE iv_action.
      WHEN 'DRONE'.
        IF can_afford( iv_minerals = 50 iv_gas = 0 ) = abap_true.
          SUBTRACT 50 FROM ms_state-minerals.
          ADD 1 TO ms_state-workers.
          ADD 1 TO ms_state-supply.
        ENDIF.
      WHEN 'ZERGLING'.
        IF can_afford( iv_minerals = 25 iv_gas = 0 ) = abap_true.
          SUBTRACT 25 FROM ms_state-minerals.
          ADD 1 TO ms_state-army.
          ADD 1 TO ms_state-supply.
        ENDIF.
      WHEN 'ROACH'.
        IF can_afford( iv_minerals = 75 iv_gas = 25 ) = abap_true.
          SUBTRACT 75 FROM ms_state-minerals.
          SUBTRACT 25 FROM ms_state-gas.
          ADD 2 TO ms_state-army.
          ADD 2 TO ms_state-supply.
        ENDIF.
      WHEN 'OVERLORD'.
        IF can_afford( iv_minerals = 100 iv_gas = 0 ) = abap_true.
          SUBTRACT 100 FROM ms_state-minerals.
          ADD 8 TO ms_state-max_supply.
        ENDIF.
      WHEN 'EXPAND'.
        IF ms_state-minerals >= 300.
          SUBTRACT 300 FROM ms_state-minerals.
          ADD 1 TO ms_state-hatcheries.
          ADD 4 TO ms_state-workers.
        ENDIF.
    ENDCASE.
  ENDMETHOD.

  METHOD simulate.
    DATA: lv_i      TYPE i,
          lv_action TYPE string.
    DO iv_frames TIMES.
      tick( ).
      lv_action = decide( ).
      apply_action( lv_action ).
    ENDDO.
  ENDMETHOD.

  METHOD print_state.
    WRITE: / 'Frame:    ', ms_state-frame.
    WRITE: / 'Minerals: ', ms_state-minerals.
    WRITE: / 'Workers:  ', ms_state-workers.
    WRITE: / 'Army:     ', ms_state-army.
    WRITE: / 'Supply:   ', ms_state-supply, '/', ms_state-max_supply.
    WRITE: / 'Hatches:  ', ms_state-hatcheries.
  ENDMETHOD.

ENDCLASS.

*─────────────────────────────────────────────
* Main program
*─────────────────────────────────────────────

START-OF-SELECTION.
  DATA: lo_bot TYPE REF TO lcl_sc2_bot.

  WRITE: / 'Phase 556: ABAP SAP — SC2 Bot Economy Analytics'.
  WRITE: /.

  CREATE OBJECT lo_bot.
  lo_bot->simulate( 2000 ).
  lo_bot->print_state( ).
