# บทเรียน Level 53 — ACL (Access Control List) (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจการทำงาน first-match + implicit deny · คำนวณ wildcard mask · เขียน standard/extended/named ACL · เลือกตำแหน่งและทิศทางที่ถูก · ป้องกัน VTY · เข้าใจข้อจำกัดของ ACL เทียบกับ stateful firewall · แก้ไข ACL อย่างปลอดภัย

---

## 1. ACL คืออะไร

**ACL (Access Control List)** = รายการกฎ **permit / deny** ที่อุปกรณ์ใช้ **คัดกรอง packet** ตามเงื่อนไข (IP ต้นทาง/ปลายทาง, protocol, port)

**ใช้ทำอะไรได้บ้าง**
- **กรอง traffic** ผ่าน interface (ใช้บ่อยที่สุด)
- **จำกัดการเข้าจัดการอุปกรณ์** (VTY/SSH, SNMP)
- **เลือก traffic** สำหรับฟีเจอร์อื่น: NAT, QoS (class-map), PBR (route-map), route filtering, VPN (interesting traffic), debug

---

## 2. กฎการทำงาน 3 ข้อ (สำคัญที่สุด)

1. **ตรวจจากบนลงล่างตามลำดับ (top-down)**
2. **เจอกฎแรกที่ตรง (first match) → ทำตามกฎนั้นทันทีแล้วหยุด** ไม่ดูกฎที่เหลือ
3. **ไม่ตรงกฎใดเลย → ถูก deny** ด้วยกฎที่มองไม่เห็นท้ายสุด (**implicit deny any**)

```
 ACL TEST:
 10 deny   host 10.0.0.5
 20 permit 10.0.0.0/24
 (implicit) deny any

 packet จาก 10.0.0.5  → ตรงกฎ 10 → deny
 packet จาก 10.0.0.9  → ไม่ตรง 10, ตรง 20 → permit
 packet จาก 10.0.1.9  → ไม่ตรงทั้งสองกฎ → implicit deny
```
**ผลที่ตามมา**
- **ลำดับสำคัญมาก:** กฎที่เจาะจงต้องอยู่ **ก่อน** กฎที่กว้าง ไม่เช่นนั้นจะไม่มีวันถูกตรวจ (**shadowed rule**)
- ACL ที่มีแต่ `deny` **จะ block ทุกอย่าง** — ต้องมี `permit` อย่างน้อยหนึ่งกฎ
- ACL ที่ **ถูกอ้างถึงแต่ยังไม่ได้สร้าง** บน Cisco จะปล่อยผ่านทั้งหมด (ระวังพิมพ์ชื่อผิด)

---

## 3. Wildcard Mask

ACL ของ Cisco ใช้ **wildcard mask** (ตรงข้ามกับ subnet mask) บอกว่า **บิตไหนต้องตรง**
- บิต **0** = ต้องตรง · บิต **1** = ไม่สนใจ
- **วิธีคิดเร็ว: wildcard = 255.255.255.255 − subnet mask**

| Subnet | Mask | Wildcard |
|---|---|---|
| /24 | 255.255.255.0 | **0.0.0.255** |
| /26 | 255.255.255.192 | **0.0.0.63** |
| /27 | 255.255.255.224 | 0.0.0.31 |
| /30 | 255.255.255.252 | 0.0.0.3 |
| /16 | 255.255.0.0 | 0.0.255.255 |
| /20 | 255.255.240.0 | 0.0.15.255 |
| /32 (host) | 255.255.255.255 | **0.0.0.0** = คีย์เวิร์ด `host` |
| ทั้งหมด | 0.0.0.0 | **255.255.255.255** = คีย์เวิร์ด `any` |

```
 10.1.1.0 0.0.0.255   = 10.1.1.0/24
 host 10.1.1.5        = 10.1.1.5 0.0.0.0
 any                  = 0.0.0.0 255.255.255.255
```
(Firewall ส่วนใหญ่และ Linux ใช้รูปแบบ CIDR ธรรมดา ไม่ต้องคิด wildcard)

---

## 4. ประเภทของ ACL (Cisco)

| | **Standard** | **Extended** |
|---|---|---|
| ตรวจ | **IP ต้นทางเท่านั้น** | ต้นทาง, **ปลายทาง**, **protocol**, **port**, flag (established) |
| หมายเลข | 1–99, 1300–1999 | 100–199, 2000–2699 |
| ความละเอียด | หยาบ | ละเอียด |
| วางไว้ | **ใกล้ปลายทาง** | **ใกล้ต้นทาง** |

