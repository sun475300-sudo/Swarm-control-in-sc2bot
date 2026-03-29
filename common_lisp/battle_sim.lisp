;; Wicked Zerg - Battle Simulation
;; Phase 127: Common Lisp

(defun battle-sim (units)
  (reduce #'+ (mapcar (lambda (u) 5) units)))

(defun calculate-swarm-damage (count)
  (* count 5))

(defun swarm-formation (center-x center-y count radius)
  (loop for i from 0 to (1- count)
        for angle = (* 2 pi (/ i count))
        collect (cons (+ center-x (* radius (cos angle)))
                      (+ center-y (* radius (sin angle))))))

(defun unit-strength (health damage armor)
  (let ((effective (* damage (/ health 100))))
    (* effective (- 1 (* armor 0.01)))))

(defun battle-outcome (attackers defenders)
  (let ((attack-power (reduce #'+ (mapcar #'unit-strength attackers)))
        (defense-power (reduce #'+ (mapcar #'unit-strength defenders))))
    (> attack-power defense-power)))

(defun calculate-threats (our-positions enemy-positions)
  (count-if (lambda (d) (< d 10))
            (mapcar (lambda (p)
                      (apply #'min
                             (mapcar (lambda (e)
                                       (sqrt (+ (expt (- (car p) (car e)) 2)
                                               (expt (- (cdr p) (cdr e)) 2))))
                                     enemy-positions)))
                    our-positions)))
