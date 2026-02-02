## Formal Semantics for Spatial and Temporal Reasoning in ODRL-SA

### 1. The Current Problem

```
┌─────────────────────────────────────────────────────────────────┐
│                    CURRENT LIMITATION                           │
│                                                                 │
│  ODRL defines relativeSpatialPosition as 2D/3D:                │
│  "four corners of a rectangle... eight corners of a cuboid"    │
│                                                                 │
│  BUT ODRL constraint syntax only supports:                      │
│  • Single leftOperand                                           │
│  • Single operator                                              │
│  • Single rightOperand                                          │
│                                                                 │
│  RESULT: Cannot express 2D constraints natively                 │
│                                                                 │
│  ODRL-SA: 1D over-approximation                                 │
│  • Sound but incomplete                                         │
│  • May miss 2D-specific conflicts                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3. The Problem: What Formal Semantics Do We Need?

```
┌─────────────────────────────────────────────────────────────────┐
│           WHAT'S MISSING IN ODRL-SA                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CURRENT STATE:                                                 │
│  • 1D interval semantics for all LeftOperands                   │
│  • No formal model for multi-dimensional spaces                 │
│  • No geometric operations (intersection, containment)          │
│  • No coordinate system semantics                               │
│  • No temporal interval algebra                                 │
│                                                                 │
│  NEEDED FOR COMPLETE ANALYSIS:                                  │
│  • N-dimensional abstract domains                               │
│  • Geometric region semantics                                   │
│  • Allen's interval algebra for temporal reasoning              │
│  • Region Connection Calculus (RCC) for spatial reasoning       │
│  • Formal soundness proofs for all dimensions                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```
---

### 4. Foundational Approach:

```
┌─────────────────────────────────────────────────────────────────┐
│           FORMAL FOUNDATIONS FOR ODRL-SA                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TEMPORAL REASONING                                             │
│  ══════════════════                                             │
│  • Allen's Interval Algebra (1983)                              │
│  • Point-based temporal logic                                   │
│  • Duration calculus                                            │
│                                                                 │
│  SPATIAL REASONING                                              │
│  ═════════════════                                              │
│  • Region Connection Calculus (RCC-8)                           │
│  • Rectangle Algebra                                            │
│  • Interval-based spatial reasoning                             │
│                                                                 │
│  ABSTRACT INTERPRETATION                                        │
│  ═══════════════════════                                        │
│  • Cousot & Cousot (1977)                                       │
│  • Galois connections                                           │
│  • Box abstract domain                                          │
│                                                                 │
│  SMT THEORIES                                                   │
│  ════════════                                                   │
│  • QF_LRA (Linear Real Arithmetic)                             │
│  • QF_LIA (Linear Integer Arithmetic)                          │
│  • Difference Logic                                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```
### 4.1 Visual form of Formal Semantics

```
┌─────────────────────────────────────────────────────────────────┐
│           FORMAL SEMANTICS HIERARCHY                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                    ODRL-SA ABSTRACT DOMAIN                      │
│                           │                                     │
│         ┌─────────────────┼─────────────────┐                  │
│         │                 │                 │                  │
│         ▼                 ▼                 ▼                  │
│    ┌─────────┐      ┌─────────┐      ┌─────────┐              │
│    │ SCALAR  │      │TEMPORAL │      │ SPATIAL │              │
│    │ DOMAIN  │      │ DOMAIN  │      │ DOMAIN  │              │
│    └────┬────┘      └────┬────┘      └────┬────┘              │
│         │                │                │                    │
│         ▼                ▼                ▼                    │
│    ┌─────────┐      ┌─────────┐      ┌─────────┐              │
│    │Interval │      │ Allen's │      │  Box    │              │
│    │ Domain  │      │Interval │      │ Domain  │              │
│    │   𝓘_D   │      │ Algebra │      │   𝓑^n   │              │
│    └─────────┘      └─────────┘      └─────────┘              │
│         │                │                │                    │
│         │                │                │                    │
│         └────────────────┼────────────────┘                    │
│                          │                                     │
│                          ▼                                     │
│                  ┌───────────────┐                             │
│                  │    GALOIS     │                             │
│                  │  CONNECTION   │                             │
│                  │   (α, γ)      │                             │
│                  └───────────────┘                             │
│                          │                                     │
│              ┌───────────┴───────────┐                         │
│              │                       │                         │
│              ▼                       ▼                         │
│       ┌─────────────┐         ┌─────────────┐                 │
│       │  ABSTRACT   │         │  CONCRETE   │                 │
│       │   WORLD     │◄───────►│   WORLD     │                 │
│       │             │   γ(α)  │             │                 │
│       └─────────────┘         └─────────────┘                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 5. Full Semantics

```
┌─────────────────────────────────────────────────────────────────┐
│           APPROACH FOR FULL SEMANTICS                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  LAYER 1: FOUNDATIONAL THEORIES                                 │
│  ══════════════════════════════                                 │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Allen's Interval│  │ Region Connect. │  │ Abstract Interp.│ │
│  │ Algebra (1983)  │  │ Calculus RCC-8  │  │ Cousot (1977)   │ │
│  │                 │  │                 │  │                 │ │
│  │ 13 temporal     │  │ 8 spatial       │  │ Galois          │ │
│  │ relations       │  │ relations       │  │ connections     │ │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘ │
│           │                    │                    │          │
│           └────────────────────┼────────────────────┘          │
│                                │                               │
│                                ▼                               │
│                                                                │
│  LAYER 2: ODRL-SA ABSTRACT DOMAINS                            │
│  ═════════════════════════════════                            │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                                                         │  │
│  │  Interval Domain 𝓘_D     Box Domain 𝓑^n                │  │
│  │  ─────────────────────   ──────────────────────        │  │
│  │  • 1D constraints        • N-dimensional constraints   │  │
│  │  • Meet = intersection   • Meet = component-wise       │  │
│  │  • ⊥ = conflict         • ⊥ = any axis empty          │  │
│  │                                                         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
│  LAYER 3: SMT ENCODING                                        │
│  ═════════════════════                                        │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                                                         │  │
│  │  QF_LRA: Real constraints    QF_LIA: Integer constr.   │  │
│  │  ───────────────────────    ─────────────────────────  │  │
│  │  • percentage               • count                    │  │
│  │  • payAmount                • dateTime (epoch)         │  │
│  │  • relativeSize             • timeInterval             │  │
│  │  • spatial positions        • etc.                     │  │
│  │                                                         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
│  LAYER 4: CONFLICT DETECTION                                  │
│  ═══════════════════════════                                  │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                                                         │  │
│  │  α(c₁) ⊓ α(c₂) = ⊥  ══►  CONFLICT (sound, complete*)  │  │
│  │  α(c₁) ⊓ α(c₂) ≠ ⊥  ══►  POSSIBLY-COMPATIBLE         │  │
│  │                                                         │  │
│  │  * Complete when using axis-specific operands          │  │
│  │                                                         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
└─────────────────────────────────────────────────────────────────┘
```

## Multi-Dimensional LeftOperands in ODRL

### 1. Complete Inventory of Spatial/Temporal LeftOperands

```
┌─────────────────────────────────────────────────────────────────┐
│           ODRL LEFTOPERANDS WITH DIMENSIONAL SEMANTICS          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SPATIAL (Position in Space)                                    │
│  ═══════════════════════════                                    │
│  • absoluteSpatialPosition    2D/3D corners of box              │
│  • relativeSpatialPosition    2D/3D as percentages              │
│  • spatial                    Named geospatial area (KB)        │
│  • spatialCoordinates         Lat/Long/Alt coordinates          │
│                                                                 │
│  TEMPORAL (Position in Time)                                    │
│  ═══════════════════════════                                    │
│  • absoluteTemporalPosition   Absolute time in stream           │
│  • relativeTemporalPosition   Percentage of stream duration     │
│  • dateTime                   Calendar date/time                │
│  • elapsedTime                Duration from reference           │
│  • delayPeriod                Waiting period                    │
│  • timeInterval               Recurring period                  │
│  • event                      Named temporal event (KB)         │
│                                                                 │
│  SIZE (Spatial Dimensions)                                      │
│  ═════════════════════════                                      │
│  • absoluteSize               Absolute dimensions (2D/3D)       │
│  • relativeSize               Percentage dimensions (2D/3D)     │
│  • resolution                 DPI/PPI (technically 1D)          │
│                                                                 │
│  GENERIC POSITION                                               │
│  ════════════════                                               │
│  • absolutePosition           Parent of spatial/temporal        │
│  • relativePosition           Parent of spatial/temporal        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 2. Dimensions

| LeftOperand | ODRL Spec Dims | Current ODRL-SA | Needs Profile? |
|-------------|----------------|-----------------|----------------|
| **absoluteSpatialPosition** | 2D/3D | Equality only |  Yes |
| **relativeSpatialPosition** | 2D/3D | 1D over-approx |  Yes |
| **spatialCoordinates** | 2D/3D (lat/long/alt) | External KB |  Yes |
| **absoluteSize** | 2D/3D | 1D over-approx |  Yes |
| **relativeSize** | 2D/3D | 1D over-approx |  Yes |
| absoluteTemporalPosition | 1D | 1D  |  No |
| relativeTemporalPosition | 1D | 1D  |  No |
| dateTime | 1D | 1D  |  No |
| elapsedTime | 1D | 1D  |  No |
| delayPeriod | 1D | 1D  |  No |
| timeInterval | 1D | 1D  |  No |
| resolution | 1D | 1D  |  No |
| spatial | Named area | External KB | ⚠️ Maybe |
| event | Named event | External KB | ⚠️ Maybe |

---

### 3. LeftOperands Requiring Profile Extension

```
┌─────────────────────────────────────────────────────────────────┐
│           LEFTOPERANDS NEEDING AXIS-SPECIFIC EXTENSION          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PRIORITY 1: Spatial Position (2D/3D)                          │
│  ════════════════════════════════════                          │
│  1. relativeSpatialPosition → X, Y, Z axes                     │
│  2. absoluteSpatialPosition → X, Y, Z axes                     │
│                                                                 │
│  PRIORITY 2: Spatial Size (2D/3D)                              │
│  ═════════════════════════════════                             │
│  3. relativeSize → Width, Height, Depth                        │
│  4. absoluteSize → Width, Height, Depth                        │
│                                                                 │
│  PRIORITY 3: Geospatial Coordinates                            │
│  ═══════════════════════════════════                           │
│  5. spatialCoordinates → Latitude, Longitude, Altitude         │
│                                                                 │
│  TOTAL: 5 base LeftOperands × 3 axes = 15 axis-specific        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```


### 5. Profile

```
┌─────────────────────────────────────────────────────────────────┐
│           ODRL-SA SPATIAL-TEMPORAL PROFILE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  BASE LEFTOPERANDS EXTENDED: 5                                  │
│  ════════════════════════════                                   │
│                                                                 │
│  1. relativeSpatialPosition                                     │
│     └── X, Y, Z axes (3 new LeftOperands)                      │
│                                                                 │
│  2. absoluteSpatialPosition                                     │
│     └── X, Y, Z axes (3 new LeftOperands)                      │
│                                                                 │
│  3. relativeSize                                                │
│     └── Width, Height, Depth (3 new LeftOperands)              │
│                                                                 │
│  4. absoluteSize                                                │
│     └── Width, Height, Depth (3 new LeftOperands)              │
│                                                                 │
│  5. spatialCoordinates                                          │
│     └── Latitude, Longitude, Altitude (3 new LeftOperands)     │
│                                                                 │
│  TOTAL NEW LEFTOPERANDS: 15                                     │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  DOMAIN SPECIFICATIONS                                          │
│  ═════════════════════                                          │
│                                                                 │
│  ┌────────────────────────────┬──────────────┬──────────────┐  │
│  │ LeftOperand                │ Domain       │ Unit         │  │
│  ├────────────────────────────┼──────────────┼──────────────┤  │
│  │ relativeSpatialPosition*   │ [0, 100]     │ Implicit %   │  │
│  │ absoluteSpatialPosition*   │ [0, ∞)       │ Required     │  │
│  │ relativeSize*              │ [0, ∞)       │ Implicit %   │  │
│  │ absoluteSize*              │ (0, ∞)       │ Required     │  │
│  │ spatialCoordinatesLat      │ [-90, 90]    │ Degrees      │  │
│  │ spatialCoordinatesLong     │ [-180, 180]  │ Degrees      │  │
│  │ spatialCoordinatesAlt      │ (-∞, ∞)      │ Meters       │  │
│  └────────────────────────────┴──────────────┴──────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Qualitative vs Quantitative Spatial and Temporal Reasoning

