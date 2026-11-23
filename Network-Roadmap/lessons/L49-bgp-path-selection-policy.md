# บทเรียน Level 49 — BGP Path Selection & Policy (ฉบับละเอียด)

> อ่านจบแล้วจะ: รู้ลำดับการเลือก best path ของ BGP · ใช้ Weight / Local Preference / AS-Path prepend / MED / Community ควบคุม traffic ขาออกและขาเข้า · เขียน prefix-list, route-map, AS-path filter · รู้จัก RPKI/MANRS · ทำ redistribution อย่างปลอดภัยด้วย route tag

---

## 1. BGP เลือกเส้นทางอย่างไร

ถ้ามีหลายเส้นทางไปยัง prefix เดียวกัน BGP เปรียบเทียบ **path attributes** ตามลำดับ (ตัวแรกที่แยกได้ชนะ) — ลำดับของ Cisco:

| ลำดับ | Attribute | เลือก | ขอบเขต | ใครตั้ง |
|---|---|---|---|---|
| 0 | Next-hop ต้อง reachable | (เงื่อนไขก่อนเปรียบเทียบ) | | |
| **1** | **Weight** (Cisco) | **สูงกว่า** | **เฉพาะ router นี้** (ไม่ส่งต่อ) | ตัวเราเอง |
| **2** | **Local Preference** | **สูงกว่า** (ค่าเริ่มต้น 100) | **ทั้ง AS** (ส่งใน iBGP) | ตัวเราเอง |
| 3 | Locally originated | route ที่ router นี้สร้างเอง (network/aggregate) | | |
| **4** | **AS-PATH** | **สั้นกว่า** | ส่งต่อทั่วอินเทอร์เน็ต | ทุก AS ตามทาง |
| 5 | Origin | IGP (i) < EGP (e) < Incomplete (?) | | |
| **6** | **MED** (Multi-Exit Discriminator) | **ต่ำกว่า** (ปกติเทียบเฉพาะจาก AS เดียวกัน) | ส่งให้ AS เพื่อนบ้าน | AS เพื่อนบ้าน |
| 7 | eBGP > iBGP | เลือก eBGP | | |
| 8 | IGP metric ไปยัง next-hop | ต่ำกว่า (hot-potato) | | |
| 9 | Oldest eBGP path | เส้นทางที่เสถียรนานกว่า | | |
| 10 | Router ID ของ neighbor | ต่ำกว่า | | |
| 11 | Neighbor IP | ต่ำกว่า | | |

**วิธีจำ (ยอดนิยม):** "**W**e **L**ove **O**ranges **A**s **O**ranges **M**ean **P**ure **R**efreshment" → Weight, Local pref, Originate, AS-path, Origin, MED, Paths (eBGP>iBGP, IGP metric...), Router ID

---

## 2. ควบคุม Traffic **ขาออก** (Outbound) — เราตัดสินใจเองได้

ขาออก = traffic จากองค์กรไปอินเทอร์เน็ต → เราเลือกเองว่าจะออกทาง ISP ไหน

### Local Preference ⭐ (ทั้ง AS)
```
 ต้องการ: ทุก router ในบริษัทออกทาง ISP-A เป็นหลัก ISP-B สำรอง
route-map ISP-A-IN permit 10
 set local-preference 200
router bgp 65001
 address-family ipv4
  neighbor 203.0.113.1 route-map ISP-A-IN in        ! route จาก ISP-A ได้ LP 200 > 100 ของ ISP-B
```
LP ถูกส่งต่อให้ iBGP peer ทุกตัว → **ทั้ง AS ตัดสินใจไปทางเดียวกัน**

### Weight (เฉพาะ router เดียว)
```
neighbor 203.0.113.1 weight 200       ! มีผลแค่ router นี้ (Cisco เท่านั้น)
```
ใช้เมื่ออยากให้ router ตัวเดียวชอบทางใดทางหนึ่ง

---

## 3. ควบคุม Traffic **ขาเข้า** (Inbound) — ทำได้แค่ "ขอ" ให้คนอื่นเลือก

ขาเข้า = traffic จากอินเทอร์เน็ตมาหา prefix ของเรา → **AS อื่นเป็นผู้ตัดสินใจ** เราทำได้แค่ปรับสิ่งที่ประกาศออกไปเพื่อ "ชักจูง"

