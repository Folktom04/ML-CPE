---
description: ทำงานตาม ROADMAP ของวันที่ระบุ เช่น /day 3
---

1. Read `ROADMAP.md` and find the section for the day number the user gave (e.g. "วัน 3"). If no number was given, pick the first day that still has unticked `[ ]` items.
2. Read the rules in `.agents/rules/` and look at what already exists in the repo from earlier days, so the new work builds on it instead of duplicating it.
3. Write an implementation plan in Thai: files to create/change, libraries to install, how the result will be tested. Stop and wait for the user to approve.
4. Implement the tasks for that day only. Do not start the next day's tasks.
5. Run `pytest -q` (and the notebook or script produced today, if any). Fix failures before continuing.
6. Tick the finished items in `ROADMAP.md` with `[x]`. If an item could not be finished, leave it `[ ]` and add a short note under it starting with `> ค้าง:`.
7. Stage and commit with a message like `day 3: clear-sky UVI module` (English).
8. Finish with a walkthrough in Thai: what was built, test results, output files, and anything the user must do by hand (buy hardware, test on phone, etc.).
