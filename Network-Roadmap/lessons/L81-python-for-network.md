# บทเรียน Level 81 — Python for Network Engineers (ฉบับละเอียด)

> อ่านจบแล้วจะ: ตั้ง environment Python ได้ถูกวิธี (venv) · ใช้ data type ที่จำเป็นกับงาน network · อ่าน/เขียน YAML/JSON/CSV · ใช้ Netmiko, NAPALM, Scrapli, Nornir · แปลง output เป็นข้อมูลด้วย TextFSM/TTP/Genie · ใช้ library `ipaddress` · จัดการ credential ปลอดภัย · ทำงานพร้อมกันหลายร้อยอุปกรณ์ · เขียนสคริปต์ที่ปลอดภัยต่อการรันในระบบจริง

---

## 1. ทำไม Network Engineer ต้องเขียน Python

| งานแบบเดิม (มือ) | ด้วย Python |
|---|---|
| SSH ทีละเครื่อง 200 switch เพื่อ backup | สคริปต์รันคืนละครั้ง 2 นาที |
| หาว่า MAC นี้อยู่พอร์ตไหน | ค้นทุก switch อัตโนมัติ |
| ตรวจว่าทุกเครื่องมี NTP/syslog ถูกต้อง | compliance report ทุกวัน |
| เปลี่ยน VLAN 50 สวิตช์ | bulk change + dry-run + rollback |
| ทำ inventory (model/serial/version) | Excel อัตโนมัติ |
**ไม่ได้มาแทนความรู้ network** — มาช่วยให้ความรู้นั้นทำงานได้ในขนาดใหญ่ แม่นยำ และทำซ้ำได้

---

## 2. ตั้ง Environment

```bash
python3 --version                       # ใช้ 3.10+ 
mkdir netauto && cd netauto
python3 -m venv .venv                   # virtual environment แยก library ต่อโปรเจค
source .venv/bin/activate               # Windows: .venv\Scripts\activate
pip install netmiko napalm nornir nornir-netmiko nornir-utils ntc-templates ttp pyyaml rich openpyxl
pip freeze > requirements.txt           # บันทึก version ไว้ติดตั้งซ้ำ
```
- **ไม่ติดตั้ง library ลง Python ของระบบ** (อาจทำ OS พัง) — ใช้ venv ทุกครั้ง (หรือ `uv`/`pipx`)
- Editor: VS Code + Python extension, ใช้ Git ตั้งแต่วันแรก (Level 84)
- **Lab:** Cisco DevNet Sandbox (ฟรี), containerlab (Arista cEOS, Nokia SR Linux, FRR), EVE-NG/GNS3/CML — **ห้ามทดลองบนอุปกรณ์ production**

---

## 3. Python ที่จำเป็นสำหรับงาน Network

### Data types หลัก
```python
hostname = "SW-ACC-01"                       # str
vlan = 10                                    # int
is_up = True                                 # bool
vlans = [10, 20, 30]                         # list (มีลำดับ)
device = {"host": "10.0.0.1", "type": "cisco_ios", "site": "BKK"}   # dict (key → value) ⭐
unique_macs = {"aa:bb", "cc:dd"}             # set (ไม่ซ้ำ)

# f-string
print(f"{hostname} VLANs: {', '.join(str(v) for v in vlans)}")
```
### Loop / condition / function / error handling
```python
def classify(util_pct: float) -> str:
    if util_pct >= 90:
        return "CRITICAL"
    elif util_pct >= 70:
        return "WARNING"
    return "OK"

interfaces = [{"name": "Gi0/1", "util": 95.2}, {"name": "Gi0/2", "util": 12.0}]
for intf in interfaces:
    print(intf["name"], classify(intf["util"]))

try:
    result = 10 / 0
except ZeroDivisionError as e:
    print("error:", e)
```
### String ที่ใช้บ่อยกับ CLI output
```python
line = "GigabitEthernet0/1   10.1.1.1   YES manual up   up"
parts = line.split()                 # ['GigabitEthernet0/1', '10.1.1.1', ...]
"up" in line ; line.startswith("Gig") ; line.strip() ; line.lower()
import re
m = re.search(r"Version (\S+),", "Cisco IOS Software, Version 17.9.4a, RELEASE")
print(m.group(1))                    # 17.9.4a
```

### Library `ipaddress` — ใช้ทุกวัน
```python
import ipaddress as ip
net = ip.ip_network("10.10.0.0/22")
print(net.num_addresses, net.netmask, net.broadcast_address)   # 1024 255.255.252.0 10.10.3.255
for sub in net.subnets(new_prefix=24):
    print(sub)                                                 # 10.10.0.0/24 ... 10.10.3.0/24
ip.ip_address("10.10.2.7") in net                              # True
ip.ip_network("10.10.1.0/24").overlaps(ip.ip_network("10.10.0.0/22"))  # True — ตรวจ IP ชน
list(ip.collapse_addresses([ip.ip_network("10.0.0.0/24"), ip.ip_network("10.0.1.0/24")]))  # [10.0.0.0/23]
```

