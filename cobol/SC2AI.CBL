       ID DIVISION.
       PROGRAM-ID. SC2AI-COMBAT.
       AUTHOR. WICKED-ZERG.
       DATE-WRITTEN. 2026-03-29.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  UNIT-COUNT             PIC 9(04) VALUE ZERO.
       01  COMBAT-POWER           PIC 9(06) VALUE ZERO.
       01  THREAT-LEVEL            PIC X(10) VALUE 'LOW'.
       01  RESOURCES.
           05  MINERALS            PIC 9(05) VALUE 0.
           05  GAS                 PIC 9(05) VALUE 0.
           05  SUPPLY              PIC 9(03) VALUE 0.
       01  GAME-STATE.
           05  PHASE               PIC X(20) VALUE 'EARLY-GAME'.
           05  ENEMY-RACE           PIC X(10) VALUE 'UNKNOWN'.

       PROCEDURE DIVISION.
       MAIN-PROCESS.
           DISPLAY 'SC2 AI Combat System (COBOL)'
           DISPLAY 'Initializing...'
           
           PERFORM INITIALIZE-GAME
           PERFORM GAME-LOOP
           STOP RUN.

       INITIALIZE-GAME.
           MOVE 50 TO MINERALS
           MOVE 0 TO GAS
           MOVE 12 TO SUPPLY
           MOVE 'EARLY-GAME' TO PHASE.

       GAME-LOOP.
           PERFORM ANALYZE-COMBAT
           PERFORM CALCULATE-POWER
           PERFORM DETERMINE-ACTION
           PERFORM EXECUTE-ORDERS
           GO TO GAME-LOOP.

       ANALYZE-COMBAT.
           COMPUTE UNIT-COUNT = FUNCTION RANDOM(200)
           IF UNIT-COUNT > 150
               MOVE 'HIGH' TO THREAT-LEVEL
           ELSE IF UNIT-COUNT > 50
               MOVE 'MEDIUM' TO THREAT-LEVEL
           ELSE
               MOVE 'LOW' TO THREAT-LEVEL.

       CALCULATE-POWER.
           COMPUTE COMBAT-POWER = UNIT-COUNT * 10.

       DETERMINE-ACTION.
           IF COMBAT-POWER > 1000
               DISPLAY 'ACTION: ATTACK'
           ELSE IF COMBAT-POWER > 500
               DISPLAY 'ACTION: DEFEND'
           ELSE
               DISPLAY 'ACTION: EXPAND'.

       EXECUTE-ORDERS.
           ADD 10 TO MINERALS
           ADD 1 TO SUPPLY.
