# บทเรียน Level 31 — การทำงานของ Switch & MAC Address Table (ฉบับละเอียด)

> อ่านจบแล้วจะ: อธิบาย Learning / Forwarding / Flooding / Filtering ได้ · อ่าน MAC address table · หาตำแหน่งเครื่องจาก MAC/IP · เข้าใจ MAC aging, MAC flapping, CAM overflow · อ่าน interface counter หาปัญหาชั้น L1/L2

---

## 1. Switch ทำงานอย่างไร (4 พฤติกรรม)

Switch ตัดสินใจจาก **MAC address** และจำไว้ใน **MAC Address Table** (หรือ CAM table — Content Addressable Memory ที่ค้นหาได้เร็วมากในฮาร์ดแวร์)

### ① Learning — เรียนรู้จาก **Source MAC**
ทุก frame ที่เข้ามา switch จด "MAC ต้นทางนี้อยู่หลังพอร์ตนี้ ใน VLAN นี้"

### ② Forwarding — ส่งต่อตาม **Destination MAC**
ถ้ารู้จัก MAC ปลายทาง → ส่งออก **เฉพาะพอร์ตนั้น**

### ③ Flooding — ไม่รู้จักก็ส่งทุกพอร์ต
ส่งออกทุกพอร์ตใน VLAN เดียวกัน (ยกเว้นพอร์ตที่รับเข้ามา) เมื่อ
- **Unknown unicast** — ยังไม่เคยเห็น MAC ปลายทาง
- **Broadcast** — FF:FF:FF:FF:FF:FF (เช่น ARP request, DHCP Discover)
- **Multicast** — (ถ้าไม่ได้เปิด IGMP snooping)

### ④ Filtering — ไม่ส่งกลับพอร์ตเดิม
ถ้า MAC ปลายทางอยู่พอร์ตเดียวกับที่รับเข้ามา → ทิ้ง (ไม่ต้องส่ง)

### ตัวอย่างทีละขั้น
```
 [PC-A aa:aa]─Gi1─┐                 ┌─Gi3─[PC-C cc:cc]
                  [     SWITCH     ]
 [PC-B bb:bb]─Gi2─┘                 └─Gi4─[PC-D dd:dd]

 เริ่มต้น: ตาราง MAC ว่าง

 1) PC-A → PC-C (ARP request, broadcast)
    Learn: aa:aa = Gi1 · Flood ออก Gi2, Gi3, Gi4
 2) PC-C ตอบ PC-A (unicast)
    Learn: cc:cc = Gi3 · Forward ออก Gi1 อย่างเดียว (รู้จัก aa:aa แล้ว)
 3) PC-A → PC-C (ข้อมูลจริง)
    Forward ออก Gi3 อย่างเดียว · PC-B, PC-D ไม่เห็นข้อมูลนี้

 ตาราง MAC:
 VLAN  MAC     Type     Port
  1    aa:aa   DYNAMIC  Gi1
  1    cc:cc   DYNAMIC  Gi3
```

---

## 2. MAC Address Table

```
Switch# show mac address-table
          Mac Address Table
-------------------------------------------
Vlan    Mac Address       Type        Ports
----    -----------       --------    -----
  10    0050.56a1.1111    DYNAMIC     Gi1/0/5
  10    0050.56a1.2222    DYNAMIC     Gi1/0/6
  20    0011.2233.4455    STATIC      Gi1/0/10
  10    aabb.cc00.0100    DYNAMIC     Gi1/0/48     ← หลายเครื่องอยู่หลังพอร์ต uplink
  10    aabb.cc00.0200    DYNAMIC     Gi1/0/48

show mac address-table dynamic
show mac address-table address 0050.56a1.1111
show mac address-table interface Gi1/0/5
show mac address-table vlan 10
show mac address-table count
clear mac address-table dynamic [interface Gi1/0/5]
```
- **ตารางแยกตาม VLAN** — MAC เดียวกันใน VLAN ต่างกันนับเป็นคนละรายการ
- **พอร์ต uplink/trunk** มักมี MAC จำนวนมาก (เครื่องทั้งหมดที่อยู่หลัง switch อีกตัว)
- **Type:** DYNAMIC (เรียนรู้เอง), STATIC (ตั้งเอง), หรือ sticky/secure (port security)

### MAC Aging
- รายการ dynamic จะหมดอายุถ้าไม่เห็น frame จาก MAC นั้นนานเกิน **300 วินาที** (ค่าเริ่มต้นส่วนใหญ่)
- ช่วยให้ตารางทันสมัยเมื่อเครื่องย้ายพอร์ตหรือปิดเครื่อง
```
show mac address-table aging-time
mac address-table aging-time 600
```

---

## 3. งานจริง: หาว่าเครื่องเสียบอยู่พอร์ตไหน

**โจทย์:** รู้ IP 10.0.10.55 อยากรู้ว่าเสียบอยู่ switch ไหน พอร์ตไหน

