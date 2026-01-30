# ============================================================================
# MOTIVATING EXAMPLES FOR ODRL-SA PAPER
# Real-World Policy Conflict Scenarios in Data Spaces
# ============================================================================
#
# These examples demonstrate why static analysis of ODRL policies is essential
# for reliable data exchange in federated environments like GAIA-X, IDS, and
# research data infrastructures.
#
# ============================================================================

"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                    MOTIVATION: WHY STATIC POLICY ANALYSIS?                   ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  In federated data spaces, policies are:                                     ║
║    • Written by different stakeholders (data providers, consumers, admins)   ║
║    • Combined dynamically at runtime                                         ║
║    • Inherited across organizational hierarchies                             ║
║    • Subject to regulatory compliance requirements                           ║
║                                                                              ║
║  Without static analysis, conflicts are discovered only at RUNTIME:          ║
║    → Data access failures                                                    ║
║    → Compliance violations                                                   ║
║    → User frustration                                                        ║
║    → Legal liability                                                         ║
║                                                                              ║
║  ODRL-SA enables DESIGN-TIME conflict detection:                             ║
║    → Catch errors before deployment                                          ║
║    → Ensure policy consistency                                               ║
║    → Verify regulatory compliance                                            ║
║    → Build trust in data ecosystems                                          ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝


════════════════════════════════════════════════════════════════════════════════
SECTION 1: INTERNAL CONSTRAINT CONFLICTS
════════════════════════════════════════════════════════════════════════════════

These occur when constraints within a SINGLE rule are mutually unsatisfiable.

────────────────────────────────────────────────────────────────────────────────
Example 1.1: Scientific Dataset Access - Impossible Time Window
────────────────────────────────────────────────────────────────────────────────

SCENARIO:
A research institution wants to allow access to climate data, but the policy
author made an error specifying the access window.

POLICY (Natural Language):
"Researchers may access the climate dataset for analysis, but only during
the embargo period (before January 2024) AND only after peer review
completion (after June 2024)."

POLICY (Formal):
    Permission:
        action: analyze
        target: ClimateDataset2023
        constraints:
            dateTime ≤ 2024-01-01  (before embargo ends)
            AND
            dateTime ≥ 2024-06-01  (after peer review)

CONFLICT ANALYSIS:
    α(dateTime ≤ 2024-01-01) = (-∞, 1704067200]
    α(dateTime ≥ 2024-06-01) = [1717200000, +∞)
    
    Meet: (-∞, 1704067200] ∩ [1717200000, +∞) = ∅
    
    JUDGMENT: CONFLICT
    
EXPLANATION:
No timestamp can simultaneously be before January 2024 AND after June 2024.
The policy author likely meant OR instead of AND, or made a date error.

REAL-WORLD IMPACT:
Without static analysis, researchers would receive cryptic "access denied"
errors with no explanation of why the policy is self-contradictory.


────────────────────────────────────────────────────────────────────────────────
Example 1.2: Media Licensing - Contradictory Quality Requirements
────────────────────────────────────────────────────────────────────────────────

SCENARIO:
A stock photo agency offers tiered licensing. A policy author accidentally
creates an impossible quality tier.

POLICY (Natural Language):
"The Standard License permits printing images at high resolution (at least
600 DPI) but restricts output to low resolution (at most 300 DPI)."

POLICY (Formal):
    Permission:
        action: print
        target: StockPhoto_12345
        constraints:
            resolution ≥ 600 DPI  (high quality required)
            AND
            resolution ≤ 300 DPI  (low quality limit)

CONFLICT ANALYSIS:
    α(resolution ≥ 600) = [600, +∞)
    α(resolution ≤ 300) = (0, 300]
    
    Meet: [600, +∞) ∩ (0, 300] = ∅
    
    JUDGMENT: CONFLICT 

EXPLANATION:
No resolution value can be simultaneously ≥600 AND ≤300.
This license tier is unsatisfiable - no valid use exists.

REAL-WORLD IMPACT:
Customers who purchase this license cannot legally use the image at ANY
resolution. This creates legal liability and customer complaints.


────────────────────────────────────────────────────────────────────────────────
Example 1.3: Data Monetization - Impossible Payment Range
────────────────────────────────────────────────────────────────────────────────

SCENARIO:
A data marketplace allows access to IoT sensor data with usage-based pricing.
The pricing policy contains a configuration error.

POLICY (Natural Language):
"Access is granted for payments of exactly €50, €100, or €200, but the
payment must also be at least €500 for premium data access."