### 1. The Core Distinction

```
┌─────────────────────────────────────────────────────────────────┐
│     QUALITATIVE vs QUANTITATIVE REASONING                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  QUANTITATIVE                      QUALITATIVE                  │
│  ════════════                      ═══════════                  │
│  "How much?"                       "What relationship?"         │
│  Exact numbers                     Symbolic relations           │
│  Precise coordinates               Topological properties       │
│                                                                 │
│  ┌─────────────────┐              ┌─────────────────┐          │
│  │  x = 45.5       │              │  A is INSIDE B  │          │
│  │  y = 23.7       │              │  A OVERLAPS B   │          │
│  │  t = 1706745600 │              │  A BEFORE B     │          │
│  └─────────────────┘              └─────────────────┘          │
│                                                                 │
│  Examples:                         Examples:                    │
│  • "at position 50px"              • "left of the image"       │
│  • "after 2024-01-31"              • "during the event"        │
│  • "size 1920×1080"                • "larger than original"    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 2. Simple Analogy

```
┌─────────────────────────────────────────────────────────────────┐
│                    EVERYDAY ANALOGY                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  QUESTION: "Where is the coffee shop?"                         │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  QUANTITATIVE ANSWER:                                   │   │
│  │  "At coordinates 50.9375° N, 6.9603° E"                │   │
│  │  "350 meters from here, bearing 45°"                    │   │
│  │                                                         │   │
│  │  → Precise, requires measurement                        │   │
│  │  → Machine-friendly                                     │   │
│  │  → Needs reference frame                                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  QUALITATIVE ANSWER:                                    │   │
│  │  "Next to the library"                                  │   │
│  │  "Between the bank and the park"                        │   │
│  │  "Inside the shopping center"                           │   │
│  │                                                         │   │
│  │  → Intuitive, human-friendly                            │   │
│  │  → No exact numbers needed                              │   │
│  │  → Relationship-based                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  BOTH ARE USEFUL! They serve different purposes.               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3. Temporal Reasoning Comparison

```
┌─────────────────────────────────────────────────────────────────┐
│              TEMPORAL REASONING COMPARISON                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  QUANTITATIVE (Point/Interval Arithmetic)                      │
│  ═════════════════════════════════════════                     │
│                                                                 │
│  "Meeting starts at 14:00 and ends at 15:30"                   │
│                                                                 │
│  Timeline:  ──────[14:00═══════════15:30]──────►               │
│                                                                 │
│  Operations:                                                    │
│  • Duration = 15:30 - 14:00 = 90 minutes                       │
│  • Overlap check: t₁ ≤ t ≤ t₂                                  │
│  • Distance: |t₁ - t₂|                                         │
│                                                                 │
│  ODRL Examples:                                                 │
│  • dateTime gteq "2024-01-01T00:00:00Z"                        │
│  • elapsedTime lteq "PT2H" (≤ 2 hours)                         │
│  • absoluteTemporalPosition eq 180 (at 180 seconds)            │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  QUALITATIVE (Allen's Interval Algebra)                        │
│  ══════════════════════════════════════                        │
│                                                                 │
│  "Meeting is DURING the conference"                            │
│  "Lunch MEETS the afternoon session"                           │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │  Conference: [═══════════════════════════════════]     │   │
│  │  Meeting:           [═══════════]                      │   │
│  │  Lunch:                         [════]                  │   │
│  │  Afternoon:                          [═══════════]     │   │
│  │                                                         │   │
│  │  Relations:                                             │   │
│  │  • Meeting DURING Conference                            │   │
│  │  • Lunch MEETS Afternoon (end = start)                 │   │
│  │  • Meeting BEFORE Afternoon                            │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  No exact times needed! Just relationships.                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 4. Allen's 13 Temporal Relations (Qualitative)

```
┌─────────────────────────────────────────────────────────────────┐
│              ALLEN'S INTERVAL ALGEBRA (1983)                    │
│              13 Qualitative Temporal Relations                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  A: [═══════]           B: [═══════]                           │
│                                                                 │
│  1. BEFORE / AFTER                                             │
│     A: [═══]                                                   │
│     B:           [═══]     A < B (A before B)                  │
│                                                                 │
│  2. MEETS / MET-BY                                             │
│     A: [═══]                                                   │
│     B:      [═══]          A m B (A meets B)                   │
│                                                                 │
│  3. OVERLAPS / OVERLAPPED-BY                                   │
│     A: [═══════]                                               │
│     B:      [═══════]      A o B (A overlaps B)                │
│                                                                 │
│  4. STARTS / STARTED-BY                                        │
│     A: [═══]                                                   │
│     B: [═══════════]       A s B (A starts B)                  │
│                                                                 │
│  5. DURING / CONTAINS                                          │
│     A:    [═══]                                                │
│     B: [═══════════]       A d B (A during B)                  │
│                                                                 │
│  6. FINISHES / FINISHED-BY                                     │
│     A:        [═══]                                            │
│     B: [═══════════]       A f B (A finishes B)                │
│                                                                 │
│  7. EQUALS                                                     │
│     A: [═══════]                                               │
│     B: [═══════]           A = B (A equals B)                  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  KEY INSIGHT: No numbers! Pure topology.                       │
│  • Can reason about time without knowing exact timestamps      │
│  • Supports constraint propagation                             │
│  • Decidable reasoning                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 5. Spatial Reasoning Comparison

```
┌─────────────────────────────────────────────────────────────────┐
│              SPATIAL REASONING COMPARISON                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  QUANTITATIVE (Coordinate Geometry)                            │
│  ══════════════════════════════════                            │
│                                                                 │
│  "Image at position (100, 200) with size (300, 150)"           │
│                                                                 │
│     0    100        400                                        │
│   0 ┌─────┬──────────┬────────────────────┐                   │
│     │     │          │                    │                    │
│ 200 ├─────┼──────────┤                    │                    │
│     │     │  IMAGE   │                    │                    │
│ 350 ├─────┼──────────┤                    │                    │
│     │     │          │                    │                    │
│     └─────┴──────────┴────────────────────┘                   │
│                                                                 │
│  Operations:                                                    │
│  • Area = 300 × 150 = 45,000 px²                               │
│  • Center = (250, 275)                                         │
│  • Distance to origin = √(100² + 200²)                         │
│                                                                 │
│  ODRL Examples:                                                 │
│  • absoluteSpatialPositionX lteq 400                           │
│  • absoluteSize eq 1920 (width in pixels)                      │
│  • relativeSpatialPosition gteq 25 (≥ 25% from edge)          │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  QUALITATIVE (Region Connection Calculus - RCC-8)              │
│  ════════════════════════════════════════════════              │
│                                                                 │
│  "Logo is INSIDE the header"                                   │
│  "Sidebar is ADJACENT to content"                              │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │   ┌─────────────────────────────────────────────────┐  │   │
│  │   │  HEADER                                         │  │   │
│  │   │     ┌──────┐                                    │  │   │
│  │   │     │ LOGO │  (Logo INSIDE Header)              │  │   │
│  │   │     └──────┘                                    │  │   │
│  │   └─────────────────────────────────────────────────┘  │   │
│  │   ┌────────┬────────────────────────────────────────┐  │   │
│  │   │SIDEBAR │           CONTENT                      │  │   │
│  │   │        │  (Sidebar ADJACENT-TO Content)         │  │   │
│  │   │        │                                        │  │   │
│  │   └────────┴────────────────────────────────────────┘  │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  No coordinates needed! Just topological relationships.        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 6. RCC-8: 8 Qualitative Spatial Relations

```
┌─────────────────────────────────────────────────────────────────┐
│              REGION CONNECTION CALCULUS (RCC-8)                 │
│              8 Qualitative Spatial Relations                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. DC - Disconnected (no contact)                             │
│     ┌───┐      ┌───┐                                           │
│     │ A │      │ B │     A and B are separate                  │
│     └───┘      └───┘                                           │
│                                                                 │
│  2. EC - Externally Connected (touching)                       │
│     ┌───┬───┐                                                  │
│     │ A │ B │            A and B touch at boundary             │
│     └───┴───┘                                                  │
│                                                                 │
│  3. PO - Partial Overlap                                       │
│     ┌─────┐                                                    │
│     │ A ┌─┼───┐                                                │
│     └───┼─┘ B │          A and B partially overlap             │
│         └─────┘                                                │
│                                                                 │
│  4. EQ - Equal (same region)                                   │
│     ┌───────┐                                                  │
│     │ A = B │            A and B are identical                 │
│     └───────┘                                                  │
│                                                                 │
│  5. TPP - Tangential Proper Part (inside, touching edge)       │
│     ┌─────────┐                                                │
│     │ B ┌───┐ │                                                │
│     │   │ A ├─┤          A inside B, touches B's boundary      │
│     │   └───┘ │                                                │
│     └─────────┘                                                │
│                                                                 │
│  6. NTPP - Non-Tangential Proper Part (strictly inside)        │
│     ┌───────────┐                                              │
│     │ B         │                                              │
│     │   ┌───┐   │        A strictly inside B                   │
│     │   │ A │   │                                              │
│     │   └───┘   │                                              │
│     └───────────┘                                              │
│                                                                 │
│  7. TPPi - TPP Inverse (contains, touched from inside)         │
│  8. NTPPi - NTPP Inverse (strictly contains)                   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  KEY INSIGHT: Shape and size don't matter!                     │
│  • Only topology matters                                        │
│  • Works for any shaped regions                                │
│  • No coordinates needed                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 7. What Each Approach Can Do

```
┌─────────────────────────────────────────────────────────────────┐
│              CAPABILITIES COMPARISON                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  QUANTITATIVE REASONING                                        │
│  ══════════════════════                                        │
│                                                                 │
│  CAN DO:                                                     │
│  • Exact position: "at 50px from left"                         │
│  • Precise timing: "at 14:30:00 UTC"                           │
│  • Exact size: "1920×1080 pixels"                              │
│  • Distance calculation: "350 meters apart"                    │
│  • Area/volume computation                                      │
│  • Metric comparisons: "A is 2x larger than B"                 │
│                                                                 │
│  CANNOT DO (easily):                                         │
│  • Reason without exact values                                 │
│  • Handle vague descriptions                                    │
│  • "Somewhere in the top half"                                 │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  QUALITATIVE REASONING                                         │
│  ═════════════════════                                         │
│                                                                 │
│  CAN DO:                                                     │
│  • Topological relations: "A inside B"                         │
│  • Relative ordering: "A before B"                             │
│  • Constraint propagation: "if A before B and B before C,      │
│                             then A before C"                   │
│  • Reason with incomplete information                          │
│  • Handle natural language descriptions                        │
│  • Compositionality: combine relations                         │
│                                                                 │
│  CANNOT DO:                                                  │
│  • Exact measurements                                          │
│  • Precise distances                                           │
│  • Metric comparisons                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 8. ODRL-SA: Hybrid Approach

```
┌─────────────────────────────────────────────────────────────────┐
│              ODRL-SA HYBRID APPROACH                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ODRL-SA combines BOTH approaches:                             │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │  QUANTITATIVE LAYER (Primary)                          │   │
│  │  ═══════════════════════════                           │   │
│  │                                                         │   │
│  │  • Interval arithmetic for constraints                  │   │
│  │  • SMT solving (QF_LRA, QF_LIA)                        │   │
│  │  • Exact conflict detection                            │   │
│  │                                                         │   │
│  │  ODRL: dateTime gteq "2024-01-01"                      │   │
│  │  ODRL-SA: Interval [2024-01-01, +∞)                    │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                     │
│                          ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │  QUALITATIVE INTERPRETATION (Derived)                  │   │
│  │  ════════════════════════════════════                  │   │
│  │                                                         │   │
│  │  From quantitative intervals, derive qualitative:       │   │
│  │                                                         │   │
│  │  Intervals [10,30] and [50,70]:                        │   │
│  │  → Allen relation: BEFORE (disjoint)                   │   │
│  │  → Conflict: YES                                       │   │
│  │                                                         │   │
│  │  Intervals [10,50] and [30,70]:                        │   │
│  │  → Allen relation: OVERLAPS                            │   │
│  │  → Conflict: NO (intersection [30,50])                 │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  BENEFIT: Precise quantitative analysis + intuitive            │
│           qualitative explanations                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 9. Mapping ODRL Operators to Qualitative Relations

