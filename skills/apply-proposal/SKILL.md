---
name: apply-proposal
description: Apply an existing KNX device proposal only after the user has explicitly reviewed and approved that exact proposal.
---

# Apply Proposal

Use this skill only when a proposal already exists, has been reviewed, and the user explicitly authorizes applying it.

## Execution

Pass one JSON object through standard input:

```bash
printf '%s' '<JSON>' |
/home/an/knx-bridge/.venv/bin/python \
/home/an/knx-bridge/skills/apply-proposal/main.py
```

## Inputs

**Required:**

- `proposal_path`: absolute path to the exact proposal JSON file approved by the user

## Output

Returns the output produced by the current apply_device_proposal.py execution.

## Critical behavior

The current wrapper automatically invokes the underlying script with --confirm. It does not expose a safe dry-run mode through its current JSON contract.

## Safety
- Never invoke this skill without explicit user approval for the exact proposal.
- Do not use it for exploratory testing.
- Do not fabricate or substitute a proposal path.
- Reconfirm that the proposal path points to the reviewed file immediately before execution.
- Report validation errors instead of silently repairing the proposal.
- Do not claim this skill supports dry-run unless the implementation is changed and retested.
