"""How collectors talk to devices.

Collectors never open connections themselves; they ask a transport. That makes it
possible to swap the real network for fixture files (``--mock``) and for tests.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).parent / "fixtures"


class TransportError(RuntimeError):
    pass


class HttpTransport:
    """Small wrapper around requests with retries for 429/5xx and clear error messages."""

    def __init__(self, base_url: str, headers: dict[str, str] | None = None,
                 verify: bool | str = True, timeout: int = 20, retries: int = 2):
        import requests  # imported lazily so mock mode and tests do not need it

        self._requests = requests
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(headers or {})
        self.verify = verify
        self.timeout = timeout
        self.retries = retries
        if verify is False:
            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def __enter__(self) -> "HttpTransport":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.session.close()

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        last_error = ""
        for attempt in range(self.retries + 1):
            try:
                resp = self.session.get(url, params=params, verify=self.verify, timeout=self.timeout)
            except self._requests.RequestException as exc:  # connection refused, timeout, TLS error ...
                last_error = f"{type(exc).__name__}: {exc}"
            else:
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < self.retries:
                    wait = float(resp.headers.get("Retry-After", 2 * (attempt + 1)))
                    time.sleep(min(wait, 30))
                    continue
                if resp.status_code == 401:
                    raise TransportError(f"401 Unauthorized for {path}: check the API token")
                if resp.status_code == 403:
                    raise TransportError(f"403 Forbidden for {path}: token valid but no permission "
                                         "(API profile / trusted hosts)")
                if resp.status_code >= 400:
                    raise TransportError(f"HTTP {resp.status_code} for {path}: {resp.text[:200]}")
                content_type = resp.headers.get("Content-Type", "")
                if "json" in content_type:
                    return resp.json()
                return resp.text
            if attempt < self.retries:
                time.sleep(2 * (attempt + 1))
        raise TransportError(last_error or f"request to {url} failed")


class SshTransport:
    """Runs CLI commands with Netmiko and parses them with TextFSM (ntc-templates)."""

    def __init__(self, device_type: str, host: str, username: str | None, password: str | None,
                 port: int | None = None, timeout: int = 20):
        self.params = {
            "device_type": device_type,
            "host": host,
            "username": username,
            "password": password,
            "port": port or 22,
            "timeout": timeout,
            "conn_timeout": timeout,
        }
        self.conn = None

    def __enter__(self) -> "SshTransport":
        try:
            from netmiko import ConnectHandler
        except ImportError as exc:
            raise TransportError("netmiko is not installed: pip install netmiko ntc-templates") from exc
        try:
            self.conn = ConnectHandler(**self.params)
        except Exception as exc:  # netmiko raises several exception types
            raise TransportError(f"SSH to {self.params['host']} failed: {type(exc).__name__}: {exc}") from exc
        return self

    def __exit__(self, *exc: Any) -> None:
        if self.conn is not None:
            self.conn.disconnect()

    def run(self, command: str, parse: bool = True) -> Any:
        """Return parsed rows (list of dict) when a TextFSM template exists, else raw text."""
        assert self.conn is not None
        output = self.conn.send_command(command, use_textfsm=parse, read_timeout=self.params["timeout"] * 3)
        return output


class MockTransport:
    """Answers from JSON fixture files so the tool can be tried without real devices."""

    def __init__(self, platform: str, device_name: str):
        fixture = {"cisco_nxos": "cisco_ios"}.get(platform, platform)   # NX-OS reuses the IOS sample
        path = FIXTURES / f"{fixture}.json"
        if not path.exists():
            raise TransportError(f"no mock fixture for platform '{platform}'")
        data = json.loads(path.read_text(encoding="utf-8"))
        # A device-specific block (e.g. "fgt-branch-cnx") can override the default answers.
        self.answers = dict(data.get("default", {}))
        self.answers.update(data.get(device_name, {}))

    def __enter__(self) -> "MockTransport":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None

    def _lookup(self, key: str) -> Any:
        if key not in self.answers:
            raise TransportError(f"mock fixture has no answer for '{key}'")
        answer = self.answers[key]
        if isinstance(answer, dict) and answer.get("__error__"):
            raise TransportError(answer["__error__"])
        return answer

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        key = path
        if params and "cmd" in params:   # Palo Alto XML API: answer by command
            key = params["cmd"]
        return self._lookup(key)

    def run(self, command: str, parse: bool = True) -> Any:
        return self._lookup(command)
