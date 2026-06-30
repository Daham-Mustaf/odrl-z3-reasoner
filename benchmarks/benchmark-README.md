# ODRL-SA Benchmark Suite

Sound conflict detection problems from ODRL (Open Digital Rights Language) policies,
encoded as SMT-LIB 2.6 instances in QF-LRA and QF-LIA.

## Problem Families

| Family   | Description                          | Logic  | Problems | Status Mix      |
|----------|--------------------------------------|--------|----------|-----------------|
| ODRL-BND | Bounded-domain constraint conflicts  | QF-LRA | ~80      | sat + unsat     |
| ODRL-DNT | Deontic conflicts (perm ∩ prohib)    | QF-LRA | ~30      | sat + unsat     |
| ODRL-UNT | Unit-dependent conflicts             | QF-LRA | ~100     | sat + unsat     |
| ODRL-MIX | Multi-constraint interactions        | Mixed  | ~20      | sat + unsat     |
| ODRL-INH | Inheritance validation               | Mixed  | ~20      | sat + unsat     |

## Interpretation

These problems encode ODRL policy conflict detection. The SMT result maps to a
policy judgment:

| Context              | sat                | unsat          | unknown    |
|----------------------|--------------------|----------------|------------|
| Internal consistency | Rule is consistent | INTERNAL-CONFLICT | —        |
| Deontic check        | DEONTIC-CONFLICT   | No conflict    | —          |
| Inheritance check    | Child VIOLATES parent | Child is valid | —       |

## SZS Status Mapping

| SMT Result | SZS Status    | ODRL-SA Judgment    |
|------------|---------------|---------------------|
| sat        | Satisfiable   | COMPATIBLE or DEONTIC-CONFLICT (context-dependent) |
| unsat      | Unsatisfiable | CONFLICT or VALID-INHERITANCE (context-dependent)  |
| unknown    | GaveUp        | UNKNOWN             |

## Source

Generated from the ODRL-SA static analyzer test suite (214+ test cases).

- Tool: ODRL-SA (Fraunhofer FIT & RWTH Aachen University)
- Domain: W3C ODRL 2.2 (https://www.w3.org/TR/odrl-model/)
- Contact: Daham Mustafa (daham.mohammed.mustafa@fit.fraunhofer.de)

## File Format

Each `.smt2` file is a standalone SMT-LIB 2.6 problem with:
- `set-info :status` declaring expected result
- Comments documenting the ODRL source policy
- Domain bounds from the ODRL specification
- Constraint encoding following ODRL-SA's formal semantics
