;;; Phase 522: Scheme Advanced (Guile/Chicken)
;;; SC2 Bot Game Engine using Scheme continuations & SRFI

;; ─────────────────────────────────────────────
;; Call/cc based coroutine system
;; ─────────────────────────────────────────────

(define *tasks* '())
(define *current-cont* #f)

(define (spawn-task thunk)
  (set! *tasks* (append *tasks* (list thunk))))

(define (yield)
  (call-with-current-continuation
   (lambda (k)
     (set! *tasks* (append *tasks* (list (lambda () (k #f)))))
     (run-next-task))))

(define (run-next-task)
  (if (null? *tasks*)
      (display "All tasks complete\n")
      (let ([task (car *tasks*)])
        (set! *tasks* (cdr *tasks*))
        (task))))

(define (run-scheduler)
  (run-next-task))

;; ─────────────────────────────────────────────
;; Association list based game state
;; ─────────────────────────────────────────────

(define (make-game-state)
  (list
   (cons 'minerals 50)
   (cons 'gas 0)
   (cons 'supply 12)
   (cons 'max-supply 14)
   (cons 'workers 12)
   (cons 'frame 0)
   (cons 'units '())
   (cons 'buildings '(hatchery))
   (cons 'enemy-units '())))

(define (state-get state key)
  (cdr (assq key state)))

(define (state-set state key val)
  (cons (cons key val)
        (filter (lambda (pair) (not (eq? (car pair) key)))
                state)))

(define (state-update state key f)
  (state-set state key (f (state-get state key))))

;; ─────────────────────────────────────────────
;; Build order interpreter
;; ─────────────────────────────────────────────

(define *build-queue* '())

(define (enqueue-build item)
  (set! *build-queue* (append *build-queue* (list item))))

(define (process-build-queue! state)
  (if (null? *build-queue*)
      state
      (let* ([item (car *build-queue*)]
             [cost (unit-cost item)]
             [min (car cost)]
             [gas (cdr cost)])
        (if (and (>= (state-get state 'minerals) min)
                 (>= (state-get state 'gas) gas))
            (begin
              (set! *build-queue* (cdr *build-queue*))
              (-> state
                  (state-update 'minerals (lambda (m) (- m min)))
                  (state-update 'gas (lambda (g) (- g gas)))
                  (state-update 'units (lambda (us) (cons item us)))))
            state))))

(define (unit-cost unit)
  (case unit
    [(drone)     (cons 50 0)]
    [(zergling)  (cons 25 0)]
    [(roach)     (cons 75 25)]
    [(hydralisk) (cons 100 50)]
    [(mutalisk)  (cons 100 100)]
    [else        (cons 0 0)]))

;; ─────────────────────────────────────────────
;; Threading macro (->)
;; ─────────────────────────────────────────────

(define-syntax ->
  (syntax-rules ()
    [(_ x) x]
    [(_ x (f arg ...) rest ...)
     (-> (f x arg ...) rest ...)]))

;; ─────────────────────────────────────────────
;; Economy simulation
;; ─────────────────────────────────────────────

(define (tick-economy state)
  (let* ([workers (state-get state 'workers)]
         [mineral-income (inexact->exact (floor (* workers 0.7 8)))]
         [new-state (state-update state 'minerals
                                  (lambda (m) (+ m mineral-income)))])
    (state-update new-state 'frame
                  (lambda (f) (+ f 1)))))

(define (run-simulation state rounds)
  (let loop ([s state] [n rounds])
    (if (= n 0)
        s
        (let* ([s1 (tick-economy s)]
               [s2 (process-build-queue! s1)])
          (loop s2 (- n 1))))))

;; ─────────────────────────────────────────────
;; Decision engine
;; ─────────────────────────────────────────────

(define (decide-action state)
  (let ([minerals (state-get state 'minerals)]
        [workers  (state-get state 'workers)]
        [supply   (state-get state 'supply)])
    (cond
      [(< workers 16) 'train-drone]
      [(> minerals 300) 'expand]
      [(> minerals 100) 'train-zergling]
      [else 'wait])))

;; ─────────────────────────────────────────────
;; Main
;; ─────────────────────────────────────────────

(define (main)
  (display "Phase 522: Scheme Advanced\n")
  (let ([state (make-game-state)])
    (enqueue-build 'drone)
    (enqueue-build 'drone)
    (enqueue-build 'zergling)
    (enqueue-build 'zergling)
    (enqueue-build 'roach)
    (let ([final (run-simulation state 100)])
      (display (string-append
                "Final minerals: "
                (number->string (state-get final 'minerals))
                "\n"))
      (display (string-append
                "Units: "
                (with-output-to-string
                  (lambda () (write (state-get final 'units))))
                "\n")))))

(main)
