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

uv run python main.py tests/ttl/dateTime/ --all


echo ""
echo "--- payAmount Tests ---"
uv run python main.py tests/ttl/unit_dependent/payAmount/ --all

echo ""
echo "--- resolution Tests ---"
uv run python main.py tests/ttl/unit_dependent/resolution/ --all


uv run python main.py tests/ttl/unit_dependent/absoluteSize/ --all
uv run python main.py tests/ttl/unit_dependent/absolutePosition/ --all
uv run python main.py tests/ttl/relativePosition --all
uv run python main.py tests/ttl/relativeSize --all
uv run python main.py tests/ttl/relativeTemporalPosition/ --all
uv run python main.py tests/ttl/relativeSpatialPosition/ --al

uv run python main.py tests/ttl/absolutePosition --all
uv run python main.py tests/ttl/absoluteTemporalPosition --all


uv run python main.py tests/ttl/elapsedTime --all

uv run python main.py tests/ttl/delayPeriod --all

uv run python main.py tests/ttl/delayPeriod/test_odrl_inheritance.ttl --all

