# Copy main.py
cp outputs/main.py .

# Test single file (basic)
uv run python main.py tests/ttl/percentage/percentage_conflict.ttl

# Test single file (verbose)
uv run python main.py tests/ttl/percentage/percentage_conflict.ttl -v

# Test single file (debug - shows Z3 formulas)
uv run python main.py tests/ttl/percentage/percentage_conflict.ttl -d

# Test single file (verbose + debug)
uv run python main.py tests/ttl/percentage/percentage_overlap.ttl -vd

uv run python main.py tests/ttl/percentage/policy_duty.ttl --all

# Test entire directory
uv run python main.py tests/ttl/percentage/

# JSON output
uv run python main.py tests/ttl/percentage/percentage_conflict.ttl --json
```


# Entire directory (normal)
uv run python main.py tests/ttl/percentage/

# Entire directory (verbose)
uv run python main.py tests/ttl/percentage/ -v

# Entire directory (debug)
uv run python main.py tests/ttl/percentage/ -d

# Entire directory (verbose + debug)
uv run python main.py tests/ttl/percentage/ -vd


