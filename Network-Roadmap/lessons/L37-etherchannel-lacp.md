# บทเรียน Level 37 — EtherChannel / Link Aggregation (LACP) (ฉบับละเอียด)

> อ่านจบแล้วจะ: รวมหลายลิงก์เป็นลิงก์เดียวได้ · เลือก LACP/PAgP/static · ตั้งค่าทั้ง L2 และ L3 port-channel · เข้าใจ load-balancing hash และข้อจำกัด · รู้จัก MLAG/vPC/StackWise Virtual · แก้ปัญหา bundle ไม่ขึ้น

---

## 1. ปัญหาที่ EtherChannel แก้

ต่อ switch 2 ตัวด้วยสาย 2 เส้นเพื่อเพิ่ม bandwidth และสำรอง → **STP จะ block เส้นหนึ่ง** (เพราะเป็นวง) ได้ใช้จริงแค่เส้นเดียว

**EtherChannel (Link Aggregation, Port-Channel, LAG, Bond, Team)** = รวมหลายพอร์ตเป็น **ลิงก์เสมือนเส้นเดียว**
- STP มองเป็น **1 ลิงก์** → ไม่ block → **ใช้ทุกเส้นพร้อมกัน**
- เส้นใดขาด → traffic ย้ายไปเส้นที่เหลือภายในเสี้ยววินาที (ไม่ต้องรอ STP)

```
 ก่อน:  [SW1]═══Gi1═══[SW2]    STP block Gi2 → ได้ 1 Gbps
            ───Gi2─X─

 หลัง:  [SW1]═╦═Gi1═╦═[SW2]    Port-channel 1 = 2 Gbps (รวม), สำรองกัน
              ╚═Gi2═╝
```
ใช้ระหว่าง switch↔switch, switch↔server (NIC bonding/teaming), switch↔firewall, switch↔storage/hypervisor

---

## 2. Protocol สำหรับสร้าง Bundle

| | **LACP** (IEEE 802.3ad / 802.1AX) ⭐ | PAgP | Static (On) |
|---|---|---|---|
| มาตรฐาน | เปิด (ทุกยี่ห้อ, Linux, VMware vDS, Windows) | Cisco เท่านั้น | — |
| เจรจา/ตรวจสอบ | ✅ ตรวจว่าอีกฝั่งพร้อมและต่อถูกคู่ | ✅ | ❌ ไม่ตรวจอะไรเลย |
| Mode | **active** (เริ่มเจรจา) / **passive** (รอ) | desirable / auto | on |
| จำนวนลิงก์ | สูงสุด 16 (active 8 + standby 8) | 8 | 8 |

**การจับคู่ LACP**
| ฝั่ง A \ ฝั่ง B | active | passive |
|---|---|---|
| **active** | ✅ | ✅ |
| **passive** | ✅ | ❌ (ไม่มีใครเริ่ม) |

> **Best practice:** ใช้ **LACP active ทั้งสองฝั่ง** หลีกเลี่ยง static `on` เพราะถ้าเสียบสายผิดคู่หรืออีกฝั่งยังไม่ได้ตั้งค่า อาจเกิด loop/traffic หายโดยไม่มีอะไรเตือน

---

## 3. เงื่อนไข: ทุกพอร์ตใน Bundle ต้องเหมือนกัน

- **Speed และ duplex** เท่ากัน
- **Switchport mode** เดียวกัน (access ทั้งหมด หรือ trunk ทั้งหมด)
- **Access VLAN** เดียวกัน / **allowed VLAN + native VLAN** เดียวกัน (กรณี trunk)
- ไม่เป็น SPAN destination, ไม่ได้ตั้ง port security ต่างกัน

ถ้าไม่ตรง พอร์ตนั้นจะถูก **suspended (s)** ไม่เข้า bundle

> 💡 **เคล็ดลับ:** ตั้งค่า (VLAN/trunk) ที่ **interface port-channel** — ค่าจะถูกส่งลงไปยังพอร์ตสมาชิกให้ตรงกันเอง และแก้ไขภายหลังที่ port-channel เท่านั้น

---

## 4. ตั้งค่า L2 EtherChannel (Cisco)

