"""FortiGate via the FortiOS REST API (read-only API administrator + token).

Endpoints used (FortiOS 7.x; field names can differ slightly between versions, so
parsing is defensive and keeps the raw JSON in ``result.raw``):

  /api/v2/monitor/system/status              hostname, model, serial, version
  /api/v2/monitor/system/resource/usage      cpu, memory, sessions
  /api/v2/monitor/system/interface           link, speed, errors
  /api/v2/monitor/router/ipv4                routing table
  /api/v2/monitor/router/bgp/neighbors       BGP peers
  /api/v2/monitor/vpn/ipsec                  IPsec tunnels
  /api/v2/monitor/system/ha-checksums        HA config sync
  /api/v2/monitor/virtual-wan/health-check   SD-WAN SLA
"""
from __future__ import annotations

from typing import Any

from ..model import DeviceResult, to_float, to_int
from ..transport import HttpTransport
from .base import Collector

EP = {
    "status": "/api/v2/monitor/system/status",
    "resource": "/api/v2/monitor/system/resource/usage",
    "interfaces": "/api/v2/monitor/system/interface",
    "routes": "/api/v2/monitor/router/ipv4",
    "bgp": "/api/v2/monitor/router/bgp/neighbors",
    "vpn": "/api/v2/monitor/vpn/ipsec",
    "ha": "/api/v2/monitor/system/ha-checksums",
    "sdwan": "/api/v2/monitor/virtual-wan/health-check",
}


def _results(payload: Any) -> Any:
    return payload.get("results") if isinstance(payload, dict) else None


def _current(entry: Any) -> float | None:
    """resource/usage returns e.g. {"cpu": [{"current": 12, ...}]}."""
    if isinstance(entry, list) and entry:
        entry = entry[0]
    if isinstance(entry, dict):
        return to_float(entry.get("current"))
    return to_float(entry)


class FortiGateCollector(Collector):
    def open_transport(self) -> HttpTransport:
        d = self.device
        port = f":{d.port}" if d.port else ""
        return HttpTransport(
            base_url=f"https://{d.host}{port}",
            headers={"Authorization": f"Bearer {d.token}", "Accept": "application/json"},
            verify=d.verify_tls,
            timeout=d.timeout,
        )

    def _get(self, t: Any, key: str, result: DeviceResult) -> Any:
        params = {"vdom": self.device.vdom} if self.device.vdom else None
        payload = t.get(EP[key], params=params)
        result.raw[key] = payload
        return payload

    def collect_into(self, t: Any, result: DeviceResult) -> None:
        # status is mandatory: if it fails the device is reported as failed
        status = self._get(t, "status", result)
        res = _results(status) or {}
        result.facts = {
            "hostname": res.get("hostname"),
            "model": res.get("model_name") or res.get("model"),
            "serial": status.get("serial") or res.get("serial"),
            "version": status.get("version") or res.get("version"),
            "build": status.get("build"),
        }
        self.section(result, "resources", self._resources, t, result)
        self.section(result, "interfaces", self._interfaces, t, result)
        self.section(result, "routes", self._routes, t, result)
        self.section(result, "bgp", self._bgp, t, result)
        self.section(result, "vpn", self._vpn, t, result)
        self.section(result, "ha", self._ha, t, result)
        self.section(result, "sdwan", self._sdwan, t, result)

    def _resources(self, t: Any, result: DeviceResult) -> None:
        res = _results(self._get(t, "resource", result)) or {}
        result.resources = {
            "cpu_pct": _current(res.get("cpu")),
            "mem_pct": _current(res.get("mem")),
            "sessions": to_int(_current(res.get("session"))),
        }

    def _interfaces(self, t: Any, result: DeviceResult) -> None:
        res = _results(self._get(t, "interfaces", result)) or {}
        items = res.values() if isinstance(res, dict) else res
        for it in items:
            link = it.get("link")
            result.interfaces.append({
                "name": it.get("name"),
                "ip": f"{it.get('ip')}/{it.get('mask')}" if it.get("ip") and it.get("ip") != "0.0.0.0" else None,
                "status": "up" if link in (True, "up") else "down",
                "speed": it.get("speed"),
                "duplex": it.get("duplex"),
                "rx_errors": to_int(it.get("rx_errors")) or 0,
                "tx_errors": to_int(it.get("tx_errors")) or 0,
            })

    def _routes(self, t: Any, result: DeviceResult) -> None:
        for r in _results(self._get(t, "routes", result)) or []:
            result.routes.append({
                "prefix": r.get("ip_mask"),
                "nexthop": r.get("gateway"),
                "interface": r.get("interface"),
                "protocol": r.get("type"),
                "distance": r.get("distance"),
            })

    def _bgp(self, t: Any, result: DeviceResult) -> None:
        peers = []
        for n in _results(self._get(t, "bgp", result)) or []:
            peers.append({
                "peer": n.get("neighbor_ip"),
                "remote_as": n.get("remote_as"),
                "state": str(n.get("state", "")).lower(),
            })
        result.neighbors["bgp"] = peers

    def _vpn(self, t: Any, result: DeviceResult) -> None:
        for tun in _results(self._get(t, "vpn", result)) or []:
            proxies = tun.get("proxyid") or []
            up = [p for p in proxies if str(p.get("status", "")).lower() == "up"]
            result.vpn.append({
                "name": tun.get("name"),
                "peer": tun.get("rgwy"),
                "status": "up" if proxies and len(up) == len(proxies) else ("partial" if up else "down"),
                "selectors_up": f"{len(up)}/{len(proxies)}",
                "rx_bytes": sum(to_int(p.get("incoming_bytes")) or 0 for p in proxies),
                "tx_bytes": sum(to_int(p.get("outgoing_bytes")) or 0 for p in proxies),
            })

    def _ha(self, t: Any, result: DeviceResult) -> None:
        members = _results(self._get(t, "ha", result)) or []
        if not members:
            result.ha = {"mode": "standalone"}
            return
        sums = {str((m.get("checksum") or {}).get("all")) for m in members}
        result.ha = {
            "mode": "cluster",
            "members": [m.get("serial_no") for m in members],
            "in_sync": len(sums) == 1,
        }

    def _sdwan(self, t: Any, result: DeviceResult) -> None:
        res = _results(self._get(t, "sdwan", result)) or {}
        for hc_name, members in res.items():
            for member, m in (members or {}).items():
                result.sdwan.append({
                    "healthcheck": hc_name,
                    "member": member,
                    "status": m.get("status"),
                    "latency_ms": to_float(m.get("latency")),
                    "jitter_ms": to_float(m.get("jitter")),
                    "loss_pct": to_float(m.get("packet_loss")),
                })
