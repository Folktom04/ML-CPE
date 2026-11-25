# บทเรียน Level 63 — Layer 2 Security (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจการโจมตีในชั้น Layer 2 ทั้งหมด (MAC flooding, ARP spoofing, DHCP starvation/rogue, VLAN hopping, STP manipulation, rogue RA) · ตั้งค่า DHCP Snooping, Dynamic ARP Inspection, IP Source Guard, RA Guard ได้ถูกลำดับ · ทำ access switch security baseline ที่ครบถ้วน

> ⚠️ การทดลองโจมตีในบทนี้ทำได้เฉพาะใน lab ที่แยกจากเครือข่ายจริงและเป็นของตัวเองเท่านั้น

---

## 1. ทำไม Layer 2 สำคัญ

- Firewall ส่วนใหญ่ **อยู่ที่ขอบหรือระหว่าง zone** — **ไม่เห็น traffic ภายใน VLAN เดียวกัน**
- โปรโตคอล L2 ส่วนใหญ่ (ARP, DHCP, STP, DTP, CDP) **ออกแบบมาโดยเชื่อใจกัน ไม่มีการยืนยันตัวตน**
- ผู้โจมตีที่ **เสียบสายได้หนึ่งพอร์ต** (หรือเครื่องที่ติดมัลแวร์) สามารถดักข้อมูล ปลอมเป็น gateway หรือล่มทั้ง VLAN ได้

> 🔑 "ความปลอดภัยของเครือข่ายเริ่มที่ access port"

---

## 2. ภาพรวมการโจมตีและการป้องกัน

| การโจมตี | ผลลัพธ์ | การป้องกัน |
|---|---|---|
| **MAC flooding (CAM overflow)** | ตาราง MAC เต็ม → switch flood ทุก frame (ทำงานเหมือน hub) → ดักข้อมูลได้ | **Port Security** (จำกัด MAC ต่อพอร์ต) |
| **MAC spoofing** | ปลอมเป็นเครื่องอื่น (เช่น printer) | 802.1X, profiling (NAC) |
| **DHCP Starvation** | ขอ IP ด้วย MAC ปลอมจนหมด pool → ผู้ใช้จริงไม่ได้ IP | **DHCP Snooping rate limit**, port security |
| **Rogue DHCP** | แจก gateway/DNS ปลอม → MITM / redirect | **DHCP Snooping** (trusted port) |
| **ARP Spoofing/Poisoning** | อ้างเป็นเจ้าของ IP ของ gateway → MITM | **Dynamic ARP Inspection (DAI)** |
| **IP Spoofing (ใน LAN)** | ใช้ IP ของคนอื่น | **IP Source Guard** |
| **VLAN Hopping (switch spoofing)** | เจรจา DTP เป็น trunk → เข้าถึงทุก VLAN | ปิด DTP (`mode access`, `nonegotiate`) |
| **VLAN Hopping (double tagging)** | ส่ง frame 2 tag ข้ามไป VLAN อื่น | native VLAN ไม่ใช้งาน, ไม่ใช้ VLAN 1, tag native |
| **STP manipulation** | ส่ง BPDU priority ต่ำ → เป็น root bridge → traffic วิ่งผ่านผู้โจมตี / ทำให้ topology ปั่นป่วน | **BPDU Guard**, **Root Guard** |
| **Rogue RA (IPv6)** | ประกาศตัวเป็น IPv6 router → MITM | **RA Guard**, DHCPv6 Guard |
| **CDP/LLDP reconnaissance** | ได้ข้อมูลรุ่น/OS/IP | ปิดที่พอร์ตที่ไม่จำเป็น |
| **Rogue AP / switch ที่ผู้ใช้เสียบเอง** | ขยายเครือข่ายโดยไม่ได้รับอนุญาต, loop | BPDU Guard, port security, 802.1X, WIPS |

---

## 3. DHCP Snooping — รากฐานของการป้องกัน

