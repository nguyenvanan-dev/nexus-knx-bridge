# Project Architecture

## 1. High-Level Overview
- **Project Name:** KNX Smart Home Platform (`knx-bridge`)
- **Purpose:** Connect physical KNX infrastructure to an LLM-driven AI Assistant (via OpenClaw).
- **Core Components:** FastAPI, `xknx`, SQLite, OpenClaw AI Gateway.

## 2. Component Architecture
- **FastAPI:** Core REST API bridging commands to the KNX bus (`127.0.0.1:5055`).
- **KNX Tunnel:** Connection to IP `10.1.10.137:3671` via `xknx`.
- **OpenClaw Gateway:** AI orchestrator processing natural language and translating to API calls.
- **Messaging Adapters:** Telegram (native to OpenClaw) and Zalo (webhook).
- **Background Workers:**
  - `background_queue.py`
  - `notification_engine.py`
  - `trigger_manager.py`

## 3. Database Architecture
**Unified `smarthome.db` (SQLite with WAL mode).**
Key Tables:
- `devices`: KNX mapping, Group Addresses, and roles.
- `users`: Local users.
- `device_history`: Time-series device state changes.
- `automation_rules_v2`: Complex logic triggers and actions.
- `floor_plans` & `floor_plan_devices`: UI mapping.
- `ai_conversations` & `ai_memories`: Unified from legacy `chat_history.db`.
- `scenes` & `scene_actions`.

## 4. Identity & Authorization Architecture
**STRICT RULE:** Authorization happens BEFORE AI execution.
- **RBAC Policy:** Handled purely by OpenClaw configuration (`~/.openclaw/openclaw.json`).
- **`ownerAllowFrom`:** Contains immutable IDs (Telegram: `1504699142`, Zalo: `a883cba5f1ed18b341fc`).
- **Gateway Evaluation:** Gateway checks sender ID against `ownerAllowFrom` and assigns `role: owner` or `guest`.
- **AI Context Enforcement:** AI relies on the `role` metadata provided by the Gateway. The AI is **NOT** the authorization authority.

## 5. File Configuration
- **`~/.openclaw/openclaw.json`:** OpenClaw routing, tokens, models, RBAC (`ownerAllowFrom`).
- **`knx-bridge/.env`:** Backend tokens (`KNX_API_TOKEN`) and secrets.
- **`devices.json`:** Group Address to component mappings.
