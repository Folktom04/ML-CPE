# บทเรียน Level 46 — OSPF Multi-Area & LSA (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจว่าทำไมต้องแบ่ง area · บทบาท ABR/ASBR · LSA Type 1, 2, 3, 4, 5, 7 · Stub / Totally Stubby / NSSA · Summarization ที่ ABR และ ASBR · Virtual link · BFD · ออกแบบ OSPF สำหรับองค์กรหลายสาขา

---

## 1. ทำไมต้องแบ่ง Area

Single area ที่ใหญ่มาก (router หลายร้อยตัว) มีปัญหา
- **LSDB ใหญ่** → ใช้ memory มาก
- **SPF รันบ่อย** — ลิงก์ใดลิงก์หนึ่ง flap ทำให้ **ทุก router** ต้องคำนวณใหม่
- **Flooding** ของ LSA ไปทั่วทั้งเครือข่าย

**Multi-area** แบ่ง OSPF เป็นส่วน ๆ:
- รายละเอียดของ topology **อยู่แค่ใน area** (LSA type 1/2 ไม่ข้าม area)
- area อื่นเห็นแค่ **"สรุปว่ามีวงอะไรบ้าง"** (type 3) — ถ้าทำ summarization ยิ่งเหลือน้อย
- การเปลี่ยนแปลงใน area หนึ่ง **ไม่ทำให้ area อื่นต้องรัน SPF เต็ม**

> 💡 **เปรียบเทียบ:** แต่ละจังหวัดมีแผนที่ถนนละเอียดของตัวเอง (intra-area) ส่วนข้ามจังหวัดใช้แค่ "ป้ายบอกทางไปจังหวัดอื่น" (inter-area summary)

---

## 2. โครงสร้าง: Backbone Area 0

```
              ┌──────────── Area 0 (Backbone) ────────────┐
              │   [CORE-1]════════════[CORE-2]             │
              └──────┬────────────────────┬───────────────┘
                 [ABR-1]               [ABR-2]       ← มี interface ทั้งใน area 0 และ area อื่น
              ┌─────┴──────┐        ┌─────┴──────┐
              │  Area 10   │        │  Area 20   │
              │ (สาขาเหนือ) │        │ (สาขาใต้)   │
              └────────────┘        └──────┬─────┘
                                      [ASBR] ── route ภายนอก (static/BGP/อีก protocol)
```
**กฎสำคัญ:** **ทุก area ต้องต่อกับ Area 0** และ traffic ระหว่าง area ต้องผ่าน Area 0 (ป้องกัน loop ระหว่าง area)

### ประเภท Router

| ประเภท | ลักษณะ |
|---|---|
| **Internal router** | ทุก interface อยู่ area เดียว |
| **Backbone router** | มี interface อย่างน้อยหนึ่งใน area 0 |
| **ABR (Area Border Router)** | เชื่อม **area 0 กับ area อื่น** — สร้าง LSA type 3/4, ทำ summarization ระหว่าง area |
| **ASBR (Autonomous System Boundary Router)** | **นำ route จากภายนอก OSPF** เข้ามา (redistribute static/connected/BGP/EIGRP) — สร้าง LSA type 5 (หรือ 7 ใน NSSA) |

---

## 3. LSA Types (ต้องจำ)

| Type | ชื่อ | สร้างโดย | ขอบเขต | บอกอะไร | ใน routing table |
|---|---|---|---|---|---|
| **1** | Router LSA | ทุก router | **ใน area** | router นี้มีลิงก์อะไร cost เท่าไร | `O` |
| **2** | Network LSA | **DR** | ใน area | router ใดต่ออยู่บน broadcast segment นี้ | `O` |
| **3** | Summary LSA | **ABR** | ข้าม area | วงใน area อื่น (prefix + cost) | `O IA` |
| **4** | ASBR Summary | **ABR** | ข้าม area | วิธีไปหา ASBR ที่อยู่ area อื่น | — |
| **5** | AS External | **ASBR** | **ทั้ง OSPF domain** (ยกเว้น stub) | route จากภายนอก OSPF | `O E1` / `O E2` |
| **7** | NSSA External | ASBR ใน **NSSA** | ใน NSSA เท่านั้น | route ภายนอกใน NSSA (ABR แปลงเป็น type 5) | `O N1` / `O N2` |

### External Route: E1 vs E2
- **E2 (ค่าเริ่มต้น):** metric = **ค่าที่ ASBR กำหนดเท่านั้น** ไม่บวก cost ภายใน (ทุก router เห็นเท่ากัน)
- **E1:** metric = ค่าภายนอก **+ cost ภายในไปถึง ASBR** → ใช้เมื่อมีหลาย ASBR และอยากให้เลือกตัวที่ใกล้ที่สุด

### ลำดับความชอบของ route ใน OSPF (ถ้า prefix เดียวกัน)
**Intra-area (O) > Inter-area (O IA) > External E1/N1 > External E2/N2** — ไม่ขึ้นกับ cost

