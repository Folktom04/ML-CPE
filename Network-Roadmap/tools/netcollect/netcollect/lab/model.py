"""Load a lab topology and turn it into per-device SNMP OID tables, CLI and API data."""
from __future__ import annotations

import ipaddress
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..discovery import mibs

DEFAULT_TOPOLOGY = Path(__file__).with_name("topology.yaml")
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

SNMP_KINDS = {"cisco_ios", "aruba_switch", "huawei_switch", "fortigate", "paloalto", "printer", "linux"}
NEIGHBOR_TABLE_KINDS = {"cisco_ios", "aruba_switch", "huawei_switch"}
CDP_KINDS = {"cisco_ios"}
ALL_KINDS = SNMP_KINDS | {"ap", "phone", "host"}


class LabError(ValueError):
    pass


def oid(text: str) -> tuple[int, ...]:
    return tuple(int(x) for x in text.strip(".").split("."))


@dataclass
class LabDevice:
    name: str
    kind: str
    ip: str
    extra_ips: list[str] = field(default_factory=list)
    model: str | None = None
    model_text: str | None = None
    serials: list[str] = field(default_factory=list)
    version: str | None = None
    location: str | None = None
    api_token: str | None = None
    cli: dict[str, Any] = field(default_factory=dict)
    snmp: dict[tuple[int, ...], tuple[str, Any]] = field(default_factory=dict)   # oid -> (type, value)

    @property
    def runs_snmp(self) -> bool:
        return self.kind in SNMP_KINDS

    def mac(self, n: int = 0) -> str:
        last = [int(x) for x in self.ip.split(".")]
        return "70:0f:%02x:%02x:%02x:%02x" % (last[1], last[2], last[3], n)

    def set(self, o: str, kind: str, value: Any) -> None:
        self.snmp[oid(o)] = (kind, value)


@dataclass
class Lab:
    settings: dict[str, Any]
    devices: list[LabDevice]
    links: list[list[str]]
    hosts: dict[str, Any]

    def by_name(self, name: str) -> LabDevice:
        for d in self.devices:
            if d.name == name:
                return d
        raise LabError(f"unknown device in links/hosts: {name}")

    def addresses(self) -> list[str]:
        out = []
        for d in self.devices:
            if d.runs_snmp:
                out += [d.ip, *d.extra_ips]
        return out


def load_lab(path: str | Path | None = None) -> Lab:
    data = yaml.safe_load(Path(path or DEFAULT_TOPOLOGY).read_text(encoding="utf-8")) or {}
    settings = data.get("lab", {}) or {}
    devices = []
    seen_ip: set[str] = set()
    for raw in data.get("devices", []) or []:
        kind = raw.get("kind")
        if kind not in ALL_KINDS:
            raise LabError(f"{raw.get('name')}: unknown kind {kind} (use {sorted(ALL_KINDS)})")
        d = LabDevice(name=raw["name"], kind=kind, ip=str(raw["ip"]),
                      extra_ips=[str(x) for x in raw.get("extra_ips", [])],
                      model=raw.get("model"), model_text=raw.get("model_text"),
                      serials=[str(s) for s in raw.get("serials", [])], version=str(raw.get("version") or "") or None,
                      location=raw.get("location"), api_token=raw.get("api_token"), cli=raw.get("cli", {}) or {})
        for ip in [d.ip, *d.extra_ips]:
            addr = ipaddress.ip_address(ip)
            if d.runs_snmp and not addr.is_loopback:
                raise LabError(f"{d.name}: lab devices must use 127.x.x.x addresses (got {ip})")
            if ip in seen_ip:
                raise LabError(f"duplicate lab IP {ip}")
            seen_ip.add(ip)
        devices.append(d)
    lab = Lab(settings=settings, devices=devices, links=data.get("links", []) or [],
              hosts=data.get("hosts", {}) or {})
    build_snmp(lab)
    return lab


# ----------------------------------------------------------------------------------------
# SNMP tables

PROFILES = {
    "cisco_ios": ("1.3.6.1.4.1.9.1.2494",
                  "Cisco IOS Software [Cupertino], Catalyst L3 Switch Software (CAT9K_IOSXE), Version {version}, "
                  "RELEASE SOFTWARE (fc3)\r\nTechnical Support: http://www.cisco.com/techsupport"),
    "aruba_switch": ("1.3.6.1.4.1.11.2.3.7.11.181",
                     "{model_text}, revision {version}, ROM WC.16.01.0008 (/ws/swbuildm/rel_lab/code/build)"),
    "huawei_switch": ("1.3.6.1.4.1.2011.2.23.505",
                      "{model}\r\nHuawei Versatile Routing Platform Software\r\nVRP (R) software,Version {version}\r\n"
                      "Copyright (C) 2000-2023 HUAWEI TECH Co., Ltd."),
    "fortigate": ("1.3.6.1.4.1.12356.101.1.1004", "{model}"),
    "paloalto": ("1.3.6.1.4.1.25461.2.3.38", "Palo Alto Networks PA-3400 series firewall"),
    "printer": ("1.3.6.1.4.1.11.2.3.9.1",
                "HP ETHERNET MULTI-ENVIRONMENT,ROM none,JETDIRECT,JD153,EEPROM JSI24090012"),
    "linux": ("1.3.6.1.4.1.8072.3.2.10", "Linux {name} 5.15.0-105-generic #115-Ubuntu SMP x86_64"),
}


