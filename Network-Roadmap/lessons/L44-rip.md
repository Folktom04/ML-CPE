# บทเรียน Level 44 — RIP (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจการทำงานของ RIP ซึ่งเป็นตัวอย่างคลาสสิกของ Distance Vector · ตั้ง RIPv2/RIPng · เข้าใจ timer, auto-summary, passive interface · รู้ข้อจำกัดและวิธี migrate ไป OSPF

> 📌 RIP แทบไม่ถูกเลือกใช้ในเครือข่ายใหม่แล้ว แต่ยังต้องรู้เพราะ (1) เป็นพื้นฐานที่อธิบาย distance vector ได้ชัดที่สุด (2) ยังเจอในอุปกรณ์เก่า/ระบบอุตสาหกรรม/อุปกรณ์ราคาประหยัด (3) ยังถูกถามในการสอบและสัมภาษณ์

---

## 1. RIP คืออะไร

**RIP (Routing Information Protocol)** — routing protocol แบบ **distance vector** ที่เก่าแก่ที่สุดที่ยังใช้อยู่
- **Metric = hop count** (จำนวน router ที่ต้องผ่าน)
- **Max 15 hop** — 16 = **unreachable (infinity)** → ใช้ได้กับเครือข่ายเล็กเท่านั้น
- ส่ง **ทั้ง routing table** ให้เพื่อนบ้าน **ทุก 30 วินาที**
- **AD = 120**, ใช้ **UDP 520** (RIPng ใช้ UDP 521)

| เวอร์ชัน | ลักษณะ |
|---|---|
| **RIPv1** | **Classful** (ไม่ส่ง subnet mask → ไม่รองรับ VLSM), ส่งแบบ **broadcast**, ไม่มี authentication — **เลิกใช้** |
| **RIPv2** | **Classless** (ส่ง mask, รองรับ VLSM/CIDR), ส่ง **multicast 224.0.0.9**, รองรับ **authentication (MD5)**, มี route tag |
| **RIPng** | สำหรับ **IPv6** (multicast ff02::9) |

---

## 2. การทำงาน (ตัวอย่าง)

```
 10.1.0.0/24 ── R1 ── R2 ── R3 ── 10.3.0.0/24

 เริ่มต้น: แต่ละ router รู้แค่วงที่ต่อตรง (metric 0)
 รอบที่ 1 (30 วิ): R1 บอก R2 ว่า "10.1.0.0 อยู่ห่างฉัน 0 hop" → R2 บันทึก 10.1.0.0 via R1 metric 1
                    R3 บอก R2 ว่า "10.3.0.0 0 hop"          → R2 บันทึก 10.3.0.0 via R3 metric 1
 รอบที่ 2: R2 บอก R1 ว่า "10.3.0.0 1 hop" → R1 บันทึก metric 2 · R2 บอก R3 ทำนองเดียวกัน
 → converge: ทุกตัวรู้ทุกวง
```
ข้อเสีย: ต้องรอเป็นรอบ ๆ ข่าวจึงเดินทางได้ทีละ hop → **converge ช้า** ในเครือข่ายที่ใหญ่ขึ้น

---

## 3. Timers ของ RIP

| Timer | ค่าเริ่มต้น | ความหมาย |
|---|---|---|
| **Update** | 30 วินาที | ส่ง routing table ให้เพื่อนบ้าน |
| **Invalid** | 180 วินาที | ไม่ได้ยิน update ของ route นี้นานเท่านี้ → ถือว่า route ใช้ไม่ได้ (metric 16) แต่ยังอยู่ใน table |
| **Hold-down** | 180 วินาที | (Cisco) ช่วงที่ไม่รับข้อมูล route นั้นที่แย่กว่าเดิม — กันข่าวเก่า |
| **Flush** | 240 วินาที | ลบ route ออกจาก table |

→ ถ้าเพื่อนบ้านหายไปเงียบ ๆ (ไม่ใช่ลิงก์ down) อาจใช้เวลา **3–4 นาที** กว่าจะรู้ — ช้ามากสำหรับปัจจุบัน
(ถ้าลิงก์ down ตรง ๆ จะส่ง **triggered update** ทันที)

---

## 4. ตั้งค่า RIPv2 (Cisco)

