"""Write results: one JSON per device, CSV tables, and an Excel workbook (if openpyxl is installed)."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from .checks import Finding
from .model import DeviceResult

SUMMARY_COLUMNS = ["device", "platform", "host", "ok", "error", "hostname", "model", "serial",
                   "version", "cpu_pct", "mem_pct", "sessions", "interfaces_up", "interfaces_down",
                   "bgp_established", "bgp_total", "vpn_up", "vpn_total", "ha", "duration_s"]


def summary_row(r: DeviceResult) -> dict[str, Any]:
    bgp = r.neighbors.get("bgp", [])
    ha = r.ha or {}
    ha_text = ha.get("mode", "")
    if "in_sync" in ha:
        ha_text += " in-sync" if ha["in_sync"] else " OUT-OF-SYNC"
    return {
        "device": r.device, "platform": r.platform, "host": r.host, "ok": r.ok, "error": r.error or "",
        "hostname": r.facts.get("hostname"), "model": r.facts.get("model"), "serial": r.facts.get("serial"),
        "version": r.facts.get("version"),
        "cpu_pct": r.resources.get("cpu_pct"), "mem_pct": r.resources.get("mem_pct"),
        "sessions": r.resources.get("sessions"),
        "interfaces_up": sum(1 for i in r.interfaces if i.get("status") == "up"),
        "interfaces_down": sum(1 for i in r.interfaces if i.get("status") == "down"),
        "bgp_established": sum(1 for p in bgp if p.get("state") == "established"), "bgp_total": len(bgp),
        "vpn_up": sum(1 for v in r.vpn if v.get("status") == "up"), "vpn_total": len(r.vpn),
        "ha": ha_text, "duration_s": r.duration_s,
    }


def _flatten(results: Iterable[DeviceResult], attr: str) -> list[dict[str, Any]]:
    rows = []
    for r in results:
        value = getattr(r, attr)
        if attr == "neighbors":
            for proto, items in value.items():
                rows += [{"device": r.device, "protocol": proto, **i} for i in items]
        else:
            rows += [{"device": r.device, **i} for i in value]
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    if not rows and not columns:
        return
    cols = columns or sorted({k for row in rows for k in row}, key=lambda k: (k != "device", k))
    with path.open("w", newline="", encoding="utf-8-sig") as f:   # utf-8-sig: opens correctly in Excel
        writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        writer.writerows({k: _cell(v) for k, v in row.items()} for row in rows)


def write_reports(results: list[DeviceResult], findings: list[Finding], outdir: Path,
                  include_raw: bool = False, excel: bool = True) -> dict[str, Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    files: dict[str, Path] = {}

    dev_dir = outdir / "devices"
    dev_dir.mkdir(exist_ok=True)
    for r in results:
        data = r.to_dict()
        if not include_raw:
            data.pop("raw", None)
        (dev_dir / f"{r.device}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str),
                                                  encoding="utf-8")
    files["devices"] = dev_dir

    tables = {
        "summary": [summary_row(r) for r in results],
        "findings": [f.to_dict() for f in findings],
        "interfaces": _flatten(results, "interfaces"),
        "routes": _flatten(results, "routes"),
        "neighbors": _flatten(results, "neighbors"),
        "vpn": _flatten(results, "vpn"),
        "sdwan": _flatten(results, "sdwan"),
        "probes": _flatten(results, "checks"),
    }
    for name, rows in tables.items():
        columns = SUMMARY_COLUMNS if name == "summary" else (
            ["device", "severity", "category", "item", "message"] if name == "findings" else None)
        if rows or columns:
            path = outdir / f"{name}.csv"
            _write_csv(path, rows, columns)
            files[name] = path

    if excel:
        path = _write_excel(tables, outdir / "report.xlsx")
        if path:
            files["excel"] = path
    return files


def _write_excel(tables: dict[str, list[dict[str, Any]]], path: Path) -> Path | None:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
    except ImportError:
        return None
    wb = Workbook()
    wb.remove(wb.active)
    fills = {"critical": PatternFill("solid", fgColor="F8D7DA"), "warning": PatternFill("solid", fgColor="FFF3CD")}
    for name, rows in tables.items():
        if not rows:
            continue
        ws = wb.create_sheet(name[:31])
        cols = SUMMARY_COLUMNS if name == "summary" else list(dict.fromkeys(k for row in rows for k in row))
        ws.append(cols)
        for cell in ws[1]:
            cell.font = Font(bold=True)
        for row in rows:
            ws.append([_cell(row.get(c)) for c in cols])
            if name == "findings" and row.get("severity") in fills:
                for cell in ws[ws.max_row]:
                    cell.fill = fills[row["severity"]]
        ws.freeze_panes = "A2"
        for col in ws.columns:
            width = max(len(str(c.value or "")) for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(max(10, width + 2), 60)
    wb.save(path)
    return path


def _cell(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return value
