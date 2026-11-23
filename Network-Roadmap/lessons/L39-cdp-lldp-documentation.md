# บทเรียน Level 39 — CDP, LLDP & เอกสารเครือข่าย (ฉบับละเอียด)

> อ่านจบแล้วจะ: ใช้ CDP/LLDP หาว่าพอร์ตต่อกับอะไร · วาด topology จากข้อมูลจริง · เข้าใจ LLDP-MED กับ IP phone · รู้ความเสี่ยงและการปิดอย่างเหมาะสม · จัดทำเอกสารเครือข่าย L1/L2/L3 ที่องค์กรต้องมี

---

## 1. Discovery Protocol คืออะไร

โปรโตคอลชั้น Layer 2 ที่อุปกรณ์ **ประกาศข้อมูลตัวเองให้เพื่อนบ้านที่ต่อตรงกัน** (ไม่ข้าม router และไม่ส่งต่อเกิน 1 hop) ทำให้รู้ว่า "พอร์ตนี้ต่อกับอุปกรณ์อะไร พอร์ตไหน"

| | **CDP** (Cisco Discovery Protocol) | **LLDP** (Link Layer Discovery Protocol) |
|---|---|---|
| มาตรฐาน | Cisco proprietary | **IEEE 802.1AB** (ทุกยี่ห้อ, Linux, VMware, Windows Server) |
| ค่าเริ่มต้นบน Cisco | **เปิด** | ปิด (ต้อง `lldp run`) บนหลายรุ่น |
| ส่งทุก / หมดอายุ | 60 วินาที / 180 วินาที (holdtime) | 30 วินาที / 120 วินาที |
| ส่วนขยาย | — | **LLDP-MED** (สำหรับ endpoint เช่น IP phone) |

> 💡 ในเครือข่ายหลายยี่ห้อ ใช้ **LLDP** เป็นหลัก

---

## 2. ข้อมูลที่ได้

```
Switch# show cdp neighbors
Device ID        Local Intrfce     Holdtme    Capability  Platform     Port ID
DIST-SW1         Gig 1/0/49        162         R S I      C9500-48Y4C  Twe 1/0/10
AP-3F-01         Gig 1/0/12        150         T          C9130AXI-S   Gig 0
SEP001122334455  Gig 1/0/5         140         H P M      IP Phone     Port 1

Capability: R=Router S=Switch H=Host I=IGMP P=Phone T=Trans-Bridge(AP) M=Two-port Mac relay
```
```
Switch# show cdp neighbors Gi1/0/49 detail
Device ID: DIST-SW1
  IP address: 10.0.99.2                       ← IP จัดการของเพื่อนบ้าน
Platform: cisco C9500-48Y4C, Capabilities: Router Switch IGMP
Interface: GigabitEthernet1/0/49, Port ID (outgoing port): TwentyFiveGigE1/0/10
Version: Cisco IOS XE Software, Version 17.x.x   ← เวอร์ชัน OS
Native VLAN: 999
Duplex: full
```
```
show lldp neighbors [detail]
show lldp neighbors Gi1/0/49 detail
show cdp / show lldp                 ! สถานะ protocol และ timer
```
**ข้อมูลที่ได้:** ชื่ออุปกรณ์, IP จัดการ, รุ่น/platform, เวอร์ชัน OS, พอร์ตฝั่งตรงข้าม, capability, native VLAN, duplex, (LLDP) system description, VLAN, PoE

---

## 3. ใช้ทำอะไรในงานจริง

1. **ไล่หาว่าพอร์ต uplink ต่อไปที่ไหน** (ใช้ร่วมกับ MAC table หาตำแหน่งเครื่อง — Level 31)
2. **วาด/ตรวจ topology** จากข้อมูลจริง (เอกสารมักไม่ตรงของจริง)
3. **ตรวจการเดินสายหลังติดตั้ง** — เทียบกับ cable plan ว่าต่อตรงพอร์ตตามแบบ
4. **ตรวจความไม่สอดคล้อง:** CDP เตือน **native VLAN mismatch**, **duplex mismatch**
5. **Inventory:** รุ่นและเวอร์ชันของอุปกรณ์ที่ต่ออยู่ (AP, phone)
6. **IP phone รับ voice VLAN และค่า PoE** ผ่าน CDP/LLDP-MED

### LLDP-MED (Media Endpoint Discovery)
ส่วนขยายของ LLDP สำหรับอุปกรณ์ปลายทาง โดยเฉพาะ **IP phone** ยี่ห้อที่ไม่ใช่ Cisco
- แจ้ง **voice VLAN** และ **QoS (DSCP/CoS)** ให้ phone
- เจรจา **PoE** (phone ขอกำลังไฟที่ต้องการ)
- ข้อมูล inventory และ location (สำหรับเบอร์ฉุกเฉิน)