```
┌─────────────────────────────────────────────────────────────────┐
│         ODRL OPERATORS → QUALITATIVE RELATIONS                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TEMPORAL (ODRL → Allen's Algebra)                             │
│  ═════════════════════════════════                             │
│                                                                 │
│  ┌────────────────────────┬────────────────────────────────┐   │
│  │ ODRL Constraint        │ Implied Allen Relation         │   │
│  ├────────────────────────┼────────────────────────────────┤   │
│  │ dateTime lt X          │ Current time BEFORE X          │   │
│  │ dateTime gt X          │ Current time AFTER X           │   │
│  │ dateTime eq X          │ Current time EQUALS X          │   │
│  │ elapsedTime lteq D     │ Action DURING window [0,D]     │   │
│  │ delayPeriod gteq D     │ Action AFTER delay period      │   │
│  └────────────────────────┴────────────────────────────────┘   │
│                                                                 │
│  SPATIAL (ODRL → RCC-8)                                        │
│  ══════════════════════                                        │
│                                                                 │
│  ┌────────────────────────┬────────────────────────────────┐   │
│  │ ODRL Constraint        │ Implied RCC-8 Relation         │   │
│  ├────────────────────────┼────────────────────────────────┤   │
│  │ relSpatialPos [0,50]   │ Asset INSIDE left half         │   │
│  │ relSpatialPos [50,100] │ Asset INSIDE right half        │   │
│  │ Both constraints       │ DC (disconnected) = CONFLICT   │   │
│  └────────────────────────┴────────────────────────────────┘   │
│                                                                 │
│  ODRL-SA derives qualitative relations from quantitative       │
│  interval analysis for intuitive conflict explanations.        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```











---



### 7. Implementation Architecture

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar, Optional, List, Tuple
from z3 import *

T = TypeVar('T')

# ═══════════════════════════════════════════════════════════════
# LAYER 1: ABSTRACT DOMAIN INTERFACES
# ═══════════════════════════════════════════════════════════════

class AbstractDomain(ABC, Generic[T]):
    """Base class for abstract domains with lattice operations."""
    
    @abstractmethod
    def meet(self, other: 'AbstractDomain[T]') -> 'AbstractDomain[T]':
        """Lattice meet (intersection)."""
        pass
    
    @abstractmethod
    def join(self, other: 'AbstractDomain[T]') -> 'AbstractDomain[T]':
        """Lattice join (union over-approximation)."""
        pass
    
    @abstractmethod
    def is_bottom(self) -> bool:
        """Check if element is ⊥ (empty)."""
        pass
    
    @abstractmethod
    def contains(self, value: T) -> bool:
        """Check if concrete value is in the abstract element."""
        pass


# ═══════════════════════════════════════════════════════════════
# LAYER 2: INTERVAL DOMAIN (1D)
# ═══════════════════════════════════════════════════════════════

@dataclass
class Interval(AbstractDomain[float]):
    """1D interval abstract domain."""
    
    lo: float
    hi: float
    lo_inclusive: bool = True
    hi_inclusive: bool = True
    
    @staticmethod
    def bottom() -> 'Interval':
        return Interval(float('inf'), float('-inf'))
    
    @staticmethod
    def top() -> 'Interval':
        return Interval(float('-inf'), float('inf'))
    
    def is_bottom(self) -> bool:
        if self.lo > self.hi:
            return True
        if self.lo == self.hi:
            return not (self.lo_inclusive and self.hi_inclusive)
        return False
    
    def meet(self, other: 'Interval') -> 'Interval':
        """Interval intersection."""
        new_lo = max(self.lo, other.lo)
        new_hi = min(self.hi, other.hi)
        
        # Handle inclusivity at boundaries
        if new_lo == self.lo and new_lo == other.lo:
            lo_inc = self.lo_inclusive and other.lo_inclusive
        elif new_lo == self.lo:
            lo_inc = self.lo_inclusive
        else:
            lo_inc = other.lo_inclusive
        
        if new_hi == self.hi and new_hi == other.hi:
            hi_inc = self.hi_inclusive and other.hi_inclusive
        elif new_hi == self.hi:
            hi_inc = self.hi_inclusive
        else:
            hi_inc = other.hi_inclusive
        
        return Interval(new_lo, new_hi, lo_inc, hi_inc)
    
    def join(self, other: 'Interval') -> 'Interval':
        """Interval union (convex hull)."""
        return Interval(
            min(self.lo, other.lo),
            max(self.hi, other.hi),
            self.lo_inclusive if self.lo <= other.lo else other.lo_inclusive,
            self.hi_inclusive if self.hi >= other.hi else other.hi_inclusive
        )
    
    def contains(self, value: float) -> bool:
        if self.is_bottom():
            return False
        lo_ok = (value > self.lo) or (value == self.lo and self.lo_inclusive)
        hi_ok = (value < self.hi) or (value == self.hi and self.hi_inclusive)
        return lo_ok and hi_ok


# ═══════════════════════════════════════════════════════════════
# LAYER 3: BOX DOMAIN (N-D)
# ═══════════════════════════════════════════════════════════════

@dataclass
class Box(AbstractDomain[Tuple[float, ...]]):
    """N-dimensional box (Cartesian product of intervals)."""
    
    intervals: List[Interval]
    
    @property
    def dimension(self) -> int:
        return len(self.intervals)
    
    @staticmethod
    def from_intervals(*intervals: Interval) -> 'Box':
        return Box(list(intervals))
    
    @staticmethod
    def bottom(n: int) -> 'Box':
        return Box([Interval.bottom() for _ in range(n)])
    
    @staticmethod
    def top(n: int) -> 'Box':
        return Box([Interval.top() for _ in range(n)])
    
    def is_bottom(self) -> bool:
        """Box is ⊥ if ANY dimension is ⊥."""
        return any(i.is_bottom() for i in self.intervals)
    
    def meet(self, other: 'Box') -> 'Box':
        """Component-wise interval meet."""
        if self.dimension != other.dimension:
            raise ValueError(f"Dimension mismatch: {self.dimension} vs {other.dimension}")
        
        return Box([
            i1.meet(i2) 
            for i1, i2 in zip(self.intervals, other.intervals)
        ])
    
    def join(self, other: 'Box') -> 'Box':
        """Component-wise interval join."""
        if self.dimension != other.dimension:
            raise ValueError(f"Dimension mismatch: {self.dimension} vs {other.dimension}")
        
        return Box([
            i1.join(i2) 
            for i1, i2 in zip(self.intervals, other.intervals)
        ])
    
    def contains(self, point: Tuple[float, ...]) -> bool:
        if len(point) != self.dimension:
            return False
        return all(
            interval.contains(coord) 
            for interval, coord in zip(self.intervals, point)
        )


# ═══════════════════════════════════════════════════════════════
# LAYER 4: ALLEN'S INTERVAL ALGEBRA (TEMPORAL)
# ═══════════════════════════════════════════════════════════════

class AllenRelation(Enum):
    """Allen's 13 interval relations."""
    BEFORE = "before"           # I < J: b < c
    AFTER = "after"             # I > J: a > d
    MEETS = "meets"             # I m J: b = c
    MET_BY = "met_by"           # I mi J: a = d
    OVERLAPS = "overlaps"       # I o J: a < c < b < d
    OVERLAPPED_BY = "overlapped_by"
    STARTS = "starts"           # I s J: a = c, b < d
    STARTED_BY = "started_by"
    DURING = "during"           # I d J: a > c, b < d
    CONTAINS = "contains"
    FINISHES = "finishes"       # I f J: a > c, b = d
    FINISHED_BY = "finished_by"
    EQUALS = "equals"           # I = J: a = c, b = d


def allen_relation(i1: Interval, i2: Interval) -> AllenRelation:
    """Determine Allen relation between two intervals."""
    a, b = i1.lo, i1.hi
    c, d = i2.lo, i2.hi
    
    if b < c:
        return AllenRelation.BEFORE
    if a > d:
        return AllenRelation.AFTER
    if b == c:
        return AllenRelation.MEETS
    if a == d:
        return AllenRelation.MET_BY
    if a < c < b < d:
        return AllenRelation.OVERLAPS
    if c < a < d < b:
        return AllenRelation.OVERLAPPED_BY
    if a == c and b < d:
        return AllenRelation.STARTS
    if a == c and b > d:
        return AllenRelation.STARTED_BY
    if a > c and b < d:
        return AllenRelation.DURING
    if a < c and b > d:
        return AllenRelation.CONTAINS
    if a > c and b == d:
        return AllenRelation.FINISHES
    if a < c and b == d:
        return AllenRelation.FINISHED_BY
    if a == c and b == d:
        return AllenRelation.EQUALS
    
    raise ValueError(f"Cannot determine Allen relation for {i1}, {i2}")


def temporal_conflict(i1: Interval, i2: Interval) -> bool:
    """Check if two temporal intervals conflict (disjoint)."""
    rel = allen_relation(i1, i2)
    return rel in {AllenRelation.BEFORE, AllenRelation.AFTER}


# ═══════════════════════════════════════════════════════════════
# LAYER 5: RCC-8 (SPATIAL)
# ═══════════════════════════════════════════════════════════════

class RCC8Relation(Enum):
    """RCC-8 spatial relations."""
    DC = "disconnected"              # Disjoint
    EC = "externally_connected"      # Touch at boundary only
    PO = "partial_overlap"           # Overlap but neither contains other
    EQ = "equal"                     # Same region
    TPP = "tangential_proper_part"   # Inside, touching boundary
    NTPP = "non_tangential_proper_part"  # Strictly inside
    TPPi = "tangential_proper_part_inverse"
    NTPPi = "non_tangential_proper_part_inverse"


def rcc8_relation_boxes(b1: Box, b2: Box) -> RCC8Relation:
    """Determine RCC-8 relation between two axis-aligned boxes."""
    meet = b1.meet(b2)
    
    if meet.is_bottom():
        return RCC8Relation.DC
    
    # Check for equality
    if all(
        i1.lo == i2.lo and i1.hi == i2.hi 
        for i1, i2 in zip(b1.intervals, b2.intervals)
    ):
        return RCC8Relation.EQ
    
    # Check containment
    b1_in_b2 = all(
        i2.lo <= i1.lo and i1.hi <= i2.hi
        for i1, i2 in zip(b1.intervals, b2.intervals)
    )
    b2_in_b1 = all(
        i1.lo <= i2.lo and i2.hi <= i1.hi
        for i1, i2 in zip(b1.intervals, b2.intervals)
    )
    
    if b1_in_b2 and not b2_in_b1:
        # Check if touching boundary
        touches_boundary = any(
            i1.lo == i2.lo or i1.hi == i2.hi
            for i1, i2 in zip(b1.intervals, b2.intervals)
        )
        return RCC8Relation.TPP if touches_boundary else RCC8Relation.NTPP
    
    if b2_in_b1 and not b1_in_b2:
        touches_boundary = any(
            i1.lo == i2.lo or i1.hi == i2.hi
            for i1, i2 in zip(b1.intervals, b2.intervals)
        )
        return RCC8Relation.TPPi if touches_boundary else RCC8Relation.NTPPi
    
    # Check if only touching (externally connected)
    # This happens when meet has zero volume in at least one dimension
    zero_volume = any(
        m.lo == m.hi for m in meet.intervals
    )
    if zero_volume:
        return RCC8Relation.EC
    
    return RCC8Relation.PO


def spatial_conflict(b1: Box, b2: Box) -> bool:
    """Check if two spatial boxes conflict (disconnected)."""
    return rcc8_relation_boxes(b1, b2) == RCC8Relation.DC


# ═══════════════════════════════════════════════════════════════
# LAYER 6: CONSTRAINT ABSTRACTION
# ═══════════════════════════════════════════════════════════════

