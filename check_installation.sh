#!/usr/bin/env bash
set -euo pipefail

echo "=================================================="
echo "       KNX Bridge Installation Checker            "
echo "=================================================="

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

ERRORS=0

check_cmd() {
    if command -v "$1" >/dev/null 2>&1; then
        echo "✓ [OK] Command '$1' installed: $($1 --version 2>&1 | head -n 1)"
    else
        echo "✗ [FAIL] Command '$1' is missing"
        ERRORS=$((ERRORS + 1))
    fi
}

check_cmd python3
check_cmd node
check_cmd npm

if [ -d ".venv" ]; then
    echo "✓ [OK] Python virtual environment (.venv) present"
else
    echo "✗ [FAIL] Python virtual environment (.venv) missing"
    ERRORS=$((ERRORS + 1))
fi

if [ -f "config.json" ]; then
    PERM=$(stat -c "%a" config.json 2>/dev/null || stat -f "%Lp" config.json 2>/dev/null || echo "unknown")
    echo "✓ [OK] config.json exists (Permissions: $PERM)"
else
    echo "✗ [FAIL] config.json missing"
    ERRORS=$((ERRORS + 1))
fi

if systemctl --user is-active --quiet knx-bridge.service 2>/dev/null; then
    echo "✓ [OK] Service knx-bridge is ACTIVE"
else
    echo "⚠ [WARN] Service knx-bridge is not active"
fi

if systemctl --user is-active --quiet knx-frontend.service 2>/dev/null; then
    echo "✓ [OK] Service knx-frontend is ACTIVE"
else
    echo "⚠ [WARN] Service knx-frontend is not active"
fi

echo "--------------------------------------------------"
if [ "$ERRORS" -eq 0 ]; then
    echo "Result: Installation check PASSED"
else
    echo "Result: Found $ERRORS issues during check"
fi
echo "=================================================="
