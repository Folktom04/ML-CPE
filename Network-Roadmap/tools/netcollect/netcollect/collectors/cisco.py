"""Cisco IOS / IOS-XE / NX-OS over SSH (Netmiko) with TextFSM parsing (ntc-templates).

Each "section" maps to one show command. You can override commands per device:

    options:
      commands:
        interfaces_brief: "show ip interface brief vrf all"

TextFSM field names have changed between ntc-templates releases (upper/lower case,
renamed fields), so rows are normalised to lower-case keys and looked up with
fallbacks. The raw output of every command is kept in ``result.raw``.
"""
from __future__ import annotations

import re
from typing import Any

from ..model import DeviceResult, to_float, to_int
from ..transport import SshTransport
from .base import Collector

DEFAULT_COMMANDS = {
    "version": "show version",
    "cpu": "show processes cpu",
    "interfaces_brief": "show ip interface brief",
    "interfaces": "show interfaces",
    "routes": "show ip route",
    "bgp": "show ip bgp summary",
    "ospf": "show ip ospf neighbor",
    "hsrp": "show standby brief",
}

NXOS_COMMANDS = dict(DEFAULT_COMMANDS, cpu="show system resources", interfaces="show interface",
                     ospf="show ip ospf neighbors", hsrp="show hsrp brief")

CPU_PATTERNS = [
    re.compile(r"five minutes:\s*(\d+)%"),                 # IOS / IOS-XE
    re.compile(r"CPU states\s*:\s*[\d.]+% user,\s*[\d.]+% kernel,\s*([\d.]+)% idle"),  # NX-OS (idle)
]


def rows(output: Any) -> list[dict[str, Any]]:
    """Parsed TextFSM output -> list of dicts with lower-case keys. Raw text -> []."""
    if not isinstance(output, list):
        return []
    return [{str(k).lower(): v for k, v in row.items()} for row in output if isinstance(row, dict)]


def pick(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def first(value: Any) -> Any:
    return value[0] if isinstance(value, list) and value else value


class CiscoCollector(Collector):
    def commands(self) -> dict[str, str]:
        base = NXOS_COMMANDS if self.device.platform == "cisco_nxos" else DEFAULT_COMMANDS
        merged = dict(base)
        merged.update(self.device.options.get("commands", {}) or {})
        return merged

    def open_transport(self) -> SshTransport:
        d = self.device
        return SshTransport(d.platform, d.host, d.username, d.password, d.port, d.timeout)

    def _run(self, t: Any, key: str, result: DeviceResult, parse: bool = True) -> Any:
        cmd = self.commands()[key]
        output = t.run(cmd, parse=parse)
        result.raw[cmd] = output
        return output

    def collect_into(self, t: Any, result: DeviceResult) -> None:
        version = rows(self._run(t, "version", result))
        if not version:
            raise RuntimeError("could not parse 'show version' (is ntc-templates installed?)")
        v = version[0]
        result.facts = {
            "hostname": pick(v, "hostname"),
            "model": first(pick(v, "hardware", "platform", "chassis")),
            "serial": first(pick(v, "serial", "serial_number")),
            "version": pick(v, "version", "os"),
            "uptime": pick(v, "uptime"),
        }
        self.section(result, "cpu", self._cpu, t, result)
        self.section(result, "interfaces", self._interfaces, t, result)
        self.section(result, "routes", self._routes, t, result)
        self.section(result, "bgp", self._bgp, t, result)
        self.section(result, "ospf", self._ospf, t, result)
        self.section(result, "hsrp", self._hsrp, t, result)

    def _cpu(self, t: Any, result: DeviceResult) -> None:
        text = str(self._run(t, "cpu", result, parse=False))
        for i, pattern in enumerate(CPU_PATTERNS):
            m = pattern.search(text)
            if m:
                value = float(m.group(1))
                result.resources["cpu_pct"] = value if i == 0 else round(100 - value, 1)
                return

    def _interfaces(self, t: Any, result: DeviceResult) -> None:
        detail = {}
        for r in rows(self._run(t, "interfaces", result)):
            name = pick(r, "interface")
            detail[name] = {
                "crc": to_int(pick(r, "crc")) or 0,
                "input_errors": to_int(pick(r, "input_errors")) or 0,
                "output_errors": to_int(pick(r, "output_errors")) or 0,
                "duplex": pick(r, "duplex"),
                "speed": pick(r, "speed", "bandwidth"),
                "description": pick(r, "description"),
            }
        for r in rows(self._run(t, "interfaces_brief", result)):
            name = pick(r, "interface", "intf")
            status = str(pick(r, "status", "link_status") or "").lower()
            proto = str(pick(r, "proto", "protocol", "protocol_status") or "").lower()
            if "admin" in status:
                state = "admin-down"
            elif status == "up" and proto == "up":
                state = "up"
            else:
                state = "down"
            ip = pick(r, "ip_address", "ipaddr")
            d = detail.get(name, {})
            result.interfaces.append({
                "name": name,
                "ip": None if ip in (None, "unassigned") else first(ip),
                "status": state,
                "description": d.get("description"),
                "speed": d.get("speed"),
                "duplex": d.get("duplex"),
                "rx_errors": d.get("input_errors", 0),
                "tx_errors": d.get("output_errors", 0),
                "crc": d.get("crc", 0),
            })

    def _routes(self, t: Any, result: DeviceResult) -> None:
        for r in rows(self._run(t, "routes", result)):
            prefix = pick(r, "network")
            length = pick(r, "prefix_length", "mask")
            result.routes.append({
                "prefix": f"{prefix}/{length}" if prefix and length else prefix,
                "nexthop": first(pick(r, "nexthop_ip", "next_hop")),
                "interface": first(pick(r, "nexthop_if", "interface")),
                "protocol": pick(r, "protocol"),
            })

    def _bgp(self, t: Any, result: DeviceResult) -> None:
        peers = []
        for r in rows(self._run(t, "bgp", result)):
            state_raw = pick(r, "state_pfxrcd", "state_or_prefixes_received", "state", "prefixes_received")
            state_text = str(state_raw or "").strip()
            established = state_text.isdigit()
            peers.append({
                "peer": pick(r, "bgp_neigh", "neighbor", "neighbor_ip"),
                "remote_as": pick(r, "neigh_as", "remote_as"),
                "state": "established" if established else state_text.lower(),
                "prefixes": to_int(state_text) if established else None,
                "up_down": pick(r, "up_down", "uptime"),
            })
        result.neighbors["bgp"] = peers

    def _ospf(self, t: Any, result: DeviceResult) -> None:
        result.neighbors["ospf"] = [
            {
                "neighbor_id": pick(r, "neighbor_id"),
                "state": str(pick(r, "state") or "").split("/")[0].lower(),
                "address": pick(r, "address", "ip_address"),
                "interface": pick(r, "interface"),
            }
            for r in rows(self._run(t, "ospf", result))
        ]

    def _hsrp(self, t: Any, result: DeviceResult) -> None:
        groups = [
            {
                "interface": pick(r, "interface"),
                "group": pick(r, "group"),
                "state": str(pick(r, "state") or "").lower(),
                "virtual_ip": pick(r, "virtual_ip", "vip"),
                "priority": to_float(pick(r, "priority")),
            }
            for r in rows(self._run(t, "hsrp", result))
        ]
        if groups:
            result.ha = {"mode": "hsrp", "groups": groups}