```
 1) ที่ L3 switch/router (gateway ของ VLAN) หา MAC จาก IP
    show ip arp 10.0.10.55          → 0050.56a1.1111  Vlan10
 2) หา MAC ใน MAC table
    show mac address-table address 0050.56a1.1111
    → Gi1/0/48 (เป็น uplink — เครื่องอยู่หลัง switch อีกตัว)
 3) ดูว่า Gi1/0/48 ต่อไป switch ไหน
    show cdp neighbors Gi1/0/48     → ACCESS-SW-3F (Gi1/0/52)
 4) เข้า ACCESS-SW-3F แล้วหา MAC อีกครั้ง
    show mac address-table address 0050.56a1.1111  → Gi1/0/17  ✅ พบพอร์ตปลายทาง
 5) ดูข้อมูลพอร์ต: show interfaces Gi1/0/17 status / description
```
งานนี้ทำซ้ำบ่อยมาก จึงนิยมเขียนสคริปต์อัตโนมัติ (Python/Netmiko — Tier 9) หรือใช้ระบบ NMS/NetBox

---

## 4. ปัญหาที่เกี่ยวกับ MAC Table

### MAC Flapping
```
%SW_MATM-4-MACFLAP_NOTIF: Host 0050.56a1.1111 in vlan 10 is flapping between port Gi1/0/1 and port Gi1/0/2
```
MAC เดียวกันถูกเห็นสลับไปมาระหว่าง 2 พอร์ต — สาเหตุที่เป็นไปได้
- **L2 loop** (สำคัญที่สุด — STP ไม่ทำงาน/มีคนต่อสายวน) → broadcast storm
- **NIC teaming/bonding ตั้งผิด mode** (server ส่งออกทั้งสอง NIC ด้วย MAC เดียวโดยที่ switch ไม่ได้ทำ port-channel)
- VM ย้าย host (ปกติถ้าเกิดครั้งเดียว)
- Wi-Fi client roaming ระหว่าง AP (ปกติ)

### CAM Table Overflow (MAC Flooding Attack)
- ผู้โจมตีส่ง frame ด้วย **MAC ต้นทางปลอมหลายแสนตัว** จนตารางเต็ม
- switch ไม่สามารถเรียนรู้ MAC ใหม่ → **flood ทุก frame** → ทำงานเหมือน hub → ผู้โจมตีดักข้อมูลได้
- ป้องกันด้วย **Port Security** จำกัดจำนวน MAC ต่อพอร์ต (Level 38)

### Unknown Unicast Flooding
- เกิดเมื่อ ARP cache ของ router ยาวกว่า MAC aging ของ switch (เช่น 4 ชม. vs 5 นาที) แล้วมี traffic ทางเดียวไปยังเครื่องที่เงียบ → switch ลืม MAC แต่ router ยังส่งมา → flood
- แก้ด้วยการปรับ timer ให้สอดคล้องกัน

---

## 5. วิธีส่งต่อ: Store-and-Forward vs Cut-Through

| | Store-and-Forward | Cut-Through |
|---|---|---|
| หลักการ | รับ frame **ครบทั้ง frame** ตรวจ FCS แล้วจึงส่ง | อ่าน **MAC ปลายทาง** แล้วเริ่มส่งทันที |
| ข้อดี | ไม่ส่ง frame เสียต่อ, รองรับต่างความเร็วได้ | **latency ต่ำมาก** |
| ข้อเสีย | latency สูงกว่าเล็กน้อย | อาจส่งต่อ frame ที่เสีย |
| ใช้ที่ | switch องค์กรทั่วไป | Data center, การเงิน/HFT |

---

## 6. อ่าน Interface Counter — หาปัญหาชั้น L1/L2

```
Switch# show interfaces Gi1/0/17
GigabitEthernet1/0/17 is up, line protocol is up (connected)
  Full-duplex, 1000Mb/s, media type is 10/100/1000BaseTX
  5 minute input rate 2500000 bits/sec, 300 packets/sec
     123 input errors, 120 CRC, 0 frame, 0 overrun, 0 ignored
     0 output errors, 0 collisions, 2 interface resets
     0 late collision, 0 deferred
     5000 output drops (Total output drops)
```

| Counter | ความหมาย | สาเหตุที่เป็นไปได้ |
|---|---|---|
| **CRC / input errors** | frame เสียระหว่างทาง | สาย/หัว/พอร์ต/SFP เสีย, สัญญาณรบกวน, duplex mismatch |
| **late collision** | ชนหลังส่งไปแล้ว 64 ไบต์ | **duplex mismatch**, สายยาวเกิน |
| **runts / giants** | frame เล็ก/ใหญ่ผิดมาตรฐาน | collision, MTU ไม่ตรง |
| **output drops** | ส่งออกไม่ทัน buffer เต็ม | **congestion**, microburst, พอร์ตปลายทางช้ากว่า |
| **interface resets** | พอร์ตรีเซ็ต | link flap, keepalive, PoE |
| speed/duplex ผิด | 100/half แทน 1000/full | สายคู่เสีย, ตั้งค่าตายตัวไม่ตรงกัน |

