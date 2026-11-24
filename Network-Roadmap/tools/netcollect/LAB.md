# LAN จำลอง (netcollect lab) — ทดสอบ discover และ collect โดยไม่ต้องมีอุปกรณ์จริง

> `python -m netcollect lab` สร้าง **เครือข่ายจำลองบนเครื่องเดียว** ที่ "อุปกรณ์" แต่ละตัวมี IP ของตัวเองและตอบเหมือนของจริงผ่าน **protocol จริง**:
> - **SNMP v2c/v3** (UDP) — ให้ `discover`, `snmpwalk`, Zabbix, LibreNMS, PRTG ถามได้
> - **SSH** แบบ Cisco IOS-XE CLI — ให้ `collect` (Netmiko) หรือคุณเอง `ssh` เข้าไปพิมพ์ `show ...`
> - **HTTPS REST API ของ FortiGate** และ **XML API ของ Palo Alto** — พร้อม certificate จาก CA ของ lab (ตรวจ TLS ได้จริง)
>
> ต่างจาก `--mock` ตรงที่ `--mock` อ่านข้อมูลจากไฟล์โดยตรง ส่วน lab **ส่งข้อมูลผ่านเครือข่าย** จึงทดสอบได้ทั้งการเชื่อมต่อ, รหัสผ่าน, timeout, TLS และการ parse output จริง

```
                       เครื่องของคุณ (ทุกอย่างอยู่บน loopback 127.x.x.x — ไม่ส่ง traffic ออกเครือข่ายจริง)
 ┌───────────────────────────────────────────────────────────────────────────────────────────────┐
 │ EDGE-RTR-01 127.0.10.1   ─CDP─┐                                                               │
 │ CORE-SW-02  127.0.10.3   ─CDP─┤                                                               │
 │ FGT-HQ      127.0.10.254 ─LLDP┤                                                               │
 │ AP-2F-01    127.0.50.21  ─LLDP┼── CORE-SW-01 127.0.10.2 (+127.0.10.252) ── ARP: PC/IoT 4 เครื่อง │
 │ IP Phone    127.0.30.55  ─CDP─┤                                                               │
 │ ACC-SW-2F   127.0.10.12  ─LLDP┘── LLDP ── ACC-SW-3F 127.0.11.13 (คนละวง)                        │
 │ PA-DMZ-01 127.0.10.21 · PRN-ACC-2F 127.0.10.50 · nms01 127.0.10.60                              │
 └───────────────────────────────────────────────────────────────────────────────────────────────┘
   SNMP :1161 (ทุกเครื่อง)   SSH :2222 (Cisco)   HTTPS :8443 (FortiGate, Palo Alto)
```

---

## 1. ติดตั้ง

```bash
cd Network-Roadmap/tools/netcollect
python3 -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt                            # รวม pysnmp, netmiko (paramiko, cryptography)
```
| ระบบปฏิบัติการ | หมายเหตุ |
|---|---|
| **Linux** | ใช้ได้ทันที (ทุก IP ใน 127.0.0.0/8 ใช้ได้) |
| **Windows** | ใช้ได้ทันที — ถ้า Windows Firewall ถามให้อนุญาต Python ให้เลือก "Private networks" (traffic อยู่บนเครื่องเท่านั้น) |
| **macOS** | มีแค่ 127.0.0.1 → รัน `python -m netcollect lab aliases` แล้วคัดลอกคำสั่ง `sudo ifconfig lo0 alias ...` ไปรันก่อน (หายเมื่อ reboot) |

---

## 2. วิธีที่ 1: ทดสอบอัตโนมัติทั้งระบบ (1 คำสั่ง)

```bash
python -m netcollect lab selftest
```
ระบบจะ: เปิด LAN จำลอง → รัน **discover จริงผ่าน SNMPv3** → สร้าง inventory → รัน **collect จริงผ่าน SSH และ HTTPS** → ตรวจผล → ปิด lab
```
1) discover (SNMPv3, real UDP to the lab agents)
  [PASS] discover found CORE-SW-01  (127.0.10.2)
  [PASS] CORE-SW-01 serial(s)  (FOC2412X0AB, FOC2412X0AC)
  ...
  [PASS] SEP001122334455 seen via CDP/LLDP (no SNMP)  (Cisco IP Phone 8841)
  [PASS] device answering on two IPs merged  (['127.0.10.252'])
2) collect (SSH to Cisco, HTTPS REST/XML API to FortiGate/Palo Alto, TLS verified with lab CA)
  [PASS] collect core-sw-01 (cisco_ios)  (C9300-48P FOC2412X0AB 17.9.4a)
  [PASS] collect fgt-hq (fortigate)  (FortiGate FG100FTK20012345 v7.2.8)
  [PASS] finding detected: core-sw-02 ospf
  ...
Self-test: 34/34 checks passed · outputs in lab-run
```
- `--snmp-version 2c` ทดสอบด้วย v2c · ผลลัพธ์ทั้งหมด (Excel/CSV/inventory) อยู่ใน `lab-run/`
- ใช้คำสั่งนี้ทุกครั้งหลังแก้โค้ด เพื่อยืนยันว่าทั้งระบบยังทำงาน

