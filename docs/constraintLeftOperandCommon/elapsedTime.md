## elapsedTime - Formal Specification

### ODRL Vocabulary Definition

```turtle
:elapsedTime
    a :LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrl: ;
    rdfs:label "Elapsed Time"@en ;
    skos:definition "A continuous elapsed time period which may be used for 
                     exercising of the action of the Rule. Right operand value 
                     MUST be an xsd:duration as defined by [[xmlschema11-2]]."@en ;
    skos:note "Only the eq, lt, lteq operators SHOULD be used. See also 
               Metered Time. <br />Example: <code>elapsedTime eq P60M</code> 
               indicates a total elapsed time of 60 Minutes." ;
    skos:scopeNote "Non-Normative"@en .
```

---

### 1. Semantic Analysis

#### 1.1 What It Measures

| Aspect | Description |
|--------|-------------|
| **Semantics** | Total continuous time window allowed for exercising an action |
| **Example** | "You have 60 minutes to use this asset" |
| **Reference point** | Implicit (start of permission grant, first use, etc.) |
| **Value type** | `xsd:duration` (ISO 8601 duration) |

#### 1.2 Key Characteristics

| Property | Value | Implication |
|----------|-------|-------------|
| **Continuous** | Yes | Uninterrupted time window |
| **Reference-dependent** | Yes | Requires start point to evaluate |
| **Cumulative** | No | Unlike `meteredTime` which accumulates |
| **Operators** | eq, lt, lteq (SHOULD) | Upper bound semantics |

#### 1.3 Distinction from Related LeftOperands

| LeftOperand | Semantics | Cumulative | Reference |
|-------------|-----------|------------|-----------|
| **elapsedTime** | Continuous window duration | No | Start of grant |
| **meteredTime** | Accumulated active usage | Yes | Total usage time |
| **dateTime** | Absolute temporal point | N/A | Calendar |
| **timeInterval** | Recurring period | N/A | Event-based |

---

### 2. The Challenge: Reference-Dependence

#### 2.1 The Problem

`elapsedTime` constraints are **reference-dependent** — they require knowing:
1. **Start reference point** (when does the clock start?)
2. **Current time** (what time is "now"?)

```
elapsedTime lteq P60M
```

This means: "current_time - start_time ≤ 60 minutes"

But ODRL doesn't specify what `start_time` is!

#### 2.2 Possible Reference Points

| Reference | Interpretation |
|-----------|----------------|
| Policy creation | Clock starts when policy is created |
| First access | Clock starts on first use of asset |
| Grant time | Clock starts when permission is granted |
| Session start | Clock starts when session begins |

**ODRL leaves this unspecified** — it's profile/implementation dependent.

---

### 3. Static Analysis Approach

#### 3.1 What We CAN Analyze

Despite reference-dependence, we can still detect certain conflicts:

| Scenario | Analyzable | Reason |
|----------|------------|--------|
| `elapsedTime lteq P30M` ∧ `elapsedTime gteq P60M` | ✅ Yes | Duration intervals don't overlap |
| `elapsedTime eq P60M` ∧ `elapsedTime eq P30M` | ✅ Yes | Different exact durations |
| `elapsedTime lteq P60M` ∧ `dateTime gteq 2025-01-01` | ❌ No | Different dimensions |

#### 3.2 Abstraction Strategy

**Key insight:** Treat `elapsedTime` as a **duration constraint** independent of reference point.

$$\text{elapsedTime} : \mathbb{D}^+ \quad \text{(positive durations)}$$

Where $\mathbb{D}^+ = \{ d \in \text{Duration} \mid d > 0 \}$

---

### 4. xsd:duration Handling

#### 4.1 ISO 8601 Duration Format

```
P[n]Y[n]M[n]DT[n]H[n]M[n]S

P     = duration designator
[n]Y  = years
[n]M  = months (before T)
[n]D  = days
T     = time designator
[n]H  = hours
[n]M  = minutes (after T)
[n]S  = seconds
```

