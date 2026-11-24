from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from netcollect import cli
from netcollect.checks import evaluate, evaluate_all
from netcollect.collectors import probe
from netcollect.collectors.paloalto import parse_response
from netcollect.collectors.rest import dig
from netcollect.inventory import Device, InventoryError, filter_devices, load_inventory
from netcollect.model import DeviceResult
from netcollect.runner import collect_all, collect_one
from netcollect.transport import TransportError

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "inventory.example.yaml"


def mock_devices():
    return load_inventory(EXAMPLE, mock=True)


def by_name(results, name):
    return next(r for r in results if r.device == name)


# ---------------- inventory ----------------

def test_inventory_requires_secret_env_unless_mock(monkeypatch, tmp_path):
    inv = tmp_path / "inv.yaml"
    inv.write_text("devices:\n  - {name: fw, platform: fortigate, host: 10.0.0.1, token_env: TEST_FGT_TOKEN}\n")
    monkeypatch.delenv("TEST_FGT_TOKEN", raising=False)
    with pytest.raises(InventoryError, match="TEST_FGT_TOKEN"):
        load_inventory(inv)
    monkeypatch.setenv("TEST_FGT_TOKEN", "abc")
    assert load_inventory(inv)[0].token == "abc"
    assert load_inventory(inv, mock=True)  # mock mode does not need secrets


def test_inventory_groups_defaults_and_validation(tmp_path):
    inv = tmp_path / "inv.yaml"
    inv.write_text(
        "defaults: {timeout: 7}\n"
        "groups: {fw: {platform: fortigate, timeout: 9}}\n"
        "devices:\n  - {name: a, group: fw, host: 1.1.1.1}\n  - {name: b, platform: probe, host: x}\n"
    )
    a, b = load_inventory(inv, mock=True)
    assert a.platform == "fortigate" and a.timeout == 9
    assert b.timeout == 7
    inv.write_text("devices:\n  - {name: a, platform: juniper, host: 1.1.1.1}\n")
    with pytest.raises(InventoryError, match="unsupported platform"):
        load_inventory(inv)
    inv.write_text("devices:\n  - {name: a, platform: probe, host: x}\n  - {name: a, platform: probe, host: y}\n")
    with pytest.raises(InventoryError, match="duplicate"):
        load_inventory(inv)


def test_filter_devices():
    devices = mock_devices()
    assert {d.name for d in filter_devices(devices, tag="site=CNX")} == {"fgt-branch-cnx"}
    assert all(d.platform == "fortigate" for d in filter_devices(devices, platforms=["fortigate"]))
    assert [d.name for d in filter_devices(devices, names=["pa-dmz-01"])] == ["pa-dmz-01"]
    with pytest.raises(InventoryError):
        filter_devices(devices, tag="site")


# ---------------- collectors (mock data) ----------------

def test_fortigate_normalisation():
    r = collect_one(next(d for d in mock_devices() if d.name == "fgt-hq"), mock=True)
    assert r.ok, r.error
    assert r.facts["serial"] == "FG100FTK20012345" and r.facts["version"] == "v7.2.8"
    assert r.resources == {"cpu_pct": 23.0, "mem_pct": 47.0, "sessions": 18432}
    assert {i["name"] for i in r.interfaces} == {"wan1", "wan2", "internal", "port3"}
    assert r.neighbors["bgp"][0]["state"] == "established"
    vpn = {v["name"]: v for v in r.vpn}
    assert vpn["VPN-CNX"]["status"] == "up" and vpn["VPN-KKC"]["status"] == "down"
    assert r.ha["in_sync"] is True
    assert len(r.sdwan) == 2


def test_partial_section_failure_keeps_device_ok():
    r = collect_one(next(d for d in mock_devices() if d.name == "fgt-branch-cnx"), mock=True)
    assert r.ok
    assert any("sdwan" in e for e in r.extra["section_errors"])
    assert r.resources["cpu_pct"] == 91.0


def test_unreachable_device_is_reported_not_raised():
    r = collect_one(next(d for d in mock_devices() if d.name == "fgt-branch-hdy"), mock=True)
    assert not r.ok and "ConnectTimeout" in r.error


def test_paloalto_normalisation():
    r = collect_one(next(d for d in mock_devices() if d.name == "pa-dmz-01"), mock=True)
    assert r.ok, r.error
    assert r.facts["model"] == "PA-3410" and r.facts["version"] == "11.1.4"
    assert r.resources["sessions"] == 48211
    eth3 = next(i for i in r.interfaces if i["name"] == "ethernet1/3")
    assert eth3["status"] == "down" and eth3["ip"] is None
    assert r.neighbors["bgp"][0] == {"peer": "198.51.100.9", "remote_as": "65002", "state": "active"}
    assert r.ha == {"mode": "Active-Passive", "role": "active", "peer_role": "passive", "in_sync": True}