POLICY (Formal):
    Permission:
        action: use
        target: IoTSensorStream
        constraints:
            payAmount isAnyOf {50, 100, 200} EUR
            AND
            payAmount ≥ 500 EUR

CONFLICT ANALYSIS:
    α(payAmount isAnyOf {50, 100, 200}) = {50, 100, 200}
    α(payAmount ≥ 500) = [500, +∞)
    
    Meet: {50, 100, 200} ∩ [500, +∞) = ∅
    
    JUDGMENT: CONFLICT

EXPLANATION:
The discrete payment options (50, 100, 200) have no intersection with
the minimum requirement (≥500). No valid payment amount exists.


════════════════════════════════════════════════════════════════════════════════
SECTION 2: DEONTIC CONFLICTS (Permission vs. Prohibition)
════════════════════════════════════════════════════════════════════════════════

These occur when an action is BOTH permitted AND prohibited under overlapping
conditions, creating legal ambiguity.

────────────────────────────────────────────────────────────────────────────────
Example 2.1: Healthcare Data - Conflicting Access Policies
────────────────────────────────────────────────────────────────────────────────

SCENARIO:
A hospital's data governance team creates policies for patient records.
Two team members create overlapping rules without coordination.

POLICY (Natural Language):
"Researchers may access anonymized records for up to 1000 patients."
"Access to more than 500 patient records is prohibited for privacy."

POLICY (Formal):
    Permission:
        action: access
        target: PatientRecords
        constraint: count ≤ 1000
        
    Prohibition:
        action: access
        target: PatientRecords
        constraint: count > 500

DEONTIC ANALYSIS:
    φ_permission = (count ≤ 1000) ∧ (count ≥ 0)  →  count ∈ [0, 1000]
    φ_prohibition = (count > 500) ∧ (count ≥ 0)  →  count ∈ (500, +∞)
    
    Overlap: [0, 1000] ∩ (500, +∞) = (500, 1000]
    
    JUDGMENT: DEONTIC CONFLICT ⚠️
    WITNESS: count = 750

EXPLANATION:
For count values in (500, 1000], the action is SIMULTANEOUSLY:
  • Permitted (because 750 ≤ 1000) ✓
  • Prohibited (because 750 > 500) ✓

This creates legal ambiguity: can a researcher access 750 records or not?

REAL-WORLD IMPACT:
  • Legal uncertainty for researchers
  • Potential GDPR/HIPAA compliance issues
  • Risk of unauthorized data exposure OR unnecessary access denial


────────────────────────────────────────────────────────────────────────────────
Example 2.2: Digital Rights Management - Streaming vs. Download Conflict
────────────────────────────────────────────────────────────────────────────────

SCENARIO:
A video streaming service has policies for content access. The marketing
and legal teams create conflicting policies for a promotional period.

POLICY (Natural Language):
Marketing: "Users may stream content for up to 4 hours per session."
Legal: "Streaming beyond 2 hours is prohibited to limit bandwidth costs."

POLICY (Formal):
    Permission:
        action: stream
        target: PremiumContent
        constraint: elapsedTime ≤ PT4H  (4 hours = 14400 seconds)
        
    Prohibition:
        action: stream
        target: PremiumContent
        constraint: elapsedTime > PT2H  (2 hours = 7200 seconds)

DEONTIC ANALYSIS:
    φ_permission = (elapsed ≤ 14400) ∧ (elapsed > 0)  →  elapsed ∈ (0, 14400]
    φ_prohibition = (elapsed > 7200) ∧ (elapsed > 0)  →  elapsed ∈ (7200, +∞)
    
    Overlap: (0, 14400] ∩ (7200, +∞) = (7200, 14400]
    
    JUDGMENT: DEONTIC CONFLICT ⚠️
    WITNESS: elapsedTime = 10800 (3 hours)

EXPLANATION:
Between 2-4 hours of streaming, users have both permission AND prohibition.
Should the system allow or deny streaming at 3 hours?


────────────────────────────────────────────────────────────────────────────────
Example 2.3: Manufacturing Data - Quality Control Paradox
────────────────────────────────────────────────────────────────────────────────

SCENARIO:
A manufacturing company shares sensor data with partners. Quality assurance
requires high-fidelity data, but security restricts data resolution.

POLICY (Natural Language):
QA Team: "Partners may access sensor readings at 100Hz or higher for analysis."
Security: "External access above 50Hz sampling rate is prohibited."

