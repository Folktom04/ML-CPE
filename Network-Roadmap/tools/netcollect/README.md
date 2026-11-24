# netcollect — สคริปต์ Python กวาดข้อมูลอุปกรณ์เครือข่ายในครั้งเดียว

> เป้าหมาย: แทนที่การ SSH/เปิด GUI ทีละเครื่องเพื่อพิมพ์คำสั่งใน [Cheat Sheets](../../cheatsheets/README.md) ด้วยสคริปต์ที่
> **ดึงข้อมูลจากอุปกรณ์ทุกตัวพร้อมกัน (SSH + REST/XML API)** → **แปลงเป็นรูปแบบเดียวกัน** → **ตรวจหาปัญหาอัตโนมัติ** → **ออกรายงาน CSV/Excel/JSON**

```
 inventory.yaml ──► [netcollect] ──┬─ Cisco IOS/NX-OS  (SSH + Netmiko + TextFSM)
                                    ├─ FortiGate        (FortiOS REST API)
                                    ├─ Palo Alto        (PAN-OS XML API)
                                    ├─ REST API อะไรก็ได้ (NetBox, Meraki, ระบบภายใน ...)
                                    └─ Probe            (DNS / ping / TCP port จากเครื่องที่รัน)
                     ▼
     ข้อมูลรูปแบบเดียวกัน (facts, interfaces, routes, BGP/OSPF, VPN, HA, SD-WAN)
                     ▼
     ตรวจกฎ (CRC, BGP ไม่ขึ้น, OSPF ค้าง, VPN ล่ม, HA ไม่ sync, CPU สูง ...)
                     ▼
     output/<เวลา>/ summary.csv · findings.csv · interfaces.csv · vpn.csv · ... · report.xlsx · devices/*.json
```

---

> 🔎 **ยังไม่มีรายชื่ออุปกรณ์?** ใช้คำสั่ง **`discover`** สแกนวง IP ผ่าน SNMP เพื่อหา **ชื่อ ยี่ห้อ รุ่น serial และ version** ของ switch/router/firewall/printer ทั้งหมด ไล่ CDP/LLDP ต่อจาก core switch และ **สร้าง `inventory.yaml` ให้อัตโนมัติ** — ดูคู่มือ **[DISCOVER.md](DISCOVER.md)**
> ```bash
> python -m netcollect discover --mock --subnet 10.0.10.0/24 --seed 10.0.10.2 --ping --arp
> ```

## 1. ลองใช้ภายใน 2 นาที (ไม่ต้องมีอุปกรณ์จริง)

```bash
cd Network-Roadmap/tools/netcollect
python3 -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m netcollect collect -i inventory.example.yaml --mock
```
`--mock` ใช้ข้อมูลตัวอย่างในโฟลเดอร์ `netcollect/fixtures/` (สมมติขึ้น) ซึ่งจงใจใส่ปัญหาไว้ให้เห็นว่าระบบตรวจเจอ:
```
Collecting from 9 device(s), 10 in parallel (MOCK data) ...
  [FAIL] fgt-branch-hdy           0.00s  TransportError: ConnectTimeout: ...
  [OK  ] core-sw-01               0.00s
  ...
Devices: 8/9 collected
Findings: 6 critical, 8 warning

severity  device          category    item                   message
critical  core-sw-02      ospf        10.255.0.3             OSPF neighbor state exstart - EXSTART/EXCHANGE usually means MTU mismatch
critical  edge-rtr-01     bgp         198.51.100.1           BGP not established (state=active, AS 65002)
critical  fgt-hq          vpn         VPN-KKC                IPsec tunnel down (selectors 0/1, peer 198.51.100.30)
warning   core-sw-02      interface   GigabitEthernet1/0/8   error counters crc=235, rx_errors=235 - check cable/SFP/duplex ...
warning   fgt-hq          vpn         VPN-AWS                tunnel up, sending but receiving 0 bytes - check the remote side
...
Reports written to: output/20261124-103000
```
เปิด `output/<เวลา>/report.xlsx` จะเห็นแต่ละหัวข้อเป็นชีต (summary, findings, interfaces, routes, neighbors, vpn, sdwan, probes) และแถว critical/warning มีสีพื้นหลัง

---

## 2. โครงสร้างโค้ด (อ่านตามลำดับนี้จะเข้าใจทั้งหมด)