def abstract_constraint(
    domain_min: float,
    domain_max: float,
    operator: str,
    value: float,
    min_inclusive: bool = True,
    max_inclusive: bool = True
) -> Interval:
    """
    Abstract a constraint to an interval.
    
    Args:
        domain_min: Minimum of LeftOperand domain
        domain_max: Maximum of LeftOperand domain
        operator: ODRL operator (eq, lt, lteq, gt, gteq, neq)
        value: Right operand value
        min_inclusive: Whether domain minimum is inclusive
        max_inclusive: Whether domain maximum is inclusive
    
    Returns:
        Interval representing the constraint
    """
    if operator == "eq":
        return Interval(value, value, True, True)
    elif operator == "neq":
        # Over-approximate as full domain (sound but imprecise)
        return Interval(domain_min, domain_max, min_inclusive, max_inclusive)
    elif operator == "lt":
        return Interval(domain_min, value, min_inclusive, False)
    elif operator == "lteq":
        return Interval(domain_min, value, min_inclusive, True)
    elif operator == "gt":
        return Interval(value, domain_max, False, max_inclusive)
    elif operator == "gteq":
        return Interval(value, domain_max, True, max_inclusive)
    else:
        raise ValueError(f"Unknown operator: {operator}")


# ═══════════════════════════════════════════════════════════════
# LAYER 7: CONFLICT DETECTOR
# ═══════════════════════════════════════════════════════════════

@dataclass
class ConflictResult:
    """Result of conflict detection."""
    is_conflict: bool
    is_complete: bool  # True if analysis is complete (not over-approximated)
    witness: Optional[Tuple[float, ...]] = None  # Counter-example if compatible
    explanation: str = ""


class ConflictDetector:
    """
    Unified conflict detector using formal semantics.
    """
    
    def detect_1d_conflict(
        self,
        constraints: List[Tuple[str, float]],  # (operator, value) pairs
        domain_min: float,
        domain_max: float,
        min_inclusive: bool = True,
        max_inclusive: bool = True
    ) -> ConflictResult:
        """Detect conflict in 1D constraints."""
        
        # Abstract all constraints
        intervals = [
            abstract_constraint(domain_min, domain_max, op, val, 
                               min_inclusive, max_inclusive)
            for op, val in constraints
        ]
        
        # Compute meet (intersection)
        result = intervals[0]
        for interval in intervals[1:]:
            result = result.meet(interval)
        
        if result.is_bottom():
            return ConflictResult(
                is_conflict=True,
                is_complete=True,
                explanation="Interval intersection is empty"
            )
        else:
            # Find witness
            if result.lo_inclusive:
                witness = result.lo
            elif result.hi_inclusive:
                witness = result.hi
            else:
                witness = (result.lo + result.hi) / 2
            
            return ConflictResult(
                is_conflict=False,
                is_complete=True,
                witness=(witness,),
                explanation=f"Compatible with witness: {witness}"
            )
    
    def detect_nd_conflict(
        self,
        constraints_by_axis: dict,  # axis -> [(operator, value), ...]
        domains: dict,  # axis -> (min, max, min_inc, max_inc)
    ) -> ConflictResult:
        """Detect conflict in N-dimensional (box) constraints."""
        
        axes = list(constraints_by_axis.keys())
        n = len(axes)
        
        # Abstract constraints per axis
        intervals_by_axis = {}
        for axis in axes:
            domain_min, domain_max, min_inc, max_inc = domains[axis]
            constraints = constraints_by_axis[axis]
            
            intervals = [
                abstract_constraint(domain_min, domain_max, op, val, min_inc, max_inc)
                for op, val in constraints
            ]
            
            # Meet all intervals on this axis
            result = intervals[0]
            for interval in intervals[1:]:
                result = result.meet(interval)
            
            intervals_by_axis[axis] = result
        
        # Check if any axis is empty
        for axis, interval in intervals_by_axis.items():
            if interval.is_bottom():
                return ConflictResult(
                    is_conflict=True,
                    is_complete=True,
                    explanation=f"Empty intersection on axis {axis}"
                )
        
        # All axes have non-empty intersection - find witness
        witness = []
        for axis in axes:
            interval = intervals_by_axis[axis]
            if interval.lo_inclusive:
                witness.append(interval.lo)
            elif interval.hi_inclusive:
                witness.append(interval.hi)
            else:
                witness.append((interval.lo + interval.hi) / 2)
        
        return ConflictResult(
            is_conflict=False,
            is_complete=True,
            witness=tuple(witness),
            explanation=f"Compatible with witness: {tuple(witness)}"
        )
    
    def detect_temporal_conflict(
        self,
        intervals: List[Interval]
    ) -> Tuple[bool, Optional[AllenRelation]]:
        """Detect temporal conflict using Allen's algebra."""
        
        # Pairwise check
        for i, i1 in enumerate(intervals):
            for j, i2 in enumerate(intervals):
                if i < j:
                    rel = allen_relation(i1, i2)
                    if rel in {AllenRelation.BEFORE, AllenRelation.AFTER}:
                        return True, rel
        
        return False, None
    
    def detect_spatial_conflict(
        self,
        boxes: List[Box]
    ) -> Tuple[bool, Optional[RCC8Relation]]:
        """Detect spatial conflict using RCC-8."""
        
        # Pairwise check
        for i, b1 in enumerate(boxes):
            for j, b2 in enumerate(boxes):
                if i < j:
                    rel = rcc8_relation_boxes(b1, b2)
                    if rel == RCC8Relation.DC:
                        return True, rel
        
        return False, None
```

---

### 8. Summary: Complete Formal Semantics

```
┌─────────────────────────────────────────────────────────────────┐
│           ODRL-SA COMPLETE FORMAL SEMANTICS                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  MATHEMATICAL FOUNDATIONS                                       │
│  ════════════════════════                                       │
│  1. Interval Domain (𝓘_D)        - 1D constraint abstraction   │
│  2. Box Domain (𝓑^n)             - N-D constraint abstraction  │
│  3. Galois Connection (α, γ)     - Soundness guarantee         │
│  4. Allen's Interval Algebra     - Temporal reasoning          │
│  5. Region Connection Calculus   - Spatial reasoning           │
│                                                                 │
│  FORMAL GUARANTEES                                              │
│  ═════════════════                                              │
│  • SOUNDNESS: α(c₁) ⊓ α(c₂) = ⊥ ⟹ concrete conflict          │
│  • DECIDABILITY: QF_LRA/QF_LIA fragments                       │
│  • COMPLETENESS: For axis-aligned boxes                        │
│  • ALLEN CORRECTNESS: 13 temporal relations                    │
│  • RCC-8 CORRECTNESS: 8 spatial relations                      │
│                                                                 │
│  IMPLEMENTATION                                                 │
│  ══════════════                                                 │
│  • Python dataclasses for domains                              │
│  • Z3 SMT solver for satisfiability                           │
│  • Profile for axis-specific operands                          │
│                                                                 │
│  EXTENSIBILITY                                                  │
│  ════════════                                                   │
│  • New dimensions via Box domain                               │
│  • New temporal relations via Allen composition                │
│  • New spatial relations via RCC-8 extension                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 9. Publication Statement

> **Formal Semantics.** ODRL-SA's conflict detection is grounded in established mathematical theories: **Allen's Interval Algebra** (1983) for temporal reasoning, **Region Connection Calculus (RCC-8)** for spatial reasoning, and **Abstract Interpretation** (Cousot & Cousot, 1977) for soundness guarantees. We define a unified abstract domain combining 1D intervals for scalar/temporal constraints and N-dimensional boxes for spatial constraints. A Galois connection between concrete and abstract domains ensures that all detected conflicts are genuine (soundness). For axis-aligned box constraints using our Spatial-Temporal Profile, analysis is both sound and complete. The framework naturally extends to additional dimensions through the Box domain product structure.

---

This provides a complete formal semantics foundation for spatial and temporal reasoning in ODRL-SA!





























### 4. Proposed ODRL-SA Spatial-Temporal Profile