### ฝั่ง Server
- Linux: `lldpd` (`lldpcli show neighbors`) — ดูได้ว่า NIC แต่ละช่องต่อ switch ตัวไหนพอร์ตไหน (มีประโยชน์มากตอนติดตั้ง server)
- VMware vDS/ESXi: เปิด CDP/LLDP บน vSwitch แล้วดูใน vCenter ได้
- Windows Server: ติดตั้ง feature Data Center Bridging/LLDP agent

---

## 4. ความเสี่ยงด้านความปลอดภัย

CDP/LLDP ส่งข้อมูล **รุ่น, เวอร์ชัน OS, IP จัดการ** เป็นข้อความธรรมดา → ผู้โจมตีที่เสียบพอร์ตได้จะรู้ทันทีว่าควรใช้ช่องโหว่ใด

**แนวปฏิบัติ**
- **ปิดบนพอร์ตที่หันไปภายนอก:** ลิงก์ไป ISP/อินเทอร์เน็ต, พอร์ตใน DMZ, พอร์ตที่ต่อกับอุปกรณ์ของบุคคลภายนอก
- **พอร์ตผู้ใช้:** พิจารณาตามความจำเป็น — ถ้ามี IP phone ต้องเปิด (CDP หรือ LLDP-MED); ถ้าไม่มีอาจปิดการส่ง (transmit)
- **ระหว่าง switch ภายใน:** เปิดไว้ (มีประโยชน์ในการดูแล)
```
interface Gi0/0
 description TO-ISP
 no cdp enable
 no lldp transmit
 no lldp receive
! ปิดทั้งเครื่อง
no cdp run
no lldp run
```

---

## 5. เอกสารเครือข่ายที่องค์กรต้องมี

> "ถ้าไม่ได้บันทึกไว้ ก็เท่ากับไม่มีอยู่จริง" — เอกสารที่ดีทำให้แก้ปัญหาเร็วขึ้น ส่งต่องานได้ และผ่านการตรวจสอบ (audit)

### 5.1 L1 — Physical
- **Rack elevation:** อุปกรณ์อยู่ตู้ไหน U ไหน
- **Cable/port mapping:** สายจาก patch panel พอร์ตไหน → switch พอร์ตไหน → โต๊ะ/จุดใด
- **Floor plan:** ตำแหน่งจุด LAN, AP, ตู้ rack
- **Fiber/backbone:** เส้นทางไฟเบอร์ระหว่างอาคาร, ชนิด, จำนวน core
- **Power:** อุปกรณ์ต่อ PDU/UPS ใด

### 5.2 L2 — Data Link
- รายการ VLAN (ID, ชื่อ, หน้าที่)
- Trunk: allowed VLAN, native VLAN
- STP: root bridge ของแต่ละ VLAN/instance
- EtherChannel/MLAG
- แผนภาพ L2 (switch เชื่อมกันอย่างไร พอร์ตไหน)

### 5.3 L3 — Network
- **IP plan / IPAM:** subnet, VLAN, gateway, DHCP scope
- Routing: protocol, area/AS, static route, summary
- แผนภาพ L3 (router/L3 switch/firewall, subnet, VRF)
- NAT, VPN, firewall zone

### 5.4 เอกสารอื่น
- **Inventory:** ชื่อ, รุ่น, serial, OS version, วันหมดประกัน/EoL, สัญญา support
- **Config backup** (อัตโนมัติ เก็บประวัติ)
- **Credentials** (ในระบบจัดการรหัสผ่าน ไม่ใช่ในไฟล์ Excel)
- **Runbook/SOP**, contact/escalation, ข้อมูลวงจร ISP (เลขวงจร, เบอร์แจ้งเสีย)

### 5.5 มาตรฐานการตั้งชื่อ (Naming Convention)
```
 <สถานที่>-<อาคาร/ชั้น>-<ประเภท>-<ลำดับ>
 BKK-HQ-F03-ASW-01     (Access Switch ชั้น 3 สำนักงานใหญ่กรุงเทพ)
 BKK-DC1-CORE-01
 CNX-BR01-FW-01

 Interface description:
 "UPLINK|BKK-HQ-DIST-01|Te1/0/10"
 "USER|F03-A12"  "AP|AP-F03-01"  "SRV|ESXI-01|vmnic0"
```
ชื่อที่มีความหมายช่วยให้อ่าน log, CDP, monitoring เข้าใจทันที

### 5.6 เครื่องมือ
| เครื่องมือ | ใช้ทำ |
|---|---|
| draw.io (diagrams.net), Visio, Lucidchart | แผนภาพ |
| **NetBox / Nautobot** | Source of Truth: DCIM, IPAM, cable, inventory (Level 89) |
| Oxidized / RANCID / Ansible | สำรอง config อัตโนมัติ + diff |
| Wiki (BookStack, Confluence) | Runbook, SOP |
| LibreNMS / Zabbix / NMS | auto-discovery topology จาก CDP/LLDP |

> 🔑 **เอกสารต้องอัปเดตทุกครั้งที่มี change** — ใส่เป็นขั้นตอนบังคับใน change process ไม่เช่นนั้นเอกสารจะล้าสมัยและไม่มีใครเชื่อถือ

