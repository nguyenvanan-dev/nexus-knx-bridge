# Project Architecture

## 1. High-Level Overview
- **Project Name:** NEXUS KNX Bridge
- **Primary Product:** OpenClaw KNX AI Agent accessed through Zalo and Telegram.
- **Purpose:** Control, monitor and operate physical KNX infrastructure through
  natural-language conversations.
- **Administration Layer:** Next.js web UI for setup, ETS import, device
  registry, diagnostics and system administration.
- **Core Components:** OpenClaw, KNX tools/skills, FastAPI, `xknx`, SQLite and
  Next.js.

```text
Zalo Bot -------\
                 -> OpenClaw KNX AI Agent -> Tools/Skills -> FastAPI -> KNX/IP
Telegram Bot ---/                 |
                                  -> Memory and approved proposals

Web Admin -------------------------------------> FastAPI / SQLite
AI provider -> OpenClaw
AI providers -> optional 9router -> OpenClaw
```

## 2. Component Architecture
- **FastAPI:** Core REST API bridging commands to the KNX bus (`127.0.0.1:5055`).
- **KNX Tunnel:** Connection to the gateway configured at runtime via `xknx`.
- **OpenClaw Runtime:** KNX AI Agent orchestrator for conversations, memory,
  tools and skills.
- **Messaging Channels:** Telegram and Zalo are conversational interfaces to the
  same KNX AI Agent, not notification-only adapters.
- **9router:** Optional OpenAI-compatible provider router for quota-aware
  fallback. It is not the agent runtime.
- **Next.js:** Administration UI added after the agent to simplify setup and
  operation.
- **Background Workers:**
  - `background_queue.py`
  - `notification_engine.py`
  - `trigger_manager.py`

## 3. Database Architecture
The runtime intentionally uses two SQLite databases with separate ownership:

- **`smarthome.db`** is the canonical KNX, device, scene, automation and web
  administration database. It uses WAL mode.
- **`data/chat_history.db`** stores Zalo/group conversation history used by the
  chat-history and summarization flow. It is not the canonical device registry.

Key `smarthome.db` tables:
- `devices`: KNX mapping, Group Addresses, and roles.
- `users`: Local users.
- `device_history`: Time-series device state changes.
- `automation_rules_v2`: Complex logic triggers and actions.
- `floor_plans` & `floor_plan_devices`: UI mapping.
- `ai_conversations` & `ai_memories`: Agent-facing conversation context and
  structured memory.
- `scenes` & `scene_actions`.

## 4. Identity & Authorization Architecture
**STRICT RULE:** Authorization happens BEFORE AI execution.
- **RBAC Policy:** Handled purely by OpenClaw configuration (`~/.openclaw/openclaw.json`).
- **`ownerAllowFrom`:** Contains administrator-configured Telegram and Zalo user IDs.
- **Gateway Evaluation:** Gateway checks sender ID against `ownerAllowFrom` and assigns `role: owner` or `guest`.
- **AI Context Enforcement:** AI relies on the `role` metadata provided by the Gateway. The AI is **NOT** the authorization authority.

## 5. File Configuration
- **`~/.openclaw/openclaw.json`:** OpenClaw routing, tokens, models, RBAC (`ownerAllowFrom`).
- **`knx-bridge/.env`:** Backend tokens (`KNX_API_TOKEN`) and secrets.
- **`smarthome.db`:** Canonical device, Group Address, scene, and runtime configuration storage.
- **`data/chat_history.db`:** Zalo/group message history for summarization and
  retrieval.
