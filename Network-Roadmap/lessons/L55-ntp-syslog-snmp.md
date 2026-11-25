# บทเรียน Level 55 — NTP, Syslog, SNMP (ฉบับละเอียด)

> อ่านจบแล้วจะ: ตั้งเวลาให้ทุกอุปกรณ์ตรงกันด้วย NTP · ส่ง log เข้า syslog server พร้อมระดับความรุนแรงที่เหมาะสม · ใช้ SNMP (โดยเฉพาะ v3) monitor อุปกรณ์ · อ่าน OID/MIB · รู้จัก streaming telemetry · ตั้งค่า baseline การจัดการอุปกรณ์ได้ครบ

> สามบริการนี้คือ **"พื้นฐานการจัดการ (management plane)"** ที่ทุกอุปกรณ์ต้องตั้งตั้งแต่วันแรก — ถ้าไม่มี ก็แก้ปัญหาและตรวจสอบย้อนหลังไม่ได้

---

## 1. NTP — Network Time Protocol

### ทำไมเวลาต้องตรง

| ระบบ | ถ้าเวลาไม่ตรง |
|---|---|
| **Log correlation** | เทียบเหตุการณ์ข้ามอุปกรณ์ไม่ได้ (firewall บอก 10:05 router บอก 09:58) — สืบสวนเหตุการณ์ไม่ได้ |
| **Kerberos / Active Directory** | เวลาคลาดเกิน 5 นาที (ค่าเริ่มต้น) → **login ล้มเหลว** |
| **Certificate / TLS** | cert ดูเหมือนหมดอายุหรือยังไม่เริ่มใช้ → เชื่อมต่อไม่ได้ |
| **MFA (TOTP)** | รหัส OTP ไม่ตรง |
| **กฎหมาย (พ.ร.บ.คอมพิวเตอร์ฯ)** | log ต้องระบุเวลาที่ถูกต้องและอ้างอิงเวลามาตรฐานได้ |
| Backup, scheduling, billing, ระบบการเงิน | ทำงานผิดเวลา |

### Stratum — ลำดับชั้นความแม่นยำ
```
 Stratum 0: นาฬิกาอ้างอิง (atomic clock, GPS)        ← ไม่ได้อยู่บนเครือข่าย
 Stratum 1: server ที่ต่อกับ stratum 0 โดยตรง
 Stratum 2: sync จาก stratum 1
 ...
 Stratum 16: ไม่ได้ sync (unsynchronized)
```
- NTP ใช้ **UDP 123** · ปรับเวลาอย่างค่อยเป็นค่อยไปและชดเชยความหน่วงของเครือข่าย (แม่นระดับมิลลิวินาทีในเครือข่ายทั่วไป)
- แหล่งเวลาในไทย: **time.navy.mi.th** (กองทัพเรือ — หน่วยงานเวลามาตรฐานของประเทศ), **pool.ntp.org** (`th.pool.ntp.org`), time.google.com, time.cloudflare.com

### ออกแบบ NTP ในองค์กร
```
 Internet NTP (≥ 3-4 แหล่ง) หรือ GPS appliance
           │
   [NTP ภายใน 2 ตัว] (core router/DC หรือ server เฉพาะ)
           │
   อุปกรณ์ทั้งหมด (switch, firewall, server, AP) → sync จาก NTP ภายใน
   (Windows ในโดเมน: sync จาก domain controller · PDC emulator sync จากแหล่งภายนอก)
```
- ใช้ **อย่างน้อย 3–4 แหล่ง** เพื่อให้ NTP ตัดแหล่งที่ผิดปกติออกได้ (ถ้ามีแค่ 2 แหล่งที่ไม่ตรงกัน ไม่รู้ว่าเชื่อใคร)
- ใช้ **authentication** ระหว่างอุปกรณ์กับ NTP ภายใน (ป้องกันการปลอมเวลา) · รุ่นใหม่มี **NTS (Network Time Security)**
- ตั้ง **timezone** ให้ถูกบนทุกอุปกรณ์ (ไทย UTC+7) หรือใช้ UTC ทั้งหมดแล้วแปลงใน SIEM (ทำให้เทียบข้ามประเทศง่าย)

