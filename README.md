# ODRL-SA: ODRL Static Analyzer

A formal conflict-detection tool for ODRL (Open Digital Rights Language) policies, built on the
Z3 SMT solver. Given one or two ODRL policies in Turtle, ODRL-SA decides at design time whether
their constraints can be satisfied together, returning a three-valued verdict
(`CONFLICT`, `POSSIBLY-COMPATIBLE`, `UNKNOWN`) with a witness model or an explanation.

ODRL-SA is one engine that covers ODRL constraints across three categories:

- **Self-contained constraints**, decidable from the operand's datatype and domain alone.
- **Temporal constraints**, where instants, durations, and recurrence interact.
- **External knowledge base constraints**, whose meaning depends on an external vocabulary.

On top of constraint-level conflict, it performs deontic analysis: detecting overlaps between
permissions and prohibitions over the same action and target.

---

## What it detects

ODRL-SA decides conflict through sound abstract interpretation: each constraint denotes a region
of its operand's domain, and two constraints conflict when those regions cannot be satisfied
together. The same three-valued judgment applies to all three categories below; the difference is
how a constraint's region is derived.

### 1. Self-contained constraints

Constraints whose conflict is decidable from the operand's XSD datatype and domain, with no
external lookup. Numeric operands (`count`, `percentage`, `payAmount`, `resolution`,
`absolutePosition`, `absoluteSize`, `relativePosition`, `relativeSize`,
`absoluteTemporalPosition`) and `dateTime` fall here. Each comparison denotes an interval over the
operand's domain, and conflict reduces to interval disjointness. This is the core, fully
implemented path.

### 2. Temporal constraints

Constraints over time, where the operands are not independent. ODRL-SA separates the two temporal
sorts, instants and durations, so the comparison operators are read correctly per sort (an `lt` on
`dateTime` means "earlier than"; an `lt` on a duration means "shorter than"). It covers:

- the instant operand `dateTime`,
- the duration operands `elapsedTime`, `meteredTime`, `delayPeriod`,
- the recurrence operand `timeInterval` (a condition that repeats every period),
- cross-operand relations that hold in every execution, for example metered usage never exceeding
  elapsed time, and delay never exceeding elapsed time,
- ordered sequencing via `andSequence`, where a delay is measured from the previous satisfaction.

This is the path being extended with the sort-stratified semantics (see Status). The other two
categories do not depend on it.

### 3. External knowledge base constraints

Constraints whose values are terms from an external vocabulary, so deciding comparability and
conflict needs semantic grounding rather than datatype reasoning alone. ODRL-SA grounds values
through pluggable oracles before comparing:

- **units** via QUDT (so `EUR` and `euro` are recognised as the same, and incompatible dimensions
  are flagged),
- **languages** and **media types / file formats** via IANA,
- **purposes** via DPV,

and more under `src/grounding`. When the required oracle is unavailable, ODRL-SA returns `UNKNOWN`
rather than guessing, which keeps the analysis sound.

### Verdicts

Every comparison yields one of three values, in order `CONFLICT` below `UNKNOWN` below
`POSSIBLY-COMPATIBLE`:

- `CONFLICT`: the two constraints cannot be satisfied together (a contradiction).
- `POSSIBLY-COMPATIBLE`: they can be satisfied together (a witness model is returned).
- `UNKNOWN`: the result is undetermined, because only one side constrains the operand, the
  operands are not comparable, or a required oracle is missing.

`CONFLICT` and `POSSIBLY-COMPATIBLE` are determinate; `UNKNOWN` is epistemic. Rule- and
policy-level judgments aggregate the per-constraint verdicts conservatively (the worst verdict
wins).

---

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Installation

#### Option 1: Using uv (recommended)

```bash
git clone https://github.com/Daham-Mustaf/odrl-z3-reasoner.git
cd odrl-z3-reasoner

# Install dependencies from the lockfile
uv sync

# Run the analyzer
uv run python main.py tests/ttl/resolution/01_eq_eq_conflict.ttl
```

#### Option 2: Using pip

```bash
git clone https://github.com/Daham-Mustaf/odrl-z3-reasoner.git
cd odrl-z3-reasoner

python -m venv .venv
source .venv/bin/activate        # On Windows: .venv\Scripts\activate

# Editable install from pyproject.toml (pulls z3-solver, rdflib, etc.)
pip install -e .

# Run the analyzer
python main.py tests/ttl/resolution/01_eq_eq_conflict.ttl
```

### Basic Usage

```bash
# Analyze a single policy file
uv run python main.py analyze path/to/policy.ttl

# Analyze all policies in a directory
uv run python main.py tests/ttl/resolution/

# Verbose output (show all analysis levels)
uv run python main.py --verbose tests/ttl/payAmount/

# JSON report
uv run python main.py --json tests/ttl/
```

## Example Output

```
============================================================
ANALYZING: 09_deontic_overlap_conflict.ttl
============================================================
[POLICY STRUCTURE]
----------------------------------------
  Policy ID: http://example.org/policy01
  Type: Set
  Rules:
    [permission] rule_1   Action: play   Constraints: ['constraint_1']
    [prohibition] rule_2  Action: play   Constraints: ['constraint_2']

[PERMISSION: rule_1]
  Formula: absoluteTemporalPosition <= 200
  Result: [OK] POSSIBLY-COMPATIBLE

[PROHIBITION: rule_2]
  Formula: absoluteTemporalPosition >= 100
  Result: [OK] POSSIBLY-COMPATIBLE

[Deontic Check: action=play]
  Deontic check: And(permission_formula, prohibition_formula)
  [CONFLICT] Deontic conflict for action 'play'
  Witness: {'absoluteTemporalPosition': 150}
```