---

## 6. ตัวอย่าง: ไล่ topology ด้วย CDP/LLDP (Crawl)

```
 1) เริ่มที่ core: show cdp neighbors → เห็น DIST-A, DIST-B, FW-01
 2) เข้า DIST-A: show cdp neighbors → เห็น ASW-F01, ASW-F02, ASW-F03 ...
 3) ทำซ้ำทุกตัว จดเป็นตาราง: Local device | Local port | Remote device | Remote port
 4) นำตารางไปวาดแผนภาพ (หรือให้สคริปต์ Python + Graphviz วาดให้ — Tier 9)
```

---

## 7. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| CDP/LLDP มองเห็นทั้งเครือข่าย | เห็นเฉพาะเพื่อนบ้านที่ต่อตรง (1 hop) |
| LLDP ใช้ได้เฉพาะ Cisco | CDP คือของ Cisco; LLDP เป็นมาตรฐานทุกยี่ห้อ |
| ปิด CDP ทุกพอร์ตปลอดภัยที่สุด | IP phone ต้องใช้ CDP/LLDP-MED; ควรปิดเฉพาะพอร์ตที่หันออกภายนอก |
| เอกสารทำครั้งเดียวตอนติดตั้ง | ต้องอัปเดตทุก change |

---

## 8. Cheat Sheet

```
CDP (Cisco, เปิดเป็นค่าเริ่มต้น, 60/180s) · LLDP (IEEE 802.1AB, ทุกยี่ห้อ, 30/120s, lldp run)
show cdp neighbors [detail] · show lldp neighbors [detail] · Linux: lldpcli show neighbors
ได้: ชื่อ, IP จัดการ, รุ่น, OS version, พอร์ตปลายทาง, native VLAN, duplex
LLDP-MED: voice VLAN + QoS + PoE สำหรับ IP phone
ปิดที่พอร์ตไป ISP/DMZ/ภายนอก: no cdp enable · no lldp transmit/receive
เอกสาร: L1 (rack, cable, floor) · L2 (VLAN, trunk, STP) · L3 (IPAM, routing) · inventory · config backup
Naming: สถานที่-อาคาร-ประเภท-ลำดับ · interface description มีมาตรฐาน · NetBox = source of truth
```

---

## 9. แบบทดสอบ 10 ข้อ

1. CDP กับ LLDP ต่างกันอย่างไร
2. CDP/LLDP เห็นอุปกรณ์ได้ไกลกี่ hop
3. คำสั่งดู IP และเวอร์ชัน OS ของ switch ที่ต่อกับพอร์ต Gi1/0/49
4. LLDP-MED ช่วย IP phone อย่างไร
5. ทำไมควรปิด CDP/LLDP บนพอร์ตที่ต่อ ISP
6. บน Linux server จะรู้ได้อย่างไรว่า NIC แต่ละช่องต่อ switch พอร์ตไหน
7. เอกสารระดับ L1, L2, L3 มีอะไรบ้าง (อย่างละ 2 ตัวอย่าง)
8. ยกตัวอย่าง naming convention ของ access switch
9. ทำไมเอกสารเครือข่ายจึงมักล้าสมัย แก้อย่างไร
10. CDP แจ้งเตือน native VLAN mismatch บนพอร์ต trunk ควรทำอะไร

<details><summary><b>เฉลย</b></summary>

1. CDP เป็นของ Cisco (เปิดเป็นค่าเริ่มต้น); LLDP เป็นมาตรฐาน IEEE 802.1AB ใช้ได้ทุกยี่ห้อ
2. 1 hop (เฉพาะเพื่อนบ้านที่ต่อตรง)
3. `show cdp neighbors Gi1/0/49 detail` (หรือ `show lldp neighbors Gi1/0/49 detail`)
4. แจ้ง voice VLAN, ค่า QoS และเจรจากำลังไฟ PoE
5. ไม่เปิดเผยรุ่น/เวอร์ชัน OS/IP จัดการให้ภายนอก ซึ่งช่วยผู้โจมตีเลือกช่องโหว่
6. ติดตั้ง `lldpd` แล้วใช้ `lldpcli show neighbors`
7. L1: rack elevation, cable/port mapping, floor plan · L2: VLAN list, trunk/native, STP root · L3: IP plan/IPAM, routing, firewall zone
8. `BKK-HQ-F03-ASW-01`
9. ไม่ได้อัปเดตเมื่อมีการเปลี่ยนแปลง — บังคับให้อัปเดตเอกสารเป็นขั้นตอนหนึ่งของ change process และใช้ source of truth/การ discovery อัตโนมัติ
10. ตรวจและตั้ง native VLAN ให้ตรงกันทั้งสองฝั่ง (เป็น VLAN ที่ไม่ใช้งาน)
</details>

---

➡️ ต่อไป: **Level 40 — L3 Switching & Campus Design**
