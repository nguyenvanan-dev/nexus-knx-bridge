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

if command -v python3 >/dev/null 2>&1 && ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
    echo "✗ [FAIL] Python >= 3.11 is required"
    ERRORS=$((ERRORS + 1))
fi

if command -v node >/dev/null 2>&1; then
    NODE_VERSION_OK=$(node -p 'const [a,b]=process.versions.node.split(".").map(Number); Number(a > 20 || (a === 20 && b >= 9))')
    if [ "$NODE_VERSION_OK" != "1" ]; then
        echo "✗ [FAIL] Node.js >= 20.9 is required"
        ERRORS=$((ERRORS + 1))
    fi
fi

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

if [ -f ".env" ]; then
    ENV_PERM=$(stat -c "%a" .env 2>/dev/null || stat -f "%Lp" .env 2>/dev/null || echo "unknown")
    if [ "$ENV_PERM" = "600" ]; then
        echo "✓ [OK] .env exists with secure permissions (0600)"
    else
        echo "✗ [FAIL] .env permissions are $ENV_PERM; expected 600"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "✗ [FAIL] .env missing"
    ERRORS=$((ERRORS + 1))
fi

check_service() {
    local service="$1"
    if systemctl --user is-active --quiet "$service" 2>/dev/null; then
        echo "✓ [OK] User service $service is ACTIVE"
    elif systemctl is-active --quiet "$service" 2>/dev/null; then
        echo "✓ [OK] System service $service is ACTIVE"
    else
        echo "✗ [FAIL] Service $service is not active"
        ERRORS=$((ERRORS + 1))
    fi
}

check_service knx-bridge.service
check_service knx-frontend.service

echo "--------------------------------------------------"
if [ "$ERRORS" -eq 0 ]; then
    echo "Result: Installation check PASSED"
else
    echo "Result: Found $ERRORS issues during check"
fi
echo "=================================================="
exit "$ERRORS"
