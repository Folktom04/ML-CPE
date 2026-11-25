# บทเรียน Level 35 — Spanning Tree Protocol (STP 802.1D) (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจว่าทำไม L2 loop ร้ายแรง · STP เลือก Root Bridge, Root Port, Designated Port, Blocked Port อย่างไร (คำนวณเองได้) · รู้ port states และเวลา converge · กำหนด root bridge ให้ถูกที่ · อ่าน `show spanning-tree`

---

## 1. ปัญหา: L2 Loop

องค์กรต่อ switch หลายเส้นเพื่อสำรอง (redundancy) แต่ใน Layer 2 การมีเส้นทางวนก่อให้เกิดหายนะ เพราะ **Ethernet frame ไม่มี TTL** (ต่างจาก IP) — frame จะวนไม่สิ้นสุด

```
        [SW1]────────[SW2]
           \          /
            \        /
             [ SW3 ]
```
ถ้ามี broadcast 1 frame (เช่น ARP) เข้าวง:
1. **Broadcast storm** — frame ถูก flood และทวีคูณวนไปเรื่อย ๆ ใช้ bandwidth 100%, CPU switch พุ่ง, เครือข่ายล่มทั้งหมดภายในไม่กี่วินาที
2. **MAC table instability (MAC flapping)** — switch เห็น MAC เดียวกันมาจากหลายพอร์ตสลับกัน
3. **Duplicate frames** — ปลายทางได้รับข้อมูลเดิมหลายชุด

**STP (Spanning Tree Protocol, IEEE 802.1D)** แก้ด้วยการ **block พอร์ตบางพอร์ต** ให้เหลือโครงสร้างแบบต้นไม้ (ไม่มีวง) และ **เปิดพอร์ตที่ block ไว้อัตโนมัติเมื่อเส้นหลักเสีย**

---

## 2. BPDU และ Bridge ID

Switch แลกข้อมูล STP กันด้วย **BPDU (Bridge Protocol Data Unit)** ส่งทุก **2 วินาที** (hello time) ไปยัง multicast MAC `01:80:C2:00:00:00`

**Bridge ID (BID) = Priority + MAC address**
```
 Bridge ID (8 ไบต์)
 ┌──────────────────┬─────────────────────┐
 │ Priority (4 บิต) + Extended System ID   │  MAC Address (48 บิต)
 │   = VLAN ID (12 บิต)                    │
 └──────────────────┴─────────────────────┘
 Priority ค่าเริ่มต้น 32768 · ตั้งได้เป็นผลคูณของ 4096 (0, 4096, 8192 ... 61440)
 BID ของ VLAN 10 = 32768 + 10 = 32778
```
**ยิ่งค่า BID ต่ำยิ่งชนะ**

---

## 3. STP ทำงาน 4 ขั้นตอน

### ขั้นที่ 1: เลือก **Root Bridge** (1 ตัวทั้งเครือข่าย ต่อ VLAN)
- switch ที่มี **Bridge ID ต่ำที่สุด** (priority ต่ำสุด ถ้าเท่ากันดู MAC ต่ำสุด)
- **ทุกพอร์ตของ Root Bridge เป็น Designated Port (forwarding)**

### ขั้นที่ 2: เลือก **Root Port (RP)** บน switch ที่ไม่ใช่ root (ตัวละ 1 พอร์ต)
- พอร์ตที่มี **Root Path Cost ต่ำที่สุด** ไปถึง root (ผลรวม cost ของลิงก์ตลอดทาง)
- ถ้าเท่ากัน tie-breaker: (1) Bridge ID ของเพื่อนบ้านที่ต่ำกว่า → (2) Port priority ของเพื่อนบ้าน → (3) Port number ของเพื่อนบ้าน

### ขั้นที่ 3: เลือก **Designated Port (DP)** บนทุก segment (1 พอร์ตต่อลิงก์)
- ในแต่ละลิงก์ พอร์ตของ switch ที่มี **cost ไป root ต่ำกว่า** เป็น DP
- เท่ากัน → switch ที่ BID ต่ำกว่าชนะ

