# บทเรียน Level 45 — OSPF Single Area (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจการทำงานของ OSPF ทุกขั้น · Router ID · neighbor state 8 ขั้น · DR/BDR · cost และ reference bandwidth · ตั้งค่า OSPFv2/v3 ได้ · แก้ปัญหา neighbor ไม่ขึ้นได้ครบทุกสาเหตุ

---

## 1. OSPF คืออะไร

**OSPF (Open Shortest Path First)** — **link-state IGP มาตรฐานเปิด** ที่นิยมที่สุดในองค์กร (OSPFv2 = IPv4 RFC 2328, **OSPFv3** = IPv6)
- ทุก router ในวง area เดียวกันมี **แผนที่เดียวกัน (LSDB)** แล้วคำนวณเส้นทางสั้นที่สุดเองด้วย **Dijkstra (SPF)**
- **Metric = cost** (คำนวณจาก bandwidth)
- **AD = 110** · IP protocol **89** (ไม่ใช่ TCP/UDP)
- Multicast: **224.0.0.5** (All OSPF routers) · **224.0.0.6** (All DR/BDR)
- Converge เร็ว, รองรับ VLSM/summarization, แบ่ง area ได้ (Level 46), authentication, ECMP

---

## 2. ภาพรวมการทำงาน 4 ขั้น

```
 ① Hello: ค้นหาเพื่อนบ้าน (neighbor) บนแต่ละ interface
 ② Adjacency: แลก LSDB กันจนตรงกัน (Full)
 ③ SPF: แต่ละ router คำนวณต้นไม้เส้นทางสั้นที่สุดโดยมีตัวเองเป็นราก
 ④ ใส่ route ที่ดีที่สุดลง routing table (O)
 เมื่อมีการเปลี่ยนแปลง → ส่ง LSA ใหม่ (flood) → ทุกตัวคำนวณ SPF ใหม่
```

### ชนิดของ Packet ใน OSPF

| Type | ชื่อ | หน้าที่ |
|---|---|---|
| 1 | **Hello** | ค้นหาและรักษาความสัมพันธ์กับเพื่อนบ้าน |
| 2 | DBD (Database Description) | สรุปรายการ LSA ที่มี |
| 3 | LSR (Link State Request) | ขอ LSA ที่ยังไม่มี |
| 4 | LSU (Link State Update) | ส่ง LSA จริง |
| 5 | LSAck | ยืนยันว่าได้รับ LSU |

---

## 3. Router ID (RID)

ตัวระบุของ router ใน OSPF (เขียนแบบ IPv4 32 บิต) — **ต้องไม่ซ้ำ** ในเครือข่าย
**ลำดับการเลือก:**
1. ตั้งเองด้วย `router-id` ✅ **(แนะนำเสมอ)**
2. IP สูงสุดของ **loopback** interface ที่ up
3. IP สูงสุดของ interface ที่ up

> ⚠️ เปลี่ยน router-id แล้วต้อง `clear ip ospf process` จึงจะมีผล (ทำให้ neighbor reset — ทำในช่วง maintenance)

---

## 4. Neighbor States — 8 ขั้น (ต้องจำ ใช้แก้ปัญหา)

```
 Down → Init → 2-Way → ExStart → Exchange → Loading → Full
```

| State | เกิดอะไรขึ้น |
|---|---|
| **Down** | ยังไม่ได้ยิน hello |
| (Attempt) | (เฉพาะ NBMA ที่ตั้ง neighbor เอง) |
| **Init** | ได้รับ hello จากเพื่อนบ้านแล้ว แต่ **ยังไม่เห็น RID ของเราใน hello ของเขา** |
| **2-Way** | เห็นกันทั้งสองทาง (bidirectional) → บน broadcast network จะเลือก DR/BDR ที่ขั้นนี้ |
| **ExStart** | เลือกว่าใครเป็น master/slave สำหรับแลก DBD |
| **Exchange** | แลก DBD (สรุปรายการ LSA) |
| **Loading** | ขอ (LSR) และรับ (LSU) LSA ที่ยังขาด |
| **Full** ✅ | LSDB ตรงกัน — adjacency สมบูรณ์ |

