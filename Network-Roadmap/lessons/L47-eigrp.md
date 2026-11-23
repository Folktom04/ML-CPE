# บทเรียน Level 47 — EIGRP (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจ EIGRP และอัลกอริทึม DUAL · Successor / Feasible Successor / FD / RD / Feasibility Condition (คำนวณเองได้) · metric และ K-values · ตั้งค่าแบบ classic และ named mode · stub, summarization, unequal-cost load balancing · แก้ปัญหา neighbor และ Stuck-in-Active

---

## 1. EIGRP คืออะไร

**EIGRP (Enhanced Interior Gateway Routing Protocol)** — routing protocol ที่ Cisco พัฒนา (เผยแพร่เป็น RFC 7868 แบบ informational ปี 2016 แต่ในทางปฏิบัติยังใช้กับอุปกรณ์ Cisco เป็นหลัก)
- **Advanced distance vector** (บางตำราเรียก hybrid): ได้ข้อมูลจากเพื่อนบ้านแบบ distance vector แต่มีฟีเจอร์คล้าย link state (neighbor, ส่ง update เฉพาะเมื่อมีการเปลี่ยนแปลง)
- อัลกอริทึม **DUAL (Diffusing Update Algorithm)** — รับประกันไม่เกิด loop และ **มีเส้นทางสำรองเตรียมไว้** → converge เร็วมาก
- **AD:** **90** (internal), **170** (external), 5 (summary)
- IP protocol **88**, multicast **224.0.0.10** (IPv6: ff02::a)
- รองรับ VLSM, summarization ได้ทุก interface, **unequal-cost load balancing** (ฟีเจอร์เด่นที่ OSPF ไม่มี)

**ใช้ที่ไหน:** องค์กรที่ใช้อุปกรณ์ Cisco ทั้งหมด โดยเฉพาะ WAN hub-and-spoke/DMVPN · ถ้ามีหลายยี่ห้อ → ใช้ OSPF

---

## 2. ตาราง 3 ตารางของ EIGRP

| ตาราง | เก็บอะไร | คำสั่ง |
|---|---|---|
| **Neighbor table** | เพื่อนบ้านที่ติดต่อกันได้ | `show ip eigrp neighbors` |
| **Topology table** | **ทุกเส้นทาง** ที่เพื่อนบ้านประกาศมา พร้อม FD/RD | `show ip eigrp topology` |
| **Routing table** | เส้นทางที่ดีที่สุด (successor) | `show ip route eigrp` |

### Packet Types
Hello (ค้นหา/รักษา neighbor ทุก 5 วินาทีบน LAN, hold time 15 วินาที) · Update · Query · Reply · Ack — ส่งแบบ **reliable** ด้วย RTP (Reliable Transport Protocol) ของ EIGRP เอง

---

## 3. Metric และ K-Values

**Metric แบบคลาสสิก** คำนวณจาก
```
 Metric = 256 × [ K1×BW + (K2×BW)/(256−Load) + K3×Delay ] × [K5/(Reliability+K4)]
 ค่าเริ่มต้น K1=1, K2=0, K3=1, K4=0, K5=0  →  Metric = 256 × (BW + Delay)

 BW    = 10^7 / bandwidth ที่ต่ำที่สุดตลอดเส้นทาง (kbps)
 Delay = ผลรวม delay ของทุก interface ตลอดเส้นทาง (หน่วย 10 ไมโครวินาที)
```
- ใช้ **bandwidth ต่ำสุด (คอขวด)** + **delay รวม** → สะท้อนเส้นทางจริงดีกว่า hop count
- **K-values ต้องตรงกัน** ทุก neighbor ไม่เช่นนั้นจะไม่เป็น neighbor
- **Wide metrics (named mode):** รองรับ interface ความเร็วสูง (10G ขึ้นไป) ได้ดีกว่า metric แบบ 32 บิตเดิม

> 💡 ปรับเส้นทางให้ใช้ **delay** (`delay` ใต้ interface) แทนการแก้ bandwidth เพราะค่า bandwidth ถูกใช้โดยฟีเจอร์อื่นด้วย (QoS, OSPF cost)

---

