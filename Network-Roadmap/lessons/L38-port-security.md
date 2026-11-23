# บทเรียน Level 38 — Port Security & Access Control บน Switch (ฉบับละเอียด)

> อ่านจบแล้วจะ: จำกัดอุปกรณ์ที่เสียบพอร์ตได้ด้วย Port Security · เลือก violation mode · ใช้ sticky MAC · กู้ err-disabled อัตโนมัติ · รู้จัก Private VLAN, Protected Port และ Storm Control · สร้าง access-port template มาตรฐาน

---

## 1. ทำไมต้องควบคุมพอร์ต

พอร์ต LAN ที่ผนังห้องประชุม/โถงต้อนรับ = **ประตูเข้าเครือข่ายภายใน** ถ้าไม่ควบคุม
- คนนอกเสียบโน้ตบุ๊กแล้วได้ IP เข้าระบบภายในทันที
- พนักงานเสียบ **switch/router บ้าน** → loop, rogue DHCP
- ผู้โจมตีทำ **MAC flooding** (CAM overflow) ให้ switch ทำงานเหมือน hub แล้วดักข้อมูล

**ระดับการควบคุม (จากพื้นฐานถึงสูง)**
1. ปิดพอร์ตที่ไม่ใช้ + parking VLAN (Level 32)
2. **Port Security** — จำกัดจำนวน/รายการ MAC
3. DHCP snooping, Dynamic ARP Inspection (Level 63)
4. **802.1X / NAC** — ยืนยันตัวตนผู้ใช้/อุปกรณ์ก่อนเข้าเครือข่าย (Level 66, ดีที่สุด)

---

## 2. Port Security

กำหนดว่าพอร์ตหนึ่ง **ยอมรับได้กี่ MAC และ MAC ใดบ้าง**

```
interface GigabitEthernet1/0/5
 switchport mode access                         ! ต้องเป็น access หรือ trunk ที่ตั้งไว้ชัดเจน (ไม่ใช่ dynamic)
 switchport access vlan 10
 switchport port-security                       ! เปิดใช้ (สำคัญ: ลืมบรรทัดนี้ = ไม่ทำงาน)
 switchport port-security maximum 2             ! สูงสุด 2 MAC (เช่น IP phone + PC)
 switchport port-security mac-address sticky    ! เรียนรู้ MAC แล้วจำลง config
 switchport port-security violation restrict    ! ทำอะไรเมื่อละเมิด
 switchport port-security aging time 60         ! (ทางเลือก) ลบ MAC ที่เรียนรู้หลังไม่ใช้ 60 นาที
 switchport port-security aging type inactivity
```

### วิธีกำหนด MAC ที่อนุญาต
| วิธี | ลักษณะ |
|---|---|
| **Dynamic** (ค่าเริ่มต้น) | เรียนรู้ MAC แรก ๆ จนครบ maximum แต่ **หายเมื่อ reboot/พอร์ต down** |
| **Static** | กำหนด MAC เอง: `switchport port-security mac-address 0050.56a1.1111` |
| **Sticky** ⭐ | เรียนรู้อัตโนมัติแล้ว **เขียนลง running-config** (ต้อง `write memory` เพื่อให้คงอยู่หลัง reboot) — สะดวกที่สุดในการ roll-out |

### Violation Modes — เมื่อมี MAC เกิน/ไม่ได้รับอนุญาต

| Mode | ทิ้ง traffic ที่ผิด | ส่ง log/SNMP trap | เพิ่ม violation counter | ปิดพอร์ต (err-disabled) |
|---|---|---|---|---|
| **protect** | ✅ | ❌ | ❌ | ❌ |
| **restrict** | ✅ | ✅ | ✅ | ❌ |
| **shutdown** (ค่าเริ่มต้น) | ✅ | ✅ | ✅ | ✅ |

- **protect** เงียบเกินไป ไม่รู้ว่ามีเหตุการณ์ (ไม่แนะนำ)
- **restrict** ผู้ใช้ที่ถูกต้องยังใช้งานได้ และทีม IT ได้รับแจ้ง — นิยมใช้ในสำนักงาน
- **shutdown** เข้มที่สุด เหมาะกับพอร์ตสาธารณะ/ความเสี่ยงสูง แต่ต้องมีคนมาเปิดพอร์ต (หรือใช้ recovery)

### ตรวจสอบ
```
show port-security
Secure Port  MaxSecureAddr  CurrentAddr  SecurityViolation  Security Action
Gi1/0/5            2             2              3              Restrict

show port-security interface Gi1/0/5
show port-security address
show interfaces status err-disabled
```

---

## 3. err-disabled และการกู้คืน

เมื่อ violation mode = shutdown พอร์ตจะเข้า **err-disabled** (ไฟพอร์ตดับ)

