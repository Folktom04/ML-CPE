#!/usr/bin/env python3
"""Insert a link to lessons/LNN-*.md under each '## Level N' heading in the tier files."""
import glob, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lessons = {}
for p in glob.glob(os.path.join(ROOT, "lessons", "L[0-9][0-9]*.md")):
    m = re.match(r"L(\d+)-", os.path.basename(p))
    if m:
        lessons[int(m.group(1))] = "lessons/" + os.path.basename(p)

for tier in sorted(glob.glob(os.path.join(ROOT, "[01][0-9]-*.md"))):
    lines = open(tier, encoding="utf-8").read().split("\n")
    out, i, changed = [], 0, False
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = re.match(r"## Level (\d+) ", line)
        if m and int(m.group(1)) in lessons:
            n = int(m.group(1))
            # look ahead within this section for an existing link
            j = i + 1
            section = []
            while j < len(lines) and not lines[j].startswith("## "):
                section.append(lines[j]); j += 1
            if not any(f"lessons/L{n:02d}-" in s for s in section):
                out += ["", f"> 📖 **อ่านบทเรียนฉบับละเอียด:** [{lessons[n]}]({lessons[n]})"]
                changed = True
        i += 1
    if changed:
        open(tier, "w", encoding="utf-8").write("\n".join(out))
        print("updated", os.path.basename(tier))
