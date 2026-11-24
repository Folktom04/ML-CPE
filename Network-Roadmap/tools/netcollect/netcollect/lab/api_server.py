"""HTTPS servers that imitate the FortiOS REST API and the PAN-OS XML API for lab devices."""
from __future__ import annotations

import json
import secrets
import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .model import Lab, LabDevice, fortigate_answers, paloalto_answers


def _handler(device: LabDevice, answers: dict[str, Any], log: list[str]):
    token = device.api_token or ""

    class Handler(BaseHTTPRequestHandler):
        server_version = "lab-api"

        def log_message(self, fmt: str, *args: Any) -> None:     # keep the console quiet, keep a log
            log.append(f"{device.name} {self.command} {self.path.split('?')[0]} -> {args[1] if len(args) > 1 else ''}")

        def _send(self, code: int, body: str, ctype: str) -> None:
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        # ---- FortiGate ----
        def _fortigate(self) -> None:
            if self.headers.get("Authorization", "") != f"Bearer {token}":
                return self._send(401, json.dumps({"http_status": 401, "status": "error"}), "application/json")
            path = urlparse(self.path).path
            answer = answers.get(path)
            if answer is None:
                return self._send(404, json.dumps({"http_status": 404, "status": "error"}), "application/json")
            self._send(200, json.dumps(answer), "application/json")

        # ---- Palo Alto ----
        def _paloalto(self, params: dict[str, list[str]]) -> None:
            kind = params.get("type", [""])[0]
            if kind == "keygen":
                user, pw = params.get("user", [""])[0], params.get("password", [""])[0]
                creds = (device.cli or {}).get("api_user", "labadmin"), (device.cli or {}).get("api_password", "lab-api-pass")
                if (user, pw) != creds:
                    return self._send(403, '<response status="error"><result><msg>Invalid credentials.</msg>'
                                           "</result></response>", "application/xml")
                return self._send(200, f'<response status="success"><result><key>{token}</key></result></response>',
                                  "application/xml")
            if self.headers.get("X-PAN-KEY", "") != token and params.get("key", [""])[0] != token:
                return self._send(403, '<response status="error" code="403"><result><msg>Invalid Credential</msg>'
                                       "</result></response>", "application/xml")
            cmd = params.get("cmd", [""])[0]
            answer = answers.get(cmd)
            if kind != "op" or answer is None:
                return self._send(200, '<response status="error" code="17"><msg><line>show -&gt; not supported '
                                       "in lab</line></msg></response>", "application/xml")
            self._send(200, answer, "application/xml")

        def do_GET(self) -> None:  # noqa: N802
            if device.kind == "fortigate":
                return self._fortigate()
            self._paloalto(parse_qs(urlparse(self.path).query))

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0") or 0)
            body = self.rfile.read(length).decode("utf-8") if length else ""
            if device.kind == "paloalto":
                params = parse_qs(urlparse(self.path).query)
                params.update(parse_qs(body))
                return self._paloalto(params)
            self._send(405, json.dumps({"status": "error"}), "application/json")

    return Handler


def start_api_servers(lab: Lab, cert: Path, key: Path, log: list[str]) -> list[ThreadingHTTPServer]:
    port = int((lab.settings.get("api", {}) or {}).get("port", 8443))
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(cert, key)
    servers = []
    for device in lab.devices:
        if device.kind not in ("fortigate", "paloalto"):
            continue
        if not device.api_token:
            device.api_token = secrets.token_hex(16)
        answers = fortigate_answers(device) if device.kind == "fortigate" else paloalto_answers(device)
        httpd = ThreadingHTTPServer((device.ip, port), _handler(device, answers, log))
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
        httpd.daemon_threads = True
        threading.Thread(target=httpd.serve_forever, name=f"api-{device.name}", daemon=True).start()
        servers.append(httpd)
    return servers
