"""Base class: every collector fills the same DeviceResult."""
from __future__ import annotations

import logging
from typing import Any

from ..inventory import Device
from ..model import DeviceResult
from ..transport import MockTransport

log = logging.getLogger(__name__)


class Collector:
    def __init__(self, device: Device, mock: bool = False):
        self.device = device
        self.mock = mock

    # Subclasses implement these two -------------------------------------------------
    def open_transport(self) -> Any:  # pragma: no cover - overridden
        raise NotImplementedError

    def collect_into(self, transport: Any, result: DeviceResult) -> None:  # pragma: no cover
        raise NotImplementedError
    # ------------------------------------------------------------------------------------

    def transport(self) -> Any:
        if self.mock:
            return MockTransport(self.device.platform, self.device.name)
        return self.open_transport()

    def section(self, result: DeviceResult, name: str, func, *args) -> Any:
        """Run one data section; a failure is recorded but does not stop the other sections."""
        try:
            return func(*args)
        except Exception as exc:  # keep collecting other sections
            msg = f"{name}: {type(exc).__name__}: {exc}"
            log.info("%s %s", self.device.name, msg)
            result.extra.setdefault("section_errors", []).append(msg)
            return None
