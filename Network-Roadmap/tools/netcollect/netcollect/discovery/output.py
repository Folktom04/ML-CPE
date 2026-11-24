"""Write discovery results (CSV / Excel / JSON) and generate an inventory for 'netcollect collect'."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from ..report import _write_csv, _write_excel
from .engine import DiscoveryResult

DEVICE_COLUMNS = ["name", "ip", "other_ips", "vendor", "type", "model", "serial", "serials", "version",
                  "platform", "sys_name", "location", "uptime", "found_by", "snmp", "sys_object_id",
                  "description"]
NEIGHBOR_COLUMNS = ["protocol", "local_device", "local_ip", "local_port", "remote_name", "remote_port",
                    "remote_ip", "remote_platform", "remote_chassis_id"]
HOST_COLUMNS = ["ip", "mac", "source", "snmp_device"]
ERROR_COLUMNS = ["ip", "stage", "error"]

# Credentials the generated inventory refers to (names of environment variables, never values)
PLATFORM_DEFAULTS = {
    "cisco_ios": {"group": "cisco"},
    "cisco_nxos": {"group": "cisco"},
    "fortigate": {"token_env": "{NAME}_TOKEN"},
    "paloalto": {"token_env": "{NAME}_KEY"},
}


def device_name(dev: dict[str, Any]) -> str:
    raw = dev["sys_name"].split(".")[0] if dev.get("sys_name") else (dev.get("ip") or "device")
    name = re.sub(r"[^A-Za-z0-9_-]+", "-", raw).strip("-").lower()
    return name or "device"


def assign_names(devices: list[dict[str, Any]]) -> None:
    used: dict[str, int] = {}
    for dev in devices:
        base = device_name(dev)
        used[base] = used.get(base, 0) + 1
        dev["name"] = base if used[base] == 1 else f"{base}-{used[base]}"


def build_inventory(devices: list[dict[str, Any]], subnets: list[str]) -> str:
    supported, unsupported = [], []
    for dev in devices:
        if dev.get("platform") and dev.get("ip"):
            entry: dict[str, Any] = {"name": dev["name"], "platform": dev["platform"], "host": dev["ip"]}
            for key, value in PLATFORM_DEFAULTS.get(dev["platform"], {}).items():
                entry[key] = value.replace("{NAME}", re.sub(r"[^A-Z0-9]", "_", dev["name"].upper()))
            tags = {k: v for k, v in {"model": dev.get("model"), "serial": dev.get("serial"),
                                      "location": dev.get("location"), "discovered": "yes"}.items() if v}
            entry["tags"] = tags
            supported.append(entry)
        else:
            unsupported.append(dev)

    header = [
        "# inventory ที่สร้างอัตโนมัติจาก: python -m netcollect discover",
        f"# วันที่: {datetime.now():%Y-%m-%d %H:%M}   subnets: {', '.join(subnets) or '-'}",
        "# ตรวจทานก่อนใช้งาน: ชื่อ, IP สำหรับจัดการ, และ environment variable ของ credential",
        "# ใช้ต่อ:  python -m netcollect collect -i <ไฟล์นี้>",
        "",
    ]
    body = {
        "groups": {"cisco": {"username_env": "NET_USER", "password_env": "NET_PASS"}},
        "devices": supported,
    }
    if not supported:
        body["devices"] = [{"name": "example", "platform": "probe", "host": "127.0.0.1"}]
        header.append("# ไม่พบอุปกรณ์ที่ collect รองรับ จึงใส่ตัวอย่าง probe ไว้แทน")
    text = "\n".join(header) + yaml.safe_dump(body, allow_unicode=True, sort_keys=False)
    if unsupported:
        text += "\n# อุปกรณ์ที่พบแต่ 'collect' ยังไม่รองรับ (ข้อมูลอยู่ใน devices.csv):\n"
        for dev in unsupported:
            text += (f"#   - {dev.get('name')}  {dev.get('ip') or '-'}  {dev.get('vendor') or '?'}  "
                     f"{dev.get('model') or ''}  serial={dev.get('serial') or '-'}\n")
    return text


def write_discovery(result: DiscoveryResult, outdir: Path, subnets: list[str], excel: bool = True,
                    inventory_path: Path | None = None) -> dict[str, Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    assign_names(result.devices)
    files: dict[str, Path] = {}
    tables = {
        "devices": (result.devices, DEVICE_COLUMNS),
        "neighbors": (result.neighbors, NEIGHBOR_COLUMNS),
        "hosts": (result.hosts, HOST_COLUMNS),
        "errors": (result.errors, ERROR_COLUMNS),
    }
    for name, (rows, cols) in tables.items():
        if rows or name == "devices":
            path = outdir / f"{name}.csv"
            _write_csv(path, rows, cols)
            files[name] = path
    if excel:
        path = _write_excel({n: r for n, (r, _) in tables.items()}, outdir / "discovery.xlsx",
                            columns={n: c for n, (_, c) in tables.items()})
        if path:
            files["excel"] = path
    (outdir / "discovery.json").write_text(json.dumps({
        "stats": result.stats, "devices": result.devices, "neighbors": result.neighbors,
        "hosts": result.hosts, "errors": result.errors}, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8")
    files["json"] = outdir / "discovery.json"
    inv = inventory_path or outdir / "inventory.discovered.yaml"
    inv.parent.mkdir(parents=True, exist_ok=True)
    inv.write_text(build_inventory(result.devices, subnets), encoding="utf-8")
    files["inventory"] = inv
    return files
