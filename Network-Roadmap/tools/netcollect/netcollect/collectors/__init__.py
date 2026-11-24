from __future__ import annotations

from .base import Collector
from .cisco import CiscoCollector
from .fortigate import FortiGateCollector
from .paloalto import PaloAltoCollector
from .probe import ProbeCollector
from .rest import RestCollector

REGISTRY: dict[str, type[Collector]] = {
    "cisco_ios": CiscoCollector,
    "cisco_nxos": CiscoCollector,
    "fortigate": FortiGateCollector,
    "paloalto": PaloAltoCollector,
    "rest": RestCollector,
    "probe": ProbeCollector,
}

__all__ = ["REGISTRY", "Collector"]