**Named ACL** (แนะนำ) — ตั้งชื่อสื่อความหมาย และ **แก้ไขทีละบรรทัดได้ด้วย sequence number**

### ทำไมวาง Standard ใกล้ปลายทาง แต่ Extended ใกล้ต้นทาง
```
 [HR 10.0.20.0] ──R1──────R2── [Payroll Server] 
                   │
                   └── [Internet]
 ต้องการ: HR ห้ามเข้า Payroll แต่ไปอินเทอร์เน็ตได้

 Standard (ดูแค่ต้นทาง): deny 10.0.20.0 → ถ้าวางที่ R1 ขาเข้าจาก HR จะบล็อก HR ไป "ทุกที่" รวมอินเทอร์เน็ต ❌
   → ต้องวางใกล้ปลายทาง (R2 ขาออกไป Payroll)
 Extended (ดูปลายทางด้วย): deny 10.0.20.0 → host Payroll → วางที่ R1 ขาเข้าจาก HR ได้ ✅
   → ทิ้งตั้งแต่ต้นทาง ไม่เปลือง bandwidth ระหว่างทาง
```

---

## 5. ตัวอย่าง Config

### Standard ACL — จำกัดการ SSH เข้าอุปกรณ์ (ใช้บ่อยมาก)
```
ip access-list standard MGMT-ONLY
 10 permit 10.0.99.0 0.0.0.255          ! management network
 20 permit host 10.0.0.50               ! jump host
 30 deny   any log
line vty 0 15
 access-class MGMT-ONLY in              ! สำหรับ VTY ใช้ access-class (ไม่ใช่ access-group)
 transport input ssh
```

### Extended ACL — Guest เข้าภายในไม่ได้
```
ip access-list extended GUEST-IN
 10 permit udp 10.0.50.0 0.0.1.255 host 10.0.0.53 eq domain     ! DNS ภายในที่อนุญาต
 20 permit udp any eq bootpc any eq bootps                       ! DHCP
 30 deny   ip 10.0.50.0 0.0.1.255 10.0.0.0 0.255.255.255 log     ! ห้ามเข้าเครือข่ายภายใน
 40 deny   ip 10.0.50.0 0.0.1.255 172.16.0.0 0.15.255.255
 50 deny   ip 10.0.50.0 0.0.1.255 192.168.0.0 0.0.255.255
 60 permit ip 10.0.50.0 0.0.1.255 any                            ! อินเทอร์เน็ต
!
interface Vlan50
 ip access-group GUEST-IN in
```

### Extended ACL — อนุญาตเฉพาะบริการที่จำเป็นไปยัง Server zone
```
ip access-list extended TO-SERVERS
 10 permit tcp 10.0.10.0 0.0.0.255 host 10.0.100.10 eq 443       ! ผู้ใช้ → เว็บแอป
 20 permit tcp 10.0.10.0 0.0.0.255 host 10.0.100.20 eq 445       ! ผู้ใช้ → file server
 30 permit tcp host 10.0.99.10 10.0.100.0 0.0.0.255 eq 22         ! admin → SSH
 40 permit icmp 10.0.0.0 0.255.255.255 10.0.100.0 0.0.0.255 echo
 50 deny   ip any 10.0.100.0 0.0.0.255 log
 60 permit ip any any
```
**Operators:** `eq` (เท่ากับ), `neq`, `gt`, `lt`, `range 8000 8100` · ชื่อ port: `www`(80), `domain`(53), `bootps`(67) …

---

## 6. ทิศทาง In / Out

```
          in →  [ROUTER INTERFACE]  → out
 - in  = ตรวจ packet ที่ "เข้ามา" ทาง interface นี้ (ก่อน routing)
 - out = ตรวจ packet ที่ "ออกไป" ทาง interface นี้ (หลัง routing)
```
- **1 interface · 1 ทิศทาง · 1 protocol (IPv4/IPv6) = ใส่ได้ 1 ACL**
- ACL **ขาออก (out) ไม่ตรวจ traffic ที่ router สร้างเอง** (เช่น ping จาก router)
- คิดในมุมของ router: "ยืนอยู่ในตัว router แล้วมองที่ interface"

---

## 7. ข้อจำกัด: ACL เป็น Stateless