---

## 3. วิธีที่ 2: เปิด lab ทิ้งไว้แล้วลองเองทีละขั้น (แนะนำสำหรับฝึก)

**Terminal 1** — เปิด lab:
```bash
python -m netcollect lab start
```
จะแสดงรายชื่ออุปกรณ์ บริการ และคำสั่งตัวอย่าง (กด Ctrl+C เพื่อปิด)

**Terminal 2** — ใช้งานเหมือนเครือข่ายจริง:
```bash
source lab-run/lab.env              # Windows PowerShell:  . .\lab-run\lab.ps1
                                    # (ตั้ง SNMP_USER, SNMP_AUTH_PASS, NET_USER, FGT_HQ_TOKEN ... ของ lab)

# ① ค้นหาอุปกรณ์ทั้งหมด + สร้าง inventory
python -m netcollect discover --snmp-version 3 --snmp-port 1161 \
    --subnet 127.0.10.0/24 --seed 127.0.10.2 --scope 127.0.0.0/8 --arp \
    --inventory-defaults lab-run/lab-inventory-defaults.yaml --inventory-out lab-run/inventory.yaml

# ② ดึงข้อมูลละเอียด + ตรวจปัญหา
python -m netcollect collect -i lab-run/inventory.yaml
```
ทำไมต้องมีตัวเลือกเพิ่มใน lab:
| ตัวเลือก | เหตุผล |
|---|---|
| `--snmp-port 1161` | Linux ต้องเป็น root ถึงใช้ port 161 ได้ lab จึงใช้ 1161 (เครือข่ายจริงไม่ต้องใส่) |
| `--scope 127.0.0.0/8` | ค่าเริ่มต้นการไล่ CDP/LLDP ไม่ไป IP ประเภท loopback (ป้องกันในเครือข่ายจริง) lab จึงต้องอนุญาตเอง |
| `--inventory-defaults` | ใส่พอร์ต SSH 2222 / HTTPS 8443 และไฟล์ CA ของ lab ลงใน inventory ที่สร้าง |
| ไม่ใช้ `--ping` | บน Linux ทุก IP ใน 127.x ตอบ ping จึงเห็น "เครื่อง" ครบ 254 IP ซึ่งไม่ตรงกับความจริง (ใช้ `--arp` แทน) |

### ลองด้วยเครื่องมือมาตรฐานอื่น (เหมือนกับอุปกรณ์จริง)
```bash
# SNMP (Net-SNMP)
snmpwalk -v3 -l authPriv -u $SNMP_USER -a SHA -A $SNMP_AUTH_PASS -x AES -X $SNMP_PRIV_PASS 127.0.10.2:1161 1.3.6.1.2.1.1
snmpwalk -v2c -c $SNMP_COMMUNITY 127.0.10.2:1161 1.0.8802.1.1.2.1.4.1.1.9      # ชื่อเพื่อนบ้าน LLDP
snmpget  -v2c -c $SNMP_COMMUNITY 127.0.10.254:1161 1.3.6.1.4.1.12356.100.1.1.1.0   # serial FortiGate

# SSH เหมือนเข้า Cisco
ssh -p 2222 $NET_USER@127.0.10.2        # รหัส: ค่าใน $NET_PASS
CORE-SW-01# show version
CORE-SW-01# show ip interface brief | include Vlan
CORE-SW-01# show ip ospf neighbor
CORE-SW-01# exit

# FortiGate REST API (ตรวจ TLS ด้วย CA ของ lab)
curl --cacert lab-run/lab-ca.pem -H "Authorization: Bearer $FGT_HQ_TOKEN" \
     https://127.0.10.254:8443/api/v2/monitor/system/status
curl --cacert lab-run/lab-ca.pem -H "Authorization: Bearer $FGT_HQ_TOKEN" \
     https://127.0.10.254:8443/api/v2/monitor/vpn/ipsec

# Palo Alto: ขอ API key แบบเดียวกับของจริง แล้วเรียก op command
curl --cacert lab-run/lab-ca.pem -X POST https://127.0.10.21:8443/api/ \
     --data-urlencode type=keygen --data-urlencode user=labadmin --data-urlencode password=lab-api-pass
curl --cacert lab-run/lab-ca.pem -H "X-PAN-KEY: $PA_DMZ_01_KEY" -G https://127.0.10.21:8443/api/ \
     --data-urlencode type=op --data-urlencode "cmd=<show><system><info></info></system></show>"
```
> ต่อเครื่องมือ monitoring จริง (Zabbix/LibreNMS/Prometheus snmp_exporter) เข้ากับ lab ได้ด้วย เพื่อฝึก Level 86 — ตั้ง SNMP port เป็น 1161

