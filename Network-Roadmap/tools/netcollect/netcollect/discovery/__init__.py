"""Network discovery: find devices on subnets and read name/vendor/model/serial/version via SNMP."""
from __future__ import annotations

import asyncio
from typing import Any

from .engine import DiscoveryConfig, DiscoveryError, DiscoveryResult, Discoverer
from .snmp import MockSnmpClient, PysnmpClient, SnmpCredentials, SnmpError

__all__ = ["DiscoveryConfig", "DiscoveryError", "DiscoveryResult", "SnmpCredentials", "SnmpError",
           "run_discovery"]


def run_discovery(cfg: DiscoveryConfig, creds: SnmpCredentials, mock: bool = False,
                  client: Any = None) -> DiscoveryResult:
    async def main() -> DiscoveryResult:
        snmp = client or (MockSnmpClient(creds) if mock else PysnmpClient(creds))
        try:
            return await Discoverer(snmp, cfg, mock=mock or isinstance(snmp, MockSnmpClient)).run()
        finally:
            snmp.close()

    return asyncio.run(main())