ACL ทั่วไป **ไม่จำสถานะการเชื่อมต่อ** — ถ้าอนุญาตขาไป ต้องคิดถึง **ขากลับ** ด้วย
```
 ผู้ใช้ภายใน → เว็บภายนอก port 443 (ขาไป: src port สุ่ม → dst 443)
 ขากลับ: src 443 → dst port สุ่ม → ACL ขาเข้าที่ขอบต้อง "อนุญาต" ด้วย ไม่เช่นนั้นถูกบล็อก
```
ทางแก้แบบเก่า: `permit tcp any any established` (อนุญาตเฉพาะ TCP ที่มี ACK/RST = การตอบกลับ) — แต่ใช้กับ UDP/ICMP ไม่ได้และปลอมได้
**ทางแก้ที่ถูกต้อง:** ใช้ **stateful firewall** (Level 62) ซึ่งจำ session และอนุญาตขากลับอัตโนมัติ

| | ACL (stateless) | Stateful Firewall |
|---|---|---|
| จำ session | ❌ | ✅ |
| ขากลับ | ต้องเขียนกฎเอง | อนุญาตอัตโนมัติ |
| ตรวจแอปพลิเคชัน | ❌ | NGFW ✅ |
| Log/สถิติ | จำกัด | ละเอียด |
| ความเร็ว | เร็วมาก (hardware) | ขึ้นกับรุ่น |
| ใช้ที่ | switch/router: กรองเบื้องต้น, VTY, ระหว่าง VLAN ที่เชื่อถือ | ขอบเครือข่าย, ระหว่าง zone ความเสี่ยงต่างกัน |

---

## 8. แก้ไข ACL อย่างปลอดภัย

```
show access-lists GUEST-IN
Extended IP access list GUEST-IN
    10 permit udp ... (1532 matches)          ← จำนวนครั้งที่ตรง — ใช้ดูว่ากฎถูกใช้จริงไหม
    30 deny ip ... log (87 matches)
!
ip access-list extended GUEST-IN
 25 permit tcp 10.0.50.0 0.0.1.255 host 10.0.0.80 eq 443      ! แทรกระหว่าง 20 กับ 30
 no 40                                                         ! ลบบรรทัดที่ 40
ip access-list resequence GUEST-IN 10 10                       ! เรียงเลขใหม่
clear access-list counters GUEST-IN
```
> ⚠️ **ห้ามลบทั้ง ACL แล้วสร้างใหม่ขณะผูกกับ interface ผ่าน remote** — ระหว่างนั้นอาจปล่อยผ่านหรือบล็อกทั้งหมด (รวม SSH ของเรา) · ใช้ `reload in 10` ก่อนแก้ ACL ที่อาจตัดตัวเอง (Level 29)
> ⚠️ **ACL ขาเข้าที่ interface ที่เรา SSH อยู่** — ต้องอนุญาต traffic ของเราก่อนเสมอ

---

## 9. IPv6 ACL

- เป็น named เสมอ · ไม่มี wildcard (ใช้ prefix length)
- **ระวัง implicit rules:** IPv6 ACL ของ Cisco มี implicit **permit** สำหรับ **NDP (NS/NA)** ก่อน implicit deny — ถ้าเขียน `deny ipv6 any any` เองท้ายสุดจะบล็อก NDP ทำให้เครือข่ายพัง ต้องอนุญาต ICMPv6 ที่จำเป็น
```
ipv6 access-list V6-IN
 permit icmp any any nd-na
 permit icmp any any nd-ns
 permit tcp 2001:db8:10::/64 any eq 443
 deny ipv6 any any log
interface Gi0/1
 ipv6 traffic-filter V6-IN in
```

---

## 10. Best Practice

- เขียน **remark** อธิบายทุกกฎ (`remark Allow HR to payroll - CHG-1234`)
- ใช้ **object-group** (ถ้าอุปกรณ์รองรับ) จัดกลุ่ม IP/port ให้อ่านง่าย
- กฎเจาะจงไว้บน · กฎที่ match บ่อยไว้บน (ประสิทธิภาพบนอุปกรณ์ software)
- ใส่ `deny ... log` ท้ายสุดเพื่อดูสิ่งที่ถูกบล็อก (แต่ระวัง log จำนวนมากกิน CPU)
- **ตรวจ hit count เป็นระยะ** ลบกฎที่ไม่ถูกใช้ (หลังยืนยันกับเจ้าของ)
- ทดสอบใน lab/ช่วง maintenance และมี rollback

---

