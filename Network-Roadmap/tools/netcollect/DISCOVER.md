# netcollect discover — ค้นหาอุปกรณ์ทั้งหมดในเครือข่าย พร้อมชื่อ รุ่น และ Serial Number

> คำสั่ง `discover` ค้นหาอุปกรณ์เองโดยไม่ต้องรู้รายชื่อล่วงหน้า:
> **สแกนวง IP → ถาม SNMP ทีละเครื่อง (ชื่อ, ยี่ห้อ, รุ่น, serial, version) → ไล่ CDP/LLDP ต่อจาก core switch → ออกรายงาน Excel/CSV → สร้าง `inventory.yaml` ให้ใช้กับ `collect` ได้ทันที**

```
            ① สแกนวง IP (--subnet 10.0.10.0/24)
                 │ ถาม SNMP ทุก IP พร้อมกัน (ค่าเริ่มต้น 32 IP พร้อมกัน)
                 ▼
            ② อุปกรณ์ที่ตอบ SNMP → อ่าน system group + ENTITY-MIB (+ OID เฉพาะยี่ห้อ)
                 │ ได้: ชื่อ, ยี่ห้อ, รุ่น, serial (ทุกตัวใน stack), version, ตำแหน่ง, uptime
                 ▼
            ③ (ถ้าใส่ --seed) อ่านตาราง CDP/LLDP → เจอเพื่อนบ้านที่มี IP → ถาม SNMP ต่อ → วนจนครบ --max-hops
                 │ ได้: switch ในวงอื่น, AP, IP phone (แม้ไม่ตอบ SNMP), ผังการเชื่อมต่อ (พอร์ตต่อพอร์ต)
                 ▼
            ④ (ถ้าใส่ --ping / --arp) รายชื่อเครื่องทั้งหมด IP + MAC (PC, กล้อง, IoT ที่ไม่มี SNMP)
                 ▼
            ⑤ devices.csv · neighbors.csv · hosts.csv · errors.csv · discovery.xlsx · inventory.discovered.yaml
```

---

> 🧪 ทดสอบกับ SNMP จริงโดยไม่ต้องมีอุปกรณ์: ดู [LAN จำลอง (LAB.md)](LAB.md)

## 1. ลองเลย (ไม่ต้องมีอุปกรณ์จริง)

```bash
cd Network-Roadmap/tools/netcollect
pip install -r requirements.txt
python -m netcollect discover --mock --subnet 10.0.10.0/24 --seed 10.0.10.2 --ping --arp
```
ผลจากเครือข่ายตัวอย่าง (สมมติ):
```
Swept 254 address(es): 8 answered SNMP · devices 10 (with serial 7) · CDP/LLDP links 9 · hosts 12

name             ip           vendor              model                   serial            version        type          collect
core-sw-01       10.0.10.2    Cisco               C9300-48P               FOC2412X0AB       17.9.4a        switch        cisco_ios
core-sw-02       10.0.10.3    Cisco               C9300-48P               FOC2412X0CD       17.9.4a        switch        cisco_ios
acc-sw-2f        10.0.10.12   HPE Aruba           JL322A                  SG03KW1234        WC.16.10.0012  switch        -
pa-dmz-01        10.0.10.21   Palo Alto Networks  PA-3410                 013201001234      11.1.4         firewall      paloalto
prn-acc-2f       10.0.10.50   HP                  HP LaserJet Pro M404dn  VNB3K12345        -              printer       -
nms01            10.0.10.60   Net-SNMP (Linux)    -                       -                 -              server        -
fgt-hq           10.0.10.254  Fortinet            FortiGate-100F          FG100FTK20012345  v7.2.8         firewall      fortigate
acc-sw-3f        10.0.11.13   Huawei              S5735-L48P4X-A1         102345678901      5.170 V200...  switch        -        ← เจอจาก LLDP (คนละวง)
sep001122334455  10.0.30.55   -                   Cisco IP Phone 8841     -                 -              phone         -        ← เจอจาก CDP (ไม่มี SNMP)
ap-2f-01         10.0.50.21   -                   Aruba AP-515 ...        -                 -              access point  -        ← เจอจาก LLDP
```
สังเกต:
- **core-sw-01 เป็น stack 2 ตัว** → ช่อง `serials` ใน devices.csv มีทั้ง `FOC2412X0AB, FOC2412X0AC`
- core-sw-01 ตอบ SNMP 2 IP (10.0.10.2 และ SVI 10.0.10.252) → **รวมเป็นแถวเดียว** (`other_ips`)
- **acc-sw-3f อยู่วง 10.0.11.x ที่ไม่ได้สแกน** แต่เจอเพราะไล่ LLDP ต่อจาก acc-sw-2f
- IP phone และ AP ไม่ตอบ SNMP แต่ยังได้ **ชื่อและรุ่น** จาก CDP/LLDP ของ switch (ไม่ได้ serial)
- ช่อง `collect` = platform ที่ใช้กับคำสั่ง `collect` ต่อได้ทันที

