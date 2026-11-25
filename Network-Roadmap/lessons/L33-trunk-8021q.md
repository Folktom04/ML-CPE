# บทเรียน Level 33 — Trunk 802.1Q, DTP & VTP (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจว่า trunk พาหลาย VLAN ข้าม switch ได้อย่างไร · อ่าน 802.1Q tag · ตั้ง trunk, allowed VLAN, native VLAN · รู้ความเสี่ยงของ DTP/VTP และ VLAN hopping · แก้ปัญหา trunk ได้

---

## 1. ปัญหาที่ Trunk แก้

มี switch 2 ตัว (ชั้น 1 และชั้น 2) และทั้งสองชั้นมีผู้ใช้ VLAN 10, 20, 30
- **ไม่มี trunk:** ต้องลากสาย 3 เส้น (เส้นละ VLAN) — เปลืองพอร์ตและสาย ขยายไม่ได้
- **มี trunk:** สายเส้นเดียวพาได้ **หลาย VLAN** โดยแปะ **tag** บอกว่า frame นี้เป็นของ VLAN ไหน

```
 ชั้น 1                                    ชั้น 2
 [SW1] VLAN10 PCs ─┐                ┌─ VLAN10 PCs [SW2]
       VLAN20 PCs ─┤═══ TRUNK ══════┤─ VLAN20 PCs
       VLAN30 PCs ─┘  (802.1Q tag)  └─ VLAN30 PCs
```

**Trunk ใช้ที่ไหน:** switch ↔ switch, switch ↔ router (router-on-a-stick), switch ↔ AP (หลาย SSID หลาย VLAN), switch ↔ server/hypervisor (VM หลาย VLAN), switch ↔ firewall

---

## 2. 802.1Q Tag

มาตรฐาน **IEEE 802.1Q** แทรก tag **4 ไบต์** ระหว่าง Source MAC กับ EtherType

```
 ปกติ:   | Dst MAC | Src MAC |            | EtherType | Payload | FCS |
 Tagged: | Dst MAC | Src MAC | 802.1Q Tag | EtherType | Payload | FCS |  (FCS คำนวณใหม่)
                               │
          ┌────────────────────┴───────────────────────┐
          │ TPID 0x8100 (16) │ PCP (3) │ DEI (1) │ VLAN ID (12) │
          └──────────────────────────────────────────────────────┘
```

| Field | ขนาด | ความหมาย |
|---|---|---|
| **TPID** | 16 บิต | ค่า 0x8100 บอกว่า "frame นี้มี VLAN tag" |
| **PCP** (Priority Code Point) | 3 บิต | ลำดับความสำคัญ **CoS 0–7** (voice = 5) ใช้กับ QoS |
| DEI | 1 บิต | ทิ้งได้ก่อนเมื่อแออัด |
| **VLAN ID** | **12 บิต** | 0–4095 (ใช้ได้ 1–4094) |

- Frame ใหญ่ขึ้น 4 ไบต์ (สูงสุด 1522) — อุปกรณ์รุ่นใหม่รองรับอยู่แล้ว
- **Q-in-Q (802.1ad):** ซ้อน tag 2 ชั้น ใช้โดยผู้ให้บริการ Metro Ethernet
- ISL เป็นวิธีของ Cisco รุ่นเก่า **เลิกใช้แล้ว**

---

## 3. Native VLAN

- บน trunk มี **VLAN เดียวที่ส่งแบบไม่มี tag** เรียกว่า **native VLAN** (ค่าเริ่มต้น = **VLAN 1**)
- frame ที่ไม่มี tag เข้ามาทาง trunk จะถูกถือว่าเป็นของ native VLAN
- **native VLAN ต้องตรงกันทั้งสองฝั่ง** ไม่เช่นนั้น
  - traffic รั่วข้าม VLAN (untagged ของ VLAN หนึ่งไปโผล่อีก VLAN)
  - CDP แจ้งเตือน `%CDP-4-NATIVE_VLAN_MISMATCH`
  - STP อาจ block พอร์ต (PVID inconsistent)
