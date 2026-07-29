# Contributing

Thank you for helping improve NEXUS KNX Bridge.

## Before Opening a Change

- Do not include `.env`, databases, API keys, bot tokens, pairing files,
  OpenClaw credentials, private vaults or real KNX project data.
- Open an issue before a large architectural change.
- Keep hardware writes disabled in automated tests.
- Never apply a real ETS proposal as part of a test.

## Development Checks

```bash
./install.sh --check-only
PYTHONPATH=. .venv/bin/python -m pytest tests/ -q
cd frontend
npm ci
npm audit --audit-level=high
npm run lint
npm run build
```

## Pull Requests

- Explain the user-visible behavior and safety impact.
- Add focused tests for fixes and new behavior.
- Keep runtime configuration outside Git.
- State clearly whether physical KNX, Telegram or Zalo tests were performed.

Security vulnerabilities must be reported privately as described in
`docs/SECURITY.md`, not in a public issue.