### หลักการ
- แบ่งพอร์ตเป็น **Trusted** (ทางไปหา DHCP server/relay จริง — uplink) และ **Untrusted** (พอร์ตผู้ใช้ทุกพอร์ต)
- บนพอร์ต **untrusted**: **ห้ามรับข้อความฝั่ง server** (DHCP OFFER/ACK/NAK) → rogue DHCP ใช้ไม่ได้
- จำกัดอัตรา DHCP request ต่อพอร์ต → ป้องกัน starvation
- สร้าง **DHCP Snooping Binding Table**: **MAC ↔ IP ↔ VLAN ↔ พอร์ต ↔ lease** — ฐานข้อมูลนี้ถูกใช้ต่อโดย DAI และ IP Source Guard

```
ip dhcp snooping
ip dhcp snooping vlan 10,20,30
no ip dhcp snooping information option        ! (บางกรณี) ปิด option 82 ถ้า relay/server ไม่รองรับ
!
interface range Gi1/0/49 - 50                 ! uplink ไป distribution
 ip dhcp snooping trust
!
interface range Gi1/0/1 - 46                  ! พอร์ตผู้ใช้ (untrusted เป็นค่าเริ่มต้น)
 ip dhcp snooping limit rate 20               ! ไม่เกิน 20 packet/วินาที (เกิน → err-disable)
!
show ip dhcp snooping
show ip dhcp snooping binding
MacAddress          IpAddress     Lease(sec)  Type           VLAN  Interface
00:50:56:A1:11:11   10.0.10.55    85000       dhcp-snooping  10    Gi1/0/5
```
> ⚠️ **ลืมตั้ง trust ที่ uplink = ทุกคนใน VLAN ไม่ได้ IP** — เพราะ OFFER จาก server จริงถูกทิ้ง
> ⚠️ **DHCP Option 82:** switch บางรุ่นใส่ option 82 แล้ว server/relay ปฏิเสธ → ปรับตามสภาพแวดล้อม

---

## 4. Dynamic ARP Inspection (DAI)

### หลักการ
ตรวจ **ARP ทุก packet บนพอร์ต untrusted** ว่า "IP ↔ MAC" ที่อ้าง **ตรงกับ DHCP snooping binding table** หรือไม่ — ไม่ตรง → ทิ้ง (และ log)
```
 ผู้โจมตี (10.0.10.66, MAC EE:EE) ส่ง ARP reply: "10.0.10.1 (gateway) อยู่ที่ EE:EE"
 DAI: binding table บอกว่าพอร์ตนี้คือ 10.0.10.66/EE:EE — ไม่ใช่ 10.0.10.1 → DROP ✅
```

```
ip arp inspection vlan 10,20,30
ip arp inspection validate src-mac dst-mac ip         ! ตรวจความสอดคล้องเพิ่มเติม
!
interface range Gi1/0/49 - 50
 ip arp inspection trust                              ! uplink
interface range Gi1/0/1 - 46
 ip arp inspection limit rate 15                      ! ป้องกัน ARP flood (เกิน → err-disable)
!
! อุปกรณ์ที่ตั้ง static IP (ไม่มีใน binding table) ต้องอนุญาตด้วย ARP ACL
arp access-list STATIC-HOSTS
 permit ip host 10.0.10.200 mac host 0011.2233.4455
ip arp inspection filter STATIC-HOSTS vlan 10
!
show ip arp inspection
show ip arp inspection statistics
```
> ⚠️ **ลำดับสำคัญ: เปิด DHCP snooping ก่อน รอให้ binding table สมบูรณ์ (ผู้ใช้ renew IP) แล้วจึงเปิด DAI** — ไม่เช่นนั้นเครื่องที่ได้ IP ก่อนเปิด snooping จะถูกบล็อก ARP ทั้งหมด
> ⚠️ อุปกรณ์ **static IP** (printer, server, กล้อง) ต้องใส่ใน ARP ACL หรือใช้ DHCP reservation

---

## 5. IP Source Guard (IPSG)

ตรวจ **IP ต้นทาง (และ MAC ถ้าต้องการ)** ของทุก packet บนพอร์ตว่าตรงกับ binding table — ป้องกันเครื่องใช้ IP ของคนอื่น/ตั้ง IP เอง
```
interface range Gi1/0/1 - 46
 ip verify source                      ! ตรวจ IP
 ip verify source port-security        ! ตรวจทั้ง IP และ MAC (ต้องเปิด port security)
show ip verify source
```
ข้อควรระวังเดียวกับ DAI: เครื่อง static IP ต้องเพิ่ม `ip source binding` ด้วยมือ

---