POLICY (Formal):
    Permission:
        action: analyze
        target: SensorData
        constraint: timeInterval ≤ 10ms  (≥100Hz, i.e., ≤10ms between samples)
        
    Prohibition:
        action: analyze  
        target: SensorData
        constraint: timeInterval ≤ 20ms  (≥50Hz, i.e., ≤20ms between samples)

DEONTIC ANALYSIS:
    φ_permission = (interval ≤ 10)   →  interval ∈ [1, 10]
    φ_prohibition = (interval ≤ 20)  →  interval ∈ [1, 20]
    
    Overlap: [1, 10] ∩ [1, 20] = [1, 10]
    
    JUDGMENT: DEONTIC CONFLICT ⚠️
    WITNESS: timeInterval = 5ms

EXPLANATION:
ALL permitted intervals (≤10ms) are ALSO prohibited (≤20ms).
The permission is completely negated by the prohibition!


════════════════════════════════════════════════════════════════════════════════
SECTION 3: POLICY INHERITANCE CONFLICTS
════════════════════════════════════════════════════════════════════════════════

In organizational hierarchies, child policies must be consistent with parent
policies. Inheritance violations create compliance gaps.

────────────────────────────────────────────────────────────────────────────────
Example 3.1: Corporate Data Governance - Department Override Violation
────────────────────────────────────────────────────────────────────────────────

SCENARIO:
A corporation has enterprise-wide data policies. A department tries to
create more permissive local policies.

PARENT POLICY (Enterprise):
"Company data may be shared externally for up to 100 records per request."

CHILD POLICY (Sales Department):
"Sales data may be shared externally for up to 500 records per request."

FORMAL REPRESENTATION:
    Parent Permission:
        action: share
        target: CompanyData
        constraint: count ≤ 100
        
    Child Permission:
        action: share
        target: SalesData (subclass of CompanyData)
        constraint: count ≤ 500

INHERITANCE ANALYSIS:
    φ_parent = (count ≤ 100) ∧ (count ≥ 0)  →  count ∈ [0, 100]
    φ_child = (count ≤ 500) ∧ (count ≥ 0)   →  count ∈ [0, 500]
    
    Subsumption check: φ_child ⊆ φ_parent?
    
    Counter-model: count = 250
      • φ_child(250) = True  (250 ≤ 500) ✓
      • φ_parent(250) = False (250 > 100) ✗
    
    JUDGMENT: INHERITANCE VIOLATION

EXPLANATION:
The child policy permits sharing 250 records, but the parent policy only
allows up to 100. The child is MORE permissive than allowed.

REAL-WORLD IMPACT:
  • Compliance violation (child exceeds parent authorization)
  • Data leakage risk (500 records shared when only 100 authorized)
  • Audit failure


────────────────────────────────────────────────────────────────────────────────
Example 3.2: Research Consortium - Embargo Period Violation
────────────────────────────────────────────────────────────────────────────────

SCENARIO:
A research consortium has data sharing agreements. A member institution
tries to allow earlier access than permitted.

PARENT POLICY (Consortium):
"Research data may be accessed only after the embargo date (2025-01-01)."

CHILD POLICY (Member Institution):
"Our researchers may access consortium data after 2024-06-01."

FORMAL REPRESENTATION:
    Parent Permission:
        action: access
        target: ConsortiumData
        constraint: dateTime ≥ 2025-01-01
        
    Child Permission:
        action: access
        target: ConsortiumData
        constraint: dateTime ≥ 2024-06-01

INHERITANCE ANALYSIS:
    φ_parent = (dateTime ≥ 1735689600)  →  [2025-01-01, +∞)
    φ_child = (dateTime ≥ 1717200000)   →  [2024-06-01, +∞)
    
    Subsumption: φ_child ⊆ φ_parent?
    
    Counter-model: dateTime = 2024-09-15 (1726358400)
      • φ_child(1726358400) = True   (Sept 2024 ≥ June 2024) ✓
      • φ_parent(1726358400) = False (Sept 2024 < Jan 2025) ✗
    
    JUDGMENT: INHERITANCE VIOLATION

EXPLANATION:
The child allows access 6 months before the consortium embargo ends.
This violates the data sharing agreement.


────────────────────────────────────────────────────────────────────────────────
Example 3.3: Valid Inheritance - Proper Restriction
────────────────────────────────────────────────────────────────────────────────

SCENARIO (Correct):
An organization properly restricts access in a child policy.

PARENT POLICY:
"Data may be used for up to 1000 operations."

