# บทเรียน Level 48 — BGP พื้นฐาน (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจว่า BGP คือโปรโตคอลที่ทำให้อินเทอร์เน็ตทำงาน · AS/ASN · eBGP vs iBGP · neighbor state · การประกาศ prefix · next-hop-self, update-source, multihop · iBGP full mesh / Route Reflector · ตั้งค่าและแก้ปัญหา BGP เบื้องต้น

---

## 1. BGP คืออะไร

**BGP (Border Gateway Protocol, BGP-4, RFC 4271)** — **routing protocol ระหว่าง Autonomous System (AS)** เป็น **path-vector** และเป็นโปรโตคอลเดียวที่ใช้แลกเส้นทางระหว่าง ISP/องค์กรบนอินเทอร์เน็ต (ตารางอินเทอร์เน็ต IPv4 มีราวหนึ่งล้าน prefix)

| | IGP (OSPF/EIGRP) | BGP |
|---|---|---|
| ขอบเขต | ภายในองค์กร | **ระหว่างองค์กร** (และภายใน DC/WAN ขนาดใหญ่) |
| เป้าหมาย | หาเส้นทางที่เร็วที่สุด converge เร็ว | **ควบคุมด้วยนโยบาย (policy)**, scale สูงมาก, เสถียร |
| ค้นหาเพื่อนบ้าน | อัตโนมัติ (multicast hello) | **กำหนด neighbor เอง** |
| Transport | IP โดยตรง | **TCP 179** (reliable) |
| เลือกเส้นทาง | metric (cost) | **path attributes** (Level 49) |
| AD | 110/90 | **eBGP 20, iBGP 200** |

> 💡 **เปรียบเทียบ:** IGP คือระบบนำทางภายในเมือง (หาทางเร็วที่สุด) — BGP คือ **ข้อตกลงการค้าระหว่างประเทศ** ว่าใครยอมให้สินค้าผ่านประเทศใด ด้วยเงื่อนไขอะไร

### ใครใช้ BGP
- **ISP / Cloud / Content provider** — เชื่อมกันเป็นอินเทอร์เน็ต
- **องค์กรที่ multihomed** (ต่อ ISP 2 รายด้วย public IP ของตัวเอง)
- **Data center fabric** (eBGP ระหว่าง leaf-spine — Level 73), EVPN (Level 74)
- **MPLS VPN, SD-WAN, Hybrid cloud** (AWS Direct Connect/VPN, Azure ExpressRoute ใช้ BGP)
- Kubernetes (Calico, MetalLB BGP mode)

---

## 2. Autonomous System (AS) และ ASN

**AS** = กลุ่ม IP prefix ภายใต้การบริหารและนโยบาย routing เดียวกัน มีหมายเลข **ASN**
| ช่วง | ประเภท |
|---|---|
| 1 – 64,495 | Public ASN (2-byte) |
| **64,512 – 65,534** | **Private ASN** (2-byte) |
| 65,536 – 4,294,967,295 | 4-byte ASN (public) |
| **4,200,000,000 – 4,294,967,294** | **Private ASN** (4-byte) |

- Public ASN ขอได้จาก RIR (**APNIC** สำหรับไทย) ต้องมีเหตุผล เช่น multihoming
- **Private ASN** ใช้ภายในองค์กร, DC fabric, เชื่อมกับ ISP ที่รับ private ASN แล้วตัดออกก่อนส่งต่อ (remove-private-as)

---

## 3. eBGP vs iBGP

```
     AS 65001 (บริษัท)                    AS 64500 (ISP-A)
  [R1]═══iBGP═══[R2]─────── eBGP ─────────[ISP-A]
    ║                                         
    ╚══iBGP══[R3]────────── eBGP ─────────[ISP-B] AS 64600
```
| | **eBGP** | **iBGP** |
|---|---|---|
| ระหว่าง | **คนละ AS** | **AS เดียวกัน** |
| AD | **20** | **200** |
| TTL ค่าเริ่มต้น | **1** (ต้องต่อตรง ไม่งั้นใช้ multihop) | 255 |
| ประกาศต่อ | ส่งต่อ route ให้ทุก peer | **route ที่ได้จาก iBGP จะไม่ถูกส่งต่อให้ iBGP peer อื่น** (กฎ split horizon ของ iBGP) |
| Next-hop | เปลี่ยนเป็นตัวเองเมื่อส่งออก | **ไม่เปลี่ยน** (คงเป็น next-hop ภายนอก) |
| AS-PATH | เพิ่ม ASN ของตัวเองเมื่อส่งออก | ไม่เพิ่ม |

