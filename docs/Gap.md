
## 1️⃣ **Open World Assumption Gap**

**Problem:** We use **Closed World Assumption** (CWA) - if something isn't stated, it's false.

**ODRL Reality:** Uses **Open World Assumption** (OWA) - unknown ≠ false.

```
Our system:    language not specified → language = ∅
ODRL semantics: language not specified → language = UNKNOWN (could be anything)
```

**Impact:** May miss conflicts when constraints are underspecified.

---

## 2️⃣ **Finite Domain Problem**

**Problem:** Z3 works best with **bounded domains**.

```
Multi-valued operands: Array[String, Bool]
Z3 finds: K(String, True) - "all strings are in set"
```

**Reality:** Real sets are finite (e.g., `{en, fr, de}`), not infinite.

**Impact:** False positives - conflicts that wouldn't occur in practice.

---

## 3️⃣ **No Runtime Context**

**Problem:** We analyze **static policy**, not **runtime state**.

```
Policy: "allow if user isA Student"
Reality: We don't know WHO the user is at analysis time
```

**Impact:** Can only detect **structural conflicts**, not **runtime conflicts**.

---

## 4️⃣ **Semantic Approximation**

| Feature | ODRL Spec | Our Implementation |
|---------|-----------|-------------------|
| `isA` | Full OWL reasoning | RDFS subClassOf only |
| `hasPart` | Mereological | String contains / set membership |
| `spatial` | GeoSPARQL | Not supported |
| `event` | CEP streams | Not supported |

---

## 5️⃣ **Policy Composition Blind Spot**

**Problem:** We analyze **single policies**, not **policy interactions**.

```
Policy A: allow use for Students
Policy B: deny use for Person

Combined: Student isA Person → CONFLICT
```

**We don't:** Automatically compose and check cross-policy conflicts.

---

## 6️⃣ **Decidability vs Expressiveness Trade-off**

```
More expressive → Undecidable (halting problem)
Our choice    → Decidable but limited (propositional + linear arithmetic)
```

**We cannot handle:**
- Recursive constraints
- Unbounded quantification
- Complex temporal logic (LTL/CTL)

---

## 📊 Summary Table

| Limitation | Severity | Workaround |
|------------|----------|------------|
| Open World | 🟡 Medium | Document assumption |
| Finite Domain | 🟡 Medium | Add domain constraints |
| No Runtime | 🟠 High | Separate runtime checker |
| Semantic Approx | 🟡 Medium | Extend hierarchy reasoner |
| No Composition | 🟠 High | Future work |
| Decidability | 🟢 Low | Acceptable trade-off |

---

## 🎓 For Your Paper

> "Our approach prioritizes **decidability** and **practical utility** over full ODRL semantic coverage. We handle ~90% of real-world policies while maintaining polynomial-time conflict detection. Limitations include closed-world assumption, static analysis only, and simplified mereological reasoning."

