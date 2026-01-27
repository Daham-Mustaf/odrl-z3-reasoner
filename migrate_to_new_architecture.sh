#!/bin/bash
# migrate_to_new_architecture.sh

echo "=== ODRL-SA Migration Script ==="

# 1. Backup old code
echo "1. Creating backup..."
mkdir -p backup_old
cp -r src/semantics backup_old/ 2>/dev/null
cp -r src/parser backup_old/ 2>/dev/null
cp -r src/normalizer backup_old/ 2>/dev/null
cp -r src/encoder backup_old/ 2>/dev/null

# 2. Delete old modules
echo "2. Removing old modules..."
rm -rf src/semantics/
rm -rf src/parser/
rm -rf src/normalizer/
rm -f src/encoder/variable_manager.py
rm -f src/grounding/classifier.py

# 3. Copy new modules
echo "3. Installing new modules..."
cp -r outputs/config/ src/config/
cp -r outputs/registry/ src/registry/
cp -r outputs/core/ src/core/
cp -r outputs/normalizer/ src/normalizer/
cp -r outputs/encoder/ src/encoder/
cp -r outputs/parser/ src/parser/

# 4. Keep grounding oracles (don't delete)
echo "4. Keeping grounding oracles..."
# src/grounding/language/, purpose/, file_format/ are kept

echo "=== Migration Complete ==="
echo ""
echo "New structure:"
echo "  src/config/        - Configuration (YAML)"
echo "  src/registry/      - OperandRegistry"
echo "  src/core/          - Core types"
echo "  src/normalizer/    - Value normalization"
echo "  src/encoder/       - Z3 encoding"
echo "  src/parser/        - ODRL parsing"
echo "  src/grounding/     - Oracles (kept)"