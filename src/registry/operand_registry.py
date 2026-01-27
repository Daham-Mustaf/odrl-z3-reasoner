# src/registry/operand_registry.py
"""
ODRL-SA Operand Registry

The central registry that reads configuration and provides a unified API
for all modules. This is the ONLY place that knows about operand definitions.

All other modules (classifier, encoder, normalizer, judgment) use this registry
instead of hardcoding operand information.

Benefits:
- Change formalism by editing config file, not code
- Single source of truth
- Easy to test different formalisms
- Clean separation of concerns

Usage:
    from registry import OperandRegistry
    
    registry = OperandRegistry()
    
    # Get operand info
    info = registry.get_operand("count")
    print(info.constraint_class)  # FULL
    print(info.domain)            # (0, None)
    
    # Get all operands of a class
    full_ops = registry.get_operands_by_class(ConstraintClass.FULL)
    
    # Check if operand needs oracle
    if registry.needs_oracle("language"):
        oracle = registry.get_oracle("language")
"""

from typing import Dict, List, Optional, Set, Any, Tuple, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import yaml
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTRAINT CLASS ENUM
# =============================================================================

class ConstraintClass(Enum):
    """
    Constraint classification per Definition 4:
        L = L_xsd ⊎ L_ref ⊎ L_sem ⊎ L_run
        where L_sem = L_kb ⊎ L_deref
    """
    FULL = "FULL"           # L_xsd: XSD-typed, fully analyzable
    PARTIAL = "PARTIAL"     # L_ref: Reference-point dependent
    GROUNDED = "GROUNDED"   # L_kb: Requires KB/ontology
    DEFERRED = "DEFERRED"   # L_deref: Requires runtime dereferencing
    RUNTIME = "RUNTIME"     # L_run: Runtime-only
    
    def can_analyze_statically(self) -> bool:
        """Can we produce CONFLICT/POSSIBLY-COMPATIBLE?"""
        return self in {ConstraintClass.FULL, ConstraintClass.PARTIAL}
    
    def needs_oracle(self) -> bool:
        """Does this class need an oracle?"""
        return self == ConstraintClass.GROUNDED


# =============================================================================
# Z3 SORT ENUM
# =============================================================================

class Z3Sort(Enum):
    """Z3 solver sort types."""
    INT = "Int"
    REAL = "Real"
    STRING = "String"
    BOOL = "Bool"


# =============================================================================
# OPERAND INFO
# =============================================================================

@dataclass(frozen=True)
class OperandInfo:
    """
    Complete information about an ODRL LeftOperand.
    
    This is the structured representation of the YAML config.
    Immutable (frozen) for safety.
    """
    name: str
    """Operand name (e.g., 'count', 'language')"""
    
    constraint_class: ConstraintClass
    """Classification: FULL, PARTIAL, GROUNDED, DEFERRED, RUNTIME"""
    
    category: str
    """Category: numeric, temporal, positional, categorical, identity"""
    
    z3_sort: Optional[Z3Sort] = None
    """Z3 sort for SMT encoding (None for non-analyzable)"""
    
    domain_min: Optional[float] = None
    """Minimum value (None = -infinity)"""
    
    domain_max: Optional[float] = None
    """Maximum value (None = +infinity)"""
    
    normalizer: str = "none"
    """Normalization function name"""
    
    operators: Tuple[str, ...] = field(default_factory=tuple)
    """Valid operators for this operand"""
    
    oracle_name: Optional[str] = None
    """Oracle class name (for GROUNDED)"""
    
    oracle_data: Optional[str] = None
    """Oracle data file (for GROUNDED)"""
    
    oracle_implemented: bool = False
    """Is the oracle implemented?"""
    
    reference_point: Optional[str] = None
    """Reference point type (for PARTIAL)"""
    
    unit_required: bool = False
    """Does this operand require a unit?"""
    
    description: str = ""
    """Human-readable description"""
    
    @property
    def domain(self) -> Tuple[Optional[float], Optional[float]]:
        """Get domain as (min, max) tuple."""
        return (self.domain_min, self.domain_max)
    
    @property
    def is_bounded(self) -> bool:
        """Does this operand have finite bounds?"""
        return self.domain_min is not None or self.domain_max is not None
    
    def __str__(self) -> str:
        return f"{self.name} ({self.constraint_class.value})"


