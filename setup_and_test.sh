#!/bin/bash
# setup_and_test.sh - MOVE SELF_CONTAINED TTL files and test

cd ~/Desktop/odrl-z3-reasoner

# Create directory
mkdir -p tests/test_data/self_contained

echo "=== Moving SELF_CONTAINED TTL files ==="

# Move from subdirectories
mv tests/test_data/atomic/*.ttl tests/test_data/self_contained/ 2>/dev/null || true
mv tests/test_data/logical/*.ttl tests/test_data/self_contained/ 2>/dev/null || true
mv tests/test_data/semantic/*.ttl tests/test_data/self_contained/ 2>/dev/null || true
mv tests/test_data/stress/*.ttl tests/test_data/self_contained/ 2>/dev/null || true
mv tests/test_data/temporal/*.ttl tests/test_data/self_contained/ 2>/dev/null || true

# Remove empty directories
rmdir tests/test_data/atomic tests/test_data/logical tests/test_data/semantic tests/test_data/stress tests/test_data/temporal 2>/dev/null || true

# Move individual files
mv tests/test_data/count_conflict.ttl tests/test_data/self_contained/ 2>/dev/null || true
mv tests/test_data/self_contained_test.ttl tests/test_data/self_contained/ 2>/dev/null || true
mv tests/test_data/no_conflict.ttl tests/test_data/self_contained/ 2>/dev/null || true
mv tests/test_data/and_composite.ttl tests/test_data/self_contained/ 2>/dev/null || true
mv tests/test_data/conflict_permission_prohibition.ttl tests/test_data/self_contained/ 2>/dev/null || true
mv tests/test_data/cross_currency_safe.ttl tests/test_data/self_contained/ 2>/dev/null || true
mv tests/test_data/policy_complex.ttl tests/test_data/self_contained/ 2>/dev/null || true
mv tests/test_data/policy_stress_test.ttl tests/test_data/self_contained/ 2>/dev/null || true
mv tests/test_data/xone_overlap.ttl tests/test_data/self_contained/ 2>/dev/null || true
mv tests/test_data/time_window_conflict.ttl tests/test_data/self_contained/ 2>/dev/null || true
mv tests/test_data/time_window_safe.ttl tests/test_data/self_contained/ 2>/dev/null || true
mv tests/test_data/mixed_constraints.ttl tests/test_data/self_contained/ 2>/dev/null || true

echo ""
echo "=== Files in self_contained ==="
ls tests/test_data/self_contained/
echo ""
echo "Total: $(ls tests/test_data/self_contained/*.ttl | wc -l) files"
echo ""

# Test all
echo "=== Testing all policies ==="

for f in tests/test_data/self_contained/*.ttl; do
    echo "────────────────────────────────────────"
    echo "Testing: $(basename $f)"
    uv run python -m src "$f"
    echo ""
done

echo "=== DONE ==="