#!/bin/bash
# Grounding Module Cleanup Script
# Run from: ~/Desktop/odrl-z3-reasoner/

echo "=========================================="
echo "ODRL-SA Grounding Module Cleanup"
echo "=========================================="
echo ""

# Check we're in the right directory
if [ ! -d "src/grounding" ]; then
    echo "ERROR: Run this from the odrl-z3-reasoner root directory"
    exit 1
fi

echo "Step 1: Clean up file_format module"
echo "------------------------------------"

# Delete old hardcoded ontology builder
if [ -f "src/grounding/file_format/ontology_builder.py" ]; then
    echo "  Deleting: src/grounding/file_format/ontology_builder.py (old hardcoded version)"
    rm -f src/grounding/file_format/ontology_builder.py
    rm -f src/grounding/file_format/__pycache__/ontology_builder*.pyc 2>/dev/null
    echo "  ✓ Deleted"
else
    echo "  Already clean (ontology_builder.py not found)"
fi

echo ""
echo "Step 2: Rename files for consistency"
echo "------------------------------------"

# Rename sparql_tests.py to tests.py in language
if [ -f "src/grounding/language/sparql_tests.py" ]; then
    echo "  Renaming: language/sparql_tests.py → language/tests.py"
    mv src/grounding/language/sparql_tests.py src/grounding/language/tests.py
    echo "  ✓ Renamed"
fi

# Delete sparql_tests_v2.py if it exists (or merge manually first)
if [ -f "src/grounding/language/sparql_tests_v2.py" ]; then
    echo "  NOTE: language/sparql_tests_v2.py exists - review and delete manually if not needed"
fi

# Rename sparql_tests.py to tests.py in purpose
if [ -f "src/grounding/purpose/sparql_tests.py" ]; then
    echo "  Renaming: purpose/sparql_tests.py → purpose/tests.py"
    mv src/grounding/purpose/sparql_tests.py src/grounding/purpose/tests.py
    echo "  ✓ Renamed"
fi

echo ""
echo "Step 3: Show current structure"
echo "------------------------------------"
echo ""
tree src/grounding/ -I '__pycache__|*.pyc'

echo ""
echo "=========================================="
echo "Cleanup complete!"
echo ""
echo "Next steps (to be done with Claude):"
echo "  1. Create oracle.py for language module"
echo "  2. Create oracle.py for purpose module"
echo "  3. Create tests.py for file_format module"
echo "  4. Consolidate language module files"
echo "=========================================="