```
! ทั้งสองฝั่งทำเหมือนกัน
interface range GigabitEthernet1/0/49 - 50
 description UPLINK-TO-DIST
 channel-group 1 mode active              ! สร้าง Port-channel1 อัตโนมัติ (LACP active)
!
interface Port-channel1
 description UPLINK-TO-DIST
 switchport mode trunk
 switchport trunk allowed vlan 10,20,30,99
 switchport trunk native vlan 999
!
port-channel load-balance src-dst-ip      ! (global) วิธีกระจาย traffic
```

### L3 EtherChannel (routed port-channel)
```
interface range Te1/1/1 - 2
 no switchport
 channel-group 10 mode active
interface Port-channel10
 no switchport
 ip address 10.255.0.1 255.255.255.252
```

### ตรวจสอบ
```
Switch# show etherchannel summary
Flags:  D - down        P - bundled in port-channel
        I - stand-alone s - suspended
        R - Layer3      S - Layer2
        U - in use      ...
Group  Port-channel  Protocol    Ports
------+-------------+-----------+------------------------------
1      Po1(SU)         LACP      Gi1/0/49(P)   Gi1/0/50(P)      ← ✅ ปกติ
2      Po2(SD)         LACP      Gi1/0/51(I)   Gi1/0/52(s)      ← ❌ มีปัญหา

show etherchannel port-channel
show lacp neighbor                    ! ฝั่งตรงข้ามเห็นเราไหม (system ID, port, state)
show interfaces Port-channel1
```
| Flag | ความหมาย |
|---|---|
| **SU / RU** | L2 / L3 port-channel ใช้งานอยู่ ✅ |
| **P** | พอร์ตอยู่ใน bundle ✅ |
| **I** | stand-alone — ไม่ได้รับ LACP จากอีกฝั่ง (ทำงานเป็นพอร์ตเดี่ยว) |
| **s** | suspended — ค่าไม่ตรงกับพอร์ตอื่น |
| **D** | down |

---

## 5. Load Balancing — สิ่งที่ต้องเข้าใจให้ถูก

EtherChannel **ไม่ได้แบ่งทีละ packet** แต่ใช้ **hash** ของข้อมูลใน header (MAC/IP/port) เลือกว่า **flow ไหนไปเส้นไหน** — packet ของ flow เดียวกันไปเส้นเดิมเสมอ (เพื่อไม่ให้ลำดับสลับ)

```
 hash(src-dst-ip) ของ flow A → ลิงก์ 1
 hash(src-dst-ip) ของ flow B → ลิงก์ 2
 hash(src-dst-ip) ของ flow C → ลิงก์ 1
```

**ผลที่ตามมา**
- 🔑 **1 flow ใช้ได้สูงสุดแค่ความเร็วของ 1 ลิงก์** (ไฟล์ใหญ่ไฟล์เดียวผ่าน 2×1G ได้แค่ ~1G)
- bandwidth รวมได้เมื่อมี **หลาย flow** และ hash กระจายดี
- ถ้า hash เลือกข้อมูลที่หลากหลายน้อย (เช่น src-mac ทั้งที่ traffic ทั้งหมดมาจาก router ตัวเดียว) → ทุก flow ไปเส้นเดียว (polarization)

| วิธี | ใช้เมื่อ |
|---|---|
| src-mac / dst-mac | L2 ล้วน (ไม่ค่อยดี) |
| **src-dst-ip** | ทั่วไป (ค่าที่นิยม) |
| **src-dst-port / L4** (`src-dst-mixed-ip-port`) | มี flow จำนวนมากจาก IP คู่เดียวกัน (เช่น server ↔ storage) กระจายดีที่สุด |

```
show etherchannel load-balance
port-channel load-balance src-dst-mixed-ip-port    ! (ชื่อคำสั่งแต่ละรุ่นต่างกัน)
```
- **จำนวนลิงก์แนะนำเป็น 2, 4, 8** เพื่อให้ hash กระจายสม่ำเสมอ (ขึ้นกับ hardware)

---

## 6. EtherChannel ข้าม 2 Switch: MLAG / vPC / Stack

EtherChannel ปกติต้องจบที่ switch ตัวเดียว → switch ตัวนั้นเป็น **single point of failure**

