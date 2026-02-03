; ============================================================
; Problem:  ODRL-DNT-001
; Family:   ODRL-DNT (Deontic Conflicts)
; Status:   sat
; Logic:    QF_LRA
; Source:   ODRL-SA Benchmark Suite
; Authors:  Daham Mustafa (Fraunhofer FIT & RWTH Aachen)
; Date:     2026-02-03
; ============================================================
;
; Description:
;   A policy permits printing at resolution <= 300 DPI and
;   prohibits printing at resolution >= 150 DPI.
;   Both rules are individually consistent, but their
;   conjunction is satisfiable — meaning there exist
;   resolutions (150 to 300) where printing is simultaneously
;   permitted and forbidden: a deontic conflict.
;
; ODRL Source:
;   Permission(print, resolution lteq 300 DPI)
;   Prohibition(print, resolution gteq 150 DPI)
;
; Deontic Interpretation:
;   sat    → DEONTIC-CONFLICT (witness identifies conflict zone)
;   unsat  → NO-CONFLICT
;
; SZS Status: Satisfiable
; ============================================================

(set-logic QF_LRA)

; Left operand variable: resolution (DPI)
(declare-const resolution Real)

; Domain bound: resolution > 0 (ODRL spec: positive real)
(assert (> resolution 0))

; Permission constraint: resolution <= 300
(assert (<= resolution 300))

; Prohibition constraint: resolution >= 150
(assert (>= resolution 150))

(check-sat)
(get-model)
(exit)