---

## 2. Serial Number มาจากไหน (ทำไมต้องใช้ SNMP)

การสแกนเครือข่ายเฉย ๆ (ping/port scan) ได้แค่ IP และ MAC — **serial ต้องถามจากตัวอุปกรณ์** ผ่าน SNMP:

| ข้อมูล | MIB / OID ที่อ่าน | ใช้ได้กับ |
|---|---|---|
| ชื่อ, คำอธิบาย, ตำแหน่ง, uptime | SNMPv2-MIB `sysName`, `sysDescr`, `sysLocation`, `sysUpTime` | ทุกอุปกรณ์ที่เปิด SNMP |
| **ยี่ห้อ** | `sysObjectID` → หมายเลของค์กร (เช่น `.4.1.9` = Cisco, `.4.1.12356` = Fortinet) | ทุกอุปกรณ์ |
| **รุ่น + serial + version** ⭐ | ENTITY-MIB `entPhysicalModelName`, `entPhysicalSerialNum`, `entPhysicalSoftwareRev` (เลือกเฉพาะ chassis) | switch/router ส่วนใหญ่ (Cisco, Aruba, Huawei, Juniper, Arista, Dell, H3C ...) |
| serial/version สำรอง | OID เฉพาะยี่ห้อ: Fortinet `fnSysSerial` + `fgSysVersion`, Palo Alto `panSysSerialNumber` + `panSysSwVersion`, Cisco รุ่นเก่า `chassisId` | FortiGate, Palo Alto, Cisco เก่า |
| serial เครื่องพิมพ์ | Printer-MIB `prtGeneralSerialNumber` + `hrDeviceDescr` (รุ่น) | printer ส่วนใหญ่ |
| เพื่อนบ้าน | LLDP-MIB (ทุกยี่ห้อ), CISCO-CDP-MIB | switch/router/AP/phone |
| IP ↔ MAC ของเครื่องอื่น | IP-MIB `ipNetToMediaPhysAddress` (ตาราง ARP ของ router/L3 switch) | อุปกรณ์ L3 |

**ไม่ได้ serial เมื่อ:** อุปกรณ์ไม่เปิด SNMP, switch แบบ unmanaged, PC/IoT ทั่วไป (ใช้ระบบจัดการเครื่อง เช่น Intune/SCCM แทน), อุปกรณ์ที่ไม่ได้ implement ENTITY-MIB

---

## 3. เตรียมอุปกรณ์จริง: เปิด SNMP แบบอ่านอย่างเดียว

**แนะนำ SNMPv3 (authPriv)** — มีการยืนยันตัวตนและเข้ารหัส · v2c ส่ง community เป็นข้อความธรรมดา ใช้ได้แต่ต้องจำกัดด้วย ACL
**จำกัดที่มาเสมอ:** อนุญาตเฉพาะ IP ของเครื่องที่รันสคริปต์ (สมมติ `10.0.10.60`)

