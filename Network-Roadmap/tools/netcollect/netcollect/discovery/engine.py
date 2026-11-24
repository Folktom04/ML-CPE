"""Discovery engine: subnet sweep -> SNMP identify -> CDP/LLDP crawl -> host list (ping/ARP).

Everything runs in one asyncio loop with a semaphore limiting concurrent queries.
"""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import platform as _platform
import re
import subprocess
from dataclasses import dataclass, field
from typing import Any

from ..collectors import probe
from . import mibs
from .snmp import SnmpError, SnmpTimeout

log = logging.getLogger(__name__)

MAX_HOSTS_DEFAULT = 1024


class DiscoveryError(ValueError):
    pass


@dataclass
class DiscoveryConfig:
    subnets: list[str] = field(default_factory=list)
    seeds: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    scope: list[str] = field(default_factory=list)       # where the CDP/LLDP crawl may go
    max_hops: int = 3
    workers: int = 32
    ping: bool = False
    arp: bool = False
    allow_large: bool = False


@dataclass
class DiscoveryResult:
    devices: list[dict[str, Any]] = field(default_factory=list)
    neighbors: list[dict[str, Any]] = field(default_factory=list)
    hosts: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)


def expand_targets(cfg: DiscoveryConfig) -> list[str]:
    excluded: list[ipaddress.IPv4Network] = []
    for e in cfg.exclude:
        try:
            excluded.append(ipaddress.ip_network(e, strict=False))
        except ValueError as exc:
            raise DiscoveryError(f"bad --exclude {e}: {exc}") from exc
    targets: list[str] = []
    seen: set[str] = set()
    for s in cfg.subnets:
        try:
            net = ipaddress.ip_network(s, strict=False)
        except ValueError as exc:
            raise DiscoveryError(f"bad --subnet {s}: {exc}") from exc
        if net.version != 4:
            raise DiscoveryError(f"{s}: only IPv4 subnets can be swept")
        hosts = [net.network_address] if net.num_addresses == 1 else list(net.hosts())
        for ip in hosts:
            if any(ip in x for x in excluded):
                continue
            if str(ip) not in seen:
                seen.add(str(ip))
                targets.append(str(ip))
    total = len(targets)
    if total > MAX_HOSTS_DEFAULT and not cfg.allow_large:
        raise DiscoveryError(f"{total} addresses to sweep (> {MAX_HOSTS_DEFAULT}); narrow the subnets "
                             "or add --allow-large")
    return targets


def in_scope(ip: str | None, cfg: DiscoveryConfig) -> bool:
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if any(addr in ipaddress.ip_network(e, strict=False) for e in cfg.exclude):
        return False
    if cfg.scope:
        return any(addr in ipaddress.ip_network(s, strict=False) for s in cfg.scope)
    return addr.is_private and not addr.is_loopback   # safe default: never crawl to public addresses