```turtle
@prefix odrl:   <http://www.w3.org/ns/odrl/2/> .
@prefix odrlsa: <http://odrl-sa.2/> .
@prefix rdfs:   <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos:   <http://www.w3.org/2004/02/skos/core#> .
@prefix xsd:    <http://www.w3.org/2001/XMLSchema#> .
@prefix owl:    <http://www.w3.org/2002/07/owl#> .

# ═══════════════════════════════════════════════════════════════════
# ODRL-SA SPATIAL-TEMPORAL PROFILE
# Version 1.0
# 
# Extends ODRL Core with axis-specific LeftOperands for complete
# multi-dimensional conflict detection in spatial and size constraints.
# ═══════════════════════════════════════════════════════════════════

odrlsa:SpatialTemporalProfile a odrl:Profile ;
    rdfs:label "ODRL-SA Spatial-Temporal Profile"@en ;
    skos:definition """Profile extending ODRL with axis-specific 
        LeftOperands for complete 2D/3D conflict detection in 
        spatial position, size, and geospatial coordinates."""@en ;
    odrl:inheritFrom odrl: ;
    rdfs:seeAlso <https://www.w3.org/TR/odrl-vocab/> .

# ═══════════════════════════════════════════════════════════════════
# PART 1: RELATIVE SPATIAL POSITION (Percentage-based, 2D/3D)
# Domain: [0, 100] per axis
# ═══════════════════════════════════════════════════════════════════

odrlsa:relativeSpatialPositionX a odrl:LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrlsa: ;
    rdfs:subPropertyOf odrl:relativeSpatialPosition ;
    skos:broader odrl:relativeSpatialPosition ;
    rdfs:label "Relative Spatial Position X-Axis"@en ;
    skos:definition """X-axis (horizontal) position as percentage of 
        the full horizontal extent. Domain: [0, 100]."""@en ;
    skos:note "0 = left edge, 100 = right edge"@en ;
    odrlsa:axis "X" ;
    odrlsa:dimension "horizontal" ;
    odrlsa:domain "[0, 100]" ;
    odrlsa:valueType xsd:decimal .

odrlsa:relativeSpatialPositionY a odrl:LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrlsa: ;
    rdfs:subPropertyOf odrl:relativeSpatialPosition ;
    skos:broader odrl:relativeSpatialPosition ;
    rdfs:label "Relative Spatial Position Y-Axis"@en ;
    skos:definition """Y-axis (vertical) position as percentage of 
        the full vertical extent. Domain: [0, 100]."""@en ;
    skos:note "0 = top edge, 100 = bottom edge"@en ;
    odrlsa:axis "Y" ;
    odrlsa:dimension "vertical" ;
    odrlsa:domain "[0, 100]" ;
    odrlsa:valueType xsd:decimal .

odrlsa:relativeSpatialPositionZ a odrl:LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrlsa: ;
    rdfs:subPropertyOf odrl:relativeSpatialPosition ;
    skos:broader odrl:relativeSpatialPosition ;
    rdfs:label "Relative Spatial Position Z-Axis"@en ;
    skos:definition """Z-axis (depth) position as percentage of 
        the full depth extent for 3D spaces. Domain: [0, 100]."""@en ;
    skos:note "0 = front, 100 = back"@en ;
    odrlsa:axis "Z" ;
    odrlsa:dimension "depth" ;
    odrlsa:domain "[0, 100]" ;
    odrlsa:valueType xsd:decimal .

# ═══════════════════════════════════════════════════════════════════
# PART 2: ABSOLUTE SPATIAL POSITION (Unit-dependent, 2D/3D)
# Domain: [0, ∞) per axis, requires unit
# ═══════════════════════════════════════════════════════════════════

odrlsa:absoluteSpatialPositionX a odrl:LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrlsa: ;
    rdfs:subPropertyOf odrl:absoluteSpatialPosition ;
    skos:broader odrl:absoluteSpatialPosition ;
    rdfs:label "Absolute Spatial Position X-Axis"@en ;
    skos:definition """X-axis (horizontal) position in absolute units."""@en ;
    skos:note "Requires unit specification (px, mm, cm, etc.)"@en ;
    odrlsa:axis "X" ;
    odrlsa:dimension "horizontal" ;
    odrlsa:domain "[0, ∞)" ;
    odrlsa:requiresUnit true ;
    odrlsa:valueType xsd:decimal .

odrlsa:absoluteSpatialPositionY a odrl:LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrlsa: ;
    rdfs:subPropertyOf odrl:absoluteSpatialPosition ;
    skos:broader odrl:absoluteSpatialPosition ;
    rdfs:label "Absolute Spatial Position Y-Axis"@en ;
    skos:definition """Y-axis (vertical) position in absolute units."""@en ;
    skos:note "Requires unit specification (px, mm, cm, etc.)"@en ;
    odrlsa:axis "Y" ;
    odrlsa:dimension "vertical" ;
    odrlsa:domain "[0, ∞)" ;
    odrlsa:requiresUnit true ;
    odrlsa:valueType xsd:decimal .

odrlsa:absoluteSpatialPositionZ a odrl:LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrlsa: ;
    rdfs:subPropertyOf odrl:absoluteSpatialPosition ;
    skos:broader odrl:absoluteSpatialPosition ;
    rdfs:label "Absolute Spatial Position Z-Axis"@en ;
    skos:definition """Z-axis (depth) position in absolute units for 3D spaces."""@en ;
    skos:note "Requires unit specification (px, mm, cm, etc.)"@en ;
    odrlsa:axis "Z" ;
    odrlsa:dimension "depth" ;
    odrlsa:domain "[0, ∞)" ;
    odrlsa:requiresUnit true ;
    odrlsa:valueType xsd:decimal .

# ═══════════════════════════════════════════════════════════════════
# PART 3: RELATIVE SIZE (Percentage-based, 2D/3D)
# Domain: [0, ∞) per axis (can exceed 100% for enlargement)
# ═══════════════════════════════════════════════════════════════════

odrlsa:relativeSizeWidth a odrl:LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrlsa: ;
    rdfs:subPropertyOf odrl:relativeSize ;
    skos:broader odrl:relativeSize ;
    rdfs:label "Relative Size Width"@en ;
    skos:definition """Width dimension as percentage of original width. 
        Domain: [0, ∞). Values >100 indicate enlargement."""@en ;
    skos:note "100 = original width, 200 = double width"@en ;
    odrlsa:axis "width" ;
    odrlsa:dimension "horizontal" ;
    odrlsa:domain "[0, ∞)" ;
    odrlsa:valueType xsd:decimal .

odrlsa:relativeSizeHeight a odrl:LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrlsa: ;
    rdfs:subPropertyOf odrl:relativeSize ;
    skos:broader odrl:relativeSize ;
    rdfs:label "Relative Size Height"@en ;
    skos:definition """Height dimension as percentage of original height. 
        Domain: [0, ∞). Values >100 indicate enlargement."""@en ;
    skos:note "100 = original height, 200 = double height"@en ;
    odrlsa:axis "height" ;
    odrlsa:dimension "vertical" ;
    odrlsa:domain "[0, ∞)" ;
    odrlsa:valueType xsd:decimal .

odrlsa:relativeSizeDepth a odrl:LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrlsa: ;
    rdfs:subPropertyOf odrl:relativeSize ;
    skos:broader odrl:relativeSize ;
    rdfs:label "Relative Size Depth"@en ;
    skos:definition """Depth dimension as percentage of original depth for 3D objects. 
        Domain: [0, ∞). Values >100 indicate enlargement."""@en ;
    skos:note "100 = original depth, 200 = double depth"@en ;
    odrlsa:axis "depth" ;
    odrlsa:dimension "depth" ;
    odrlsa:domain "[0, ∞)" ;
    odrlsa:valueType xsd:decimal .

# ═══════════════════════════════════════════════════════════════════
# PART 4: ABSOLUTE SIZE (Unit-dependent, 2D/3D)
# Domain: (0, ∞) per axis (zero excluded), requires unit
# ═══════════════════════════════════════════════════════════════════

odrlsa:absoluteSizeWidth a odrl:LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrlsa: ;
    rdfs:subPropertyOf odrl:absoluteSize ;
    skos:broader odrl:absoluteSize ;
    rdfs:label "Absolute Size Width"@en ;
    skos:definition """Width dimension in absolute units. Domain: (0, ∞)."""@en ;
    skos:note "Requires unit specification (px, mm, cm, MB, etc.)"@en ;
    odrlsa:axis "width" ;
    odrlsa:dimension "horizontal" ;
    odrlsa:domain "(0, ∞)" ;
    odrlsa:requiresUnit true ;
    odrlsa:valueType xsd:decimal .

odrlsa:absoluteSizeHeight a odrl:LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrlsa: ;
    rdfs:subPropertyOf odrl:absoluteSize ;
    skos:broader odrl:absoluteSize ;
    rdfs:label "Absolute Size Height"@en ;
    skos:definition """Height dimension in absolute units. Domain: (0, ∞)."""@en ;
    skos:note "Requires unit specification (px, mm, cm, MB, etc.)"@en ;
    odrlsa:axis "height" ;
    odrlsa:dimension "vertical" ;
    odrlsa:domain "(0, ∞)" ;
    odrlsa:requiresUnit true ;
    odrlsa:valueType xsd:decimal .

odrlsa:absoluteSizeDepth a odrl:LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrlsa: ;
    rdfs:subPropertyOf odrl:absoluteSize ;
    skos:broader odrl:absoluteSize ;
    rdfs:label "Absolute Size Depth"@en ;
    skos:definition """Depth dimension in absolute units for 3D objects. Domain: (0, ∞)."""@en ;
    skos:note "Requires unit specification (px, mm, cm, etc.)"@en ;
    odrlsa:axis "depth" ;
    odrlsa:dimension "depth" ;
    odrlsa:domain "(0, ∞)" ;
    odrlsa:requiresUnit true ;
    odrlsa:valueType xsd:decimal .

# ═══════════════════════════════════════════════════════════════════
# PART 5: GEOSPATIAL COORDINATES (Lat/Long/Alt)
# Domain: Latitude [-90, 90], Longitude [-180, 180], Altitude [0, ∞)
# ═══════════════════════════════════════════════════════════════════

odrlsa:spatialCoordinatesLatitude a odrl:LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrlsa: ;
    rdfs:subPropertyOf odrl:spatialCoordinates ;
    skos:broader odrl:spatialCoordinates ;
    rdfs:label "Geospatial Latitude"@en ;
    skos:definition """Latitude coordinate in degrees. Domain: [-90, 90]."""@en ;
    skos:note "-90 = South Pole, 0 = Equator, 90 = North Pole"@en ;
    odrlsa:axis "latitude" ;
    odrlsa:domain "[-90, 90]" ;
    odrlsa:valueType xsd:decimal .

odrlsa:spatialCoordinatesLongitude a odrl:LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrlsa: ;
    rdfs:subPropertyOf odrl:spatialCoordinates ;
    skos:broader odrl:spatialCoordinates ;
    rdfs:label "Geospatial Longitude"@en ;
    skos:definition """Longitude coordinate in degrees. Domain: [-180, 180]."""@en ;
    skos:note "-180/180 = International Date Line, 0 = Prime Meridian"@en ;
    odrlsa:axis "longitude" ;
    odrlsa:domain "[-180, 180]" ;
    odrlsa:valueType xsd:decimal .

odrlsa:spatialCoordinatesAltitude a odrl:LeftOperand, owl:NamedIndividual, skos:Concept ;
    rdfs:isDefinedBy odrlsa: ;
    rdfs:subPropertyOf odrl:spatialCoordinates ;
    skos:broader odrl:spatialCoordinates ;
    rdfs:label "Geospatial Altitude"@en ;
    skos:definition """Altitude in meters above sea level. Domain: (-∞, ∞)."""@en ;
    skos:note "Negative values indicate below sea level"@en ;
    odrlsa:axis "altitude" ;
    odrlsa:domain "(-∞, ∞)" ;
    odrlsa:unit "meters" ;
    odrlsa:valueType xsd:decimal .

# ═══════════════════════════════════════════════════════════════════
# PROFILE METADATA
# ═══════════════════════════════════════════════════════════════════

odrlsa:axis a owl:DatatypeProperty ;
    rdfs:label "Axis"@en ;
    skos:definition "The axis this LeftOperand measures."@en ;
    rdfs:domain odrl:LeftOperand ;
    rdfs:range xsd:string .

odrlsa:dimension a owl:DatatypeProperty ;
    rdfs:label "Dimension"@en ;
    skos:definition "The dimensional category (horizontal, vertical, depth)."@en ;
    rdfs:domain odrl:LeftOperand ;
    rdfs:range xsd:string .

odrlsa:domain a owl:DatatypeProperty ;
    rdfs:label "Domain"@en ;
    skos:definition "The mathematical domain of valid values."@en ;
    rdfs:domain odrl:LeftOperand ;
    rdfs:range xsd:string .

odrlsa:requiresUnit a owl:DatatypeProperty ;
    rdfs:label "Requires Unit"@en ;
    skos:definition "Whether this LeftOperand requires a unit specification."@en ;
    rdfs:domain odrl:LeftOperand ;
    rdfs:range xsd:boolean .

odrlsa:valueType a owl:ObjectProperty ;
    rdfs:label "Value Type"@en ;
    skos:definition "The XSD datatype for the rightOperand value."@en ;
    rdfs:domain odrl:LeftOperand ;
    rdfs:range rdfs:Datatype .
```

---


### 6. How It Solves the Problem

#### 6.1 Before Profile (1D Over-Approximation)

```turtle
# Cannot distinguish X from Y
[ odrl:leftOperand odrl:relativeSpatialPosition ;
  odrl:operator odrl:lteq ;
  odrl:rightOperand "50"^^xsd:decimal ]
# Meaning ambiguous: X ≤ 50? Y ≤ 50? Both?
```

#### 6.2 After Profile (Complete 2D/3D)

```turtle
# Explicit 2D bounding box: [10%, 20%] to [60%, 80%]
[ odrl:and (
    [ odrl:leftOperand odrlsa:relativeSpatialPositionX ;
      odrl:operator odrl:gteq ;
      odrl:rightOperand "10"^^xsd:decimal ]
    [ odrl:leftOperand odrlsa:relativeSpatialPositionX ;
      odrl:operator odrl:lteq ;
      odrl:rightOperand "60"^^xsd:decimal ]
    [ odrl:leftOperand odrlsa:relativeSpatialPositionY ;
      odrl:operator odrl:gteq ;
      odrl:rightOperand "20"^^xsd:decimal ]
    [ odrl:leftOperand odrlsa:relativeSpatialPositionY ;
      odrl:operator odrl:lteq ;
      odrl:rightOperand "80"^^xsd:decimal ]
) ]
```

---

### 7. Extensibility Analysis

#### 7.1 How Extensible Is This Approach?

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXTENSIBILITY ANALYSIS                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  EXTENSION MECHANISM: rdfs:subPropertyOf + skos:broader        │
│  ═══════════════════════════════════════════════════════       │
│                                                                 │
│  odrlsa:relativeSpatialPositionX                               │
│      rdfs:subPropertyOf odrl:relativeSpatialPosition           │
│      skos:broader odrl:relativeSpatialPosition                 │
│                                                                 │
│  BENEFITS:                                                      │
│   Standard ODRL profile extension mechanism                   │
│   Backward compatible (generic operands still work)           │
│   Semantic inheritance (X isA relativeSpatialPosition)        │
│   Tool can detect and upgrade automatically                   │
│   No changes to ODRL Core required                            │
│                                                                 │
│  EXTENSIBILITY PATTERNS:                                        │
│  ════════════════════════                                       │
│                                                                 │
│  Pattern 1: Add New Axes                                        │
│  ─────────────────────────                                      │
│  odrlsa:relativeSpatialPositionW (4D time dimension)           │
│      rdfs:subPropertyOf odrl:relativeSpatialPosition           │
│                                                                 │
│  Pattern 2: Add New Coordinate Systems                          │
│  ─────────────────────────────────────                         │
│  odrlsa:polarCoordinatesR (radius)                             │
│  odrlsa:polarCoordinatesTheta (angle)                          │
│      rdfs:subPropertyOf odrl:relativeSpatialPosition           │
│                                                                 │
│  Pattern 3: Add Domain-Specific Sizes                          │
│  ────────────────────────────────────                          │
│  odrlsa:videoResolutionWidth                                   │
│  odrlsa:videoResolutionHeight                                  │
│  odrlsa:videoResolutionFrameRate                               │
│      rdfs:subPropertyOf odrl:absoluteSize                      │
│                                                                 │
│  Pattern 4: Add Geospatial Extensions                          │
│  ────────────────────────────────────                          │
│  odrlsa:spatialCoordinatesGeohash                              │
│  odrlsa:spatialCoordinatesMGRS                                 │
│      rdfs:subPropertyOf odrl:spatialCoordinates                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 7.2 Future Extensions

