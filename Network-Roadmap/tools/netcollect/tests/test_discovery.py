from __future__ import annotations

import asyncio
import csv
import json

import pytest
import yaml

from netcollect import cli
from netcollect.discovery import DiscoveryConfig, DiscoveryError, SnmpCredentials, run_discovery
from netcollect.discovery import mibs
from netcollect.discovery.engine import Discoverer, expand_targets, in_scope, parse_neighbor_table
from netcollect.discovery.output import build_inventory, assign_names
from netcollect.discovery.snmp import MockSnmpClient, PysnmpClient, SnmpError


def discover(**kw):
    cfg = DiscoveryConfig(subnets=kw.pop("subnets", ["10.0.10.0/24"]), **kw)
    return run_discovery(cfg, SnmpCredentials(), mock=True)


def by_name(result, sys_name):
    return next(d for d in result.devices if (d.get("sys_name") or "").startswith(sys_name))


# ---------------- helpers ----------------

def test_expand_targets_exclude_and_limits():
    cfg = DiscoveryConfig(subnets=["10.0.0.0/30", "10.0.0.1/32"], exclude=["10.0.0.2"])
    assert expand_targets(cfg) == ["10.0.0.1"]
    with pytest.raises(DiscoveryError, match="allow-large"):
        expand_targets(DiscoveryConfig(subnets=["10.0.0.0/20"]))
    assert len(expand_targets(DiscoveryConfig(subnets=["10.0.0.0/20"], allow_large=True))) == 4094
    with pytest.raises(DiscoveryError):
        expand_targets(DiscoveryConfig(subnets=["10.0.0.300/24"]))


def test_scope_defaults_to_private_only():
    cfg = DiscoveryConfig()
    assert in_scope("10.1.2.3", cfg) and in_scope("192.168.1.1", cfg)
    assert not in_scope("8.8.8.8", cfg) and not in_scope(None, cfg) and not in_scope("abc", cfg)
    cfg = DiscoveryConfig(scope=["10.0.10.0/24"], exclude=["10.0.10.5"])
    assert in_scope("10.0.10.9", cfg) and not in_scope("10.0.11.9", cfg) and not in_scope("10.0.10.5", cfg)


def test_mib_helpers():
    assert mibs.enterprise("1.3.6.1.4.1.12356.101.1.1004") == 12356
    assert mibs.enterprise(None) is None
    assert mibs.mac(bytes.fromhex("00090faabb01")) == "00:09:0f:aa:bb:01"
    assert mibs.mac("D4-81-D7-AA-BB-CC") == "d4:81:d7:aa:bb:cc"
    assert mibs.text(b"core-sw\x00") == "core-sw"
    assert mibs.text(bytes([1, 2, 3])) == "01:02:03"
    assert mibs.text("สวิตช์ชั้น 2".encode()) == "สวิตช์ชั้น 2"
    assert mibs.ipv4_from_bytes(bytes([10, 0, 10, 3])) == "10.0.10.3"
    assert mibs.parse_version("Cisco IOS Software, Version 17.9.4a, RELEASE") == "17.9.4a"
    assert mibs.parse_version("Juniper Networks, Inc. ex2300 ... JUNOS 21.4R3-S4 built") == "21.4R3-S4"
    assert mibs.parse_version("Aruba JL322A 2930M, revision WC.16.10.0012, ROM") == "WC.16.10.0012"
    assert mibs.clean_version("Version 5.170 V200R021") == "5.170 V200R021"
    assert mibs.clean_version("v7.2.8,build1639") == "v7.2.8"
    assert mibs.uptime_text(8640000 + 366000) == "1d 01:01"
    assert mibs.guess_platform("Cisco", "Cisco NX-OS(tm) n9000", None) == "cisco_nxos"
    assert mibs.guess_platform("Fortinet", "FortiSwitch-148F", None) is None
    assert mibs.guess_type("Cisco IP Phone 8841") == "phone"
    assert mibs.refine_vendor("HP", "Aruba JL322A") == "HPE Aruba"


def test_parse_local_neighbor_tables():
    linux = "10.0.10.1 dev eth0 lladdr 00:11:22:33:44:55 REACHABLE\n10.0.10.9 dev eth0 FAILED\n"
    windows = "  10.0.10.20          a4-bb-6d-11-22-33     dynamic\n"
    mac_os = "? (10.0.10.30) at 0:11:22:33:44:5 on en0 ifscope [ethernet]\n"
    rows = parse_neighbor_table(linux + windows + mac_os)
    assert rows[0] == {"ip": "10.0.10.1", "mac": "00:11:22:33:44:55"}
    assert rows[1] == {"ip": "10.0.10.20", "mac": "a4:bb:6d:11:22:33"}
    assert rows[2]["ip"] == "10.0.10.30"
    assert len(rows) == 3


