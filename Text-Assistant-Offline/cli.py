"""Command-line interface.

    python cli.py correct  "ผมอยากกินข้าวมันไก่ที่ร้านนนั้น"
    python cli.py style    "พรุ่งนี้กูไม่ไปทำงานนะ" --style formal --gender male
    python cli.py style    "พรุ่งนี้กูไม่ไปทำงานนะ" --all
    python cli.py translate "สวัสดีครับ" --to en --back
    python cli.py translate -f letter.txt --to ja
    echo "ข้อความ" | python cli.py correct
    python cli.py status
"""
import argparse
import json
import sys

from textassist import LANGUAGES, STYLES, TextAssistant


def read_text(args) -> str:
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            return f.read()
    if args.text:
        return " ".join(args.text)
    if not sys.stdin.isatty():
        return sys.stdin.read()
    sys.exit("No text given. Pass it as an argument, with -f FILE, or through stdin.")


def print_result(r, as_json: bool, label: str = ""):
    if as_json:
        print(json.dumps(r.to_dict(), ensure_ascii=False, indent=2))
        return
    if label:
        print(f"[{label}]")
    print(r.text)
    for c in r.changes:
        print(f"  • {c['from']!r} → {c['to']!r}")
    for w in r.warnings:
        print(f"  ! {w}")
    if r.extra.get("back_translation"):
        print(f"  ↺ แปลกลับ: {r.extra['back_translation']}")


def main():
    ap = argparse.ArgumentParser(description="Offline Thai text assistant",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("text", nargs="*", help="text to process")
        p.add_argument("-f", "--file", help="read text from a UTF-8 file")
        p.add_argument("--json", action="store_true", help="print JSON")

    common(sub.add_parser("correct", help="แก้คำผิด / fix spelling"))

    p = sub.add_parser("style", help="ปรับระดับภาษา / rewrite tone")
    common(p)
    p.add_argument("-s", "--style", choices=list(STYLES), default="polite")
    p.add_argument("--all", action="store_true", help="show polite, formal and casual versions")
    p.add_argument("-g", "--gender", choices=["male", "female", "neutral"], default="neutral",
                   help="speaker, for ผม/ดิฉัน and ครับ/ค่ะ")

    p = sub.add_parser("translate", help="แปลภาษา / translate")
    common(p)
    p.add_argument("-t", "--to", dest="target", choices=list(LANGUAGES), default="en")
    p.add_argument("--from", dest="source", default="auto", help="source language (default: auto)")
    p.add_argument("-s", "--style", choices=list(STYLES), help="tone of the translation")
    p.add_argument("--glossary", help='JSON of fixed terms, e.g. \'{"ฝ่ายบุคคล": "HR Department"}\'')
    p.add_argument("--back", action="store_true", help="also translate back to check the meaning")

    sub.add_parser("status", help="show which models are installed")

    args = ap.parse_args()
    a = TextAssistant()

    if args.cmd == "status":
        print(json.dumps(a.status(), ensure_ascii=False, indent=2))
        return

    text = read_text(args)
    if args.cmd == "correct":
        print_result(a.correct(text), args.json)
    elif args.cmd == "style":
        if args.all:
            for s, r in a.rewrite_all(text, gender=args.gender).items():
                print_result(r, args.json, STYLES[s]["th"])
        else:
            print_result(a.rewrite(text, args.style, args.gender), args.json)
    elif args.cmd == "translate":
        glossary = json.loads(args.glossary) if args.glossary else None
        print_result(a.translate(text, args.target, args.source, glossary, args.style, args.back), args.json)


if __name__ == "__main__":
    main()