## 11. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| ACL ตรวจทุกกฎแล้วเลือกกฎที่ดีที่สุด | หยุดที่กฎแรกที่ตรง |
| ไม่ตรงกฎใดก็ผ่าน | implicit deny ท้ายสุด |
| wildcard เหมือน subnet mask | ตรงข้ามกัน (255.255.255.255 − mask) |
| อนุญาตขาไปแล้วขากลับผ่านเอง | ACL เป็น stateless ต้องอนุญาตขากลับเอง (หรือใช้ firewall) |
| ใส่หลาย ACL บน interface เดียวทิศเดียวได้ | ได้ 1 ACL ต่อ interface/ทิศทาง/protocol |

---

## 12. Cheat Sheet

```
Top-down · first match แล้วหยุด · implicit deny any ท้ายสุด · ต้องมี permit
Wildcard = 255.255.255.255 − mask · /24 = 0.0.0.255 · host = /32 · any
Standard (src) วางใกล้ปลายทาง · Extended (src/dst/proto/port) วางใกล้ต้นทาง
ip access-list extended NAME → seq permit|deny proto src dst eq port [log]
interface: ip access-group NAME in|out · VTY: access-class NAME in
1 ACL ต่อ interface/ทิศทาง/protocol · out ไม่ตรวจ traffic ที่ router สร้างเอง
Stateless → ขากลับต้องคิดเอง → ใช้ stateful firewall ที่ขอบ/ระหว่าง zone
show access-lists (hit count) · แทรกด้วย seq · no <seq> · reload in 10 ก่อนแก้ remote
IPv6 ACL: อนุญาต ND (ns/na) ก่อน deny ipv6 any any
```

---

## 13. แบบทดสอบ 10 ข้อ

1. อธิบายกฎการทำงานของ ACL 3 ข้อ
2. wildcard mask ของ 172.16.32.0/20 คืออะไร
3. ACL มีกฎ `deny host 10.1.1.5` เพียงกฎเดียวแล้วผูกกับ interface ผลคืออะไร
4. Standard กับ Extended ACL ต่างกันอย่างไร และควรวางที่ใด
5. ต้องการให้เข้า SSH อุปกรณ์ได้เฉพาะจาก 10.0.99.0/24 ใช้ ACL ประเภทใด ผูกอย่างไร
6. ACL ด้านล่าง กฎใดจะไม่มีวันถูกใช้ เพราะอะไร: `10 permit ip 10.0.0.0 0.255.255.255 any` / `20 deny ip host 10.1.1.1 any`
7. ACL ขาออก (out) ตรวจ ping ที่ router สร้างเองหรือไม่
8. ทำไมกล่าวว่า ACL เป็น stateless และมีผลอย่างไร
9. วิธีเพิ่มกฎระหว่างบรรทัด 20 กับ 30 ใน named ACL
10. ข้อควรระวังเมื่อเขียน IPv6 ACL ที่จบด้วย `deny ipv6 any any`

<details><summary><b>เฉลย</b></summary>

1. ตรวจจากบนลงล่าง; หยุดที่กฎแรกที่ตรงแล้วทำตาม; ไม่ตรงกฎใดเลยถูก deny (implicit deny)
2. 0.0.15.255
3. บล็อกทุกอย่าง (10.1.1.5 ตรงกฎ deny ส่วน packet อื่นตก implicit deny)
4. Standard ตรวจเฉพาะ IP ต้นทาง วางใกล้ปลายทาง; Extended ตรวจต้นทาง ปลายทาง protocol port วางใกล้ต้นทาง
5. Standard ACL `permit 10.0.99.0 0.0.0.255` แล้ว `line vty 0 15` → `access-class <ชื่อ> in`
6. กฎ 20 — 10.1.1.1 ตรงกฎ 10 ซึ่งกว้างกว่าและอยู่ก่อน (shadowed)
7. ไม่ตรวจ
8. ไม่จำสถานะการเชื่อมต่อ จึงต้องเขียนกฎอนุญาตขากลับเอง และตรวจระดับแอปไม่ได้ — ที่ขอบ/ระหว่าง zone ควรใช้ stateful firewall
9. `ip access-list extended <ชื่อ>` → `25 permit ...`
10. จะบล็อก NDP (ICMPv6 NS/NA) ทำให้หาเพื่อนบ้าน/router ไม่ได้ ต้องอนุญาต ICMPv6 ที่จำเป็นก่อน
</details>

---

➡️ ต่อไป: **Level 54 — QoS**