- **Best practice:** ตั้ง native VLAN เป็น **VLAN ที่ไม่ได้ใช้งาน** (เช่น 999) หรือสั่ง tag native VLAN ด้วย (`vlan dot1q tag native`) เพื่อป้องกัน VLAN hopping

---

## 4. ตั้งค่า Trunk (Cisco)

```
interface GigabitEthernet1/0/48
 description UPLINK-TO-DIST-SW1
 switchport trunk encapsulation dot1q        ! จำเป็นเฉพาะรุ่นที่รองรับ ISL ด้วย (รุ่นใหม่ไม่ต้อง)
 switchport mode trunk                       ! บังคับเป็น trunk
 switchport trunk native vlan 999
 switchport trunk allowed vlan 10,20,30,99,110
 switchport nonegotiate                      ! ปิด DTP
```

### แก้ไข allowed VLAN — ⚠️ จุดที่ทำให้ระบบล่มบ่อยที่สุด
```
switchport trunk allowed vlan 40             ! ❌ อันตราย! "แทนที่" ทั้งหมด เหลือแค่ VLAN 40 → VLAN อื่นหลุดทั้งหมด
switchport trunk allowed vlan add 40         ! ✅ เพิ่ม VLAN 40 เข้าไป
switchport trunk allowed vlan remove 30      ! ✅ เอา VLAN 30 ออก
switchport trunk allowed vlan except 1-9     ! ทุก VLAN ยกเว้น
```
> 🔑 **ลืมคำว่า `add` คือสาเหตุ outage คลาสสิก** ตรวจทุกครั้งก่อนกด Enter

### ตรวจสอบ
```
Switch# show interfaces trunk
Port        Mode         Encapsulation  Status        Native vlan
Gi1/0/48    on           802.1q         trunking      999

Port        Vlans allowed on trunk
Gi1/0/48    10,20,30,99,110

Port        Vlans allowed and active in management domain
Gi1/0/48    10,20,30,99,110                    ← VLAN ต้องถูกสร้างบน switch นี้ด้วย

Port        Vlans in spanning tree forwarding state and not pruned
Gi1/0/48    10,20,30,99,110                    ← ส่งได้จริง (ไม่ถูก STP block)
```
**VLAN จะวิ่งผ่าน trunk ได้ต้องครบ 3 อย่าง:** อยู่ใน allowed list · **ถูกสร้าง (active) บน switch ทั้งสองฝั่ง** · ไม่ถูก STP block

---

## 5. DTP — Dynamic Trunking Protocol (Cisco)

DTP ให้ switch **เจรจากันเองว่าจะเป็น trunk หรือ access**

| ฝั่ง A \ ฝั่ง B | access | dynamic auto | dynamic desirable | trunk |
|---|---|---|---|---|
| **access** | access | access | access | ❌ ไม่ตรงกัน |
| **dynamic auto** | access | **access** | trunk | trunk |
| **dynamic desirable** | access | trunk | trunk | trunk |
| **trunk** | ❌ | trunk | trunk | trunk |

- **auto + auto = access** (ทั้งคู่รอให้อีกฝั่งเริ่ม จึงไม่มีใครเริ่ม)
- ค่าเริ่มต้นของ switch Cisco หลายรุ่นคือ dynamic auto หรือ desirable

> ⚠️ **ความเสี่ยง:** ผู้โจมตีเสียบเครื่องที่ส่ง DTP ขอเป็น trunk ได้ → เข้าถึงทุก VLAN (**switch spoofing**)
> **Best practice:** **ปิด DTP ทุกพอร์ต** — พอร์ตผู้ใช้ `switchport mode access` · พอร์ต trunk `switchport mode trunk` + `switchport nonegotiate`
> ยี่ห้ออื่นไม่มี DTP (ต้องตั้ง trunk เองทั้งสองฝั่ง)

---

## 6. VTP — VLAN Trunking Protocol (Cisco)

VTP ส่งรายการ VLAN จาก switch ตัวหนึ่งไปให้ตัวอื่นอัตโนมัติ

