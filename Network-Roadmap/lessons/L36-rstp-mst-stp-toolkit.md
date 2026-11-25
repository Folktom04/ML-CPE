# บทเรียน Level 36 — RSTP, MST & STP Toolkit (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจว่า RSTP converge เร็วได้อย่างไร · port role/state ใหม่ · ตั้ง MST สำหรับเครือข่ายหลายยี่ห้อ · ใช้ PortFast, BPDU Guard, BPDU Filter, Root Guard, Loop Guard, UDLD, Storm Control ได้ถูกที่ · เขียนมาตรฐาน STP ขององค์กรได้

---

## 1. RSTP — Rapid Spanning Tree (802.1w)

STP เดิม converge 30–50 วินาที ช้าเกินไปสำหรับเครือข่ายปัจจุบัน **RSTP converge ในระดับไม่กี่วินาทีหรือน้อยกว่า** และเป็นค่าเริ่มต้นของ switch รุ่นใหม่ส่วนใหญ่ (Cisco ใช้ **Rapid PVST+** = RSTP ต่อ VLAN)

### Port States (ลดเหลือ 3)

| 802.1D | RSTP |
|---|---|
| Disabled / Blocking / Listening | **Discarding** |
| Learning | **Learning** |
| Forwarding | **Forwarding** |

### Port Roles

| Role | หน้าที่ |
|---|---|
| **Root Port** | ทางที่ดีที่สุดไป root |
| **Designated Port** | พอร์ตที่ส่งต่อในแต่ละ segment |
| **Alternate Port** | **ทางสำรองไป root** (จาก switch อื่น) — พร้อมขึ้นเป็น root port ทันทีเมื่อ root port เสีย |
| **Backup Port** | สำรองของ designated port บน segment เดียวกัน (พบเมื่อมี hub — หายาก) |
| Edge Port | พอร์ตปลายทาง (= PortFast) เข้า forwarding ทันที |

### ทำไม RSTP เร็ว
1. **Alternate port เตรียมไว้ล่วงหน้า** — root port เสีย → alternate ขึ้นแทนทันที (ไม่ต้องรอ timer)
2. **Proposal/Agreement (handshake)** บนลิงก์ point-to-point — switch ตกลงกันโดยตรงแล้ว forwarding ได้เลย ไม่ต้องรอ forward delay
3. **ตรวจเพื่อนบ้านหายเร็ว** — ไม่ได้รับ BPDU 3 ครั้ง (6 วินาที) ก็ถือว่าเพื่อนบ้านหาย (เดิมรอ max age 20 วินาที)
4. **Edge port** ไม่ก่อ topology change

**Link type:** RSTP เร็วได้บนลิงก์ **point-to-point (full-duplex)** ส่วน shared (half-duplex/hub) จะกลับไปทำงานช้าแบบเดิม

```
spanning-tree mode rapid-pvst
show spanning-tree summary          ! ยืนยัน "Switch is in rapid-pvst mode"
```

---

## 2. MST — Multiple Spanning Tree (802.1s)

**ปัญหา:** PVST+/Rapid PVST+ รัน 1 instance ต่อ VLAN — VLAN 500 ตัว = 500 instance (กิน CPU) และเป็นของ Cisco (ยี่ห้ออื่นไม่รองรับเต็มรูปแบบ)

**MST:** จัดกลุ่ม **หลาย VLAN เข้า instance เดียว** (เช่น 2 instance พอสำหรับ load balancing) และเป็น **มาตรฐานเปิด** ใช้ร่วมกับยี่ห้ออื่นได้ (ALE, Aruba, Extreme, Huawei ฯลฯ)

```
 Instance 0 (IST) — ทุก VLAN ที่ไม่ได้ map + BPDU ของ region
 Instance 1 — VLAN 10,30,50 ... → root ที่ CORE-1
 Instance 2 — VLAN 20,40,60 ... → root ที่ CORE-2
```
### MST Region — ต้องตรงกัน 3 อย่าง (ไม่ตรง = คนละ region)
1. **Region name**
2. **Revision number**
3. **VLAN-to-instance mapping**