---

## 4. Area Types — ลดขนาด LSDB ของ area ปลายทาง

| Area | Type 3 (inter-area) | Type 5 (external) | Type 7 | Default route จาก ABR | ใช้เมื่อ |
|---|---|---|---|---|---|
| **Standard** | ✅ | ✅ | — | — | ทั่วไป |
| **Stub** | ✅ | ❌ | — | ✅ (type 3 default) | สาขาที่ไม่มีทางออกอื่น ไม่ต้องรู้ route ภายนอก |
| **Totally Stubby** (Cisco) | ❌ (เหลือแค่ default) | ❌ | — | ✅ | สาขาเล็กที่ต้องการ table เล็กที่สุด |
| **NSSA** | ✅ | ❌ | ✅ | (ตั้งได้) | อยากเป็น stub **แต่มี ASBR** ในพื้นที่ (เช่น สาขาที่มี static/ISP ของตัวเอง) |
| **Totally NSSA** | ❌ | ❌ | ✅ | ✅ | เหมือน NSSA แต่ตัด inter-area ด้วย |

```
! Stub — ทุก router ใน area ต้องตั้งเหมือนกัน (stub flag อยู่ใน hello)
router ospf 1
 area 10 stub
! Totally stubby — ตั้งที่ ABR เพิ่ม no-summary
 area 10 stub no-summary
! NSSA
 area 20 nssa
 area 20 nssa no-summary                    ! (ที่ ABR) totally NSSA
```
> ⚠️ Area 0 เป็น stub/NSSA **ไม่ได้**

---

## 5. Summarization

### ที่ ABR — สรุป route ระหว่าง area (type 3)
```
router ospf 1
 area 10 range 10.10.0.0 255.255.0.0        ! area 10 ประกาศออกไปเป็น 10.10.0.0/16 วงเดียว
```
### ที่ ASBR — สรุป route ภายนอก (type 5/7)
```
router ospf 1
 summary-address 172.16.0.0 255.255.0.0
```
- Cisco สร้าง **Null0 route** ของ summary อัตโนมัติ ป้องกัน loop
- **IP plan ต้องออกแบบให้ summarize ได้** (แต่ละ area ได้ block ต่อเนื่อง — Level 10)
- ข้อควรระวัง: summary ทำให้เห็นรายละเอียดน้อยลง อาจเลือกเส้นทางไม่ optimal เล็กน้อย

---

## 6. Redistribution เข้า OSPF (ASBR)

```
router ospf 1
 redistribute static subnets                 ! "subnets" สำคัญ (IOS เก่า ไม่ใส่จะนำเข้าเฉพาะ classful)
 redistribute connected subnets route-map ONLY-DMZ
 default-information originate               ! ประกาศ default
```
- ใช้ **route-map/prefix-list** คัดเฉพาะที่ต้องการเสมอ
- ระวัง **mutual redistribution** ระหว่าง 2 protocol หลายจุด → loop (ใช้ route tag กรอง — Level 49)

---

## 7. Virtual Link (ทางแก้ชั่วคราว)

area ที่ **ไม่ได้ต่อกับ area 0 โดยตรง** สามารถสร้าง **virtual link** ผ่าน transit area ไปยัง area 0 ได้
```
 area 0 ── ABR1 ──(area 1 transit)── ABR2 ── area 2
 ABR1: area 1 virtual-link <RID ของ ABR2>
 ABR2: area 1 virtual-link <RID ของ ABR1>
```
ใช้ระหว่างรวมบริษัท/เปลี่ยนโครงสร้าง — **ไม่ใช่การออกแบบถาวรที่ดี** (transit area เป็น stub ไม่ได้)

---

## 8. BFD — ตรวจลิงก์เสียเร็ว

OSPF ปกติรู้ว่าเพื่อนบ้านหายเมื่อครบ **dead interval (40 วินาที)** (ถ้าลิงก์ไม่ down ตรง ๆ เช่น ผ่าน switch หรือ provider)
**BFD (Bidirectional Forwarding Detection)** ส่ง hello เล็ก ๆ ทุกไม่กี่สิบมิลลิวินาที → ตรวจพบภายใน **< 1 วินาที** แล้วแจ้ง OSPF ทันที
```
interface Gi0/0
 bfd interval 300 min_rx 300 multiplier 3     ! ตรวจพบภายใน ~900 ms
router ospf 1
 bfd all-interfaces
show bfd neighbors
```

---

## 9. ตัวอย่างออกแบบ: องค์กร 20 สาขา

