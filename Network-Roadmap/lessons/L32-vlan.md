# บทเรียน Level 32 — VLAN (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจว่า VLAN คืออะไรและทำไมทุกองค์กรต้องใช้ · ตั้ง VLAN, access port, voice VLAN · ออกแบบ VLAN plan · รู้ best practice ด้านความปลอดภัย · แก้ปัญหาที่เกี่ยวกับ VLAN

---

## 1. VLAN คืออะไร

**VLAN (Virtual LAN)** คือการแบ่ง switch ตัวเดียว (หรือหลายตัว) ออกเป็น **หลายเครือข่ายเสมือนที่แยกกัน** ในระดับ Layer 2

- **1 VLAN = 1 broadcast domain = (ปกติ) 1 subnet**
- เครื่องต่าง VLAN **คุยกันตรง ๆ ไม่ได้** ต้องผ่านอุปกรณ์ L3 (router/L3 switch/firewall) — Level 34

```
 ไม่มี VLAN: ทุกพอร์ตอยู่วงเดียวกัน broadcast ถึงทุกคน
 ┌──────────────── SWITCH ────────────────┐
 │ บัญชี บัญชี  HR  HR  Guest Guest  กล้อง   │   ← ทุกคนเห็น broadcast กัน คุยกันได้หมด

 มี VLAN:
 ┌──────────────── SWITCH ────────────────┐
 │ [VLAN 10 บัญชี] [VLAN 20 HR] [VLAN 50 Guest] [VLAN 60 CCTV] │
     10.0.10.0/24    10.0.20.0/24  10.0.50.0/24    10.0.60.0/24
```

> 💡 **เปรียบเทียบ:** switch คืออาคาร VLAN คือ **การกั้นห้อง** — อยู่อาคารเดียวกัน แต่คนต่างห้องคุยกันต้องผ่าน "ประตูที่มี รปภ." (router/firewall)

---

## 2. ทำไมต้องใช้ VLAN

| ประโยชน์ | อธิบาย |
|---|---|
| **ความปลอดภัย** | แยก Guest, IoT, กล้อง CCTV ออกจากระบบงาน; ควบคุมการคุยข้าม VLAN ด้วย ACL/firewall |
| **ลด broadcast** | broadcast domain เล็กลง เครือข่ายเสถียรขึ้น |
| **จัดการง่าย** | จัดกลุ่มตามหน้าที่ ไม่ผูกกับตำแหน่ง (บัญชีอยู่คนละชั้นก็อยู่ VLAN เดียวกันได้) |
| **QoS** | ให้ voice VLAN ได้ลำดับความสำคัญสูง |
| **ลดต้นทุน** | ไม่ต้องซื้อ switch แยกให้แต่ละกลุ่ม |
| **จำกัดขอบเขตปัญหา** | loop/broadcast storm ลามแค่ใน VLAN นั้น |

---

## 3. VLAN ID และประเภท

- **VLAN ID** มี 12 บิต → 0–4095 ใช้ได้ **1–4094** (0 และ 4095 สงวน)
- **Normal range:** 1–1005 · **Extended range:** 1006–4094
- **VLAN 1** = default VLAN ทุกพอร์ตอยู่ VLAN 1 เป็นค่าเริ่มต้น ลบไม่ได้
- 1002–1005 สงวนไว้สำหรับเทคโนโลยีเก่า (Token Ring/FDDI)

| ประเภท VLAN | ใช้ทำอะไร |
|---|---|
| **Data/User VLAN** | เครื่องผู้ใช้ |
| **Voice VLAN** | IP phone (ได้ QoS) |
| **Management VLAN** | IP สำหรับจัดการ switch/AP/อุปกรณ์ (แยกจากผู้ใช้) |
| **Native VLAN** | VLAN ที่วิ่งบน trunk แบบไม่มี tag (Level 33) |
| **Parking/Blackhole VLAN** | VLAN ที่ไม่ได้ใช้งาน เอาพอร์ตว่างมาใส่ไว้ |

---

## 4. Access Port

**Access port** = พอร์ตที่เป็นสมาชิก **VLAN เดียว** (data) ใช้ต่อ PC, printer, AP (ในบางแบบ), กล้อง — frame ที่ออกไปหาเครื่อง **ไม่มี VLAN tag** อุปกรณ์ปลายทางไม่รู้ด้วยซ้ำว่าอยู่ VLAN อะไร

### ตั้งค่า Cisco
```
vlan 10
 name ACCOUNTING
vlan 20
 name HR
vlan 110
 name VOICE
vlan 999
 name PARKING
!
interface range GigabitEthernet1/0/1 - 20
 description USER-ACCOUNTING
 switchport mode access                  ! บังคับเป็น access (ปิดการเจรจา trunk)
 switchport access vlan 10
 switchport voice vlan 110
 spanning-tree portfast                  ! (Level 36)
 spanning-tree bpduguard enable
!
interface range GigabitEthernet1/0/21 - 46
 description UNUSED
 switchport mode access
 switchport access vlan 999
 shutdown                                ! ปิดพอร์ตที่ไม่ใช้
```
> ถ้าสั่ง `switchport access vlan 30` แต่ยังไม่ได้สร้าง VLAN 30 — Cisco จะสร้างให้อัตโนมัติ แต่ควรสร้างพร้อมตั้งชื่อเองเพื่อความเป็นระเบียบ

