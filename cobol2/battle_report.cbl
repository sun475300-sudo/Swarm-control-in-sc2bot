      *================================================================*
      * BATTLE-REPORT.CBL                                            *
      * SC2 Zerg Bot – Battle Statistics Report Generator            *
      *                                                              *
      * Reads cumulative game statistics from WORKING-STORAGE,       *
      * calculates win rates and unit efficiency, then formats a     *
      * classic column-aligned battle report to the console.         *
      *                                                              *
      * Compile:  cobc -free -x battle_report.cbl -o battle_report  *
      * Run:      ./battle_report                                    *
      *================================================================*
       IDENTIFICATION DIVISION.
       PROGRAM-ID.    BATTLE-REPORT.
       AUTHOR.        지휘관봇-AI.
       DATE-WRITTEN.  2026-03-30.

      *----------------------------------------------------------------
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. X86-64.
       OBJECT-COMPUTER. X86-64.

      *----------------------------------------------------------------
       DATA DIVISION.
       WORKING-STORAGE SECTION.

      * ---- Raw game counters ----------------------------------------
       01  WS-GAMES-PLAYED          PIC 9(5)      VALUE 0.
       01  WS-GAMES-WON             PIC 9(5)      VALUE 0.
       01  WS-GAMES-LOST            PIC 9(5)      VALUE 0.

      * ---- Unit production totals -----------------------------------
       01  WS-ZERGLINGS-MADE        PIC 9(7)      VALUE 0.
       01  WS-ROACHES-MADE          PIC 9(6)      VALUE 0.
       01  WS-HYDRALISKS-MADE       PIC 9(6)      VALUE 0.
       01  WS-BANELINGS-MADE        PIC 9(6)      VALUE 0.

      * ---- Unit kill / loss counters --------------------------------
       01  WS-UNITS-KILLED          PIC 9(7)      VALUE 0.
       01  WS-UNITS-LOST            PIC 9(7)      VALUE 0.

      * ---- Economy totals -------------------------------------------
       01  WS-MINERALS-COLLECTED    PIC 9(9)      VALUE 0.
       01  WS-GAS-COLLECTED         PIC 9(9)      VALUE 0.

      * ---- Computed fields ------------------------------------------
       01  WS-WIN-RATE              PIC 9(3)V9(2) VALUE 0.
       01  WS-WIN-RATE-DISPLAY      PIC ZZ9.99    VALUE 0.
       01  WS-KD-RATIO              PIC 9(3)V9(2) VALUE 0.
       01  WS-KD-DISPLAY            PIC ZZ9.99    VALUE 0.
       01  WS-AVG-MINERALS          PIC 9(7)V9(2) VALUE 0.
       01  WS-AVG-MINERALS-DISP     PIC Z,ZZZ,ZZ9.99 VALUE 0.

      * ---- Report formatting work areas ----------------------------
       01  WS-SEPARATOR             PIC X(60)
           VALUE ALL '='.
       01  WS-BLANK-LINE            PIC X(60)
           VALUE SPACES.

      *----------------------------------------------------------------
       PROCEDURE DIVISION.

      *----------------------------------------------------------------
       000-MAIN.
           PERFORM 100-INITIALIZE-DATA
           PERFORM 200-COMPUTE-STATISTICS
           PERFORM 300-PRINT-REPORT
           STOP RUN.

      *----------------------------------------------------------------
      * 100-INITIALIZE-DATA
      * Populate working-storage with sample bot telemetry.
      * In production these would be read from a flat file or DB.
      *----------------------------------------------------------------
       100-INITIALIZE-DATA.
           MOVE 150          TO WS-GAMES-PLAYED
           MOVE 97           TO WS-GAMES-WON
           MOVE 53           TO WS-GAMES-LOST
           MOVE 48320        TO WS-ZERGLINGS-MADE
           MOVE 9410         TO WS-ROACHES-MADE
           MOVE 6870         TO WS-HYDRALISKS-MADE
           MOVE 3201         TO WS-BANELINGS-MADE
           MOVE 72440        TO WS-UNITS-KILLED
           MOVE 38910        TO WS-UNITS-LOST
           MOVE 142500000    TO WS-MINERALS-COLLECTED
           MOVE  58300000    TO WS-GAS-COLLECTED.

      *----------------------------------------------------------------
      * 200-COMPUTE-STATISTICS
      * Derive win rate, K/D ratio, and average economy per game.
      *----------------------------------------------------------------
       200-COMPUTE-STATISTICS.
           IF WS-GAMES-PLAYED > 0
               COMPUTE WS-WIN-RATE =
                   (WS-GAMES-WON / WS-GAMES-PLAYED) * 100
               COMPUTE WS-AVG-MINERALS =
                   WS-MINERALS-COLLECTED / WS-GAMES-PLAYED
           END-IF

           IF WS-UNITS-LOST > 0
               COMPUTE WS-KD-RATIO =
                   WS-UNITS-KILLED / WS-UNITS-LOST
           END-IF

           MOVE WS-WIN-RATE      TO WS-WIN-RATE-DISPLAY
           MOVE WS-KD-RATIO      TO WS-KD-DISPLAY
           MOVE WS-AVG-MINERALS  TO WS-AVG-MINERALS-DISP.

      *----------------------------------------------------------------
      * 300-PRINT-REPORT
      * Emit a formatted battle statistics report to STDOUT.
      *----------------------------------------------------------------
       300-PRINT-REPORT.
           DISPLAY WS-SEPARATOR
           DISPLAY '  SC2 ZERG BOT -- BATTLE STATISTICS REPORT'
           DISPLAY '  Generated: 2026-03-30'
           DISPLAY WS-SEPARATOR

           DISPLAY '  OVERALL RECORD'
           DISPLAY '    Games Played : ' WS-GAMES-PLAYED
           DISPLAY '    Wins         : ' WS-GAMES-WON
           DISPLAY '    Losses       : ' WS-GAMES-LOST
           DISPLAY '    Win Rate     : ' WS-WIN-RATE-DISPLAY '%'
           DISPLAY WS-BLANK-LINE

           DISPLAY '  UNIT PRODUCTION'
           DISPLAY '    Zerglings    : ' WS-ZERGLINGS-MADE
           DISPLAY '    Roaches      : ' WS-ROACHES-MADE
           DISPLAY '    Hydralisks   : ' WS-HYDRALISKS-MADE
           DISPLAY '    Banelings    : ' WS-BANELINGS-MADE
           DISPLAY WS-BLANK-LINE

           DISPLAY '  COMBAT EFFICIENCY'
           DISPLAY '    Units Killed : ' WS-UNITS-KILLED
           DISPLAY '    Units Lost   : ' WS-UNITS-LOST
           DISPLAY '    K/D Ratio    : ' WS-KD-DISPLAY
           DISPLAY WS-BLANK-LINE

           DISPLAY '  ECONOMY TOTALS'
           DISPLAY '    Minerals Mined   : ' WS-MINERALS-COLLECTED
           DISPLAY '    Gas Mined        : ' WS-GAS-COLLECTED
           DISPLAY '    Avg Min/Game     : ' WS-AVG-MINERALS-DISP

           DISPLAY WS-SEPARATOR
           DISPLAY '  END OF REPORT'
           DISPLAY WS-SEPARATOR.