### Cisco IOS / IOS-XE (SNMPv3)
```
ip access-list standard SNMP-NETCOLLECT
 permit 10.0.10.60
snmp-server view NETCOLLECT-VIEW iso included
snmp-server group NETCOLLECT-RO v3 priv read NETCOLLECT-VIEW access SNMP-NETCOLLECT
snmp-server user netcollect NETCOLLECT-RO v3 auth sha <AuthPass> priv aes 128 <PrivPass>
! CDP เปิดเป็นค่าเริ่มต้น · LLDP:
lldp run
```
ตรวจ: `show snmp user` · `show snmp group`

### Cisco (SNMPv2c — ถ้าจำเป็น)
```
snmp-server community <ชื่อที่เดายาก> RO SNMP-NETCOLLECT
```

### FortiGate (SNMPv3)
```
config system snmp sysinfo
    set status enable
end
config system snmp user
    edit "netcollect"
        set queries enable
        set security-level auth-priv
        set auth-proto sha256
        set auth-pwd <AuthPass>
        set priv-proto aes
        set priv-pwd <PrivPass>
    next
end
config system interface
    edit "port3"                       ← interface ที่เครื่องสแกนเข้ามา
        append allowaccess snmp
    next
end
```
และจำกัดที่มาด้วย local-in policy หรือ trusted hosts ตามนโยบายองค์กร (รันด้วย `--v3-auth-proto SHA256`)

### ยี่ห้ออื่น (Aruba, Huawei, Juniper, Palo Alto, HPE, Dell ...)
หลักการเดียวกัน: สร้าง **SNMPv3 user แบบ read-only (auth + priv)**, view ที่อ่านได้อย่างน้อย `system`, `ENTITY-MIB`, `LLDP-MIB`, `IP-MIB`, และจำกัดที่มาเฉพาะ IP ของเครื่องที่สแกน — ดูคำสั่งในเอกสารของแต่ละยี่ห้อ
(Palo Alto: Device → Setup → Operations → SNMP Setup และต้องเปิด SNMP ใน Interface Management Profile)

> ⚠️ ทำตาม change process (Level 95) และแจ้งทีม security ก่อนสแกน — IDS/IPS อาจเห็นการสแกนเป็นการโจมตี · สแกนเฉพาะเครือข่ายที่คุณได้รับอนุญาตให้ดูแลเท่านั้น

---

## 4. รันกับเครือข่ายจริง

### เก็บ credential ใน environment variable (ไม่เขียนลงไฟล์)
```bash
# SNMPv3 (แนะนำ)
export SNMP_USER=netcollect
read -s SNMP_AUTH_PASS && export SNMP_AUTH_PASS      # พิมพ์โดยไม่แสดงบนจอ
read -s SNMP_PRIV_PASS && export SNMP_PRIV_PASS
# หรือ SNMPv2c
read -s SNMP_COMMUNITY && export SNMP_COMMUNITY
```
Windows PowerShell: `$env:SNMP_USER = "netcollect"` และ `$env:SNMP_AUTH_PASS = Read-Host` (แนะนำดึงจาก vault ในระบบจริง)

### ตัวอย่างคำสั่ง
```bash
# 1) สแกนวง management อย่างเดียว (SNMPv3)
python -m netcollect discover --snmp-version 3 --subnet 10.0.10.0/24

# 2) สแกน + ไล่ CDP/LLDP จาก core switch ไปได้ 3 ทอด
python -m netcollect discover --snmp-version 3 --subnet 10.0.10.0/24 --seed 10.0.10.2 --max-hops 3

# 3) ครบทุกอย่าง: สแกนหลายวง + ไล่ LLDP + รายชื่อเครื่องทั้งหมด (ping + ARP)
python -m netcollect discover --snmp-version 3 \
  --subnet 10.0.10.0/24 --subnet 10.0.11.0/24 --seed 10.0.10.2 --ping --arp \
  --exclude 10.0.10.200 -o reports --inventory-out inventory.yaml

# 4) SNMPv2c และ SHA256/AES256
python -m netcollect discover --subnet 10.0.10.0/24                       # v2c ใช้ SNMP_COMMUNITY
python -m netcollect discover --snmp-version 3 --v3-auth-proto SHA256 --v3-priv-proto AES256 --subnet 10.0.10.0/24

# 5) ใช้ inventory ที่สร้างได้ต่อทันที
python -m netcollect collect -i inventory.yaml
```

