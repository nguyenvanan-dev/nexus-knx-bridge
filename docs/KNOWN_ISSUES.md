# Known Issues & False Assumptions

## 1. Known False Assumptions (Corrected)
**Do NOT make these assumptions in future development:**

- ❌ **Assumption:** Authorization can be verified by asking the AI if the user is "Hai Lúa" or "Boss An".
  - **Truth:** Display names are easily spoofed. Authorization MUST use immutable IDs (`ownerAllowFrom`) checked at the Gateway level, NOT in AI Prompts.
- ❌ **Assumption:** A dirty repository means a broken build.
  - **Truth:** In this repository, `smarthome.db` is runtime data and `__pycache__` is generated. These will always make the tree appear dirty if not ignored properly.
- ❌ **Assumption:** `cat` inside a bash script is an acceptable way to write files.
  - **Truth:** Always prioritize AI agent specific tools (`write_to_file`) over bash scripting for file creation to avoid escaping nightmares.

## 2. Known Issues (Bugs & Technical Debt)
- **Technical Debt:** OpenClaw is currently running as a standalone background process (`openclaw`) rather than a monitored `systemd` service. This will cause failures if the Raspberry Pi reboots.
- **Technical Debt:** Zalo and Telegram IDs are hardcoded in `~/.openclaw/openclaw.json`. Ideally, these should be template-injected from a `.env` file to prevent accidental commits of sensitive user IDs, but OpenClaw does not currently natively parse `.env` files for its JSON config.
- **Code Review:** `tests/performance/stress_test.py` contains uncommitted changes (97 additions, 31 deletions) that need review.