## 4. DUAL — หัวใจของ EIGRP

### นิยามที่ต้องจำ
| คำ | ความหมาย |
|---|---|
| **FD (Feasible Distance)** | metric **ที่ดีที่สุด** จาก **ตัวเรา** ไปถึงปลายทาง |
| **RD / AD (Reported/Advertised Distance)** | metric จาก **เพื่อนบ้าน** ไปถึงปลายทาง (ที่เพื่อนบ้านบอกมา) |
| **Successor** | เพื่อนบ้านที่ให้เส้นทางดีที่สุด (FD) → **ลง routing table** |
| **Feasible Successor (FS)** | **เส้นทางสำรองที่รับประกันว่าไม่ loop** → เก็บใน topology table พร้อมใช้ทันที |
| **Feasibility Condition (FC)** | เพื่อนบ้านจะเป็น FS ได้ ก็ต่อเมื่อ **RD ของเขา < FD ปัจจุบันของเรา** |

**ทำไม FC รับประกันไม่ loop:** ถ้าเพื่อนบ้านอยู่ใกล้ปลายทางกว่าเรา (RD < FD) แปลว่าเส้นทางของเขา **ไม่ได้วนกลับมาผ่านเรา**

### ตัวอย่างคำนวณ
```
                 R2 (RD = 10)
          20 /             \
       R1                    NET X
          30 \             /
                 R3 (RD = 25)
          40 \
                 R4 (RD = 50)  → ไป X ผ่าน R4

 R1 ไป X:
   ผ่าน R2: 20 + 10 = 30  ← ดีที่สุด → FD = 30 · Successor = R2
   ผ่าน R3: 30 + 25 = 55  · RD 25 < FD 30 ✅ → Feasible Successor
   ผ่าน R4: 40 + 50 = 90  · RD 50 > FD 30 ❌ → ไม่เป็น FS (อาจ loop ได้)
```
- **R2 เสีย** → R1 ใช้ R3 (FS) **ทันที** ไม่ต้องถามใคร (convergence ระดับมิลลิวินาที) ✅
- ถ้า **ไม่มี FS** → route เข้าสถานะ **Active** แล้วส่ง **Query** ถามเพื่อนบ้านทุกตัว รอ **Reply** ครบจึงเลือกเส้นทางใหม่

### Passive vs Active
- **Passive (P)** = ปกติ มี successor ใช้งานได้ ✅
- **Active (A)** = กำลังคำนวณใหม่ (ส่ง query และรอ reply)

---

## 5. ตั้งค่า EIGRP

### Classic mode
```
router eigrp 100                           ! 100 = AS number — ต้องตรงกันทุก neighbor!
 eigrp router-id 1.1.1.1
 network 10.0.0.0 0.255.255.255            ! wildcard mask
 network 192.168.10.0 0.0.0.255
 passive-interface GigabitEthernet0/1
 no auto-summary                           ! (ค่าเริ่มต้นใน IOS ใหม่แล้ว)
```
### Named mode (แนะนำ — config อยู่ที่เดียว รองรับ IPv4/IPv6 และ wide metrics)
```
router eigrp CORP
 address-family ipv4 unicast autonomous-system 100
  eigrp router-id 1.1.1.1
  network 10.0.0.0 0.255.255.255
  af-interface default
   passive-interface
  exit-af-interface
  af-interface GigabitEthernet0/0
   no passive-interface
   authentication mode hmac-sha-256 S3cr3t!
  exit-af-interface
  topology base
   variance 2
   maximum-paths 4
  exit-af-topology
```

### เงื่อนไข Neighbor
**AS number ตรงกัน · K-values ตรงกัน · subnet เดียวกัน · authentication ตรงกัน** (hello/hold timer ไม่จำเป็นต้องตรงกัน — ต่างจาก OSPF)

---

## 6. ฟีเจอร์สำคัญ