**Examples:**
- `P60M` = 60 minutes ❌ AMBIGUOUS (could be 60 months!)
- `PT60M` = 60 minutes ✅
- `P1D` = 1 day
- `PT1H30M` = 1 hour 30 minutes
- `P1Y2M3DT4H5M6S` = 1 year, 2 months, 3 days, 4 hours, 5 minutes, 6 seconds

#### 4.2 The Month/Year Problem

Months and years have **variable lengths**:
- February = 28 or 29 days
- Months = 28-31 days
- Years = 365 or 366 days

**This makes durations partially ordered, not totally ordered!**

$$P1M \stackrel{?}{\lessgtr} P30D \quad \text{(depends on which month)}$$

#### 4.3 ODRL-SA Strategy: Normalize to Seconds

**Conservative approach:** Normalize durations to seconds using fixed conversions.

| Unit | Seconds | Note |
|------|---------|------|
| Second | 1 | Exact |
| Minute | 60 | Exact |
| Hour | 3600 | Exact |
| Day | 86400 | Fixed (ignores DST) |
| Month | 2629746 | Average (30.44 days) |
| Year | 31556952 | Average (365.25 days) |

**Trade-off:** This is an approximation, but enables decidable comparison.

---

### 5. Formal Domain Specification

$$\text{dom}(\texttt{elapsedTime}) = \mathbb{R}_{> 0} = (0, +\infty) \quad \text{(seconds)}$$

| Property | Value | Justification |
|----------|-------|---------------|
| **Lower bound** | 0 (exclusive) | Zero duration is meaningless |
| **Upper bound** | ∞ | No theoretical maximum |
| **Internal representation** | Seconds (Real) | Normalized from xsd:duration |

---

### 6. Operator Specification

**ODRL recommendation:** Only `eq`, `lt`, `lteq` SHOULD be used.

| Operator | Valid | Semantics | Common Use |
|----------|-------|-----------|------------|
| `eq` | ✅ | Exact duration | "Exactly 60 minutes" |
| `lt` | ✅ | Less than | "Under 60 minutes" |
| `lteq` | ✅ | At most | "Up to 60 minutes" |
| `gt` | ⚠️ | Greater than | Unusual but valid |
| `gteq` | ⚠️ | At least | "Minimum 60 minutes" |
| `neq` | ⚠️ | Not equal | Unusual |
| `isAnyOf` | ⚠️ | Set membership | Unusual for durations |
| `isNoneOf` | ⚠️ | Set exclusion | Unusual for durations |
| `isAllOf` | ❌ | Not meaningful | |

**ODRL-SA approach:** Support all numeric operators, but flag non-recommended usage.

---

### 7. SMT Encoding

#### 7.1 Duration Parser

```python
import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class ParsedDuration:
    """Parsed ISO 8601 duration components."""
    years: float = 0
    months: float = 0
    days: float = 0
    hours: float = 0
    minutes: float = 0
    seconds: float = 0
    
    # Conversion constants (to seconds)
    SECONDS_PER_MINUTE = 60
    SECONDS_PER_HOUR = 3600
    SECONDS_PER_DAY = 86400
    SECONDS_PER_MONTH = 2629746    # Average: 30.44 days
    SECONDS_PER_YEAR = 31556952    # Average: 365.25 days
    
    def to_seconds(self) -> float:
        """Convert duration to total seconds."""
        return (
            self.years * self.SECONDS_PER_YEAR +
            self.months * self.SECONDS_PER_MONTH +
            self.days * self.SECONDS_PER_DAY +
            self.hours * self.SECONDS_PER_HOUR +
            self.minutes * self.SECONDS_PER_MINUTE +
            self.seconds
        )
    
    def has_calendar_components(self) -> bool:
        """Check if duration has variable-length components."""
        return self.years > 0 or self.months > 0


def parse_xsd_duration(duration_str: str) -> Optional[ParsedDuration]:
    """
    Parse xsd:duration string to components.
    
    Format: P[n]Y[n]M[n]DT[n]H[n]M[n]S
    
    Examples:
        PT60M -> 60 minutes
        P1D -> 1 day
        P1Y2M3DT4H5M6S -> complex duration
    """
    # Regex for ISO 8601 duration
    pattern = r'^P(?:(\d+(?:\.\d+)?)Y)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)D)?(?:T(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?)?$'
    
    match = re.match(pattern, duration_str)
    if not match:
        return None
    
    groups = match.groups()
    
    return ParsedDuration(
        years=float(groups[0] or 0),
        months=float(groups[1] or 0),
        days=float(groups[2] or 0),
        hours=float(groups[3] or 0),
        minutes=float(groups[4] or 0),
        seconds=float(groups[5] or 0)
    )


def duration_to_seconds(duration_str: str) -> Optional[float]:
    """Convert xsd:duration string to seconds."""
    parsed = parse_xsd_duration(duration_str)
    if parsed is None:
        return None
    return parsed.to_seconds()
```