---

## 4. ปัญหาที่ใส่ไว้ใน lab (ให้ฝึกหา)

| อุปกรณ์ | ปัญหาจำลอง | คำสั่ง/ข้อมูลที่เห็น |
|---|---|---|
| CORE-SW-02 | OSPF ค้าง EXSTART (MTU ไม่ตรง) | `show ip ospf neighbor` · finding `ospf` |
| CORE-SW-02 | พอร์ต Gi1/0/8 มี CRC 235 + half duplex | `show interfaces` · finding `interface` |
| CORE-SW-02 | CPU 84% | `show processes cpu` · finding `resources` |
| EDGE-RTR-01 | BGP กับ 198.51.100.1 ค้าง Active | `show ip bgp summary` · finding `bgp` |
| FGT-HQ | VPN-KKC ล่ม, VPN-AWS รับ 0 byte, SD-WAN wan2 loss 6% | REST API `vpn/ipsec`, `virtual-wan/health-check` |
| PA-DMZ-01 | BGP peer ISP-B ไม่ขึ้น, ethernet1/3 down | XML API |
| CORE-SW-01 | ตอบ SNMP สอง IP | discover ต้องรวมเป็นอุปกรณ์เดียว |
| ACC-SW-3F | อยู่คนละวง | discover เจอได้จากการไล่ LLDP เท่านั้น |
| AP / IP Phone | ไม่มี SNMP | เห็นแค่ชื่อ/รุ่นจาก CDP/LLDP — ไม่มี serial |

### ฝึกกรณีผิดพลาด (เหมือนที่จะเจอในงานจริง)
```bash
SNMP_AUTH_PASS=wrong python -m netcollect discover --snmp-version 3 --snmp-port 1161 --subnet 127.0.10.2/32
#   → errors.csv: "Wrong SNMP PDU digest" (รหัส auth ผิด)
SNMP_USER=nobody python -m netcollect discover --snmp-version 3 --snmp-port 1161 --subnet 127.0.10.2/32
#   → "Unknown USM user"
SNMP_COMMUNITY=wrong python -m netcollect discover --snmp-port 1161 --subnet 127.0.10.0/24
#   → 0 answered SNMP (v2c community ผิดจะเงียบ ไม่มี error)
FGT_HQ_TOKEN=wrong python -m netcollect collect -i lab-run/inventory.yaml --device fgt-hq
#   → 401 Unauthorized: check the API token
python -m netcollect collect -i lab-run/inventory.yaml --device fgt-hq     # หลังปิด lab
#   → ConnectionError (เหมือนอุปกรณ์ดับ/firewall กั้น)
```
แก้ `lab-run/inventory.yaml` ให้ `verify_tls: false` แล้วเทียบกับการใช้ CA — เข้าใจว่าการตรวจ certificate ป้องกันอะไร (Level 65)

---

## 5. ออกแบบ LAN จำลองของคุณเอง

คัดลอก `netcollect/lab/topology.yaml` มาแก้ แล้วรัน:
```bash
python -m netcollect lab start --topology my-lab.yaml
python -m netcollect lab selftest --topology my-lab.yaml
```
### เพิ่มอุปกรณ์
```yaml
devices:
  - name: ACC-SW-4F
    kind: cisco_ios               # cisco_ios | aruba_switch | huawei_switch | fortigate | paloalto | printer | linux | ap | phone
    ip: 127.0.10.14               # ต้องเป็น 127.x.x.x และไม่ซ้ำ
    model: C9200L-48P-4X
    serials: [JAE12345678]
    version: 17.9.4a
    location: BKK HQ, 4th floor IDF
    cli:                          # (เฉพาะ cisco_ios) ข้อมูลที่ show commands จะตอบ
      default_gateway: 127.0.10.4
      cpu: 15
      interfaces:
        - {name: Vlan10, ip: 127.0.10.14/24, description: MGMT}
        - {name: GigabitEthernet1/0/48, description: uplink-core}
        - {name: GigabitEthernet1/0/5, description: PC-4F-05, crc: 50}     # ใส่ปัญหาเอง
      ospf: []
      bgp: []
      hsrp: []
```
### เพิ่มสายเชื่อม (CDP/LLDP)
```yaml
links:
  - [CORE-SW-01, GigabitEthernet1/0/46, ACC-SW-4F, GigabitEthernet1/0/48, both]   # lldp | cdp | both
```
### เพิ่มเครื่องในตาราง ARP
```yaml
hosts:
  arp_device: CORE-SW-01
  list:
    - [10.0.20.77, a4:bb:6d:00:00:77]
```
### เปลี่ยน credential/พอร์ตของ lab
แก้ในหัวข้อ `lab:` (snmp/ssh/api) — ค่าทั้งหมดเป็นรหัส **สำหรับ lab เท่านั้น** ห้ามนำไปใช้กับระบบจริง

