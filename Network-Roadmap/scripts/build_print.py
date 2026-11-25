#!/usr/bin/env python3
"""Build a print-ready A4 PDF from the detailed lessons (lessons/LNN-*.md).

    python3 scripts/build_print.py --from 1 --to 6
    python3 scripts/build_print.py --from 7 --to 10 --out print/Lessons-L07-L10.pdf

- Each lesson starts on a new page; a cover, a table of contents with page numbers
  and page numbers in the footer are added.
- Quiz answers (<details> blocks) are moved to an answer key at the end of the book,
  so the quiz can be done on paper without seeing the answers.
- Navigation lines/links that make no sense on paper are removed.
- Layout never cuts a code/diagram box, note box, table, list item or heading across
  pages (headings stay with the content after them); after building, the PDF itself is
  checked and any split is reported.

Requires: Python packages 'markdown', 'pypdf', 'beautifulsoup4' (and optionally 'pdfplumber'
for the split check), Node.js with Playwright (Chromium), and Thai fonts (e.g. Noto Sans Thai).
"""
from __future__ import annotations

import argparse
import glob
import html
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
LESSONS = ROOT / "lessons"

THAI_MONTHS = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม",
               "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]

DETAILS_RE = re.compile(r"<details>\s*<summary>.*?</summary>(.*?)</details>", re.S)
LINK_RE = re.compile(r"\[([^\]]+)\]\((?!https?://)[^)]*\)")

CSS = """
@page { size: A4; margin: 16mm 15mm 18mm 15mm; }
:root { --ink: #111; --muted: #555; --line: #bbb; --soft: #f2f2f2; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: "Noto Sans Thai", "Noto Sans", "Loma", sans-serif, "Noto Color Emoji";
       font-size: 10.5pt; line-height: 1.62; color: var(--ink); margin: 0; }
h1 { font-size: 19pt; line-height: 1.3; margin: 0 0 6pt; padding-bottom: 6pt; border-bottom: 2.5pt solid #222; }
h2 { font-size: 14pt; margin: 16pt 0 6pt; padding: 3pt 0 3pt 8pt; border-left: 4pt solid #222;
     break-after: avoid; }
h3 { font-size: 12pt; margin: 12pt 0 4pt; break-after: avoid; }
h4 { font-size: 11pt; margin: 10pt 0 4pt; break-after: avoid; }
p { margin: 4pt 0 6pt; orphans: 3; widows: 3; }
ul, ol { margin: 4pt 0 6pt; padding-left: 18pt; }
li { margin: 1.5pt 0; }
hr { border: 0; border-top: 0.6pt solid var(--line); margin: 10pt 0; }
blockquote { margin: 8pt 0; padding: 6pt 10pt; background: var(--soft); border-left: 3pt solid #666;
             border-radius: 2pt; break-inside: avoid; }
blockquote p { margin: 2pt 0; }
code { font-family: "DejaVu Sans Mono", "Noto Sans Thai", monospace; font-size: 9pt;
       background: var(--soft); padding: 0.5pt 3pt; border-radius: 2pt; }
pre { font-family: "DejaVu Sans Mono", "Noto Sans Thai", monospace; font-size: 8.3pt;
      line-height: 1.38; background: #f6f6f6; border: 0.6pt solid #ccc; border-radius: 3pt;
      padding: 6pt 8pt; margin: 6pt 0 8pt; white-space: pre-wrap; word-break: break-word; }
pre code { background: none; padding: 0; font-size: inherit; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 10pt; font-size: 9.4pt; line-height: 1.45; }
th, td { border: 0.6pt solid #999; padding: 3pt 5pt; vertical-align: top; text-align: left; }
th { background: #e4e4e4; font-weight: 700; }
tr { break-inside: avoid; }
thead { display: table-header-group; }
a { color: inherit; text-decoration: none; }

.cover { height: 255mm; display: flex; flex-direction: column; justify-content: center; text-align: center;
         break-after: page; }
.cover .kicker { font-size: 12pt; letter-spacing: 1pt; color: var(--muted); }
.cover h1 { font-size: 30pt; border: 0; margin: 10pt 0 6pt; }
.cover .range { font-size: 18pt; margin: 4pt 0 6pt; }
.cover .tier { font-size: 13pt; color: var(--muted); margin: 0 0 22pt; }
.cover .box { margin: 0 auto; text-align: left; border: 1pt solid #333; padding: 10pt 16pt; width: 135mm;
              font-size: 10.5pt; }
.cover .meta { margin-top: 26pt; color: var(--muted); font-size: 10pt; }
.cover .name { margin-top: 30pt; font-size: 11pt; }

.toc { }
.toc h1 { margin-bottom: 14pt; }
.toc .row { display: flex; align-items: baseline; font-size: 11.5pt; margin: 7pt 0; }
.toc .row .t { flex: 0 1 auto; }
.toc .row .dots { flex: 1; border-bottom: 1pt dotted #777; margin: 0 6pt; transform: translateY(-3pt); }
.toc .row .p { flex: 0 0 auto; min-width: 16pt; text-align: right; font-weight: 700; }
.toc .tips { margin-top: 22pt; font-size: 10pt; }

.lesson { break-before: page; padding-top: 8pt; }
.answers, .lesson h1:first-child { padding-top: 2pt; }
.answer-note { border: 1pt dashed #666; padding: 5pt 9pt; margin: 8pt 0; font-size: 9.8pt; }
.answer-lines { margin: 6pt 0 0; }
.answers { break-before: page; padding-top: 8pt; }
.answers h1 { margin-bottom: 8pt; }
.answers section { break-inside: avoid-page; margin-bottom: 10pt; }
.answers h2 { font-size: 12.5pt; margin-top: 10pt; }
/* ---- pagination: never cut boxes, keep headings with their content ---- */
pre, blockquote, .tablewrap, .answer-note, .keep, li, tr, img, figure { break-inside: avoid; }
h1, h2, h3, h4 { break-after: avoid; break-inside: avoid; }
.tablewrap { margin: 6pt 0 10pt; }
.tablewrap table { margin: 0; }
.keep > :last-child { margin-bottom: 6pt; }
.marker { font-size: 6pt; color: #fff; font-weight: 400; margin-left: 4pt; font-family: "DejaVu Sans Mono", monospace; }
"""