#### 7.2 SMT Encoder

```python
from z3 import *
from enum import Enum
from typing import List, Tuple, Optional

class AnalysisResult(Enum):
    CONFLICT = "CONFLICT"
    POSSIBLY_COMPATIBLE = "POSSIBLY_COMPATIBLE"
    UNKNOWN = "UNKNOWN"

class ElapsedTimeEncoder:
    """
    SMT encoder for elapsedTime constraints.
    
    Theory: QF_LRA (Quantifier-Free Linear Real Arithmetic)
    Domain: (0, ∞) in seconds
    """
    
    # Recommended operators per ODRL spec
    RECOMMENDED_OPS = {"eq", "lt", "lteq"}
    VALID_OPS = {"eq", "neq", "lt", "lteq", "gt", "gteq", "isAnyOf", "isNoneOf"}
    
    def __init__(self):
        self.warnings: List[str] = []
    
    def encode(
        self, 
        operator: str, 
        duration_value: str,
        var: Optional[ArithRef] = None
    ) -> Tuple[BoolRef, List[str]]:
        """
        Encode elapsedTime constraint as SMT formula.
        
        Returns (formula, warnings).
        """
        self.warnings = []
        
        # Validate operator
        if operator not in self.VALID_OPS:
            raise ValueError(f"Invalid operator for elapsedTime: {operator}")
        
        if operator not in self.RECOMMENDED_OPS:
            self.warnings.append(
                f"Operator '{operator}' not recommended for elapsedTime; "
                f"ODRL recommends: {self.RECOMMENDED_OPS}"
            )
        
        # Parse duration
        seconds = duration_to_seconds(duration_value)
        if seconds is None:
            self.warnings.append(f"Could not parse duration: {duration_value}")
            return BoolVal(True), self.warnings  # Over-approximate
        
        if seconds <= 0:
            self.warnings.append(f"Duration must be positive: {duration_value}")
            return BoolVal(False), self.warnings  # Unsatisfiable
        
        # Check for calendar components
        parsed = parse_xsd_duration(duration_value)
        if parsed and parsed.has_calendar_components():
            self.warnings.append(
                f"Duration '{duration_value}' contains months/years; "
                f"using average conversion (may be imprecise)"
            )
        
        # Create or use provided variable
        if var is None:
            var = Real('elapsedTime')
        
        # Domain constraint: strictly positive
        domain = var > 0
        
        # Encode operator
        if operator == "eq":
            constraint = var == seconds
        elif operator == "neq":
            constraint = var != seconds
        elif operator == "lt":
            constraint = var < seconds
        elif operator == "lteq":
            constraint = var <= seconds
        elif operator == "gt":
            constraint = var > seconds
        elif operator == "gteq":
            constraint = var >= seconds
        elif operator == "isAnyOf":
            # Value should be a list of durations
            if isinstance(duration_value, list):
                secs_list = [duration_to_seconds(d) for d in duration_value]
                secs_list = [s for s in secs_list if s is not None and s > 0]
                if not secs_list:
                    return BoolVal(False), self.warnings
                constraint = Or([var == s for s in secs_list])
            else:
                constraint = var == seconds
        elif operator == "isNoneOf":
            if isinstance(duration_value, list):
                secs_list = [duration_to_seconds(d) for d in duration_value]
                secs_list = [s for s in secs_list if s is not None and s > 0]
                constraint = And([var != s for s in secs_list])
            else:
                constraint = var != seconds
        
        return And(domain, constraint), self.warnings
    
    def detect_conflict(
        self,
        constraints: List[Tuple[str, str]]  # [(operator, duration), ...]
    ) -> Tuple[AnalysisResult, Optional[float], List[str]]:
        """
        Detect conflicts among elapsedTime constraints.
        
        Returns (result, witness_seconds, warnings).
        """
        all_warnings = []
        solver = Solver()
        var = Real('elapsedTime')
        
        for op, duration in constraints:
            formula, warnings = self.encode(op, duration, var)
            solver.add(formula)
            all_warnings.extend(warnings)
        
        if solver.check() == sat:
            model = solver.model()
            # Extract witness value
            witness = None
            if model[var] is not None:
                witness = float(model[var].as_fraction())
            return AnalysisResult.POSSIBLY_COMPATIBLE, witness, all_warnings
        else:
            return AnalysisResult.CONFLICT, None, all_warnings
```