```
! Cisco
clock timezone ICT 7 0
ntp authentication-key 1 md5 S3cr3t!
ntp authenticate
ntp trusted-key 1
ntp server 10.0.0.123 key 1 prefer
ntp server 10.0.0.124 key 1
ntp source Loopback0
show ntp status            ! "Clock is synchronized, stratum 3, reference is 10.0.0.123"
show ntp associations      ! * = ใช้อยู่ (sys.peer)
show clock detail
```
```bash
# Linux (chrony)
chronyc sources -v ; chronyc tracking
timedatectl
# Windows
w32tm /query /status ; w32tm /query /peers ; w32tm /resync
```

---

## 2. Syslog — รวม Log ไว้ที่เดียว

### ทำไมต้องส่ง log ออกไปเก็บที่อื่น
- Log ในอุปกรณ์ (buffer) **จำกัดขนาดและหายเมื่อ reboot**
- รวมศูนย์ → **ค้นหาข้ามอุปกรณ์**, **แจ้งเตือน**, **เก็บตามกฎหมาย** (พ.ร.บ.คอมฯ: ≥ 90 วัน), **สืบสวนเหตุการณ์ด้านความปลอดภัย**
- ผู้โจมตีที่ยึดอุปกรณ์ได้ลบ log ในเครื่องได้ แต่ลบ log ที่ส่งออกไปแล้วไม่ได้

### Protocol
- **UDP 514** (ดั้งเดิม ไม่รับประกันการส่ง), **TCP 514/601**, **TLS 6514** (เข้ารหัส — แนะนำเมื่อส่งข้ามเครือข่ายที่ไม่น่าไว้ใจ)
- รูปแบบ: RFC 3164 (เดิม), RFC 5424 (มาตรฐานใหม่)

### Severity Levels (ต้องจำ)

| Level | ชื่อ | ความหมาย | ตัวอย่าง |
|---|---|---|---|
| **0** | **Emergency** | ระบบใช้งานไม่ได้ | |
| **1** | **Alert** | ต้องแก้ทันที | อุณหภูมิวิกฤต |
| **2** | **Critical** | สภาวะวิกฤต | hardware เสีย |
| **3** | **Error** | ข้อผิดพลาด | interface error |
| **4** | **Warning** | คำเตือน | MAC flapping, config change บางอย่าง |
| **5** | **Notice** | ปกติแต่สำคัญ | interface up/down, OSPF neighbor change |
| **6** | **Informational** | ข้อมูลทั่วไป | ACL log, login |
| **7** | **Debug** | ละเอียดสำหรับแก้ปัญหา | output ของ debug |

**วิธีจำ (0→7):** "**E**very **A**wesome **C**isco **E**ngineer **W**ill **N**eed **I**ce cream **D**aily"
> ⚠️ ตัวเลข **ยิ่งน้อยยิ่งรุนแรง** · การตั้ง `logging trap 6` = ส่งระดับ **0 ถึง 6** (ทุกระดับที่รุนแรงเท่าหรือมากกว่า)

```
! Cisco
service timestamps log datetime msec localtime show-timezone
service sequence-numbers
logging buffered 64000 informational          ! เก็บในเครื่องด้วย
logging host 10.0.0.50 transport udp port 514
logging trap informational                    ! ส่งระดับ 0-6 ไป server
logging source-interface Loopback0            ! IP ต้นทางคงที่ (ระบุอุปกรณ์ได้ง่าย)
logging origin-id hostname
login on-success log                          ! log การ login
archive
 log config
  logging enable                              ! log ทุกคำสั่งที่แก้ config (ใครทำอะไร)
show logging
```
### อ่าน log ของ Cisco
```
000123: Nov 23 10:15:02.123 ICT: %LINEPROTO-5-UPDOWN: Line protocol on Interface Gi1/0/12, changed state to down
                                 └facility┘└sev┘└mnemonic┘  └────────── ข้อความ ──────────┘
```