**กู้ด้วยมือ** (หลังตรวจสอบสาเหตุ)
```
interface Gi1/0/5
 shutdown
 no shutdown
```
**กู้อัตโนมัติ** (พอร์ตกลับมาเองหลังเวลาที่กำหนด — ถ้าสาเหตุยังอยู่ จะถูกปิดอีก)
```
errdisable recovery cause psecure-violation
errdisable recovery cause bpduguard
errdisable recovery interval 300               ! 5 นาที
show errdisable recovery
```
**สาเหตุ err-disabled ที่พบบ่อย:** psecure-violation, bpduguard, udld, link-flap, dhcp-rate-limit, arp-inspection, storm-control

---

## 4. ข้อพิจารณาในการใช้ Port Security จริง

| สถานการณ์ | ตั้ง maximum |
|---|---|
| PC อย่างเดียว | 1 |
| IP phone + PC | 2 (บางรุ่น phone ใช้ MAC ในทั้ง data และ voice VLAN → 3) |
| Docking station/USB-LAN | MAC ของ dock อาจต่างจากเครื่อง |
| VM บนเครื่องผู้ใช้ (bridged) | MAC เพิ่มตามจำนวน VM |
| พอร์ตห้องประชุม/hot desk | ใช้ aging หรือ 802.1X แทน sticky |

**ข้อจำกัดของ Port Security**
- **MAC ปลอมได้ง่าย** (ผู้โจมตีคัดลอก MAC ของ printer มาใช้)
- **จัดการยาก** เมื่อมีหลายพันพอร์ต (ย้ายโต๊ะ/เปลี่ยนเครื่อง ต้องล้าง sticky)
- มือถือ/โน้ตบุ๊ก **สุ่ม MAC** (private address)
→ องค์กรขนาดใหญ่จึงใช้ **802.1X/NAC** (ยืนยันตัวตนด้วย certificate/บัญชี) และใช้ port security เป็นชั้นเสริม (เช่น จำกัดจำนวน MAC เพื่อป้องกัน MAC flooding)

---

## 5. Private VLAN (PVLAN)

แยกเครื่อง **ภายใน VLAN/subnet เดียวกัน** ไม่ให้คุยกันเอง แต่ยังออก gateway ได้

| ประเภทพอร์ต | คุยกับใครได้ |
|---|---|
| **Promiscuous** | ทุกพอร์ต (ใช้กับ router/gateway/firewall) |
| **Isolated** | **เฉพาะ promiscuous** (ไม่คุยกับเพื่อนบ้าน) |
| **Community** | สมาชิก community เดียวกัน + promiscuous |

```
          [Gateway] ← promiscuous
              │
   ┌──────────┼───────────┐
 [Guest A] [Guest B]   [Web1][Web2]
 isolated  isolated    community "WEB"
 (A กับ B คุยกันไม่ได้)  (Web1 กับ Web2 คุยกันได้)
```
**ใช้ที่:** Wi-Fi/LAN แขกในโรงแรม หอพัก, DMZ ที่ server ไม่ควรคุยกันเอง, ผู้ให้บริการ hosting — ประหยัด subnet (ไม่ต้องแบ่ง VLAN ให้ทุกลูกค้า)

**ทางเลือกที่ง่ายกว่า:** `switchport protected` (Protected Port) — พอร์ตที่เป็น protected คุยกันเองไม่ได้ภายใน switch เดียวกัน ส่วน Wi-Fi ใช้ **client isolation** บน AP

---

## 6. Storm Control

จำกัดปริมาณ broadcast/multicast/unknown unicast ที่เข้าพอร์ต — ลดความเสียหายจาก loop หรือเครื่องที่ติดมัลแวร์ส่ง broadcast รัว ๆ
```
interface range Gi1/0/1-46
 storm-control broadcast level 1.00            ! ไม่เกิน 1% ของ bandwidth
 storm-control multicast level 5.00
 storm-control action trap                     ! หรือ shutdown
```

---

## 7. Access-Port Template มาตรฐาน (รวมทุก Level ที่ผ่านมา)

```
interface range GigabitEthernet1/0/1 - 46
 description USER-PORT
 switchport mode access
 switchport access vlan 10
 switchport voice vlan 110
 switchport nonegotiate
 switchport port-security
 switchport port-security maximum 3
 switchport port-security violation restrict
 switchport port-security aging time 120
 switchport port-security aging type inactivity
 spanning-tree portfast
 spanning-tree bpduguard enable
 storm-control broadcast level 1.00
 storm-control action trap
 ip dhcp snooping limit rate 20                ! (เมื่อเปิด DHCP snooping — Level 63)
 no shutdown
!
interface range GigabitEthernet1/0/47 - 48
 description UNUSED
 switchport mode access
 switchport access vlan 999
 shutdown
!
errdisable recovery cause psecure-violation
errdisable recovery cause bpduguard
errdisable recovery interval 300
```
> 🏢 ใช้ template นี้เป็น "มาตรฐาน" ของทุก switch และตรวจ compliance ด้วยสคริปต์/automation (Tier 9)