---

### 8. Abstract Interpretation

#### 8.1 Abstract Domain

$$\hat{\mathcal{D}} = \mathbb{I}_{\mathbb{Q}^+} = \{ [a, b] \mid 0 < a \leq b \leq \infty \}$$

Intervals over positive rationals (representing seconds).

#### 8.2 Abstraction Function

$$\alpha(\texttt{elapsedTime op } d) = \begin{cases}
[d, d] & \text{if op} = \texttt{eq} \\
(0, d) & \text{if op} = \texttt{lt} \\
(0, d] & \text{if op} = \texttt{lteq} \\
(d, +\infty) & \text{if op} = \texttt{gt} \\
[d, +\infty) & \text{if op} = \texttt{gteq} \\
(0, +\infty) \setminus \{d\} & \text{if op} = \texttt{neq}
\end{cases}$$

Where $d = \texttt{toSeconds}(\text{duration})$.

#### 8.3 Conflict Detection

$$\texttt{CONFLICT}(c_1, c_2) \iff \alpha(c_1) \cap \alpha(c_2) = \emptyset$$

---

### 9. Conflict Detection Examples

```python
encoder = ElapsedTimeEncoder()

# Example 1: Compatible constraints
# elapsedTime lteq PT60M ∧ elapsedTime gteq PT30M
# → (0, 3600] ∩ [1800, ∞) = [1800, 3600] ≠ ∅
result, witness, _ = encoder.detect_conflict([
    ("lteq", "PT60M"),
    ("gteq", "PT30M")
])
# → POSSIBLY_COMPATIBLE, witness ≈ 1800-3600

# Example 2: Conflicting constraints
# elapsedTime lteq PT30M ∧ elapsedTime gteq PT60M
# → (0, 1800] ∩ [3600, ∞) = ∅
result, _, _ = encoder.detect_conflict([
    ("lteq", "PT30M"),
    ("gteq", "PT60M")
])
# → CONFLICT

# Example 3: Exact duration conflict
# elapsedTime eq PT60M ∧ elapsedTime eq PT30M
# → {3600} ∩ {1800} = ∅
result, _, _ = encoder.detect_conflict([
    ("eq", "PT60M"),
    ("eq", "PT30M")
])
# → CONFLICT

# Example 4: Upper bound only (typical use)
# elapsedTime lteq PT60M
# → (0, 3600] ≠ ∅
result, witness, _ = encoder.detect_conflict([
    ("lteq", "PT60M")
])
# → POSSIBLY_COMPATIBLE
```

---

### 10. Formal Semantics

#### 10.1 Evaluation Semantics (Runtime)

At runtime, `elapsedTime` is evaluated relative to a reference point:

