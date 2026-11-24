"""Turn collected data into findings ("what needs attention") using simple rules.

The rules follow the explained cheat sheets: CRC errors -> cabling, BGP not
established, OSPF stuck, VPN down, HA out of sync, SD-WAN SLA, high CPU/memory.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .model import DeviceResult

DEFAULT_THRESHOLDS = {
    "cpu_pct": 80.0,
    "mem_pct": 85.0,
    "interface_errors": 0,     # any CRC/input/output error counter above this is reported
    "sdwan_loss_pct": 2.0,
    "sdwan_latency_ms": 150.0,
    "sdwan_jitter_ms": 30.0,
    "probe_loss_pct": 5.0,
}

OSPF_OK = {"full", "2way"}


@dataclass
class Finding:
    device: str
    severity: str      # critical / warning / info
    category: str
    item: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate(result: DeviceResult, thresholds: dict[str, float] | None = None) -> list[Finding]:
    th = dict(DEFAULT_THRESHOLDS)
    th.update(thresholds or {})
    out: list[Finding] = []

    def add(sev: str, cat: str, item: str, msg: str) -> None:
        out.append(Finding(result.device, sev, cat, item, msg))

    if not result.ok:
        add("critical", "collection", result.host, f"collection failed: {result.error}")
        return out

    for err in result.extra.get("section_errors", []):
        add("info", "collection", "section", f"partial data: {err}")

    cpu = result.resources.get("cpu_pct")
    if cpu is not None and cpu >= th["cpu_pct"]:
        add("warning", "resources", "cpu", f"CPU {cpu:.0f}% >= {th['cpu_pct']:.0f}%")
    mem = result.resources.get("mem_pct")
    if mem is not None and mem >= th["mem_pct"]:
        add("warning", "resources", "memory", f"memory {mem:.0f}% >= {th['mem_pct']:.0f}% (FortiGate: conserve mode risk)")

    for intf in result.interfaces:
        if intf.get("status") != "up":
            continue
        errors = {k: intf.get(k) or 0 for k in ("crc", "rx_errors", "tx_errors")}
        bad = {k: v for k, v in errors.items() if v > th["interface_errors"]}
        if bad:
            detail = ", ".join(f"{k}={v}" for k, v in bad.items())
            add("warning", "interface", intf.get("name") or "?",
                f"error counters {detail} - check cable/SFP/duplex, clear counters and re-check")
        if str(intf.get("duplex") or "").lower().startswith("half"):
            add("warning", "interface", intf.get("name") or "?", "half duplex - possible duplex mismatch/bad cable")

    for peer in result.neighbors.get("bgp", []):
        if peer.get("state") != "established":
            add("critical", "bgp", str(peer.get("peer")),
                f"BGP not established (state={peer.get('state') or 'unknown'}, AS {peer.get('remote_as')})")
    for nb in result.neighbors.get("ospf", []):
        if nb.get("state") not in OSPF_OK:
            hint = " - EXSTART/EXCHANGE usually means MTU mismatch" if nb.get("state") in {"exstart", "exchange"} else ""
            add("critical", "ospf", str(nb.get("neighbor_id")), f"OSPF neighbor state {nb.get('state')}{hint}")

    for tun in result.vpn:
        if tun.get("status") != "up":
            add("critical", "vpn", str(tun.get("name")),
                f"IPsec tunnel {tun.get('status')} (selectors {tun.get('selectors_up', '?')}, peer {tun.get('peer')})")
        elif tun.get("tx_bytes") and not tun.get("rx_bytes"):
            add("warning", "vpn", str(tun.get("name")), "tunnel up, sending but receiving 0 bytes - check the remote side")

    ha = result.ha or {}
    if ha.get("in_sync") is False:
        add("critical", "ha", ha.get("mode", "ha"), "HA configuration NOT in sync")
    for g in ha.get("groups", []) or []:
        if g.get("state") not in {"active", "standby"}:
            add("warning", "ha", f"{g.get('interface')} grp {g.get('group')}", f"HSRP state {g.get('state')}")

    for m in result.sdwan:
        name = f"{m.get('healthcheck')}/{m.get('member')}"
        if str(m.get("status")).lower() != "up":
            add("critical", "sdwan", name, f"SD-WAN member {m.get('status')}")
            continue
        if (m.get("loss_pct") or 0) > th["sdwan_loss_pct"]:
            add("warning", "sdwan", name, f"packet loss {m['loss_pct']}%")
        if (m.get("latency_ms") or 0) > th["sdwan_latency_ms"]:
            add("warning", "sdwan", name, f"latency {m['latency_ms']} ms")
        if (m.get("jitter_ms") or 0) > th["sdwan_jitter_ms"]:
            add("warning", "sdwan", name, f"jitter {m['jitter_ms']} ms")

    for c in result.checks:
        target = str(c.get("target"))
        if not c.get("ok"):
            add("critical", c.get("test", "probe"), target, f"{c.get('test')} failed: {c.get('detail', '')}".strip())
        elif c.get("test") == "ping" and (c.get("loss_pct") or 0) > th["probe_loss_pct"]:
            add("warning", "ping", target, f"packet loss {c['loss_pct']}%")
    return out


def evaluate_all(results: list[DeviceResult], thresholds: dict[str, float] | None = None) -> list[Finding]:
    findings: list[Finding] = []
    for r in results:
        findings.extend(evaluate(r, thresholds))
    order = {"critical": 0, "warning": 1, "info": 2}
    return sorted(findings, key=lambda f: (order.get(f.severity, 9), f.device))