def lesson_files(first: int, last: int) -> list[tuple[int, Path]]:
    files = []
    for p in glob.glob(str(LESSONS / "L[0-9][0-9]*.md")):
        m = re.match(r"L(\d+)-", Path(p).name)
        if m and first <= int(m.group(1)) <= last:
            files.append((int(m.group(1)), Path(p)))
    if not files:
        sys.exit(f"no lessons found in range {first}-{last}")
    return sorted(files)


def prepare(text: str) -> tuple[str, str, list[str]]:
    """Return (title, body markdown without title, list of answer-key markdown blocks)."""
    lines = text.splitlines()
    title = lines[0].lstrip("# ").strip()
    body = "\n".join(lines[1:])
    answers = [m.group(1).strip() for m in DETAILS_RE.finditer(body)]
    body = DETAILS_RE.sub("@@ANSWER_NOTE@@", body)
    # drop "next lesson" navigation at the end (paper has no links)
    cut = re.search(r"\n(?:---\s*\n+)?(?:##\s*)?(?:➡️|⬅️|🎉)[^\n]*(?:\n.*)*\Z", body)
    if cut:
        body = body[:cut.start()]
    body = body.rstrip().rstrip("-").rstrip()
    body = LINK_RE.sub(r"\1", body)          # keep link text, remove relative targets
    return title, body, answers


def md_to_html(text: str) -> str:
    raw = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"], output_format="html5")
    return keep_together(raw)


BLOCKS = {"p", "pre", "table", "ul", "ol", "blockquote", "div", "hr"}