The permission allows positions up to 200 and the prohibition forbids positions from 100, so any
value in [100, 200] is both permitted and prohibited: a deontic conflict, witnessed at 150.

## Project Structure

```
odrl-z3-reasoner/
├── src/
│   ├── analyzer/          # High-level policy analysis (orchestration, conflict levels)
│   ├── core/              # Core types, classifier, three-valued judgment
│   ├── encoder/           # Z3 SMT encoding and abstract domains
│   ├── grounding/         # External-KB oracles (units, language, purpose, formats)
│   ├── normalizer/        # Value normalization (units, durations)
│   ├── parser/            # Turtle policy parser
│   ├── reasoner/          # Conflict detection logic
│   ├── registry/          # Operand registry
│   └── reporting/         # Output formatting
├── tests/
│   └── ttl/               # Test policies organized by operand
├── docs/                  # Documentation
└── data/                  # External vocabularies (ontologies, etc.)
```

## Running Tests

```bash
uv run pytest                       # all tests
uv run pytest --cov=src             # with coverage
uv run pytest tests/test_encoder.py -v
uv run pytest -k "resolution"       # tests for one operand
```

## Supported ODRL LeftOperands

Grouped by the category that decides them.

| Category | LeftOperand | Notes |
|---|---|---|
| Self-contained | `count` | non-negative integer |
| Self-contained | `percentage` | 0 to 100 |
| Self-contained | `payAmount` | currency (unit-grounded) |
| Self-contained | `resolution` | dpi / ppi (unit-grounded) |
| Self-contained | `absolutePosition`, `absoluteSize` | unit-grounded |
| Self-contained | `relativePosition`, `relativeSize` | proportional |
| Self-contained | `absoluteTemporalPosition` | position in a media stream (seconds) |
| Temporal | `dateTime` | instant (ISO 8601) |
| Temporal | `elapsedTime`, `meteredTime`, `delayPeriod` | duration (ISO 8601) |
| Temporal | `timeInterval` | recurrence period (ISO 8601) |
| External KB | language, media type, purpose values | grounded via IANA / DPV oracles |

## Supported Operators

- **Comparison**: `eq`, `neq`, `lt`, `lteq`, `gt`, `gteq`
- **Set**: `isAnyOf`, `isNoneOf`, `isAllOf`
- **Logical (composite)**: `and`, `or`, `xone`, `andSequence`

## Writing Test Policies

```turtle
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix ex:   <http://example.org/> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

ex:policy01 a odrl:Set ;
    odrl:permission ex:rule_1 ;
    odrl:prohibition ex:rule_2 .

ex:rule_1 a odrl:Permission ;
    odrl:action odrl:play ;
    odrl:target ex:video01 ;
    odrl:constraint ex:constraint_1 .

ex:rule_2 a odrl:Prohibition ;
    odrl:action odrl:play ;
    odrl:target ex:video01 ;
    odrl:constraint ex:constraint_2 .

ex:constraint_1 a odrl:Constraint ;
    odrl:leftOperand odrl:absoluteTemporalPosition ;
    odrl:operator odrl:lteq ;
    odrl:rightOperand "200"^^xsd:decimal .

ex:constraint_2 a odrl:Constraint ;
    odrl:leftOperand odrl:absoluteTemporalPosition ;
    odrl:operator odrl:gteq ;
    odrl:rightOperand "100"^^xsd:decimal .
```

## Configuration

Operands are configured in `src/config/operands.yaml`:

```yaml
resolution:
  type: numeric
  domain: non_negative
  unit_dimension: resolution
  default_unit: dpi
```

Operators are configured in `src/config/operators.yaml`.

## Status

ODRL-SA is in active development toward a usable release. The self-contained and external-KB
categories, the three-valued judgment, and deontic analysis are implemented. The temporal category
is being extended with sort-stratified semantics: separating instants from durations, modelling
`timeInterval` recurrence, adding the cross-operand relations (metered at most elapsed, delay at
most elapsed), and giving `andSequence` a real ordered semantics rather than treating it as `and`.
Until that lands, temporal verdicts on durations, recurrence, and sequences should be treated as
provisional.

## Documentation

- [Implementation Status](docs/IMPLEMENTATION_STATUS.md)
- [Theoretical Foundations](docs/odrl-theoretical-foundations.md)
- [ODRL-SA Capabilities](docs/ODRL-SA-CAPABILITIES.md)
- [XSD-Grounded Constraints](docs/XSD-Grounded-ODRL-Constraints.md)

## Contributing

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Run the tests (`uv run pytest`).
4. Commit your changes.
5. Open a Pull Request.

## License

Released under the MIT License. See [LICENSE](LICENSE) for the full text.

Note on the copyright holder: because this work originates in a research context (Fraunhofer FIT
and RWTH Aachen University), confirm with your institution's IP or technology-transfer office that
the holder named in `LICENSE` is correct and that a permissive license is permitted before
publishing. If you need an explicit patent grant or contributor terms, Apache License 2.0 is the
common alternative.

## Citation

```bibtex
@software{odrl_sa,
  title  = {ODRL-SA: A Formal Verification Tool for ODRL Policies},
  author = {Daham Mustafa},
  year   = {2026},
  url    = {https://github.com/Daham-Mustaf/odrl-z3-reasoner}
}
```