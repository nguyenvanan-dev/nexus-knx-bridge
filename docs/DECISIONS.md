# Engineering Decisions Log

This document tracks significant architectural and engineering decisions to prevent future AI agents from reverting or misunderstanding core designs.

## Decision 1: Shift Authorization out of AI Prompts
- **Context:** Previously, the bot used display names ("Hai Lúa", "Boss An") and `IDENTITY.md` prompts to determine user privileges.
- **Decision:** Remove all prompt-based authorization. Implement Application-Layer RBAC using immutable platform IDs.
- **Why:** Display names are mutable. AI hallucinations and prompt injections compromise security.
- **Implementation:** `ownerAllowFrom` in `~/.openclaw/openclaw.json` maps Telegram ID `1504699142` and Zalo ID `a883cba5f1ed18b341fc` to `role: owner`.
- **Status:** Implemented and Verified.

## Decision 2: Unify Databases
- **Context:** The system had fragmented databases (`chat_history.db`, `knx.db`).
- **Decision:** Consolidate into a single `smarthome.db`.
- **Why:** Reduces connection overhead, simplifies backups, allows cross-table foreign key constraints (e.g., AI memories referencing devices).
- **Status:** Implemented and Verified.

## Decision 3: Enable SQLite WAL Mode
- **Context:** Database locking issues during concurrent reads/writes from background workers and FastAPI.
- **Decision:** Enable Write-Ahead Logging (`journal_mode=wal`) and connection pooling.
- **Why:** Greatly improves concurrency for read-heavy automation engines.
- **Status:** Implemented and Verified.

## Decision 4: EventBus and Background Batching
- **Context:** Writing every KNX event synchronously blocked the main asyncio event loop.
- **Decision:** Implement `EventBus` and `background_queue.py` to batch inserts.
- **Why:** Prevents I/O blocking during high KNX bus traffic.
- **Status:** Implemented and Verified.
