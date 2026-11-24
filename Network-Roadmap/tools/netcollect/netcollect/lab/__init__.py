"""Simulated LAN for testing netcollect without real devices.

    python -m netcollect lab start               # run the lab until Ctrl+C, print commands to try
    python -m netcollect lab selftest            # start lab -> discover -> collect -> verify -> stop
    python -m netcollect lab aliases             # macOS: loopback alias commands
"""
from __future__ import annotations

import asyncio
import os
import platform
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .model import Lab, LabError, load_lab

__all__ = ["LabError", "load_lab", "RunningLab", "lab_env", "write_lab_files"]


def env_name(device_name: str, suffix: str) -> str:
    return re.sub(r"[^A-Z0-9]", "_", device_name.upper()) + suffix


def lab_env(lab: Lab) -> dict[str, str]:
    """Environment variables the lab expects (all values are lab-only test secrets)."""
    s, ssh = lab.settings.get("snmp", {}) or {}, lab.settings.get("ssh", {}) or {}
    env = {
        "SNMP_COMMUNITY": s.get("community", "lab-community"),
        "SNMP_USER": s.get("v3_user", "labuser"),
        "SNMP_AUTH_PASS": s.get("v3_auth_pass", "lab-auth-pass"),
        "SNMP_PRIV_PASS": s.get("v3_priv_pass", "lab-priv-pass"),
        "NET_USER": ssh.get("username", "labadmin"),
        "NET_PASS": ssh.get("password", "lab-ssh-pass"),
    }
    for d in lab.devices:
        if d.kind == "fortigate":
            env[env_name(d.name, "_TOKEN")] = d.api_token or ""
        elif d.kind == "paloalto":
            env[env_name(d.name, "_KEY")] = d.api_token or ""
    return env


def write_lab_files(lab: Lab, outdir: Path, ca: Path) -> dict[str, Path]:
    env = lab_env(lab)
    snmp_port = (lab.settings.get("snmp", {}) or {}).get("port", 1161)
    ssh_port = (lab.settings.get("ssh", {}) or {}).get("port", 2222)
    api_port = (lab.settings.get("api", {}) or {}).get("port", 8443)
    files = {
        "env_sh": outdir / "lab.env",
        "env_ps1": outdir / "lab.ps1",
        "defaults": outdir / "lab-inventory-defaults.yaml",
    }
    files["env_sh"].write_text("# LAB ONLY test credentials:  source lab.env\n" +
                               "".join(f"export {k}='{v}'\n" for k, v in env.items()), encoding="utf-8")
    files["env_ps1"].write_text("# LAB ONLY test credentials:  . .\\lab.ps1\n" +
                                "".join(f"$env:{k} = '{v}'\n" for k, v in env.items()), encoding="utf-8")
    defaults = {
        "defaults": {"verify_tls": str(ca.resolve()), "timeout": 15},
        "groups": {"cisco": {"port": ssh_port}, "fortigate": {"port": api_port}, "paloalto": {"port": api_port}},
    }
    files["defaults"].write_text("# ใช้กับ: discover --inventory-defaults <ไฟล์นี้> (พอร์ตและ CA ของ lab)\n" +
                                 yaml.safe_dump(defaults, sort_keys=False), encoding="utf-8")
    lab.settings["_ports"] = {"snmp": snmp_port, "ssh": ssh_port, "api": api_port}
    return files


@dataclass
class RunningLab:
    lab: Lab
    outdir: Path
    log: list[str] = field(default_factory=list)
    files: dict[str, Path] = field(default_factory=dict)
    _loop: Any = None
    _thread: threading.Thread | None = None
    _engines: list[Any] = field(default_factory=list)
    _servers: list[Any] = field(default_factory=list)
    _ssh: tuple[list[Any], threading.Event] | None = None

    def start(self) -> "RunningLab":
        from .api_server import start_api_servers
        from .certs import make_certs
        from .snmp_agent import start_snmp_agents
        from .ssh_server import start_ssh_servers

        self.outdir.mkdir(parents=True, exist_ok=True)
        ips = [d.ip for d in self.lab.devices] + [ip for d in self.lab.devices for ip in d.extra_ips]
        ca, cert, key = make_certs(self.outdir, ips)
        try:
            self._servers = start_api_servers(self.lab, cert, key, self.log)
            self._ssh = start_ssh_servers(self.lab, self.log)
            ready = threading.Event()
            errors: list[BaseException] = []

            def run_loop() -> None:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
                try:
                    self._engines = start_snmp_agents(self.lab)
                except BaseException as exc:
                    errors.append(exc)
                    ready.set()
                    return
                ready.set()
                self._loop.run_forever()

            self._thread = threading.Thread(target=run_loop, name="lab-snmp", daemon=True)
            self._thread.start()
            ready.wait(30)
            if errors:
                raise errors[0]
        except OSError as exc:
            self.stop()
            raise LabError(_bind_help(exc)) from exc
        self.files = write_lab_files(self.lab, self.outdir, ca)
        self.files["ca"] = ca
        return self

    def stop(self) -> None:
        from .snmp_agent import stop_snmp_agents

        for s in self._servers:
            s.shutdown()
            s.server_close()
        if self._ssh:
            socks, stop = self._ssh
            stop.set()
            for s in socks:
                s.close()
        if self._loop is not None and self._loop.is_running():
            loop = self._loop

            async def shutdown() -> None:
                stop_snmp_agents(self._engines)
                tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
                for t in tasks:
                    t.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

            try:
                asyncio.run_coroutine_threadsafe(shutdown(), loop).result(10)
            except Exception:
                pass
            loop.call_soon_threadsafe(loop.stop)
            if self._thread:
                self._thread.join(5)