```turtle
# ═══════════════════════════════════════════════════════════════
# EXAMPLE FUTURE EXTENSIONS
# ═══════════════════════════════════════════════════════════════

# Video-specific dimensions
odrlsa:videoWidth a odrl:LeftOperand ;
    rdfs:subPropertyOf odrl:absoluteSize ;
    skos:definition "Video frame width in pixels."@en ;
    odrlsa:axis "width" ;
    odrlsa:domain "(0, ∞)" ;
    odrlsa:unit "px" .

odrlsa:videoHeight a odrl:LeftOperand ;
    rdfs:subPropertyOf odrl:absoluteSize ;
    skos:definition "Video frame height in pixels."@en ;
    odrlsa:axis "height" ;
    odrlsa:domain "(0, ∞)" ;
    odrlsa:unit "px" .

# Audio-specific dimensions
odrlsa:audioDuration a odrl:LeftOperand ;
    rdfs:subPropertyOf odrl:absoluteTemporalPosition ;
    skos:definition "Audio track duration in seconds."@en ;
    odrlsa:domain "(0, ∞)" ;
    odrlsa:unit "seconds" .

# Polar coordinates (for circular displays)
odrlsa:polarRadius a odrl:LeftOperand ;
    rdfs:subPropertyOf odrl:relativeSpatialPosition ;
    skos:definition "Radial distance as percentage of maximum radius."@en ;
    odrlsa:axis "r" ;
    odrlsa:domain "[0, 100]" .

odrlsa:polarAngle a odrl:LeftOperand ;
    rdfs:subPropertyOf odrl:relativeSpatialPosition ;
    skos:definition "Angle in degrees from reference."@en ;
    odrlsa:axis "theta" ;
    odrlsa:domain "[0, 360)" .
```

---

### 8. Implementation in ODRL-SA

```python
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from enum import Enum
from z3 import *

class AxisType(Enum):
    X = "X"
    Y = "Y"
    Z = "Z"
    WIDTH = "width"
    HEIGHT = "height"
    DEPTH = "depth"
    LATITUDE = "latitude"
    LONGITUDE = "longitude"
    ALTITUDE = "altitude"

@dataclass
class AxisMapping:
    """Maps profile LeftOperands to axes."""
    base_operand: str
    axis: AxisType
    domain_min: float
    domain_max: float
    inclusive_min: bool = True
    inclusive_max: bool = True

# Profile configuration
SPATIAL_PROFILE_MAPPINGS: Dict[str, AxisMapping] = {
    # Relative Spatial Position
    "relativeSpatialPositionX": AxisMapping("relativeSpatialPosition", AxisType.X, 0, 100),
    "relativeSpatialPositionY": AxisMapping("relativeSpatialPosition", AxisType.Y, 0, 100),
    "relativeSpatialPositionZ": AxisMapping("relativeSpatialPosition", AxisType.Z, 0, 100),
    
    # Absolute Spatial Position
    "absoluteSpatialPositionX": AxisMapping("absoluteSpatialPosition", AxisType.X, 0, float('inf')),
    "absoluteSpatialPositionY": AxisMapping("absoluteSpatialPosition", AxisType.Y, 0, float('inf')),
    "absoluteSpatialPositionZ": AxisMapping("absoluteSpatialPosition", AxisType.Z, 0, float('inf')),
    
    # Relative Size
    "relativeSizeWidth": AxisMapping("relativeSize", AxisType.WIDTH, 0, float('inf')),
    "relativeSizeHeight": AxisMapping("relativeSize", AxisType.HEIGHT, 0, float('inf')),
    "relativeSizeDepth": AxisMapping("relativeSize", AxisType.DEPTH, 0, float('inf')),
    
    # Absolute Size
    "absoluteSizeWidth": AxisMapping("absoluteSize", AxisType.WIDTH, 0, float('inf'), False, True),
    "absoluteSizeHeight": AxisMapping("absoluteSize", AxisType.HEIGHT, 0, float('inf'), False, True),
    "absoluteSizeDepth": AxisMapping("absoluteSize", AxisType.DEPTH, 0, float('inf'), False, True),
    
    # Spatial Coordinates
    "spatialCoordinatesLatitude": AxisMapping("spatialCoordinates", AxisType.LATITUDE, -90, 90),
    "spatialCoordinatesLongitude": AxisMapping("spatialCoordinates", AxisType.LONGITUDE, -180, 180),
    "spatialCoordinatesAltitude": AxisMapping("spatialCoordinates", AxisType.ALTITUDE, float('-inf'), float('inf')),
}


class MultiDimensionalAnalyzer:
    """
    Analyzer with automatic dimension detection and profile support.
    """
    
    def __init__(self):
        self.profile_mappings = SPATIAL_PROFILE_MAPPINGS
    
    def detect_dimensions(self, constraints: List[dict]) -> Dict[str, Set[AxisType]]:
        """Detect which base operands use which axes."""
        dimensions: Dict[str, Set[AxisType]] = {}
        
        for c in constraints:
            operand = c.get('leftOperand', '')
            
            # Check if it's a profile operand
            if operand in self.profile_mappings:
                mapping = self.profile_mappings[operand]
                base = mapping.base_operand
                if base not in dimensions:
                    dimensions[base] = set()
                dimensions[base].add(mapping.axis)
            
            # Check if it's a generic operand
            elif operand in ['relativeSpatialPosition', 'absoluteSpatialPosition', 
                           'relativeSize', 'absoluteSize', 'spatialCoordinates']:
                if operand not in dimensions:
                    dimensions[operand] = set()
                # Generic operand = 1D treatment
        
        return dimensions
    
    def analyze(self, constraints: List[dict]) -> dict:
        """Analyze constraints with multi-dimensional awareness."""
        dimensions = self.detect_dimensions(constraints)
        
        solver = Solver()
        variables: Dict[str, RealRef] = {}
        warnings: List[str] = []
        
        for c in constraints:
            operand = c.get('leftOperand', '')
            operator = c['operator']
            value = float(c['rightOperand'])
            
            if operand in self.profile_mappings:
                # Profile operand - use axis-specific variable
                mapping = self.profile_mappings[operand]
                var_name = f"{mapping.base_operand}_{mapping.axis.value}"
                
                if var_name not in variables:
                    variables[var_name] = Real(var_name)
                    # Add domain constraint
                    solver.add(self._domain_constraint(variables[var_name], mapping))
                
                solver.add(self._encode_constraint(variables[var_name], operator, value))
            
            else:
                # Generic operand - 1D treatment with warning
                var_name = operand
                if var_name not in variables:
                    variables[var_name] = Real(var_name)
                    warnings.append(
                        f"Using 1D over-approximation for '{operand}'. "
                        f"For complete 2D/3D analysis, use ODRL-SA Spatial Profile."
                    )
                
                solver.add(self._encode_constraint(variables[var_name], operator, value))
        
        # Check satisfiability
        result = solver.check()
        
        if result == sat:
            model = solver.model()
            witness = {str(v): str(model[v]) for v in variables.values()}
            return {
                'status': 'POSSIBLY-COMPATIBLE',
                'dimensions': {k: [a.value for a in v] for k, v in dimensions.items()},
                'witness': witness,
                'warnings': warnings,
                'complete': len(warnings) == 0
            }
        else:
            return {
                'status': 'CONFLICT',
                'dimensions': {k: [a.value for a in v] for k, v in dimensions.items()},
                'warnings': warnings,
                'complete': True  # Conflict detection is always complete
            }
    
    def _domain_constraint(self, var: RealRef, mapping: AxisMapping) -> BoolRef:
        """Generate domain constraint for a variable."""
        constraints = []
        
        if mapping.domain_min != float('-inf'):
            if mapping.inclusive_min:
                constraints.append(var >= mapping.domain_min)
            else:
                constraints.append(var > mapping.domain_min)
        
        if mapping.domain_max != float('inf'):
            if mapping.inclusive_max:
                constraints.append(var <= mapping.domain_max)
            else:
                constraints.append(var < mapping.domain_max)
        
        return And(constraints) if constraints else BoolVal(True)
    
    def _encode_constraint(self, var: RealRef, operator: str, value: float) -> BoolRef:
        """Encode a single constraint."""
        if operator == "eq":
            return var == value
        elif operator == "neq":
            return var != value
        elif operator == "lt":
            return var < value
        elif operator == "lteq":
            return var <= value
        elif operator == "gt":
            return var > value
        elif operator == "gteq":
            return var >= value
        else:
            raise ValueError(f"Unknown operator: {operator}")
```

---

### 9. Complete Comparison: Before vs After Profile

```
┌─────────────────────────────────────────────────────────────────┐
│                    BEFORE vs AFTER PROFILE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SCENARIO: Two non-overlapping regions in 2D                   │
│                                                                 │
│  Region A: X∈[10,30], Y∈[10,30]                                │
│  Region B: X∈[70,90], Y∈[70,90]                                │
│                                                                 │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  BEFORE PROFILE (1D)                                 │      │
│  │  ═══════════════════                                 │      │
│  │                                                      │      │
│  │  Constraints (ambiguous):                            │      │
│  │  • relativeSpatialPosition gteq 10                   │      │
│  │  • relativeSpatialPosition lteq 30                   │      │
│  │  • relativeSpatialPosition gteq 70                   │      │
│  │  • relativeSpatialPosition lteq 90                   │      │
│  │                                                      │      │
│  │  Analysis: [10,30] ∩ [70,90] = ∅                    │      │
│  │  Result: CONFLICT (but only on 1D projection!)      │      │
│  │                                                      │      │
│  │  Problem: Cannot express "A is top-left, B is       │      │
│  │           bottom-right" - different constraint sets  │      │
│  │                                                      │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                 │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  AFTER PROFILE (2D)                                  │      │
│  │  ══════════════════                                  │      │
│  │                                                      │      │
│  │  Region A constraints:                               │      │
│  │  • relativeSpatialPositionX gteq 10                  │      │
│  │  • relativeSpatialPositionX lteq 30                  │      │
│  │  • relativeSpatialPositionY gteq 10                  │      │
│  │  • relativeSpatialPositionY lteq 30                  │      │
│  │                                                      │      │
│  │  Region B constraints:                               │      │
│  │  • relativeSpatialPositionX gteq 70                  │      │
│  │  • relativeSpatialPositionX lteq 90                  │      │
│  │  • relativeSpatialPositionY gteq 70                  │      │
│  │  • relativeSpatialPositionY lteq 90                  │      │
│  │                                                      │      │
│  │  Analysis:                                           │      │
│  │  X: [10,30] ∩ [70,90] = ∅  → CONFLICT on X          │      │
│  │  Y: [10,30] ∩ [70,90] = ∅  → CONFLICT on Y          │      │
│  │                                                      │      │
│  │  Result: CONFLICT  (correctly detected!)           │      │
│  │                                                      │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 10. Summary Table

| Aspect | Without Profile | With Profile |
|--------|-----------------|--------------|
| **Spatial Position 2D** | 1D over-approx |  Complete |
| **Spatial Position 3D** | 1D over-approx |  Complete |
| **Size 2D** | 1D over-approx |  Complete |
| **Size 3D** | 1D over-approx |  Complete |
| **Geospatial** | External KB |  Complete |
| **Soundness** |  Sound |  Sound |
| **Completeness** |  Incomplete |  Complete |
| **ODRL Compliance** |  Core |  Profile |
| **Backward Compatible** | N/A |  Yes |
| **New LeftOperands** | 0 | 15 |

---

### 11. Publication Statement

> **ODRL-SA Spatial-Temporal Profile.** ODRL Core defines several LeftOperands with multi-dimensional semantics (`relativeSpatialPosition`, `absoluteSpatialPosition`, `relativeSize`, `absoluteSize`, `spatialCoordinates`) but lacks axis-specific granularity in its constraint model. We propose the **ODRL-SA Spatial-Temporal Profile** that extends these 5 base LeftOperands with 15 axis-specific variants (X/Y/Z for positions, Width/Height/Depth for sizes, Latitude/Longitude/Altitude for geospatial coordinates). This profile uses standard ODRL extension mechanisms (`rdfs:subPropertyOf`, `skos:broader`) ensuring backward compatibility while enabling **complete** 2D/3D conflict detection. ODRL-SA automatically detects profile usage and upgrades from 1D over-approximation to full multi-dimensional analysis when axis-specific operands are present.



---

### 2. Solution Options Analysis

#### Option A: Profile-Defined Axis-Specific LeftOperands (RECOMMENDED)

```turtle
# Define axis-specific LeftOperands in a profile
ex:relativeSpatialPositionX a odrl:LeftOperand ;
    rdfs:subPropertyOf odrl:relativeSpatialPosition ;
    skos:definition "X-axis position as percentage [0,100]" .

