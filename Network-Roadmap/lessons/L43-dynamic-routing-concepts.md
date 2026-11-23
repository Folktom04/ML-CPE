# บทเรียน Level 43 — แนวคิด Dynamic Routing (ฉบับละเอียด)

> อ่านจบแล้วจะ: รู้ว่าเมื่อไรควรใช้ dynamic routing · แยก IGP/EGP · Distance Vector / Link State / Path Vector · metric ของแต่ละโปรโตคอล · convergence และกลไกป้องกัน loop · passive interface, authentication, filtering · Control/Data/Management plane, RIB/FIB/CEF

---

## 1. ทำไมต้องใช้ Dynamic Routing

| สถานการณ์ | Static | Dynamic |
|---|---|---|
| Router 3 ตัว เส้นทางเดียว | ✅ เหมาะ | ไม่จำเป็น |
| Router 50 ตัว หลายเส้นทาง | ❌ แก้ด้วยมือทุกตัว ผิดพลาดง่าย | ✅ เรียนรู้และปรับเองอัตโนมัติ |
| ลิงก์ขาด | ❌ ไม่ปรับเอง (เว้นแต่ track) | ✅ หาเส้นทางใหม่เอง (convergence) |
| เพิ่ม subnet ใหม่ | ❌ เพิ่ม route ทุก router | ✅ ประกาศครั้งเดียว ทุกตัวรู้ |

**Dynamic routing protocol** = router **แลกข้อมูลเส้นทางกันเอง** เพื่อสร้าง routing table และ **ปรับอัตโนมัติ** เมื่อเครือข่ายเปลี่ยน

---

## 2. IGP vs EGP

| | IGP (Interior Gateway Protocol) | EGP (Exterior Gateway Protocol) |
|---|---|---|
| ใช้ | **ภายในองค์กรเดียว** (Autonomous System เดียว) | **ระหว่างองค์กร/ISP** (ระหว่าง AS) |
| เป้าหมาย | หาเส้นทางที่ **เร็ว/ดีที่สุด** converge เร็ว | ควบคุมด้วย **นโยบาย (policy)** scale ระดับอินเทอร์เน็ต |
| ตัวอย่าง | **OSPF**, **EIGRP**, IS-IS, RIP | **BGP** (ตัวเดียวที่ใช้จริงในปัจจุบัน) |

**Autonomous System (AS)** = กลุ่มเครือข่ายภายใต้การบริหารและนโยบาย routing เดียวกัน มีหมายเลข **ASN** (เช่น ISP ไทย, มหาวิทยาลัย, cloud provider)

---

## 3. ประเภทของ Routing Protocol

### 3.1 Distance Vector — "บอกต่อจากเพื่อนบ้าน"
- รู้แค่ **ระยะทาง (distance/metric)** และ **ทิศทาง (vector = next hop)** ไปยังแต่ละวง
- ได้ข้อมูลจาก **เพื่อนบ้านโดยตรง** ไม่เห็นแผนที่ทั้งเครือข่าย (routing by rumor)
- รุ่นเก่าส่ง **ทั้ง routing table เป็นระยะ** (RIP ทุก 30 วินาที)
- อัลกอริทึม: **Bellman-Ford**
- ตัวอย่าง: **RIP**, (EIGRP = advanced distance vector)

> 💡 เหมือนถามทางกับคนที่ทางแยก "ไปเชียงใหม่ทางนี้ 700 กม." — เชื่อตามที่บอก ไม่ได้เห็นแผนที่เอง

### 3.2 Link State — "ทุกคนมีแผนที่เดียวกัน"
- ทุก router แลก **สถานะลิงก์ (LSA)** ของตัวเองไปทั่วทั้ง area → ทุกตัวมี **ฐานข้อมูลเดียวกัน (LSDB)** = แผนที่ทั้งเครือข่าย
- แต่ละ router คำนวณเส้นทางสั้นที่สุดเองด้วย **Dijkstra (SPF)**
- ส่ง update **เฉพาะเมื่อมีการเปลี่ยนแปลง** (+ refresh นาน ๆ ครั้ง)
- converge เร็ว, ไม่ค่อยเกิด loop, แต่ใช้ CPU/memory มากกว่า
- ตัวอย่าง: **OSPF**, **IS-IS**