def _bind_help(exc: OSError) -> str:
    msg = f"cannot open lab address/port: {exc}."
    if platform.system() == "Darwin":
        msg += " On macOS only 127.0.0.1 exists by default: run 'python -m netcollect lab aliases' first."
    elif "in use" in str(exc).lower():
        msg += " Another lab (or program) is already using it: stop it or change the ports in the topology."
    return msg


def alias_commands(lab: Lab) -> list[str]:
    ips = sorted({ip for d in lab.devices for ip in [d.ip, *d.extra_ips] if ip != "127.0.0.1"},
                 key=lambda x: tuple(int(p) for p in x.split(".")))
    return [f"sudo ifconfig lo0 alias {ip} up" for ip in ips]


def print_instructions(running: RunningLab) -> None:
    lab = running.lab
    ports = lab.settings["_ports"]
    out = running.outdir
    snmp_devices = [d for d in lab.devices if d.runs_snmp]
    print(f"\nLAB is running: {len(snmp_devices)} SNMP devices "
          f"({sum(1 for d in lab.devices if d.kind == 'cisco_ios')} with SSH, "
          f"{sum(1 for d in lab.devices if d.kind in ('fortigate', 'paloalto'))} with HTTPS API)\n")
    for d in lab.devices:
        services = []
        if d.runs_snmp:
            services.append(f"SNMP:{ports['snmp']}")
        if d.kind == "cisco_ios":
            services.append(f"SSH:{ports['ssh']}")
        if d.kind in ("fortigate", "paloalto"):
            services.append(f"HTTPS:{ports['api']}")
        shown = "+".join([d.ip, *d.extra_ips])
        print(f"  {d.name:<17} {d.kind:<14} {shown:<26} {', '.join(services) or '(neighbour only)'}")
    shell = "PowerShell:  . " + str(running.files["env_ps1"]) if platform.system() == "Windows" else \
        "source " + str(running.files["env_sh"])
    print(f"""
Try it in another terminal (from the netcollect folder):

  {shell}
  python -m netcollect discover --snmp-version 3 --snmp-port {ports['snmp']} \\
      --subnet 127.0.10.0/24 --seed 127.0.10.2 --scope 127.0.0.0/8 --arp \\
      --inventory-defaults {running.files['defaults']} --inventory-out {out / 'inventory.yaml'}
  python -m netcollect collect -i {out / 'inventory.yaml'}

  snmpwalk -v3 -l authPriv -u $SNMP_USER -a SHA -A $SNMP_AUTH_PASS -x AES -X $SNMP_PRIV_PASS 127.0.10.2:{ports['snmp']} 1.3.6.1.2.1.1
  ssh -p {ports['ssh']} $NET_USER@127.0.10.2            (password: $NET_PASS, then: show version)
  curl --cacert {running.files['ca']} -H "Authorization: Bearer $FGT_HQ_TOKEN" https://127.0.10.254:{ports['api']}/api/v2/monitor/system/status

Press Ctrl+C to stop the lab.""")


def run_forever(topology: str | None, outdir: Path) -> int:
    running = RunningLab(load_lab(topology), outdir).start()
    print_instructions(running)
    seen = 0
    try:
        while True:
            time.sleep(1)
            if len(running.log) > seen and os.environ.get("NETCOLLECT_LAB_VERBOSE"):
                for line in running.log[seen:]:
                    print("  [lab]", line)
            seen = len(running.log)
    except KeyboardInterrupt:
        print("\nstopping lab ...")
    finally:
        running.stop()
    return 0