ROUTER_DESCR = ("Cisco IOS Software [Dublin], c8000be Software (X86_64_LINUX_IOSD-UNIVERSALK9-M), "
                "Version {version}, RELEASE SOFTWARE (fc2)\r\nTechnical Support: http://www.cisco.com/techsupport")


def _fmt(template: str, d: LabDevice) -> str:
    return template.format(version=d.version or "", model=d.model or "", model_text=d.model_text or d.model or "",
                           name=d.name)


def build_snmp(lab: Lab) -> None:
    for d in lab.devices:
        if not d.runs_snmp:
            continue
        object_id, descr = PROFILES[d.kind]
        if d.kind == "cisco_ios" and re.match(r"(C8\d{3}|ISR|ASR)", d.model or ""):
            object_id, descr = "1.3.6.1.4.1.9.1.2846", ROUTER_DESCR
        d.set(mibs.SYS["descr"], "str", _fmt(descr, d))
        d.set(mibs.SYS["object_id"], "oid", object_id)
        d.set(mibs.SYS["uptime"], "ticks", 153201230 + sum(oid(d.ip)) * 1000)
        d.set(mibs.SYS["contact"], "str", "noc@lab.example")
        d.set(mibs.SYS["name"], "str", d.name)
        d.set(mibs.SYS["location"], "str", d.location or "")

        if d.kind in ("cisco_ios", "aruba_switch", "huawei_switch"):      # ENTITY-MIB chassis entries
            base = 1000
            for i, serial in enumerate(d.serials):
                idx = base * (i + 1)
                e = mibs.ENT
                d.set(f"{e}.2.{idx}", "str", d.model_text or d.model)
                d.set(f"{e}.5.{idx}", "int", mibs.ENT_CLASS_CHASSIS)
                d.set(f"{e}.7.{idx}", "str", f"Switch {i + 1}")
                d.set(f"{e}.10.{idx}", "str", ("Version " if d.kind == "huawei_switch" else "") + (d.version or ""))
                d.set(f"{e}.11.{idx}", "str", serial)
                d.set(f"{e}.13.{idx}", "str", d.model)
            d.set(f"{mibs.ENT}.2.{base + 1}", "str", "Power Supply A")    # a PSU with its own serial (ignored)
            d.set(f"{mibs.ENT}.5.{base + 1}", "int", 6)
            d.set(f"{mibs.ENT}.11.{base + 1}", "str", "PSU" + (d.serials[0] if d.serials else "0"))
        elif d.kind == "fortigate":
            d.set("1.3.6.1.4.1.12356.100.1.1.1.0", "str", d.serials[0] if d.serials else "")
            d.set("1.3.6.1.4.1.12356.101.4.1.1.0", "str", d.version or "")
        elif d.kind == "paloalto":
            d.set("1.3.6.1.4.1.25461.2.1.2.1.1.0", "str", d.version or "")
            d.set("1.3.6.1.4.1.25461.2.1.2.1.3.0", "str", d.serials[0] if d.serials else "")
            d.set("1.3.6.1.4.1.25461.2.1.2.2.1.0", "str", d.model or "")
        elif d.kind == "printer":
            d.set(mibs.PRINTER_SERIAL, "str", d.serials[0] if d.serials else "")
            d.set(mibs.HR_DEVICE_DESCR, "str", d.model or "")

    _build_neighbors(lab)
    _build_arp(lab)


def _remote_descr(d: LabDevice) -> str:
    if d.runs_snmp:
        return d.snmp[oid(mibs.SYS["descr"])][1]
    return d.model or d.kind


