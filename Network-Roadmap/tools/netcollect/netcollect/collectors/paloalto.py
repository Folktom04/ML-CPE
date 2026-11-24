"""Palo Alto Networks via the PAN-OS XML API (operational commands, read-only admin + API key).

Each request is ``GET /api/?type=op&cmd=<xml command>`` with the key in the
``X-PAN-KEY`` header. The answer is XML: ``<response status="success"><result>...``.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from ..model import DeviceResult, to_int
from ..transport import HttpTransport, TransportError
from .base import Collector

CMD = {
    "system": "<show><system><info></info></system></show>",
    "resources": "<show><system><resources></resources></system></show>",
    "sessions": "<show><session><info></info></session></show>",
    "interfaces": "<show><interface>all</interface></show>",
    "routes": "<show><routing><route></route></routing></show>",
    "bgp": "<show><routing><protocol><bgp><peer></peer></bgp></protocol></routing></show>",
    "vpn": "<show><vpn><ipsec-sa></ipsec-sa></vpn></show>",
    "ha": "<show><high-availability><state></state></high-availability></show>",
}


def parse_response(text: str) -> ET.Element:
    """Return the <result> element, raising on status="error"."""
    root = ET.fromstring(text)
    if root.get("status") != "success":
        msg = " ".join(root.itertext()).strip()
        raise TransportError(f"PAN-OS API error: {msg[:200]}")
    result = root.find("result")
    return result if result is not None else root


def _text(node: ET.Element | None, path: str) -> str | None:
    if node is None:
        return None
    found = node.find(path)
    return found.text.strip() if found is not None and found.text else None


class PaloAltoCollector(Collector):
    def open_transport(self) -> HttpTransport:
        d = self.device
        port = f":{d.port}" if d.port else ""
        return HttpTransport(
            base_url=f"https://{d.host}{port}",
            headers={"X-PAN-KEY": d.token or ""},
            verify=d.verify_tls,
            timeout=d.timeout,
        )

    def _op(self, t: Any, key: str, result: DeviceResult) -> ET.Element:
        text = t.get("/api/", params={"type": "op", "cmd": CMD[key]})
        result.raw[key] = text
        return parse_response(text)

    def collect_into(self, t: Any, result: DeviceResult) -> None:
        system = self._op(t, "system", result).find("system")
        result.facts = {
            "hostname": _text(system, "hostname"),
            "model": _text(system, "model"),
            "serial": _text(system, "serial"),
            "version": _text(system, "sw-version"),
            "uptime": _text(system, "uptime"),
            "threat_version": _text(system, "threat-version"),
        }
        self.section(result, "sessions", self._sessions, t, result)
        self.section(result, "interfaces", self._interfaces, t, result)
        self.section(result, "routes", self._routes, t, result)
        self.section(result, "bgp", self._bgp, t, result)
        self.section(result, "vpn", self._vpn, t, result)
        self.section(result, "ha", self._ha, t, result)

    def _sessions(self, t: Any, result: DeviceResult) -> None:
        res = self._op(t, "sessions", result)
        result.resources["sessions"] = to_int(_text(res, "num-active"))
        result.resources["session_max"] = to_int(_text(res, "num-max"))

    def _interfaces(self, t: Any, result: DeviceResult) -> None:
        res = self._op(t, "interfaces", result)
        ips = {}
        for e in res.findall("./ifnet/entry"):
            ips[_text(e, "name")] = {"ip": _text(e, "ip"), "zone": _text(e, "zone")}
        for e in res.findall("./hw/entry"):
            name = _text(e, "name")
            state = (_text(e, "state") or "").lower()
            info = ips.get(name, {})
            ip = info.get("ip")
            result.interfaces.append({
                "name": name,
                "ip": ip if ip and ip != "N/A" else None,
                "zone": info.get("zone"),
                "status": "up" if state == "up" else "down",
                "speed": _text(e, "speed"),
                "duplex": _text(e, "duplex"),
            })

    def _routes(self, t: Any, result: DeviceResult) -> None:
        for e in self._op(t, "routes", result).findall("./entry"):
            result.routes.append({
                "prefix": _text(e, "destination"),
                "nexthop": _text(e, "nexthop"),
                "interface": _text(e, "interface"),
                "protocol": _text(e, "flags"),
                "virtual_router": _text(e, "virtual-router"),
            })

    def _bgp(self, t: Any, result: DeviceResult) -> None:
        peers = []
        for e in self._op(t, "bgp", result).findall("./entry"):
            peers.append({
                "peer": (_text(e, "peer-address") or "").split(":")[0] or e.get("peer"),
                "remote_as": _text(e, "remote-as"),
                "state": (_text(e, "status") or "").lower(),
            })
        result.neighbors["bgp"] = peers

    def _vpn(self, t: Any, result: DeviceResult) -> None:
        for e in self._op(t, "vpn", result).findall("./entries/entry"):
            result.vpn.append({
                "name": _text(e, "name"),
                "peer": _text(e, "remote"),
                "gateway": _text(e, "gateway"),
                "status": "up",   # ipsec-sa lists only established SAs
            })

    def _ha(self, t: Any, result: DeviceResult) -> None:
        res = self._op(t, "ha", result)
        if (_text(res, "enabled") or "").lower() != "yes":
            result.ha = {"mode": "standalone"}
            return
        local = res.find("./group/local-info")
        peer = res.find("./group/peer-info")
        result.ha = {
            "mode": _text(res, "./group/mode") or "cluster",
            "role": _text(local, "state"),
            "peer_role": _text(peer, "state"),
            "in_sync": (_text(res, "./group/running-sync") or "").lower() == "synchronized",
        }