# ---------------- discovery on the mock network ----------------

def test_sweep_identifies_vendors_models_serials():
    r = discover()
    core = by_name(r, "CORE-SW-01")
    assert core["vendor"] == "Cisco" and core["model"] == "C9300-48P" and core["version"] == "17.9.4a"
    assert core["serials"] == ["FOC2412X0AB", "FOC2412X0AC"]          # stack: chassis serials only (not PSU)
    assert core["other_ips"] == ["10.0.10.252"] and core["platform"] == "cisco_ios"
    fgt = by_name(r, "FGT-HQ")
    assert (fgt["serial"], fgt["version"], fgt["model"], fgt["platform"]) == \
        ("FG100FTK20012345", "v7.2.8", "FortiGate-100F", "fortigate")
    pa = by_name(r, "PA-DMZ-01")
    assert (pa["serial"], pa["model"], pa["version"]) == ("013201001234", "PA-3410", "11.1.4")
    aruba = by_name(r, "ACC-SW-2F")
    assert aruba["vendor"] == "HPE Aruba" and aruba["serial"] == "SG03KW1234" and aruba["platform"] is None
    printer = by_name(r, "PRN-ACC-2F")
    assert printer["serial"] == "VNB3K12345" and printer["type"] == "printer"
    assert printer["model"] == "HP LaserJet Pro M404dn"
    assert r.errors == [{"ip": "10.0.10.70", "stage": "snmp",
                         "error": "10.0.10.70: unknownUserName (SNMPv3 user not configured on device)"}]
    assert r.neighbors == []                                              # no seed -> no crawl
    assert not any(d["sys_name"] == "ACC-SW-3F" for d in r.devices)        # other subnet, not reached


def test_crawl_from_seed_finds_devices_beyond_the_subnet():
    r = discover(seeds=["10.0.10.2"], max_hops=3)
    hw = by_name(r, "ACC-SW-3F")
    assert hw["found_by"] == "cdp/lldp hop 1" and hw["serial"] == "102345678901" and hw["vendor"] == "Huawei"
    names = {d["sys_name"] for d in r.devices}
    assert {"SEP001122334455", "AP-2F-01"} <= names                        # neighbour-only devices
    phone = by_name(r, "SEP001122334455")
    assert phone["snmp"] is False and phone["type"] == "phone" and phone["ip"] == "10.0.30.55"
    links = {(n["local_device"], n["local_port"], n["remote_name"]) for n in r.neighbors}
    assert ("CORE-SW-01.corp.example", "GigabitEthernet1/0/47", "ACC-SW-2F") in links
    assert ("CORE-SW-01.corp.example", "Gi1/0/10", "SEP001122334455") in links
    # the core answers on two IPs but its neighbours are read only once
    assert sum(1 for n in r.neighbors if n["local_device"].startswith("CORE-SW-01")) == 5


def test_crawl_respects_hops_and_scope():
    r = discover(seeds=["10.0.10.2"], max_hops=0)
    hw = by_name(r, "ACC-SW-3F")                  # seen in LLDP, but not followed -> no SNMP data
    assert r.neighbors and hw["snmp"] is False and hw["serial"] is None
    r = discover(seeds=["10.0.10.2"], max_hops=3, scope=["10.0.10.0/24"])
    assert by_name(r, "ACC-SW-3F")["snmp"] is False   # 10.0.11.13 is outside --scope: never queried


def test_hosts_from_ping_and_arp():
    r = discover(subnets=["10.0.10.0/24"], seeds=["10.0.10.2"], ping=True, arp=True)
    hosts = {h["ip"]: h for h in r.hosts}
    assert hosts["10.0.10.100"]["mac"] == "d4:81:d7:aa:bb:cc" and hosts["10.0.10.100"]["snmp_device"] is None
    assert "arp@CORE-SW-01" in hosts["10.0.20.55"]["source"]
    assert hosts["10.0.10.2"]["snmp_device"].startswith("CORE-SW-01")
    assert list(hosts) == sorted(hosts, key=lambda ip: tuple(int(x) for x in ip.split(".")))