---

## 8. แก้ปัญหา

| อาการ | ตรวจ |
|---|---|
| ผู้ใช้เปลี่ยนเครื่องใหม่แล้วใช้งานไม่ได้ | sticky จำ MAC เครื่องเก่า → `clear port-security sticky interface Gi1/0/5` |
| เสียบ phone + PC แล้ว PC ใช้ไม่ได้ | maximum น้อยเกินไป |
| พอร์ตดับเองเป็นระยะ | err-disabled (psecure, bpduguard) → `show interfaces status err-disabled` |
| ตั้ง port-security แล้วไม่มีผล | ลืมบรรทัด `switchport port-security` หรือพอร์ตเป็น dynamic mode |

---

## 9. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| Port security ป้องกันคนแปลกหน้าได้สมบูรณ์ | MAC ปลอมได้ ใช้ 802.1X สำหรับการยืนยันตัวตนจริง |
| sticky MAC อยู่ถาวรทันที | อยู่ใน running-config ต้อง write memory |
| protect mode ดีเพราะไม่รบกวนผู้ใช้ | ไม่มี log ทีม IT ไม่รู้ว่ามีเหตุการณ์ |
| เครื่องใน VLAN เดียวกันกันไม่ให้คุยกันไม่ได้ | ใช้ Private VLAN / protected port / client isolation |

---

## 10. Cheat Sheet

```
switchport mode access → switchport port-security → maximum N → mac-address sticky → violation restrict
Violation: protect (ทิ้งเงียบ) · restrict (ทิ้ง+log+counter) · shutdown (err-disable, ค่าเริ่มต้น)
show port-security [interface X | address] · clear port-security sticky interface X
err-disabled: shut/no shut · errdisable recovery cause psecure-violation · interval 300
PVLAN: promiscuous (gateway) · isolated (คุยแค่ gateway) · community (คุยในกลุ่ม)
protected port / Wi-Fi client isolation · storm-control broadcast level 1
Port security = ชั้นพื้นฐาน · องค์กรใหญ่ใช้ 802.1X/NAC
```

---

## 11. แบบทดสอบ 10 ข้อ

1. Port security ป้องกันปัญหาใดได้บ้าง (3 ข้อ)
2. คำสั่งที่จำเป็นต้องมีเพื่อเปิด port security
3. violation mode ใดทิ้ง traffic ส่ง log แต่ไม่ปิดพอร์ต
4. ค่าเริ่มต้นของ violation mode คืออะไร
5. sticky MAC ต่างจาก dynamic อย่างไร
6. พอร์ตที่มี IP phone + PC ควรตั้ง maximum เท่าไร
7. คำสั่งกู้พอร์ต err-disabled ด้วยมือ และตั้งกู้อัตโนมัติสำหรับ port security
8. ข้อจำกัดหลักของ port security
9. Isolated port ใน PVLAN คุยกับใครได้บ้าง
10. ผู้ใช้เปลี่ยนเครื่องใหม่แล้วพอร์ตไม่ยอมให้ใช้ ทำอย่างไร

<details><summary><b>เฉลย</b></summary>

1. อุปกรณ์ที่ไม่ได้รับอนุญาตเสียบเข้าระบบ, การเสียบ switch/hub ขยายพอร์ต, MAC flooding (CAM overflow)
2. `switchport port-security` (บนพอร์ตที่เป็น access/trunk แบบกำหนดชัด)
3. restrict
4. shutdown
5. sticky เรียนรู้อัตโนมัติและบันทึกลง running-config (เก็บถาวรได้เมื่อ write memory); dynamic หายเมื่อ reboot/พอร์ต down
6. 2 (บางรุ่นอาจต้อง 3)
7. `shutdown` แล้ว `no shutdown` ที่พอร์ต; `errdisable recovery cause psecure-violation` + `errdisable recovery interval <วินาที>`
8. MAC ปลอมได้ง่าย, จัดการยากเมื่อมีพอร์ตจำนวนมาก, มีปัญหากับ MAC randomization
9. เฉพาะพอร์ต promiscuous (gateway)
10. ล้าง sticky MAC (`clear port-security sticky interface X`) หรือแก้ MAC ที่อนุญาต แล้วกู้พอร์ตถ้า err-disabled
</details>

---

➡️ ต่อไป: **Level 39 — CDP, LLDP & เอกสารเครือข่าย**
