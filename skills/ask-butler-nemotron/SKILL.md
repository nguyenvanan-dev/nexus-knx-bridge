---
name: ask-butler-nemotron
description: Send a suitable user question to the configured Butler Nemotron assistant when specialized butler-oriented analysis is needed.
---

# Ask Butler Nemotron

Use this skill only for requests matching the Butler Nemotron role configured by the project.

## Execution

Pass one JSON object through standard input:

```bash
printf '%s' '<JSON>' |
/home/an/knx-bridge/.venv/bin/python \
/home/an/knx-bridge/skills/ask-butler-nemotron/main.py
```

## Inputs

**Required:**

- `question`: question sent to the configured assistant

## Output

Returns the configured provider response or its error result.

## Safety
- Do not include passwords, tokens or credentials.
- Do not claim the model is available until the request succeeds.
- Do not use model output as permission to control KNX or write production data.
- Return timeout, authentication and provider errors without inventing an answer.