| ไฟล์ | หน้าที่ | สิ่งที่ได้เรียนรู้ |
|---|---|---|
| `netcollect/inventory.py` | อ่าน YAML, รวมค่า defaults/groups, ดึง secret จาก environment variable, กรองอุปกรณ์ | YAML, dataclass, การไม่ hard-code รหัสผ่าน |
| `netcollect/model.py` | `DeviceResult` = "แบบฟอร์มกลาง" ที่ทุกยี่ห้อต้องกรอก | การออกแบบ data model |
| `netcollect/transport.py` | วิธีคุยกับอุปกรณ์: `HttpTransport` (requests + retry 429/5xx), `SshTransport` (Netmiko), `MockTransport` (ไฟล์ตัวอย่าง) | REST, retry/backoff, status code, SSH |
| `netcollect/collectors/*.py` | ตัวดึงข้อมูลแต่ละยี่ห้อ: เรียก API/คำสั่ง → แปลงเป็น `DeviceResult` | REST/XML API, TextFSM, การ parse |
| `netcollect/runner.py` | รันหลายเครื่องพร้อมกัน (ThreadPoolExecutor), เครื่องหนึ่งพังไม่กระทบเครื่องอื่น | concurrency, error handling |
| `netcollect/checks.py` | กฎตรวจสุขภาพ → findings | แปลงความรู้ network เป็นโค้ด |
| `netcollect/report.py` | เขียน JSON/CSV/Excel | csv, json, openpyxl |
| `netcollect/cli.py` | คำสั่ง `collect` / `list` / `discover`, ตัวเลือก, exit code | argparse |
| `netcollect/discovery/` | ค้นหาอุปกรณ์ผ่าน SNMP + CDP/LLDP (ดู [DISCOVER.md](DISCOVER.md)) | SNMP, asyncio |
| `tests/` | unit test 36 ข้อ (ไม่ต้องใช้ network) | pytest, การ mock |

### แนวคิดสำคัญ 3 ข้อ
1. **ทุกยี่ห้อกรอก "แบบฟอร์มเดียวกัน"** (`DeviceResult`) — ส่วนตรวจกฎและรายงานจึงเขียนครั้งเดียวใช้ได้ทุกยี่ห้อ
2. **แยก "วิธีคุย" (transport) ออกจาก "สิ่งที่ถาม" (collector)** — จึงสลับไปใช้ข้อมูล mock ได้ และเขียน test ได้โดยไม่ต้องมีอุปกรณ์
3. **ล้มเหลวแบบมีขอบเขต** — เครื่องหนึ่งติดต่อไม่ได้ → รายงานว่า FAIL แล้วทำเครื่องอื่นต่อ · หัวข้อหนึ่งของเครื่องล้ม (เช่น ไม่ได้เปิด SD-WAN) → เก็บหัวข้ออื่นต่อ แล้วบันทึกใน `section_errors`

---

## 3. เทียบคำสั่ง CLI ที่เรียนมา ↔ สิ่งที่สคริปต์เรียก

| ข้อมูล | คำสั่งที่พิมพ์เอง (cheat sheet) | netcollect เรียก |
|---|---|---|
| FortiGate: รุ่น/version/serial | `get system status` | `GET /api/v2/monitor/system/status` |
| FortiGate: CPU/memory/session | `get system performance status` | `GET /api/v2/monitor/system/resource/usage` |
| FortiGate: interface + errors | `diagnose hardware deviceinfo nic` | `GET /api/v2/monitor/system/interface` |
| FortiGate: routing table | `get router info routing-table all` | `GET /api/v2/monitor/router/ipv4` |
| FortiGate: BGP | `get router info bgp summary` | `GET /api/v2/monitor/router/bgp/neighbors` |
| FortiGate: IPsec | `get vpn ipsec tunnel summary` | `GET /api/v2/monitor/vpn/ipsec` |
| FortiGate: HA sync | `diagnose sys ha checksum cluster` | `GET /api/v2/monitor/system/ha-checksums` |
| FortiGate: SD-WAN SLA | `diagnose sys sdwan health-check status` | `GET /api/v2/monitor/virtual-wan/health-check` |
| Palo Alto: system | `show system info` | XML API `type=op` `<show><system><info>` |
| Palo Alto: interface/route/BGP/VPN/HA/session | `show interface all` / `show routing route` / ... | XML API op command เดียวกัน |
| Cisco: ทุกอย่าง | `show version`, `show ip interface brief`, `show interfaces`, `show ip route`, `show ip bgp summary`, `show ip ospf neighbor`, `show standby brief`, `show processes cpu` | ส่งคำสั่งเดียวกันผ่าน SSH แล้ว parse ด้วย TextFSM |
| ทดสอบบริการ | `nslookup`, `ping`, `Test-NetConnection -Port` | `socket.getaddrinfo`, คำสั่ง `ping`, `socket.create_connection` |