CHILD POLICY:
"Sensitive data may be used for up to 500 operations."

FORMAL REPRESENTATION:
    Parent: count ≤ 1000  →  [0, 1000]
    Child:  count ≤ 500   →  [0, 500]
    
    Subsumption: [0, 500] ⊆ [0, 1000]? YES ✓
    
    JUDGMENT: VALID INHERITANCE ✓

EXPLANATION:
The child is MORE restrictive than the parent, which is always safe.
Any action permitted by the child is also permitted by the parent.


════════════════════════════════════════════════════════════════════════════════
SECTION 4: TAUTOLOGIES AND REDUNDANCIES
════════════════════════════════════════════════════════════════════════════════

These indicate policy quality issues that don't cause failures but suggest
errors or inefficiencies.

────────────────────────────────────────────────────────────────────────────────
Example 4.1: Tautology - Always-True Constraint (Useless)
────────────────────────────────────────────────────────────────────────────────

SCENARIO:
A policy author adds a constraint that provides no actual restriction.

POLICY:
"Users may access data if the usage percentage is at least 0%."

FORMAL:
    Permission:
        action: access
        constraint: percentage ≥ 0

ANALYSIS:
    Domain: percentage ∈ [0, 100]
    Constraint: percentage ≥ 0
    
    Effective constraint: [0, 100] ∩ [0, +∞) = [0, 100] = Domain
    
    JUDGMENT: TAUTOLOGY ⚠️

EXPLANATION:
Since percentage is always ≥ 0 by definition, this constraint adds nothing.
It may indicate the author meant something else (e.g., percentage ≥ 50).


────────────────────────────────────────────────────────────────────────────────
Example 4.2: Redundancy - Duplicate Constraints
────────────────────────────────────────────────────────────────────────────────

SCENARIO:
Multiple constraints that effectively say the same thing.

POLICY:
"Access is permitted if count ≤ 100 AND count ≤ 100."

FORMAL:
    Permission:
        action: access
        constraints:
            count ≤ 100
            AND
            count ≤ 100

ANALYSIS:
    α(count ≤ 100) = [0, 100]
    α(count ≤ 100) = [0, 100]
    
    Meet: [0, 100] ∩ [0, 100] = [0, 100]
    
    JUDGMENT: REDUNDANT ⚠️

EXPLANATION:
The second constraint adds no additional restriction. This may indicate
a copy-paste error or incomplete policy modification.


────────────────────────────────────────────────────────────────────────────────
Example 4.3: Subsumption Redundancy - Stricter Constraint Dominates
────────────────────────────────────────────────────────────────────────────────

SCENARIO:
One constraint is strictly stronger than another, making the weaker one
irrelevant.

POLICY:
"Access is permitted if count ≤ 50 AND count ≤ 100."

FORMAL:
    Permission:
        action: access
        constraints:
            count ≤ 50
            AND
            count ≤ 100

ANALYSIS:
    α(count ≤ 50) = [0, 50]
    α(count ≤ 100) = [0, 100]
    
    Meet: [0, 50] ∩ [0, 100] = [0, 50]
    
    Observation: [0, 50] ⊂ [0, 100]
    
    JUDGMENT: REDUNDANT (count ≤ 100 is subsumed) ⚠️

EXPLANATION:
Since count ≤ 50 is stricter, the count ≤ 100 constraint never has any
effect. It can be safely removed or indicates an authoring error.


════════════════════════════════════════════════════════════════════════════════
SECTION 5: COMPLEX LOGICAL OPERATOR SCENARIOS
════════════════════════════════════════════════════════════════════════════════

────────────────────────────────────────────────────────────────────────────────
Example 5.1: OR with Both Branches Impossible
────────────────────────────────────────────────────────────────────────────────

SCENARIO:
A policy offers alternatives, but both alternatives are impossible.

POLICY:
"Access is granted if (percentage > 100) OR (percentage < 0)."

FORMAL:
    Permission:
        action: access
        constraint: OR(percentage > 100, percentage < 0)

ANALYSIS:
    Domain: percentage ∈ [0, 100]
    
    α(percentage > 100) = (100, +∞) ∩ [0, 100] = ∅
    α(percentage < 0) = (-∞, 0) ∩ [0, 100] = ∅
    
    OR(∅, ∅) = ∅
    
    JUDGMENT: CONFLICT (Unsatisfiable)

EXPLANATION:
Both OR branches violate domain bounds. No valid access condition exists.