### AS-PATH Prepending
ใส่ ASN ของตัวเองซ้ำหลายครั้งในเส้นทางที่ไม่ต้องการ ให้ดู **ยาวกว่า**
```
 ต้องการ: traffic ขาเข้ามาทาง ISP-A เป็นหลัก
route-map ISP-B-OUT permit 10
 set as-path prepend 65001 65001 65001
router bgp 65001
 address-family ipv4
  neighbor 198.51.100.9 route-map ISP-B-OUT out
 → อินเทอร์เน็ตเห็น: ผ่าน ISP-A = "64500 65001" · ผ่าน ISP-B = "64600 65001 65001 65001 65001" (ยาวกว่า)
```
⚠️ ไม่รับประกัน 100% — AS อื่นอาจใช้ local preference ของเขาเองซึ่งชนะ AS-PATH

### MED
บอก **AS เพื่อนบ้านเดียวกัน** (ที่เชื่อมกับเราหลายจุด) ว่าควรเข้ามาทางจุดไหน (ต่ำกว่า = ชอบกว่า) — ใช้ได้กับ ISP เดียวที่ต่อหลายลิงก์ และ ISP ต้องยอมรับ MED

### More-specific prefix
ประกาศ /24 ที่เจาะจงกว่าทาง ISP-A และ aggregate /23 ทั้งสองทาง → longest match ทำให้ traffic เข้าทาง ISP-A (ใช้ได้ผลแน่นอนกว่า แต่เพิ่มขนาดตารางอินเทอร์เน็ต และ ISP มักไม่รับ prefix ที่ยาวกว่า /24)

### BGP Communities
**Tag** (ตัวเลข `ASN:value`) ที่แนบไปกับ route เพื่อส่ง "คำสั่ง/ข้อมูล" ให้ AS อื่น
- **Well-known:** `no-export` (อย่าส่งต่อออกนอก AS), `no-advertise`, `local-AS`
- **ของ ISP:** ISP หลายรายประกาศ community ให้ลูกค้าใช้ เช่น `64500:3` = prepend 3 ครั้งไปยัง peer บางกลุ่ม, `64500:666` = **blackhole** (RTBH — ทิ้ง traffic ไปยัง IP ที่ถูก DDoS)
- ภายในองค์กรใช้ community แท็ก route ตามแหล่งที่มา แล้วตั้ง policy ตาม tag
```
route-map TO-ISP-A permit 10
 set community 64500:100 additive
router bgp 65001
 neighbor 203.0.113.1 send-community
```

---

## 4. เครื่องมือเขียน Policy

### Prefix-list (กรองตาม prefix + ความยาว)
```
ip prefix-list MY-NETS seq 10 permit 198.51.100.0/24
ip prefix-list BOGONS seq 10 deny 10.0.0.0/8 le 32          ! le = ความยาว ≤ 32 (ทุก subnet ภายใน)
ip prefix-list BOGONS seq 20 deny 192.168.0.0/16 le 32
ip prefix-list BOGONS seq 30 deny 0.0.0.0/0 ge 25            ! ไม่รับ prefix ยาวกว่า /24
ip prefix-list BOGONS seq 100 permit 0.0.0.0/0 le 24
```
`ge` = ยาวอย่างน้อย, `le` = ยาวไม่เกิน · ท้ายสุดมี **implicit deny**

### AS-path access-list (กรองตาม AS-PATH ด้วย regular expression)
```
ip as-path access-list 10 permit ^$            ! route ที่ AS เราสร้างเอง (AS-PATH ว่าง)
ip as-path access-list 20 permit ^64500_       ! เรียนโดยตรงจาก AS 64500
```

### Route-map (if-then)
```
route-map ISP-A-IN deny 5
 match ip address prefix-list BOGONS-DENY
route-map ISP-A-IN permit 10
 set local-preference 200
route-map ISP-A-IN permit 100                  ! (ต้องมี permit ท้ายสุด ไม่เช่นนั้น route อื่นถูกทิ้งหมด)
```
หลังแก้ policy ใช้ `clear ip bgp <neighbor> soft in/out` เพื่อใช้ policy ใหม่โดยไม่ตัด session

---

## 5. ความปลอดภัยของ BGP (MANRS)

BGP เดิม **เชื่อทุกอย่างที่ peer ประกาศ** → เกิด route hijack (ประกาศ prefix ที่ไม่ใช่ของตน) และ route leak บ่อย

