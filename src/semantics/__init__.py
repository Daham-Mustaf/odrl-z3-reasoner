# src/semantics/__init__.py
"""
ODRL-SA Semantics Module

Combines NEW ODRL-SA formal components with EXISTING backward-compatible code.
"""

# =============================================================================
# NEW: ODRL-SA FORMAL COMPONENTS
# =============================================================================

# Judgment types (§7)
from .judgment import (
    Judgment,
    JudgmentResult,
    ConstraintClass,
    IncomparabilityReason,
    OracleResult,
    TruthValue,
    judgment_meet,
    judgment_join,
)

# Classification (§6)
from .classifier import (
    classify_constraint,
    classify_constraints,
    get_classification_stats,
    L_XSD,
    L_REF,
    L_SEM,
    L_RUN,
    L_ALL,
)

# Comparability (§7 Definition 10)
from .comparability import (
    is_comparable,
    ComparabilityResult,
    check_same_operand,
    check_analyzable_class,
    check_unit_compatible,
    check_scope_compatible,
    check_temporal_compatible,
    check_operator_valid,
    OPERATOR_RESTRICTIONS,
    TEMPORAL_REFERENCE_POINT,
    TEMPORAL_ABSOLUTE,
)

# Oracles (§9 Definition 15)
from .oracle import (
    GroundingOracle,
    NullOracle,
    LanguageOracle,
    SpatialOracle,
    PurposeOracle,
    CompositeOracle,
    CachingOracle,
    create_default_oracle,
    create_null_oracle,
)

# Judgment Engine
from .judgment_engine import (
    JudgmentEngine,
    create_engine,
    Interval,
    encode_constraint_to_z3,
    encode_domain_bounds,
    get_z3_sort,
    get_domain_bounds,
    DOMAIN_BOUNDS,
)

# Constraint types (UPDATED for ODRL-SA)
from .constraint_types import (
    AtomicConstraint,
    CompositeConstraint,
    Constraint,
    OperatorType,
    LogicalOperatorType,
    RightValue,
    ODRLMetadata,
    ValueDomain,
    Z3Sort,
)

# =============================================================================
# EXISTING: BACKWARD COMPATIBLE COMPONENTS
# =============================================================================

# Operand registry
from .operand_registry import (
    get_operand_info,
    get_all_operands,
    get_operands_by_category,
    get_operands_by_grounding,
    get_registry_statistics,
    OperandInfo,
    OperandCategory,
    XSDType,
    Z3SortType,
    GroundingType,
    OPERAND_REGISTRY,
)

# Operators (matching actual exports in operators.py)
from .operators import (
    # Functions
    parse_operator,
    get_operator_type,
    get_operator_category,
    is_relational_operator,
    is_set_operator,
    is_taxonomic_operator,
    is_logical_operator,
    requires_semantic_grounding,
    get_valid_operators_for_domain,
    is_operator_valid_for_domain,
    operator_to_z3,
    get_z3_relational_func,
    get_operator_semantics,
    get_smtlib_operator,
    encode_relational_smtlib,
    encode_xone_smtlib,
    # Classes
    Operator,
    OperatorCategory as OpCategory,
    # Constants
    RELATIONAL_OPERATORS,
    SET_OPERATORS,
    TAXONOMIC_OPERATORS,
    LOGICAL_OPERATORS,
    CONSTRAINT_OPERATORS,
    OPERATOR_STRING_MAP,
    OPERATOR_TO_STRING,
    OPERATOR_SYMBOLS,
    VALID_OPERATORS_BY_DOMAIN,
    OPERATOR_SEMANTICS,
)

# Domains
from .domains import (
    get_domain_bounds as get_operand_domain_bounds,
    validate_value_in_domain,
    get_z3_domain_assertions,
    DomainBounds,
)

# Units
from .units import (
    are_units_compatible,
    check_unit_compatibility,
    normalize_unit,
    UnitCompatibility,
)