def test_paloalto_error_response():
    with pytest.raises(TransportError, match="Invalid credentials"):
        parse_response('<response status="error"><msg><line>Invalid credentials.</line></msg></response>')


def test_cisco_normalisation():
    results = collect_all(mock_devices(), workers=4, mock=True)
    core1 = by_name(results, "core-sw-01")
    assert core1.facts == {"hostname": "CORE-SW-01", "model": "C9300-48P", "serial": "FOC2412X0AB",
                           "version": "17.09.04a", "uptime": "2 weeks, 3 days, 4 hours, 12 minutes"}
    assert core1.resources["cpu_pct"] == 10.0
    states = {i["name"]: i["status"] for i in core1.interfaces}
    assert states["GigabitEthernet1/0/3"] == "admin-down" and states["GigabitEthernet1/0/2"] == "down"
    assert core1.routes[0]["prefix"] == "0.0.0.0/0" and core1.routes[0]["nexthop"] == "10.0.0.254"
    assert core1.neighbors["ospf"][0]["state"] == "full"
    edge = by_name(results, "edge-rtr-01")
    bgp = {p["peer"]: p for p in edge.neighbors["bgp"]}
    assert bgp["203.0.113.1"]["state"] == "established" and bgp["203.0.113.1"]["prefixes"] == 1
    assert bgp["198.51.100.1"]["state"] == "active"
    assert [i["name"] for i in edge.interfaces][0] == "GigabitEthernet0/0/0"  # per-device command override


def test_textfsm_uppercase_keys_are_normalised():
    from netcollect.collectors.cisco import rows
    assert rows([{"INTERFACE": "Gi1", "STATUS": "up"}]) == [{"interface": "Gi1", "status": "up"}]
    assert rows("raw text output") == []


def test_rest_dig_and_fields():
    data = {"results": [{"name": "a", "site": {"name": "BKK"}}]}
    assert dig(data, "results.0.site.name") == "BKK"
    assert dig(data, "results.5.name") is None
    r = collect_one(next(d for d in mock_devices() if d.name == "netbox"), mock=True)
    assert r.ok
    assert r.extra["devices"][0] == {"name": "CORE-SW-01", "status.value": "active", "site.name": "BKK-HQ",
                                     "primary_ip4.address": "10.0.10.2/24"}


# ---------------- probes ----------------

@pytest.mark.parametrize("output,loss,avg", [
    ("4 packets transmitted, 4 received, 0% packet loss, time 3004ms\n"
     "rtt min/avg/max/mdev = 0.031/0.045/0.061/0.010 ms\n", 0.0, 0.045),
    ("    Packets: Sent = 4, Received = 3, Lost = 1 (25% loss),\n"
     "    Minimum = 13ms, Maximum = 15ms, Average = 14ms\n", 25.0, 14.0),
])
def test_ping_output_parsing(monkeypatch, output, loss, avg):
    class Proc:
        returncode = 0
        stdout = output
        stderr = ""
    monkeypatch.setattr(probe.subprocess, "run", lambda *a, **k: Proc())
    res = probe.ping("10.0.0.1")
    assert res["loss_pct"] == loss and res["avg_ms"] == avg and res["ok"]


def test_tcp_probe_open_and_refused():
    import socket
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    try:
        assert probe.tcp_port("127.0.0.1", port)["ok"]
    finally:
        srv.close()
    closed = probe.tcp_port("127.0.0.1", port)
    assert not closed["ok"] and "refused" in closed["detail"]


# ---------------- health checks ----------------

def test_checks_find_expected_problems():
    results = collect_all(mock_devices(), workers=4, mock=True)
    findings = evaluate_all(results)
    keys = {(f.device, f.category, f.item) for f in findings}
    assert ("core-sw-02", "ospf", "10.255.0.3") in keys
    assert ("core-sw-02", "interface", "GigabitEthernet1/0/8") in keys
    assert ("edge-rtr-01", "bgp", "198.51.100.1") in keys
    assert ("fgt-hq", "vpn", "VPN-KKC") in keys
    assert ("fgt-hq", "vpn", "VPN-AWS") in keys          # up but rx = 0
    assert ("fgt-branch-hdy", "collection", "10.4.10.1") in keys
    assert ("erp-check", "tcp", "erp.corp.example:1433") in keys
    assert findings[0].severity == "critical"           # sorted critical first
    assert not any(f.device == "core-sw-01" for f in findings)  # healthy device -> no findings


