---
description: ทำงานตาม ROADMAP ของวันที่ระบุ เช่น /day 3
argument-hint: <เลขวัน 1-30>
---

Work on day $ARGUMENTS of the UV Guard roadmap.

1. Read `ROADMAP.md` and find the section "วัน $ARGUMENTS". If no number was given, pick the first day that still has unticked `[ ]` items.
2. Run `git status` and `git log -5 --oneline`, and look at what earlier days already produced, so the new work builds on it instead of duplicating it.
3. Write an implementation plan in Thai: files to create/change, packages to install, how the result will be tested. Stop and wait for my approval.
4. Implement that day's tasks only. Do not start the next day's tasks.
5. Run `pytest -q` (and any script or notebook produced today). Fix failures before continuing.
6. Tick finished items in `ROADMAP.md` with `[x]`. For anything unfinished leave `[ ]` and add a note under it starting with `> ค้าง:`.
7. Commit with a message like `day $ARGUMENTS: <short summary>` in English.
8. Finish with a summary in Thai: what was built, test results, output files, and anything I must do by hand.