> 💡 เหมือนทุกคนมี Google Maps เวอร์ชันเดียวกัน แล้วคำนวณเส้นทางเอง

### 3.3 Path Vector — "บอกเส้นทางผ่าน AS ใดบ้าง"
- ประกาศ route พร้อม **รายการ AS ที่ผ่าน (AS-PATH)** → ป้องกัน loop (ถ้าเห็น AS ตัวเองใน path ก็ทิ้ง)
- เลือกเส้นทางตาม **นโยบาย/attribute** ไม่ใช่แค่ระยะทาง
- ตัวอย่าง: **BGP**

### เปรียบเทียบ

| | RIP | EIGRP | OSPF | IS-IS | BGP |
|---|---|---|---|---|---|
| ประเภท | DV | Advanced DV | Link state | Link state | Path vector |
| IGP/EGP | IGP | IGP | IGP | IGP | EGP (ใช้ภายในได้) |
| Metric | Hop count (≤15) | Bandwidth + delay | **Cost** (จาก bandwidth) | Cost | **Attributes** |
| Convergence | ช้า | เร็วมาก | เร็ว | เร็ว | ช้ากว่า (เน้นเสถียร) |
| มาตรฐาน | เปิด | Cisco (มี RFC informational) | เปิด | เปิด | เปิด |
| ใช้ที่ไหน | ของเก่า/lab | องค์กรที่ใช้ Cisco | **องค์กรทั่วไป (นิยมที่สุด)** | ISP/DC ขนาดใหญ่ | อินเทอร์เน็ต, DC, WAN |
| AD | 120 | 90 | 110 | 115 | 20/200 |
| Transport | UDP 520 | IP protocol 88 | IP protocol 89 | ตรงบน L2 (ไม่ใช่ IP) | TCP 179 |

---

## 4. Metric

ค่าที่แต่ละโปรโตคอลใช้วัดว่าเส้นทางไหน "ดีกว่า" (**ต่ำกว่า = ดีกว่า**) — เปรียบเทียบข้ามโปรโตคอลไม่ได้ (จึงต้องมี AD)

```
       R1 ──1G──R2──1G──R4         RIP: ทาง R1-R3-R4 (2 hop) = ทาง R1-R2-R4 (2 hop) → ECMP
        \                /           แม้ทาง R3 จะเป็น 10 Mbps!
         ──10M──R3──10M──           OSPF: cost 1G ต่ำกว่า 10M มาก → เลือกทาง R2 ✅
```
→ เหตุผลที่ไม่ใช้ RIP ในงานจริง: hop count ไม่สนใจความเร็วลิงก์

---

## 5. Convergence

**Convergence** = สถานะที่ **ทุก router มีข้อมูลเส้นทางถูกต้องและตรงกัน** หลังมีการเปลี่ยนแปลง
**Convergence time** = เวลาตั้งแต่เกิดการเปลี่ยนแปลง (เช่น ลิงก์ขาด) จนเครือข่ายกลับมาส่งข้อมูลได้ถูกต้อง

ขั้นตอน: **ตรวจพบ (detect)** → **แจ้ง (propagate)** → **คำนวณใหม่ (compute)** → **ติดตั้งลง FIB (install)**

**เร่ง convergence**
- ตรวจพบเร็ว: **BFD** (ตรวจลิงก์เสียระดับมิลลิวินาที), ลด hello/dead timer, link down detection ทันที (ลิงก์ fiber ตรง)
- โปรโตคอลที่มีทางสำรองเตรียมไว้: EIGRP feasible successor, OSPF/IS-IS LFA

---

## 6. กลไกป้องกัน Routing Loop (Distance Vector)

ปัญหา **Count to infinity:** ลิงก์ขาด แต่ router บอกต่อข้อมูลเก่ากันไปมา metric เพิ่มเรื่อย ๆ

