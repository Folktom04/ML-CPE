"""Run collectors for many devices in parallel; one failing device never stops the others."""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Callable

from .collectors import REGISTRY
from .inventory import Device
from .model import DeviceResult

log = logging.getLogger(__name__)


def collect_one(device: Device, mock: bool = False) -> DeviceResult:
    result = DeviceResult(device=device.name, platform=device.platform, host=device.host,
                          collected_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    start = time.perf_counter()
    collector = REGISTRY[device.platform](device, mock=mock)
    try:
        with collector.transport() as transport:
            collector.collect_into(transport, result)
        result.ok = True
    except Exception as exc:
        result.ok = False
        result.error = f"{type(exc).__name__}: {exc}"
        log.info("%s failed: %s", device.label(), result.error)
    finally:
        result.duration_s = round(time.perf_counter() - start, 2)
    return result


def collect_all(devices: list[Device], workers: int = 10, mock: bool = False,
                progress: Callable[[DeviceResult], None] | None = None) -> list[DeviceResult]:
    """Collect from every device with up to ``workers`` at the same time.

    Keep ``workers`` modest (10-20): too many parallel logins can overload
    TACACS/RADIUS servers or the devices' management CPU.
    """
    results: list[DeviceResult] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(collect_one, d, mock): d for d in devices}
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            if progress:
                progress(res)
    order = {d.name: i for i, d in enumerate(devices)}
    return sorted(results, key=lambda r: order.get(r.device, 0))