### 6.1 Unequal-Cost Load Balancing (Variance)
OSPF กระจายได้เฉพาะเส้นทาง cost เท่ากัน EIGRP กระจาย **เส้นทาง metric ไม่เท่ากัน** ได้ตามสัดส่วน
```
 variance 2 → ใช้เส้นทางที่ metric ≤ 2 × FD และต้องเป็น Feasible Successor
 ตัวอย่างข้างบน: FD 30 → ใช้ได้ถึง 60 → R3 (55, เป็น FS) ถูกใช้ร่วมกับ R2 ตามสัดส่วน
 R4 (90) ไม่ถูกใช้
```

### 6.2 Summarization (ทำได้ที่ interface ใดก็ได้)
```
interface Gi0/0
 ip summary-address eigrp 100 10.10.0.0 255.255.0.0      ! classic
! named: af-interface Gi0/0 → summary-address 10.10.0.0/16
```
สร้าง Null0 route (AD 5) อัตโนมัติ — และช่วย **จำกัดขอบเขตของ query** (query หยุดที่จุดที่ summarize)

### 6.3 EIGRP Stub ⭐ (สำคัญกับ hub-and-spoke)
```
 [HUB] ─── WAN ─── [สาขา 1..50]
 สาขาตั้งเป็น stub → hub จะ **ไม่ส่ง query** ไปที่สาขา และสาขาจะไม่ถูกใช้เป็นทางผ่าน (transit)
```
```
router eigrp 100
 eigrp stub connected summary              ! สาขาประกาศเฉพาะ connected + summary
```
→ ลด query scope, ป้องกัน **Stuck-in-Active**, converge เร็วขึ้น

---

## 7. Stuck-in-Active (SIA)

เมื่อ route เป็น Active แล้วส่ง query ออกไป แต่ **ไม่ได้รับ reply ภายในเวลาที่กำหนด** (active timer ประมาณ 3 นาที) → ตัดความสัมพันธ์กับ neighbor ที่ไม่ตอบ → route flap และอาจลามไปทั้งเครือข่าย

**สาเหตุ:** query กระจายไกลเกิน (เครือข่ายใหญ่ไม่มี summary/stub), ลิงก์ช้า/packet loss, CPU router สูง
**ป้องกัน:** **stub** ที่สาขา, **summarization**, ออกแบบเป็นลำดับชั้น, ลิงก์ที่มีคุณภาพ (EIGRP รุ่นใหม่มี SIA-Query/Reply ช่วยระหว่างรอ)

---

## 8. คำสั่งตรวจสอบ

```
show ip eigrp neighbors
H  Address       Interface  Hold Uptime    SRTT  RTO  Q   Seq
0  10.255.0.2    Gi0/0      13   02:15:30  2     200  0   45      ← Q (queue) ควรเป็น 0

show ip eigrp topology
P 10.3.0.0/24, 1 successors, FD is 3072
        via 10.255.0.2 (3072/2816), Gi0/0          ← (FD ผ่านทางนี้ / RD)
        via 10.255.0.6 (5120/2560), Gi0/1          ← RD 2560 < FD 3072 → Feasible Successor
show ip eigrp topology all-links                   ! รวมเส้นทางที่ไม่ผ่าน FC
show ip route eigrp                                ! D (internal), D EX (external)
show ip protocols                                  ! AS, K-values, variance, networks
```

---

## 9. Migration EIGRP → OSPF

EIGRP (AD 90) **ชนะ** OSPF (AD 110) จึงต้องปรับ AD ก่อน
```
 1) เปิด OSPF ขนานทุก router (route ยังเป็น D เพราะ AD 90)
 2) ตรวจ OSPF neighbor/LSDB ครบ
 3) เพิ่ม AD ของ EIGRP ให้สูงกว่า OSPF: router eigrp 100 → distance eigrp 120 170
    → route เปลี่ยนเป็น O ทันที
 4) ทดสอบ แล้วปิด EIGRP ทีละ router · rollback = ลด distance กลับ
```

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| FD คือ metric ที่เพื่อนบ้านบอกมา | FD คือ metric ของเราเอง; ที่เพื่อนบ้านบอกคือ RD |
| เส้นทางสำรองทุกเส้นเป็น Feasible Successor | ต้องผ่าน FC (RD < FD) เท่านั้น |
| EIGRP neighbor ต้อง hello/hold เท่ากัน | ไม่จำเป็น (ต้องตรง AS, K-values, subnet, auth) |
| variance ใช้ได้กับทุกเส้นทาง | ใช้ได้เฉพาะ feasible successor |
| EIGRP ใช้ได้ทุกยี่ห้อ | ในทางปฏิบัติใช้กับ Cisco เป็นหลัก |