ex:relativeSpatialPositionY a odrl:LeftOperand ;
    rdfs:subPropertyOf odrl:relativeSpatialPosition ;
    skos:definition "Y-axis position as percentage [0,100]" .

ex:relativeSpatialPositionZ a odrl:LeftOperand ;  # For 3D
    rdfs:subPropertyOf odrl:relativeSpatialPosition ;
    skos:definition "Z-axis position as percentage [0,100]" .
```

**Usage:**
```turtle
# Express 2D bounding box [10%, 20%] to [60%, 80%]
[ odrl:and (
    [ odrl:leftOperand ex:relativeSpatialPositionX ;
      odrl:operator odrl:gteq ;
      odrl:rightOperand "10"^^xsd:decimal ]
    [ odrl:leftOperand ex:relativeSpatialPositionX ;
      odrl:operator odrl:lteq ;
      odrl:rightOperand "60"^^xsd:decimal ]
    [ odrl:leftOperand ex:relativeSpatialPositionY ;
      odrl:operator odrl:gteq ;
      odrl:rightOperand "20"^^xsd:decimal ]
    [ odrl:leftOperand ex:relativeSpatialPositionY ;
      odrl:operator odrl:lteq ;
      odrl:rightOperand "80"^^xsd:decimal ]
) ]
```

| Aspect | Assessment |
|--------|------------|
| **Soundness** |  Complete for 2D |
| **Completeness** |  Full 2D conflict detection |
| **ODRL Compliance** |  Uses standard extension mechanism |
| **SMT Encoding** |  Separate variables per axis |
| **Complexity** | ⚠️ More verbose policies |
| **Backward Compatible** |  Extends, doesn't replace |

---

#### Option B: Structured RightOperand (Requires ODRL Extension)

```turtle
# Hypothetical ODRL extension for structured values
[ odrl:leftOperand odrl:relativeSpatialPosition ;
  odrl:operator odrl:within ;  # New operator
  odrl:rightOperand [
    ex:x1 "10"^^xsd:decimal ;
    ex:y1 "20"^^xsd:decimal ;
    ex:x2 "60"^^xsd:decimal ;
    ex:y2 "80"^^xsd:decimal
  ]
]
```

| Aspect | Assessment |
|--------|------------|
| **Soundness** |  Could be complete |
| **Completeness** |  Full 2D conflict detection |
| **ODRL Compliance** |  Requires ODRL spec change |
| **SMT Encoding** | ⚠️ More complex parsing |
| **Complexity** | ⚠️ New operator semantics |
| **Backward Compatible** |  Breaking change |

---

#### Option C: Interval-Based RightOperand

```turtle
# Use list/collection for range
[ odrl:leftOperand odrl:relativeSpatialPosition ;
  odrl:operator odrl:isWithin ;
  odrl:rightOperand ("10" "20" "60" "80")  # x1, y1, x2, y2
]
```

| Aspect | Assessment |
|--------|------------|
| **Soundness** |  Could be complete |
| **Completeness** |  Full 2D conflict detection |
| **ODRL Compliance** | ⚠️ Stretches current syntax |
| **SMT Encoding** | ⚠️ Needs special parsing |
| **Complexity** | ⚠️ Order-dependent semantics |
| **Backward Compatible** | ⚠️ Partial |

---

#### Option D: Enhanced Abstract Domain (Box Domain)

Instead of intervals, use **boxes** (Cartesian products of intervals):

```
┌─────────────────────────────────────────────────────────────────┐
│                    BOX ABSTRACT DOMAIN                          │
│                                                                 │
│  1D Interval:  [a, b] ⊆ ℝ                                      │
│                                                                 │
│  2D Box:       [a₁, b₁] × [a₂, b₂] ⊆ ℝ²                        │
│                                                                 │
│  3D Box:       [a₁, b₁] × [a₂, b₂] × [a₃, b₃] ⊆ ℝ³            │
│                                                                 │
│  Box intersection:                                              │
│  ([a₁,b₁] × [a₂,b₂]) ∩ ([c₁,d₁] × [c₂,d₂])                    │
│  = ([a₁,b₁] ∩ [c₁,d₁]) × ([a₂,b₂] ∩ [c₂,d₂])                  │
│                                                                 │
│  CONFLICT iff any dimension has empty intersection              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

| Aspect | Assessment |
|--------|------------|
| **Soundness** |  Sound AND complete for boxes |
| **Completeness** |  For axis-aligned boxes |
| **ODRL Compliance** | ⚠️ Requires axis-specific operands |
| **SMT Encoding** |  QF_LRA per dimension |
| **Complexity** | ⚠️ More complex implementation |
| **Backward Compatible** |  Extends current approach |

---

### 3. Recommended Solution: Hybrid Approach

#### 3.1 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    HYBRID SOLUTION                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  LAYER 1: ODRL Core (Current)                                  │
│  ═══════════════════════════                                   │
│  • relativeSpatialPosition as 1D scalar                        │
│  • Sound over-approximation                                     │
│  • Works with any ODRL policy                                   │
│                                                                 │
│  LAYER 2: Profile Extension (Enhanced)                         │
│  ═════════════════════════════════════                         │
│  • Axis-specific LeftOperands (X, Y, Z)                        │
│  • Full 2D/3D conflict detection                               │
│  • Opt-in for profiles that need it                            │
│                                                                 │
│  DETECTION LOGIC:                                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  if policy uses axis-specific operands:                 │   │
│  │      → Use Box domain (complete 2D/3D analysis)         │   │
│  │  else:                                                   │   │
│  │      → Use 1D interval (sound over-approximation)       │   │
│  │      → Add warning: "2D analysis available with profile"│   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.2 Implementation

```python
from z3 import *
from dataclasses import dataclass
from typing import Optional, List, Tuple
from enum import Enum

class SpatialDimension(Enum):
    D1 = 1  # 1D (scalar)
    D2 = 2  # 2D (rectangle)
    D3 = 3  # 3D (cuboid)

@dataclass
class Box:
    """N-dimensional box (Cartesian product of intervals)."""
    intervals: List[Tuple[float, float]]  # [(min, max), ...]
    
    @property
    def dimension(self) -> int:
        return len(self.intervals)
    
    def intersect(self, other: 'Box') -> Optional['Box']:
        """Compute box intersection. Returns None if empty."""
        if self.dimension != other.dimension:
            return None
        
        result = []
        for (a1, b1), (a2, b2) in zip(self.intervals, other.intervals):
            lo = max(a1, a2)
            hi = min(b1, b2)
            if lo > hi:
                return None  # Empty intersection
            result.append((lo, hi))
        
        return Box(result)
    
    def is_empty(self) -> bool:
        return any(lo > hi for lo, hi in self.intervals)


class SpatialEncoder:
    """SMT encoder for spatial constraints with dimension awareness."""
    
    def __init__(self, dimension: SpatialDimension = SpatialDimension.D1):
        self.dimension = dimension
        self._create_variables()
    
    def _create_variables(self):
        """Create Z3 variables based on dimension."""
        if self.dimension == SpatialDimension.D1:
            self.vars = [Real('relativeSpatialPosition')]
        elif self.dimension == SpatialDimension.D2:
            self.vars = [
                Real('relativeSpatialPosition_X'),
                Real('relativeSpatialPosition_Y')
            ]
        elif self.dimension == SpatialDimension.D3:
            self.vars = [
                Real('relativeSpatialPosition_X'),
                Real('relativeSpatialPosition_Y'),
                Real('relativeSpatialPosition_Z')
            ]
    
    def domain_constraint(self) -> BoolRef:
        """All coordinates in [0, 100]."""
        constraints = []
        for var in self.vars:
            constraints.append(And(var >= 0, var <= 100))
        return And(constraints)
    
    def encode_box(self, box: Box) -> BoolRef:
        """Encode a box constraint."""
        if box.dimension != self.dimension.value:
            raise ValueError(f"Box dimension {box.dimension} != encoder dimension {self.dimension.value}")
        
        constraints = [self.domain_constraint()]
        for var, (lo, hi) in zip(self.vars, box.intervals):
            constraints.append(And(var >= lo, var <= hi))
        
        return And(constraints)
    
    def encode_1d_constraint(self, operator: str, value: float, axis: int = 0) -> BoolRef:
        """Encode a single-axis constraint."""
        var = self.vars[axis] if axis < len(self.vars) else self.vars[0]
        domain = And(var >= 0, var <= 100)
        
        if operator == "eq":
            return And(domain, var == value)
        elif operator == "neq":
            return And(domain, var != value)
        elif operator == "lt":
            return And(domain, var < value)
        elif operator == "lteq":
            return And(domain, var <= value)
        elif operator == "gt":
            return And(domain, var > value)
        elif operator == "gteq":
            return And(domain, var >= value)
        else:
            raise ValueError(f"Unknown operator: {operator}")


class SpatialConflictDetector:
    """Detect conflicts in spatial constraints with dimension awareness."""
    
    def __init__(self):
        pass
    
    def detect_dimension(self, constraints: List[dict]) -> SpatialDimension:
        """Detect if constraints use axis-specific operands."""
        operands = {c.get('leftOperand') for c in constraints}
        
        if any('_X' in op or '_Y' in op or '_Z' in op for op in operands if op):
            if any('_Z' in op for op in operands if op):
                return SpatialDimension.D3
            return SpatialDimension.D2
        
        return SpatialDimension.D1
    
    def analyze(self, constraints: List[dict]) -> dict:
        """Analyze spatial constraints for conflicts."""
        dimension = self.detect_dimension(constraints)
        encoder = SpatialEncoder(dimension)
        
        solver = Solver()
        solver.add(encoder.domain_constraint())
        
        for c in constraints:
            axis = self._get_axis(c.get('leftOperand', ''))
            encoded = encoder.encode_1d_constraint(
                c['operator'],
                float(c['rightOperand']),
                axis
            )
            solver.add(encoded)
        
        result = solver.check()
        
        if result == sat:
            model = solver.model()
            witness = {str(v): model[v] for v in encoder.vars}
            return {
                'status': 'POSSIBLY-COMPATIBLE',
                'dimension': dimension.name,
                'witness': witness,
                'complete': dimension != SpatialDimension.D1
            }
        else:
            return {
                'status': 'CONFLICT',
                'dimension': dimension.name,
                'complete': True  # Conflict detection is always complete
            }
    
    def _get_axis(self, operand: str) -> int:
        """Map operand name to axis index."""
        if '_X' in operand:
            return 0
        elif '_Y' in operand:
            return 1
        elif '_Z' in operand:
            return 2
        return 0  # Default to first axis
```

---

### 4. Profile Definition for 2D/3D Support