def _build_neighbors(lab: Lab) -> None:
    port_numbers: dict[str, dict[str, int]] = {}
    rem_index: dict[str, int] = {}
    cdp_index: dict[str, int] = {}

    def local_port(dev: LabDevice, port: str) -> int:
        ports = port_numbers.setdefault(dev.name, {})
        if port not in ports:
            digits = re.findall(r"\d+", port)
            candidate = int(digits[-1]) if digits else len(ports) + 1
            while candidate in ports.values():
                candidate += 100
            ports[port] = candidate
        return ports[port]

    def add(local: LabDevice, lport: str, remote: LabDevice, rport: str, proto: str) -> None:
        if local.kind not in NEIGHBOR_TABLE_KINDS:
            return
        num = local_port(local, lport)
        if proto in ("lldp", "both"):
            rem_index[local.name] = rem_index.get(local.name, 0) + 1
            idx = f"0.{num}.{rem_index[local.name]}"
            local.set(f"{mibs.LLDP_LOC_PORT}.3.{num}", "str", lport)
            local.set(f"{mibs.LLDP_LOC_PORT}.4.{num}", "str", lport)
            local.set(f"{mibs.LLDP_REM}.4.{idx}", "int", 4)
            local.set(f"{mibs.LLDP_REM}.5.{idx}", "bytes", bytes.fromhex(remote.mac().replace(":", "")))
            local.set(f"{mibs.LLDP_REM}.7.{idx}", "str", rport)
            local.set(f"{mibs.LLDP_REM}.8.{idx}", "str", rport)
            local.set(f"{mibs.LLDP_REM}.9.{idx}", "str", remote.name)
            local.set(f"{mibs.LLDP_REM}.10.{idx}", "str", _remote_descr(remote))
            local.set(f"{mibs.LLDP_MAN_ADDR}.{idx}.1.4.{remote.ip}", "int", 2)
        if proto in ("cdp", "both") and local.kind in CDP_KINDS:
            cdp_index[local.name] = cdp_index.get(local.name, 0) + 1
            idx = f"{num}.{cdp_index[local.name]}"
            platform = f"cisco {remote.model}" if remote.kind == "cisco_ios" else (remote.model or remote.kind)
            local.set(f"{mibs.IF_NAME}.{num}", "str", lport)
            local.set(f"{mibs.CDP_CACHE}.3.{idx}", "int", 1)
            local.set(f"{mibs.CDP_CACHE}.4.{idx}", "bytes", bytes(int(x) for x in remote.ip.split(".")))
            local.set(f"{mibs.CDP_CACHE}.5.{idx}", "str", _remote_descr(remote))
            local.set(f"{mibs.CDP_CACHE}.6.{idx}", "str", remote.name)
            local.set(f"{mibs.CDP_CACHE}.7.{idx}", "str", rport)
            local.set(f"{mibs.CDP_CACHE}.8.{idx}", "str", platform)

    for link in lab.links:
        if len(link) != 5:
            raise LabError(f"link must be [devA, portA, devB, portB, lldp|cdp|both]: {link}")
        a, pa, b, pb, proto = link
        if proto not in ("lldp", "cdp", "both"):
            raise LabError(f"link protocol must be lldp, cdp or both: {link}")
        da, db = lab.by_name(a), lab.by_name(b)
        add(da, str(pa), db, str(pb), proto)
        add(db, str(pb), da, str(pa), proto)


def _build_arp(lab: Lab) -> None:
    if not lab.hosts:
        return
    dev = lab.by_name(lab.hosts.get("arp_device", ""))
    entries = [(ip, mac) for ip, mac in (lab.hosts.get("list") or [])]
    entries += [(d.ip, d.mac()) for d in lab.devices if d is not dev and d.ip]
    for ip, mac in entries:
        dev.set(f"{mibs.ARP_PHYS}.20.{ip}", "bytes", bytes.fromhex(mac.replace(":", "")))


# ----------------------------------------------------------------------------------------
# API data for FortiGate / Palo Alto: fixture answers with this device's identity

def fortigate_answers(d: LabDevice) -> dict[str, Any]:
    data = json.loads((FIXTURES / "fortigate.json").read_text(encoding="utf-8"))["default"]
    status = data["/api/v2/monitor/system/status"]
    status["serial"] = d.serials[0] if d.serials else ""
    status["version"] = (d.version or "").split(",")[0]
    status["results"].update({"hostname": d.name, "model_name": "FortiGate", "model": d.model})
    return data


def paloalto_answers(d: LabDevice) -> dict[str, str]:
    data = json.loads((FIXTURES / "paloalto.json").read_text(encoding="utf-8"))["default"]
    key = "<show><system><info></info></system></show>"
    text = data[key]
    for tag, value in (("hostname", d.name), ("serial", d.serials[0] if d.serials else ""),
                       ("model", d.model or ""), ("sw-version", d.version or ""), ("ip-address", d.ip)):
        text = re.sub(rf"<{tag}>[^<]*</{tag}>", f"<{tag}>{value}</{tag}>", text)
    data[key] = text
    return data


def cisco_cli_device(d: LabDevice) -> dict[str, Any]:
    cli = dict(d.cli)
    interfaces = []
    for i in cli.get("interfaces", []):
        item = {"status": "up", **i}
        interfaces.append(item)
    if not interfaces:
        interfaces = [{"name": "Vlan10", "ip": f"{d.ip}/24", "status": "up", "description": "MGMT"}]
    return {"name": d.name, "ip": d.ip, "version": d.version or "17.9.4a", "serials": d.serials or ["LAB0000"],
            "model": d.model or "C9300-48P", **{k: v for k, v in cli.items() if k != "interfaces"},
            "interfaces": interfaces}