def test_thresholds_override():
    r = DeviceResult(device="x", platform="fortigate", host="h", ok=True, resources={"cpu_pct": 70})
    assert evaluate(r) == []
    assert evaluate(r, {"cpu_pct": 60})[0].category == "resources"


def test_ha_out_of_sync_and_down_interface_errors_ignored():
    r = DeviceResult(device="x", platform="fortigate", host="h", ok=True,
                     ha={"mode": "cluster", "in_sync": False},
                     interfaces=[{"name": "p1", "status": "down", "crc": 99}])
    cats = [f.category for f in evaluate(r)]
    assert cats == ["ha"]


# ---------------- CLI end to end ----------------

def test_cli_mock_end_to_end(tmp_path, capsys):
    code = cli.main(["collect", "-i", str(EXAMPLE), "--mock", "-o", str(tmp_path), "-w", "3"])
    assert code == cli.EXIT_FAILED          # one device unreachable in the sample data
    run_dir = next(tmp_path.iterdir())
    for name in ["summary.csv", "findings.csv", "interfaces.csv", "vpn.csv", "report.xlsx"]:
        assert (run_dir / name).exists(), name
    with (run_dir / "summary.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 9
    fgt = next(r for r in rows if r["device"] == "fgt-hq")
    assert fgt["vpn_up"] == "2" and fgt["vpn_total"] == "3" and fgt["ha"] == "cluster in-sync"
    device_json = json.loads((run_dir / "devices" / "pa-dmz-01.json").read_text(encoding="utf-8"))
    assert "raw" not in device_json and device_json["facts"]["serial"] == "013201001234"
    out = capsys.readouterr().out
    assert "MOCK" in out and "critical" in out


def test_cli_list_and_bad_filter(capsys):
    assert cli.main(["list", "-i", str(EXAMPLE), "--mock", "--tag", "site=BKK"]) == cli.EXIT_OK
    assert "core-sw-01" in capsys.readouterr().out
    assert cli.main(["list", "-i", str(EXAMPLE), "--mock", "--device", "nope"]) == cli.EXIT_USAGE


def test_cli_raw_option(tmp_path):
    cli.main(["collect", "-i", str(EXAMPLE), "--mock", "-o", str(tmp_path), "--device", "fgt-hq",
              "--raw", "--no-excel"])
    run_dir = next(tmp_path.iterdir())
    data = json.loads((run_dir / "devices" / "fgt-hq.json").read_text(encoding="utf-8"))
    assert "status" in data["raw"]
    assert not (run_dir / "report.xlsx").exists()


def test_device_label():
    assert Device("a", "probe", "h").label() == "a (probe h)"


# ---------------- HTTP transport (requests stubbed, no network) ----------------

class FakeResp:
    def __init__(self, status, payload=None, headers=None, text=""):
        self.status_code = status
        self._payload = payload
        self.headers = {"Content-Type": "application/json", **(headers or {})}
        self.text = text

    def json(self):
        return self._payload


def test_http_transport_retry_and_auth(monkeypatch):
    import requests
    from netcollect import transport as tr

    calls = []
    answers = [FakeResp(429, headers={"Retry-After": "0"}), FakeResp(200, {"results": {"hostname": "FGT"}})]

    def fake_get(self, url, params=None, verify=None, timeout=None):
        calls.append((url, dict(self.headers), params, verify))
        return answers.pop(0)

    monkeypatch.setattr(requests.Session, "get", fake_get)
    monkeypatch.setattr(tr.time, "sleep", lambda s: None)
    dev = Device("fw", "fortigate", "10.0.0.1", port=8443, token="TOKEN123", verify_tls="/ca.pem", vdom="root")
    from netcollect.collectors.fortigate import FortiGateCollector
    with FortiGateCollector(dev).open_transport() as t:
        assert t.get("/api/v2/monitor/system/status", params={"vdom": "root"}) == {"results": {"hostname": "FGT"}}
    assert len(calls) == 2                                   # retried after 429
    url, headers, params, verify = calls[-1]
    assert url == "https://10.0.0.1:8443/api/v2/monitor/system/status"
    assert headers["Authorization"] == "Bearer TOKEN123" and params == {"vdom": "root"} and verify == "/ca.pem"

    monkeypatch.setattr(requests.Session, "get", lambda self, *a, **k: FakeResp(401))
    with pytest.raises(TransportError, match="401"):
        tr.HttpTransport("https://x", retries=0).get("/api")