---

## 4. ข้อมูลโครงสร้าง: YAML, JSON, CSV

```yaml
# inventory.yaml
devices:
  - {name: SW-ACC-01, host: 10.0.10.11, platform: cisco_ios, site: BKK}
  - {name: SW-ACC-02, host: 10.0.10.12, platform: cisco_ios, site: BKK}
```
```python
import yaml, json, csv
with open("inventory.yaml") as f:
    inv = yaml.safe_load(f)                      # ใช้ safe_load เสมอ
for d in inv["devices"]:
    print(d["name"], d["host"])
json.dumps(inv, indent=2)                         # แปลงเป็น JSON (ใช้กับ API — Level 83)
with open("report.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["name", "host"])
    w.writeheader()
    w.writerows({"name": d["name"], "host": d["host"]} for d in inv["devices"])
```

---

## 5. Credential — ห้าม Hard-code

```python
import os, getpass
user = os.environ.get("NET_USER") or input("Username: ")
password = os.environ.get("NET_PASS") or getpass.getpass("Password: ")
```
| วิธี | เหมาะกับ |
|---|---|
| ถามตอนรัน (`getpass`) | สคริปต์ที่คนรันเอง |
| Environment variable | CI/ตั้งเวลา (ระวังเก็บใน shell history) |
| **Secret manager** (HashiCorp Vault, Azure Key Vault, AWS Secrets Manager, CyberArk) ⭐ | production |
| `.env` + `python-dotenv` | dev เท่านั้น — **ใส่ `.env` ใน `.gitignore`** |
- ใช้ **บัญชี automation แยก** (ใน TACACS+/RADIUS) สิทธิ์ตามจำเป็น บันทึก log ทุกคำสั่ง (Level 56/68)

---

## 6. Netmiko — SSH CLI หลายยี่ห้อ

```python
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

dev = {"device_type": "cisco_ios", "host": "10.0.10.11",
       "username": user, "password": password, "timeout": 20}
try:
    with ConnectHandler(**dev) as conn:
        print(conn.find_prompt())
        out = conn.send_command("show version")                    # คำสั่ง show
        rows = conn.send_command("show ip interface brief", use_textfsm=True)  # → list of dict
        for r in rows:
            if r["status"] != "up":
                print("DOWN:", r["interface"])
        cfg = ["interface Gi1/0/10", "description Printer-2F", "switchport access vlan 20"]
        print(conn.send_config_set(cfg))                           # เข้า config mode ให้
        conn.save_config()                                         # write memory
except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
    print("connect failed:", e)
```
- `device_type`: `cisco_ios`, `cisco_nxos`, `cisco_xr`, `arista_eos`, `juniper_junos`, `fortinet`, `paloalto_panos`, `hp_procurve`, `huawei`, `mikrotik_routeros`, `linux`...
- `send_command(..., read_timeout=120)` สำหรับคำสั่งที่ช้า · `send_config_from_file()`

---

## 7. Parse Output — จาก Text เป็นข้อมูล

Output ของ CLI เป็นข้อความสำหรับคนอ่าน → ต้อง **parse** เป็นข้อมูลก่อนใช้งานต่อ
| เครื่องมือ | หลักการ |
|---|---|
| **TextFSM + ntc-templates** ⭐ | template สำเร็จรูปหลายร้อยคำสั่ง (Netmiko `use_textfsm=True`) |
| **TTP** (Template Text Parser) | เขียน template ที่หน้าตาเหมือน output — เข้าใจง่าย |
| **Genie (pyATS)** | parser ของ Cisco ครอบคลุมมาก (`use_genie=True`) |
| Regex | งานเล็กที่ไม่มี template |
| ⭐⭐ **ใช้ API ที่คืน JSON แทน** | `show ... | json` (NX-OS/EOS), NETCONF/RESTCONF (Level 83) — ไม่ต้อง parse เลย |
```python
from ttp import ttp
data = """
interface GigabitEthernet1/0/1
 description Uplink-Core
 switchport access vlan 10
"""
template = """
interface {{ interface }}
 description {{ description | ORPHRASE }}
 switchport access vlan {{ vlan }}
"""
parser = ttp(data=data, template=template); parser.parse()
print(parser.result(format="json")[0])
```

---

## 8. NAPALM — API กลางข้ามยี่ห้อ

