# OpenClaw Skill Allowlist Configuration

- Canonical skill path: `/home/an/knx-bridge/skills`
- Runtime symlink: `/home/an/.openclaw/workspace/skills`

## Agent production allowlist

The `main` agent is explicitly configured to allow the following skills:
- goplaces
- ask-engineer-deepseek
- ask-butler-nemotron
- zalo-history
- knx-bridge
- agent-memory
- document-reader
- weather-checker

## Important Policy Updates

- **AGENTS.md Configuration**: The agent system prompt in `AGENTS.md` is strictly updated to enforce usage of the canonical `document-reader` skill for parsing documents.
- **Legacy Path Prohibition**: The agent is explicitly prohibited from calling legacy paths (e.g. `skills/official/document_to_knx_skill.py` or `skills/official/apply_device_proposal.py`) or executing python scripts manually via the terminal.
- **apply-proposal Exclusion**: The `apply-proposal` skill is intentionally excluded from the default `main` agent allowlist to prevent unauthorized execution of device modifications without a secure validation and user confirmation mechanism.