**MANRS (Mutually Agreed Norms for Routing Security)** — แนวปฏิบัติสำหรับ network operator
1. **Filtering** — กรองทั้งขาเข้าและขาออก (ประกาศเฉพาะ prefix ของตนและของลูกค้าที่ยืนยันแล้ว)
2. **Anti-spoofing** — กรอง source IP ปลอม (BCP 38/uRPF)
3. **Coordination** — ข้อมูลติดต่อเป็นปัจจุบัน
4. **Global validation** — ลงทะเบียน route ใน **IRR** และสร้าง **RPKI ROA**

### RPKI (Resource Public Key Infrastructure)
- เจ้าของ prefix สร้าง **ROA (Route Origin Authorization)** ผ่านพอร์ทัลของ RIR (APNIC) ระบุว่า "prefix นี้ ความยาวไม่เกินเท่านี้ อนุญาตให้ AS นี้เป็นผู้ประกาศ"
- router ตรวจ route ที่ได้รับกับ validator (เช่น Routinator, rpki-client) → สถานะ **Valid / Invalid / NotFound** → นิยม **drop Invalid**
- ป้องกัน **origin hijack** ได้ (ยังป้องกัน path manipulation ไม่ได้ทั้งหมด — มี ASPA เพิ่มในอนาคต)

### มาตรการอื่น
- `maximum-prefix` ต่อ neighbor
- TCP-AO/MD5, **GTSM** (`neighbor X ttl-security hops 1`)
- ไม่รับ bogon (private, reserved), prefix ยาวกว่า /24 (IPv4) หรือ /48 (IPv6), และ default route ถ้าไม่ต้องการ

---

## 6. Redistribution — นำ route ระหว่าง protocol

ใช้เมื่อเชื่อม 2 routing domain (เช่น OSPF ภายใน ↔ BGP กับ WAN/MPLS, EIGRP ↔ OSPF ช่วง migration)

```
router ospf 1
 redistribute bgp 65001 subnets route-map BGP-TO-OSPF
router bgp 65001
 address-family ipv4
  redistribute ospf 1 route-map OSPF-TO-BGP
```
**ความเสี่ยงของ Mutual redistribution หลายจุด:** route จาก A → B (จุดที่ 1) → ย้อนกลับ B → A (จุดที่ 2) → เกิด **routing loop / suboptimal routing**

**ป้องกันด้วย Route Tag**
```
route-map OSPF-TO-EIGRP deny 10
 match tag 200                       ! อย่านำ route ที่เคยมาจาก EIGRP กลับเข้าไป
route-map OSPF-TO-EIGRP permit 20
 set tag 100                         ! แท็กว่ามาจาก OSPF
route-map EIGRP-TO-OSPF deny 10
 match tag 100
route-map EIGRP-TO-OSPF permit 20
 set tag 200
```
**แนวปฏิบัติ:** redistribute **เท่าที่จำเป็น** (กรองด้วย prefix-list), ระบุ seed metric, ใช้ tag, ทดสอบใน lab ก่อนเสมอ

---

## 7. ตัวอย่างออกแบบ: องค์กร Dual ISP ด้วย BGP

```
 เป้าหมาย: ออกทาง ISP-A เป็นหลัก (1 Gbps) · เข้าทาง ISP-A เป็นหลัก · ISP-B สำรองทั้งสองทาง
 - รับเฉพาะ default route (หรือ partial route) จากทั้งสอง ISP (ประหยัด memory)
 - Outbound: route-map ISP-A-IN set local-preference 200
 - Inbound: route-map ISP-B-OUT set as-path prepend 65001 65001 65001 (หรือ community ของ ISP)
 - Outbound filter: prefix-list ประกาศเฉพาะ 198.51.100.0/24 ทั้งสอง ISP
 - Inbound filter: ไม่รับ bogon/prefix ของตัวเอง · maximum-prefix
 - RPKI ROA สำหรับ prefix ของเรา (origin AS 65001 — ต้องเป็น public ASN ในการใช้งานจริง)
 - ทดสอบ: ปิด ISP-A แล้ววัดเวลาที่ traffic ย้ายไป ISP-B ทั้งสองทิศทาง
```

---

