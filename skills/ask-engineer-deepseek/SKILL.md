---
name: ask-engineer-deepseek
description: Send a technical question to the configured Engineer DeepSeek assistant when specialist engineering analysis is required.
---

# Ask Engineer DeepSeek

Use this skill for engineering questions matching the role configured by the project.

## Execution

Pass one JSON object through standard input:

```bash
printf '%s' '<JSON>' |
/home/an/knx-bridge/.venv/bin/python \
/home/an/knx-bridge/skills/ask-engineer-deepseek/main.py
```

## Inputs

**Required:**

- `question`: technical question sent to the configured assistant

## Output

Returns the configured provider response or its error result.

## Safety
- Do not include secrets or credentials.
- Do not treat model output as an approved ETS or KNX change.
- Do not automatically execute recommendations returned by the model.
- Return timeout, authentication and provider errors clearly.
