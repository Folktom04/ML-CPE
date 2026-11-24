"""Generic REST API collector: call any list of JSON endpoints and keep selected fields.

Use it for systems that have an API but no dedicated collector (Meraki, NetBox,
Catalyst Center, monitoring systems, an internal web app ...).

    - name: netbox
      platform: rest
      host: netbox.example.local
      token_env: NETBOX_TOKEN
      options:
        auth_header: Authorization
        auth_prefix: "Token "
        endpoints:
          - name: devices
            path: /api/dcim/devices/?limit=1000
            items: results            # where the list is inside the JSON (dot path)
            fields: [name, status.value, site.name, primary_ip4.address]
"""
from __future__ import annotations

from typing import Any

from ..model import DeviceResult
from ..transport import HttpTransport
from .base import Collector


def dig(data: Any, path: str | None) -> Any:
    """Follow a dot path like 'results.0.name' through dicts and lists."""
    if not path:
        return data
    for part in path.split("."):
        if isinstance(data, dict):
            data = data.get(part)
        elif isinstance(data, list) and part.isdigit() and int(part) < len(data):
            data = data[int(part)]
        else:
            return None
    return data


class RestCollector(Collector):
    def open_transport(self) -> HttpTransport:
        d = self.device
        opts = d.options
        headers = {"Accept": "application/json"}
        if d.token:
            headers[opts.get("auth_header", "Authorization")] = f"{opts.get('auth_prefix', 'Bearer ')}{d.token}"
        scheme = opts.get("scheme", "https")
        port = f":{d.port}" if d.port else ""
        return HttpTransport(f"{scheme}://{d.host}{port}", headers=headers, verify=d.verify_tls, timeout=d.timeout)

    def collect_into(self, t: Any, result: DeviceResult) -> None:
        endpoints = self.device.options.get("endpoints") or []
        if not endpoints:
            raise RuntimeError("rest device needs options.endpoints")
        ok = 0
        for ep in endpoints:
            got = self.section(result, ep["name"], self._endpoint, t, ep, result)
            ok += got is not None
        if ok == 0:
            raise RuntimeError("all endpoints failed: " + "; ".join(result.extra.get("section_errors", [])))
        result.facts.setdefault("hostname", self.device.host)

    def _endpoint(self, t: Any, ep: dict[str, Any], result: DeviceResult) -> bool:
        payload = t.get(ep["path"])
        result.raw[ep["name"]] = payload
        data = dig(payload, ep.get("items"))
        fields = ep.get("fields")
        if fields and isinstance(data, list):
            data = [{f: dig(item, f) for f in fields} for item in data]
        elif fields and isinstance(data, dict):
            data = {f: dig(data, f) for f in fields}
        result.extra[ep["name"]] = data
        return True