### iBGP Full Mesh และทางแก้
เพราะ iBGP ไม่ส่งต่อ route ที่ได้จาก iBGP → **ทุก router ที่รัน iBGP ต้อง peer กันครบทุกคู่** (n(n−1)/2) — router 20 ตัว = 190 session ❌
**ทางแก้:**
- **Route Reflector (RR)** ⭐ — router กลางที่ได้รับอนุญาตให้ "สะท้อน" route ให้ client ทุกตัว → client peer แค่กับ RR (ควรมี RR 2 ตัวสำรองกัน)
- Confederation (แบ่ง AS ย่อย — ใช้น้อย)

---

## 4. BGP Neighbor States

```
 Idle → Connect → Active → OpenSent → OpenConfirm → Established
```
| State | ความหมาย / สิ่งที่บ่งบอก |
|---|---|
| **Idle** | ยังไม่เริ่ม หรือถูกปิด/มีข้อผิดพลาด (เช่น ไม่มี route ไปหา neighbor) |
| **Connect** | กำลังสร้าง TCP |
| **Active** | ⚠️ **TCP ไม่สำเร็จ กำลังลองใหม่** (ชื่อชวนเข้าใจผิด — ไม่ใช่ "ทำงานอยู่") |
| **OpenSent / OpenConfirm** | TCP ได้แล้ว กำลังแลก OPEN (ตรวจ AS, router-id, hold time, capability) |
| **Established** ✅ | พร้อมแลก route (UPDATE) |

**ข้อความ:** OPEN (เริ่มต้น), **UPDATE** (ประกาศ/ถอน route), **KEEPALIVE** (ทุก 60 วินาที, hold time 180 วินาที), NOTIFICATION (แจ้งข้อผิดพลาดแล้วปิด session)

---

## 5. ตั้งค่า eBGP กับ ISP (องค์กร multihomed)

```
router bgp 65001
 bgp router-id 1.1.1.1
 bgp log-neighbor-changes
 neighbor 203.0.113.1 remote-as 64500              ! ISP-A
 neighbor 203.0.113.1 description ISP-A
 neighbor 203.0.113.1 password S3cr3t!             ! TCP MD5 (ตามที่ตกลงกับ ISP)
 !
 address-family ipv4 unicast
  network 198.51.100.0 mask 255.255.255.0          ! ประกาศ prefix ของบริษัท
  neighbor 203.0.113.1 activate
  neighbor 203.0.113.1 prefix-list OUT-ONLY-MINE out    ! ⚠️ ประกาศเฉพาะ prefix ของเราเท่านั้น
  neighbor 203.0.113.1 maximum-prefix 1000000 90 warning-only
 exit-address-family
!
ip prefix-list OUT-ONLY-MINE seq 10 permit 198.51.100.0/24
ip route 198.51.100.0 255.255.255.0 Null0          ! ให้ prefix มีอยู่ใน routing table (เงื่อนไขของ network)
```

### กฎสำคัญของคำสั่ง `network` ใน BGP
**ประกาศได้ก็ต่อเมื่อ prefix + mask นั้น "มีอยู่ใน routing table ตรงทุกตัว"** (ต่างจาก OSPF/EIGRP ที่ใช้เลือก interface)
→ นิยมสร้าง **static route ไป Null0** ของ aggregate ไว้ เพื่อให้ประกาศได้เสถียร (ไม่หายเมื่อวงย่อยภายใน flap)

> ⚠️ **Route leak:** องค์กรที่ multihomed แต่ไม่กรอง route ขาออก อาจ **ประกาศ route ที่ได้จาก ISP-A ออกไปให้ ISP-B** → กลายเป็นทางผ่าน (transit) ของอินเทอร์เน็ต ทำให้ traffic มหาศาลวิ่งผ่านบริษัทหรือเกิด outage ระดับภูมิภาค **ต้องใช้ prefix-list ขาออกเสมอ**

---

## 6. iBGP — ตั้งค่าที่จำเป็น

