#lang racket

;;; Phase 521: Racket Advanced
;;; SC2 Bot Strategy DSL using Racket macros

(require racket/match
         racket/list
         racket/string)

;; ─────────────────────────────────────────────
;; Strategy DSL Macros
;; ─────────────────────────────────────────────

(define-syntax-rule (define-strategy name
                      #:race race
                      #:opener opener
                      #:transitions transitions
                      #:win-condition win)
  (define name
    (strategy race opener transitions win)))

(define-syntax-rule (when-supply supply body ...)
  (λ (state)
    (when (>= (game-state-supply state) supply)
      body ...)))

(define-syntax-rule (on-minerals amount body ...)
  (λ (state)
    (when (>= (game-state-minerals state) amount)
      body ...)))

(define-syntax build-order
  (syntax-rules (->)
    [(_ (supply -> action) ...)
     (list (cons supply (λ () action)) ...)]))

;; ─────────────────────────────────────────────
;; Game State
;; ─────────────────────────────────────────────

(struct game-state
  (supply minerals gas workers
   hatcheries queens units
   enemy-race frame)
  #:transparent)

(struct strategy
  (race opener transitions win-condition)
  #:transparent)

;; ─────────────────────────────────────────────
;; Strategy Definitions
;; ─────────────────────────────────────────────

(define-strategy zerg-ling-flood
  #:race 'zerg
  #:opener '(pool-first hatch-gas)
  #:transitions
  (build-order
   (13 -> 'spawning-pool)
   (16 -> 'zergling-speed)
   (20 -> 'expand))
  #:win-condition 'ling-run-by)

(define-strategy roach-ravager-push
  #:race 'zerg
  #:opener '(hatch-first)
  #:transitions
  (build-order
   (17 -> 'spawning-pool)
   (22 -> 'roach-warren)
   (28 -> 'push))
  #:win-condition 'ravager-push)

;; ─────────────────────────────────────────────
;; Pattern Matching on Game State
;; ─────────────────────────────────────────────

(define (choose-strategy state)
  (match state
    [(game-state s m _ w _ _ _ 'terran _)
     #:when (< s 50)
     zerg-ling-flood]
    [(game-state s _ _ _ h _ _ 'protoss _)
     #:when (>= h 2)
     roach-ravager-push]
    [_
     roach-ravager-push]))

;; ─────────────────────────────────────────────
;; Continuation-based Game Loop
;; ─────────────────────────────────────────────

(define (run-bot initial-state)
  (let loop ([state initial-state]
             [strategy (choose-strategy initial-state)])
    (define action (execute-strategy strategy state))
    (define new-state (apply-action state action))
    (if (game-over? new-state)
        (report-result new-state)
        (loop new-state
              (adapt-strategy strategy new-state)))))

(define (execute-strategy strat state)
  (let* ([opener (strategy-opener strat)]
         [transitions (strategy-transitions strat)])
    (or (find-applicable-transition transitions state)
        (default-action state))))

(define (find-applicable-transition transitions state)
  (for/first ([t (in-list transitions)]
              #:when ((cdr t) state))
    (car t)))

(define (default-action state)
  (cond
    [(< (game-state-workers state) 66) 'train-drone]
    [(can-build-unit? state 'zergling) 'train-zergling]
    [else 'wait]))

;; ─────────────────────────────────────────────
;; Utility: Higher-Order Strategy Combinators
;; ─────────────────────────────────────────────

(define (strategy-or . strategies)
  (λ (state)
    (for/first ([s (in-list strategies)]
                #:when (strategy-applicable? s state))
      s)))

(define (strategy-sequence . steps)
  (λ (state)
    (foldl (λ (step acc) (step acc)) state steps)))

(define (adaptive-strategy base-strategy opponent-info)
  (λ (state)
    (if (detected-early-aggression? opponent-info state)
        (defensive-pivot state)
        (base-strategy state))))

;; ─────────────────────────────────────────────
;; Stubs
;; ─────────────────────────────────────────────

(define (apply-action state action) state)
(define (game-over? state) #f)
(define (report-result state) (displayln "Game over"))
(define (adapt-strategy s _) s)
(define (can-build-unit? s u) #t)
(define (strategy-applicable? s st) #t)
(define (detected-early-aggression? info state) #f)
(define (defensive-pivot state) 'defend)

;; ─────────────────────────────────────────────
;; Main Entry Point
;; ─────────────────────────────────────────────

(module+ main
  (displayln "Phase 521: Racket Advanced — Strategy Macro DSL")
  (let ([state (game-state 12 50 0 12 1 1 '() 'terran 0)])
    (define strat (choose-strategy state))
    (printf "Selected strategy: ~a~n" (strategy-win-condition strat))))