### Syslog Server / ระบบที่ใช้
rsyslog, syslog-ng (Linux), Graylog, **ELK/OpenSearch**, Splunk, **Wazuh**, FortiAnalyzer, Kiwi Syslog — ระดับองค์กรนำ log เข้า **SIEM** (Level 68) เพื่อ correlation และแจ้งเตือน

---

## 3. SNMP — Simple Network Management Protocol

### ใช้ทำอะไร
**ดึงข้อมูลสถานะและสถิติ** จากอุปกรณ์เพื่อ monitor: interface up/down, bandwidth, error, CPU, memory, อุณหภูมิ, พัดลม, PSU, จำนวนผู้ใช้ Wi-Fi ฯลฯ

### องค์ประกอบ
```
 [NMS / Manager]  ── GET/WALK (poll, UDP 161) ──►  [Agent ในอุปกรณ์]
 (Zabbix, LibreNMS,  ◄──────── Response ──────────    มี MIB = ฐานข้อมูลค่าต่าง ๆ
  PRTG, SolarWinds)  ◄── TRAP / INFORM (UDP 162) ──   (ส่งแจ้งเตือนเองเมื่อมีเหตุการณ์)
```
- **MIB (Management Information Base)** = โครงสร้างข้อมูลแบบต้นไม้ของค่าที่อ่านได้
- **OID (Object Identifier)** = ที่อยู่ของค่าแต่ละตัวในต้นไม้ เช่น
  - `1.3.6.1.2.1.1.5.0` = sysName (ชื่ออุปกรณ์)
  - `1.3.6.1.2.1.1.3.0` = sysUpTime
  - `1.3.6.1.2.1.2.2.1.8` = ifOperStatus (สถานะ interface)
  - `1.3.6.1.2.1.31.1.1.1.6` = **ifHCInOctets** (ตัวนับไบต์ขาเข้า 64 บิต — ใช้คำนวณ bandwidth)
- **Poll (GET/GETNEXT/GETBULK/WALK)** — manager ถามเป็นระยะ (เช่น ทุก 1–5 นาที)
- **Trap** — agent ส่งแจ้งเตือนทันทีเมื่อมีเหตุการณ์ (ไม่มีการยืนยันรับ) · **Inform** = trap ที่มีการยืนยัน
- **SET** — แก้ค่าในอุปกรณ์ (ควรปิด/ไม่ใช้)

### คำนวณ bandwidth จาก SNMP
```
 poll ifHCInOctets ทุก 300 วินาที: ครั้งที่ 1 = 1,000,000,000 · ครั้งที่ 2 = 4,750,000,000
 Mbps = (4,750,000,000 − 1,000,000,000) × 8 ÷ 300 ÷ 1,000,000 = 100 Mbps (เฉลี่ยในช่วง 5 นาที)
```
> ใช้ตัวนับ **64 บิต (HC — High Capacity)** เสมอบนลิงก์ ≥ 1G ตัวนับ 32 บิตวนกลับเป็น 0 เร็วเกินไป (ที่ 1 Gbps วนครบใน ~34 วินาที)
> ค่าเฉลี่ย 5 นาที **มองไม่เห็น microburst** (Level 90)

### เวอร์ชันของ SNMP

| เวอร์ชัน | การยืนยันตัวตน | เข้ารหัส | ใช้ไหม |
|---|---|---|---|
| v1 | community string (ข้อความธรรมดา) | ❌ | ❌ |
| **v2c** | community string (ข้อความธรรมดา) | ❌ | พบมาก แต่เสี่ยง — community ถูกดักได้ |
| **v3** ⭐ | **username + HMAC (SHA)** | ✅ **AES** | **แนะนำ** |