```
show interfaces counters errors        ! ดู error ทุกพอร์ตในตารางเดียว
show interfaces status                 ! สถานะ, VLAN, duplex, speed ทุกพอร์ต
show interfaces status err-disabled
clear counters Gi1/0/17                ! ล้างแล้วดูว่าเพิ่มขึ้นใหม่หรือไม่ (ค่าสะสมเก่าอาจทำให้เข้าใจผิด)
```
> 💡 **เทคนิค:** counter เป็นค่าสะสมตั้งแต่บูต/ล้างครั้งล่าสุด ให้ `clear counters` แล้วดูซ้ำหลังผ่านไปสักพัก เพื่อรู้ว่าปัญหายังเกิดอยู่หรือไม่

---

## 7. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| Switch เรียนรู้จาก MAC ปลายทาง | เรียนรู้จาก **MAC ต้นทาง** |
| Switch ส่ง broadcast เฉพาะคนที่ต้องการ | broadcast flood ทุกพอร์ตใน VLAN |
| MAC flapping เป็นปัญหาเสมอ | เกิดครั้งเดียวจาก VM/Wi-Fi roaming เป็นปกติ แต่ถี่ ๆ อาจเป็น loop |
| พอร์ต uplink ควรมี MAC เดียว | uplink มี MAC ของทุกเครื่องที่อยู่หลังมัน |

---

## 8. Cheat Sheet

```
Learn (src MAC) · Forward (dst MAC รู้จัก) · Flood (unknown/broadcast/multicast) · Filter
ตาราง MAC แยกตาม VLAN · aging 300 วินาที
show mac address-table [address X | interface Y | vlan Z | count]
หาเครื่อง: show ip arp IP → show mac address-table address MAC → cdp neighbors → ทำซ้ำ
MAC flapping = loop / teaming ผิด · CAM overflow → port security
Store-and-forward (ตรวจ FCS) vs Cut-through (latency ต่ำ)
CRC = สาย/สัญญาณ · late collision = duplex mismatch · output drops = congestion
show interfaces counters errors · clear counters แล้วดูซ้ำ
```

---

## 9. แบบทดสอบ 10 ข้อ

1. Switch เรียนรู้ MAC จาก field ใดของ frame
2. Frame ประเภทใดบ้างที่ switch จะ flood
3. ตารางด้านบน พอร์ต Gi1/0/48 มีหลาย MAC หมายความว่าอะไร
4. MAC aging time ค่าเริ่มต้นเท่าไร มีไว้ทำไม
5. อธิบายขั้นตอนหาพอร์ตที่เครื่อง IP 10.0.10.55 เสียบอยู่
6. Log "MAC flapping between Gi1/0/1 and Gi1/0/2" สาเหตุที่เป็นไปได้ 2 ข้อ
7. CAM table overflow attack ทำให้เกิดอะไร ป้องกันอย่างไร
8. Store-and-forward ต่างจาก cut-through อย่างไร
9. พอร์ตมี late collision และ CRC เพิ่มขึ้น สงสัยอะไร
10. output drops สูงบนพอร์ตที่ต่อ server บ่งบอกอะไร

<details><summary><b>เฉลย</b></summary>

1. Source MAC
2. Unknown unicast, broadcast, multicast (ที่ไม่ได้ทำ IGMP snooping)
3. เป็นพอร์ต uplink/trunk ที่มีเครื่องหลายเครื่องอยู่หลัง (switch อีกตัว)
4. 300 วินาที — ลบรายการที่ไม่ใช้งานให้ตารางทันสมัยเมื่อเครื่องย้าย/ปิด
5. `show ip arp 10.0.10.55` ที่ gateway → ได้ MAC → `show mac address-table address <MAC>` → ถ้าเป็น uplink ใช้ CDP/LLDP หา switch ถัดไป → ทำซ้ำจนเจอ access port
6. L2 loop และ NIC teaming/bonding ตั้งผิด (หรือ VM ย้าย host)
7. ตาราง MAC เต็ม switch flood ทุก frame เหมือน hub ผู้โจมตีดักข้อมูลได้ — ป้องกันด้วย port security จำกัดจำนวน MAC
8. Store-and-forward รับครบและตรวจ FCS ก่อนส่ง; cut-through ส่งทันทีที่อ่าน MAC ปลายทาง (latency ต่ำแต่อาจส่ง frame เสีย)
9. Duplex mismatch (หรือสายยาวเกิน/เสีย)
10. ส่งออกไม่ทัน — congestion/microburst หรือพอร์ตปลายทางรับไม่ทัน
</details>

---

➡️ ต่อไป: **Level 32 — VLAN**
