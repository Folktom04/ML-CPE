"""Reachability probes from the machine running the script: ping, TCP port, DNS.

    - name: erp-check
      platform: probe
      host: erp.corp.local
      options:
        ping: true
        tcp_ports: [443, 1433]
        dns: true
"""
from __future__ import annotations

import platform
import re
import socket
import subprocess
import time
from typing import Any

from ..model import DeviceResult
from .base import Collector

RTT_RE = re.compile(r"(?:min/avg/max[^=]*=\s*[\d.]+/([\d.]+)/)|(?:Average = (\d+)ms)")
LOSS_RE = re.compile(r"(\d+(?:\.\d+)?)% (?:packet )?loss")


def ping(host: str, count: int = 4, timeout: int = 2) -> dict[str, Any]:
    windows = platform.system().lower() == "windows"
    cmd = ["ping", "-n" if windows else "-c", str(count)]
    cmd += ["-w", str(timeout * 1000)] if windows else ["-W", str(timeout)]
    cmd.append(host)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=count * (timeout + 1) + 5)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"test": "ping", "target": host, "ok": False, "detail": f"{type(exc).__name__}: {exc}"}
    out = proc.stdout + proc.stderr
    loss = LOSS_RE.search(out)
    rtt = RTT_RE.search(out)
    avg = None
    if rtt:
        avg = float(rtt.group(1) or rtt.group(2))
    loss_pct = float(loss.group(1)) if loss else (0.0 if proc.returncode == 0 else 100.0)
    return {"test": "ping", "target": host, "ok": proc.returncode == 0 and loss_pct < 100,
            "loss_pct": loss_pct, "avg_ms": avg}


def tcp_port(host: str, port: int, timeout: float = 3.0) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            ms = round((time.perf_counter() - start) * 1000, 1)
            return {"test": "tcp", "target": f"{host}:{port}", "ok": True, "detail": "open", "connect_ms": ms}
    except ConnectionRefusedError:
        return {"test": "tcp", "target": f"{host}:{port}", "ok": False,
                "detail": "refused (reached host, nothing listening / rejected)"}
    except (socket.timeout, TimeoutError):
        return {"test": "tcp", "target": f"{host}:{port}", "ok": False,
                "detail": "timeout (dropped by firewall or no route)"}
    except OSError as exc:
        return {"test": "tcp", "target": f"{host}:{port}", "ok": False, "detail": str(exc)}


def dns_lookup(name: str) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        infos = socket.getaddrinfo(name, None)
    except socket.gaierror as exc:
        return {"test": "dns", "target": name, "ok": False, "detail": str(exc)}
    addresses = sorted({i[4][0] for i in infos})
    return {"test": "dns", "target": name, "ok": True, "addresses": addresses,
            "lookup_ms": round((time.perf_counter() - start) * 1000, 1)}


class _LocalProbes:
    """Stands in for a transport: probes run locally, there is no session to open."""

    def __enter__(self) -> "_LocalProbes":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None


class ProbeCollector(Collector):
    def open_transport(self) -> _LocalProbes:
        return _LocalProbes()

    def collect_into(self, t: Any, result: DeviceResult) -> None:
        opts = self.device.options
        host = self.device.host
        if self.mock:
            result.checks = list(t.run("probes"))
        else:
            if opts.get("dns", False):
                result.checks.append(dns_lookup(host))
            if opts.get("ping", True):
                result.checks.append(ping(host, count=int(opts.get("ping_count", 4))))
            for port in opts.get("tcp_ports", []) or []:
                result.checks.append(tcp_port(host, int(port), float(opts.get("tcp_timeout", 3))))
        result.facts = {"hostname": host}
        if result.checks and not any(c.get("ok") for c in result.checks):
            # nothing worked: still a valid result, the health checks will flag it
            result.extra["all_probes_failed"] = True
