# UV Guard

This folder (`ML-CPE/Final-Project/`, inside the course git repo) is shared by two agents: Claude Code and Google Antigravity. The rules live once in `.agents/rules/` and are imported here, so edit them there, not in this file.

@.agents/rules/00-project-context.md
@.agents/rules/10-python-ml.md
@.agents/rules/20-api-and-app.md

## Claude Code specifics
- Slash commands: `/day N`, `/status`, `/checkpoint` (in `.claude/commands/`). They mirror the Antigravity workflows in `.agents/workflows/`.
- A PostToolUse hook runs `pytest` after every edit to `source_code/src/` or `source_code/tests/`. If it reports failures, fix them before moving on.
- Use the project virtualenv: `.venv/bin/python` (macOS/Linux) or `.venv\Scripts\python.exe` (Windows).
- Division of labour: Claude Code does data, ML, backend and tests. UI checks of the Expo web build are usually done with Antigravity's browser agent; if the user asks you to do them, use `npx expo start --web` and describe what to verify.
- Both agents tick the same `ROADMAP.md`. Before starting, run `git status` and `git log -5 --oneline` to see what the other agent already did.
