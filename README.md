# ODRL-SA: ODRL Static Analyzer

A formal verification tool for ODRL (Open Digital Rights Language) policies using Z3 SMT solver. ODRL-SA performs design-time conflict detection through sound abstract interpretation, identifying both internal constraint conflicts and deontic conflicts between permissions and prohibitions.

## Features

- **Policy Parsing**: Parse ODRL policies in Turtle (.ttl) format
- **Constraint Normalization**: Normalize constraint values with unit conversion
- **Z3 Encoding**: Encode ODRL constraints as SMT formulas
- **Conflict Detection**: Detect internal contradictions within rules
- **Deontic Analysis**: Identify permission/prohibition overlaps
- **Composite Constraints**: Support for `and`, `or`, `xone` logical operators
- **Multiple LeftOperands**: Support for `absoluteTemporalPosition`, `absolutePosition`, `absoluteSize`, `payAmount`, `resolution`, `dateTime`, `percentage`, and more

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Installation

#### Option 1: Using uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/odrl-z3-reasoner.git
cd odrl-z3-reasoner

# Install dependencies with uv
uv sync

# Run the analyzer
uv run python -m src analyze tests/ttl/resolution/01_eq_eq_conflict.ttl
```

#### Option 2: Using pip

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/odrl-z3-reasoner.git
cd odrl-z3-reasoner

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the analyzer
python -m src analyze tests/ttl/resolution/01_eq_eq_conflict.ttl
```

### Basic Usage

```bash
# Analyze a single policy file
uv run python -m src analyze path/to/policy.ttl

# Analyze all policies in a directory
uv run python -m src analyze tests/ttl/resolution/

# Run with verbose output
uv run python -m src analyze --verbose tests/ttl/payAmount/

# Generate JSON report
uv run python -m src analyze --output report.json tests/ttl/
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
    [permission] rule_1
      Action: play
      Target: http://example.org/video01
      Constraints: ['constraint_1']
    [prohibition] rule_2
      Action: play
      Target: http://example.org/video01
      Constraints: ['constraint_2']

[PERMISSION: rule_1]
----------------------------------------
  Action: play
  Formula: 200 >= absoluteTemporalPosition_default_default
  Result: [OK] POSSIBLY-COMPATIBLE
  Model: {'absoluteTemporalPosition_default_default': 0}

[PROHIBITION: rule_2]
----------------------------------------
  Action: play
  Formula: 100 <= absoluteTemporalPosition_default_default
  Result: [OK] POSSIBLY-COMPATIBLE
  Model: {'absoluteTemporalPosition_default_default': 100}

[Deontic Check: action=play]
----------------------------------------
  Deontic check: And(permission_formula, prohibition_formula)
  [CONFLICT] Deontic conflict for action 'play'
  Witness: {'absoluteTemporalPosition_default_default': 150}
```

## Project Structure

```
odrl-z3-reasoner/
├── src/
│   ├── analyzer/          # High-level policy analysis
│   ├── core/              # Core types and classifiers
│   ├── encoder/           # Z3 SMT encoding
│   ├── grounding/         # Semantic grounding (language, units, etc.)
│   ├── normalizer/        # Value normalization
│   ├── parser/            # Turtle policy parser
│   ├── reasoner/          # Conflict detection logic
│   ├── registry/          # Operand registry
│   └── reporting/         # Output formatting
├── tests/
│   └── ttl/               # Test policies organized by operand
├── docs/                  # Documentation
└── data/                  # External data (ontologies, etc.)
```

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src

# Run specific test file
uv run pytest tests/test_encoder.py -v

# Run tests for specific operand
uv run pytest -k "resolution"
```

## Supported ODRL LeftOperands

| LeftOperand | Description | Unit Support |
|-------------|-------------|--------------|
| `absoluteTemporalPosition` | Position in time stream (seconds) | ✓ |
| `absolutePosition` | Position in sequence | ✓ |
| `absoluteSize` | Size measurement | ✓ |
| `payAmount` | Payment amount | Currency |
| `resolution` | Image/display resolution | dpi/ppi |
| `dateTime` | Date/time constraints | ISO 8601 |
| `percentage` | Percentage values | 0-100 |
| `relativePosition` | Relative positioning | ✓ |
| `relativeSize` | Relative size | ✓ |
| `timeInterval` | Time duration | ISO 8601 |
| `count` | Count constraints | ✓ |
| `elapsedTime` | Elapsed time | Duration |

## Supported Operators

- **Comparison**: `eq`, `neq`, `lt`, `lteq`, `gt`, `gteq`
- **Set**: `isAnyOf`, `isNoneOf`, `isAllOf`
- **Logical (composite)**: `and`, `or`, `xone`

## Writing Test Policies

Example Turtle policy with a conflict:

```turtle
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix ex: <http://example.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

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

### Operand Configuration

Operands are configured in `src/config/operands.yaml`:

```yaml
resolution:
  type: numeric
  domain: non_negative
  unit_dimension: resolution
  default_unit: dpi
```

### Operator Configuration

Operators are configured in `src/config/operators.yaml`.

## Documentation

- [Implementation Status](docs/IMPLEMENTATION_STATUS.md)
- [Theoretical Foundations](docs/odrl-theoretical-foundations.md)
- [ODRL-SA Capabilities](docs/ODRL-SA-CAPABILITIES.md)
- [XSD-Grounded Constraints](docs/XSD-Grounded-ODRL-Constraints.md)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`uv run pytest`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## License

[Add your license here]

## Citation

If you use ODRL-SA in your research, please cite:

```bibtex
@software{odrl_sa,
  title = {ODRL-SA: A Formal Verification Tool for ODRL Policies},
  author = {Daham Jayawardena},
  year = {2025},
  url = {https://github.com/YOUR_USERNAME/odrl-z3-reasoner}
}
```