class Discoverer:
    def __init__(self, client: Any, cfg: DiscoveryConfig, mock: bool = False):
        self.client = client
        self.cfg = cfg
        self.mock = mock
        self.sem = asyncio.Semaphore(max(1, cfg.workers))
        self.by_ip: dict[str, dict[str, Any]] = {}
        self.result = DiscoveryResult()
        self.attempted: set[str] = set()

    # ---------------- identify one IP ----------------
    async def identify(self, ip: str, found_by: str) -> dict[str, Any] | None:
        if ip in self.attempted:
            return self.by_ip.get(ip)
        self.attempted.add(ip)
        async with self.sem:
            try:
                sys_values = await self.client.get(ip, list(mibs.SYS.values()))
            except SnmpTimeout:
                return None
            except SnmpError as exc:
                self.result.errors.append({"ip": ip, "stage": "snmp", "error": str(exc)})
                return None
            except Exception as exc:  # unexpected transport problems must not stop the sweep
                self.result.errors.append({"ip": ip, "stage": "snmp", "error": f"{type(exc).__name__}: {exc}"})
                return None
            s = {k: sys_values.get(oid) for k, oid in mibs.SYS.items()}
            if all(v is None for v in s.values()):
                return None
            dev = await self._details(ip, s, found_by)
        self.by_ip[ip] = dev
        return dev

    async def _details(self, ip: str, s: dict[str, Any], found_by: str) -> dict[str, Any]:
        descr = mibs.text(s["descr"])
        object_id = s["object_id"] if isinstance(s["object_id"], str) else mibs.text(s["object_id"])
        ent_no = mibs.enterprise(object_id)
        vendor_info = mibs.VENDORS.get(ent_no or -1, {})
        dev: dict[str, Any] = {
            "ip": ip,
            "sys_name": mibs.text(s["name"]),
            "vendor": vendor_info.get("vendor") or (f"enterprise {ent_no}" if ent_no else None),
            "description": mibs.one_line(descr, 200),
            "sys_object_id": object_id,
            "location": mibs.text(s["location"]),
            "contact": mibs.text(s["contact"]),
            "uptime": mibs.uptime_text(s["uptime"]),
            "found_by": found_by,
            "snmp": True,
            "model": None, "serial": None, "serials": [], "version": None,
        }

        # ENTITY-MIB: chassis model / serial / software revision
        try:
            rows = await self.client.walk(ip, mibs.ENT)
            entities = mibs.table(rows, mibs.ENT, mibs.ENT_COLS)
        except SnmpError:
            entities = {}
        chassis = [e for e in entities.values() if e.get("class") == mibs.ENT_CLASS_CHASSIS]
        with_serial = [e for e in chassis if mibs.text(e.get("serial"))] or \
                      [e for e in entities.values() if mibs.text(e.get("serial")) and mibs.text(e.get("model"))]
        if with_serial:
            dev["serials"] = [mibs.text(e.get("serial")) for e in with_serial]
            dev["serial"] = dev["serials"][0]
            dev["model"] = mibs.text(with_serial[0].get("model")) or mibs.text(with_serial[0].get("name"))
            dev["version"] = mibs.text(with_serial[0].get("sw_rev"))
        elif chassis:
            dev["model"] = mibs.text(chassis[0].get("model"))

        # Vendor specific OIDs (FortiGate, Palo Alto, old Cisco) and Printer-MIB serial as fallbacks
        extra = {k: v for k, v in vendor_info.items() if k in ("serial", "version", "model")}
        if not dev["serial"]:
            extra.setdefault("printer_serial", mibs.PRINTER_SERIAL)
        if not dev["model"]:
            extra.setdefault("hr_model", mibs.HR_DEVICE_DESCR)
        if extra:
            try:
                got = await self.client.get(ip, list(extra.values()))
            except SnmpError:
                got = {}
            values = {k: mibs.text(got.get(oid)) for k, oid in extra.items()}
            dev["serial"] = dev["serial"] or values.get("serial") or values.get("printer_serial")
            if dev["serial"] and not dev["serials"]:
                dev["serials"] = [dev["serial"]]
            if values.get("version"):
                dev["version"] = values["version"]
            dev["model"] = dev["model"] or values.get("model") or values.get("hr_model")

        if dev["vendor"] == "Fortinet" and not dev["model"]:
            dev["model"] = descr
        dev["version"] = mibs.clean_version(dev["version"]) or mibs.parse_version(descr)
        dev["vendor"] = mibs.refine_vendor(dev["vendor"], descr)
        dev["type"] = mibs.guess_type(dev["model"], descr, dev["sys_name"])
        dev["platform"] = mibs.guess_platform(dev["vendor"], descr, dev["model"])
        return dev

    # ---------------- neighbours ----------------
    async def neighbors_of(self, dev: dict[str, Any]) -> list[dict[str, Any]]:
        ip = dev["ip"]
        found: list[dict[str, Any]] = []
        async with self.sem:
            found += await self._lldp(ip, dev)
            found += await self._cdp(ip, dev)
        return found

    async def _lldp(self, ip: str, dev: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            rows = await self.client.walk(ip, mibs.LLDP_REM)
        except SnmpError:
            return []
        if not rows:
            return []
        remotes = mibs.table(rows, mibs.LLDP_REM, mibs.LLDP_REM_COLS)
        try:
            loc = mibs.table(await self.client.walk(ip, mibs.LLDP_LOC_PORT), mibs.LLDP_LOC_PORT, mibs.LLDP_LOC_COLS)
        except SnmpError:
            loc = {}
        addresses: dict[str, str] = {}
        try:
            for oid, _ in await self.client.walk(ip, mibs.LLDP_MAN_ADDR):
                parts = oid[len(mibs.LLDP_MAN_ADDR) + 1:].split(".")
                # index: timeMark.localPort.remIndex.addrSubtype.addrLen.addr...
                if len(parts) >= 9 and parts[3] == "1" and parts[4] == "4":
                    addresses.setdefault(".".join(parts[:3]), ".".join(parts[5:9]))
        except SnmpError:
            pass
        out = []
        for index, r in remotes.items():
            parts = index.split(".")
            local_port_num = parts[1] if len(parts) > 1 else ""
            lp = loc.get(local_port_num, {})
            local_port = mibs.text(lp.get("port_desc")) or mibs.text(lp.get("port_id")) or local_port_num
            out.append({
                "protocol": "lldp", "local_device": dev.get("sys_name") or ip, "local_ip": ip,
                "local_port": local_port,
                "remote_name": mibs.text(r.get("sys_name")) or mibs.mac(r.get("chassis_id")),
                "remote_port": mibs.text(r.get("port_desc")) or mibs.text(r.get("port_id")),
                "remote_ip": addresses.get(index),
                "remote_platform": mibs.one_line(r.get("sys_desc")),
                "remote_chassis_id": mibs.mac(r.get("chassis_id")),
            })
        return out

    async def _cdp(self, ip: str, dev: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            rows = await self.client.walk(ip, mibs.CDP_CACHE)
        except SnmpError:
            return []
        if not rows:
            return []
        cache = mibs.table(rows, mibs.CDP_CACHE, mibs.CDP_COLS)
        try:
            if_names = {oid.rsplit(".", 1)[1]: mibs.text(v) for oid, v in await self.client.walk(ip, mibs.IF_NAME)}
        except SnmpError:
            if_names = {}
        out = []
        for index, r in cache.items():
            if_index = index.split(".")[0]
            out.append({
                "protocol": "cdp", "local_device": dev.get("sys_name") or ip, "local_ip": ip,
                "local_port": if_names.get(if_index) or f"ifIndex {if_index}",
                "remote_name": mibs.text(r.get("device_id")),
                "remote_port": mibs.text(r.get("device_port")),
                "remote_ip": mibs.ipv4_from_bytes(r.get("address")) if r.get("address_type") in (1, None) else None,
                "remote_platform": mibs.one_line(r.get("platform")),
                "remote_chassis_id": None,
            })
        return out

    # ---------------- hosts (ping sweep + ARP) ----------------
    async def ping_sweep(self, targets: list[str]) -> list[str]:
        if self.mock:
            return [ip for ip in targets if ip in self.client.ping_alive]

        async def one(ip: str) -> str | None:
            async with self.sem:
                res = await asyncio.to_thread(probe.ping, ip, 1, 1)
            return ip if res.get("ok") else None

        return [ip for ip in await asyncio.gather(*(one(ip) for ip in targets)) if ip]

    async def arp_tables(self, devices: list[dict[str, Any]]) -> list[dict[str, Any]]:
        hosts = []

        async def one(dev: dict[str, Any]) -> None:
            async with self.sem:
                try:
                    rows = await self.client.walk(dev["ip"], mibs.ARP_PHYS)
                except SnmpError:
                    return
            for oid, value in rows:
                parts = oid[len(mibs.ARP_PHYS) + 1:].split(".")
                if len(parts) == 5:
                    hosts.append({"ip": ".".join(parts[1:]), "mac": mibs.mac(value),
                                  "source": f"arp@{dev.get('sys_name') or dev['ip']}"})

        await asyncio.gather(*(one(d) for d in devices))
        return hosts

    # ---------------- whole run ----------------
    async def run(self) -> DiscoveryResult:
        cfg = self.cfg
        targets = expand_targets(cfg)
        seeds = [s for s in cfg.seeds if s not in targets]
        self.result.stats["addresses_swept"] = len(targets)
        self.result.stats["seeds"] = len(seeds)

        found = await asyncio.gather(*(self.identify(ip, "sweep") for ip in targets),
                                     *(self.identify(ip, "seed") for ip in seeds))
        level = [d for d in found if d]
        self.result.stats["snmp_answered"] = len(level)

        if cfg.seeds:
            await self._crawl(level)

        if cfg.ping or cfg.arp:
            await self._hosts(targets)

        self.result.devices = self._merge_devices()
        self.result.stats["devices"] = len(self.result.devices)
        self.result.stats["with_serial"] = sum(1 for d in self.result.devices if d.get("serial"))
        return self.result

    async def _crawl(self, start: list[dict[str, Any]]) -> None:
        crawled: set[str] = set()     # device keys, so a switch answering on several IPs is read once
        level = start
        for hop in range(self.cfg.max_hops + 1):
            todo = []
            for d in level:
                if device_key(d) not in crawled:
                    crawled.add(device_key(d))
                    todo.append(d)
            if not todo:
                break
            neighbor_lists = await asyncio.gather(*(self.neighbors_of(d) for d in todo))
            next_ips: list[str] = []
            for items in neighbor_lists:
                self.result.neighbors.extend(items)
                for n in items:
                    rip = n.get("remote_ip")
                    if hop < self.cfg.max_hops and in_scope(rip, self.cfg) and rip not in self.attempted:
                        next_ips.append(rip)
            next_ips = list(dict.fromkeys(next_ips))
            level = [d for d in await asyncio.gather(*(self.identify(ip, f"cdp/lldp hop {hop + 1}")
                                                       for ip in next_ips)) if d]
        self.result.stats["neighbor_links"] = len(self.result.neighbors)

    async def _hosts(self, targets: list[str]) -> None:
        hosts: dict[str, dict[str, Any]] = {}
        if self.cfg.ping:
            for ip in await self.ping_sweep(targets):
                hosts[ip] = {"ip": ip, "mac": None, "source": "ping"}
            for n in (self.client.local_neighbors if self.mock else local_neighbor_table()):
                if n["ip"] in hosts or n["ip"] in targets:
                    entry = hosts.setdefault(n["ip"], {"ip": n["ip"], "mac": None, "source": "local-arp"})
                    entry["mac"] = entry["mac"] or n.get("mac")
        if self.cfg.arp:
            for h in await self.arp_tables(list(self.by_ip.values())):
                entry = hosts.setdefault(h["ip"], {"ip": h["ip"], "mac": None, "source": h["source"]})
                entry["mac"] = entry["mac"] or h["mac"]
                if h["source"] not in entry["source"]:
                    entry["source"] += f", {h['source']}"
        for ip, h in hosts.items():
            dev = self.by_ip.get(ip)
            h["snmp_device"] = (dev.get("sys_name") or ip) if dev else None
        self.result.hosts = sorted(hosts.values(), key=lambda h: ipaddress.ip_address(h["ip"]))
        self.result.stats["hosts"] = len(self.result.hosts)

    def _merge_devices(self) -> list[dict[str, Any]]:
        """One row per physical device: the same switch can answer on several IPs (SVIs)."""
        merged: dict[str, dict[str, Any]] = {}
        for dev in self.by_ip.values():
            key = device_key(dev)
            if key in merged:
                merged[key].setdefault("other_ips", []).append(dev["ip"])
                continue
            merged[key] = dict(dev, other_ips=[])

        known_names = {(d.get("sys_name") or "").lower().split(".")[0] for d in merged.values()}
        known_ips = set(self.by_ip)
        for n in self.result.neighbors:   # neighbours that do not answer SNMP (phones, APs, ...)
            name = n.get("remote_name")
            short = (name or "").lower().split(".")[0].split("(")[0]
            if not name or short in known_names or (n.get("remote_ip") in known_ips):
                continue
            known_names.add(short)
            merged[f"nbr:{short}"] = {
                "ip": n.get("remote_ip"), "sys_name": name, "vendor": None, "model": n.get("remote_platform"),
                "serial": None, "serials": [], "version": mibs.parse_version(n.get("remote_platform")),
                "type": mibs.guess_type(n.get("remote_platform"), name),
                "platform": None, "found_by": f"{n['protocol']} from {n['local_device']}", "snmp": False,
                "other_ips": [], "description": n.get("remote_platform"),
            }
        return sorted(merged.values(), key=lambda d: (not d.get("snmp"), _ip_key(d.get("ip"))))


def device_key(dev: dict[str, Any]) -> str:
    return (dev.get("serial") or "").lower() or (dev.get("sys_name") or "").lower() or dev["ip"]


def _ip_key(ip: str | None) -> tuple[int, int]:
    try:
        return (0, int(ipaddress.ip_address(ip or "")))
    except ValueError:
        return (1, 0)


NEIGH_RE = [
    re.compile(r"^(\d+\.\d+\.\d+\.\d+)\s.*lladdr\s+([0-9a-fA-F:]{17})"),              # Linux: ip neigh
    re.compile(r"^\s*(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F]{2}(?:-[0-9a-fA-F]{2}){5})"),  # Windows: arp -a
    re.compile(r"\((\d+\.\d+\.\d+\.\d+)\) at ([0-9a-fA-F:]{11,17})"),                  # macOS/BSD: arp -a
]


def parse_neighbor_table(output: str) -> list[dict[str, str]]:
    found = []
    for line in output.splitlines():
        for pattern in NEIGH_RE:
            m = pattern.search(line)
            if m:
                found.append({"ip": m.group(1), "mac": mibs.mac(m.group(2))})
                break
    return found


def local_neighbor_table() -> list[dict[str, str]]:
    """IP/MAC learned by this computer (only devices in the same L2 segment)."""
    cmd = ["ip", "neigh", "show"] if _platform.system() == "Linux" else ["arp", "-a"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    return parse_neighbor_table(out)