**SNMPv3 Security Levels:** `noAuthNoPriv` · `authNoPriv` · **`authPriv`** (ยืนยันตัวตน + เข้ารหัส — ใช้ระดับนี้)

```
! Cisco SNMPv3 (read-only)
ip access-list standard SNMP-NMS
 permit host 10.0.0.60
snmp-server view RO-VIEW iso included
snmp-server group NMS-GROUP v3 priv read RO-VIEW access SNMP-NMS
snmp-server user nmsuser NMS-GROUP v3 auth sha AuthP@ss123 priv aes 128 PrivP@ss123
snmp-server host 10.0.0.60 version 3 priv nmsuser
snmp-server enable traps snmp linkdown linkup
snmp-server enable traps envmon
snmp-server location BKK-HQ-F03-RACK2
snmp-server contact noc@company.example
```
```bash
# ทดสอบจาก Linux
snmpwalk -v3 -l authPriv -u nmsuser -a SHA -A 'AuthP@ss123' -x AES -X 'PrivP@ss123' 10.0.99.11 1.3.6.1.2.1.1
snmpget  -v2c -c <community> 10.0.99.11 1.3.6.1.2.1.1.5.0        # v2c (lab เท่านั้น)
```
### Best practice SNMP
- ใช้ **v3 authPriv** · ถ้าจำเป็นต้องใช้ v2c: community ที่เดายาก, **read-only**, **ACL จำกัดเฉพาะ NMS**, ไม่ใช้ "public/private"
- **ปิด SNMP write** · กรอง UDP 161 จากภายนอก
- ตั้ง `snmp-server location/contact` ให้เป็นมาตรฐาน (NMS จะดึงไปแสดง)

---

## 4. Streaming Telemetry — อนาคตของการ monitor

| | SNMP Polling | Streaming Telemetry (gNMI/gRPC, NETCONF) |
|---|---|---|
| รูปแบบ | NMS ถามเป็นรอบ (pull) | **อุปกรณ์ส่งเอง (push)** ตามรอบหรือเมื่อเปลี่ยน |
| ความละเอียด | นาที | **วินาทีหรือต่ำกว่า** |
| ข้อมูล | MIB (เก่า, ไม่ครบทุกฟีเจอร์) | **YANG model** (structured, ครบกว่า) |
| ภาระอุปกรณ์ | การ walk ตารางใหญ่หนัก | มีประสิทธิภาพกว่า |
| ใช้ที่ | ทุกที่ (มาตรฐานเดิม) | Data center, SP, อุปกรณ์รุ่นใหม่ |

เครื่องมือ: Telegraf/gNMIc → InfluxDB/Prometheus → Grafana (Level 83, 86)

---

## 5. Management Baseline (ทุกอุปกรณ์ต้องมี)

```
☐ Hostname ตาม naming convention         ☐ NTP ≥ 2 แหล่ง + timezone + authentication
☐ Syslog ไป server กลาง (+timestamp msec)  ☐ SNMPv3 read-only + ACL + location/contact
☐ AAA (TACACS+/RADIUS) + local fallback    ☐ SSH เท่านั้น + ACL management
☐ Config backup อัตโนมัติ                   ☐ อยู่ใน monitoring + alert
☐ Banner + log การ login/การแก้ config      ☐ ใช้ loopback/management VRF เป็น source
```

---

## 6. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| Syslog severity 7 รุนแรงที่สุด | **0 = Emergency รุนแรงที่สุด** · 7 = Debug |
| ใช้ NTP server เดียวก็พอ | ควรใช้หลายแหล่ง (≥ 3) |
| SNMPv2c เข้ารหัส community | ส่งเป็นข้อความธรรมดา |
| Trap แทนการ poll ได้ทั้งหมด | trap อาจหาย (UDP) ต้องมี poll ด้วย |
| ค่าเฉลี่ย 5 นาทีจาก SNMP เห็นทุกปัญหา | มองไม่เห็น burst สั้น ๆ |