> 📌 บน broadcast network (Ethernet ที่มีหลาย router): router ที่เป็น **DROTHER ด้วยกันจะค้างที่ 2-Way — เป็นเรื่องปกติ** (Full กับ DR/BDR เท่านั้น)

---

## 5. Hello — เงื่อนไขที่ต้องตรงกันจึงเป็น Neighbor ได้

| ต้องตรงกัน | หมายเหตุ |
|---|---|
| **Area ID** | อยู่ area เดียวกันบนลิงก์นั้น |
| **Subnet และ mask** (บน broadcast/P2P ที่ไม่ใช่ unnumbered) | อยู่วงเดียวกัน |
| **Hello / Dead interval** | ค่าเริ่มต้น Ethernet: **10 / 40 วินาที** |
| **Authentication** | ชนิดและ key ตรงกัน |
| **Stub area flag** | เป็น stub เหมือนกัน (Level 46) |
| **MTU** | ไม่ตรงกัน → **ค้างที่ ExStart/Exchange** (ข้อนี้ไม่ได้เช็กใน hello แต่ทำให้แลก DBD ไม่ผ่าน) |
| **Router ID ไม่ซ้ำ** | ซ้ำ → adjacency มีปัญหา |
| Network type | ต่างกันอาจขึ้น Full แต่ route ผิด |

---

## 6. Network Types และ DR/BDR

### ปัญหาบน broadcast network
LAN ที่มี router 5 ตัว ถ้าทุกตัว Full กับทุกตัว = n(n−1)/2 = 10 adjacency และ LSA ถูก flood ซ้ำซ้อนมาก

### DR (Designated Router) / BDR (Backup DR)
- ทุก router (DROTHER) สร้าง Full adjacency **เฉพาะกับ DR และ BDR**
- ส่ง LSA ไปที่ DR/BDR (224.0.0.6) → DR กระจายต่อให้ทุกตัว (224.0.0.5)
- **เลือกจาก:** **OSPF interface priority สูงสุด** (ค่าเริ่มต้น 1, ตั้ง 0 = ไม่ร่วมเลือก) → ถ้าเท่ากัน **Router ID สูงสุด**
- **ไม่มี preemption:** DR ที่เลือกแล้วจะคงอยู่ แม้มี router ที่ priority สูงกว่าเข้ามาภายหลัง (ต้อง clear process)

```
interface Gi0/0
 ip ospf priority 100     ! อยากให้เป็น DR
 ip ospf priority 0       ! ไม่เอาเป็น DR/BDR
```

### Network Types

| Type | DR/BDR | Hello/Dead | ใช้กับ |
|---|---|---|---|
| **Broadcast** | ✅ | 10/40 | Ethernet (ค่าเริ่มต้น) |
| **Point-to-point** | ❌ | 10/40 | serial, tunnel, **ลิงก์ Ethernet ระหว่าง router 2 ตัว** |
| NBMA / Point-to-multipoint | ขึ้นกับชนิด | 30/120 | Frame Relay/DMVPN (ของเก่าและเฉพาะทาง) |

> 💡 **Best practice:** ลิงก์ Ethernet ระหว่าง router/L3 switch **2 ตัว** ให้ตั้ง `ip ospf network point-to-point` → ไม่ต้องเลือก DR, ขึ้น Full เร็วขึ้น, LSDB เล็กลง

---

## 7. Cost และ Reference Bandwidth

**Cost = Reference bandwidth ÷ Interface bandwidth** (ปัดเศษ, ต่ำสุด 1)
- ค่าเริ่มต้น reference = **100 Mbps** → 100M = 1, **1G = 1, 10G = 1, 100G = 1** ❌ (แยกไม่ออก!)

```
router ospf 1
 auto-cost reference-bandwidth 100000     ! หน่วย Mbps = 100 Gbps
! → 100G = 1 · 40G = 2 · 10G = 10 · 1G = 100 · 100M = 1000
```
> ⚠️ ต้องตั้งค่า reference bandwidth **เหมือนกันทุก router** ใน OSPF domain ไม่เช่นนั้น cost จะไม่สอดคล้องกัน

**ปรับ cost ด้วยมือ** (traffic engineering)
```
interface Gi0/2
 ip ospf cost 500           ! ให้เส้นนี้เป็นทางสำรอง
```
Route cost = ผลรวม cost ของ interface **ขาออก** ตลอดเส้นทาง · cost เท่ากันหลายเส้น → **ECMP** (ค่าเริ่มต้น 4 เส้น, `maximum-paths`)

