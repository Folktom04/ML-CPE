"""OIDs and helpers to turn raw SNMP answers into names, vendors, models, serials and versions.

Standard MIBs used (supported by almost every managed switch/router/firewall/AP/printer):
  SNMPv2-MIB  system group      sysDescr, sysObjectID, sysUpTime, sysName, sysLocation
  ENTITY-MIB  entPhysicalTable  class, model name, serial number, software revision (chassis)
  LLDP-MIB    lldpRemTable      neighbours (all vendors)
  CISCO-CDP-MIB cdpCacheTable   neighbours (Cisco and some others)
  IP-MIB      ipNetToMediaTable ARP table (IP <-> MAC of hosts behind a router/L3 switch)
  IF-MIB      ifName            interface names for CDP local ports
"""
from __future__ import annotations

import re
from typing import Any

SYS = {
    "descr": "1.3.6.1.2.1.1.1.0",
    "object_id": "1.3.6.1.2.1.1.2.0",
    "uptime": "1.3.6.1.2.1.1.3.0",
    "contact": "1.3.6.1.2.1.1.4.0",
    "name": "1.3.6.1.2.1.1.5.0",
    "location": "1.3.6.1.2.1.1.6.0",
}

ENT = "1.3.6.1.2.1.47.1.1.1.1"
ENT_COLS = {"descr": 2, "class": 5, "name": 7, "sw_rev": 10, "serial": 11, "model": 13}
ENT_CLASS_CHASSIS = 3
ENT_CLASS_STACK = 11

LLDP_REM = "1.0.8802.1.1.2.1.4.1.1"
LLDP_REM_COLS = {"chassis_id": 5, "port_id": 7, "port_desc": 8, "sys_name": 9, "sys_desc": 10, "capabilities": 12}
LLDP_MAN_ADDR = "1.0.8802.1.1.2.1.4.2.1.3"     # lldpRemManAddrIfSubtype: the address is in the index
LLDP_LOC_PORT = "1.0.8802.1.1.2.1.3.7.1"
LLDP_LOC_COLS = {"port_id": 3, "port_desc": 4}

CDP_CACHE = "1.3.6.1.4.1.9.9.23.1.2.1.1"
CDP_COLS = {"address_type": 3, "address": 4, "version": 5, "device_id": 6, "device_port": 7, "platform": 8,
            "capabilities": 9}
IF_NAME = "1.3.6.1.2.1.31.1.1.1.1"
ARP_PHYS = "1.3.6.1.2.1.4.22.1.2"

PRINTER_SERIAL = "1.3.6.1.2.1.43.5.1.1.17.1"     # Printer-MIB prtGeneralSerialNumber
HR_DEVICE_DESCR = "1.3.6.1.2.1.25.3.2.1.3.1"     # HOST-RESOURCES-MIB hrDeviceDescr.1 (printer/server model)

# IANA private enterprise number (in sysObjectID 1.3.6.1.4.1.<n>) -> vendor + extra OIDs
VENDORS: dict[int, dict[str, Any]] = {
    9: {"vendor": "Cisco", "serial": "1.3.6.1.4.1.9.3.6.3.0"},
    11: {"vendor": "HP"},
    207: {"vendor": "Allied Telesis"},
    311: {"vendor": "Microsoft"},
    674: {"vendor": "Dell"},
    890: {"vendor": "Zyxel"},
    1916: {"vendor": "Extreme"},
    1991: {"vendor": "Brocade"},
    2011: {"vendor": "Huawei"},
    2620: {"vendor": "Check Point"},
    2636: {"vendor": "Juniper"},
    3375: {"vendor": "F5"},
    4526: {"vendor": "Netgear"},
    8072: {"vendor": "Net-SNMP (Linux/Unix)"},
    11863: {"vendor": "TP-Link"},
    12356: {"vendor": "Fortinet", "serial": "1.3.6.1.4.1.12356.100.1.1.1.0",
            "version": "1.3.6.1.4.1.12356.101.4.1.1.0"},
    14823: {"vendor": "Aruba"},
    14988: {"vendor": "MikroTik"},
    25053: {"vendor": "Ruckus"},
    25461: {"vendor": "Palo Alto Networks", "version": "1.3.6.1.4.1.25461.2.1.2.1.1.0",
            "serial": "1.3.6.1.4.1.25461.2.1.2.1.3.0", "model": "1.3.6.1.4.1.25461.2.1.2.2.1.0"},
    25506: {"vendor": "H3C"},
    30065: {"vendor": "Arista"},
    41112: {"vendor": "Ubiquiti"},
}

VERSION_PATTERNS = [
    re.compile(r"JUNOS ([\w.\-]+)"),
    re.compile(r"RouterOS ([\d.]+)"),
    re.compile(r"[Vv]ersion[:\s]+([\w.()\-]+)"),
    re.compile(r"[Rr]evision\s+([\w.\-]+)"),
    re.compile(r"\bv(\d+\.\d+(?:\.\d+)*)"),
]