```
router rip
 version 2
 no auto-summary                         ! สำคัญมาก (ดูข้อ 5)
 network 10.0.0.0                        ! classful network — เปิด RIP บน interface ที่อยู่ใน 10.x.x.x ทั้งหมด
 network 192.168.1.0
 passive-interface GigabitEthernet0/1    ! LAN ผู้ใช้: ประกาศวง แต่ไม่ส่ง update ออกไป
 default-information originate           ! ประกาศ default route (ถ้ามี)
!
! Authentication
key chain RIP-KEYS
 key 1
  key-string S3cr3t!
interface GigabitEthernet0/0
 ip rip authentication mode md5
 ip rip authentication key-chain RIP-KEYS
```
> ⚠️ คำสั่ง `network` ของ RIP รับเฉพาะ **classful network** (เช่น 10.0.0.0, 172.16.0.0, 192.168.1.0) ไม่มี wildcard — จะเปิดบน **ทุก interface** ที่อยู่ในวงนั้น

### RIPng (IPv6)
```
ipv6 unicast-routing
ipv6 router rip RIPNG
interface GigabitEthernet0/0
 ipv6 rip RIPNG enable                   ! เปิดที่ interface แทนคำสั่ง network
```

### ตรวจสอบ
```
show ip protocols                        ! version, timers, networks, passive interfaces, neighbors (routing information sources)
show ip route rip
R    10.3.0.0/24 [120/2] via 10.255.0.2, 00:00:12, GigabitEthernet0/0
                  ↑AD ↑hop                ↑ อายุของข้อมูล (รีเซ็ตทุก 30 วิ)
show ip rip database
debug ip rip                             ! ดู update ที่รับ/ส่ง (ใช้ใน lab)
```

---

## 5. Auto-Summary — ทำไมต้องปิด

**Auto-summary** สรุป route เป็น classful boundary อัตโนมัติเมื่อส่งข้าม major network ต่างกัน ซึ่งทำให้ **discontiguous network** พัง

```
 10.1.1.0/24 ── R1 ──172.16.0.0/30── R2 ──172.16.0.4/30── R3 ── 10.3.3.0/24

 auto-summary เปิด: R1 ประกาศ "10.0.0.0/8" · R3 ก็ประกาศ "10.0.0.0/8"
 → R2 เห็น 10.0.0.0/8 สองทาง (metric เท่ากัน) → ส่ง traffic ไป 10.1.1.x สลับไปทาง R3 ครึ่งหนึ่ง ❌
 no auto-summary: R1 ประกาศ 10.1.1.0/24, R3 ประกาศ 10.3.3.0/24 → ถูกต้อง ✅
```
(IOS รุ่นใหม่ปิด auto-summary เป็นค่าเริ่มต้นแล้ว แต่ควรใส่ให้ชัดเจน)

---

## 6. ข้อจำกัดของ RIP (ทำไมองค์กรไม่ใช้)

| ข้อจำกัด | ผลกระทบ |
|---|---|
| **Hop count ไม่สนใจ bandwidth** | เลือกทาง 2 hop ผ่านลิงก์ 10 Mbps แทน 3 hop ผ่าน 10 Gbps |
| **Max 15 hop** | ใช้กับเครือข่ายใหญ่ไม่ได้ |
| **Converge ช้า** (invalid/hold-down นาที) | ระบบล่มนานเมื่อเส้นทางเปลี่ยน |
| **ส่งทั้ง table ทุก 30 วินาที** | เปลือง bandwidth/CPU ในเครือข่ายที่มี route มาก |
| **ไม่มี area/hierarchy** | scale ไม่ได้ |

**ยังพบได้ใน:** เครือข่ายเก่าที่ยังไม่ migrate, อุปกรณ์ราคาประหยัด/SOHO, ระบบอุตสาหกรรมบางแบบ, การแลก route กับอุปกรณ์ที่รองรับแค่ RIP, lab

---

## 7. Migrate จาก RIP → OSPF โดยไม่หยุดระบบ (ใช้ AD)

