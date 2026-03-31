       IDENTIFICATION DIVISION.
       PROGRAM-ID. SC2BOTDATA.
       AUTHOR. SWARM-CONTROL-SYSTEM.
      *Phase 553: COBOL Legacy
      *SC2 Bot economy data processing in COBOL
      *Demonstrates legacy system integration for game analytics

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT GAME-LOG-FILE
               ASSIGN TO "game_log.dat"
               ORGANIZATION IS SEQUENTIAL.
           SELECT REPORT-FILE
               ASSIGN TO "bot_report.txt"
               ORGANIZATION IS SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.
       FD GAME-LOG-FILE.
       01 GAME-LOG-RECORD.
          05 GL-FRAME         PIC 9(6).
          05 GL-MINERALS      PIC 9(5).
          05 GL-GAS           PIC 9(4).
          05 GL-SUPPLY        PIC 9(3).
          05 GL-MAX-SUPPLY    PIC 9(3).
          05 GL-WORKERS       PIC 9(3).
          05 GL-ARMY          PIC 9(4).
          05 GL-ACTION        PIC X(15).

       FD REPORT-FILE.
       01 REPORT-RECORD       PIC X(80).

       WORKING-STORAGE SECTION.
       01 WS-GAME-STATE.
          05 WS-MINERALS      PIC 9(5)   VALUE 50.
          05 WS-GAS           PIC 9(4)   VALUE 0.
          05 WS-SUPPLY        PIC 9(3)   VALUE 12.
          05 WS-MAX-SUPPLY    PIC 9(3)   VALUE 14.
          05 WS-WORKERS       PIC 9(3)   VALUE 12.
          05 WS-ARMY          PIC 9(4)   VALUE 0.
          05 WS-FRAME         PIC 9(6)   VALUE 0.
          05 WS-HATCHERIES    PIC 9(2)   VALUE 1.

       01 WS-INCOME           PIC 9(5).
       01 WS-LOOP-CTR         PIC 9(6).
       01 WS-ACTION           PIC X(15).
       01 WS-UNIT-COST-M      PIC 9(4).
       01 WS-UNIT-COST-G      PIC 9(4).
       01 WS-UNIT-COST-S      PIC 9(3).

       01 WS-REPORT-LINE.
          05 RP-LABEL         PIC X(20).
          05 RP-VALUE         PIC Z(5)9.

       01 WS-ANALYTICS.
          05 WS-TOTAL-MINERALS PIC 9(10)  VALUE 0.
          05 WS-MAX-WORKERS    PIC 9(3)   VALUE 0.
          05 WS-MAX-ARMY       PIC 9(4)   VALUE 0.
          05 WS-EXPAND-FRAME   PIC 9(6)   VALUE 999999.

       01 WS-SUPPLY-RATIO     PIC 9V99.
       01 WS-EOF-FLAG         PIC X      VALUE 'N'.
       01 WS-FRAMES-TO-SIM    PIC 9(6)   VALUE 2000.

       PROCEDURE DIVISION.
       MAIN-PARA.
           DISPLAY "Phase 553: COBOL Legacy - SC2 Bot Economy"
           PERFORM SIMULATE-GAME
               VARYING WS-LOOP-CTR FROM 1 BY 1
               UNTIL WS-LOOP-CTR > WS-FRAMES-TO-SIM
           PERFORM PRINT-REPORT
           STOP RUN.

       SIMULATE-GAME.
           PERFORM TICK-ECONOMY
           PERFORM MAKE-DECISION
           PERFORM APPLY-ACTION.

       TICK-ECONOMY.
           COMPUTE WS-INCOME = WS-WORKERS * 8 / 10
           ADD WS-INCOME TO WS-MINERALS
           ADD 1 TO WS-FRAME
           IF WS-MINERALS > WS-TOTAL-MINERALS
               MOVE WS-MINERALS TO WS-TOTAL-MINERALS.

       MAKE-DECISION.
           COMPUTE WS-SUPPLY-RATIO = WS-SUPPLY / WS-MAX-SUPPLY
           EVALUATE TRUE
               WHEN WS-SUPPLY-RATIO >= 0.95 AND
                    WS-MINERALS >= 100
                   MOVE "OVERLORD     " TO WS-ACTION
               WHEN WS-WORKERS < 22 AND
                    WS-MINERALS >= 50
                   MOVE "DRONE        " TO WS-ACTION
               WHEN WS-MINERALS >= 300 AND
                    WS-HATCHERIES < 3
                   MOVE "EXPAND       " TO WS-ACTION
               WHEN WS-MINERALS >= 75 AND
                    WS-GAS >= 25
                   MOVE "ROACH        " TO WS-ACTION
               WHEN WS-MINERALS >= 25
                   MOVE "ZERGLING     " TO WS-ACTION
               WHEN OTHER
                   MOVE "WAIT         " TO WS-ACTION
           END-EVALUATE.

       APPLY-ACTION.
           EVALUATE WS-ACTION
               WHEN "DRONE        "
                   MOVE 50 TO WS-UNIT-COST-M
                   MOVE 0  TO WS-UNIT-COST-G
                   MOVE 1  TO WS-UNIT-COST-S
                   PERFORM TRAIN-UNIT
                   ADD 1 TO WS-WORKERS
                   IF WS-WORKERS > WS-MAX-WORKERS
                       MOVE WS-WORKERS TO WS-MAX-WORKERS
                   END-IF
               WHEN "ZERGLING     "
                   MOVE 25 TO WS-UNIT-COST-M
                   MOVE 0  TO WS-UNIT-COST-G
                   MOVE 1  TO WS-UNIT-COST-S
                   PERFORM TRAIN-UNIT
                   ADD 1 TO WS-ARMY
                   IF WS-ARMY > WS-MAX-ARMY
                       MOVE WS-ARMY TO WS-MAX-ARMY
                   END-IF
               WHEN "ROACH        "
                   MOVE 75 TO WS-UNIT-COST-M
                   MOVE 25 TO WS-UNIT-COST-G
                   MOVE 2  TO WS-UNIT-COST-S
                   PERFORM TRAIN-UNIT
                   ADD 2 TO WS-ARMY
               WHEN "OVERLORD     "
                   MOVE 100 TO WS-UNIT-COST-M
                   MOVE 0   TO WS-UNIT-COST-G
                   MOVE 0   TO WS-UNIT-COST-S
                   PERFORM TRAIN-UNIT
                   ADD 8 TO WS-MAX-SUPPLY
               WHEN "EXPAND       "
                   SUBTRACT 300 FROM WS-MINERALS
                   ADD 1 TO WS-HATCHERIES
                   ADD 4 TO WS-WORKERS
                   IF WS-EXPAND-FRAME = 999999
                       MOVE WS-FRAME TO WS-EXPAND-FRAME
                   END-IF
           END-EVALUATE.

       TRAIN-UNIT.
           IF WS-MINERALS >= WS-UNIT-COST-M AND
              WS-GAS >= WS-UNIT-COST-G
               SUBTRACT WS-UNIT-COST-M FROM WS-MINERALS
               SUBTRACT WS-UNIT-COST-G FROM WS-GAS
               ADD WS-UNIT-COST-S TO WS-SUPPLY.

       PRINT-REPORT.
           DISPLAY "==============================="
           DISPLAY "FINAL GAME STATE REPORT"
           DISPLAY "==============================="
           MOVE "Frame:        " TO RP-LABEL
           MOVE WS-FRAME TO RP-VALUE
           DISPLAY WS-REPORT-LINE
           MOVE "Minerals:     " TO RP-LABEL
           MOVE WS-MINERALS TO RP-VALUE
           DISPLAY WS-REPORT-LINE
           MOVE "Workers:      " TO RP-LABEL
           MOVE WS-WORKERS TO RP-VALUE
           DISPLAY WS-REPORT-LINE
           MOVE "Army:         " TO RP-LABEL
           MOVE WS-ARMY TO RP-VALUE
           DISPLAY WS-REPORT-LINE
           MOVE "Supply:       " TO RP-LABEL
           MOVE WS-SUPPLY TO RP-VALUE
           DISPLAY WS-REPORT-LINE
           MOVE "Max Supply:   " TO RP-LABEL
           MOVE WS-MAX-SUPPLY TO RP-VALUE
           DISPLAY WS-REPORT-LINE
           MOVE "Hatcheries:   " TO RP-LABEL
           MOVE WS-HATCHERIES TO RP-VALUE
           DISPLAY WS-REPORT-LINE
           DISPLAY "==============================="
           DISPLAY "ANALYTICS"
           DISPLAY "==============================="
           MOVE "Max Workers:  " TO RP-LABEL
           MOVE WS-MAX-WORKERS TO RP-VALUE
           DISPLAY WS-REPORT-LINE
           MOVE "Max Army:     " TO RP-LABEL
           MOVE WS-MAX-ARMY TO RP-VALUE
           DISPLAY WS-REPORT-LINE
           MOVE "Expand Frame: " TO RP-LABEL
           MOVE WS-EXPAND-FRAME TO RP-VALUE
           DISPLAY WS-REPORT-LINE.
