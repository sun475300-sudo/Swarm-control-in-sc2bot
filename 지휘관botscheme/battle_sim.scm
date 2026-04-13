;; Wicked Zerg - Battle Simulation
;; Phase 126: Scheme

(define (battle-sim units)
  (foldl (lambda (unit acc) (+ acc 5)) 0 units))

(define (calculate-swarm-damage count)
  (* count 5))

(define (swarm-formation center-x center-y count radius)
  (let ((angle-step (* 2 pi (/ 1 count))))
    (map (lambda (i)
           (let ((angle (* angle-step i)))
             (cons (+ center-x (* radius (cos angle)))
                   (+ center-y (* radius (sin angle))))))
         (iota count))))

(define (unit-strength health damage armor)
  (let ((effective (* damage (/ health 100))))
    (* effective (- 1 (* armor 0.01)))))

(define (battle-outcome attackers defenders)
  (let ((attack-power (foldl + 0 (map unit-strength attackers)))
        (defense-power (foldl + 0 (map unit-strength defenders))))
    (> attack-power defense-power)))

(define (calculate-threats our-positions enemy-positions)
  (let ((distances (map (lambda (p)
                          (apply min (map (lambda (e)
                                           (sqrt (+ (expt (- (car p) (car e)) 2)
                                                   (expt (- (cdr p) (cdr e)) 2))))
                                         enemy-positions)))
                        our-positions)))
    (count (lambda (d) (< d 10)) distances)))