**Multi-chassis LAG** ให้ปลายด้านหนึ่งของ bundle **กระจายไป 2 switch** โดยอุปกรณ์ปลายทางยังเห็นเป็น port-channel เดียว

```
          [CORE-1]════peer-link════[CORE-2]
              ╲                     ╱
               ╲   Port-channel    ╱
                ╲═══════╦════════╱
                    [ACCESS / SERVER]   ← เห็นเป็น LACP bundle เดียว, ไม่มี STP block
```
| เทคโนโลยี | ผู้ผลิต | ลักษณะ |
|---|---|---|
| **StackWise / Stacking** | Cisco Catalyst, หลายยี่ห้อ | หลาย switch เป็น **control plane เดียว** (จัดการเป็นเครื่องเดียว) |
| **StackWise Virtual / VSS** | Cisco Catalyst 9000/6500 | 2 chassis เป็น control plane เดียว |
| **vPC** | Cisco Nexus | 2 switch **control plane แยกกัน** ประสานผ่าน peer-link + peer-keepalive |
| **MLAG** | Arista, Aruba (VSX), Dell, Juniper (MC-LAG), Cumulus | หลักการเดียวกับ vPC |
| **Virtual Chassis / VSF / IRF** | Juniper / Aruba-HPE / H3C | รวมเป็นเครื่องเดียว |

**ข้อควรรู้**
- **Peer-link** ต้องมีความจุพอ (ปกติเป็น port-channel เส้นใหญ่) และ **peer-keepalive** ควรวิ่งคนละเส้นทาง (เช่น management) เพื่อป้องกัน **split-brain**
- Control plane เดียว (stack) จัดการง่าย แต่ upgrade software อาจกระทบทั้ง stack · Control plane แยก (vPC/MLAG) upgrade ทีละตัวได้ แต่ config ต้องสอดคล้องกันทั้งคู่
- ใช้มากใน **campus core** (access dual-homed ไป core 2 ตัว) และ **data center** (server dual-homed ไป ToR 2 ตัว)

---

## 7. ฝั่ง Server: NIC Teaming / Bonding

| Server | การตั้งค่า | Switch ต้องเป็น |
|---|---|---|
| Linux bond mode 4 (802.3ad) | LACP | **LACP port-channel** |
| Linux bond mode 1 (active-backup) | — | **พอร์ตธรรมดา** (ห้ามทำ port-channel) |
| VMware vSS: Route based on IP hash | static | **static EtherChannel (on)** |
| VMware vDS: LACP | LACP | LACP |
| VMware: Route based on originating port / LBT | — | **พอร์ตธรรมดา** (นิยมที่สุด ไม่ต้องตั้ง switch) |
| Windows: Switch Independent | — | พอร์ตธรรมดา |
| Windows: LACP | LACP | LACP |

> ⚠️ **ฝั่ง server กับ switch ต้องตั้งให้ตรงกัน** — server ใช้แบบ switch-independent แต่ switch ทำ port-channel (หรือกลับกัน) → MAC flapping, traffic หาย

---

## 8. แก้ปัญหา EtherChannel

| อาการ | สาเหตุ |
|---|---|
| พอร์ตเป็น **(I) stand-alone** | อีกฝั่งไม่ได้ตั้ง LACP, passive ทั้งคู่, เสียบผิดพอร์ต/ผิดอุปกรณ์ |
| พอร์ตเป็น **(s) suspended** | speed/duplex/VLAN/trunk/native ไม่ตรงกับพอร์ตอื่น |
| Port-channel ขึ้นแต่ใช้ได้แค่เส้นเดียว | hash ไม่กระจาย (flow เดียว/ข้อมูลไม่หลากหลาย) → เปลี่ยน load-balance method |
| ตั้ง static `on` ฝั่งเดียว | loop หรือ traffic หาย → ใช้ LACP |
| MAC flapping บนพอร์ต server | teaming ของ server ไม่ตรงกับ switch |
| vPC/MLAG ไม่ขึ้น | peer-link/keepalive, config consistency check ไม่ผ่าน |

---