## 8. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| Local Preference ต่ำกว่าชนะ | **สูงกว่าชนะ** (ต่างจาก MED ที่ต่ำกว่าชนะ) |
| Weight ส่งต่อให้ router อื่น | Weight มีผลเฉพาะ router เดียว |
| AS-path prepend ควบคุม traffic ขาออก | ใช้ชักจูง **ขาเข้า** |
| ควบคุมขาเข้าได้แน่นอน 100% | ทำได้แค่ชักจูง AS อื่นมีนโยบายของตัวเอง |
| route-map ที่ไม่มี permit ท้ายสุดปล่อย route ที่เหลือผ่าน | implicit deny ทิ้งทั้งหมด |

---

## 9. Cheat Sheet

```
ลำดับ: Weight↑ → LocalPref↑ → Originated → AS-PATH สั้น → Origin (i<e<?) → MED↓ → eBGP>iBGP → IGP metric↓ → oldest → RID↓
ขาออก (เราเลือก): Local Preference (ทั้ง AS, default 100) · Weight (router เดียว)
ขาเข้า (ชักจูง): AS-PATH prepend · MED (AS เดียวกัน) · more-specific · community ของ ISP
Community: no-export · ASN:value · RTBH blackhole · send-community
Prefix-list ge/le · AS-path regex (^$ = ของเราเอง) · route-map (ต้องมี permit ท้าย)
clear ip bgp X soft in|out
ความปลอดภัย: filter in/out · max-prefix · TTL security · RPKI ROA (drop invalid) · MANRS
Redistribution: กรอง + route tag ป้องกัน loop
```

---

## 10. แบบทดสอบ 10 ข้อ

1. เรียง 6 attribute แรกในการเลือก best path ของ BGP (Cisco)
2. Weight ต่างจาก Local Preference อย่างไร
3. ต้องการให้ทั้งบริษัทออกอินเทอร์เน็ตทาง ISP-A เป็นหลัก ใช้ attribute ใด ตั้งที่ไหน
4. ต้องการให้ traffic จากอินเทอร์เน็ตเข้ามาทาง ISP-A เป็นหลัก ทำได้อย่างไร (2 วิธี)
5. MED ต่ำหรือสูงชนะ และใช้เปรียบเทียบเมื่อใด
6. Community `no-export` ทำอะไร
7. RTBH คืออะไร ใช้เมื่อใด
8. RPKI ROA ป้องกันอะไร
9. Prefix-list `permit 10.0.0.0/8 le 24` หมายความว่าอะไร
10. Mutual redistribution มีความเสี่ยงอะไร ป้องกันอย่างไร

<details><summary><b>เฉลย</b></summary>

1. Weight → Local Preference → Locally originated → AS-PATH สั้น → Origin → MED
2. Weight มีผลเฉพาะ router เดียวและเป็นของ Cisco; Local Preference ส่งต่อใน iBGP มีผลทั้ง AS (ทั้งคู่สูงกว่าชนะ)
3. Local Preference — ตั้งเป็นค่าสูง (เช่น 200) บน route ที่รับจาก ISP-A (route-map ขาเข้าจาก neighbor ISP-A)
4. AS-PATH prepend บน route ที่ประกาศออกไปทาง ISP-B; ประกาศ more-specific ทาง ISP-A; หรือใช้ community ของ ISP (MED ถ้าเป็น ISP เดียวกันหลายลิงก์)
5. ต่ำกว่าชนะ — โดยปกติเปรียบเทียบเฉพาะเส้นทางที่มาจาก AS เพื่อนบ้านเดียวกัน
6. บอกให้ AS ที่รับ route ไม่ส่งต่อ route นั้นออกไปยัง eBGP peer ภายนอก
7. Remotely Triggered Black Hole — ประกาศ IP ที่ถูก DDoS พร้อม community blackhole ให้ ISP ทิ้ง traffic ไปยัง IP นั้นที่ขอบเครือข่ายของ ISP
8. Origin hijack — AS ที่ไม่ได้รับอนุญาตประกาศ prefix ของเรา
9. อนุญาต prefix ที่อยู่ใน 10.0.0.0/8 และมีความยาวตั้งแต่ /8 ถึง /24
10. Route วนกลับเข้า domain เดิมทำให้เกิด loop/เส้นทางไม่ optimal — ป้องกันด้วย route tag + route-map กรอง, redistribute เฉพาะที่จำเป็น
</details>

---

➡️ ต่อไป: **Level 50 — First Hop Redundancy (HSRP / VRRP / GLBP)**