| Mode | พฤติกรรม |
|---|---|
| Server | สร้าง/ลบ VLAN ได้ และกระจายให้ตัวอื่น |
| Client | รับรายการจาก server สร้างเองไม่ได้ |
| **Transparent** | ไม่ใช้ข้อมูล VTP ของคนอื่น (แต่ส่งต่อ) สร้าง VLAN เองได้ |
| Off | ปิด VTP |

> ⚠️ **ความเสี่ยงที่ทำให้ทั้งองค์กรล่ม:** นำ switch ที่ **configuration revision สูงกว่า** (เช่น เคยใช้ใน lab) มาเสียบในโดเมนเดียวกัน → VLAN database ของทั้งองค์กรถูก **เขียนทับ/ลบ** → ทุกพอร์ตที่อยู่ใน VLAN ที่หายไปหยุดทำงาน
> **ด้วยเหตุนี้หลายองค์กรตั้ง VTP เป็น transparent หรือ off** แล้วจัดการ VLAN ด้วยมือหรือ automation (Ansible) แทน ถ้าจะใช้ ให้ใช้ VTPv3 (มี primary server ป้องกันได้ดีขึ้น) และตั้งรหัสผ่าน

---

## 7. VLAN Hopping — การโจมตีและการป้องกัน

### Switch Spoofing
ผู้โจมตีเจรจา DTP ให้พอร์ตตัวเองเป็น trunk → **ป้องกัน:** ปิด DTP, `switchport mode access` ที่พอร์ตผู้ใช้

### Double Tagging
```
 ผู้โจมตีอยู่ใน VLAN 1 (= native VLAN ของ trunk) ส่ง frame ที่มี 2 tag: [VLAN 1][VLAN 20]
 SW1 ถอด tag นอก (VLAN 1 = native → ส่งแบบไม่มี tag) → ส่งผ่าน trunk เหลือ tag [VLAN 20]
 SW2 เห็น tag VLAN 20 → ส่งเข้า VLAN 20 ✅ ผู้โจมตีส่งข้อมูลข้าม VLAN ได้ (ทางเดียว)
```
**ป้องกัน:** native VLAN เป็น VLAN ที่ไม่มีผู้ใช้ (เช่น 999), ไม่ให้ผู้ใช้อยู่ VLAN 1, หรือ `vlan dot1q tag native`

---

## 8. Trunk ไปยัง AP / Server / Firewall

- **AP หลาย SSID:** แต่ละ SSID map กับ VLAN → พอร์ต switch เป็น trunk, native VLAN มักเป็น VLAN จัดการ AP (ตามคู่มือ vendor)
- **Hypervisor (ESXi/Hyper-V/Proxmox):** พอร์ต trunk ไปยัง host, VM แต่ละตัวอยู่ใน port group/VLAN ของตัวเอง
- **Linux server:** สร้าง VLAN subinterface (`eth0.20`) — Level 26
- **Router-on-a-stick:** trunk ไป router ที่มี subinterface ต่อ VLAN — Level 34

---

## 9. แก้ปัญหา Trunk

| อาการ | ตรวจ |
|---|---|
| VLAN ใหม่ใช้งานข้าม switch ไม่ได้ | `show interfaces trunk`: VLAN อยู่ใน allowed? ถูกสร้างบนทั้งสองฝั่ง? ไม่ถูก STP block? |
| เพิ่ม VLAN แล้ว VLAN อื่นหลุดทั้งหมด | ลืม `add` ใน `switchport trunk allowed vlan` |
| CDP แจ้ง native VLAN mismatch | ตั้ง native VLAN ให้ตรงกัน |
| พอร์ตไม่เป็น trunk | DTP mode ไม่ตรง (auto+auto) หรืออีกฝั่งเป็น access → ตั้ง trunk ทั้งสองฝั่ง |
| เชื่อมต่างยี่ห้อแล้วไม่ทำงาน | ยี่ห้ออื่นไม่มี DTP; ตรวจ tagged/untagged ของแต่ละ VLAN ให้ตรงกัน |

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| `allowed vlan 40` คือการเพิ่ม VLAN | เป็นการ **แทนที่** ต้องใช้ `add` |
| อยู่ใน allowed list แล้วผ่านแน่นอน | VLAN ต้องถูกสร้างบน switch และไม่ถูก STP block |
| native VLAN ไม่สำคัญ | ไม่ตรงกันทำให้ traffic รั่ว และเป็นช่องโหว่ double tagging |
| VTP ช่วยประหยัดเวลา ใช้ได้อย่างปลอดภัย | เสี่ยงลบ VLAN ทั้งองค์กร หลายที่จึงปิด |