```
 1) เปิด OSPF ขนานกับ RIP บนทุก router (ยังไม่ปิด RIP)
 2) OSPF (AD 110) ชนะ RIP (AD 120) → route จาก OSPF ลง table แทนอัตโนมัติ
 3) ตรวจว่าทุก route เป็น "O" ครบ (show ip route) และ OSPF neighbor ครบ
 4) ทดสอบการเชื่อมต่อ/failover
 5) ปิด RIP ทีละ router (no router rip) ในช่วง maintenance
 6) ถ้ามีปัญหา: เปิด RIP คืน (rollback)
```
เทคนิคเดียวกันใช้กับการย้ายจาก protocol หนึ่งไปอีก protocol ได้ทั่วไป (เช่น EIGRP → OSPF ต้องปรับ AD เพราะ EIGRP 90 < OSPF 110 — Level 47)

---

## 8. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| RIP เลือกเส้นทางที่เร็วที่สุด | เลือกเส้นทางที่ **hop น้อยที่สุด** ไม่สนใจความเร็ว |
| RIPv2 รองรับ VLSM เพราะคำสั่ง network ใส่ mask ได้ | คำสั่ง network ยังเป็น classful แต่ **update ส่ง mask ไปด้วย** จึงรองรับ VLSM |
| Hop 16 ใช้ได้ | 16 = unreachable |
| passive-interface ทำให้ไม่ประกาศวงนั้น | ยังประกาศ แค่ไม่ส่ง update ออกทาง interface นั้น |

---

## 9. Cheat Sheet

```
RIP = distance vector · metric = hop count · max 15 (16 = unreachable) · AD 120
v1 classful/broadcast (เลิกใช้) · v2 classless/multicast 224.0.0.9/MD5 · RIPng IPv6 ff02::9
UDP 520 (RIPng 521) · update 30s · invalid 180s · hold-down 180s · flush 240s
router rip → version 2 → no auto-summary → network <classful> → passive-interface
show ip protocols · show ip route rip · debug ip rip
ข้อจำกัด: ไม่สนใจ bandwidth, 15 hop, converge ช้า, ส่งทั้ง table
Migrate → OSPF: รันขนาน (AD 110 < 120) → ตรวจ → ปิด RIP
```

---

## 10. แบบทดสอบ 10 ข้อ

1. RIP เป็น routing protocol ประเภทใด ใช้ metric อะไร
2. hop count สูงสุดที่ใช้ได้ และค่าใดหมายถึง unreachable
3. RIPv1 กับ RIPv2 ต่างกันอย่างไร (3 ข้อ)
4. RIPv2 ส่ง update ไปที่ address ใด ใช้ port อะไร
5. Update timer และ invalid timer ค่าเริ่มต้นเท่าไร
6. ทำไมต้องใส่ `no auto-summary`
7. คำสั่ง `network 10.1.1.0` ใน RIP มีผลอย่างไร
8. ยกข้อจำกัดของ RIP 3 ข้อ
9. AD ของ RIP เท่าไร และใช้ประโยชน์จากค่า AD ในการ migrate ไป OSPF อย่างไร
10. RIP เลือกเส้นทาง A (2 hop ผ่านลิงก์ 10 Mbps) หรือ B (3 hop ผ่านลิงก์ 1 Gbps)

<details><summary><b>เฉลย</b></summary>

1. Distance vector; metric = hop count
2. 15 hop; 16 = unreachable
3. v2 เป็น classless (ส่ง mask, รองรับ VLSM), ส่งแบบ multicast (224.0.0.9) แทน broadcast, รองรับ authentication
4. 224.0.0.9, UDP 520
5. Update 30 วินาที, Invalid 180 วินาที
6. ป้องกันการสรุป route ตาม classful boundary ซึ่งทำให้ discontiguous network ทำงานผิด
7. ถูกแปลงเป็น classful (10.0.0.0) → เปิด RIP บนทุก interface ที่อยู่ในวง 10.0.0.0/8
8. ไม่สนใจ bandwidth, จำกัด 15 hop, converge ช้า, ส่งทั้ง table ทุก 30 วินาที, ไม่มี hierarchy
9. AD 120 — รัน OSPF (AD 110) ขนาน route ของ OSPF จะชนะและลง table แทนอัตโนมัติ แล้วจึงปิด RIP
10. A (hop น้อยกว่า) แม้จะช้ากว่า
</details>

---

➡️ ต่อไป: **Level 45 — OSPF Single Area**