## 6. IPv6 First-Hop Security

IPv6 มีปัญหาคล้ายกัน แต่ใช้ NDP/RA แทน ARP/DHCP

| ฟีเจอร์ | ป้องกัน |
|---|---|
| **RA Guard** | Rogue Router Advertisement (เครื่องอ้างเป็น IPv6 router) |
| **DHCPv6 Guard** | Rogue DHCPv6 server |
| **ND Inspection / Snooping** | NDP spoofing (เทียบเท่า DAI) |
| **IPv6 Source Guard** | IPv6 source spoofing |

```
ipv6 nd raguard policy HOSTS
 device-role host
interface range Gi1/0/1 - 46
 ipv6 nd raguard attach-policy HOSTS
```
> 🔑 **แม้องค์กรยังไม่ได้ใช้ IPv6 ก็ควรเปิด RA Guard** — เครื่องส่วนใหญ่เปิด IPv6 อยู่แล้วและจะรับ RA ปลอม

---

## 7. ป้องกัน VLAN Hopping และ STP Attack (ทบทวน)

```
! พอร์ตผู้ใช้
interface range Gi1/0/1 - 46
 switchport mode access                 ! ปิด DTP
 switchport nonegotiate
 spanning-tree portfast
 spanning-tree bpduguard enable         ! เสียบ switch/ส่ง BPDU → err-disable
! Trunk
interface Gi1/0/49
 switchport mode trunk
 switchport nonegotiate
 switchport trunk native vlan 999       ! native = VLAN ที่ไม่ใช้งาน
 switchport trunk allowed vlan 10,20,30,99
vlan dot1q tag native                   ! (ถ้ารองรับ) tag native VLAN ด้วย
! Downlink จาก distribution
interface Gi1/0/1
 spanning-tree guard root
```
(รายละเอียด Level 33, 36, 38)

---

## 8. Access Switch Security Baseline (รวมทั้งหมด)

```
☐ พอร์ตว่าง: shutdown + parking VLAN
☐ พอร์ตผู้ใช้: mode access + nonegotiate + PortFast + BPDU Guard
☐ Port Security (maximum, restrict) หรือ 802.1X/MAB
☐ DHCP Snooping (trust เฉพาะ uplink, rate limit พอร์ตผู้ใช้)
☐ Dynamic ARP Inspection (+ ARP ACL สำหรับ static)
☐ IP Source Guard (ถ้าเหมาะสม)
☐ RA Guard / DHCPv6 Guard
☐ Storm control
☐ Trunk: native VLAN ไม่ใช้งาน, allowed VLAN เฉพาะที่ใช้, ไม่ใช้ VLAN 1
☐ CDP/LLDP ปิดในพอร์ตที่ไม่จำเป็น (เปิดสำหรับ IP phone)
☐ Management: SSH + ACL + AAA, management VLAN แยก
☐ errdisable recovery (ตามนโยบาย) + log/alert ไปที่ NOC
☐ 802.1X/NAC (ระดับสูงสุด — Level 66)
```

---

## 9. แผนการเปิดใช้งานจริง (ไม่ให้ผู้ใช้ได้รับผลกระทบ)

```
 1) สำรวจ: อุปกรณ์ static IP ทั้งหมด, DHCP server/relay, uplink ของทุก switch
 2) เปิด DHCP snooping + trust uplink (ทีละ switch/VLAN) → ตรวจผู้ใช้ยังได้ IP
 3) รอ binding table ครบ (อย่างน้อย 1 lease cycle หรือสั่งผู้ใช้ renew)
 4) เปิด DAI แบบ log ก่อน (ถ้าอุปกรณ์รองรับ) หรือทีละ VLAN นอกเวลางาน + ARP ACL สำหรับ static
 5) ติดตาม log/statistics → แก้ข้อยกเว้น
 6) เปิด IPSG / RA Guard
 7) เพิ่มใน config template มาตรฐาน + ตรวจ compliance อัตโนมัติ
```

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| Firewall ป้องกันการโจมตีใน VLAN เดียวกันได้ | firewall ไม่เห็น traffic ภายใน VLAN ต้องป้องกันที่ switch |
| เปิด DAI ได้ทันทีโดยไม่มีผลกระทบ | ต้องมี DHCP snooping binding ก่อน และจัดการอุปกรณ์ static IP |
| DHCP snooping ตั้งแค่เปิดคำสั่งก็พอ | ต้องตั้ง trusted port ที่ uplink |
| ไม่ใช้ IPv6 ไม่ต้องสนใจ RA Guard | เครื่องเปิด IPv6 อยู่แล้ว rogue RA ใช้โจมตีได้ |
| Port security ป้องกัน MAC spoofing ได้สมบูรณ์ | ปลอม MAC ได้ — ใช้ 802.1X |

