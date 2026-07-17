---
name: agent-memory
description: Search or store durable project information in local bot memory when previously stored context is needed or the user explicitly requests that information be remembered.
---

# Agent Memory

Use this skill to search existing local memory or store durable information appropriate for future reuse.

## Execution

Pass one JSON object through standard input:

```bash
printf '%s' '<JSON>' |
/home/an/knx-bridge/.venv/bin/python \
/home/an/knx-bridge/skills/agent-memory/main.py
```

## Inputs

**Required:**

- `action`: search or remember

For search:
- `query`: search text

For remember:
- `content`: information to store

**Optional fields supported by the schema:**
- `topic`
- `wing`
- `hall`
- `room`
- `tags`
- `importance`

## Output

Returns memory search results or the insertion result produced by the current executable.

## Safety
- Do not store passwords, tokens, credentials, private keys or other secrets.
- Use remember only when the user explicitly requests storage or the applicable memory policy permits it.
- Prefer search before assuming stored project details.
- Do not modify KNX devices, ETS configuration or unrelated production data.