# Durations
from .durations import (
    parse_duration,
    parse_duration_to_seconds,
    duration_to_seconds,
    normalize_duration,
)

# Grounding (legacy)
from .grounding import (
    is_self_contained,
    is_statically_analyzable,
    get_grounding_requirement,
    GroundingRequirement,
)

# Validator
from .validator import (
    validate_constraint,
    ValidationResult,
    ValidationSeverity,
)

# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    # === NEW: ODRL-SA ===
    "Judgment",
    "JudgmentResult", 
    "ConstraintClass",
    "IncomparabilityReason",
    "OracleResult",
    "TruthValue",
    "judgment_meet",
    "judgment_join",
    "classify_constraint",
    "classify_constraints",
    "get_classification_stats",
    "L_XSD",
    "L_REF", 
    "L_SEM",
    "L_RUN",
    "L_ALL",
    "is_comparable",
    "ComparabilityResult",
    "check_same_operand",
    "check_analyzable_class",
    "check_unit_compatible",
    "check_scope_compatible",
    "check_temporal_compatible",
    "check_operator_valid",
    "OPERATOR_RESTRICTIONS",
    "TEMPORAL_REFERENCE_POINT",
    "TEMPORAL_ABSOLUTE",
    "GroundingOracle",
    "NullOracle",
    "LanguageOracle",
    "SpatialOracle",
    "PurposeOracle",
    "CompositeOracle",
    "CachingOracle",
    "create_default_oracle",
    "create_null_oracle",
    "JudgmentEngine",
    "create_engine",
    "Interval",
    "encode_constraint_to_z3",
    "encode_domain_bounds",
    "get_z3_sort",
    "get_domain_bounds",
    "DOMAIN_BOUNDS",
    "AtomicConstraint",
    "CompositeConstraint",
    "Constraint",
    "OperatorType",
    "LogicalOperatorType",
    "RightValue",
    "ODRLMetadata",
    "ValueDomain",
    "Z3Sort",
    
    # === EXISTING ===
    # Operand registry
    "get_operand_info",
    "get_all_operands",
    "get_operands_by_category",
    "get_operands_by_grounding",
    "get_registry_statistics",
    "OperandInfo",
    "OperandCategory",
    "XSDType",
    "Z3SortType",
    "GroundingType",
    "OPERAND_REGISTRY",
    # Operators
    "parse_operator",
    "get_operator_type",
    "get_operator_category",
    "is_relational_operator",
    "is_set_operator",
    "is_taxonomic_operator",
    "is_logical_operator",
    "requires_semantic_grounding",
    "get_valid_operators_for_domain",
    "is_operator_valid_for_domain",
    "operator_to_z3",
    "get_z3_relational_func",
    "get_operator_semantics",
    "get_smtlib_operator",
    "encode_relational_smtlib",
    "encode_xone_smtlib",
    "Operator",
    "OpCategory",
    "RELATIONAL_OPERATORS",
    "SET_OPERATORS",
    "TAXONOMIC_OPERATORS",
    "LOGICAL_OPERATORS",
    "CONSTRAINT_OPERATORS",
    "OPERATOR_STRING_MAP",
    "OPERATOR_TO_STRING",
    "OPERATOR_SYMBOLS",
    "VALID_OPERATORS_BY_DOMAIN",
    "OPERATOR_SEMANTICS",
    # Domains
    "get_operand_domain_bounds",
    "validate_value_in_domain",
    "get_z3_domain_assertions",
    "DomainBounds",
    # Units
    "are_units_compatible",
    "check_unit_compatibility",
    "normalize_unit",
    "UnitCompatibility",
    # Durations
    "parse_duration",
    "parse_duration_to_seconds",
    "duration_to_seconds",
    "normalize_duration",
    # Grounding
    "is_self_contained",
    "is_statically_analyzable",
    "get_grounding_requirement",
    "GroundingRequirement",
    # Validator
    "validate_constraint",
    "ValidationResult",
    "ValidationSeverity",
]