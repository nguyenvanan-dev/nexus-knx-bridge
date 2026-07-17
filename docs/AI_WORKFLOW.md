# AI Workflow

To maintain a consistent, secure, and productive environment, all AI agents (Antigravity, Claude, ChatGPT, etc.) must follow this workflow strictly.

## 1. Startup Routine
Whenever starting a new session or continuing a task:
1. **Read `PROJECT_STATE.md`**: Understand the current objective and milestone.
2. **Consult Project Brain**: Review `ARCHITECTURE.md`, `DECISIONS.md`, and `KNOWN_ISSUES.md` if the task involves those domains.
3. **Check State**: Run `git status` and `git log -n 5` to confirm the local environment matches the documentation.
4. **DO NOT REDISCOVER**: Check section 6 of `PROJECT_STATE.md` to avoid wasting tokens investigating verified components.

## 2. Coding Guidelines
- **Verify Before Modifying**: Do not blind-write code. Use `grep`, `cat`, or read tools to understand the surrounding context first.
- **No Prompt Authorization**: NEVER write code or configuration that grants user permissions based on `display_name`, `username`, or chat context. Rely on OpenClaw's Gateway RBAC (`ownerAllowFrom`).
- **Restart Services**: If modifying backend code, always restart the service: `sudo systemctl restart knx-bridge` and verify with `systemctl status knx-bridge`.

## 3. Wrap-up Routine
Before ending a turn or session:
1. **Verify**: Ensure the code runs (e.g., `curl localhost:5055/health`).
2. **Update Documentation**: If your changes altered architecture, deployment, or task status, update the relevant `docs/` files (e.g., `PROJECT_STATE.md`, `CHANGELOG.md`).
3. **Commit**: Only commit if the user explicitly authorizes it, or if it's the natural conclusion of a planned task. Ensure commit messages follow conventional commits (e.g., `feat:`, `fix:`, `docs:`).

## 4. Anti-Hallucination & Environment Context
**CRITICAL CONTEXT**: You (the AI) are operating directly via SSH on a **Raspberry Pi 4 (Ubuntu)**.
- **Topology**: This Pi is the central server (`knx-bridge`). All backend (`uvicorn` on `5055`) and frontend (`Next.js` on `3000`) code runs HERE on this Pi. 
- **Network**: The Pi is accessed by the User over the LAN via its IP (e.g., `10.1.10.x`). Do NOT assume the web server is running on the User's local laptop. 
- **Rule**: Never make up excuses about "local vs remote" execution. Verify facts via system commands (`hostname -I`, `ss -tlnp`) before claiming an error is due to the execution environment.
