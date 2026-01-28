Great questions! Let me answer each one and create a comprehensive main file:

## 1. Current Engine Capabilities & Where to Extend

| Feature | Status | Where to Change |
|---------|--------|-----------------|
| Policy metadata |  Parsed | `src/parser/ttl_parser.py` - `_extract_policy()` |
| Normalization |  Working | `src/normalizer/normalizer.py` + `src/config/operands.yaml` |
| Inheritance check | 🟡 Exists | `src/reasoner/inheritance_checker.py` |
| Add new operands |  Easy | `src/config/operands.yaml` + `src/core/abstract_domains.py` |
| Permission conflicts |  Working | Current engine |
| Prohibition conflicts |  Working | Current engine |
| Duty conflicts |  Working | Current engine |
| Permission vs Prohibition | 🟡 Partial | Needs cross-rule check |

## 2. Comprehensive Main File## Usage Examples

```bash
# Copy the comprehensive main
cp outputs/main_comprehensive.py main.py

# Basic analysis
uv run python main.py tests/ttl/percentage/percentage_conflict.ttl

# Verbose (shows constraints and rules)
uv run python main.py tests/ttl/percentage/percentage_conflict.ttl -v

# Debug (shows Z3 formulas)
uv run python main.py tests/ttl/percentage/percentage_conflict.ttl -d

# Show policy structure
uv run python main.py tests/ttl/percentage/percentage_conflict.ttl --show-policy

# Show normalization
uv run python main.py tests/ttl/percentage/percentage_overlap.ttl --show-normalize

# ALL debug output
uv run python main.py tests/ttl/percentage/percentage_conflict.ttl --all

# Analyze entire directory
uv run python main.py tests/ttl/percentage/

# JSON output
uv run python main.py tests/ttl/percentage/ --json

# Inheritance check (when implemented)
uv run python main.py parent.ttl child.ttl -v
```

## What Each Flag Shows

| Flag | Shows |
|------|-------|
| (none) | One-line summary per file |
| `-v` | Constraints, rules, models |
| `-d` | Z3 encoding, formulas, domains |
| `--show-policy` | Full policy structure (rules, targets) |
| `--show-normalize` | Value normalization process |
| `--all` | Everything above |
| `--json` | Machine-readable JSON |

## Current Capabilities

| Feature | Status |
|---------|--------|
|  Permission analysis | Working |
|  Prohibition analysis | Working |
|  Duty analysis | Working |
|  Internal conflicts (within rule) | Working |
|  Cross-rule conflicts (perm vs prohib) | Working |
|  Composite constraints (AND/OR/XONE) | Working |
|  Domain bounds | Working |
| 🟡 Inheritance check | Placeholder |

## Where to Extend

| To Add | File | Function |
|--------|------|----------|
| New operand | `src/config/operands.yaml` | Add entry |
| Domain bounds | `src/encoder/z3_encoder.py` | `DOMAIN_BOUNDS` |
| Abstract domain | `src/core/abstract_domains.py` | New class |
| Validator rules | `src/core/validator.py` | Add to dicts |
| Inheritance logic | `main.py` | `check_inheritance()` |
| New operator encoding | `src/encoder/z3_encoder.py` | `ConstraintEncoder.encode()` |