### ตัวเลือกทั้งหมด
| ตัวเลือก | ความหมาย |
|---|---|
| `--subnet CIDR` | วงที่จะสแกน (ใส่ได้หลายครั้ง) — เกิน 1,024 IP ต้องใส่ `--allow-large` (กันสแกนผิดวงโดยไม่ตั้งใจ) |
| `--seed IP` | อุปกรณ์เริ่มไล่ CDP/LLDP (ปกติคือ core switch) — ไม่ใส่ = ไม่ไล่ |
| `--max-hops N` | ไล่ต่อได้กี่ทอด (ค่าเริ่มต้น 3) · `0` = อ่านเพื่อนบ้านแต่ไม่ถามต่อ |
| `--scope CIDR` | วงที่การไล่ LLDP/CDP **อนุญาตให้ถาม** · ค่าเริ่มต้น: เฉพาะ IP ส่วนตัว (10/8, 172.16/12, 192.168/16) — ไม่ไปถาม IP สาธารณะของ ISP |
| `--exclude IP/CIDR` | IP ที่ห้ามแตะ (เช่น ระบบที่อ่อนไหว) |
| `--ping` | ping ทุก IP ในวง เพื่อเจอเครื่องที่ไม่มี SNMP (+ MAC จากตาราง ARP ของเครื่องที่รันสคริปต์ ถ้าอยู่วงเดียวกัน) |
| `--arp` | อ่านตาราง ARP ของ router/L3 switch ผ่าน SNMP → IP+MAC ของเครื่องทุกเครื่องที่คุยผ่าน gateway นั้น |
| `--snmp-version 2c/3` | ค่าเริ่มต้น 2c |
| `--community-env`, `--v3-user-env`, `--v3-auth-env`, `--v3-priv-env` | **ชื่อ** env var ที่เก็บ credential (ค่าเริ่มต้น `SNMP_COMMUNITY`, `SNMP_USER`, `SNMP_AUTH_PASS`, `SNMP_PRIV_PASS`) |
| `--v3-auth-proto` / `--v3-priv-proto` | MD5, SHA, SHA224, SHA256, SHA384, SHA512 / DES, AES, AES192, AES256 — ต้องตรงกับที่ตั้งบนอุปกรณ์ |
| `--timeout`, `--retries` | ค่าเริ่มต้น 2 วินาที, 1 ครั้ง (WAN ช้าให้เพิ่ม timeout) |
| `-w N` | จำนวนที่ถามพร้อมกัน (ค่าเริ่มต้น 32) |
| `-o DIR`, `--inventory-out FILE`, `--no-excel` | ตำแหน่งผลลัพธ์ |

---

## 5. ผลลัพธ์

| ไฟล์ | เนื้อหา | ใช้ทำอะไร |
|---|---|---|
| **devices.csv** | หนึ่งแถวต่ออุปกรณ์: name, ip, other_ips, vendor, type, model, **serial**, **serials** (ทุกตัวใน stack), version, platform, location, uptime, found_by, snmp | **ทะเบียนทรัพย์สิน (asset inventory)**, ตรวจ EoL/support contract (Level 94), ตรวจกับ NetBox (Level 89) |
| **neighbors.csv** | ใครต่อกับใคร: local_device, local_port → remote_name, remote_port, remote_ip, platform | **วาดผังเครือข่าย**, เอกสารพอร์ต uplink (Level 39) |
| **hosts.csv** | IP + MAC ของทุกเครื่องที่พบ (จาก ping/ARP) และบอกว่าเป็นอุปกรณ์ SNMP ตัวไหน | หาเครื่องแปลกปลอม, ตรวจ IP ที่ใช้งานจริงเทียบ IPAM |
| **errors.csv** | IP ที่ตอบ SNMP แต่ error (รหัส v3 ผิด, ไม่มี user, ไม่มีสิทธิ์) | แก้ credential ให้ครบ |
| **discovery.xlsx** | รวมทุกตารางเป็นชีต | ส่งต่อ/รายงาน |
| **discovery.json** | ข้อมูลครบสำหรับสคริปต์อื่น | ต่อยอด |
| **inventory.discovered.yaml** | inventory สำหรับ `collect` (เฉพาะอุปกรณ์ที่ collect รองรับ) + รายการที่ยังไม่รองรับเป็น comment | ใช้ต่อทันที |