### ตรวจสอบ
```
show vlan brief
VLAN Name          Status    Ports
---- ------------- --------- ---------------------------
1    default       active    Gi1/0/47, Gi1/0/48
10   ACCOUNTING    active    Gi1/0/1, Gi1/0/2, ... Gi1/0/20
20   HR            active
110  VOICE         active    Gi1/0/1, ... (แสดงพอร์ตที่มี voice VLAN)
999  PARKING       active    Gi1/0/21, ...

show interfaces Gi1/0/5 switchport      ! Administrative/Operational Mode, Access VLAN, Voice VLAN
show interfaces status                  ! คอลัมน์ Vlan บอก VLAN ของแต่ละพอร์ต
```
(พอร์ตที่เป็น trunk จะไม่แสดงใน `show vlan brief`)

---

## 5. Voice VLAN

ใช้เมื่อ **PC ต่อผ่าน IP phone** (phone มี switch ในตัว 2 พอร์ต) ทำให้ใช้สาย/พอร์ตเดียวได้ทั้งคู่

```
 [PC] ── [IP Phone] ── Gi1/0/5 [SWITCH]
           │
  PC: untagged → VLAN 10 (data)
  Phone: tagged 802.1Q → VLAN 110 (voice) + CoS 5 (ลำดับความสำคัญสูง)
```
- Switch บอก phone ว่า voice VLAN คืออะไรผ่าน **CDP** (Cisco phone) หรือ **LLDP-MED** (ยี่ห้ออื่น) หรือ DHCP option
- พอร์ตลักษณะนี้ยังนับเป็น access port ที่มี voice VLAN (บางคนเรียก "multi-VLAN access port")
- ถ้าใช้ port security ต้องตั้ง maximum MAC อย่างน้อย 2 (phone + PC)

---

## 6. ออกแบบ VLAN Plan (ตัวอย่างองค์กร)

| VLAN | ชื่อ | Subnet | Gateway | หมายเหตุ |
|---|---|---|---|---|
| 10 | USERS-HQ | 10.1.10.0/23 | .1 | ผู้ใช้ทั่วไป |
| 20 | VOICE | 10.1.20.0/24 | .1 | IP phone + QoS |
| 30 | PRINTER | 10.1.30.0/24 | .1 | |
| 40 | WIFI-CORP | 10.1.40.0/22 | .1 | 802.1X |
| 50 | WIFI-GUEST | 10.1.50.0/23 | firewall | ออกได้เฉพาะ internet |
| 60 | CCTV | 10.1.60.0/24 | .1 | เข้าได้เฉพาะจาก NVR |
| 70 | IOT | 10.1.70.0/24 | .1 | จำกัดเข้มงวด |
| 99 | MGMT | 10.1.99.0/24 | .1 | อุปกรณ์เครือข่าย, เข้าได้จาก IT เท่านั้น |
| 100 | SERVERS | 10.1.100.0/24 | .1 | |
| 999 | PARKING | — | — | พอร์ตว่าง |

**หลักการออกแบบ**
- แยกตาม **หน้าที่ + ระดับความเสี่ยง** (ไม่ใช่แยกตามชั้นอย่างเดียว)
- ให้ **เลข VLAN สอดคล้องกับ subnet** (VLAN 20 → 10.x.20.0) อ่านง่าย
- ขนาด subnet เผื่อการเติบโต (Level 9–10)
- ใช้ชื่อ VLAN ที่สื่อความหมาย เป็นมาตรฐานเดียวกันทุก switch
- บันทึกใน IPAM/NetBox

### VLAN กว้างแค่ไหน (L2 ข้ามหลาย switch)?
- **แนวทางปัจจุบัน:** อย่าขยาย VLAN เดียวไปทั่วทั้ง campus — จำกัด VLAN ให้อยู่ในอาคาร/distribution เดียว เพื่อลดขอบเขตของ loop/broadcast storm (ดู routed access ใน Level 40)

---

## 7. Best Practice ด้านความปลอดภัย

1. **ไม่ใช้ VLAN 1** สำหรับผู้ใช้/การจัดการ (เป็นค่าเริ่มต้นที่ผู้โจมตีรู้, control protocol ใช้)
2. **พอร์ตที่ไม่ใช้:** shutdown + ใส่ parking VLAN
3. **กำหนด `switchport mode access`** อย่างชัดเจนบนพอร์ตผู้ใช้ (ปิด DTP — ป้องกันผู้โจมตีเจรจาเป็น trunk)
4. **Management VLAN แยก** และจำกัดการเข้าถึง
5. **Native VLAN บน trunk** เป็น VLAN ที่ไม่ใช้งาน (Level 33)
6. VLAN **ไม่ใช่ระบบความปลอดภัยที่สมบูรณ์** — ต้องควบคุมการคุยข้าม VLAN ด้วย ACL/firewall และพิจารณา 802.1X/private VLAN