> ชื่อ field ใน API อาจต่างกันเล็กน้อยตาม version ของ FortiOS/PAN-OS — โค้ดอ่านแบบ "ยืดหยุ่น" และเก็บข้อมูลดิบไว้ได้ด้วย `--raw` เพื่อตรวจเทียบ

---

## 4. เตรียมอุปกรณ์จริง (ทำครั้งเดียว) — ใช้สิทธิ์ **อ่านอย่างเดียว** เสมอ

### FortiGate — REST API Admin
1. **System → Admin Profiles** → สร้าง profile เช่น `api-readonly` ตั้งทุกหมวดเป็น **Read** (หรือ None ในหมวดที่ไม่ใช้)
2. **System → Administrators → Create New → REST API Admin** → ใส่ชื่อ เช่น `netcollect`, เลือก profile `api-readonly`
3. **Trusted Hosts** = ใส่เฉพาะ IP ของเครื่องที่จะรันสคริปต์ (สำคัญด้านความปลอดภัย)
4. กด OK → ระบบแสดง **API token ครั้งเดียว** → เก็บใน password manager/vault
5. ทดสอบจากเครื่องที่รันสคริปต์:
```bash
export FGT_HQ_TOKEN='...'      # อย่าพิมพ์ token ลงไฟล์ที่ commit
curl -s --cacert corp-ca.pem -H "Authorization: Bearer $FGT_HQ_TOKEN" \
     https://10.0.10.254/api/v2/monitor/system/status | python3 -m json.tool
```
ถ้าได้ `401` = token ผิด · `403` = trusted host/สิทธิ์ไม่พอ · timeout = HTTPS admin ไม่ได้เปิดบน interface นั้นหรือ firewall กั้น

### Palo Alto — API Key
1. สร้าง admin role แบบ read-only (Device → Admin Roles: เปิด XML API เฉพาะ **Operational Requests**) และสร้าง admin user ที่ใช้ role นี้
2. ขอ API key (ส่งรหัสผ่านแบบ POST เพื่อไม่ให้อยู่ใน URL/log):
```bash
curl -s --cacert corp-ca.pem -X POST https://10.0.10.21/api/ \
     --data-urlencode type=keygen --data-urlencode user=netcollect --data-urlencode "password=$PA_PASS"
# ได้ <key>LUFRPT1...</key> → เก็บเป็น env var PA_DMZ_KEY
```

### Cisco — บัญชี SSH แบบดูอย่างเดียว
ใช้บัญชีใน TACACS+/RADIUS ที่ให้สิทธิ์เฉพาะคำสั่ง `show` (หรือ privilege level ที่จำกัด) และเก็บ log ทุกคำสั่ง
```bash
export NET_USER=netcollect
read -s NET_PASS && export NET_PASS        # พิมพ์รหัสโดยไม่แสดงบนจอ/ไม่เข้า history
```

### TLS (HTTPS)
- ค่าเริ่มต้น `verify_tls: true` (ตรวจ certificate)
- ถ้าอุปกรณ์ใช้ cert จาก CA ภายใน → `verify_tls: /path/to/corp-ca.pem`
- `verify_tls: false` ใช้ **เฉพาะ lab** — ปิดแล้วเสี่ยงถูกดักข้อมูล (และ token) ระหว่างทาง

---

## 5. เขียน inventory ของคุณ

