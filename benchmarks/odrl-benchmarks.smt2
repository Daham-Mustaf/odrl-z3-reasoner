; ============================================================
; ODRL-SA Benchmark Suite for TPTP / SMT-LIB
; Family: ODRL-BND (Bounded Domain Constraint Conflicts)
; ============================================================

; ============================================================
; Problem ODRL-BND-001: SAT (No Conflict)
; Status: sat
; Description: Two percentage constraints with overlapping ranges
; Source: ODRL Core - percentage LeftOperand
; ============================================================
; Permission: use asset if percentage <= 80
; Permission: use asset if percentage >= 30
; Expected: sat (overlap at [30, 80])

(set-logic QF_LRA)
(set-info :source |ODRL-SA Benchmark Suite - Fraunhofer FIT & RWTH Aachen|)
(set-info :category "crafted")
(set-info :status sat)
(set-info :smt-lib-version 2.6)
(set-info :description "Two percentage constraints with overlapping ranges. No conflict.")

(declare-const percentage Real)

; Domain bounds (ODRL spec: "MUST be xsd:decimal from 0 to 100")
(assert (>= percentage 0))
(assert (<= percentage 100))

; Constraint 1: percentage <= 80
(assert (<= percentage 80))

; Constraint 2: percentage >= 30
(assert (>= percentage 30))

(check-sat)
; Expected: sat
; Witness: percentage = 50
(get-model)
(exit)


; ============================================================
; Problem ODRL-BND-002: UNSAT (Internal Conflict)
; Status: unsat
; Description: Two percentage constraints with empty intersection
; Source: ODRL Core - percentage LeftOperand
; ============================================================
; Rule: use asset if percentage <= 20 AND percentage >= 60
; Expected: unsat (no value in [0,100] satisfies both)

(set-logic QF_LRA)
(set-info :source |ODRL-SA Benchmark Suite - Fraunhofer FIT & RWTH Aachen|)
(set-info :category "crafted")
(set-info :status unsat)

(declare-const percentage Real)

; Domain
(assert (>= percentage 0))
(assert (<= percentage 100))

; Constraint 1: percentage <= 20
(assert (<= percentage 20))

; Constraint 2: percentage >= 60
(assert (>= percentage 60))

(check-sat)
; Expected: unsat
(exit)


; ============================================================
; Problem ODRL-DNT-001: SAT (Deontic Conflict)
; Status: sat
; Description: Permission and prohibition overlap on resolution
; Source: ODRL Core - resolution LeftOperand
; ============================================================
; Permission: print if resolution <= 300 DPI
; Prohibition: do not print if resolution >= 150 DPI
; Expected: sat (conflict zone [150, 300])

(set-logic QF_LRA)
(set-info :source |ODRL-SA Benchmark Suite - Fraunhofer FIT & RWTH Aachen|)
(set-info :category "crafted")
(set-info :status sat)
(set-info :description "Deontic conflict: permission and prohibition overlap on resolution.")

(declare-const resolution Real)

; Domain (ODRL spec: resolution > 0)
(assert (> resolution 0))

; Permission formula: resolution <= 300
(assert (<= resolution 300))

; Prohibition formula: resolution >= 150
(assert (>= resolution 150))

(check-sat)
; Expected: sat
; Witness: resolution = 200 (both permitted and forbidden)
(get-model)
(exit)