### ตัวอย่าง inventory ที่สร้างให้
```yaml
groups:
  cisco: {username_env: NET_USER, password_env: NET_PASS}
devices:
- name: core-sw-01
  platform: cisco_ios
  host: 10.0.10.2
  group: cisco
  tags: {model: C9300-48P, serial: FOC2412X0AB, location: 'BKK HQ, DC room, Rack A1', discovered: 'yes'}
- name: fgt-hq
  platform: fortigate
  host: 10.0.10.254
  token_env: FGT_HQ_TOKEN            ← ตั้ง env var นี้ด้วย token ของ REST API admin
  ...
# อุปกรณ์ที่พบแต่ 'collect' ยังไม่รองรับ (ข้อมูลอยู่ใน devices.csv):
#   - acc-sw-2f  10.0.10.12  HPE Aruba  JL322A  serial=SG03KW1234
```
**ตรวจทานก่อนใช้:** ชื่ออุปกรณ์, IP ที่ใช้จัดการ (บางเครื่องตอบ SNMP หลาย IP), ชื่อ env var ของ credential

---

## 6. การทำงานภายใน (สำหรับเรียนรู้/แก้โค้ด)

| ไฟล์ | หน้าที่ |
|---|---|
| `netcollect/discovery/snmp.py` | SNMP client แบบ async (pysnmp): `get` และ `walk` (GETBULK) · แปลงค่าเป็น Python · `MockSnmpClient` อ่านเครือข่ายตัวอย่างจาก `fixtures/discovery.json` |
| `netcollect/discovery/mibs.py` | รายการ OID, ตารางหมายเลของค์กร → ยี่ห้อ, ฟังก์ชันแปลง MAC/IP/ข้อความ, แยก version, เดาชนิดอุปกรณ์ และ platform |
| `netcollect/discovery/engine.py` | ลำดับงาน: sweep → identify → crawl (BFS ตามจำนวน hop) → hosts → รวมอุปกรณ์ที่ซ้ำ |
| `netcollect/discovery/output.py` | เขียน CSV/Excel/JSON และสร้าง inventory |

แนวคิดสำคัญ:
- **asyncio + semaphore** — ถาม SNMP หลายร้อย IP พร้อมกันแต่จำกัดจำนวน ไม่ให้เครือข่าย/อุปกรณ์รับภาระเกิน
- **IP ที่ไม่ตอบ = timeout (เงียบ)** ส่วน **ตอบแต่ปฏิเสธ = error** (บันทึกใน errors.csv) — ช่วยแยก "ไม่มีเครื่อง/ไม่เปิด SNMP" ออกจาก "รหัสผิด"
- **รวมอุปกรณ์ซ้ำด้วย serial** (หรือ sysName) — switch ที่มีหลาย SVI ตอบหลาย IP จะเหลือแถวเดียว และถูกอ่าน CDP/LLDP ครั้งเดียว
- **ขอบเขตการไล่ปลอดภัยเป็นค่าเริ่มต้น** — ไม่ถาม IP สาธารณะ, เคารพ `--exclude`/`--scope`

### เพิ่มยี่ห้อ/OID เอง
- ยี่ห้อใหม่: เพิ่มใน `VENDORS` ของ `mibs.py` (หมายเลของค์กรจาก IANA "Private Enterprise Numbers") พร้อม OID serial/version ถ้ารู้
- อยากได้ข้อมูลเพิ่ม (เช่น จำนวนพอร์ต): เพิ่ม OID ใน `_details()` ของ `engine.py` แล้วเพิ่มคอลัมน์ใน `DEVICE_COLUMNS`
- ทดสอบด้วยการเพิ่มอุปกรณ์จำลองใน `fixtures/discovery.json` แล้วรัน `pytest`