### ขั้นที่ 4: พอร์ตที่เหลือ → **Blocked (Non-designated / Alternate)**
- ไม่ส่งข้อมูลผู้ใช้ แต่ยังรับ BPDU เพื่อเฝ้าดู

### Path Cost (ต่อลิงก์)

| ความเร็ว | Short (802.1D-1998, Cisco default) | Long (802.1t) |
|---|---|---|
| 10 Mbps | 100 | 2,000,000 |
| 100 Mbps | 19 | 200,000 |
| **1 Gbps** | **4** | 20,000 |
| **10 Gbps** | **2** | 2,000 |
| 100 Gbps | — (ใช้ long) | 200 |

---

## 4. ตัวอย่างคำนวณ (ต้องทำได้)

```
           SW1 (Priority 32768, MAC 0000.0000.0001)
          Gi0/1 ── 1G ── Gi0/1  SW2 (32768, MAC ...0002)
          Gi0/2               Gi0/2
            │ 1G                │ 1G
          Gi0/1 ── SW3 (32768, MAC ...0003) ─ Gi0/2
```
**① Root Bridge:** priority เท่ากัน → MAC ต่ำสุด = **SW1** → Gi0/1, Gi0/2 ของ SW1 = **DP**

**② Root Port:**
- SW2: ทางตรงผ่าน Gi0/1 cost 4 · ทางอ้อมผ่าน SW3 cost 4+4 = 8 → **RP = Gi0/1**
- SW3: ทางตรงผ่าน Gi0/1 cost 4 → **RP = Gi0/1**

**③ ลิงก์ SW2–SW3 (Gi0/2 ทั้งคู่):** cost ไป root ของ SW2 = 4, ของ SW3 = 4 → เท่ากัน → BID ต่ำกว่า = SW2 → **SW2 Gi0/2 = DP**

**④ SW3 Gi0/2 = Blocked** ✅ วงถูกตัดที่จุดนี้

```
            [SW1 ROOT]
            DP/      \DP
           RP/        \RP
         [SW2]──DP──X──[SW3]    X = blocked
```

---

## 5. Port States ของ 802.1D

| State | รับ BPDU | ส่ง BPDU | เรียน MAC | ส่งข้อมูล | ระยะเวลา |
|---|---|---|---|---|---|
| **Blocking** | ✅ | ❌ | ❌ | ❌ | (max age 20 วินาที เมื่อมีการเปลี่ยนแปลงทางอ้อม) |
| **Listening** | ✅ | ✅ | ❌ | ❌ | **15 วินาที** (forward delay) |
| **Learning** | ✅ | ✅ | ✅ | ❌ | **15 วินาที** |
| **Forwarding** | ✅ | ✅ | ✅ | ✅ | — |
| Disabled | ❌ | ❌ | ❌ | ❌ | (shutdown) |

**Timer:** Hello 2 วินาที · Forward Delay 15 วินาที · Max Age 20 วินาที

→ **802.1D converge ช้า 30–50 วินาที** (listening + learning = 30 วิ, + max age 20 วิ ถ้าเส้นที่เสียอยู่ทางอ้อม)
→ PC เสียบสายแล้วรอ ~30 วินาทีก่อนใช้งานได้ (DHCP timeout!) — แก้ด้วย **PortFast** และ **RSTP** (Level 36)

---

## 6. Topology Change (TCN)

เมื่อ topology เปลี่ยน (ลิงก์ up/down) switch ส่ง **TCN BPDU** ไปหา root → root แจ้งทุกตัวให้ **ลด MAC aging เหลือ 15 วินาที** ชั่วคราว เพื่อเรียนรู้ MAC ใหม่ตามเส้นทางใหม่
- TCN บ่อย ๆ = มีพอร์ตขึ้นลงอยู่เรื่อย ๆ (เช่น PC เปิดปิดบนพอร์ตที่ไม่ได้ตั้ง PortFast) → MAC table ถูกล้างบ่อย → unknown unicast flooding
```
show spanning-tree detail | include ieee|occurr|from|is exec
! ดูว่า topology change เกิดกี่ครั้ง ล่าสุดเมื่อไร มาจากพอร์ตไหน
```