def keep_together(fragment: str) -> str:
    """Group elements so the browser never splits them across pages.

    - every table gets a wrapper that must stay on one page;
    - a heading stays on the same page as the content that follows it;
    - a short lead-in paragraph ("ตัวอย่าง:", "วิธีแก้:") stays with the box/list after it.
    Elements taller than a page still have to split; the build reports them.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(fragment, "html.parser")
    for hr in soup.find_all("hr", recursive=False):     # section separators: headings already stand out,
        hr.decompose()                                  # and a lone rule at a page edge looks like a defect
    for table in soup.find_all("table"):
        table.wrap(soup.new_tag("div", attrs={"class": "tablewrap"}))

    def next_block(el):
        sib = el.next_sibling
        while sib is not None and getattr(sib, "name", None) is None:
            if str(sib).strip():
                return None
            sib = sib.next_sibling
        return sib

    def is_lead_in(el) -> bool:
        return el.name == "p" and len(el.get_text(strip=True)) <= 180

    def is_heading(el) -> bool:
        return el is not None and el.name in ("h2", "h3", "h4")

    for el in list(soup.find_all(["h2", "h3", "h4", "p"], recursive=False)):
        if el.parent is None or el.parent.name == "div" and "keep" in (el.parent.get("class") or []):
            continue
        if not (is_heading(el) or is_lead_in(el)):
            continue
        group = [el]
        nxt = next_block(el)
        # heading -> (optional short lead-in paragraph) -> first block
        while nxt is not None and nxt.name in BLOCKS | {"h3", "h4"} and len(group) < 4:
            group.append(nxt)
            if nxt.name == "p" and is_lead_in(nxt) or is_heading(nxt):
                nxt = next_block(nxt)
                continue
            break
        if len(group) == 1 or (not is_heading(el) and group[-1].name in ("p", "hr")):
            continue
        wrapper = soup.new_tag("div", attrs={"class": "keep"})
        el.insert_before(wrapper)
        for g in group:
            wrapper.append(g.extract())
    return str(soup)


def tier_title(first: int, last: int) -> str:
    """'Tier 2 — Protocol หลัก' when the range lies inside one tier, else ''."""
    for f in sorted(ROOT.glob("[01][0-9]-*.md")):
        head = f.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
        m = re.search(r"\(Level (\d+)[–-](\d+)\)", head)
        if m and int(m.group(1)) <= first and last <= int(m.group(2)):
            return re.sub(r"\s*\(Level .*?\)", "", head)
    return ""


def build_html(lessons: list[tuple[int, Path]], pages: dict[str, int] | None, first: int, last: int,
               learner_name: bool) -> str:
    today = date.today()
    today_th = f"{today.day} {THAI_MONTHS[today.month - 1]} {today.year + 543}"
    items = []
    short_titles = []
    toc_rows = []
    answer_sections = []
    for num, path in lessons:
        title, body, answers = prepare(path.read_text(encoding="utf-8"))
        key = f"L{num:02d}"
        short = re.sub(r"^บทเรียน\s*", "", title).replace(" (ฉบับละเอียด)", "")
        short_titles.append(short)
        ans_page = (pages or {}).get(f"A{num:02d}")
        note = ("<div class='answer-note'>✍️ ทำแบบทดสอบบนกระดาษก่อน แล้วตรวจคำตอบที่ <b>เฉลยท้ายเล่ม</b>"
                + (f" หน้า {ans_page}" if ans_page else "") + "</div>")
        body_html = md_to_html(body).replace("<p>@@ANSWER_NOTE@@</p>", note).replace("@@ANSWER_NOTE@@", note)
        items.append(f"<article class='lesson'><h1>{html.escape(title)}<span class='marker'>@@{key}@@</span></h1>"
                     f"{body_html}</article>")
        page = (pages or {}).get(key, "")
        toc_rows.append(f"<div class='row'><span class='t'>{html.escape(short)}</span>"
                        f"<span class='dots'></span><span class='p'>{page}</span></div>")
        for a in answers:
            answer_sections.append(f"<section><h2>{html.escape(short)}<span class='marker'>@@A{num:02d}@@</span>"
                                   f"</h2>{md_to_html(a)}</section>")
    answer_page = (pages or {}).get("ANS", "")
    toc_rows.append(f"<div class='row'><span class='t'>เฉลยแบบทดสอบทุกบท</span><span class='dots'></span>"
                    f"<span class='p'>{answer_page}</span></div>")

    tier = tier_title(first, last)
    contents = "<br>".join("• " + html.escape(t) for t in short_titles)
    name_line = ("<div class='name'>ชื่อ ______________________________ &nbsp; เริ่มเรียน ____/____/______</div>"
                 if learner_name else "")
    cover = f"""
