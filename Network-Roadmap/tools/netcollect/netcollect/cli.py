"""Command line entry point.

    python -m netcollect collect -i inventory.yaml              # all devices
    python -m netcollect collect -i inventory.yaml --mock       # try without real devices
    python -m netcollect collect -i inventory.yaml --tag site=BKK --platform fortigate
    python -m netcollect list -i inventory.yaml
    python -m netcollect discover --subnet 10.0.10.0/24 --seed 10.0.10.2      # find devices via SNMP
"""
from __future__ import annotations

import argparse
import json
import logging
import os
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

    d = sub.add_parser("discover", help="find devices on subnets via SNMP (name, vendor, model, serial, version)")
    d.add_argument("--subnet", action="append", default=[], help="subnet to sweep, e.g. 10.0.10.0/24 (repeatable)")
    d.add_argument("--seed", action="append", default=[],
                   help="start CDP/LLDP crawl from this device IP, e.g. the core switch (repeatable)")
    d.add_argument("--max-hops", type=int, default=3, help="how far the CDP/LLDP crawl may go (default 3; 0 = read neighbours but do not follow)")
    d.add_argument("--scope", action="append", default=[],
                   help="CIDR the crawl may enter (default: private addresses only)")
    d.add_argument("--exclude", action="append", default=[], help="IP or CIDR never to query (repeatable)")
    d.add_argument("--ping", action="store_true", help="also ping-sweep to list hosts that do not answer SNMP")
    d.add_argument("--arp", action="store_true", help="also read ARP tables of SNMP devices (IP/MAC of all hosts)")
    d.add_argument("--snmp-version", choices=["2c", "3"], default="2c")
    d.add_argument("--community-env", default="SNMP_COMMUNITY", help="env var holding the v2c community")
    d.add_argument("--v3-user-env", default="SNMP_USER", help="env var holding the SNMPv3 user")
    d.add_argument("--v3-auth-env", default="SNMP_AUTH_PASS", help="env var holding the v3 auth password")
    d.add_argument("--v3-priv-env", default="SNMP_PRIV_PASS", help="env var holding the v3 privacy password")
    d.add_argument("--v3-auth-proto", default="SHA", help="MD5, SHA, SHA224, SHA256, SHA384, SHA512")
    d.add_argument("--v3-priv-proto", default="AES", help="DES, AES (AES128), AES192, AES256")
    d.add_argument("--snmp-port", type=int, default=161)
    d.add_argument("--timeout", type=float, default=2.0, help="SNMP timeout in seconds (default 2)")
    d.add_argument("--retries", type=int, default=1)
    d.add_argument("-w", "--workers", type=int, default=32, help="parallel queries (default 32)")
    d.add_argument("--allow-large", action="store_true", help="allow sweeping more than 1024 addresses")
    d.add_argument("-o", "--output", default="output", help="output folder (a timestamped subfolder is created)")
    d.add_argument("--inventory-out", help="where to write the generated inventory YAML")
    d.add_argument("--no-excel", action="store_true")
    d.add_argument("--mock", action="store_true", help="use built-in sample network, no network access")
    d.add_argument("-v", "--verbose", action="store_true")
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
    if args.command == "discover":
        return _discover(args)
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


def _discover(args: argparse.Namespace) -> int:
    from .discovery import DiscoveryConfig, DiscoveryError, SnmpCredentials, SnmpError, run_discovery
    from .discovery.output import write_discovery

    if not args.subnet and not args.seed:
        print("give at least one --subnet or --seed", file=sys.stderr)
        return EXIT_USAGE
    env = os.environ.get
    if args.snmp_version == "3":
        creds = SnmpCredentials(version="3", user=env(args.v3_user_env), auth_key=env(args.v3_auth_env),
                                priv_key=env(args.v3_priv_env), auth_proto=args.v3_auth_proto,
                                priv_proto=args.v3_priv_proto)
        missing = [] if creds.user else [args.v3_user_env]
    else:
        creds = SnmpCredentials(version="2c", community=env(args.community_env))
        missing = [] if creds.community else [args.community_env]
    if missing and not args.mock:
        print(f"environment variable {missing[0]} is not set (SNMP credentials)", file=sys.stderr)
        return EXIT_USAGE
    creds.port, creds.timeout, creds.retries = args.snmp_port, args.timeout, args.retries
    cfg = DiscoveryConfig(subnets=args.subnet, seeds=args.seed, exclude=args.exclude, scope=args.scope,
                          max_hops=max(0, args.max_hops), workers=args.workers, ping=args.ping, arp=args.arp,
                          allow_large=args.allow_large)

    mode = " (MOCK network)" if args.mock else ""
    print(f"Discovering{mode}: subnets={args.subnet or '-'} seeds={args.seed or '-'} using {creds.describe()}")
    try:
        result = run_discovery(cfg, creds, mock=args.mock)
    except (DiscoveryError, SnmpError) as exc:
        print(f"discovery error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    outdir = Path(args.output) / ("discover-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    files = write_discovery(result, outdir, args.subnet, excel=not args.no_excel,
                            inventory_path=Path(args.inventory_out) if args.inventory_out else None)
    st = result.stats
    seeds = f" + {st['seeds']} seed(s)" if st.get("seeds") else ""
    print(f"\nSwept {st.get('addresses_swept', 0)} address(es){seeds}: {st.get('snmp_answered', 0)} answered SNMP · "
          f"devices {st.get('devices', 0)} (with serial {st.get('with_serial', 0)})"
          + (f" · CDP/LLDP links {st['neighbor_links']}" if "neighbor_links" in st else "")
          + (f" · hosts {st['hosts']}" if "hosts" in st else ""))
    if result.devices:
        print()
        _print_table([[d.get("name"), d.get("ip") or "-", d.get("vendor") or "-", _short(d.get("model") or "-", 28),
                       d.get("serial") or "-", _short(d.get("version") or "-", 18), d.get("type") or "-",
                       d.get("platform") or "-"] for d in result.devices],
                     ["name", "ip", "vendor", "model", "serial", "version", "type", "collect"])
    if result.errors:
        print(f"\n{len(result.errors)} SNMP error(s) (wrong credentials/version?) - see errors.csv")
    print(f"\nReports written to: {outdir}")
    for name, path in files.items():
        print(f"  {name:<10} {path}")
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