---

## 8. ตั้งค่า OSPFv2 (Cisco)

### วิธี interface (แนะนำ — ชัดเจน)
```
interface Loopback0
 ip address 1.1.1.1 255.255.255.255
 ip ospf 1 area 0
interface GigabitEthernet0/0
 description P2P-TO-R2
 ip address 10.255.0.1 255.255.255.252
 ip ospf network point-to-point
 ip ospf 1 area 0
interface GigabitEthernet0/1
 description LAN-USERS
 ip address 10.0.10.1 255.255.255.0
 ip ospf 1 area 0
!
router ospf 1
 router-id 1.1.1.1
 auto-cost reference-bandwidth 100000
 passive-interface default
 no passive-interface GigabitEthernet0/0
 log-adjacency-changes detail
```
### วิธี network command (ใช้ wildcard mask)
```
router ospf 1
 network 10.255.0.0 0.0.0.3 area 0        ! เปิดบน interface ที่ IP ตรงกับ pattern นี้
 network 10.0.10.0 0.0.0.255 area 0
 network 0.0.0.0 255.255.255.255 area 0   ! ทุก interface (สะดวกแต่ควรระวัง)
```
> คำสั่ง `network` **ไม่ได้ประกาศ prefix ตามที่พิมพ์** แต่เป็นการเลือก interface ที่จะเปิด OSPF แล้ว OSPF ประกาศวงของ interface นั้น
> "1" ใน `router ospf 1` คือ **process ID** มีความหมายเฉพาะในเครื่อง **ไม่จำเป็นต้องตรงกัน** ระหว่าง router

### Authentication
```
interface Gi0/0
 ip ospf authentication message-digest
 ip ospf message-digest-key 1 md5 S3cr3t!
! (IOS-XE รุ่นใหม่แนะนำ key chain + HMAC-SHA)
```

### OSPFv3 (IPv6)
```
ipv6 unicast-routing
router ospfv3 1
 router-id 1.1.1.1                       ! ยังเป็นรูปแบบ IPv4 32 บิต (ต้องตั้งเองถ้าไม่มี IPv4)
interface Gi0/0
 ospfv3 1 ipv6 area 0
! neighbor สื่อสารด้วย link-local address
```

---

## 9. คำสั่งตรวจสอบ

```
show ip ospf neighbor
Neighbor ID  Pri  State        Dead Time  Address      Interface
2.2.2.2        0  FULL/  -     00:00:35   10.255.0.2   Gi0/0     ← P2P (ไม่มี DR)
3.3.3.3        1  FULL/DR      00:00:38   10.0.20.3    Gi0/2
4.4.4.4        1  2WAY/DROTHER 00:00:31   10.0.20.4    Gi0/2     ← ปกติ (DROTHER ด้วยกัน)

show ip ospf interface brief            ! interface, area, cost, state (DR/BDR/P2P), จำนวน neighbor
show ip ospf interface Gi0/0            ! hello/dead, network type, cost, priority, passive?
show ip ospf                            ! router-id, reference bandwidth, จำนวน SPF ที่รัน
show ip ospf database                   ! LSDB
show ip route ospf
show ip protocols
```

---

## 10. แก้ปัญหา OSPF

| อาการ | สาเหตุที่น่าจะเป็น |
|---|---|
| ไม่เห็น neighbor เลย | interface down/passive, OSPF ไม่ได้เปิดบน interface, area ไม่ตรง, subnet ไม่ตรง, hello/dead ไม่ตรง, authentication ไม่ตรง, ACL บล็อก protocol 89/multicast |
| ค้างที่ **Init** | ได้ยินเขาแต่เขาไม่ได้ยินเรา (ทางเดียว) — ACL/firewall บล็อกขาหนึ่ง, unidirectional link |
| ค้างที่ **ExStart/Exchange** | **MTU mismatch** (สาเหตุอันดับหนึ่ง), router ID ซ้ำ |
| ค้างที่ **2-Way** | ปกติถ้าทั้งคู่เป็น DROTHER |
| Full แต่ไม่มี route | network type ไม่ตรงกัน (broadcast ฝั่งหนึ่ง P2P อีกฝั่ง), route ถูก filter, วงไม่ได้ถูกประกาศ |
| Traffic เดินทางไม่ตามที่คาด | reference bandwidth ไม่ตั้ง/ไม่ตรงกัน, cost ถูกปรับ |
| Neighbor ขึ้นลงบ่อย (flap) | ลิงก์ไม่เสถียร, CPU สูง, dead timer สั้นเกิน |
| Log "duplicate router-id" | RID ซ้ำ |