---

## 6. ส่วนประกอบภายใน (สำหรับศึกษา/แก้ไข)

| ไฟล์ | หน้าที่ |
|---|---|
| `netcollect/lab/topology.yaml` | เครือข่ายตัวอย่าง (แก้/คัดลอกได้) |
| `netcollect/lab/model.py` | อ่าน topology → สร้างตาราง OID ของแต่ละอุปกรณ์ (system, ENTITY-MIB, LLDP-MIB, CDP-MIB, ARP, OID เฉพาะยี่ห้อ) |
| `netcollect/lab/snmp_agent.py` | SNMP agent จริง (pysnmp command responder) หนึ่งตัวต่อหนึ่ง IP · รองรับ GET/GETNEXT/GETBULK · v2c + v3 (SHA/AES) |
| `netcollect/lab/ssh_server.py` + `cli_outputs.py` | SSH server (paramiko) จำลอง prompt และ output ของ Cisco ที่ ntc-templates อ่านได้ |
| `netcollect/lab/api_server.py` + `certs.py` | HTTPS server จำลอง FortiOS REST / PAN-OS XML API, ตรวจ token/API key, CA ของ lab |
| `netcollect/lab/selftest.py` | ทดสอบทั้งระบบอัตโนมัติ |

**สิ่งที่ lab ช่วยพบแล้ว:** ntc-templates รุ่นปัจจุบันใช้ชื่อช่อง `bgp_neighbor`, `neighbor_as`, `virtual_ip_address` ซึ่งต่างจากที่ตัวเก็บข้อมูล Cisco เคยรองรับ — ถ้าไม่มีการทดสอบผ่าน SSH จริง ข้อมูล BGP/HSRP จะว่างเมื่อใช้กับอุปกรณ์จริง (แก้แล้ว)

### ข้อจำกัด (lab ไม่ใช่อุปกรณ์จริงทั้งหมด)
- CLI ของ Cisco รองรับเฉพาะคำสั่งที่ collect ใช้ (`show version`, `show ip interface brief`, `show interfaces`, `show ip route`, `show ip bgp summary`, `show ip ospf neighbor`, `show standby brief`, `show processes cpu`) และ `| include/exclude`
- FortiGate/Palo Alto ตอบจากข้อมูลตัวอย่าง (เปลี่ยนเฉพาะชื่อ/serial/รุ่น/version ตาม topology)
- ไม่จำลอง routing/forwarding จริง — สำหรับฝึก routing ใช้ containerlab/EVE-NG/GNS3 (Level 28)
- รายละเอียด output ของอุปกรณ์จริงต่างกันตามรุ่นและ version — ก่อนใช้งานจริงให้ทดสอบกับอุปกรณ์ 1 เครื่องพร้อม `--raw`

---

## 7. แก้ปัญหา lab

| อาการ | วิธีแก้ |
|---|---|
| `cannot open lab address/port ... Cannot assign requested address` | macOS: รัน `lab aliases` ก่อน · ตรวจว่า IP ใน topology เป็น 127.x |
| `... Address already in use` | lab อีกตัว/โปรแกรมอื่นใช้พอร์ตอยู่ → ปิดก่อน หรือเปลี่ยนพอร์ตใน `lab:` |
| discover: `0 answered SNMP` | ลืม `--snmp-port 1161` หรือยังไม่ได้ `source lab-run/lab.env` |
| collect: `certificate verify failed` | ใช้ inventory/CA จาก lab คนละรอบ (CA สร้างใหม่ทุกครั้งที่ start) → รัน discover ใหม่ หรือชี้ `verify_tls` ไปที่ `lab-run/lab-ca.pem` ปัจจุบัน |
| collect Cisco: `netmiko is not installed` | `pip install -r requirements.txt` |
| `lab needs extra packages` | `pip install pysnmp paramiko cryptography` |

⬅️ [README ของ netcollect](README.md) · [คู่มือ discover](DISCOVER.md)