# =============================================================================
# OPERATOR INFO
# =============================================================================

@dataclass(frozen=True)
class OperatorInfo:
    """Information about an ODRL operator."""
    name: str
    symbol: str
    description: str
    category: str  # comparison, set_based, logical
    requires_oracle: bool = False
    requires_ordering: bool = False
    oracle_method: Optional[str] = None
    z3_encoding: Optional[str] = None
    inverse: Optional[str] = None


# =============================================================================
# OPERAND REGISTRY
# =============================================================================

class OperandRegistry:
    """
    Central registry for ODRL operand and operator information.
    
    Reads from YAML configuration files and provides a unified API.
    All modules should use this registry instead of hardcoding.
    """
    
    _instance: Optional['OperandRegistry'] = None
    _initialized: bool = False
    
    def __new__(cls, config_dir: Optional[str] = None):
        """Singleton pattern - only one registry instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize registry from configuration files.
        
        Args:
            config_dir: Directory containing operands.yaml and operators.yaml
                       If None, uses default location.
        """
        if OperandRegistry._initialized and config_dir is None:
            return
        
        # Find config directory
        if config_dir is None:
            # Try several locations
            possible_paths = [
                Path(__file__).parent.parent / "config",
                Path(__file__).parent.parent.parent / "config",
                Path.cwd() / "config",
                Path.cwd() / "src" / "config",
            ]
            for path in possible_paths:
                if (path / "operands.yaml").exists():
                    config_dir = str(path)
                    break
        
        if config_dir is None:
            logger.warning("Config directory not found, using defaults")
            self._init_defaults()
            return
        
        self._config_dir = Path(config_dir)
        self._operands: Dict[str, OperandInfo] = {}
        self._operators: Dict[str, OperatorInfo] = {}
        self._class_index: Dict[ConstraintClass, Set[str]] = {c: set() for c in ConstraintClass}
        self._category_index: Dict[str, Set[str]] = {}
        
        # Load configurations
        self._load_operands()
        self._load_operators()
        
        OperandRegistry._initialized = True
        logger.info(f"OperandRegistry initialized with {len(self._operands)} operands")
    
    def _init_defaults(self):
        """Initialize with hardcoded defaults (fallback)."""
        self._operands = {}
        self._operators = {}
        self._class_index = {c: set() for c in ConstraintClass}
        self._category_index = {}
        OperandRegistry._initialized = True
    
    def _load_operands(self):
        """Load operands from YAML file."""
        operands_file = self._config_dir / "operands.yaml"
        
        if not operands_file.exists():
            logger.error(f"Operands file not found: {operands_file}")
            return
        
        with open(operands_file, 'r') as f:
            data = yaml.safe_load(f)
        
        for name, config in data.items():
            # Skip metadata
            if name.startswith('_'):
                continue
            
            # Parse constraint class
            class_str = config.get('class', 'RUNTIME')
            try:
                constraint_class = ConstraintClass(class_str)
            except ValueError:
                logger.warning(f"Unknown class '{class_str}' for {name}, using RUNTIME")
                constraint_class = ConstraintClass.RUNTIME
            
            # Parse Z3 sort
            z3_sort = None
            sort_str = config.get('z3_sort')
            if sort_str:
                try:
                    z3_sort = Z3Sort(sort_str)
                except ValueError:
                    logger.warning(f"Unknown z3_sort '{sort_str}' for {name}")
            
            # Parse domain
            domain = config.get('domain', {})
            domain_min = domain.get('min')
            domain_max = domain.get('max')
            
            # Parse operators
            operators = tuple(config.get('operators', []))
            
            # Create OperandInfo
            info = OperandInfo(
                name=name,
                constraint_class=constraint_class,
                category=config.get('category', 'unknown'),
                z3_sort=z3_sort,
                domain_min=domain_min,
                domain_max=domain_max,
                normalizer=config.get('normalize', 'none'),
                operators=operators,
                oracle_name=config.get('oracle'),
                oracle_data=config.get('oracle_data'),
                oracle_implemented=config.get('implemented', False),
                reference_point=config.get('reference_point'),
                unit_required=config.get('unit_required', False),
                description=config.get('description', ''),
            )
            
            self._operands[name] = info
            
            # Update indices
            self._class_index[constraint_class].add(name)
            
            category = info.category
            if category not in self._category_index:
                self._category_index[category] = set()
            self._category_index[category].add(name)
        
        logger.info(f"Loaded {len(self._operands)} operands from {operands_file}")
    
    def _load_operators(self):
        """Load operators from YAML file."""
        operators_file = self._config_dir / "operators.yaml"
        
        if not operators_file.exists():
            logger.warning(f"Operators file not found: {operators_file}")
            return
        
        with open(operators_file, 'r') as f:
            data = yaml.safe_load(f)
        
        # Load comparison operators
        for name, config in data.get('comparison', {}).items():
            self._operators[name] = OperatorInfo(
                name=name,
                symbol=config.get('symbol', name),
                description=config.get('description', ''),
                category='comparison',
                requires_ordering=config.get('requires_ordering', False),
                z3_encoding=config.get('z3_encoding'),
                inverse=config.get('inverse'),
            )
        
        # Load set-based operators
        for name, config in data.get('set_based', {}).items():
            self._operators[name] = OperatorInfo(
                name=name,
                symbol=config.get('symbol', name),
                description=config.get('description', ''),
                category='set_based',
                requires_oracle=config.get('requires_oracle', True),
                oracle_method=config.get('oracle_method'),
                inverse=config.get('inverse'),
            )
        
        # Load logical operators
        for name, config in data.get('logical', {}).items():
            self._operators[name] = OperatorInfo(
                name=name,
                symbol=config.get('symbol', name),
                description=config.get('description', ''),
                category='logical',
                z3_encoding=config.get('z3_encoding'),
            )
        
        logger.info(f"Loaded {len(self._operators)} operators from {operators_file}")
    
    # =========================================================================
    # OPERAND QUERIES
    # =========================================================================
    
    def get_operand(self, name: str) -> Optional[OperandInfo]:
        """
        Get information about an operand.
        
        Args:
            name: Operand name (e.g., 'count', 'language')
                  Can include URI prefix which will be stripped.
        
        Returns:
            OperandInfo or None if not found
        """
        # Normalize: strip URI prefix
        if '#' in name:
            name = name.split('#')[-1]
        elif '/' in name:
            name = name.split('/')[-1]
        
        return self._operands.get(name)
    
    def get_class(self, name: str) -> ConstraintClass:
        """Get the constraint class for an operand."""
        info = self.get_operand(name)
        if info:
            return info.constraint_class
        return ConstraintClass.RUNTIME  # Default: most conservative
    
    def get_domain(self, name: str) -> Tuple[Optional[float], Optional[float]]:
        """Get the domain bounds for an operand."""
        info = self.get_operand(name)
        if info:
            return info.domain
        return (None, None)
    
    def get_z3_sort(self, name: str) -> Optional[Z3Sort]:
        """Get the Z3 sort for an operand."""
        info = self.get_operand(name)
        if info:
            return info.z3_sort
        return None
    
    def get_normalizer(self, name: str) -> str:
        """Get the normalizer function name for an operand."""
        info = self.get_operand(name)
        if info:
            return info.normalizer
        return "none"
    
    def get_oracle_name(self, name: str) -> Optional[str]:
        """Get the oracle class name for an operand."""
        info = self.get_operand(name)
        if info:
            return info.oracle_name
        return None
    
    def needs_oracle(self, name: str) -> bool:
        """Check if an operand needs an oracle."""
        info = self.get_operand(name)
        if info:
            return info.constraint_class == ConstraintClass.GROUNDED
        return False
    
    def is_oracle_implemented(self, name: str) -> bool:
        """Check if the oracle for an operand is implemented."""
        info = self.get_operand(name)
        if info:
            return info.oracle_implemented
        return False
    
    def requires_unit(self, name: str) -> bool:
        """Check if an operand requires a unit."""
        info = self.get_operand(name)
        if info:
            return info.unit_required
        return False
    
    # =========================================================================
    # BULK QUERIES
    # =========================================================================
    
    def get_operands_by_class(self, constraint_class: ConstraintClass) -> Set[str]:
        """Get all operand names for a constraint class."""
        return self._class_index.get(constraint_class, set()).copy()
    
    def get_operands_by_category(self, category: str) -> Set[str]:
        """Get all operand names for a category."""
        return self._category_index.get(category, set()).copy()
    
    def get_all_operands(self) -> List[str]:
        """Get all operand names."""
        return list(self._operands.keys())
    
    def get_full_operands(self) -> Set[str]:
        """Get all FULL class operands (L_xsd)."""
        return self.get_operands_by_class(ConstraintClass.FULL)
    
    def get_partial_operands(self) -> Set[str]:
        """Get all PARTIAL class operands (L_ref)."""
        return self.get_operands_by_class(ConstraintClass.PARTIAL)
    
    def get_grounded_operands(self) -> Set[str]:
        """Get all GROUNDED class operands (L_kb)."""
        return self.get_operands_by_class(ConstraintClass.GROUNDED)
    
    def get_runtime_operands(self) -> Set[str]:
        """Get all RUNTIME class operands (L_run)."""
        return self.get_operands_by_class(ConstraintClass.RUNTIME)
    
    # =========================================================================
    # OPERATOR QUERIES
    # =========================================================================
    
    def get_operator(self, name: str) -> Optional[OperatorInfo]:
        """Get information about an operator."""
        # Normalize
        if '#' in name:
            name = name.split('#')[-1]
        elif '/' in name:
            name = name.split('/')[-1]
        
        return self._operators.get(name)
    
    def is_comparison_operator(self, name: str) -> bool:
        """Check if operator is a comparison operator."""
        op = self.get_operator(name)
        return op is not None and op.category == 'comparison'
    
    def is_set_operator(self, name: str) -> bool:
        """Check if operator is a set-based operator."""
        op = self.get_operator(name)
        return op is not None and op.category == 'set_based'
    
    def is_logical_operator(self, name: str) -> bool:
        """Check if operator is a logical operator."""
        op = self.get_operator(name)
        return op is not None and op.category == 'logical'
    
    def operator_requires_oracle(self, name: str) -> bool:
        """Check if operator requires an oracle."""
        op = self.get_operator(name)
        return op is not None and op.requires_oracle
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            'total_operands': len(self._operands),
            'class_counts': {
                c.value: len(ops) for c, ops in self._class_index.items()
            },
            'category_counts': {
                cat: len(ops) for cat, ops in self._category_index.items()
            },
            'total_operators': len(self._operators),
            'implemented_oracles': sum(
                1 for info in self._operands.values() 
                if info.oracle_implemented
            ),
        }
    
    def print_summary(self):
        """Print a summary of the registry."""
        stats = self.get_statistics()
        
        print("=" * 60)
        print("ODRL-SA Operand Registry")
        print("=" * 60)
        
        print(f"\nTotal Operands: {stats['total_operands']}")
        print("\nBy Class:")
        for cls, count in stats['class_counts'].items():
            pct = count / stats['total_operands'] * 100
            print(f"  {cls}: {count} ({pct:.0f}%)")
        
        print("\nBy Category:")
        for cat, count in stats['category_counts'].items():
            print(f"  {cat}: {count}")
        
        print(f"\nTotal Operators: {stats['total_operators']}")
        print(f"Implemented Oracles: {stats['implemented_oracles']}")
        
        print("=" * 60)


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_registry: Optional[OperandRegistry] = None


def get_registry(config_dir: Optional[str] = None) -> OperandRegistry:
    """
    Get the global registry instance.
    
    Args:
        config_dir: Optional config directory (only used on first call)
    
    Returns:
        OperandRegistry singleton
    """
    global _registry
    if _registry is None:
        _registry = OperandRegistry(config_dir)
    return _registry


def reset_registry():
    """Reset the global registry (for testing)."""
    global _registry
    _registry = None
    OperandRegistry._instance = None
    OperandRegistry._initialized = False


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    # Test the registry
    import sys
    
    # Find config directory
    config_dir = None
    for path in [Path.cwd() / "config", Path(__file__).parent.parent / "config"]:
        if path.exists():
            config_dir = str(path)
            break
    
    if config_dir:
        print(f"Using config: {config_dir}")
    
    registry = OperandRegistry(config_dir)
    registry.print_summary()
    
    print("\nSample Operand Queries:")
    for name in ["count", "dateTime", "elapsedTime", "language", "meteredTime"]:
        info = registry.get_operand(name)
        if info:
            print(f"  {name}: {info.constraint_class.value}, domain={info.domain}")
        else:
            print(f"  {name}: NOT FOUND")