---

## 11. Cheat Sheet

```
Trunk = สายเดียวหลาย VLAN · 802.1Q tag 4 ไบต์: TPID 0x8100 · PCP(CoS 3 บิต) · VLAN ID 12 บิต
Native VLAN = untagged บน trunk (default 1) · ต้องตรงกันทั้งสองฝั่ง · ใช้ VLAN ที่ไม่ใช้งาน
switchport mode trunk · native vlan 999 · allowed vlan 10,20 · nonegotiate
⚠️ allowed vlan add X (อย่าลืม add!) · remove X
show interfaces trunk: allowed → active (สร้างแล้ว) → forwarding (ไม่ถูก STP block)
DTP: auto+auto = access · ปิด DTP ทุกพอร์ต
VTP: เสี่ยงเขียนทับ VLAN · ใช้ transparent/off หรือ v3
VLAN hopping: switch spoofing (ปิด DTP) · double tagging (native VLAN ไม่ใช้งาน)
```

---

## 12. แบบทดสอบ 10 ข้อ

1. Trunk คืออะไร ใช้เชื่อมอุปกรณ์อะไรบ้าง
2. 802.1Q tag มีขนาดเท่าไร field ใดเก็บ VLAN ID และกี่บิต
3. Native VLAN คืออะไร ค่าเริ่มต้นคือ VLAN ใด
4. ผลของ native VLAN mismatch
5. ต้องการเพิ่ม VLAN 50 เข้า trunk ที่มี VLAN 10,20,30 อยู่ ใช้คำสั่งอะไร ถ้าพิมพ์ผิดจะเกิดอะไร
6. VLAN 40 อยู่ใน allowed list แต่ยังใช้ข้าม switch ไม่ได้ สาเหตุที่เป็นไปได้ 2 ข้อ
7. dynamic auto ทั้งสองฝั่งจะเกิด trunk หรือไม่
8. ทำไมควรปิด DTP
9. ความเสี่ยงของ VTP คืออะไร
10. การโจมตี double tagging ทำงานอย่างไร ป้องกันอย่างไร

<details><summary><b>เฉลย</b></summary>

1. ลิงก์ที่พาหลาย VLAN ในสายเดียวด้วย tag — switch↔switch, switch↔router, switch↔AP, switch↔server/hypervisor/firewall
2. 4 ไบต์; VLAN ID 12 บิต
3. VLAN ที่ส่งบน trunk แบบไม่มี tag — ค่าเริ่มต้น VLAN 1
4. Traffic untagged รั่วไปอีก VLAN, CDP เตือน, STP อาจ block พอร์ต
5. `switchport trunk allowed vlan add 50` — ถ้าลืม `add` จะเหลือแค่ VLAN 50 และ VLAN อื่นหลุดทั้งหมด
6. VLAN 40 ยังไม่ถูกสร้างบน switch ฝั่งใดฝั่งหนึ่ง หรือถูก STP block
7. ไม่ — เป็น access
8. ป้องกันผู้โจมตีเจรจาให้พอร์ตเป็น trunk (switch spoofing) และทำให้สถานะพอร์ตคาดเดาได้
9. Switch ที่มี revision สูงกว่าเขียนทับ/ลบ VLAN database ของทั้งโดเมน
10. ผู้โจมตีใน native VLAN ส่ง frame 2 tag switch แรกถอด tag นอก (native) แล้วส่ง tag ในข้าม trunk ไปเข้า VLAN เป้าหมาย — ป้องกันด้วย native VLAN ที่ไม่มีผู้ใช้, ไม่ใช้ VLAN 1, tag native VLAN
</details>

---

➡️ ต่อไป: **Level 34 — Inter-VLAN Routing**
