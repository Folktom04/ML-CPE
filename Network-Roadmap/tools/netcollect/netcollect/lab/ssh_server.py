"""SSH servers that imitate a Cisco IOS-XE CLI (enough for Netmiko 'show' commands)."""
from __future__ import annotations

import socket
import threading
from typing import Any

from .cli_outputs import run_command
from .model import Lab, cisco_cli_device


def _server_interface(username: str, password: str):
    import paramiko

    class Server(paramiko.ServerInterface):
        def check_auth_password(self, user: str, pw: str) -> int:
            ok = (user, pw) == (username, password)
            return paramiko.AUTH_SUCCESSFUL if ok else paramiko.AUTH_FAILED

        def get_allowed_auths(self, user: str) -> str:
            return "password"

        def check_channel_request(self, kind: str, chanid: int) -> int:
            return paramiko.OPEN_SUCCEEDED if kind == "session" else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

        def check_channel_pty_request(self, *args: Any) -> bool:
            return True

        def check_channel_shell_request(self, channel: Any) -> bool:
            return True

    return Server()


def _shell(chan: Any, dev: dict[str, Any], log: list[str]) -> None:
    prompt = f"{dev['name']}#"
    chan.send(f"\r\n{prompt}".encode())
    buf = ""
    skip_lf = False
    while True:
        data = chan.recv(1024)
        if not data:
            return
        for ch in data.decode("utf-8", errors="ignore"):
            if ch == "\n" and skip_lf:
                skip_lf = False
                continue
            skip_lf = ch == "\r"
            if ch in "\r\n":
                cmd = buf
                buf = ""
                if cmd.strip() in ("exit", "quit", "logout"):
                    chan.send(b"\r\n")
                    chan.close()
                    return
                out = run_command(dev, cmd)
                if cmd.strip():
                    log.append(f"{dev['name']} ssh: {cmd.strip()}")
                if out is None:
                    out = f"{' ' * (len(prompt) + 1)}^\n% Invalid input detected at '^' marker.\n"
                text = "\r\n" + (out.replace("\n", "\r\n") + "\r\n" if out else "") + prompt
                chan.send(text.encode())
            elif ch in ("\x08", "\x7f"):
                buf = buf[:-1]
            else:
                buf += ch
                chan.send(ch.encode())          # echo, like a real terminal


def _serve(sock: socket.socket, host_key: Any, dev: dict[str, Any], creds: tuple[str, str],
           log: list[str], stop: threading.Event) -> None:
    import paramiko

    while not stop.is_set():
        try:
            client, _ = sock.accept()
        except OSError:
            return

        def handle(client: socket.socket = client) -> None:
            transport = paramiko.Transport(client)
            transport.add_server_key(host_key)
            try:
                transport.start_server(server=_server_interface(*creds))
                chan = transport.accept(20)
                if chan is None:
                    return
                _shell(chan, dev, log)
            except Exception as exc:  # a broken client must not kill the lab
                log.append(f"{dev['name']} ssh error: {type(exc).__name__}: {exc}")
            finally:
                transport.close()

        threading.Thread(target=handle, daemon=True).start()


def start_ssh_servers(lab: Lab, log: list[str]) -> tuple[list[socket.socket], threading.Event]:
    import paramiko

    s = lab.settings.get("ssh", {}) or {}
    port = int(s.get("port", 2222))
    creds = (s.get("username", "labadmin"), s.get("password", "lab-ssh-pass"))
    host_key = paramiko.RSAKey.generate(2048)
    stop = threading.Event()
    sockets = []
    for device in lab.devices:
        if device.kind != "cisco_ios":
            continue
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((device.ip, port))
        sock.listen(20)
        threading.Thread(target=_serve, args=(sock, host_key, cisco_cli_device(device), creds, log, stop),
                         name=f"ssh-{device.name}", daemon=True).start()
        sockets.append(sock)
    return sockets, stop