$$\llbracket \texttt{elapsedTime op } d \rrbracket_{\text{eval}}(t_{\text{now}}, t_{\text{ref}}) = \begin{cases}
\top & \text{if } (t_{\text{now}} - t_{\text{ref}}) \; \textit{op} \; d \\
\bot & \text{otherwise}
\end{cases}$$

Where:
- $t_{\text{now}}$ = current timestamp
- $t_{\text{ref}}$ = reference timestamp (start of grant, first use, etc.)
- $d$ = duration in seconds

#### 10.2 Static Analysis Semantics

For static analysis, we abstract away the reference point:

$$\llbracket \texttt{elapsedTime op } d \rrbracket_{\text{static}} = \{ t \in \mathbb{R}_{>0} \mid t \; \textit{op} \; d \}$$

**Soundness guarantee:**

$$\llbracket c_1 \rrbracket_{\text{static}} \cap \llbracket c_2 \rrbracket_{\text{static}} = \emptyset \implies \forall t_{\text{ref}}. \neg(\llbracket c_1 \rrbracket_{\text{eval}} \land \llbracket c_2 \rrbracket_{\text{eval}})$$

---

### 11. Comparison with meteredTime

| Aspect | elapsedTime | meteredTime |
|--------|-------------|-------------|
| **Semantics** | Continuous window | Accumulated active time |
| **Counting** | Wall-clock time | Active usage time |
| **Pauses** | Clock keeps running | Clock pauses |
| **Example** | "Valid for 24 hours" | "1 hour of playback" |
| **Static analysis** | ✅ Partial support | ❌ Runtime only |
| **Reference** | Start of grant | Cumulative |

**Key distinction:**
- `elapsedTime`: "You have 60 minutes from now to use this"
- `meteredTime`: "You have 60 minutes of actual usage time"

---

### 12. Classification

| Property | Value |
|----------|-------|
| **Analyzability Class** | PARTIAL |
| **Category** | L_temporal_duration |
| **Z3 Sort** | Real |
| **Domain** | (0, ∞) seconds |
| **External KB Required** | No |
| **Reference-dependent** | Yes (for evaluation) |
| **Decidable (static)** | Yes (interval arithmetic) |
| **Complete** | No (reference point unknown) |

---

### 13. Configuration Entry

```python
"elapsedTime": {
    "class": "PARTIAL",
    "category": "L_temporal_duration",
    "z3_sort": "Real",
    "domain": {
        "min": 0,
        "max": None,
        "inclusive_min": False,  # Strictly positive
        "inclusive_max": None
    },
    "value_type": "xsd:duration",
    "operators": {
        "recommended": ["eq", "lt", "lteq"],
        "valid": ["eq", "neq", "lt", "lteq", "gt", "gteq", "isAnyOf", "isNoneOf"]
    },
    "reference_dependent": True,
    "external_kb": False,
    "decidable": True,
    "complete": False,
    "smt_theory": "QF_LRA",
    "notes": "Duration normalized to seconds; months/years use average conversion"
}
```

---

### 14. Complete Implementation

