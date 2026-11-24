from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

from netcollect import cli
from netcollect.discovery import mibs
from netcollect.lab import LabError, alias_commands, lab_env, load_lab
from netcollect.lab.cli_outputs import COMMANDS, run_command
from netcollect.lab.model import cisco_cli_device, fortigate_answers, oid, paloalto_answers

HAVE_LAB_DEPS = all(importlib.util.find_spec(m) for m in ("pysnmp", "paramiko", "cryptography", "netmiko"))


def test_default_topology_builds_snmp_tables():
    lab = load_lab()
    core = lab.by_name("CORE-SW-01")
    assert core.snmp[oid(mibs.SYS["name"])] == ("str", "CORE-SW-01")
    serials = [v for o, (k, v) in core.snmp.items() if o[:len(oid(mibs.ENT)) + 1] == oid(mibs.ENT) + (11,)]
    assert "FOC2412X0AB" in serials and "FOC2412X0AC" in serials
    lldp_names = [v for o, (k, v) in core.snmp.items() if o[:len(oid(mibs.LLDP_REM)) + 1] == oid(mibs.LLDP_REM) + (9,)]
    assert {"ACC-SW-2F", "FGT-HQ", "AP-2F-01"} <= set(lldp_names)
    cdp_ids = [v for o, (k, v) in core.snmp.items() if o[:len(oid(mibs.CDP_CACHE)) + 1] == oid(mibs.CDP_CACHE) + (6,)]
    assert {"CORE-SW-02", "SEP001122334455", "EDGE-RTR-01"} <= set(cdp_ids)
    arp = [o for o in core.snmp if o[:len(oid(mibs.ARP_PHYS))] == oid(mibs.ARP_PHYS)]
    assert len(arp) >= 4
    assert not lab.by_name("AP-2F-01").snmp                       # neighbour-only device: no agent
    fgt = lab.by_name("FGT-HQ")
    assert fgt.snmp[oid("1.3.6.1.4.1.12356.100.1.1.1.0")] == ("str", "FG100FTK20012345")
    edge = lab.by_name("EDGE-RTR-01")
    assert "c8000be" in edge.snmp[oid(mibs.SYS["descr"])][1]       # routers get a router description


def test_topology_validation(tmp_path):
    bad = tmp_path / "t.yaml"
    bad.write_text("devices:\n  - {name: X, kind: cisco_ios, ip: 10.0.0.1}\n")
    with pytest.raises(LabError, match="127"):
        load_lab(bad)
    bad.write_text("devices:\n  - {name: X, kind: toaster, ip: 127.0.0.2}\n")
    with pytest.raises(LabError, match="unknown kind"):
        load_lab(bad)
    bad.write_text("devices:\n  - {name: X, kind: linux, ip: 127.0.0.2}\nlinks:\n  - [X, a, Y, b, lldp]\n")
    with pytest.raises(LabError, match="unknown device"):
        load_lab(bad)
    bad.write_text("devices:\n  - {name: X, kind: linux, ip: 127.0.0.2}\n  - {name: Y, kind: linux, ip: 127.0.0.2}\n")
    with pytest.raises(LabError, match="duplicate"):
        load_lab(bad)


def test_lab_env_and_aliases():
    lab = load_lab()
    env = lab_env(lab)
    assert env["FGT_HQ_TOKEN"] == "lab-fgt-hq-token" and env["PA_DMZ_01_KEY"] == "lab-pa-dmz-key"
    assert env["SNMP_USER"] == "labuser" and env["NET_USER"] == "labadmin"
    assert "sudo ifconfig lo0 alias 127.0.10.2 up" in alias_commands(lab)


def test_api_answers_use_device_identity():
    lab = load_lab()
    status = fortigate_answers(lab.by_name("FGT-HQ"))["/api/v2/monitor/system/status"]
    assert status["serial"] == "FG100FTK20012345" and status["version"] == "v7.2.8"
    pa = paloalto_answers(lab.by_name("PA-DMZ-01"))["<show><system><info></info></system></show>"]
    assert "<hostname>PA-DMZ-01</hostname>" in pa and "<serial>013201001234</serial>" in pa


def test_cli_commands_and_filters():
    dev = cisco_cli_device(load_lab().by_name("CORE-SW-02"))
    assert "Processor board ID FOC2412X0CD" in run_command(dev, "show version")
    assert run_command(dev, "terminal length 0") == ""
    assert run_command(dev, "show running-config") is None
    filtered = run_command(dev, "show ip interface brief | include Vlan")
    assert "Vlan10" in filtered and "GigabitEthernet" not in filtered


@pytest.mark.skipif(importlib.util.find_spec("ntc_templates") is None, reason="ntc-templates not installed")
def test_cli_outputs_parse_with_ntc_templates():
    from ntc_templates.parse import parse_output
    dev = cisco_cli_device(load_lab().by_name("CORE-SW-02"))
    for cmd in COMMANDS:
        if cmd in ("show processes cpu", "show ip bgp summary"):
            continue
        assert parse_output(platform="cisco_ios", command=cmd, data=COMMANDS[cmd](dev)), cmd
    edge = cisco_cli_device(load_lab().by_name("EDGE-RTR-01"))
    rows = parse_output(platform="cisco_ios", command="show ip bgp summary", data=COMMANDS["show ip bgp summary"](edge))
    assert [r["bgp_neighbor"] for r in rows] == ["203.0.113.1", "198.51.100.1"]


def test_discover_inventory_defaults_are_merged(tmp_path):
    defaults = tmp_path / "d.yaml"
    defaults.write_text("defaults: {verify_tls: /ca.pem}\ngroups: {cisco: {port: 2222}, fortigate: {port: 8443}}\n")
    inv = tmp_path / "inv.yaml"
    assert cli.main(["discover", "--mock", "--subnet", "10.0.10.0/24", "-o", str(tmp_path / "o"), "--no-excel",
                     "--inventory-out", str(inv), "--inventory-defaults", str(defaults)]) == cli.EXIT_OK
    data = yaml.safe_load(inv.read_text(encoding="utf-8"))
    assert data["defaults"]["verify_tls"] == "/ca.pem"
    assert data["groups"]["cisco"] == {"username_env": "NET_USER", "password_env": "NET_PASS", "port": 2222}
    assert data["groups"]["fortigate"] == {"port": 8443}
    fgt = next(d for d in data["devices"] if d["name"] == "fgt-hq")
    assert fgt["group"] == "fortigate"


@pytest.mark.skipif(not HAVE_LAB_DEPS, reason="lab needs pysnmp, paramiko, cryptography, netmiko")
def test_lab_selftest_end_to_end(tmp_path):
    """Starts the simulated LAN and runs real SNMP discover + SSH/HTTPS collect against it."""
    from netcollect.lab.selftest import run_selftest
    assert run_selftest(None, tmp_path / "lab") == 0
    assert (tmp_path / "lab" / "inventory.yaml").exists()
    assert (tmp_path / "lab" / "selftest-collect").exists()