<div class='cover'>
  <div class='kicker'>NETWORK ENGINEER ROADMAP · LEVEL 1–100</div>
  <h1>บทเรียนเครือข่ายคอมพิวเตอร์<br>ฉบับละเอียด</h1>
  <div class='range'>Level {first} – {last}</div>
  {f"<div class='tier'>{html.escape(tier)}</div>" if tier else ""}
  <div class='box'>
    <b>ในเล่มนี้</b><br>
    {contents}
  </div>
  {name_line}
  <div class='meta'>พิมพ์เมื่อ {today_th} · ทุกบทมีแบบทดสอบ 10 ข้อ (เฉลยอยู่ท้ายเล่ม)<br>
  ฉบับออนไลน์และโปรเจคประจำแต่ละ Level อยู่ในโฟลเดอร์ Network-Roadmap</div>
</div>"""
    toc = f"""
<div class='toc'>
  <h1>สารบัญ</h1>
  {''.join(toc_rows)}
  <div class='tips'>
    <b>วิธีใช้เล่มนี้</b>
    <ul>
      <li>อ่านทีละบท ขีดเส้นใต้/จดโน้ตข้างกระดาษได้เลย</li>
      <li>ทำ <b>แบบทดสอบ 10 ข้อ</b> ท้ายบทด้วยตัวเองก่อน แล้วค่อยเปิดดูเฉลยท้ายเล่ม</li>
      <li>หลังจบแต่ละบท ทำ <b>5 โปรเจค</b> ของ Level นั้นในไฟล์ Tier (เช่น 01-foundations.md)</li>
    </ul>
  </div>