คัดลอก `inventory.example.yaml` เป็น `inventory.yaml` แล้วแก้ (ไฟล์ `inventory.yaml` และโฟลเดอร์ `output/` ถูกใส่ใน `.gitignore` แล้ว)
```yaml
defaults:
  verify_tls: /etc/ssl/certs/corp-ca.pem
groups:
  cisco: {username_env: NET_USER, password_env: NET_PASS}
devices:
  - {name: core-sw-01, platform: cisco_ios, group: cisco, host: 10.0.10.2, tags: {site: BKK}}
  - {name: fgt-hq, platform: fortigate, host: 10.0.10.254, token_env: FGT_HQ_TOKEN, tags: {site: BKK}}
  - {name: pa-dmz-01, platform: paloalto, host: 10.0.10.21, token_env: PA_DMZ_KEY}
  - name: erp-check
    platform: probe
    host: erp.corp.local
    options: {dns: true, ping: true, tcp_ports: [443]}
```
| ช่อง | ความหมาย |
|---|---|
| `platform` | `cisco_ios`, `cisco_nxos`, `fortigate`, `paloalto`, `rest`, `probe` |
| `*_env` | **ชื่อ** environment variable ที่เก็บ username/password/token (ไม่ใช่ค่าจริง) |
| `port` | port ของ SSH/HTTPS ถ้าไม่ใช่ค่าปกติ |
| `vdom` | FortiGate ที่เปิด VDOM |
| `tags` | ใช้กรองตอนรัน เช่น `--tag site=BKK` |
| `options.commands` | (Cisco) เปลี่ยนคำสั่งของแต่ละหัวข้อ |
| `options.endpoints` | (rest) รายการ API ที่จะเรียก |

---

## 6. คำสั่งที่ใช้บ่อย

```bash
python -m netcollect list    -i inventory.yaml                         # ดูว่าจะรันกับเครื่องไหน
python -m netcollect collect -i inventory.yaml                         # ทุกเครื่อง
python -m netcollect collect -i inventory.yaml --tag site=CNX          # เฉพาะสาขาเชียงใหม่
python -m netcollect collect -i inventory.yaml --platform fortigate    # เฉพาะ FortiGate
python -m netcollect collect -i inventory.yaml --device fgt-hq --raw   # เครื่องเดียว + เก็บข้อมูลดิบ
python -m netcollect collect -i inventory.yaml -w 20                   # 20 เครื่องพร้อมกัน
python -m netcollect collect -i inventory.yaml --thresholds thresholds.example.yaml
```
**Exit code** (ใช้ต่อกับ cron/CI/ระบบแจ้งเตือน): `0` ปกติ · `1` มี finding ระดับ critical · `2` บางเครื่องเก็บข้อมูลไม่ได้ · `3` inventory/ตัวเลือกผิด

> ⚠️ `-w` (จำนวนพร้อมกัน) อย่าตั้งสูงเกิน — การ login พร้อมกันจำนวนมากอาจทำให้ TACACS/RADIUS หรือ CPU ฝั่ง management ของอุปกรณ์รับไม่ไหว เริ่มที่ 10

---

## 7. อ่านผลลัพธ์

| ไฟล์ | ใช้ทำอะไร |
|---|---|
| `summary.csv` | หนึ่งแถวต่อเครื่อง: รุ่น, serial, version, CPU/mem, จำนวน interface up/down, BGP, VPN, HA → **ใช้ทำ inventory/EoL report** |
| `findings.csv` | รายการปัญหาเรียงจาก critical → **ใช้เป็นรายการงานเช้านี้** |
| `interfaces.csv`, `routes.csv`, `neighbors.csv`, `vpn.csv`, `sdwan.csv`, `probes.csv` | ข้อมูลละเอียดรายหัวข้อ กรอง/ทำ pivot ใน Excel ได้ |
| `report.xlsx` | ทุกตารางรวมในไฟล์เดียว |
| `devices/<name>.json` | ข้อมูลเต็มของเครื่อง (ใช้ต่อในสคริปต์อื่น/เทียบย้อนหลัง) |

### กฎตรวจที่มีให้ (ดู `netcollect/checks.py`)
| กฎ | ระดับ | ที่มา (ความรู้จาก cheat sheet) |
|---|---|---|
| เก็บข้อมูลไม่ได้ | critical | ติดต่อไม่ได้/token ผิด/SSH ไม่ได้ |
| BGP ไม่ established | critical | `Active`/`Idle` = ยังไม่เชื่อมต่อ |
| OSPF ไม่ใช่ FULL/2WAY | critical | EXSTART/EXCHANGE = MTU ไม่ตรงกัน |
| IPsec ไม่ up | critical | selectors x/y |
| VPN up แต่รับ 0 byte | warning | ฝั่งตรงข้ามไม่ตอบ/route กลับ |
| HA config ไม่ sync | critical | checksum ไม่ตรง |
| SD-WAN member ไม่ up / loss / latency / jitter เกินเกณฑ์ | critical/warning | health-check |
| interface ที่ up แต่มี CRC/errors | warning | สาย/SFP/duplex |
| half duplex | warning | duplex mismatch |
| CPU/memory เกินเกณฑ์ | warning | conserve mode (FortiGate) |
| probe DNS/ping/TCP ล้มเหลว | critical | `refused` vs `timeout` |