```
router bgp 65001
 neighbor 10.0.0.2 remote-as 65001                 ! AS เดียวกัน = iBGP
 neighbor 10.0.0.2 update-source Loopback0         ! ใช้ loopback ทำ session (ไม่หลุดเมื่อ interface หนึ่ง down)
 address-family ipv4 unicast
  neighbor 10.0.0.2 activate
  neighbor 10.0.0.2 next-hop-self                  ! ⭐ เปลี่ยน next-hop ของ route ภายนอกเป็นตัวเอง
```
| คำสั่ง | ปัญหาที่แก้ |
|---|---|
| **update-source Loopback0** | ใช้ IP ของ loopback (ซึ่ง IGP ประกาศไว้และ up ตลอด) ทำ session — ทนต่อลิงก์บางเส้นขาด |
| **next-hop-self** | route จาก eBGP มี next-hop เป็น IP ของ ISP ซึ่ง router ภายในอาจไม่รู้จัก → route ใช้ไม่ได้ (inaccessible) — next-hop-self แก้ด้วยการตั้ง next-hop เป็นตัวเอง |
| **ebgp-multihop 2** (eBGP) | peer eBGP ผ่าน loopback/ไม่ได้ต่อตรง (TTL ค่าเริ่มต้น 1) |

> 🔑 **iBGP ต้องอาศัย IGP** (OSPF/IS-IS) ให้ router ภายในรู้จัก loopback/next-hop ของกันและกัน

### Route Reflector
```
! ที่ RR
router bgp 65001
 address-family ipv4 unicast
  neighbor 10.0.0.11 route-reflector-client
  neighbor 10.0.0.12 route-reflector-client
```

---

## 7. คำสั่งตรวจสอบ

```
show ip bgp summary
Neighbor      V    AS MsgRcvd MsgSent  TblVer InQ OutQ Up/Down  State/PfxRcd
203.0.113.1   4 64500  125432    1234      ...   0    0 3d02h    985432      ← ตัวเลข = Established + จำนวน prefix ที่รับ
198.51.100.9  4 64600       0       0        0   0    0 never    Active      ← TCP ไม่สำเร็จ

show ip bgp                                   ! BGP table (ทุกเส้นทาง)
   Network          Next Hop        Metric LocPrf Weight Path
*> 8.8.8.0/24       203.0.113.1                        0 64500 15169 i   ← > = best path
*  8.8.8.0/24       192.0.2.1                          0 64600 3356 15169 i
show ip bgp 8.8.8.8                           ! รายละเอียดของ prefix (attribute ทุกตัว)
show ip bgp neighbors 203.0.113.1 advertised-routes    ! เราประกาศอะไรออกไป
show ip bgp neighbors 203.0.113.1 routes               ! รับอะไรมา (หลัง policy)
clear ip bgp 203.0.113.1 soft in/out                    ! ใช้ policy ใหม่โดยไม่ตัด session
```
**สัญลักษณ์:** `*` valid · `>` best · `i` (ซ้ายมือ) เรียนจาก iBGP · `r` RIB-failure · ท้ายบรรทัด `i`=IGP, `?`=incomplete (redistribute) · **Path** = AS-PATH (อ่านจากขวาไปซ้าย: ขวาสุดคือ AS ต้นทาง)

---

## 8. แก้ปัญหา BGP

| อาการ | สาเหตุที่น่าจะเป็น |
|---|---|
| ค้าง **Active/Idle** | IP ของ neighbor ผิด, AS ผิด, ไม่มี route ไปหา neighbor, **ACL/firewall บล็อก TCP 179**, eBGP ผ่าน loopback แต่ไม่ได้ตั้ง multihop/update-source, password ไม่ตรง |
| ขึ้นแล้วหลุดซ้ำ ๆ (flap) | hold timer, MTU/ลิงก์ไม่เสถียร, max-prefix เกิน (session ถูกปิด) |
| Established แต่ไม่มี route | ยังไม่ activate ใน address-family, policy กรองหมด, network ไม่ตรงกับ routing table |
| Route อยู่ใน BGP table แต่ไม่ใช้ | next-hop ไม่รู้จัก (ลืม next-hop-self), แพ้ AD (เช่น iBGP 200 แพ้ OSPF), RIB-failure |
| ISP ไม่เห็น prefix ของเรา | ไม่มีใน routing table (ต้องมี Null0), prefix-list ขาออกผิด, ISP ยังไม่ได้อัปเดต filter/IRR/RPKI ROA |

---