```
spanning-tree mode mst
spanning-tree mst configuration
 name CORP
 revision 1
 instance 1 vlan 10,30,50
 instance 2 vlan 20,40,60
exit
spanning-tree mst 0-1 priority 4096       ! CORE-1 เป็น root ของ instance 0,1
spanning-tree mst 2 priority 8192
!
show spanning-tree mst configuration
show spanning-tree mst 1
```
> ⚠️ เปลี่ยน mapping ต้องทำทุก switch ให้ตรงกัน — ระหว่างที่ไม่ตรงกันจะเกิด topology change/ไม่ optimal จึงควรวาง mapping ล่วงหน้าเผื่อ VLAN ในอนาคต

| | Rapid PVST+ | MST |
|---|---|---|
| Instance | 1 ต่อ VLAN | หลาย VLAN ต่อ instance |
| มาตรฐาน | Cisco | IEEE 802.1s (ทุกยี่ห้อ) |
| ความซับซ้อน | ง่าย | ต้องวาง region/mapping |
| เหมาะกับ | เครือข่าย Cisco ขนาดเล็ก–กลาง | VLAN จำนวนมาก, หลายยี่ห้อ |

---

## 3. STP Toolkit — ฟีเจอร์ป้องกันที่ต้องรู้

### 3.1 PortFast (Edge Port)
- พอร์ตที่ต่อ **อุปกรณ์ปลายทาง** (PC, printer, server, AP บางแบบ) → ข้าม listening/learning เข้า **forwarding ทันที** และไม่สร้าง TCN
- แก้ปัญหา PC รอ 30 วินาที/DHCP timeout
- ⚠️ **ห้ามใส่พอร์ตที่ต่อ switch** (เสี่ยง loop)
```
interface range Gi1/0/1-46
 spanning-tree portfast
! หรือเปิดทุก access port
spanning-tree portfast default
! trunk ไป server/hypervisor
interface Gi1/0/47
 spanning-tree portfast trunk
```

### 3.2 BPDU Guard ⭐
- ถ้าพอร์ตที่ตั้งไว้ **ได้รับ BPDU** (มีคนเสียบ switch เข้ามา) → **err-disable พอร์ตทันที**
- ใช้คู่กับ PortFast ที่พอร์ตผู้ใช้ **ทุกพอร์ต** — ป้องกัน loop จากผู้ใช้เสียบ switch บ้าน/ต่อสายวน
```
interface range Gi1/0/1-46
 spanning-tree bpduguard enable
! หรือ global (มีผลกับทุกพอร์ต PortFast)
spanning-tree portfast bpduguard default
! กู้คืนอัตโนมัติ (ทางเลือก)
errdisable recovery cause bpduguard
errdisable recovery interval 300
```

### 3.3 BPDU Filter
- **ไม่ส่งและไม่รับ BPDU** บนพอร์ต → เท่ากับปิด STP บนพอร์ตนั้น
- ⚠️ **อันตราย** ถ้าใช้ผิดที่ loop จะไม่ถูกตรวจจับ ใช้เฉพาะกรณีพิเศษ (เช่น ขอบเขตกับผู้ให้บริการ) — **โดยทั่วไปใช้ BPDU Guard แทน**
- แบบ global (`spanning-tree portfast bpdufilter default`) ปลอดภัยกว่า: ถ้าได้รับ BPDU พอร์ตจะออกจาก PortFast และกลับมาทำ STP ปกติ

### 3.4 Root Guard
- ป้องกันไม่ให้ switch ที่อยู่ปลายทาง **ประกาศตัวเป็น root** (BPDU ที่ดีกว่า/superior)
- ใส่ที่ **พอร์ต downlink ที่ไม่ควรมี root อยู่ฝั่งนั้น** (เช่น distribution → access, หรือพอร์ตที่ต่อ switch ของผู้อื่น)
- ถ้าได้รับ superior BPDU → พอร์ตเข้าสถานะ **root-inconsistent** (block) จนกว่า BPDU นั้นหยุด
```
interface Gi1/0/1
 description DOWNLINK-TO-ACCESS
 spanning-tree guard root
```