---

## 8. ต่อยอด: เพิ่มข้อมูลที่ต้องการเอง

### 8.1 เพิ่ม API อะไรก็ได้ — ไม่ต้องเขียนโค้ด (platform `rest`)
```yaml
- name: meraki
  platform: rest
  host: api.meraki.com
  token_env: MERAKI_API_KEY
  options:
    auth_header: Authorization
    auth_prefix: "Bearer "
    endpoints:
      - name: orgs
        path: /api/v1/organizations
        fields: [id, name]
      - name: devices
        path: /api/v1/organizations/123456/devices/statuses
        fields: [name, serial, status, lanIp, publicIp]
```
- `items` = ตำแหน่งของ list ใน JSON (เช่น `results`) · `fields` = เลือก field (ใช้จุดเข้าไปข้างในได้ เช่น `site.name`)
- ผลอยู่ใน `devices/<name>.json` หัวข้อ `extra`

### 8.2 เพิ่มหัวข้อใหม่ให้ FortiGate (เขียนโค้ด 3 จุด)
ตัวอย่าง: เก็บรายชื่อผู้ใช้ SSL VPN ที่เชื่อมต่ออยู่
```python
# netcollect/collectors/fortigate.py
EP["sslvpn"] = "/api/v2/monitor/vpn/ssl"                       # 1) endpoint

def _sslvpn(self, t, result):                                  # 2) ฟังก์ชันแปลงข้อมูล
    users = _results(self._get(t, "sslvpn", result)) or []
    result.extra["sslvpn_users"] = [{"user": u.get("user_name"), "ip": u.get("remote_host")} for u in users]

# ใน collect_into(): 
self.section(result, "sslvpn", self._sslvpn, t, result)        # 3) เรียกใช้
```
ชื่อ field (`user_name`, `remote_host`) ให้ตรวจกับข้อมูลจริงของ version ที่ใช้ด้วย `--raw` ก่อนเสมอ แล้วเพิ่มตัวอย่างคำตอบใน `fixtures/fortigate.json` + เขียน test → รัน `pytest` (ดู API ที่มีทั้งหมดได้จาก **FortiOS REST API reference** ใน Fortinet Developer Network)

### 8.3 เพิ่มกฎตรวจใหม่
```python
# netcollect/checks.py ภายใน evaluate()
users = result.extra.get("sslvpn_users", [])
if len(users) > th.get("sslvpn_users_max", 300):          # เกณฑ์ใหม่ ตั้งใน thresholds.yaml ได้
    add("warning", "sslvpn", "users", f"{len(users)} SSL VPN users connected (license/capacity?)")
```

### 8.4 เพิ่มยี่ห้อใหม่ (เช่น MikroTik, Aruba, Juniper)
1. สร้าง `netcollect/collectors/<vendor>.py` สืบทอด `Collector` → เขียน `open_transport()` และ `collect_into()`
2. ลงทะเบียนใน `collectors/__init__.py` (`REGISTRY`) และ `SUPPORTED_PLATFORMS` ใน `inventory.py`
3. ใส่ fixture + test

---

## 9. รันอัตโนมัติทุกวัน

### Linux (cron) — ทุกวันทำการ 07:30
```bash
# crontab -e
30 7 * * 1-5  cd /opt/netcollect && . .venv/bin/activate && . ./secrets.env && \
  python -m netcollect collect -i inventory.yaml -o /data/netcollect >> /var/log/netcollect.log 2>&1
```
`secrets.env` (สิทธิ์ `chmod 600`, เจ้าของเป็นบัญชีบริการ) เก็บ `export FGT_HQ_TOKEN=...` — ดีกว่านั้นคือดึงจาก vault (HashiCorp Vault, Azure Key Vault ฯลฯ)

### Windows (Task Scheduler)
สร้าง Task เรียก `C:\netcollect\.venv\Scripts\python.exe -m netcollect collect -i C:\netcollect\inventory.yaml -o D:\reports` และตั้ง environment variable ให้บัญชีที่รัน task

### ต่อยอดการแจ้งเตือน
ใช้ exit code (`1` = critical) หรืออ่าน `findings.csv` แล้วส่งเข้า Teams/LINE/email · หรือส่ง JSON เข้า SIEM/Grafana (Level 86)