---

## 7. แก้ปัญหา

| อาการ | สาเหตุ / วิธีแก้ |
|---|---|
| `0 answered SNMP` ทั้งที่อุปกรณ์มีอยู่ | SNMP ไม่ได้เปิด, ACL ไม่อนุญาต IP ของเครื่องที่รัน, **community ผิด (v2c จะเงียบ ไม่แจ้ง error)**, firewall กั้น UDP 161, ใช้ v2c กับอุปกรณ์ที่เปิดแค่ v3 |
| ทดสอบเครื่องเดียว | `snmpget -v3 -l authPriv -u netcollect -a SHA -A <auth> -x AES -X <priv> 10.0.10.2 1.3.6.1.2.1.1.5.0` (Net-SNMP) หรือ `--subnet 10.0.10.2/32 -v` |
| errors.csv: `Wrong SNMP PDU digest` | รหัส auth ผิด หรือ auth protocol ไม่ตรง (SHA vs SHA256) |
| errors.csv: `Unknown USM user` / `unknownUserName` | อุปกรณ์ไม่มี user นี้ (สะกดผิด, ยังไม่ได้สร้าง) |
| SNMPv3 auth ถูกแต่ **ไม่มีคำตอบเลย** (ไม่อยู่ใน errors.csv) | มักเป็น **รหัส priv ผิด หรือ priv protocol ไม่ตรง** (AES vs AES256/DES) — อุปกรณ์ถอดรหัสไม่ได้จึงเงียบ เหมือน community ผิดใน v2c |
| มีชื่อแต่ไม่มี serial | อุปกรณ์ไม่รองรับ ENTITY-MIB หรือ view ของ SNMP ไม่ให้อ่าน ENTITY-MIB → ขยาย view / ใช้ `collect` (SSH/API) แทน |
| ไม่เจอเพื่อนบ้าน | ไม่ได้ใส่ `--seed`, ไม่ได้เปิด LLDP/CDP, view ไม่ให้อ่าน LLDP-MIB, เพื่อนบ้านไม่ประกาศ management IP |
| ไล่ไปไม่ถึงบาง switch | IP นอก `--scope`/ไม่ใช่ IP ส่วนตัว, เกิน `--max-hops`, switch นั้นไม่ตอบ SNMP |
| สแกนช้า | วงใหญ่ + timeout สูง → ลด `--timeout`, เพิ่ม `-w` (ระวังภาระ), สแกนเฉพาะวง management |
| `more than 1024` | ตั้งใจสแกนวงใหญ่จริง → `--allow-large` |

---

## 8. แบบฝึกหัด

1. รัน `--mock` แบบมีและไม่มี `--seed` เปรียบเทียบว่าเจออุปกรณ์ต่างกันอย่างไร เพราะอะไร
2. รัน `--mock --seed 10.0.10.2 --max-hops 0` แล้วดูว่า acc-sw-3f ได้ serial ไหม อธิบายเหตุผล
3. เปิด devices.csv ใน Excel ทำ pivot นับอุปกรณ์ตาม vendor และ type
4. จาก neighbors.csv วาดผัง core → access → AP/phone (หรือใช้ draw.io/Mermaid)
5. ใน lab: เปิด SNMPv3 บน switch/router (Cisco CML/EVE-NG หรือ Linux + snmpd) แล้วรัน discover จริง
6. ใส่รหัส v3 ผิดโดยตั้งใจ ดูข้อความใน errors.csv แล้วจับคู่กับตารางแก้ปัญหา
7. นำ `inventory.discovered.yaml` ไปใช้กับ `collect --mock` แล้วต่อด้วย `collect` จริงเมื่อมี credential
8. เพิ่มยี่ห้อที่ยังไม่มีในตาราง `VENDORS` และเพิ่มอุปกรณ์จำลองใน fixture พร้อม test

⬅️ [README ของ netcollect](README.md)