; ============================================================
; Problem ODRL-DNT-002: UNSAT (No Deontic Conflict)
; Status: unsat
; Description: Permission and prohibition on disjoint ranges
; Source: ODRL Core - resolution LeftOperand
; ============================================================
; Permission: print if resolution <= 100 DPI
; Prohibition: do not print if resolution >= 300 DPI
; Expected: unsat (ranges don't overlap, no deontic conflict)

(set-logic QF_LRA)
(set-info :source |ODRL-SA Benchmark Suite - Fraunhofer FIT & RWTH Aachen|)
(set-info :category "crafted")
(set-info :status unsat)
(set-info :description "No deontic conflict: permission and prohibition on disjoint ranges.")

(declare-const resolution Real)

; Domain
(assert (> resolution 0))

; Permission formula: resolution <= 100
(assert (<= resolution 100))

; Prohibition formula: resolution >= 300
(assert (>= resolution 300))

(check-sat)
; Expected: unsat
(exit)


; ============================================================
; Problem ODRL-UNT-001: SAT (Unit-Dependent Deontic Conflict)
; Status: sat
; Description: payAmount constraints with same unit (EUR)
; Source: ODRL Core - payAmount LeftOperand
; ============================================================
; Permission: use if payAmount <= 500 EUR
; Prohibition: do not use if payAmount <= 200 EUR
; Expected: sat (conflict at [0, 200])

(set-logic QF_LRA)
(set-info :source |ODRL-SA Benchmark Suite - Fraunhofer FIT & RWTH Aachen|)
(set-info :category "crafted")
(set-info :status sat)
(set-info :description "Unit-dependent deontic conflict on payAmount (EUR).")

(declare-const payAmount_EUR Real)

; Domain (ODRL spec: "MUST be xsd:decimal", non-negative)
(assert (>= payAmount_EUR 0))

; Permission: payAmount <= 500
(assert (<= payAmount_EUR 500))

; Prohibition: payAmount <= 200
(assert (<= payAmount_EUR 200))

(check-sat)
; Expected: sat
; Witness: payAmount_EUR = 100 (both permitted and forbidden)
(get-model)
(exit)


; ============================================================
; Problem ODRL-UNT-002: UNSAT (Unit Mismatch → Separate Vars)
; Status: sat
; Description: payAmount with different units creates independent vars
; Source: ODRL Core - payAmount LeftOperand with unit
; Note: Different units → different Z3 variables → always sat
;       ODRL-SA reports UNKNOWN for unit mismatch, but the
;       encoding itself is trivially satisfiable
; ============================================================

(set-logic QF_LRA)
(set-info :source |ODRL-SA Benchmark Suite - Fraunhofer FIT & RWTH Aachen|)
(set-info :category "crafted")
(set-info :status sat)
(set-info :description "Different units (EUR vs USD) produce independent variables.")

(declare-const payAmount_EUR Real)
(declare-const payAmount_USD Real)

; Domains
(assert (>= payAmount_EUR 0))
(assert (>= payAmount_USD 0))

; Constraint 1: payAmount >= 100 EUR
(assert (>= payAmount_EUR 100))

; Constraint 2: payAmount <= 50 USD
(assert (<= payAmount_USD 50))

; These are independent — always sat
(check-sat)
; Expected: sat (trivially — different variables)
; ODRL-SA judgment: UNKNOWN (units not comparable)
(get-model)
(exit)


; ============================================================
; Problem ODRL-MIX-001: SAT (Multi-Constraint Deontic Conflict)
; Status: sat
; Description: Permission and prohibition with multiple LeftOperands
; Source: ODRL Core - count + dateTime
; ============================================================
; Permission: use if count <= 100 AND dateTime <= 2025-12-31
; Prohibition: do not use if count >= 20 AND dateTime >= 2025-01-01
; Expected: sat (overlap exists)

(set-logic QF_LIA)
(set-info :source |ODRL-SA Benchmark Suite - Fraunhofer FIT & RWTH Aachen|)
(set-info :category "crafted")
(set-info :status sat)
(set-info :description "Multi-constraint deontic conflict across count and dateTime.")

(declare-const count Int)
(declare-const dateTime Int)  ; Unix timestamp

; Domain bounds
(assert (>= count 0))

; Permission: count <= 100 AND dateTime <= 1735689599 (2025-12-31)
(assert (<= count 100))
(assert (<= dateTime 1735689599))

; Prohibition: count >= 20 AND dateTime >= 1704067200 (2025-01-01)
(assert (>= count 20))
(assert (>= dateTime 1704067200))

(check-sat)
; Expected: sat
; Witness: count = 50, dateTime = 1719792000 (2025-07-01)
(get-model)
(exit)


; ============================================================
; Problem ODRL-INH-001: UNSAT (Valid Inheritance)
; Status: unsat
; Description: Child is valid restriction of parent
; Source: ODRL inheritance semantics
; ============================================================
; Parent: permission if count <= 100
; Child:  permission if count <= 50
; Check:  child ∧ ¬parent → should be unsat (child ⊆ parent)

(set-logic QF_LIA)
(set-info :source |ODRL-SA Benchmark Suite - Fraunhofer FIT & RWTH Aachen|)
(set-info :category "crafted")
(set-info :status unsat)
(set-info :description "Valid inheritance: child (count <= 50) refines parent (count <= 100).")

(declare-const count Int)

; Domain
(assert (>= count 0))

; Child constraint: count <= 50
(assert (<= count 50))

; Negation of parent: NOT (count <= 100) = count > 100
(assert (> count 100))

(check-sat)
; Expected: unsat (child is valid refinement)
(exit)


; ============================================================
; Problem ODRL-INH-002: SAT (Invalid Inheritance)
; Status: sat
; Description: Child violates parent restriction
; Source: ODRL inheritance semantics
; ============================================================
; Parent: permission if count <= 50
; Child:  permission if count <= 200
; Check:  child ∧ ¬parent → sat means child exceeds parent

(set-logic QF_LIA)
(set-info :source |ODRL-SA Benchmark Suite - Fraunhofer FIT & RWTH Aachen|)
(set-info :category "crafted")
(set-info :status sat)
(set-info :description "Invalid inheritance: child (count <= 200) exceeds parent (count <= 50).")

(declare-const count Int)

; Domain
(assert (>= count 0))

; Child constraint: count <= 200
(assert (<= count 200))

; Negation of parent: NOT (count <= 50) = count > 50
(assert (> count 50))

(check-sat)
; Expected: sat
; Witness: count = 100 (child allows what parent forbids)
(get-model)
(exit)