```python
from napalm import get_network_driver
driver = get_network_driver("ios")              # eos, junos, nxos_ssh, iosxr...
with driver("10.0.10.11", user, password) as d:
    facts = d.get_facts()                        # hostname, model, serial, os_version, uptime
    print(facts["hostname"], facts["serial_number"])
    d.get_interfaces(); d.get_arp_table(); d.get_bgp_neighbors(); d.get_lldp_neighbors()
    d.load_merge_candidate(config="ntp server 10.0.0.123\n")
    diff = d.compare_config()                    # ⭐ ดู diff ก่อน
    if diff and input(f"{diff}\nCommit? [y/N] ") == "y":
        d.commit_config()
    else:
        d.discard_config()
    # d.rollback() ย้อนกลับ (ขึ้นกับ platform)
```
**Netmiko vs NAPALM:** Netmiko = "ส่งคำสั่ง CLI แล้วรับข้อความ" (ยืดหยุ่น รองรับยี่ห้อมาก) · NAPALM = **getter มาตรฐาน + config merge/replace/diff/rollback** (ข้อมูลหน้าตาเดียวกันข้ามยี่ห้อ)

**Scrapli:** SSH library ที่เร็วและรองรับ **asyncio** + NETCONF (scrapli-netconf)

---

## 9. ทำงานกับหลายร้อยอุปกรณ์: Concurrency

200 อุปกรณ์ × 10 วินาที = 33 นาที (ทีละตัว) → ทำพร้อมกัน 20 ตัว ≈ 2 นาที

### ThreadPoolExecutor (ง่ายสุด)
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

def backup(d):
    params = {"device_type": d["platform"], "host": d["host"], "username": user, "password": password}
    with ConnectHandler(**params) as c:
        cfg = c.send_command("show running-config")
    folder = Path("backups") / str(date.today()); folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{d['name']}.cfg").write_text(cfg)
    return d["name"]

with ThreadPoolExecutor(max_workers=20) as pool:
    futures = {pool.submit(backup, d): d for d in inv["devices"]}
    for fut in as_completed(futures):
        dev = futures[fut]
        try:
            print("OK  ", fut.result())
        except Exception as e:                       # เครื่องเดียวล้มไม่ทำให้ทั้งงานหยุด
            print("FAIL", dev["name"], e)
```
### Nornir — framework สำหรับ automation ด้วย Python ล้วน
```python
# config.yaml → inventory (hosts.yaml/groups.yaml หรือ NetBox plugin), runner: threaded num_workers: 20
from nornir import InitNornir
from nornir_netmiko.tasks import netmiko_send_command
from nornir_utils.plugins.functions import print_result
nr = InitNornir(config_file="config.yaml")
bkk = nr.filter(site="BKK")                      # เลือกกลุ่มอุปกรณ์
result = bkk.run(task=netmiko_send_command, command_string="show version", use_textfsm=True)
print_result(result)
print("failed:", list(result.failed_hosts))
```
- **ข้อควรระวัง:** อย่ายิงพร้อมกันมากเกินจน TACACS/AAA หรือ CPU ของอุปกรณ์รับไม่ไหว (เริ่ม 10–20 workers)

---

## 10. เขียนสคริปต์ให้ "ปลอดภัยต่อ Production"

| หลัก | ทำอย่างไร |
|---|---|
| **Dry-run ก่อนเสมอ** | `--dry-run` แสดงสิ่งที่จะทำโดยไม่ทำจริง |
| **ดู diff ก่อน commit** | NAPALM `compare_config()` |
| **ทำทีละกลุ่ม (canary)** | 1 อุปกรณ์ → 1 site → ทั้งหมด |
| **Pre/Post check** | เก็บสถานะก่อน/หลัง (interface up, neighbor) แล้วเทียบ (Level 84) |
| **Backup ก่อนแก้** | และวิธี rollback ที่ทดสอบแล้ว |
| **จัดการ error ต่ออุปกรณ์** | try/except + รายงาน fail list |
| **Log** | บันทึกว่าใครรันเมื่อไร ทำอะไรกับเครื่องไหน (`logging`) |
| **Idempotent** | รันซ้ำแล้วไม่เพิ่ม/เปลี่ยนซ้ำ (ตรวจก่อนแก้) |
| **ทำตาม change management** | สคริปต์ไม่ได้ข้าม CAB/maintenance window (Level 95) |

### ทำเป็น CLI tool
```python
import argparse
p = argparse.ArgumentParser(description="Bulk VLAN change")
p.add_argument("--site", required=True)
p.add_argument("--vlan", type=int, required=True)
p.add_argument("--dry-run", action="store_true")
args = p.parse_args()
# python vlan_change.py --site BKK --vlan 30 --dry-run
```
(หรือใช้ Typer/Click ให้สวยและมี help อัตโนมัติ)

---

## 11. ตัวอย่างงานจริง: หาว่า MAC อยู่พอร์ตไหน

```python
target = "aabb.cc00.1234"
def find_mac(d):
    with ConnectHandler(**params_of(d)) as c:
        rows = c.send_command(f"show mac address-table address {target}", use_textfsm=True)
        hits = [r for r in rows if not r["destination_port"][0].lower().startswith(("po", "te1/1/"))]
        return [(d["name"], r["vlan_id"], r["destination_port"][0]) for r in hits]   # ตัด uplink ออก