### 3.5 Loop Guard
- ป้องกันกรณี **unidirectional link** (สายไฟเบอร์เส้นรับขาดเส้นเดียว): พอร์ต blocked หยุดได้รับ BPDU → STP เดิมจะคิดว่าไม่มีเพื่อนบ้าน แล้วเปลี่ยนเป็น forwarding → **เกิด loop**
- Loop Guard: ถ้าพอร์ต root/alternate หยุดได้รับ BPDU → เข้า **loop-inconsistent** (block) แทนการเปิด
- ใช้บนพอร์ต **ระหว่าง switch** (root/alternate port)
```
spanning-tree loopguard default
```

### 3.6 UDLD (UniDirectional Link Detection — Cisco)
- ตรวจ **ลิงก์ทางเดียว** ระดับ L1/L2 โดยตรง (ส่งข้อความหากันและต้องได้คำตอบ) เหมาะกับไฟเบอร์
- **Aggressive mode** → err-disable พอร์ตเมื่อตรวจพบ
```
udld aggressive               ! global (มีผลกับพอร์ตไฟเบอร์)
interface Te1/1/1
 udld port aggressive
```

### 3.7 Storm Control
- จำกัดปริมาณ **broadcast/multicast/unknown unicast** ต่อพอร์ต (เป็น % ของ bandwidth หรือ pps) — ลดความเสียหายเมื่อเกิด storm
```
interface range Gi1/0/1-46
 storm-control broadcast level 1.00
 storm-control multicast level 5.00
 storm-control action trap               ! หรือ shutdown
```

### สรุป: ใส่อะไรที่ไหน
```
                 [CORE-1 root]═══════[CORE-2 secondary]
          Root Guard │                    │ Root Guard           ← downlink จาก core/distribution
                     │  Loop Guard/UDLD    │                       (ลิงก์ระหว่าง switch)
                [ACCESS SW]──────────[ACCESS SW]
          PortFast + BPDU Guard + Storm Control                  ← พอร์ตผู้ใช้ทุกพอร์ต
               PC   PC   AP   Printer
```

| พอร์ต | ฟีเจอร์ |
|---|---|
| **Access (ผู้ใช้)** | PortFast + **BPDU Guard** + storm control (+ port security/802.1X) |
| **Uplink ระหว่าง switch** | Loop Guard (หรือ UDLD สำหรับไฟเบอร์) |
| **Downlink จาก core/distribution ไป access** | **Root Guard** |
| **พอร์ตต่อ server/hypervisor (trunk)** | PortFast trunk + BPDU Guard |
| ทั้งเครื่อง | `spanning-tree mode rapid-pvst` (หรือ mst) + กำหนด root priority |

---

## 4. err-disabled — อ่านและกู้คืน

```
Switch# show interfaces status err-disabled
Port      Name         Status       Reason               Err-disabled Vlans
Gi1/0/12  USER-3F-12   err-disabled bpduguard

! กู้คืนด้วยมือ (หลังเอาอุปกรณ์ต้นเหตุออกแล้ว)
interface Gi1/0/12
 shutdown
 no shutdown
show errdisable recovery
```

---

## 5. มาตรฐาน STP ขององค์กร (ตัวอย่าง)

1. Mode: **Rapid PVST+** (เครือข่าย Cisco ล้วน) หรือ **MST** (หลายยี่ห้อ)
2. Root primary = CORE-1 (priority 4096), secondary = CORE-2 (8192) ตรงกับ HSRP active/standby
3. Access port ทุกพอร์ต: PortFast + BPDU Guard
4. Downlink จาก distribution: Root Guard
5. Uplink ไฟเบอร์: UDLD aggressive / Loop Guard
6. ห้ามใช้ BPDU Filter ระดับพอร์ตโดยไม่ได้รับอนุมัติ
7. ตรวจ TCN และ err-disable ใน monitoring

---