TYPE_RULES = [
    ("phone", re.compile(r"ip phone|^SEP[0-9A-F]{12}|phone", re.I)),
    ("access point", re.compile(r"access point|\bAIR-|\bAP\d|\bC9\d{3}AX|aironet|instant on ap|\bU6-|uap", re.I)),
    ("firewall", re.compile(r"fortigate|palo alto|firewall|\bPA-\d|asa\b|firepower|check ?point|sophos", re.I)),
    ("printer", re.compile(r"printer|laserjet|officejet|jetdirect|imagerunner|bizhub|ecosys|workcentre|^PRN", re.I)),
    ("switch", re.compile(r"switch|catalyst|\bC9[23]\d{2}|nexus|fortiswitch|procurve|aruba \d{4}|\bS\d{4}|\bEX\d{4}", re.I)),
    ("router", re.compile(r"router|\bISR|\bASR|\bC8\d{3}|routeros|\bMX\d+", re.I)),
    ("server", re.compile(r"linux|windows|vmware|esxi|ubuntu", re.I)),
]


def text(value: Any) -> str | None:
    """bytes/str -> clean text (None if empty). Non-printable bytes are shown as hex."""
    if value is None:
        return None
    if isinstance(value, bytes):
        stripped = value.rstrip(b"\x00")
        if stripped and not all(32 <= b < 127 or b in (9, 10, 13) or b >= 0x80 for b in stripped):
            return stripped.hex(":")
        value = stripped.decode("utf-8", errors="replace")
    result = str(value).strip()
    return result or None


def one_line(value: Any, limit: int = 120) -> str | None:
    t = text(value)
    if not t:
        return None
    t = " ".join(t.split())
    return t if len(t) <= limit else t[: limit - 3] + "..."


def mac(value: Any) -> str | None:
    if isinstance(value, bytes) and len(value) == 6:
        return value.hex(":")
    t = text(value)
    if not t:
        return None
    digits = re.sub(r"[^0-9a-fA-F]", "", t)
    if len(digits) == 12:
        return ":".join(digits[i:i + 2] for i in range(0, 12, 2)).lower()
    return t


def ipv4_from_bytes(value: Any) -> str | None:
    if isinstance(value, bytes) and len(value) == 4:
        return ".".join(str(b) for b in value)
    t = text(value)
    if t and re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", t):
        return t
    return None


def enterprise(object_id: str | None) -> int | None:
    m = re.match(r"^\.?1\.3\.6\.1\.4\.1\.(\d+)", object_id or "")
    return int(m.group(1)) if m else None


def parse_version(*candidates: str | None) -> str | None:
    for candidate in candidates:
        if not candidate:
            continue
        for pattern in VERSION_PATTERNS:
            m = pattern.search(candidate)
            if m:
                return m.group(1).rstrip(",")
    return None


def guess_type(*hints: str | None) -> str | None:
    """Check hints in order (model first, then description, then name)."""
    for hint in hints:
        if not hint:
            continue
        for name, pattern in TYPE_RULES:
            if pattern.search(hint):
                return name
    return None


def refine_vendor(vendor: str | None, descr: str | None) -> str | None:
    """Some vendors share an enterprise number (e.g. ArubaOS-Switch uses HP's 11)."""
    if vendor == "HP" and descr and "aruba" in descr.lower():
        return "HPE Aruba"
    return vendor


def clean_version(value: str | None) -> str | None:
    if not value:
        return None
    value = re.sub(r"^[Vv]ersion\s+", "", value.strip())
    return value.split(",")[0].strip() or None


def guess_platform(vendor: str | None, descr: str | None, model: str | None) -> str | None:
    """Platform name for the netcollect 'collect' inventory (None = not supported yet)."""
    d = f"{descr or ''} {model or ''}"
    if vendor == "Cisco":
        if "NX-OS" in d or "Nexus" in d:
            return "cisco_nxos"
        if "IOS" in d or "Catalyst" in d:
            return "cisco_ios"
    if vendor == "Fortinet" and re.search(r"fortigate|\bFG|FGT", d, re.I) and not re.search(r"fortiswitch|fortiap", d, re.I):
        return "fortigate"
    if vendor == "Palo Alto Networks":
        return "paloalto"
    return None


def uptime_text(ticks: Any) -> str | None:
    if not isinstance(ticks, int):
        return None
    seconds = ticks // 100
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    return f"{days}d {hours:02d}:{rem // 60:02d}"


def table(rows: list[tuple[str, Any]], base: str, columns: dict[str, int]) -> dict[str, dict[str, Any]]:
    """Group walked rows of a table into {index: {column_name: value}}."""
    by_col = {f"{base}.{num}.": name for name, num in columns.items()}
    out: dict[str, dict[str, Any]] = {}
    for oid, value in rows:
        for prefix, name in by_col.items():
            if oid.startswith(prefix):
                out.setdefault(oid[len(prefix):], {})[name] = value
                break
    return out