────────────────────────────────────────────────────────────────────────────────
Example 5.2: XONE (Exactly One) - Mutual Exclusion Requirement
────────────────────────────────────────────────────────────────────────────────

SCENARIO:
A licensing model requires exactly one tier to be selected.

POLICY:
"License applies to EXACTLY ONE of: 
  (a) personal use (count ≤ 10), 
  (b) team use (count 11-50), 
  (c) enterprise (count > 50)."

FORMAL:
    Permission:
        action: use
        constraint: XONE(
            count ≤ 10,
            AND(count ≥ 11, count ≤ 50),
            count > 50
        )

ANALYSIS:
    Tier A: [0, 10]
    Tier B: [11, 50]
    Tier C: (50, +∞)
    
    These are mutually exclusive (no overlap).
    For any count value, exactly one tier applies.
    
    JUDGMENT: CONSISTENT ✓ (Well-designed XONE)


────────────────────────────────────────────────────────────────────────────────
Example 5.3: XONE with Overlap - Invalid Tier Design
────────────────────────────────────────────────────────────────────────────────

SCENARIO:
A pricing model has overlapping tiers, breaking the exclusivity requirement.

POLICY:
"Price tier is EXACTLY ONE of:
  (a) basic (≤ €100),
  (b) standard (€50 - €200),
  (c) premium (≥ €150)."

FORMAL:
    constraint: XONE(
        payAmount ≤ 100,
        AND(payAmount ≥ 50, payAmount ≤ 200),
        payAmount ≥ 150
    )

ANALYSIS:
    Tier A: [0, 100]
    Tier B: [50, 200]
    Tier C: [150, +∞)
    
    Overlaps:
      • A ∩ B = [50, 100] (€75 matches BOTH basic AND standard)
      • B ∩ C = [150, 200] (€175 matches BOTH standard AND premium)
    
    XONE requires exactly one, but overlaps allow multiple.
    
    For payAmount = 75:
      • Tier A: 75 ≤ 100 ✓
      • Tier B: 50 ≤ 75 ≤ 200 ✓
      • Tier C: 75 ≥ 150 ✗
      
    TWO tiers match, violating XONE!
    
    JUDGMENT: XONE VIOLATION

EXPLANATION:
The pricing tiers overlap, so some payment amounts qualify for multiple
tiers, which contradicts the "exactly one" requirement.


════════════════════════════════════════════════════════════════════════════════
SECTION 6: UNIT-DEPENDENT CONFLICTS
════════════════════════════════════════════════════════════════════════════════

────────────────────────────────────────────────────────────────────────────────
Example 6.1: Currency Mismatch - Incomparable Constraints
────────────────────────────────────────────────────────────────────────────────

SCENARIO:
A global marketplace has policies from different regions with different
currencies.

POLICY:
    Constraint 1: payAmount ≤ 100 EUR
    Constraint 2: payAmount ≥ 150 USD

ANALYSIS:
    These constraints use DIFFERENT units (EUR vs USD).
    Without exchange rate information, they cannot be compared.
    
    ODRL-SA creates separate Z3 variables:
      • payAmount_EUR_default
      • payAmount_USD_default
    
    JUDGMENT: UNKNOWN (Incomparable)

EXPLANATION:
Without knowing the EUR/USD exchange rate, we cannot determine if these
constraints conflict. €100 might be more or less than $150 depending on
the rate. ODRL-SA correctly reports UNKNOWN rather than false certainty.


────────────────────────────────────────────────────────────────────────────────
Example 6.2: Same Unit - Detectable Conflict
────────────────────────────────────────────────────────────────────────────────

SCENARIO:
Both constraints use the same currency.

POLICY:
    Constraint 1: payAmount ≤ 100 EUR
    Constraint 2: payAmount ≥ 150 EUR

ANALYSIS:
    Same unit: EUR
    Same Z3 variable: payAmount_EUR_default
    
    α(payAmount ≤ 100) = [0, 100]
    α(payAmount ≥ 150) = [150, +∞)
    
    Meet: [0, 100] ∩ [150, +∞) = ∅
    
    JUDGMENT: CONFLICT


────────────────────────────────────────────────────────────────────────────────
Example 6.3: Resolution Units - DPI vs PPI Independence
────────────────────────────────────────────────────────────────────────────────

SCENARIO:
Image licensing with different resolution measurements.

POLICY:
    Constraint 1: resolution ≤ 300 DPI (print resolution)
    Constraint 2: resolution ≥ 600 PPI (screen resolution)