| กลไก | หลักการ |
|---|---|
| **Maximum metric** | RIP กำหนด 16 = unreachable (หยุดนับ) |
| **Split horizon** | **ไม่ประกาศ route กลับออกไปทาง interface ที่เรียนรู้มา** |
| **Route poisoning** | วงที่ล่มประกาศด้วย metric สูงสุด (unreachable) ทันที |
| **Poison reverse** | ตอบกลับ route ที่ถูก poison ด้วย unreachable เช่นกัน |
| **Hold-down timer** | ไม่รับข้อมูลที่แย่กว่าของ route ที่เพิ่งล่มช่วงหนึ่ง (กันข่าวเก่า) |
| **Triggered update** | ส่ง update ทันทีเมื่อมีการเปลี่ยนแปลง ไม่รอรอบ |

Link state ป้องกัน loop ด้วยการที่ทุกตัวมีแผนที่เดียวกันและคำนวณ SPF · BGP ป้องกันด้วย AS-PATH

---

## 7. ECMP — Equal-Cost Multi-Path

ถ้ามีหลายเส้นทางที่ **metric เท่ากัน** router จะใส่ทุกเส้นใน table และ **กระจาย traffic** (ต่อ flow ด้วย hash เหมือน EtherChannel)
- ✅ ใช้ bandwidth ได้หลายเส้น + สำรองทันทีเมื่อเส้นหนึ่งขาด
- ใช้มากใน data center (spine-leaf) และ routed access
- `maximum-paths 4` (ปรับจำนวนเส้นสูงสุด)

---

## 8. แนวปฏิบัติที่ดีเมื่อใช้ Dynamic Routing

| ฟีเจอร์ | เหตุผล |
|---|---|
| **Passive interface** | interface ที่ต่อผู้ใช้ (ไม่มี router อยู่) — **ยังประกาศวงนั้น** แต่ **ไม่ส่ง hello** ออกไป → ผู้ใช้ไม่สามารถตั้ง router ปลอมเข้ามาคุยด้วย และไม่เปลือง resource |
| **Authentication** (MD5/SHA) | ป้องกัน router แปลกปลอมส่ง route ปลอม |
| **Route filtering** | รับ/ประกาศเฉพาะ route ที่ตั้งใจ (prefix-list, distribute-list) |
| **Summarization** | ลดขนาด table, จำกัดผลกระทบเมื่อวงย่อย flap |
| **Router ID ชัดเจน** (loopback) | คาดเดาได้ แก้ปัญหาง่าย |
| **Log neighbor changes** | รู้ว่า neighbor ขึ้น/ลงเมื่อไร |

```
router ospf 1
 router-id 1.1.1.1
 passive-interface default                 ! ทุก interface เป็น passive
 no passive-interface GigabitEthernet0/0   ! ยกเว้นลิงก์ที่มี router อยู่
 log-adjacency-changes detail
```

---

## 9. Control / Data / Management Plane

| Plane | หน้าที่ | ตัวอย่าง |
|---|---|---|
| **Control plane** | "สมอง" — สร้างข้อมูลการตัดสินใจ | routing protocol (OSPF/BGP), STP, ARP — สร้าง **RIB** |
| **Data (Forwarding) plane** | "กล้ามเนื้อ" — ส่งต่อ packet จริง | ใช้ **FIB** ส่งต่อด้วย hardware (ASIC) ความเร็วสูง |
| **Management plane** | ช่องทางที่คนดูแลเข้ามาจัดการ | SSH, SNMP, NETCONF, syslog |

- **RIB (Routing Information Base)** = routing table (`show ip route`) สร้างโดย control plane
- **FIB (Forwarding Information Base)** = ตารางที่ปรับให้ส่งเร็วที่สุด สร้างจาก RIB + ข้อมูล L2 (adjacency) — ใน Cisco คือ **CEF (Cisco Express Forwarding)** (`show ip cef`)
- **CoPP (Control Plane Policing)** = จำกัด traffic ที่วิ่งขึ้นไปหา CPU เพื่อป้องกัน control plane ถูกโจมตี/ล่ม (เช่น ping flood, ARP storm)
- แนวคิดนี้เป็นพื้นฐานของ **SDN** (แยก control plane ไปไว้ที่ controller — Level 88)

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| Dynamic routing ดีกว่า static เสมอ | เครือข่ายเล็ก/stub ใช้ static ง่ายและปลอดภัยกว่า |
| Metric ของ OSPF กับ EIGRP เทียบกันได้ | เทียบไม่ได้ จึงใช้ AD ตัดสิน |
| Passive interface = ไม่ประกาศวงนั้น | ยังประกาศวง แค่ไม่ส่ง hello/ไม่สร้าง neighbor |
| BGP ใช้เฉพาะ ISP | องค์กรใช้กับ multihoming, DC fabric, SD-WAN, cloud |