---

## 11. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| Process ID ต้องเหมือนกันทุก router | มีความหมายเฉพาะในเครื่อง ไม่ต้องตรงกัน |
| ค้าง 2-Way เป็นปัญหาเสมอ | ปกติระหว่าง DROTHER |
| DR เปลี่ยนทันทีเมื่อมี router priority สูงกว่าเข้ามา | ไม่มี preemption |
| ค่าเริ่มต้น cost แยก 1G กับ 10G ได้ | ไม่ได้ (ทั้งคู่ = 1) ต้องปรับ reference bandwidth |
| `network` command ประกาศ prefix ตามที่พิมพ์ | เลือก interface ที่จะเปิด OSPF |

---

## 12. Cheat Sheet

```
OSPF = link state · Dijkstra SPF · metric cost · AD 110 · IP proto 89 · 224.0.0.5 / .6
RID: router-id > loopback สูงสุด > interface สูงสุด (ตั้งเองเสมอ)
States: Down → Init → 2-Way → ExStart → Exchange → Loading → Full
Neighbor ต้องตรง: area, subnet/mask, hello/dead (10/40), auth, stub flag, MTU (ExStart!)
DR/BDR: priority สูงสุด → RID สูงสุด · ไม่มี preemption · DROTHER ค้าง 2-Way ปกติ
ลิงก์ router 2 ตัว: ip ospf network point-to-point
Cost = ref BW / BW · ตั้ง auto-cost reference-bandwidth 100000 ทุกตัว
ip ospf 1 area 0 (interface) · passive-interface default · log-adjacency-changes
show ip ospf neighbor / interface brief / database · show ip route ospf
```

---

## 13. แบบทดสอบ 10 ข้อ

1. OSPF ใช้อัลกอริทึมใด และ metric คืออะไร
2. Router ID เลือกจากอะไรตามลำดับ
3. เรียง neighbor state ทั้งหมด
4. Neighbor ค้างที่ ExStart/Exchange สาเหตุที่พบบ่อยที่สุดคืออะไร
5. สิ่งที่ต้องตรงกันจึงเป็น neighbor ได้ (5 ข้อ)
6. DR/BDR เลือกอย่างไร มี preemption หรือไม่
7. ทำไมควรตั้ง `ip ospf network point-to-point` บนลิงก์ Ethernet ระหว่าง router 2 ตัว
8. ค่าเริ่มต้น reference bandwidth เท่าไร มีปัญหาอะไร
9. ตั้ง reference 100000 แล้ว cost ของลิงก์ 10G และ 1G เป็นเท่าไร
10. Process ID ใน `router ospf 10` ต้องตรงกันกับ neighbor หรือไม่

<details><summary><b>เฉลย</b></summary>

1. Dijkstra (SPF); metric = cost
2. ตั้งเองด้วย router-id → IP สูงสุดของ loopback ที่ up → IP สูงสุดของ interface ที่ up
3. Down → Init → 2-Way → ExStart → Exchange → Loading → Full
4. MTU mismatch
5. Area ID, subnet/mask, hello/dead interval, authentication, stub flag (+ MTU, RID ไม่ซ้ำ)
6. Interface priority สูงสุด ถ้าเท่ากัน Router ID สูงสุด — ไม่มี preemption
7. ไม่ต้องเลือก DR/BDR ขึ้น Full เร็วขึ้น และลด LSA (type 2)
8. 100 Mbps — ลิงก์ 100M ขึ้นไปได้ cost 1 เท่ากันหมด แยกความเร็วไม่ได้
9. 10G = 10, 1G = 100
10. ไม่ต้อง — มีความหมายเฉพาะในเครื่อง
</details>

---

➡️ ต่อไป: **Level 46 — OSPF Multi-Area & LSA**