## 6. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| PortFast ปิด STP บนพอร์ต | ยังทำ STP อยู่ แค่ข้ามการรอ (ใส่ BPDU Guard คู่กันเสมอ) |
| BPDU Filter กับ BPDU Guard คือสิ่งเดียวกัน | Guard = ปิดพอร์ตเมื่อเห็น BPDU (ปลอดภัย) · Filter = ไม่สนใจ BPDU (เสี่ยง loop) |
| MST region ตรงกันแค่ชื่อก็พอ | ต้องตรงทั้งชื่อ revision และ mapping |
| Root Guard ใส่ที่ uplink ไป root | ใส่ที่ **downlink** ที่ไม่ควรมี root อยู่ฝั่งนั้น |

---

## 7. Cheat Sheet

```
RSTP (802.1w): Discarding/Learning/Forwarding · Root/Designated/Alternate/Backup/Edge
เร็วเพราะ: alternate เตรียมไว้ + proposal/agreement + ตรวจหาย 6 วิ · ต้อง P2P full-duplex
spanning-tree mode rapid-pvst
MST (802.1s): หลาย VLAN ต่อ instance · มาตรฐานเปิด · region = name + revision + mapping ตรงกัน
PortFast + BPDU Guard = พอร์ตผู้ใช้ · Root Guard = downlink · Loop Guard/UDLD = ลิงก์ระหว่าง switch
BPDU Filter = อันตราย · Storm control = จำกัด broadcast/multicast
show interfaces status err-disabled · shut/no shut · errdisable recovery
```

---

## 8. แบบทดสอบ 10 ข้อ

1. RSTP มี port state อะไรบ้าง
2. Alternate port คืออะไร ช่วยให้ converge เร็วอย่างไร
3. ทำไม RSTP converge เร็วกว่า 802.1D (3 เหตุผล)
4. MST แก้ปัญหาอะไรของ PVST+
5. MST region ต้องตรงกันในเรื่องใดบ้าง
6. PortFast ใช้กับพอร์ตแบบไหน ห้ามใช้กับพอร์ตแบบไหน
7. BPDU Guard ทำอะไรเมื่อได้รับ BPDU
8. Root Guard ควรใส่ที่พอร์ตใด
9. Loop Guard และ UDLD ป้องกันปัญหาอะไร
10. พอร์ตผู้ใช้เป็น err-disabled reason bpduguard ควรทำอย่างไร

<details><summary><b>เฉลย</b></summary>

1. Discarding, Learning, Forwarding
2. พอร์ตสำรองที่เป็นทางไป root อีกเส้น — เมื่อ root port เสียจะขึ้นเป็น root port ทันทีโดยไม่ต้องรอ timer
3. มี alternate port เตรียมไว้, ใช้ proposal/agreement บนลิงก์ P2P แทนการรอ forward delay, ตรวจเพื่อนบ้านหายภายใน 3 hello (6 วินาที), edge port ไม่ก่อ topology change
4. จำนวน instance มากเกิน (1 ต่อ VLAN) กิน CPU และไม่เป็นมาตรฐานเปิด — MST รวมหลาย VLAN ต่อ instance และใช้ได้ทุกยี่ห้อ
5. Region name, revision number, VLAN-to-instance mapping
6. พอร์ตที่ต่ออุปกรณ์ปลายทาง (PC, printer, server); ห้ามใช้กับพอร์ตที่ต่อ switch
7. err-disable (ปิด) พอร์ตทันที
8. Downlink จาก core/distribution ไปยัง access หรือพอร์ตที่ต่อเครือข่ายของผู้อื่น ซึ่งไม่ควรมี root อยู่ฝั่งนั้น
9. Unidirectional link ที่ทำให้พอร์ต blocked เปลี่ยนเป็น forwarding และเกิด loop
10. หาและเอาอุปกรณ์ต้นเหตุออก (เช่น switch ที่ผู้ใช้เสียบ) แล้ว `shutdown` / `no shutdown` พอร์ต (หรือรอ errdisable recovery) และบันทึกเหตุการณ์
</details>

---

➡️ ต่อไป: **Level 37 — EtherChannel / Link Aggregation (LACP)**