---

## 8. แก้ปัญหาที่เกี่ยวกับ VLAN

| อาการ | ตรวจ |
|---|---|
| เครื่องได้ IP ผิดวง / 169.254 | พอร์ตอยู่ VLAN ถูกไหม (`show interfaces status`), VLAN มีบน trunk ไป gateway ไหม, DHCP relay ของ VLAN นั้น |
| เครื่องใน VLAN เดียวกันแต่คนละ switch คุยกันไม่ได้ | VLAN ถูกสร้างบนทุก switch ไหม, allowed บน trunk ไหม (Level 33) |
| ย้ายโต๊ะแล้วใช้งานไม่ได้ | พอร์ตใหม่อยู่ VLAN อื่นหรือ shutdown/err-disabled |
| IP phone ไม่ได้ IP วง voice | voice VLAN ตั้งไหม, CDP/LLDP เปิดไหม, DHCP scope ของ voice |
| VLAN แสดง "act/lshut" หรือไม่อยู่ใน `show vlan` | VLAN ถูก shutdown หรือยังไม่ได้สร้าง |

---

## 9. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| ต่าง VLAN แต่ switch เดียวกันคุยกันได้ | ต้องผ่าน router/L3 switch |
| VLAN = subnet | ปกติจับคู่ 1:1 แต่ VLAN คือ L2, subnet คือ L3 |
| VLAN ทำให้ปลอดภัยสมบูรณ์ | ต้องมี ACL/firewall ควบคุมการข้ามวงและป้องกัน VLAN hopping |
| ใช้ VLAN 1 สะดวกดี | เป็น best practice ที่ควรหลีกเลี่ยง |

---

## 10. Cheat Sheet

```
VLAN = แบ่ง switch เป็นหลาย broadcast domain (L2) · 1 VLAN ≈ 1 subnet
ID 1-4094 · normal 1-1005 · extended 1006-4094 · VLAN 1 = default (อย่าใช้)
vlan 10 / name X · switchport mode access · switchport access vlan 10 · switchport voice vlan 110
พอร์ตว่าง: shutdown + parking VLAN
show vlan brief · show interfaces status · show interfaces X switchport
ประเภท: data · voice · management · native · parking
ข้าม VLAN ต้อง L3 + ควบคุมด้วย ACL/firewall
```

---

## 11. แบบทดสอบ 10 ข้อ

1. VLAN คืออะไร และ 1 VLAN เท่ากับอะไร
2. PC 2 เครื่องอยู่ VLAN 10 และ 20 บน switch เดียวกัน ping กันได้ไหม เพราะอะไร
3. VLAN ID ที่ใช้งานได้คือช่วงใด
4. ทำไมไม่ควรใช้ VLAN 1
5. คำสั่ง Cisco ตั้งพอร์ต Gi1/0/5 เป็น access VLAN 30 และ voice VLAN 120
6. Voice VLAN ทำงานอย่างไรเมื่อ PC ต่อผ่าน IP phone
7. พอร์ตที่ไม่ได้ใช้งานควรตั้งค่าอย่างไร
8. คำสั่งดูว่าพอร์ตไหนอยู่ VLAN ใด
9. การแยก Guest และ CCTV ไว้ VLAN ต่างหากมีประโยชน์อย่างไร
10. ผู้ใช้ย้ายโต๊ะแล้วได้ IP วงผิด ควรตรวจอะไรเป็นอย่างแรก

<details><summary><b>เฉลย</b></summary>

1. การแบ่งเครือข่าย L2 เสมือนบน switch — 1 VLAN = 1 broadcast domain (ปกติคู่กับ 1 subnet)
2. ไม่ได้ (ถ้าไม่มี routing) — ต่าง VLAN คือคนละ broadcast domain ต้องผ่าน L3
3. 1–4094
4. เป็นค่าเริ่มต้นของทุกพอร์ตและ control protocol ใช้ ผู้โจมตีคาดเดาได้ เสี่ยงต่อ VLAN hopping
5. `interface Gi1/0/5` → `switchport mode access` → `switchport access vlan 30` → `switchport voice vlan 120`
6. Phone ใช้ voice VLAN แบบ tagged (พร้อม CoS) ส่วน PC ใช้ data VLAN แบบ untagged บนพอร์ตเดียวกัน switch แจ้ง voice VLAN ผ่าน CDP/LLDP-MED
7. `shutdown` และใส่ parking VLAN (และกำหนด mode access)
8. `show vlan brief` หรือ `show interfaces status`
9. จำกัดการเข้าถึงระบบงานจากอุปกรณ์ความเสี่ยงสูง ลด lateral movement ควบคุม policy และลด broadcast
10. พอร์ตใหม่อยู่ VLAN ที่ถูกต้องหรือไม่ (`show interfaces status`)
</details>

---

➡️ ต่อไป: **Level 33 — Trunk 802.1Q & DTP**