---

## 11. Cheat Sheet

```
IGP (ในองค์กร): OSPF, EIGRP, IS-IS, RIP · EGP (ระหว่าง AS): BGP
Distance vector (เชื่อเพื่อนบ้าน, Bellman-Ford): RIP, EIGRP(advanced)
Link state (แผนที่เดียวกัน, Dijkstra SPF): OSPF, IS-IS · Path vector (AS-PATH, policy): BGP
Metric: RIP hop · OSPF cost · EIGRP bw+delay · BGP attributes
Convergence: detect → propagate → compute → install · เร่งด้วย BFD
Loop prevention DV: max metric, split horizon, poisoning, hold-down, triggered update
ECMP = หลายเส้น metric เท่ากัน · passive-interface · authentication · filtering · summarization
Control (RIB) / Data (FIB/CEF) / Management · CoPP ป้องกัน CPU
```

---

## 12. แบบทดสอบ 10 ข้อ

1. เมื่อไรควรใช้ static routing และเมื่อไรควรใช้ dynamic
2. IGP กับ EGP ต่างกันอย่างไร ยกตัวอย่าง
3. Distance vector ต่างจาก link state อย่างไร
4. OSPF ใช้อัลกอริทึมใดคำนวณเส้นทาง
5. ทำไม RIP อาจเลือกเส้นทางที่ช้ากว่า
6. Split horizon คืออะไร
7. Convergence คืออะไร และ BFD ช่วยอย่างไร
8. Passive interface ทำอะไร และยังประกาศวงนั้นหรือไม่
9. RIB กับ FIB ต่างกันอย่างไร
10. CoPP ใช้ทำอะไร

<details><summary><b>เฉลย</b></summary>

1. Static: เครือข่ายเล็ก, stub, default route ไป ISP, route สำรอง; Dynamic: เครือข่ายใหญ่/หลายเส้นทาง ต้องปรับอัตโนมัติเมื่อมีการเปลี่ยนแปลง
2. IGP ใช้ภายใน AS เดียว (OSPF, EIGRP, IS-IS); EGP ใช้ระหว่าง AS (BGP)
3. Distance vector รู้แค่ระยะทางและทิศจากเพื่อนบ้าน; link state ทุก router มีแผนที่ทั้ง area และคำนวณเอง
4. Dijkstra (SPF)
5. ใช้ hop count เป็น metric ไม่สนใจ bandwidth ของลิงก์
6. ไม่ประกาศ route กลับออกไปทาง interface ที่เรียนรู้ route นั้นมา (ป้องกัน loop)
7. สถานะที่ทุก router มีเส้นทางถูกต้องตรงกันหลังมีการเปลี่ยนแปลง — BFD ตรวจลิงก์/เพื่อนบ้านเสียได้ในระดับมิลลิวินาที ทำให้เริ่มคำนวณใหม่เร็วขึ้น
8. ไม่ส่ง hello/ไม่สร้าง neighbor บน interface นั้น แต่ยังประกาศวงของ interface นั้นอยู่
9. RIB = routing table ที่ control plane สร้าง; FIB = ตารางส่งต่อที่ data plane ใช้ส่ง packet ด้วยความเร็วสูง (CEF)
10. จำกัด traffic ที่ส่งขึ้น CPU ของอุปกรณ์ เพื่อป้องกัน control plane ถูกโจมตีหรือใช้งานจนล่ม
</details>

---

➡️ ต่อไป: **Level 44 — RIP**