---

## 11. Cheat Sheet

```
L2 โปรโตคอลไม่มีการยืนยันตัวตน · firewall ไม่เห็น intra-VLAN → ป้องกันที่ access switch
MAC flooding → Port security · Rogue DHCP/Starvation → DHCP snooping (trust uplink, rate limit)
ARP spoofing → DAI (ใช้ binding table) · IP spoofing → IP Source Guard
VLAN hopping → ปิด DTP + native VLAN ไม่ใช้งาน · STP attack → BPDU Guard / Root Guard
IPv6: RA Guard · DHCPv6 Guard · ND inspection
ลำดับ: DHCP snooping → รอ binding ครบ → DAI (+ ARP ACL static) → IPSG
show ip dhcp snooping binding · show ip arp inspection statistics · show ip verify source
```

---

## 12. แบบทดสอบ 10 ข้อ

1. ทำไม firewall ที่ขอบเครือข่ายป้องกัน ARP spoofing ใน VLAN เดียวกันไม่ได้
2. MAC flooding ทำให้เกิดอะไร ป้องกันด้วยอะไร
3. DHCP snooping แบ่งพอร์ตเป็นกี่ประเภท พอร์ตใดต้องเป็น trusted
4. ถ้าเปิด DHCP snooping แต่ลืมตั้ง trusted จะเกิดอะไร
5. DHCP snooping binding table เก็บข้อมูลอะไร และฟีเจอร์ใดใช้ต่อ
6. DAI ทำงานอย่างไร
7. ทำไมต้องเปิด DHCP snooping ก่อน DAI และจัดการ printer ที่ตั้ง static IP อย่างไร
8. IP Source Guard ป้องกันอะไร
9. RA Guard ป้องกันอะไร ทำไมควรเปิดแม้ไม่ได้ใช้ IPv6
10. ป้องกัน VLAN hopping ทั้งสองแบบอย่างไร

<details><summary><b>เฉลย</b></summary>

1. Traffic ภายใน VLAN เดียวกันวิ่งผ่าน switch โดยไม่ผ่าน firewall
2. ตาราง MAC เต็ม switch flood ทุก frame ผู้โจมตีดักข้อมูลได้ — ป้องกันด้วย port security
3. 2 ประเภท: trusted และ untrusted — พอร์ต uplink ที่ไปหา DHCP server/relay ต้องเป็น trusted
4. OFFER/ACK จาก server จริงถูกทิ้ง ผู้ใช้ทั้ง VLAN ไม่ได้ IP
5. MAC, IP, VLAN, พอร์ต, lease — DAI และ IP Source Guard ใช้ต่อ
6. ตรวจ ARP บนพอร์ต untrusted ว่าคู่ IP–MAC ตรงกับ binding table หรือไม่ ถ้าไม่ตรงทิ้ง
7. DAI อ้างอิง binding table ที่สร้างจาก DHCP snooping — ถ้าไม่มี binding ARP ของเครื่องนั้นจะถูกทิ้ง; printer static IP ต้องเพิ่ม ARP ACL (หรือใช้ DHCP reservation)
8. เครื่องใช้ IP (และ MAC) ที่ไม่ได้รับจาก DHCP/ไม่ใช่ของตัวเอง
9. Rogue IPv6 Router Advertisement — อุปกรณ์ส่วนใหญ่เปิด IPv6 และจะรับ RA ปลอม ทำให้เกิด MITM ได้
10. Switch spoofing: ปิด DTP (`switchport mode access`, `nonegotiate`); Double tagging: native VLAN เป็น VLAN ที่ไม่ใช้งาน ไม่ใช้ VLAN 1 สำหรับผู้ใช้ และ tag native VLAN
</details>

---

➡️ ต่อไป: **Level 64 — IDS/IPS**