```python
from z3 import *
from dataclasses import dataclass
from typing import List, Tuple, Optional, Set
from enum import Enum
import re

class AnalysisResult(Enum):
    CONFLICT = "CONFLICT"
    POSSIBLY_COMPATIBLE = "POSSIBLY_COMPATIBLE"
    UNKNOWN = "UNKNOWN"

@dataclass
class ParsedDuration:
    """Parsed ISO 8601 duration components."""
    years: float = 0
    months: float = 0
    days: float = 0
    hours: float = 0
    minutes: float = 0
    seconds: float = 0
    
    SECONDS_PER_MINUTE = 60
    SECONDS_PER_HOUR = 3600
    SECONDS_PER_DAY = 86400
    SECONDS_PER_MONTH = 2629746
    SECONDS_PER_YEAR = 31556952
    
    def to_seconds(self) -> float:
        return (
            self.years * self.SECONDS_PER_YEAR +
            self.months * self.SECONDS_PER_MONTH +
            self.days * self.SECONDS_PER_DAY +
            self.hours * self.SECONDS_PER_HOUR +
            self.minutes * self.SECONDS_PER_MINUTE +
            self.seconds
        )
    
    def has_calendar_components(self) -> bool:
        return self.years > 0 or self.months > 0
    
    def to_human_readable(self) -> str:
        parts = []
        if self.years: parts.append(f"{self.years}y")
        if self.months: parts.append(f"{self.months}mo")
        if self.days: parts.append(f"{self.days}d")
        if self.hours: parts.append(f"{self.hours}h")
        if self.minutes: parts.append(f"{self.minutes}m")
        if self.seconds: parts.append(f"{self.seconds}s")
        return " ".join(parts) or "0s"


def parse_xsd_duration(duration_str: str) -> Optional[ParsedDuration]:
    """Parse xsd:duration string."""
    pattern = r'^P(?:(\d+(?:\.\d+)?)Y)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)D)?(?:T(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?)?$'
    match = re.match(pattern, duration_str)
    if not match:
        return None
    groups = match.groups()
    return ParsedDuration(
        years=float(groups[0] or 0),
        months=float(groups[1] or 0),
        days=float(groups[2] or 0),
        hours=float(groups[3] or 0),
        minutes=float(groups[4] or 0),
        seconds=float(groups[5] or 0)
    )


@dataclass
class ElapsedTimeConstraint:
    """Represents an elapsedTime constraint."""
    operator: str
    duration: str
    
    def to_seconds(self) -> Optional[float]:
        parsed = parse_xsd_duration(self.duration)
        return parsed.to_seconds() if parsed else None


class ElapsedTimeSemantics:
    """
    Formal semantics for elapsedTime LeftOperand.
    
    Domain: (0, ∞) in seconds
    Theory: QF_LRA
    """
    
    RECOMMENDED_OPS = {"eq", "lt", "lteq"}
    VALID_OPS = {"eq", "neq", "lt", "lteq", "gt", "gteq", "isAnyOf", "isNoneOf"}
    
    def __init__(self):
        self.warnings: List[str] = []
    
    # ===== Denotational Semantics =====
    
    def denote(self, constraint: ElapsedTimeConstraint) -> Tuple[Optional[float], Optional[float]]:
        """
        Compute denotation as interval (min, max).
        
        Returns (lower_bound, upper_bound) in seconds.
        None represents infinity.
        """
        seconds = constraint.to_seconds()
        if seconds is None or seconds <= 0:
            return (None, None)  # Invalid
        
        op = constraint.operator
        
        if op == "eq":
            return (seconds, seconds)
        elif op == "lt":
            return (0, seconds)  # Exclusive upper bound
        elif op == "lteq":
            return (0, seconds)  # Inclusive upper bound
        elif op == "gt":
            return (seconds, None)  # Exclusive lower bound
        elif op == "gteq":
            return (seconds, None)  # Inclusive lower bound
        elif op == "neq":
            return (0, None)  # Full domain minus point
        else:
            return (0, None)  # Over-approximate unknown operators
    
    def interval_intersection(
        self,
        intervals: List[Tuple[Optional[float], Optional[float]]]
    ) -> Tuple[Optional[float], Optional[float]]:
        """Compute intersection of intervals."""
        if not intervals:
            return (0, None)
        
        lower = 0.0
        upper = float('inf')
        
        for (lo, hi) in intervals:
            if lo is not None:
                lower = max(lower, lo)
            if hi is not None:
                upper = min(upper, hi)
        
        if lower > upper:
            return (None, None)  # Empty intersection
        
        return (lower, upper if upper != float('inf') else None)
    
    # ===== SMT Encoding =====
    
    def encode(
        self,
        constraint: ElapsedTimeConstraint,
        var: Optional[ArithRef] = None
    ) -> BoolRef:
        """Encode constraint as SMT formula."""
        self.warnings = []
        
        if constraint.operator not in self.VALID_OPS:
            raise ValueError(f"Invalid operator: {constraint.operator}")
        
        if constraint.operator not in self.RECOMMENDED_OPS:
            self.warnings.append(
                f"Operator '{constraint.operator}' not recommended for elapsedTime"
            )
        
        seconds = constraint.to_seconds()
        if seconds is None:
            self.warnings.append(f"Could not parse: {constraint.duration}")
            return BoolVal(True)
        
        if seconds <= 0:
            return BoolVal(False)
        
        parsed = parse_xsd_duration(constraint.duration)
        if parsed and parsed.has_calendar_components():
            self.warnings.append(
                f"Duration has months/years; using average conversion"
            )
        
        if var is None:
            var = Real('elapsedTime')
        
        domain = var > 0
        
        op = constraint.operator
        if op == "eq":
            return And(domain, var == seconds)
        elif op == "neq":
            return And(domain, var != seconds)
        elif op == "lt":
            return And(domain, var < seconds)
        elif op == "lteq":
            return And(domain, var <= seconds)
        elif op == "gt":
            return And(domain, var > seconds)
        elif op == "gteq":
            return And(domain, var >= seconds)
        else:
            return domain
    
    # ===== Conflict Detection =====
    
    def detect_conflict(
        self,
        constraints: List[ElapsedTimeConstraint]
    ) -> Tuple[AnalysisResult, Optional[float]]:
        """
        Detect conflicts using SMT solving.
        
        Returns (result, witness_seconds).
        """
        solver = Solver()
        var = Real('elapsedTime')
        
        for c in constraints:
            solver.add(self.encode(c, var))
        
        if solver.check() == sat:
            model = solver.model()
            witness = None
            if model[var] is not None:
                witness = float(model[var].as_fraction())
            return (AnalysisResult.POSSIBLY_COMPATIBLE, witness)
        else:
            return (AnalysisResult.CONFLICT, None)
    
    def detect_conflict_abstract(
        self,
        constraints: List[ElapsedTimeConstraint]
    ) -> AnalysisResult:
        """
        Detect conflicts using interval abstraction (faster).
        """
        intervals = []
        for c in constraints:
            interval = self.denote(c)
            if interval == (None, None):
                continue
            intervals.append(interval)
        
        result = self.interval_intersection(intervals)
        
        if result == (None, None):
            return AnalysisResult.CONFLICT
        else:
            return AnalysisResult.POSSIBLY_COMPATIBLE
    
    # ===== Structural Validation =====
    
    def validate(self, constraint: ElapsedTimeConstraint) -> List[str]:
        """Validate constraint structure."""
        issues = []
        
        if constraint.operator not in self.VALID_OPS:
            issues.append(f"Invalid operator: {constraint.operator}")
        elif constraint.operator not in self.RECOMMENDED_OPS:
            issues.append(f"Non-recommended operator: {constraint.operator}")
        
        parsed = parse_xsd_duration(constraint.duration)
        if parsed is None:
            issues.append(f"Invalid xsd:duration: {constraint.duration}")
        elif parsed.to_seconds() <= 0:
            issues.append(f"Duration must be positive: {constraint.duration}")
        
        return issues


# ===== Evaluation Semantics (Runtime) =====

class ElapsedTimeEvaluator:
    """
    Runtime evaluator for elapsedTime constraints.
    
    Requires reference point specification.
    """
    
    @staticmethod
    def evaluate(
        constraint: ElapsedTimeConstraint,
        current_time: float,
        reference_time: float
    ) -> bool:
        """
        Evaluate constraint at runtime.
        
        Args:
            constraint: The elapsedTime constraint
            current_time: Current timestamp (seconds since epoch)
            reference_time: Reference timestamp (start of grant)
        
        Returns:
            True if constraint is satisfied
        """
        elapsed = current_time - reference_time
        if elapsed < 0:
            return False  # Invalid: current before reference
        
        threshold = constraint.to_seconds()
        if threshold is None:
            return False  # Invalid duration
        
        op = constraint.operator
        
        if op == "eq":
            return elapsed == threshold
        elif op == "neq":
            return elapsed != threshold
        elif op == "lt":
            return elapsed < threshold
        elif op == "lteq":
            return elapsed <= threshold
        elif op == "gt":
            return elapsed > threshold
        elif op == "gteq":
            return elapsed >= threshold
        else:
            return False
```

