"""Load the device inventory (YAML) and resolve credentials from environment variables.

Secrets never live in the inventory file: the file only names the environment
variable that holds them (for example ``token_env: FGT_HQ_TOKEN``).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

SUPPORTED_PLATFORMS = {"cisco_ios", "cisco_nxos", "fortigate", "paloalto", "rest", "probe"}


class InventoryError(ValueError):
    pass


@dataclass
class Device:
    name: str
    platform: str
    host: str
    port: int | None = None
    username: str | None = None
    password: str | None = None
    token: str | None = None
    verify_tls: bool | str = True
    timeout: int = 20
    vdom: str | None = None
    tags: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)   # platform specific settings

    def label(self) -> str:
        return f"{self.name} ({self.platform} {self.host})"


def _env(var: str | None, required: bool, device: str, what: str, mock: bool) -> str | None:
    if not var:
        return None
    value = os.environ.get(var)
    if value is None and required and not mock:
        raise InventoryError(f"{device}: environment variable {var} ({what}) is not set")
    return value


def _merge(defaults: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    merged = dict(defaults)
    merged.update(item)
    return merged


def load_inventory(path: str | Path, mock: bool = False) -> list[Device]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    defaults = data.get("defaults", {}) or {}
    groups = data.get("groups", {}) or {}
    items = data.get("devices", []) or []
    if not isinstance(items, list) or not items:
        raise InventoryError("inventory must contain a non-empty 'devices' list")

    devices: list[Device] = []
    seen: set[str] = set()
    for raw in items:
        group = groups.get(raw.get("group", ""), {}) or {}
        item = _merge(_merge(defaults, group), raw)
        name = item.get("name")
        platform = item.get("platform")
        host = item.get("host")
        if not name or not platform or not host:
            raise InventoryError(f"device entry needs name, platform and host: {raw}")
        if platform not in SUPPORTED_PLATFORMS:
            raise InventoryError(f"{name}: unsupported platform '{platform}' (supported: {sorted(SUPPORTED_PLATFORMS)})")
        if name in seen:
            raise InventoryError(f"duplicate device name: {name}")
        seen.add(name)

        needs_ssh = platform in {"cisco_ios", "cisco_nxos"}
        needs_token = platform in {"fortigate", "paloalto"}
        devices.append(
            Device(
                name=name,
                platform=platform,
                host=str(host),
                port=item.get("port"),
                username=_env(item.get("username_env"), needs_ssh, name, "username", mock),
                password=_env(item.get("password_env"), needs_ssh, name, "password", mock),
                token=_env(item.get("token_env"), needs_token, name, "API token", mock),
                verify_tls=item.get("verify_tls", True),
                timeout=int(item.get("timeout", 20)),
                vdom=item.get("vdom"),
                tags=item.get("tags", {}) or {},
                options=item.get("options", {}) or {},
            )
        )
    return devices


def filter_devices(devices: list[Device], names: list[str] | None = None,
                   platforms: list[str] | None = None, tag: str | None = None) -> list[Device]:
    """Select devices by name, platform or tag (``key=value``)."""
    result = devices
    if names:
        wanted = set(names)
        result = [d for d in result if d.name in wanted]
    if platforms:
        wanted_p = set(platforms)
        result = [d for d in result if d.platform in wanted_p]
    if tag:
        if "=" not in tag:
            raise InventoryError("--tag must look like key=value, e.g. site=BKK")
        key, value = tag.split("=", 1)
        result = [d for d in result if str(d.tags.get(key)) == value]
    return result