```
 Area 0: Core DC + HQ + WAN hub (router หลัก)
 Area 1-4: แบ่งตามภูมิภาค (เหนือ/อีสาน/ใต้/ตะวันออก) — ABR อยู่ที่ hub ภูมิภาค
 สาขาในแต่ละภูมิภาค: totally stubby (เห็นแค่ default + วงในภูมิภาค)
 IP plan: ภาค 1 = 10.1.0.0/16 · ภาค 2 = 10.2.0.0/16 ... → ABR summarize ภาคละ 1 route
 สาขาที่มี ISP ของตัวเอง (local breakout): NSSA
 ทุกลิงก์ WAN: point-to-point + BFD · reference bandwidth เท่ากันทุก router
```

---

## 10. คำสั่งตรวจสอบ

```
show ip ospf                           ! เป็น ABR/ASBR ไหม, area ที่เกี่ยวข้อง, ชนิดของ area
show ip ospf database                  ! สรุป LSA แต่ละ type แยกตาม area
show ip ospf database summary          ! type 3
show ip ospf database external         ! type 5
show ip ospf database nssa-external    ! type 7
show ip ospf border-routers            ! ABR/ASBR ที่รู้จัก
show ip route ospf                     ! O, O IA, O E1/E2, O N1/N2
```

---

## 11. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| area ไหนต่อกับ area ไหนก็ได้ | ทุก area ต้องต่อ area 0 (หรือใช้ virtual link ชั่วคราว) |
| Type 1/2 ข้าม area | อยู่ใน area; ข้าม area ด้วย type 3 |
| Route ที่ cost ต่ำกว่าชนะเสมอใน OSPF | Intra-area ชนะ inter-area และ external ก่อนดู cost |
| Stub area ตั้งที่ ABR อย่างเดียว | ต้องตั้งทุก router ใน area (flag อยู่ใน hello) |
| NSSA = stub | NSSA ยอมให้มี ASBR ภายใน (type 7) |

---

## 12. Cheat Sheet

```
แบ่ง area: LSDB เล็ก · SPF เฉพาะ area · flooding จำกัด · ทุก area ต่อ area 0
ABR = เชื่อม area 0 กับ area อื่น (type 3/4, area X range) · ASBR = นำ route ภายนอกเข้า (type 5/7)
LSA: 1 router · 2 network (DR) · 3 summary (ABR) · 4 ASBR summary · 5 external (ASBR) · 7 NSSA
Route: O > O IA > O E1/N1 > O E2/N2 · E2 = metric คงที่ (default) · E1 = + cost ภายใน
Stub (ไม่มี 5) · Totally stubby (ไม่มี 3,5 เหลือ default) · NSSA (ไม่มี 5 แต่มี 7)
Summary: ABR area X range · ASBR summary-address · redistribute ... subnets
Virtual link = ชั่วคราว · BFD = ตรวจลิงก์เสีย < 1 วิ
```

---

## 13. แบบทดสอบ 10 ข้อ

1. ข้อดีของการแบ่ง OSPF เป็นหลาย area (3 ข้อ)
2. กฎสำคัญเกี่ยวกับ area 0
3. ABR กับ ASBR ต่างกันอย่างไร
4. LSA type 1, 2, 3 สร้างโดยใคร และข้าม area หรือไม่
5. LSA type 5 และ type 7 คืออะไร
6. O E1 ต่างจาก O E2 อย่างไร
7. Stub area ไม่รับ LSA type ใด และได้ default route จากที่ใด
8. เมื่อไรควรใช้ NSSA แทน stub
9. คำสั่ง summarize area 10 ให้เป็น 10.10.0.0/16 ที่ ABR
10. BFD ช่วย OSPF อย่างไร

<details><summary><b>เฉลย</b></summary>

1. LSDB เล็กลง, SPF ทำงานเฉพาะใน area ที่มีการเปลี่ยนแปลง, จำกัด flooding, summarize ได้
2. ทุก area ต้องเชื่อมกับ area 0 (backbone) และ traffic ระหว่าง area ต้องผ่าน area 0
3. ABR เชื่อม area 0 กับ area อื่น; ASBR นำ route จากภายนอก OSPF เข้ามา
4. Type 1 = ทุก router, type 2 = DR — อยู่ใน area; type 3 = ABR — ข้าม area
5. Type 5 = route ภายนอกจาก ASBR กระจายทั้ง domain; type 7 = route ภายนอกใน NSSA (ABR แปลงเป็น type 5)
6. E2 ใช้ metric ภายนอกคงที่; E1 บวก cost ภายในไปยัง ASBR ด้วย
7. ไม่รับ type 5 — ได้ default route จาก ABR
8. เมื่อ area นั้นมี ASBR (เช่น สาขาที่ redistribute static/ISP ของตัวเอง) แต่ยังอยากลด LSA ภายนอก
9. `area 10 range 10.10.0.0 255.255.0.0` (ใต้ `router ospf`)
10. ตรวจลิงก์/เพื่อนบ้านเสียภายในเสี้ยววินาที แทนการรอ dead interval ทำให้ converge เร็วขึ้น
</details>

---

➡️ ต่อไป: **Level 47 — EIGRP**