</div>"""
    answers_html = (f"<div class='answers'><h1>เฉลยแบบทดสอบ<span class='marker'>@@ANS@@</span></h1>"
                    f"{''.join(answer_sections)}</div>")
    return (f"<!doctype html><html lang='th'><head><meta charset='utf-8'><title>บทเรียน Level {first}-{last}</title>"
            f"<style>{CSS}</style></head><body>{cover}{toc}{''.join(items)}{answers_html}</body></html>")


NODE_RENDER = r"""
const { chromium } = require('playwright');
(async () => {
  const [htmlPath, pdfPath, footerText] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + htmlPath, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({
    path: pdfPath, format: 'A4', printBackground: true, preferCSSPageSize: true,
    displayHeaderFooter: true, headerTemplate: '<div></div>',
    footerTemplate: `<div style="width:100%;font-size:9px;color:#666;padding:0 15mm;display:flex;justify-content:space-between;font-family:'Noto Sans Thai',sans-serif">
      <span>${footerText}</span><span>หน้า <span class="pageNumber"></span> / <span class="totalPages"></span></span></div>`,
  });
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
"""


def render(html_text: str, pdf: Path, footer: str, work: Path) -> None:
    html_path = work / "book.html"
    html_path.write_text(html_text, encoding="utf-8")
    js = work / "render.js"
    js.write_text(NODE_RENDER, encoding="utf-8")
    env = dict(os.environ)
    node_path = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    if node_path:
        env["NODE_PATH"] = node_path + os.pathsep + env.get("NODE_PATH", "")
    subprocess.run(["node", str(js), str(html_path), str(pdf), footer], check=True, env=env)


def audit_cuts(pdf: Path) -> list[tuple[int, str]]:
    """Find boxes (code, notes, tables) that were split across a page break.

    A split box is drawn down to the bottom edge of the printable area on one page
    AND continues from the top edge of the next page. A box that merely starts at
    the top of a page is fine. Needs 'pdfplumber' (optional).
    """
    try:
        import logging
        import pdfplumber
        logging.getLogger("pdfminer").setLevel(logging.ERROR)
    except ImportError:
        print("note: pip install pdfplumber to check that no box is cut across pages")
        return []
    mm = 72 / 25.4
    at_bottom, at_top = set(), set()
    cols_end: dict[int, set] = {}      # column x-positions of a table ending near the page bottom
    cols_start: dict[int, set] = {}    # column x-positions of a table starting at the page top
    with pdfplumber.open(str(pdf)) as doc:
        top, bottom = 16 * mm, doc.pages[0].height - 18 * mm      # same as @page margins
        for n, page in enumerate(doc.pages, 1):
            for r in page.rects:                                   # code/note boxes and header cells
                if r["width"] >= 20 and r["height"] >= 2 and r.get("non_stroking_color") not in (None, [1], (1,), [1, 1, 1], (1, 1, 1)):
                    if r["bottom"] > bottom - 1.5:
                        at_bottom.add(n)
                    if r["top"] < top + 1.5:
                        at_top.add(n)
            # table column borders are drawn as thin vertical rectangles (or lines)
            verticals = [l for l in page.lines if abs(l["x0"] - l["x1"]) < 0.5]
            verticals += [r for r in page.rects if r["width"] < 2 and r["height"] > 5]
            cols_end[n] = {round(l["x0"]) for l in verticals if l["bottom"] > bottom - 60}
            cols_start[n] = {round(l["x0"]) for l in verticals if l["top"] < top + 1.5}
    cuts = [(n, f"a box runs from page {n} onto page {n + 1}") for n in sorted(at_bottom) if n + 1 in at_top]
    cuts += [(n, f"a table is split between page {n} and page {n + 1}")
             for n in cols_end if cols_end[n] and cols_end[n] == cols_start.get(n + 1)]
    return sorted(cuts)


def find_pages(pdf: Path) -> dict[str, int]:
    from pypdf import PdfReader
    pages: dict[str, int] = {}
    for i, page in enumerate(PdfReader(str(pdf)).pages, 1):
        for key in re.findall(r"@@([A-Z]+\d*|ANS)@@", page.extract_text() or ""):
            pages.setdefault(key, i)
    return pages


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="first", type=int, default=1)
    ap.add_argument("--to", dest="last", type=int, default=6)
    ap.add_argument("--out", help="output PDF (default: print/Lessons-LXX-LYY.pdf)")
    ap.add_argument("--no-name-line", action="store_true", help="do not print a name/date line on the cover")
    args = ap.parse_args()

    lessons = lesson_files(args.first, args.last)
    out = Path(args.out) if args.out else ROOT / "print" / f"Lessons-L{args.first:02d}-L{args.last:02d}.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    footer = f"บทเรียนเครือข่าย ฉบับละเอียด · Level {args.first}–{args.last}"
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        first_pass = work / "pass1.pdf"
        render(build_html(lessons, None, args.first, args.last, not args.no_name_line), first_pass, footer, work)
        pages = find_pages(first_pass)          # where each lesson/answer section landed
        render(build_html(lessons, pages, args.first, args.last, not args.no_name_line), out, footer, work)
        check = find_pages(out)
        if any(check.get(k) != v for k, v in pages.items()):
            print("warning: page numbers shifted between passes; table of contents may be off by a page")
    cuts = audit_cuts(out)
    if cuts:
        print(f"warning: {len(cuts)} item(s) split across pages (too tall for one page?):")
        for _, what in cuts:
            print(f"  {what}")
    else:
        print("check: no code box, note box or table is split across pages")
    from pypdf import PdfReader
    print(f"wrote {out} ({len(PdfReader(str(out)).pages)} pages) · lessons: "
          + json.dumps({k: v for k, v in pages.items() if k.startswith('L') or k == 'ANS'}))


if __name__ == "__main__":
    main()
