# Known Issues and Operational Limits

## Release Candidate Limits

- Real KNX actuation is not executed by CI and must be accepted by the owner.
- Telegram/Zalo delivery tests require production accounts and explicit owner
  confirmation.
- Zalo Personal uses an unofficial login mechanism. Use a secondary account,
  restrict allowed groups and understand the account restriction risk.
- OpenClaw and 9router are external runtimes; the installer validates and
  configures integration but does not silently install or restart them.

## Technical Debt

- FastAPI startup/shutdown decorators currently emit deprecation warnings and
  should eventually migrate to lifespan handlers.
- Some repository code still uses naive UTC timestamps and emits Python
  deprecation warnings.
- Next.js reports that the `middleware` convention will move to `proxy` in a
  future release.

## Operational Rules

- Runtime databases, `.env`, `config.json` and OpenClaw credentials are ignored
  intentionally and must be backed up outside Git.
- A dirty runtime directory is not necessarily broken, but tracked source
  changes must be reviewed before release.
- Never identify an authorized user by a display name; use immutable IDs and
  gateway allow-lists.