## 9. ความปลอดภัย BGP (เบื้องต้น — ละเอียดใน Level 49)
- **กรอง prefix ทั้งขาเข้าและขาออก** เสมอ
- **max-prefix** ป้องกัน peer ส่ง route มาเกินจนอุปกรณ์ล่ม
- **TCP MD5/TCP-AO** password, **GTSM (TTL security)**
- **RPKI/ROA** ป้องกันการ hijack prefix · มาตรฐาน **MANRS**
- เหตุการณ์ BGP ระดับโลกที่ควรศึกษา: YouTube hijack (Pakistan, 2008), Facebook outage (2021 — ถอน route ของ DNS ตัวเอง)

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| State "Active" = ทำงานอยู่ | Active = TCP ยังไม่สำเร็จ กำลังลองใหม่ |
| BGP หา neighbor เอง | ต้องกำหนด neighbor เอง |
| `network` ใน BGP ประกาศ prefix ได้เสมอ | ต้องมี prefix นั้นตรงใน routing table |
| iBGP ส่งต่อ route ให้ทุก peer | route ที่ได้จาก iBGP ไม่ส่งต่อให้ iBGP อื่น (ต้อง full mesh หรือ RR) |
| องค์กรเล็กไม่ต้องกรอง route ขาออก | ไม่กรองอาจกลายเป็นทางผ่านของอินเทอร์เน็ต (route leak) |

---

## 11. Cheat Sheet

```
BGP = path vector ระหว่าง AS · TCP 179 · กำหนด neighbor เอง · policy-based
AD: eBGP 20 · iBGP 200 · keepalive 60 / hold 180
ASN private: 64512-65534 · 4200000000-4294967294 · public ขอจาก APNIC
eBGP คนละ AS (TTL 1, เปลี่ยน next-hop, เพิ่ม AS-PATH) · iBGP AS เดียวกัน (ไม่ส่งต่อ iBGP→iBGP)
iBGP: full mesh หรือ Route Reflector · update-source Loopback0 · next-hop-self · ต้องมี IGP รองรับ
States: Idle → Connect → Active (TCP fail!) → OpenSent → OpenConfirm → Established
network X mask Y ต้องมีใน routing table (ip route X Y Null0)
กรองขาออกเสมอ (prefix-list) · maximum-prefix · password
show ip bgp summary / show ip bgp / neighbors X advertised-routes / routes · clear ip bgp X soft
```

---

## 12. แบบทดสอบ 10 ข้อ

1. BGP เป็น routing protocol ประเภทใด ใช้ transport อะไร
2. AD ของ eBGP และ iBGP คือเท่าไร
3. ช่วง Private ASN แบบ 2-byte คืออะไร
4. eBGP ต่างจาก iBGP อย่างไร (3 ข้อ)
5. ทำไม iBGP ต้อง full mesh และทางแก้คืออะไร
6. Neighbor ค้างที่ Active หมายความว่าอะไร ตรวจอะไร
7. คำสั่ง `network 198.51.100.0 mask 255.255.255.0` ไม่ประกาศ prefix ออกไป เพราะอะไร แก้อย่างไร
8. next-hop-self แก้ปัญหาอะไร
9. Route leak คืออะไร ป้องกันอย่างไร
10. อ่าน AS-PATH `64500 15169 i` อย่างไร

<details><summary><b>เฉลย</b></summary>

1. Path vector; TCP port 179
2. eBGP 20, iBGP 200
3. 64512–65534
4. eBGP อยู่คนละ AS / iBGP AS เดียวกัน; eBGP TTL 1 / iBGP 255; eBGP เปลี่ยน next-hop และเพิ่ม AS-PATH / iBGP ไม่เปลี่ยน; route จาก iBGP ไม่ถูกส่งต่อให้ iBGP peer อื่น
5. กฎ split horizon ของ iBGP ไม่ส่งต่อ route ที่ได้จาก iBGP — แก้ด้วย Route Reflector (หรือ confederation)
6. TCP session ยังสร้างไม่สำเร็จ — ตรวจ IP/AS ของ neighbor, route ไปหา neighbor, ACL/firewall TCP 179, update-source/multihop, password
7. Prefix/mask นั้นไม่มีอยู่ใน routing table ตรงทุกตัว — สร้าง `ip route 198.51.100.0 255.255.255.0 Null0` (หรือให้มีจาก IGP)
8. Router ภายในที่ได้ route ผ่าน iBGP ไม่รู้จัก next-hop ภายนอก (IP ของ ISP) — ตั้ง next-hop เป็นตัว router ขอบเอง
9. การประกาศ route ที่ได้จาก ISP หนึ่งไปให้ ISP อื่น ทำให้องค์กรกลายเป็นทางผ่าน — ป้องกันด้วย prefix-list ขาออกให้ประกาศเฉพาะ prefix ของตัวเอง
10. Route ผ่าน AS 64500 (เพื่อนบ้านของเรา) และมีต้นทางที่ AS 15169; `i` = origin IGP
</details>

---

➡️ ต่อไป: **Level 49 — BGP Path Selection & Policy**