```
(field name ขึ้นกับ template — ตรวจด้วยการ print ผลก่อนใช้งาน)

---

## 12. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| ต้องเก่งโปรแกรมก่อนถึงจะเริ่ม automation ได้ | เริ่มจากสคริปต์อ่านอย่างเดียว (backup/report) แล้วค่อยขยาย |
| เก็บรหัสผ่านในสคริปต์สะดวกดี | รั่วผ่าน Git/แชร์ไฟล์ — ใช้ getpass/env/vault |
| Parse ด้วย split() ทุกครั้ง | ใช้ TextFSM/TTP/Genie หรือ API ที่คืน JSON |
| ยิงพร้อมกันยิ่งมากยิ่งดี | AAA/อุปกรณ์อาจรับไม่ไหว จำกัด workers |
| สคริปต์ทำงานได้บน lab = พร้อมใช้ production | ต้องมี dry-run, diff, canary, rollback, logging |

---

## 13. Cheat Sheet

```
venv → pip install → requirements.txt · lab: DevNet sandbox/containerlab
dict/list · f-string · re · ipaddress (subnets, overlaps, collapse) · yaml.safe_load · json · csv
Credential: getpass / env / vault · ไม่ commit .env
Netmiko: ConnectHandler · send_command(use_textfsm=True) · send_config_set · save_config
Parse: TextFSM/ntc-templates · TTP · Genie · ดีกว่า: JSON/API
NAPALM: get_facts/get_interfaces · load_merge_candidate → compare_config → commit/discard
Concurrency: ThreadPoolExecutor · Nornir (inventory + filter + run) · Scrapli async
Production-safe: dry-run · diff · canary · pre/post check · backup/rollback · logging
```

---

## 14. แบบทดสอบ 10 ข้อ

1. ทำไมต้องใช้ virtual environment
2. ใช้ library อะไรตรวจว่า subnet 2 ตัวซ้อนกันไหม เขียนตัวอย่าง
3. ทำไมห้ามเก็บรหัสผ่านในโค้ด และควรเก็บที่ไหน
4. `use_textfsm=True` ใน Netmiko ทำอะไร
5. Netmiko กับ NAPALM ต่างกันอย่างไร
6. ขั้นตอนการแก้ config อย่างปลอดภัยด้วย NAPALM
7. Backup 500 อุปกรณ์ทีละตัวช้ามาก แก้อย่างไร และต้องระวังอะไร
8. ทำไมต้อง try/except ต่ออุปกรณ์ในงานหลายเครื่อง
9. Nornir มีประโยชน์อะไรเมื่อเทียบกับเขียน loop เอง
10. ก่อนรันสคริปต์ที่เปลี่ยน config บน production ต้องมีอะไรบ้าง (4 ข้อ)

<details><summary><b>เฉลย</b></summary>

1. แยก library และ version ต่อโปรเจค ไม่ปนกับ Python ของระบบ ติดตั้งซ้ำได้ด้วย requirements.txt
2. `ipaddress`: `ip_network("10.0.1.0/24").overlaps(ip_network("10.0.0.0/22"))` → True
3. รั่วผ่าน Git/การแชร์ไฟล์ — ใช้ getpass, environment variable หรือ secret manager
4. แปลง text output เป็น list of dict ด้วย TextFSM template จาก ntc-templates
5. Netmiko ส่งคำสั่ง CLI และรับข้อความ; NAPALM ให้ getter ข้อมูลมาตรฐานข้ามยี่ห้อและ config merge/replace/diff/commit/rollback
6. load_merge_candidate (หรือ replace) → compare_config ดู diff → commit_config หรือ discard_config (และ rollback เมื่อจำเป็น)
7. ทำพร้อมกัน (ThreadPoolExecutor/Nornir/asyncio) — จำกัดจำนวน workers ไม่ให้ AAA/อุปกรณ์รับไม่ไหว
8. เครื่องที่ล้มเหลวจะไม่ทำให้ทั้งงานหยุด และได้รายงานเครื่องที่ fail
9. มี inventory, filter กลุ่มอุปกรณ์, ทำงานขนานในตัว, จัดการผลลัพธ์/failed hosts และ plugin (Netmiko/NAPALM/NetBox)
10. Dry-run/diff, backup และ rollback, ทดสอบแบบ canary, pre/post check, logging, การอนุมัติ change
</details>

---

➡️ ต่อไป: **Level 82 — Ansible for Network**
