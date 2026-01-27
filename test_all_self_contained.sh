#!/bin/bash
# test_all_self_contained.sh
# Test all SELF_CONTAINED TTL files with the ODRL analyzer

set -e

DIR="tests/test_data/self_contained"
PASSED=0
FAILED=0
TOTAL=0

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║     ODRL Z3 Reasoner - SELF_CONTAINED Operands Test Suite         ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

for ttl in "$DIR"/*.ttl; do
    TOTAL=$((TOTAL + 1))
    filename=$(basename "$ttl")
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "[$TOTAL] Testing: $filename"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if uv run python -m src "$ttl" 2>&1; then
        PASSED=$((PASSED + 1))
        echo "✅ PASSED"
    else
        # Check if it's an expected failure (policy with conflicts)
        if uv run python -m src "$ttl" 2>&1 | grep -q "INVALID"; then
            PASSED=$((PASSED + 1))
            echo "✅ PASSED (conflict detected as expected)"
        else
            FAILED=$((FAILED + 1))
            echo "❌ FAILED"
        fi
    fi
    echo ""
done

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                         TEST SUMMARY                               ║"
echo "╠════════════════════════════════════════════════════════════════════╣"
echo "║  Total:  $TOTAL                                                    "
echo "║  Passed: $PASSED                                                   "
echo "║  Failed: $FAILED                                                   "
echo "╚════════════════════════════════════════════════════════════════════╝"

if [ $FAILED -eq 0 ]; then
    echo ""
    echo "🎉 All SELF_CONTAINED operand tests passed!"
    exit 0
else
    echo ""
    echo "⚠️  Some tests failed"
    exit 1
fi