"""Command line entry point.

    python -m netcollect collect -i inventory.yaml              # all devices
    python -m netcollect collect -i inventory.yaml --mock       # try without real devices
    python -m netcollect collect -i inventory.yaml --tag site=BKK --platform fortigate
    python -m netcollect list -i inventory.yaml
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml

from . import __version__
from .checks import evaluate_all
from .inventory import InventoryError, filter_devices, load_inventory
from .report import write_reports
from .runner import collect_all

EXIT_OK, EXIT_FINDINGS, EXIT_FAILED, EXIT_USAGE = 0, 1, 2, 3


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="netcollect", description="Collect network device data in one run")
    p.add_argument("--version", action="version", version=f"netcollect {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("-i", "--inventory", required=True, help="inventory YAML file")
        sp.add_argument("--device", action="append", help="only this device name (repeatable)")
        sp.add_argument("--platform", action="append", help="only this platform (repeatable)")
        sp.add_argument("--tag", help="only devices with tag key=value, e.g. site=BKK")
        sp.add_argument("--mock", action="store_true", help="use built-in sample data, no network access")

    c = sub.add_parser("collect", help="collect data and write reports")
    common(c)
    c.add_argument("-o", "--output", default="output", help="output folder (a timestamped subfolder is created)")
    c.add_argument("-w", "--workers", type=int, default=10, help="devices in parallel (default 10)")
    c.add_argument("--thresholds", help="YAML file overriding health-check thresholds")
    c.add_argument("--raw", action="store_true", help="also save raw API/CLI output in device JSON")
    c.add_argument("--no-excel", action="store_true", help="skip report.xlsx")
    c.add_argument("-v", "--verbose", action="store_true")

    ls = sub.add_parser("list", help="show which devices would be collected")
    common(ls)
    return p


def _short(text: str, limit: int = 90) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _print_table(rows: list[list[str]], headers: list[str]) -> None:
    widths = [max(len(str(x)) for x in col) for col in zip(headers, *rows)] if rows else [len(h) for h in headers]
    line = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    print(line)
    print("-" * len(line))
    for r in rows:
        print("  ".join(str(x).ljust(w) for x, w in zip(r, widths)))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if getattr(args, "verbose", False) else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    try:
        devices = load_inventory(args.inventory, mock=args.mock)
        devices = filter_devices(devices, args.device, args.platform, args.tag)
    except (InventoryError, OSError, yaml.YAMLError) as exc:
        print(f"inventory error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    if not devices:
        print("no device matches the filters", file=sys.stderr)
        return EXIT_USAGE

    if args.command == "list":
        _print_table([[d.name, d.platform, d.host, json.dumps(d.tags, ensure_ascii=False)] for d in devices],
                     ["device", "platform", "host", "tags"])
        return EXIT_OK

    thresholds = {}
    if args.thresholds:
        thresholds = yaml.safe_load(Path(args.thresholds).read_text(encoding="utf-8")) or {}

    mode = " (MOCK data)" if args.mock else ""
    print(f"Collecting from {len(devices)} device(s), {args.workers} in parallel{mode} ...")

    def progress(r) -> None:
        mark = "OK  " if r.ok else "FAIL"
        print(f"  [{mark}] {r.device:<22} {r.duration_s:>6.2f}s  {_short(r.error or '')}")

    results = collect_all(devices, workers=args.workers, mock=args.mock, progress=progress)
    findings = evaluate_all(results, thresholds)

    outdir = Path(args.output) / datetime.now().strftime("%Y%m%d-%H%M%S")
    files = write_reports(results, findings, outdir, include_raw=args.raw, excel=not args.no_excel)

    ok = sum(r.ok for r in results)
    print(f"\nDevices: {ok}/{len(results)} collected")
    if findings:
        print(f"Findings: {sum(f.severity == 'critical' for f in findings)} critical, "
              f"{sum(f.severity == 'warning' for f in findings)} warning\n")
        _print_table([[f.severity, f.device, f.category, f.item, _short(f.message)] for f in findings[:30]],
                     ["severity", "device", "category", "item", "message"])
        if len(findings) > 30:
            print(f"... {len(findings) - 30} more in findings.csv")
    else:
        print("Findings: none")
    print(f"\nReports written to: {outdir}")
    for name, path in files.items():
        print(f"  {name:<10} {path}")

    if ok < len(results):
        return EXIT_FAILED
    return EXIT_FINDINGS if any(f.severity == "critical" for f in findings) else EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