---

## 10. ความปลอดภัย (สำคัญ)

- **อ่านอย่างเดียว:** บัญชีและ token ทั้งหมดต้องเป็น read-only — สคริปต์นี้ไม่มีคำสั่งแก้ไข config
- **ไม่เก็บ secret ในไฟล์/โค้ด/Git** — ใช้ environment variable หรือ vault
- **จำกัดที่มา:** trusted hosts (FortiGate), ACL ของ management, รันจาก jump host/server ที่ควบคุมได้
- **ตรวจ TLS** — ไม่ปิด `verify_tls` ใน production
- **ผลลัพธ์มีข้อมูลอ่อนไหว** (IP, routing, serial) — เก็บในที่ที่จำกัดสิทธิ์ ระวังการแชร์ไฟล์
- ใช้กับอุปกรณ์ที่ได้รับอนุญาตให้ดูแลเท่านั้น และแจ้งทีมที่เกี่ยวข้องก่อนตั้งเวลาให้รันอัตโนมัติ

---

## 11. แก้ปัญหาการใช้งานสคริปต์

| อาการ | สาเหตุ / วิธีแก้ |
|---|---|
| `inventory error: ... environment variable X is not set` | ยังไม่ได้ `export X=...` ใน shell ที่รัน |
| FortiGate `401 Unauthorized` | token ผิด/ถูก regenerate แล้ว |
| FortiGate `403 Forbidden` | IP เครื่องที่รันไม่อยู่ใน trusted hosts / profile ไม่มีสิทธิ์ |
| `SSLError ... certificate verify failed` | ใส่ไฟล์ CA ใน `verify_tls` (หรือ cert ของอุปกรณ์หมดอายุ/ชื่อไม่ตรง) |
| `ConnectTimeout` | ไม่มี route/firewall กั้น/HTTPS admin ไม่ได้เปิดบน interface นั้น/port ผิด |
| Cisco `could not parse 'show version'` | ยังไม่ได้ติดตั้ง `ntc-templates` หรือ platform ไม่ตรง (ios vs nxos) |
| Cisco หัวข้อใดว่าง | template ของคำสั่งนั้นไม่มี/ชื่อ field ต่าง → รันด้วย `--raw` แล้วดูข้อมูลดิบ, ปรับใน `collectors/cisco.py` |
| `partial data: sdwan: HTTP 404` | ฟีเจอร์นั้นไม่ได้เปิด/version ไม่มี endpoint นี้ (ไม่ใช่ข้อผิดพลาดร้ายแรง) |
| ดูรายละเอียดเพิ่ม | เพิ่ม `-v` |

---

## 12. รัน test

```bash
pip install pytest
python -m pytest -q
```
test ทั้งหมดใช้ข้อมูลตัวอย่างและ stub ไม่ต้องต่อ network — ควรรันทุกครั้งที่แก้โค้ด

---

## 13. แบบฝึกหัด (ไล่จากง่ายไปยาก)

1. รัน `--mock` แล้วอธิบายทุก finding ว่าเกิดจากอะไร (เทียบกับ [คู่มืออธิบายคำสั่ง](../../cheatsheets/explained/README.md))
2. แก้ `fixtures/fortigate.json` ให้ VPN-KKC เป็น `up` แล้วรันใหม่ — finding หายไหม
3. เพิ่มเครื่อง `probe` ไปยังเว็บภายในองค์กรของคุณ (DNS + TCP 443) แล้วรันจริง
4. เขียน `thresholds.yaml` ให้ CPU เตือนที่ 60% แล้วรัน `--mock`
5. เพิ่ม endpoint `rest` เรียก API ที่คุณมีสิทธิ์ใช้ (เช่น NetBox ใน lab — Level 89)
6. เพิ่มหัวข้อ SSL VPN users ให้ FortiGate ตามข้อ 8.2 พร้อม fixture และ test
7. เขียน collector ใหม่สำหรับอุปกรณ์อีกยี่ห้อหนึ่งใน lab ของคุณ
8. ตั้ง cron ให้รันทุกเช้า และส่ง findings ระดับ critical เข้าแชตของทีม

---

⬅️ [Cheat Sheets](../../cheatsheets/README.md) · [บทเรียน Level 81 Python](../../lessons/L81-python-for-network.md) · [Level 83 APIs](../../lessons/L83-network-apis.md)