## 9. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| 2×1G = ดาวน์โหลดไฟล์เดียวได้ 2 Gbps | 1 flow ได้สูงสุด 1 ลิงก์ |
| passive + passive ทำงานได้ | ต้องมีอย่างน้อยฝั่งหนึ่งเป็น active |
| แก้ VLAN ที่พอร์ตสมาชิกได้ตามสะดวก | ควรแก้ที่ interface port-channel เพื่อให้ทุกพอร์ตตรงกัน |
| EtherChannel ข้าม 2 switch ได้เสมอ | ต้องใช้ stack/StackWise Virtual/vPC/MLAG |

---

## 10. Cheat Sheet

```
EtherChannel = รวมหลายพอร์ตเป็นลิงก์เดียว · STP เห็น 1 ลิงก์ · สำรองอัตโนมัติ
LACP (มาตรฐาน) active/passive · PAgP (Cisco) · on (static ไม่แนะนำ)
active+active ✅ · active+passive ✅ · passive+passive ❌
พอร์ตต้องตรงกัน: speed/duplex/mode/VLAN/native · ตั้งค่าที่ interface Port-channel
channel-group N mode active · show etherchannel summary (SU + P = ดี, I/s = ปัญหา) · show lacp neighbor
Hash ต่อ flow → 1 flow ≤ 1 ลิงก์ · src-dst-ip / src-dst-port
Multi-chassis: Stack/StackWise Virtual (control plane เดียว) · vPC/MLAG (แยก + peer-link + keepalive)
Server teaming ต้องตรงกับ switch (LACP ↔ LACP, switch-independent ↔ พอร์ตธรรมดา)
```

---

## 11. แบบทดสอบ 10 ข้อ

1. ทำไมต้องใช้ EtherChannel แทนการต่อสายหลายเส้นเฉย ๆ
2. LACP ต่างจาก PAgP และ static on อย่างไร
3. LACP passive ทั้งสองฝั่งจะเกิด bundle หรือไม่
4. พอร์ตใน bundle ต้องตรงกันในเรื่องใดบ้าง
5. `show etherchannel summary` แสดง Gi1/0/52(s) หมายความว่าอะไร
6. ทำไมการคัดลอกไฟล์เดียวผ่าน port-channel 2×10G ได้เพียง ~10G
7. เลือก load-balance method แบบใดเมื่อ traffic ส่วนใหญ่วิ่งระหว่าง server กับ storage คู่เดียว
8. vPC/MLAG แก้ปัญหาอะไร องค์ประกอบสำคัญคืออะไร
9. Server Linux ใช้ bond mode 1 พอร์ต switch ควรตั้งอย่างไร
10. ทำไมไม่แนะนำ static mode on

<details><summary><b>เฉลย</b></summary>

1. ถ้าไม่รวมเป็น bundle STP จะ block เส้นสำรอง ได้ใช้แค่เส้นเดียว; EtherChannel ใช้ทุกเส้นพร้อมกันและสำรองอัตโนมัติ
2. LACP เป็นมาตรฐานเปิดและเจรจา/ตรวจสอบ; PAgP เป็นของ Cisco; static on ไม่เจรจาและไม่ตรวจอะไร
3. ไม่เกิด
4. Speed, duplex, switchport mode, access VLAN หรือ allowed/native VLAN (trunk)
5. Suspended — ค่าของพอร์ตไม่ตรงกับพอร์ตอื่นใน bundle
6. Hash ส่ง flow เดียวกันไปลิงก์เดียวเสมอ
7. แบบที่รวม L4 port (src-dst-port / mixed-ip-port) เพื่อกระจายหลาย flow ระหว่าง IP คู่เดียวกัน
8. ให้ bundle เดียวกระจายไป 2 switch ไม่มี SPOF และไม่ถูก STP block — peer-link และ peer-keepalive (แยกเส้นทาง)
9. พอร์ตธรรมดา (access/trunk ตาม VLAN) ไม่ทำ port-channel
10. ไม่ตรวจว่าอีกฝั่งพร้อม/ต่อถูก ถ้าตั้งฝั่งเดียวหรือเสียบผิดอาจเกิด loop หรือ traffic หายโดยไม่มีการเตือน
</details>

---

➡️ ต่อไป: **Level 38 — Port Security & Access Control บน Switch**