---

## 7. Cheat Sheet

```
NTP UDP 123 · stratum 0 (ref) → 1 → 2 ... 16 = ไม่ sync · ≥3 แหล่ง · auth · timezone
เวลาผิด → log เทียบไม่ได้, Kerberos (5 นาที), cert, MFA
show ntp status / associations · chronyc sources · w32tm /query /status
Syslog UDP 514 / TLS 6514 · 0 Emerg 1 Alert 2 Crit 3 Err 4 Warn 5 Notice 6 Info 7 Debug
logging host X · logging trap informational (=0-6) · service timestamps msec · archive log config
SNMP: poll UDP 161 · trap UDP 162 · MIB/OID · ifHCInOctets (64-bit)
v1/v2c community ข้อความธรรมดา · v3 authPriv (SHA+AES) ⭐ · read-only + ACL
Mbps = Δoctets × 8 ÷ วินาที ÷ 10^6
Streaming telemetry: push, YANG, gNMI · ละเอียดกว่า SNMP
```

---

## 8. แบบทดสอบ 10 ข้อ

1. ทำไมเวลาของอุปกรณ์ต้องตรงกัน (3 เหตุผล)
2. NTP ใช้ port อะไร stratum 16 หมายความว่าอะไร
3. ทำไมควรตั้ง NTP อย่างน้อย 3 แหล่ง
4. เรียง syslog severity 0–7
5. `logging trap warnings` จะส่ง log ระดับใดบ้าง
6. SNMP poll และ trap ใช้ port อะไร ต่างกันอย่างไร
7. SNMPv2c กับ v3 ต่างกันอย่างไรด้านความปลอดภัย
8. ทำไมต้องใช้ตัวนับ ifHCInOctets (64 บิต) บนลิงก์ 10G
9. poll ifHCOutOctets ห่างกัน 60 วินาที ได้ผลต่าง 750,000,000 ไบต์ คิดเป็นกี่ Mbps
10. Streaming telemetry ดีกว่า SNMP polling อย่างไร

<details><summary><b>เฉลย</b></summary>

1. เทียบ log ข้ามอุปกรณ์ได้, Kerberos/AD ทำงาน (คลาดไม่เกิน 5 นาที), certificate/TLS และ MFA ทำงานถูกต้อง (รวมถึงข้อกำหนดทางกฎหมาย)
2. UDP 123; stratum 16 = ไม่ได้ sync
3. ให้ NTP เปรียบเทียบและตัดแหล่งที่ผิดปกติออกได้ (2 แหล่งที่ขัดกันตัดสินไม่ได้) และสำรองเมื่อแหล่งหนึ่งล่ม
4. 0 Emergency, 1 Alert, 2 Critical, 3 Error, 4 Warning, 5 Notice, 6 Informational, 7 Debug
5. ระดับ 0–4
6. Poll UDP 161 (manager ถาม agent), Trap UDP 162 (agent ส่งแจ้งเตือนเองเมื่อมีเหตุการณ์)
7. v2c ใช้ community string แบบข้อความธรรมดา ไม่เข้ารหัส; v3 มี username + HMAC และเข้ารหัส (authPriv)
8. ตัวนับ 32 บิตวนกลับเป็น 0 เร็วมากบนลิงก์ความเร็วสูง ทำให้คำนวณผิด
9. 750,000,000 × 8 ÷ 60 ÷ 1,000,000 = 100 Mbps
10. อุปกรณ์ push ข้อมูลเองแบบใกล้ real-time ความละเอียดระดับวินาที ข้อมูลเป็นโครงสร้าง YANG และมีประสิทธิภาพกว่า
</details>

---

➡️ ต่อไป: **Level 56 — AAA: RADIUS & TACACS+**
