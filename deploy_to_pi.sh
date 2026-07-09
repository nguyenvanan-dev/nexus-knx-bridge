#!/bin/bash
PI_USER="${PI_USER:-an}"
PI_HOST="${PI_HOST:-pi4-ubuntu.local}"
DEST_DIR="/home/$PI_USER/knx-bridge"

echo "Syncing code to Raspberry Pi ($PI_USER@$PI_HOST)..."
rsync -avz --exclude '.git' --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' ./ "$PI_USER@$PI_HOST:$DEST_DIR"

echo "Installing pytest on Pi if missing..."
ssh "$PI_USER@$PI_HOST" "cd $DEST_DIR && source .venv/bin/activate && pip install pytest pytest-asyncio"

echo "Running Phase 10.5A Automated Tests on Pi..."
ssh "$PI_USER@$PI_HOST" "cd $DEST_DIR && source .venv/bin/activate && PYTHONPATH=. python3 -m pytest -v tests/unit/ tests/integration/test_context_builder.py tests/unit/builders/test_suggestion_builder.py tests/unit/builders/test_predictive_automation.py tests/unit/builders/test_intent_extractor.py tests/unit/builders/test_thread_builder.py tests/unit/builders/test_user_memory_builder.py"

echo "Running Phase 10.5B Benchmarks on Pi..."
ssh "$PI_USER@$PI_HOST" "cd $DEST_DIR && source .venv/bin/activate && PYTHONPATH=. python3 tests/performance/benchmark_suite.py"

echo "Done."