---

## 11. Cheat Sheet

```
EIGRP = advanced DV · DUAL · AD 90 (int) / 170 (ext) / 5 (summary) · IP 88 · 224.0.0.10
Metric (default K1=K3=1) = 256 × (10^7/BW_min + ΣDelay/10) · ปรับด้วย delay
FD = metric ดีที่สุดของเรา · RD = ของเพื่อนบ้าน · Successor = ทางหลัก (route table)
Feasible Successor: RD < FD → สำรองทันที (ไม่ต้อง query)
Passive = ปกติ · Active = กำลัง query · SIA = รอ reply นานเกิน
Neighbor ต้องตรง: AS, K-values, subnet, auth (hello/hold ไม่ต้องตรง)
variance N = unequal-cost LB (เฉพาะ FS) · summary ได้ทุก interface · stub ที่สาขา (ลด query)
Named mode: router eigrp NAME → address-family ipv4 autonomous-system N
show ip eigrp neighbors / topology / route eigrp
```

---

## 12. แบบทดสอบ 10 ข้อ

1. EIGRP ใช้อัลกอริทึมใด และ AD ของ internal/external คือเท่าไร
2. Metric ค่าเริ่มต้นของ EIGRP ใช้ค่าใดบ้าง
3. FD กับ RD ต่างกันอย่างไร
4. Feasibility condition คืออะไร ทำไมรับประกันว่าไม่ loop
5. R1 มี FD = 100 ผ่าน R2 เพื่อนบ้าน R3 มี RD = 80 (metric รวม 150) R4 มี RD = 120 (metric รวม 140) ใครเป็น FS
6. ถ้า successor ล่มและไม่มี FS จะเกิดอะไรขึ้น
7. variance ใช้ทำอะไร มีเงื่อนไขอะไร
8. EIGRP stub ช่วยอะไรในเครือข่าย hub-and-spoke
9. Stuck-in-Active คืออะไร ป้องกันอย่างไร
10. migrate จาก EIGRP ไป OSPF ต้องทำอะไรกับ AD และเพราะอะไร

<details><summary><b>เฉลย</b></summary>

1. DUAL; internal 90, external 170
2. Bandwidth (ต่ำสุดตลอดเส้นทาง) และ delay (รวม) — K1 = K3 = 1
3. FD = metric ที่ดีที่สุดจากเราไปถึงปลายทาง; RD = metric จากเพื่อนบ้านไปถึงปลายทาง
4. RD ของเพื่อนบ้าน < FD ปัจจุบันของเรา — แสดงว่าเพื่อนบ้านอยู่ใกล้ปลายทางกว่าเรา เส้นทางของเขาจึงไม่วนผ่านเรา
5. R3 (RD 80 < FD 100) เป็น FS; R4 ไม่ใช่ (RD 120 > 100) แม้ metric รวมจะต่ำกว่า R3
6. Route เข้า Active ส่ง query ไปเพื่อนบ้านแล้วรอ reply เพื่อหาเส้นทางใหม่
7. Unequal-cost load balancing — ใช้เส้นทางที่ metric ≤ variance × FD และต้องเป็น feasible successor
8. Hub ไม่ส่ง query ไปสาขา และสาขาไม่ถูกใช้เป็นทางผ่าน — ลด query scope และป้องกัน SIA
9. Route active แล้วไม่ได้รับ reply ภายในเวลา ทำให้ตัด neighbor — ป้องกันด้วย stub, summarization, ออกแบบเป็นลำดับชั้น, ลิงก์คุณภาพดี
10. เพิ่ม AD ของ EIGRP ให้สูงกว่า 110 (`distance eigrp`) เพราะ EIGRP 90 ชนะ OSPF 110 ทำให้ route ของ OSPF ไม่ถูกใช้
</details>

---

➡️ ต่อไป: **Level 48 — BGP พื้นฐาน**