def test_inventory_generation_is_usable_by_collect(tmp_path):
    from netcollect.inventory import load_inventory
    r = discover(seeds=["10.0.10.2"])
    assign_names(r.devices)
    text = build_inventory(r.devices, ["10.0.10.0/24"])
    path = tmp_path / "inv.yaml"
    path.write_text(text, encoding="utf-8")
    devices = {d.name: d for d in load_inventory(path, mock=True)}
    assert set(devices) == {"core-sw-01", "core-sw-02", "pa-dmz-01", "fgt-hq"}
    assert devices["fgt-hq"].platform == "fortigate" and devices["core-sw-01"].host == "10.0.10.2"
    raw = yaml.safe_load(text)
    assert next(d for d in raw["devices"] if d["name"] == "fgt-hq")["token_env"] == "FGT_HQ_TOKEN"
    assert "acc-sw-3f" in text and "102345678901" in text     # unsupported devices listed as comments


def test_assign_names_unique():
    devs = [{"sys_name": "SW.corp"}, {"sys_name": "sw"}, {"ip": "10.0.0.9"}]
    assign_names(devs)
    assert [d["name"] for d in devs] == ["sw", "sw-2", "10-0-0-9"]


# ---------------- CLI ----------------

def test_cli_discover_mock_end_to_end(tmp_path, capsys):
    inv = tmp_path / "inventory.yaml"
    code = cli.main(["discover", "--mock", "--subnet", "10.0.10.0/24", "--seed", "10.0.10.2", "--ping", "--arp",
                     "-o", str(tmp_path / "out"), "--inventory-out", str(inv)])
    assert code == cli.EXIT_OK
    run_dir = next((tmp_path / "out").iterdir())
    for name in ["devices.csv", "neighbors.csv", "hosts.csv", "errors.csv", "discovery.xlsx", "discovery.json"]:
        assert (run_dir / name).exists(), name
    with (run_dir / "devices.csv").open(encoding="utf-8-sig") as f:
        rows = {r["name"]: r for r in csv.DictReader(f)}
    assert rows["core-sw-01"]["serials"] == "FOC2412X0AB, FOC2412X0AC"
    assert rows["acc-sw-3f"]["serial"] == "102345678901"
    assert inv.exists()
    # the generated inventory works with 'collect' straight away
    assert cli.main(["list", "-i", str(inv), "--mock"]) == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "MOCK network" in out and "core-sw-01" in out
    stats = json.loads((run_dir / "discovery.json").read_text(encoding="utf-8"))["stats"]
    assert stats["with_serial"] == 7


def test_cli_discover_usage_errors(monkeypatch, capsys):
    monkeypatch.delenv("SNMP_COMMUNITY", raising=False)
    assert cli.main(["discover", "--subnet", "10.0.0.0/24"]) == cli.EXIT_USAGE
    assert "SNMP_COMMUNITY" in capsys.readouterr().err
    assert cli.main(["discover", "--mock"]) == cli.EXIT_USAGE
    assert cli.main(["discover", "--mock", "--subnet", "10.0.0.0/16"]) == cli.EXIT_USAGE


def test_pysnmp_client_validates_credentials():
    with pytest.raises(SnmpError, match="community"):
        PysnmpClient(SnmpCredentials(version="2c"))
    with pytest.raises(SnmpError, match="user"):
        PysnmpClient(SnmpCredentials(version="3"))
    with pytest.raises(SnmpError, match="auth protocol"):
        PysnmpClient(SnmpCredentials(version="3", user="u", auth_key="12345678", auth_proto="XYZ"))
    c = PysnmpClient(SnmpCredentials(version="3", user="u", auth_key="12345678", priv_key="87654321",
                                     auth_proto="SHA256", priv_proto="AES256"))
    assert "authPriv" in c.creds.describe()
    c.close()


def test_snmp_errors_do_not_stop_the_sweep():
    class Flaky(MockSnmpClient):
        async def get(self, host, oids):
            if host == "10.0.10.3":
                raise RuntimeError("socket exploded")
            return await super().get(host, oids)

    cfg = DiscoveryConfig(subnets=["10.0.10.0/28"])
    result = asyncio.run(Discoverer(Flaky(), cfg, mock=True).run())
    assert any(e["ip"] == "10.0.10.3" and "socket exploded" in e["error"] for e in result.errors)
    assert any(d.get("sys_name", "").startswith("CORE-SW-01") for d in result.devices)