---

### 15. Test Cases

```turtle
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix ex:   <http://example.org/> .

# Test 1: ODRL example - exactly 60 minutes
ex:policy_elapsed_exact
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:leftOperand odrl:elapsedTime ;
            odrl:operator odrl:eq ;
            odrl:rightOperand "PT60M"^^xsd:duration
        ]
    ] .
# Expected: VALID

# Test 2: Upper bound (typical use)
ex:policy_elapsed_upper
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:leftOperand odrl:elapsedTime ;
            odrl:operator odrl:lteq ;
            odrl:rightOperand "P1D"^^xsd:duration
        ]
    ] .
# Expected: VALID (up to 1 day)

# Test 3: Conflicting bounds - CONFLICT
ex:policy_elapsed_conflict
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:elapsedTime ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "PT30M"^^xsd:duration ]
                [ odrl:leftOperand odrl:elapsedTime ;
                  odrl:operator odrl:gteq ;
                  odrl:rightOperand "PT60M"^^xsd:duration ]
            )
        ]
    ] .
# Expected: CONFLICT ((0, 1800] ∩ [3600, ∞) = ∅)

# Test 4: Compatible bounds
ex:policy_elapsed_compatible
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:elapsedTime ;
                  odrl:operator odrl:gteq ;
                  odrl:rightOperand "PT30M"^^xsd:duration ]
                [ odrl:leftOperand odrl:elapsedTime ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "PT60M"^^xsd:duration ]
            )
        ]
    ] .
# Expected: COMPATIBLE ([1800, 3600] ≠ ∅)

# Test 5: Exact values conflict
ex:policy_elapsed_exact_conflict
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:play ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrl:elapsedTime ;
                  odrl:operator odrl:eq ;
                  odrl:rightOperand "PT60M"^^xsd:duration ]
                [ odrl:leftOperand odrl:elapsedTime ;
                  odrl:operator odrl:eq ;
                  odrl:rightOperand "PT30M"^^xsd:duration ]
            )
        ]
    ] .
# Expected: CONFLICT ({3600} ∩ {1800} = ∅)

# Test 6: Duration with calendar components (warning)
ex:policy_elapsed_calendar
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:leftOperand odrl:elapsedTime ;
            odrl:operator odrl:lteq ;
            odrl:rightOperand "P1M"^^xsd:duration
        ]
    ] .
# Expected: VALID with WARNING (month has variable length)

# Test 7: Non-recommended operator (warning)
ex:policy_elapsed_gt
    a odrl:Set ;
    odrl:permission [
        odrl:action odrl:use ;
        odrl:constraint [
            odrl:leftOperand odrl:elapsedTime ;
            odrl:operator odrl:gt ;
            odrl:rightOperand "PT1H"^^xsd:duration
        ]
    ] .
# Expected: VALID with WARNING (gt not recommended)
```

---

### 16. Publication Statement

> **elapsedTime** specifies a continuous time window duration during which an action may be exercised, with values expressed as `xsd:duration` (ISO 8601). Unlike `meteredTime` which accumulates active usage, `elapsedTime` represents wall-clock time from an implicit reference point. ODRL-SA normalizes durations to seconds for SMT encoding within QF_LRA, using average conversions for variable-length components (months ≈ 30.44 days, years ≈ 365.25 days). The ODRL specification recommends only `eq`, `lt`, and `lteq` operators, reflecting the typical upper-bound semantics ("valid for at most 60 minutes"). Static conflict detection identifies unsatisfiable duration intervals—constraints like `lteq PT30M` ∧ `gteq PT60M` yield CONFLICT as $(0, 1800] \cap [3600, \infty) = \emptyset$. Full evaluation requires a reference timestamp, making this LeftOperand reference-dependent; static analysis provides sound but incomplete conflict detection.