---

## 7. PVST+ และการกำหนด Root Bridge

- **Cisco PVST+ (Per-VLAN Spanning Tree):** รัน STP **แยกต่อ VLAN** → แต่ละ VLAN มี root ของตัวเองได้ → ทำ **load balancing** ได้ (VLAN คู่ root ที่ SW1, VLAN คี่ root ที่ SW2)
- **มาตรฐาน 802.1D/802.1w เดิม:** STP เดียวทุก VLAN (CST)

### ⚠️ ต้องกำหนด Root Bridge เอง
ถ้าปล่อยค่าเริ่มต้น priority เท่ากันหมด → switch ที่ **MAC ต่ำสุด** (มักเป็น **รุ่นเก่าที่สุด**) จะเป็น root → traffic ไหลผ่าน switch เก่าที่ช้าที่สุด ซึ่งอาจอยู่ปลายเครือข่าย

```
! ที่ Core/Distribution ตัวหลัก
spanning-tree vlan 1-4094 priority 4096        ! หรือ spanning-tree vlan 1-4094 root primary
! ที่ตัวสำรอง
spanning-tree vlan 1-4094 priority 8192        ! หรือ root secondary
```
> `root primary` เป็น macro ที่คำนวณ priority ให้ต่ำกว่า root ปัจจุบัน ณ ตอนที่สั่ง — การตั้ง priority เป็นตัวเลขชัดเจนคาดเดาได้กว่า

**หลักการ:** Root = core/distribution ที่อยู่ศูนย์กลาง และ **ให้ตรงกับ HSRP/VRRP active ของ VLAN นั้น** (Level 50) เพื่อให้ L2 path และ L3 path ไปทางเดียวกัน

---

## 8. อ่าน `show spanning-tree`

```
Switch# show spanning-tree vlan 10
VLAN0010
  Spanning tree enabled protocol rstp
  Root ID    Priority    4106
             Address     0011.2233.4455
             Cost        4
             Port        49 (GigabitEthernet1/0/49)      ← root port ของ switch นี้
  Bridge ID  Priority    32778  (priority 32768 sys-id-ext 10)
             Address     00aa.bbcc.dd01

Interface           Role Sts Cost      Prio.Nbr Type
------------------- ---- --- --------- -------- ----------
Gi1/0/1             Desg FWD 4         128.1    P2p Edge      ← พอร์ตผู้ใช้ (PortFast)
Gi1/0/49            Root FWD 4         128.49   P2p
Gi1/0/50            Altn BLK 4         128.50   P2p           ← สำรอง (blocked)
```
- ถ้าเห็น **"This bridge is the root"** แปลว่า switch นี้คือ root ของ VLAN นี้ — ตรวจว่าตั้งใจไว้หรือไม่
```
show spanning-tree root
show spanning-tree summary
show spanning-tree interface Gi1/0/50 detail
```

---

## 9. แก้ปัญหา STP

| อาการ | สาเหตุ / ตรวจ |
|---|---|
| เครือข่ายล่มทั้ง VLAN, ไฟ switch กระพริบถี่, CPU สูง | **Loop/broadcast storm** — มีคนต่อสายวน/hub/switch บ้าน, STP ถูกปิด, BPDU filter ผิดที่ → ไล่ปิดพอร์ต, ดู MAC flapping log |
| PC เสียบสายแล้วรอ 30 วินาทีกว่าจะได้ IP | ไม่มี PortFast |
| Traffic อ้อมไปทาง switch เก่า | Root bridge ไม่ได้กำหนด |
| TCN บ่อยมาก | พอร์ตผู้ใช้ไม่มี PortFast, ลิงก์ flap |
| ลิงก์สำรองไม่ทำงานเมื่อเส้นหลักขาด | ตรวจ STP state, unidirectional link (Loop Guard/UDLD — Level 36) |

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| STP ทำให้ใช้ลิงก์สำรองพร้อมกันได้ | STP **block** ลิงก์สำรอง (ใช้ได้เมื่อหลักเสีย) — ต้องการใช้พร้อมกันใช้ EtherChannel/MLAG |
| Root bridge เลือกจาก switch ที่แรงที่สุด | เลือกจาก **BID ต่ำสุด** — ต้องตั้งเอง |
| ปิด STP แล้วเครือข่ายเร็วขึ้น | เสี่ยง loop ล่มทั้งเครือข่าย ห้ามปิด |
| Priority ตั้งเป็นเลขอะไรก็ได้ | ต้องเป็นผลคูณของ 4096 |