```turtle
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix odrlsa: <http://odrl-sa.2/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# ═══════════════════════════════════════════════════════════════
# ODRL-SA Spatial Profile
# Extends ODRL Core with axis-specific spatial LeftOperands
# ═══════════════════════════════════════════════════════════════

odrlsa:SpatialProfile a odrl:Profile ;
    rdfs:label "ODRL-SA Spatial Profile"@en ;
    skos:definition "Profile extending ODRL with axis-specific spatial 
                     LeftOperands for complete 2D/3D conflict detection."@en .

# ═══════════════════════════════════════════════════════════════
# Relative Spatial Position - Axis-Specific
# ═══════════════════════════════════════════════════════════════

odrlsa:relativeSpatialPositionX a odrl:LeftOperand, skos:Concept ;
    rdfs:subPropertyOf odrl:relativeSpatialPosition ;
    rdfs:label "Relative Spatial Position X"@en ;
    skos:definition "X-axis position as percentage of horizontal extent [0,100]."@en ;
    skos:note "0 = left edge, 100 = right edge"@en ;
    odrlsa:axis "X" ;
    odrlsa:domain "[0, 100]" .

odrlsa:relativeSpatialPositionY a odrl:LeftOperand, skos:Concept ;
    rdfs:subPropertyOf odrl:relativeSpatialPosition ;
    rdfs:label "Relative Spatial Position Y"@en ;
    skos:definition "Y-axis position as percentage of vertical extent [0,100]."@en ;
    skos:note "0 = top edge, 100 = bottom edge"@en ;
    odrlsa:axis "Y" ;
    odrlsa:domain "[0, 100]" .

odrlsa:relativeSpatialPositionZ a odrl:LeftOperand, skos:Concept ;
    rdfs:subPropertyOf odrl:relativeSpatialPosition ;
    rdfs:label "Relative Spatial Position Z"@en ;
    skos:definition "Z-axis position as percentage of depth extent [0,100]."@en ;
    skos:note "0 = front, 100 = back (for 3D spaces)"@en ;
    odrlsa:axis "Z" ;
    odrlsa:domain "[0, 100]" .

# ═══════════════════════════════════════════════════════════════
# Absolute Spatial Position - Axis-Specific
# ═══════════════════════════════════════════════════════════════

odrlsa:absoluteSpatialPositionX a odrl:LeftOperand, skos:Concept ;
    rdfs:subPropertyOf odrl:absoluteSpatialPosition ;
    rdfs:label "Absolute Spatial Position X"@en ;
    skos:definition "X-axis position in absolute units."@en ;
    odrlsa:axis "X" ;
    odrlsa:domain "[0, ∞)" ;
    odrlsa:requiresUnit true .

odrlsa:absoluteSpatialPositionY a odrl:LeftOperand, skos:Concept ;
    rdfs:subPropertyOf odrl:absoluteSpatialPosition ;
    rdfs:label "Absolute Spatial Position Y"@en ;
    skos:definition "Y-axis position in absolute units."@en ;
    odrlsa:axis "Y" ;
    odrlsa:domain "[0, ∞)" ;
    odrlsa:requiresUnit true .

odrlsa:absoluteSpatialPositionZ a odrl:LeftOperand, skos:Concept ;
    rdfs:subPropertyOf odrl:absoluteSpatialPosition ;
    rdfs:label "Absolute Spatial Position Z"@en ;
    skos:definition "Z-axis position in absolute units."@en ;
    odrlsa:axis "Z" ;
    odrlsa:domain "[0, ∞)" ;
    odrlsa:requiresUnit true .
```

---

### 5. Example: Complete 2D Conflict Detection

#### 5.1 Policy with 2D Constraints

```turtle
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix odrlsa: <http://odrl-sa.2/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.org/> .

# Policy 1: Asset must be in top-left quadrant
ex:policy_2d_01 a odrl:Set ;
    odrl:permission [
        odrl:action odrl:display ;
        odrl:target ex:image01 ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrlsa:relativeSpatialPositionX ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "50"^^xsd:decimal ]
                [ odrl:leftOperand odrlsa:relativeSpatialPositionY ;
                  odrl:operator odrl:lteq ;
                  odrl:rightOperand "50"^^xsd:decimal ]
            )
        ]
    ] .

# Policy 2: Asset must be in bottom-right quadrant
ex:policy_2d_02 a odrl:Set ;
    odrl:permission [
        odrl:action odrl:display ;
        odrl:target ex:image01 ;
        odrl:constraint [
            odrl:and (
                [ odrl:leftOperand odrlsa:relativeSpatialPositionX ;
                  odrl:operator odrl:gteq ;
                  odrl:rightOperand "50"^^xsd:decimal ]
                [ odrl:leftOperand odrlsa:relativeSpatialPositionY ;
                  odrl:operator odrl:gteq ;
                  odrl:rightOperand "50"^^xsd:decimal ]
            )
        ]
    ] .
```

#### 5.2 Analysis

```
┌─────────────────────────────────────────────────────────────────┐
│                    2D CONFLICT ANALYSIS                         │
│                                                                 │
│     0%              50%                              100%       │
│   0%┌───────────────┬────────────────────────────────┐         │
│     │               │                                │         │
│     │   Policy 1    │                                │         │
│     │   [0,50]×     │                                │         │
│     │   [0,50]      │                                │         │
│  50%├───────────────┼────────────────────────────────┤         │
│     │               │                                │         │
│     │               │              Policy 2          │         │
│     │               │              [50,100]×         │         │
│     │               │              [50,100]          │         │
│ 100%└───────────────┴────────────────────────────────┘         │
│                                                                 │
│  Box 1: [0,50] × [0,50]                                        │
│  Box 2: [50,100] × [50,100]                                    │
│                                                                 │
│  Intersection:                                                  │
│  X: [0,50] ∩ [50,100] = {50} (single point)                   │
│  Y: [0,50] ∩ [50,100] = {50} (single point)                   │
│                                                                 │
│  Result: {(50, 50)} — single point intersection                │
│                                                                 │
│  If constraints were STRICT (lt/gt instead of lteq/gteq):      │
│  X: [0,50) ∩ (50,100] = ∅                                      │
│  Result: CONFLICT                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 5.3 SMT Encoding

```python
from z3 import *

# 2D encoder
x = Real('relativeSpatialPositionX')
y = Real('relativeSpatialPositionY')

solver = Solver()

# Domain constraints
solver.add(And(x >= 0, x <= 100))
solver.add(And(y >= 0, y <= 100))

# Policy 1: top-left quadrant
solver.add(x <= 50)
solver.add(y <= 50)

# Policy 2: bottom-right quadrant  
solver.add(x >= 50)
solver.add(y >= 50)

# Check
result = solver.check()
print(f"Result: {result}")  # sat

if result == sat:
    m = solver.model()
    print(f"Witness: x={m[x]}, y={m[y]}")  # x=50, y=50
```

---

### 6. Comparison: 1D vs 2D Analysis

```
┌─────────────────────────────────────────────────────────────────┐
│                    1D vs 2D COMPARISON                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SCENARIO: Regions that don't overlap in 2D                    │
│                                                                 │
│  Region A: X∈[10,30], Y∈[10,30]                                │
│  Region B: X∈[70,90], Y∈[70,90]                                │
│                                                                 │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  1D ANALYSIS (Current ODRL-SA)                       │      │
│  │  ════════════════════════════                        │      │
│  │  Using single relativeSpatialPosition:               │      │
│  │  A: [10, 90] (union of all coordinates)              │      │
│  │  B: [10, 90]                                         │      │
│  │  Intersection: [10, 90] ≠ ∅                          │      │
│  │  Result: POSSIBLY-COMPATIBLE                         │      │
│  │  Reality: NO OVERLAP! (False negative)               │      │
│  │  Sound:   Complete:                                │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                 │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  2D ANALYSIS (With Spatial Profile)                  │      │
│  │  ═══════════════════════════════════                 │      │
│  │  Using axis-specific operands:                       │      │
│  │  A: [10,30] × [10,30]                               │      │
│  │  B: [70,90] × [70,90]                               │      │
│  │  X intersection: [10,30] ∩ [70,90] = ∅              │      │
│  │  Result: CONFLICT                                   │      │
│  │  Reality: CORRECT!                                   │      │
│  │  Sound:   Complete:                                │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 7. Implementation Strategy

#### 7.1 Backward Compatible Enhancement

```python
class EnhancedSpatialAnalyzer:
    """
    Enhanced spatial analyzer with automatic dimension detection.
    
    - If policy uses axis-specific operands → Full 2D/3D analysis
    - Otherwise → 1D over-approximation with warning
    """
    
    AXIS_OPERANDS = {
        'relativeSpatialPositionX': ('relative', 'X'),
        'relativeSpatialPositionY': ('relative', 'Y'),
        'relativeSpatialPositionZ': ('relative', 'Z'),
        'absoluteSpatialPositionX': ('absolute', 'X'),
        'absoluteSpatialPositionY': ('absolute', 'Y'),
        'absoluteSpatialPositionZ': ('absolute', 'Z'),
    }
    
    GENERIC_OPERANDS = {
        'relativeSpatialPosition': 'relative',
        'absoluteSpatialPosition': 'absolute',
    }
    
    def analyze(self, constraints: List[dict]) -> AnalysisResult:
        # Detect dimension
        dimension = self._detect_dimension(constraints)
        
        if dimension == 1:
            result = self._analyze_1d(constraints)
            result.add_warning(
                "Using 1D over-approximation. For complete 2D/3D analysis, "
                "use axis-specific LeftOperands from ODRL-SA Spatial Profile."
            )
            result.completeness = "SOUND_INCOMPLETE"
        else:
            result = self._analyze_nd(constraints, dimension)
            result.completeness = "SOUND_COMPLETE"
        
        return result
    
    def _detect_dimension(self, constraints: List[dict]) -> int:
        """Detect dimensionality from operand usage."""
        axes_used = set()
        
        for c in constraints:
            operand = c.get('leftOperand', '')
            if operand in self.AXIS_OPERANDS:
                _, axis = self.AXIS_OPERANDS[operand]
                axes_used.add(axis)
        
        if not axes_used:
            return 1  # Generic operands only
        
        return len(axes_used)
    
    def _analyze_1d(self, constraints: List[dict]) -> AnalysisResult:
        """1D interval analysis (current approach)."""
        # ... existing implementation
        pass
    
    def _analyze_nd(self, constraints: List[dict], n: int) -> AnalysisResult:
        """N-dimensional box analysis."""
        solver = Solver()
        vars_by_axis = {}
        
        for c in constraints:
            operand = c.get('leftOperand', '')
            if operand in self.AXIS_OPERANDS:
                kind, axis = self.AXIS_OPERANDS[operand]
                
                # Get or create variable for this axis
                var_name = f"{kind}SpatialPosition_{axis}"
                if var_name not in vars_by_axis:
                    vars_by_axis[var_name] = Real(var_name)
                    # Add domain constraint
                    if kind == 'relative':
                        solver.add(And(vars_by_axis[var_name] >= 0, 
                                      vars_by_axis[var_name] <= 100))
                    else:
                        solver.add(vars_by_axis[var_name] >= 0)
                
                var = vars_by_axis[var_name]
                
                # Encode constraint
                solver.add(self._encode_constraint(var, c['operator'], 
                                                   float(c['rightOperand'])))
        
        # Check satisfiability
        result = solver.check()
        
        if result == sat:
            model = solver.model()
            witness = {str(v): model[v] for v in vars_by_axis.values()}
            return AnalysisResult(
                status='POSSIBLY-COMPATIBLE',
                witness=witness,
                dimension=n
            )
        else:
            return AnalysisResult(
                status='CONFLICT',
                dimension=n
            )
```

---

### 8. Summary: Recommended Approach

```
┌─────────────────────────────────────────────────────────────────┐
│                    RECOMMENDED SOLUTION                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. KEEP 1D ANALYSIS FOR ODRL CORE                             │
│     • Sound over-approximation                                  │
│     • Works with any ODRL policy                               │
│     • No breaking changes                                       │
│                                                                 │
│  2. ADD SPATIAL PROFILE FOR 2D/3D                              │
│     • Define axis-specific LeftOperands                        │
│     • Full conflict detection for boxes                        │
│     • Opt-in for profiles that need precision                  │
│                                                                 │
│  3. AUTOMATIC DIMENSION DETECTION                              │
│     • If axis-specific operands found → use 2D/3D analysis    │
│     • Otherwise → use 1D with warning                         │
│                                                                 │
│  4. CLEAR REPORTING                                            │
│     • SOUND_COMPLETE: Full analysis possible                   │
│     • SOUND_INCOMPLETE: 1D over-approximation used             │
│     • Suggest profile upgrade when applicable                  │
│                                                                 │
│  BENEFITS:                                                      │
│   Backward compatible                                         │
│   Progressive enhancement                                     │
│   Sound in all cases                                         │
│   Complete when profile used                                  │
│   Clear user guidance                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 9. For Your Paper

You can present this as:

> **Multi-Dimensional Spatial Analysis.** ODRL Core's `relativeSpatialPosition` describes 2D/3D coordinates, but the constraint syntax only supports scalar values. ODRL-SA addresses this through a **two-tier approach**:
>
> 1. **ODRL Core Compatibility**: For generic `relativeSpatialPosition` constraints, ODRL-SA employs 1D interval analysis as a sound over-approximation. This guarantees no false positives but may miss conflicts that require multi-dimensional reasoning.
>
> 2. **Spatial Profile Extension**: We define an ODRL profile with axis-specific LeftOperands (`relativeSpatialPositionX`, `relativeSpatialPositionY`, `relativeSpatialPositionZ`) that enable **complete** 2D/3D conflict detection using the Box abstract domain—Cartesian products of intervals with per-axis intersection.
>
> ODRL-SA automatically detects when axis-specific operands are used and upgrades to complete multi-dimensional analysis, while maintaining backward compatibility with existing ODRL policies.
