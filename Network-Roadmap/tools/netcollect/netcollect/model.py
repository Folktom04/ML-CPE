"""Common data model: every collector returns a DeviceResult with the same shape.

Keeping one shape for every vendor is what lets the report and the health checks
work the same way for Cisco, FortiGate, Palo Alto or a generic REST API.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DeviceResult:
    device: str
    platform: str
    host: str
    collected_at: str = ""
    ok: bool = False
    error: str | None = None
    duration_s: float = 0.0
    facts: dict[str, Any] = field(default_factory=dict)       # hostname, model, serial, version, uptime
    resources: dict[str, Any] = field(default_factory=dict)   # cpu_pct, mem_pct, sessions
    interfaces: list[dict[str, Any]] = field(default_factory=list)
    routes: list[dict[str, Any]] = field(default_factory=list)
    neighbors: dict[str, list[dict[str, Any]]] = field(default_factory=dict)  # bgp, ospf
    vpn: list[dict[str, Any]] = field(default_factory=list)
    ha: dict[str, Any] = field(default_factory=dict)
    sdwan: list[dict[str, Any]] = field(default_factory=list)
    checks: list[dict[str, Any]] = field(default_factory=list)  # reachability tests (ping/tcp/dns)
    extra: dict[str, Any] = field(default_factory=dict)        # anything vendor/endpoint specific
    raw: dict[str, Any] = field(default_factory=dict)          # raw outputs, for troubleshooting

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def to_float(value: Any) -> float | None:
    """Convert '12.5', '12.5%', 12 or None to float (None if not a number)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().rstrip("%").replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


def to_int(value: Any) -> int | None:
    number = to_float(value)
    return None if number is None else int(number)