ANALYSIS:
    Different units: DPI vs PPI
    Different Z3 variables:
      • resolution_DPI_default
      • resolution_PPI_default
    
    No conflict detected (independent variables).
    
    JUDGMENT: CONSISTENT ✓ (but possibly unintended)

NOTE:
While technically DPI and PPI are often equivalent, ODRL-SA treats them
as independent without oracle knowledge. This is SOUND (no false conflicts)
but may miss some conflicts (incomplete for unknown unit relationships).


════════════════════════════════════════════════════════════════════════════════
SECTION 7: SUMMARY - CONFLICT TYPES AND DETECTION
════════════════════════════════════════════════════════════════════════════════

┌─────────────────────────┬────────────────────────────┬──────────────────────┐
│ Conflict Type           │ Cause                      │ Detection Method     │
├─────────────────────────┼────────────────────────────┼──────────────────────┤
│ INTERNAL CONFLICT       │ Mutually exclusive         │ SMT: UNSAT          │
│                         │ constraints in one rule    │                      │
├─────────────────────────┼────────────────────────────┼──────────────────────┤
│ DEONTIC CONFLICT        │ Permission & Prohibition   │ SMT: SAT on overlap  │
│                         │ overlap on same action     │                      │
├─────────────────────────┼────────────────────────────┼──────────────────────┤
│ INHERITANCE VIOLATION   │ Child more permissive      │ SMT: SAT on          │
│                         │ than parent                │ φ_child ∧ ¬φ_parent  │
├─────────────────────────┼────────────────────────────┼──────────────────────┤
│ TAUTOLOGY               │ Constraint always true     │ Compare to domain    │
├─────────────────────────┼────────────────────────────┼──────────────────────┤
│ REDUNDANCY              │ Duplicate or subsumed      │ Subsumption check    │
│                         │ constraints                │                      │
├─────────────────────────┼────────────────────────────┼──────────────────────┤
│ UNSATISFIABLE           │ Constraint violates        │ SMT: UNSAT with      │
│                         │ domain bounds              │ domain constraints   │
├─────────────────────────┼────────────────────────────┼──────────────────────┤
│ UNKNOWN                 │ Incomparable operands      │ Unit/operand         │
│                         │ or units                   │ mismatch check       │
└─────────────────────────┴────────────────────────────┴──────────────────────┘


════════════════════════════════════════════════════════════════════════════════
SECTION 8: FORMAL GUARANTEES
════════════════════════════════════════════════════════════════════════════════

SOUNDNESS:
  If ODRL-SA reports CONFLICT, there is definitely a conflict.
  No false positives - every reported conflict is real.

COMPLETENESS (for L_xsd operands):
  If a conflict exists among fully analyzable operands, ODRL-SA will find it.
  No false negatives within the supported fragment.

DECIDABILITY:
  Analysis always terminates. QF_LRA and QF_LIA are decidable theories.

OVER-APPROXIMATION (for L_sem operands):
  For semantic operands (language, purpose, etc.), ODRL-SA may report
  UNKNOWN rather than CONFLICT. This is safe but incomplete.

════════════════════════════════════════════════════════════════════════════════
"""

# For programmatic access to examples
EXAMPLES = {
    "internal_conflict": [
        {
            "name": "Impossible Time Window",
            "domain": "Research Data",
            "constraints": ["dateTime ≤ 2024-01-01", "dateTime ≥ 2024-06-01"],
            "judgment": "CONFLICT",
            "explanation": "No timestamp can be before January AND after June 2024"
        },
        {
            "name": "Contradictory Resolution",
            "domain": "Media Licensing",
            "constraints": ["resolution ≥ 600 DPI", "resolution ≤ 300 DPI"],
            "judgment": "CONFLICT",
            "explanation": "No resolution can be ≥600 AND ≤300"
        },
    ],
    "deontic_conflict": [
        {
            "name": "Healthcare Access Overlap",
            "domain": "Healthcare",
            "permission": "count ≤ 1000",
            "prohibition": "count > 500",
            "overlap": "(500, 1000]",
            "judgment": "DEONTIC CONFLICT",
            "witness": "count = 750"
        },
    ],
    "inheritance_violation": [
        {
            "name": "Department Override",
            "domain": "Corporate Governance",
            "parent": "count ≤ 100",
            "child": "count ≤ 500",
            "judgment": "INHERITANCE VIOLATION",
            "counter_model": "count = 250"
        },
    ],
}

if __name__ == "__main__":
    print(__doc__)
