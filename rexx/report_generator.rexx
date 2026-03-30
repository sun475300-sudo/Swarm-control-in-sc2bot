/* report_generator.rexx                                               */
/* REXX report generator for Zerg bot battle statistics                */
/* Phase 132 - parses bot.log, computes win rates, formats ASCII table */
/* Classic REXX style: stems for associative arrays, SAY for output    */

/* ------------------------------------------------------------------- */
/* Main program                                                         */
/* ------------------------------------------------------------------- */
SIGNAL ON NOTREADY NAME log_not_found

logFile = 'bot.log'

/* Associative stems for per-matchup stats */
/* matchups.(race).wins, matchups.(race).losses, matchups.(race).draws */
matchups.ZvZ.wins   = 0 ; matchups.ZvZ.losses   = 0 ; matchups.ZvZ.draws   = 0
matchups.ZvT.wins   = 0 ; matchups.ZvT.losses   = 0 ; matchups.ZvT.draws   = 0
matchups.ZvP.wins   = 0 ; matchups.ZvP.losses   = 0 ; matchups.ZvP.draws   = 0
matchups.ZvR.wins   = 0 ; matchups.ZvR.losses   = 0 ; matchups.ZvR.draws   = 0  /* Random */
totalGames = 0

/* ------------------------------------------------------------------- */
/* Parse bot.log line by line                                           */
/* Expected log format:                                                 */
/*   [RESULT] ZvT WIN  duration=12m34s map=Equilibrium                 */
/*   [RESULT] ZvP LOSS duration=8m05s  map=Goldenaura                  */
/* ------------------------------------------------------------------- */
DO WHILE LINES(logFile) > 0
    line = LINEIN(logFile)
    IF POS('[RESULT]', line) = 0 THEN ITERATE   /* skip non-result lines */

    /* Extract matchup token (ZvT, ZvP, ZvZ, ZvR) */
    mu = extractToken(line, 2)  /* second word after [RESULT] */
    IF mu = '' THEN ITERATE

    /* Validate matchup is one we track */
    IF mu \= 'ZvZ' & mu \= 'ZvT' & mu \= 'ZvP' & mu \= 'ZvR' THEN ITERATE

    /* Extract result token: WIN / LOSS / DRAW */
    res = extractToken(line, 3)

    SELECT
        WHEN res = 'WIN'  THEN matchups.mu.wins   = matchups.mu.wins   + 1
        WHEN res = 'LOSS' THEN matchups.mu.losses = matchups.mu.losses + 1
        WHEN res = 'DRAW' THEN matchups.mu.draws  = matchups.mu.draws  + 1
        OTHERWISE NOP
    END
    totalGames = totalGames + 1
END
CALL STREAM logFile, 'C', 'CLOSE'

/* ------------------------------------------------------------------- */
/* Print ASCII table report                                             */
/* ------------------------------------------------------------------- */
SAY ''
SAY '╔══════════════════════════════════════════════════════════╗'
SAY '║          JARVIS ZERG BOT - BATTLE STATISTICS REPORT      ║'
SAY '╠══════════╦═══════╦════════╦═══════╦═════════╦═══════════╣'
SAY '║ Matchup  ║  Wins ║ Losses ║ Draws ║  Games  ║  Win Rate ║'
SAY '╠══════════╬═══════╬════════╬═══════╬═════════╬═══════════╣'

races. = 'ZvZ ZvT ZvP ZvR'
DO i = 1 TO WORDS(races.)
    mu = WORD(races., i)
    w  = matchups.mu.wins
    l  = matchups.mu.losses
    d  = matchups.mu.draws
    g  = w + l + d
    IF g > 0 THEN
        wr = FORMAT(w / g * 100, 3, 1) || '%'
    ELSE
        wr = '  N/A '
    SAY '║' LEFT(mu, 9) '║' RIGHT(w, 6) '║' RIGHT(l, 7) '║',
        RIGHT(d, 6) '║' RIGHT(g, 8) '║' RIGHT(wr, 10) '║'
END

SAY '╠══════════╬═══════╬════════╬═══════╬═════════╬═══════════╣'
/* Overall totals */
totW = matchups.ZvZ.wins + matchups.ZvT.wins + matchups.ZvP.wins + matchups.ZvR.wins
totL = matchups.ZvZ.losses + matchups.ZvT.losses + matchups.ZvP.losses + matchups.ZvR.losses
totD = matchups.ZvZ.draws + matchups.ZvT.draws + matchups.ZvP.draws + matchups.ZvR.draws
IF totalGames > 0 THEN
    totWR = FORMAT(totW / totalGames * 100, 3, 1) || '%'
ELSE
    totWR = '  N/A '
SAY '║  TOTAL   ║' RIGHT(totW,6) '║' RIGHT(totL,7) '║',
    RIGHT(totD,6) '║' RIGHT(totalGames,8) '║' RIGHT(totWR,10) '║'
SAY '╚══════════╩═══════╩════════╩═══════╩═════════╩═══════════╝'
SAY ''
SAY 'Report generated:' DATE() TIME()
EXIT 0

/* ------------------------------------------------------------------- */
/* Subroutine: extractToken(line, n)                                    */
/* Returns the Nth whitespace-delimited word in 'line'                  */
/* Skips the leading '[RESULT]' tag (counted as word 1)                 */
/* ------------------------------------------------------------------- */
extractToken: PROCEDURE
    PARSE ARG line, n
    /* Strip bracketed tag and return Nth remaining word */
    cleaned = STRIP(line)
    RETURN WORD(cleaned, n + 1)  /* +1 because [RESULT] is word 1 */

/* ------------------------------------------------------------------- */
/* Error handler: log file not found                                    */
/* ------------------------------------------------------------------- */
log_not_found:
    SAY 'WARNING: bot.log not found. Showing empty report.'
    SIGNAL RESUME  /* attempt to continue with zero stats */