---

## 11. Cheat Sheet

```
L2 loop → broadcast storm + MAC flapping + duplicate (Ethernet ไม่มี TTL)
BPDU ทุก 2 วิ · BID = priority (32768 + VLAN) + MAC · ต่ำสุดชนะ
ขั้นตอน: Root Bridge (BID ต่ำสุด) → Root Port (cost ต่ำสุดไป root) → Designated Port (ต่อลิงก์) → ที่เหลือ Block
Cost: 1G = 4 · 10G = 2 · 100M = 19
States: Blocking → Listening 15s → Learning 15s → Forwarding (converge 30-50s)
PVST+ = STP ต่อ VLAN · ตั้ง root เอง: priority 4096 (primary) / 8192 (secondary) ที่ core
Root ควรตรงกับ HSRP active · show spanning-tree [vlan X | root | summary]
```

---

## 12. แบบทดสอบ 10 ข้อ

1. ทำไม L2 loop ร้ายแรงกว่า L3 loop
2. Bridge ID ประกอบด้วยอะไร และ BID ของ VLAN 20 ที่ priority ค่าเริ่มต้นคือเท่าไร
3. เกณฑ์เลือก Root Bridge
4. Root Port เลือกอย่างไร
5. Path cost ของลิงก์ 1 Gbps และ 10 Gbps (short method)
6. เรียง port states ของ 802.1D และบอกเวลาที่ใช้ converge
7. ทำไมต้องกำหนด root bridge เอง
8. PVST+ ช่วย load balancing ได้อย่างไร
9. switch 3 ตัว priority เท่ากัน MAC ...01, ...02, ...03 ต่อเป็นสามเหลี่ยมด้วย 1G ทั้งหมด พอร์ตใดถูก block
10. เครือข่ายล่มกะทันหัน CPU switch 100% มี log MAC flapping สงสัยอะไร แก้เบื้องต้นอย่างไร

<details><summary><b>เฉลย</b></summary>

1. Ethernet frame ไม่มี TTL จึงวนไม่สิ้นสุด เกิด broadcast storm ทันที ส่วน IP มี TTL ที่ทำให้ packet หมดอายุ
2. Priority (รวม extended system ID = VLAN) + MAC — 32768 + 20 = 32788
3. Bridge ID ต่ำสุด (priority ก่อน ถ้าเท่ากันดู MAC ต่ำสุด)
4. พอร์ตที่มี root path cost ต่ำสุด ถ้าเท่ากันดู BID ของเพื่อนบ้าน → port priority → port number
5. 1G = 4, 10G = 2
6. Blocking → Listening (15 วิ) → Learning (15 วิ) → Forwarding รวม 30–50 วินาที
7. ไม่ตั้ง switch ที่ MAC ต่ำสุด (มักเป็นรุ่นเก่า/อยู่ปลายเครือข่าย) จะเป็น root ทำให้ traffic ไหลผิดทาง
8. ตั้ง root ของแต่ละ VLAN ไว้คนละ switch ทำให้ VLAN ต่างกลุ่มใช้ลิงก์ต่างกัน
9. Root = ...01; ...02 และ ...03 มี root port ตรงไป ...01; ลิงก์ ...02–...03 cost เท่ากัน ...02 BID ต่ำกว่าได้ DP → พอร์ตของ ...03 บนลิงก์นั้นถูก block
10. L2 loop/broadcast storm — หาพอร์ตที่ทำให้เกิดวง (MAC flapping log, พอร์ตที่ broadcast สูง) แล้ว shutdown, ตรวจว่า STP เปิดอยู่และมี BPDU Guard
</details>

---

➡️ ต่อไป: **Level 36 — RSTP, MST & STP Toolkit**
