"""End-to-end self test: start the lab, run discover and collect for real, verify the results."""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from . import RunningLab, lab_env
from .model import load_lab


@contextmanager
def _env(values: dict[str, str]) -> Iterator[None]:
    old = {k: os.environ.get(k) for k in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class Checks:
    def __init__(self) -> None:
        self.rows: list[tuple[bool, str, str]] = []

    def check(self, ok: bool, what: str, detail: Any = "") -> None:
        self.rows.append((bool(ok), what, str(detail)))
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {what}" + (f"  ({detail})" if detail != "" else ""))

    @property
    def failed(self) -> int:
        return sum(1 for ok, *_ in self.rows if not ok)


def run_selftest(topology: str | None, outdir: Path, snmp_version: str = "3") -> int:
    from ..checks import evaluate_all
    from ..discovery import DiscoveryConfig, SnmpCredentials, run_discovery
    from ..discovery.output import write_discovery
    from ..inventory import load_inventory
    from ..report import write_reports
    from ..runner import collect_all

    lab = load_lab(topology)
    print(f"Starting lab ({sum(d.runs_snmp for d in lab.devices)} SNMP devices) ...")
    running = RunningLab(lab, outdir).start()
    c = Checks()
    try:
        env = lab_env(lab)
        ports = lab.settings["_ports"]
        with _env(env):
            # ---------------- 1) discover over real SNMP ----------------
            print(f"\n1) discover (SNMPv{snmp_version}, real UDP to the lab agents)")
            creds = SnmpCredentials(version=snmp_version, community=env["SNMP_COMMUNITY"], user=env["SNMP_USER"],
                                    auth_key=env["SNMP_AUTH_PASS"], priv_key=env["SNMP_PRIV_PASS"],
                                    port=ports["snmp"], timeout=1.0, retries=1)
            subnets = sorted({".".join(d.ip.split(".")[:3]) + ".0/24" for d in lab.devices
                              if d.runs_snmp and d.ip.startswith("127.0.10.")}) or ["127.0.10.0/24"]
            seeds = [lab.devices[0].ip]
            cfg = DiscoveryConfig(subnets=subnets, seeds=seeds, scope=["127.0.0.0/8"], max_hops=3,
                                  ping=False, arp=True, workers=64)
            result = run_discovery(cfg, creds)
            disc_dir = outdir / "selftest-discover"
            files = write_discovery(result, disc_dir, subnets, excel=True,
                                    inventory_path=outdir / "inventory.yaml",
                                    inventory_defaults=running.files["defaults"])
            found = {d.get("sys_name"): d for d in result.devices}
            for d in lab.devices:
                if d.runs_snmp:
                    got = found.get(d.name)
                    c.check(got is not None and got.get("snmp"), f"discover found {d.name}", d.ip)
                    if got and d.serials:
                        c.check(got.get("serials") == d.serials, f"{d.name} serial(s)", ", ".join(got.get("serials") or []))
                elif d.kind in ("ap", "phone") and any(d.name in link for link in lab.links):
                    c.check(d.name in found, f"{d.name} seen via CDP/LLDP (no SNMP)", (found.get(d.name) or {}).get("model"))
            dup = next((x for x in result.devices if x.get("other_ips")), None)
            c.check(dup is not None, "device answering on two IPs merged", dup and dup.get("other_ips"))
            c.check(result.neighbors, "CDP/LLDP neighbour links", len(result.neighbors))
            c.check(result.hosts, "hosts from ARP", len(result.hosts))
            c.check(files["inventory"].exists(), "inventory generated", files["inventory"])

            # ---------------- 2) collect over real SSH / HTTPS ----------------
            print("\n2) collect (SSH to Cisco, HTTPS REST/XML API to FortiGate/Palo Alto, TLS verified with lab CA)")
            devices = load_inventory(files["inventory"])
            results = collect_all(devices, workers=8)
            findings = evaluate_all(results)
            write_reports(results, findings, outdir / "selftest-collect")
            for r in results:
                c.check(r.ok, f"collect {r.device} ({r.platform})",
                        r.error or f"{r.facts.get('model')} {r.facts.get('serial')} {r.facts.get('version')}")
            by_dev = {(f.device, f.category) for f in findings}
            expected = [("core-sw-02", "ospf"), ("core-sw-02", "interface"), ("edge-rtr-01", "bgp"),
                        ("fgt-hq", "vpn"), ("pa-dmz-01", "bgp")]
            for dev, cat in expected:
                if any(x.device == dev for x in results):
                    c.check((dev, cat) in by_dev, f"finding detected: {dev} {cat}")
            cisco = next((r for r in results if r.platform == "cisco_ios" and r.neighbors.get("bgp")), None)
            if cisco:
                c.check(all(p.get("peer") for p in cisco.neighbors["bgp"]), "Cisco BGP peers parsed from CLI",
                        [p.get("peer") for p in cisco.neighbors["bgp"]])
    finally:
        running.stop()

    total = len(c.rows)
    print(f"\nSelf-test: {total - c.failed}/{total} checks passed · outputs in {outdir}")
    return 0 if c.failed == 0 else 1
