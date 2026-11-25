# บทเรียน Level 97 — MPLS & Segment Routing (Service Provider) (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจเครือข่ายผู้ให้บริการ (core/aggregation/access, PE/P/CE) · MPLS label และ push/swap/pop, PHP · LDP · IS-IS ในฐานะ IGP ของ SP · L3VPN (VRF, RD, RT, MP-BGP VPNv4) แบบลงมือ · L2VPN (VPWS, VPLS, EVPN) · Traffic Engineering จาก RSVP-TE สู่ Segment Routing (SR-MPLS, SRv6) · TI-LFA · ตั้ง lab ด้วย IOS-XR/SR Linux/FRR

---

## 1. เครือข่ายผู้ให้บริการ (SP) หน้าตาอย่างไร

```
 [ลูกค้า A สาขา 1]─CE─┐                                         ┌─CE─[ลูกค้า A สาขา 2]
                     PE1 ═══ P ═══ P ═══ P ═══ PE2
 [ลูกค้า B สาขา 1]─CE─┘      (MPLS core: รู้แค่ label/loopback)  └─CE─[ลูกค้า B สาขา 2]
```

| บทบาท | หน้าที่ |
|---|---|
| **CE** (Customer Edge) | router ของลูกค้า — ไม่รู้เรื่อง MPLS |
| **PE** (Provider Edge) | ขอบของผู้ให้บริการ — มี **VRF** ต่อลูกค้า, ใส่/ถอด label, คุย MP-BGP |
| **P** (Provider) | core router — **swap label อย่างเดียว ไม่รู้ route ของลูกค้า** ⭐ |
| Route Reflector | กระจาย VPN route ระหว่าง PE (ไม่ต้อง full mesh iBGP) |

**ชั้นของ SP:** Access (สายไปลูกค้า: ไฟเบอร์/GPON/Metro-E) → Aggregation → Core (ความจุสูงมาก) → Peering/Transit (อินเทอร์เน็ต — Level 48/49)

**ทำไม enterprise engineer ควรรู้:** ใช้บริการ MPLS VPN/Metro-E/EVPN ของ ISP, DC ขนาดใหญ่ใช้ EVPN/SR, งานที่ ISP/telco/integrator (เช่น งาน SI ใน SI-Track) ต้องใช้ตรง ๆ

---

## 2. MPLS พื้นฐาน

**MPLS (Multiprotocol Label Switching)** = ส่ง packet ตาม **label สั้น ๆ** แทนการ lookup IP ทุก hop
```
 ┌────────┬───────────────────┬──────────┐
 │ L2 hdr │ MPLS label stack  │ IP packet│
 └────────┴───────────────────┴──────────┘
 Label entry (32 บิต): Label 20 บิต | TC 3 บิต (QoS, เดิม EXP) | S 1 บิต (bottom of stack) | TTL 8 บิต
```
- Label มีความหมาย **เฉพาะ router นั้น (local significance)**
- **Label stack:** ซ้อนได้หลายชั้น (เช่น transport label + VPN label) — "Multiprotocol" เพราะขนได้ทั้ง IPv4, IPv6, Ethernet frame
- Ethertype 0x8847

### การทำงาน

| ตำแหน่ง | การกระทำ |
|---|---|
| Ingress **LER** (Label Edge Router = PE ขาเข้า) | **Push** label |
| **LSR** (Label Switch Router = P) | **Swap** label (ตาม LFIB) |
| Egress LER (PE ขาออก) | **Pop** label แล้วส่งตาม IP/VRF |

```
 PE1 --[push 100]--> P1 --[swap 100→200]--> P2 --[swap 200→300]--> PE2 --[pop]--> CE
 เส้นทางของ label จาก PE1 ถึง PE2 = LSP (Label Switched Path) — ทิศเดียว
```
### PHP — Penultimate Hop Popping
router **ก่อนสุดท้าย** ถอด label ด้านบนออกให้ (PE ปลายทางประกาศ **implicit-null, label 3**) → PE ไม่ต้อง lookup สองครั้ง (label แล้วค่อย IP)
- explicit-null (label 0) ใช้เมื่อต้องการรักษา TC/QoS bit ถึง PE

### ประโยชน์ของ MPLS ในปัจจุบัน
ความเร็วของ lookup ไม่ใช่เหตุผลหลักแล้ว (ASIC เร็วทั้งคู่) แต่เป็น:
1. **VPN** (L3VPN/L2VPN) — แยกลูกค้าหลายรายบน core เดียว (IP ซ้ำกันได้)
2. **Traffic Engineering** — บังคับเส้นทางได้ (ไม่ต้องตาม IGP shortest path)
3. **BGP-free core** — P router ไม่ต้องมี full Internet table
4. Fast reroute (FRR/TI-LFA)

---

## 3. IGP ของ SP: IS-IS

SP ส่วนใหญ่ใช้ **IS-IS** เป็น underlay IGP (แทน OSPF)

| เหตุผล | อธิบาย |
|---|---|
| ทำงานบน L2 โดยตรง (ไม่ใช่ IP) | ไม่ถูกโจมตีด้วย IP spoofing ง่าย ๆ, รองรับ IPv4/IPv6 พร้อมกันใน instance เดียว |
| **TLV** ขยายง่าย | เพิ่มข้อมูลใหม่ (TE, Segment Routing) ได้สะดวก |
| scale ดีใน area ใหญ่ | ออกแบบ flat L2 ได้หลายร้อย router |

- Level 1 (ภายใน area) / Level 2 (backbone) / L1/L2 — คล้าย area ของ OSPF
- **NET address:** `49.0001.0100.0000.0001.00` (area 49.0001, system ID 0100.0000.0001)
```
router isis CORE
 net 49.0001.0100.0000.0001.00
 is-type level-2-only
 metric-style wide
 address-family ipv4 unicast
  segment-routing mpls                 ! (เมื่อใช้ SR)
!
interface GigabitEthernet0/0/0/0
 ! IOS-XR: ใต้ router isis
```

---

## 4. LDP — แจก Label แบบดั้งเดิม

**LDP (Label Distribution Protocol)** ให้ router แลก label กับ neighbor สำหรับทุก prefix ใน IGP (โดยเฉพาะ loopback ของ PE)
```
mpls ldp router-id Loopback0 force
interface GigabitEthernet0/1
 mpls ip                                ! IOS: เปิด LDP บน interface core
show mpls ldp neighbor
show mpls forwarding-table              ! LFIB: local label → outgoing label → next-hop
traceroute mpls ipv4 10.255.0.2/32      ! ตรวจ LSP
```
- **LDP-IGP sync:** ไม่ให้ IGP ใช้ลิงก์ที่ LDP ยังไม่พร้อม (ไม่เช่นนั้น traffic ที่ต้องมี label ถูกทิ้ง → blackhole)
- ปัจจุบัน **Segment Routing แทน LDP** ในเครือข่ายใหม่ (ข้อ 7)

---

## 5. MPLS L3VPN (ลงลึก — ต่อจาก Level 57)

### องค์ประกอบ

| องค์ประกอบ | หน้าที่ |
|---|---|
| **VRF** | routing table แยกต่อลูกค้าบน PE |
| **RD (Route Distinguisher)** 64 บิต | ทำให้ prefix ของลูกค้าต่างรายที่ **ซ้ำกัน** ไม่ชนกันใน BGP: RD:IPv4 = **VPNv4 prefix** (เช่น 65000:1:10.1.0.0/16 vs 65000:2:10.1.0.0/16) |
| **RT (Route Target)** extended community | ควบคุม **import/export** — route ไป VRF ไหนบ้าง (ทำ hub-and-spoke, extranet ได้) |
| **MP-BGP (VPNv4/VPNv6)** | iBGP ระหว่าง PE (ผ่าน RR) แลก VPN route + **VPN label** |
| **PE–CE routing** | static, eBGP (นิยม), OSPF, RIP — ต่อ VRF |

### Label 2 ชั้น
```
 [Transport label (ไป PE2 — จาก LDP/SR)] [VPN label (ระบุ VRF/prefix ที่ PE2 — จาก MP-BGP)] [IP ของลูกค้า]
 P router ดูแค่ transport label → ไม่รู้จัก IP ลูกค้าเลย
 PHP ที่ P ตัวสุดท้ายถอด transport → PE2 เห็น VPN label → รู้ว่าเป็น VRF ไหน
```
### Config ตัวอย่าง (Cisco IOS-XE PE)
```
vrf definition CUST-A
 rd 65000:1
 address-family ipv4
  route-target export 65000:1
  route-target import 65000:1
!
interface GigabitEthernet0/2
 description to CE-A1
 vrf forwarding CUST-A
 ip address 192.168.100.1 255.255.255.252
!
router bgp 65000
 neighbor 10.255.0.10 remote-as 65000          ! RR
 neighbor 10.255.0.10 update-source Loopback0
 address-family vpnv4
  neighbor 10.255.0.10 activate
  neighbor 10.255.0.10 send-community extended  ! ต้องส่ง RT
 address-family ipv4 vrf CUST-A
  neighbor 192.168.100.2 remote-as 65101        ! eBGP กับ CE ลูกค้า
  neighbor 192.168.100.2 activate
  neighbor 192.168.100.2 as-override            ! ลูกค้าใช้ AS เดียวกันทุกสาขา
```
```
show bgp vpnv4 unicast all summary
show bgp vpnv4 unicast vrf CUST-A
show ip route vrf CUST-A
ping vrf CUST-A 10.2.0.1
show mpls forwarding-table vrf CUST-A
```
### ปัญหาที่พบบ่อย
- ลูกค้าใช้ AS เดียวกันทุกสาขา → eBGP loop prevention ทิ้ง route → `as-override` (PE) หรือ `allowas-in` (CE)
- ลูกค้า multihomed (2 PE) + OSPF PE–CE → ต้องระวัง loop (down bit/domain tag)
- RT import/export ไม่ตรง → route ไม่ปรากฏใน VRF
- ลืม `send-community extended` → RT หาย

---

## 6. L2VPN

| บริการ | ลักษณะ | เทคโนโลยีเดิม → ใหม่ |
|---|---|---|
| **VPWS / E-Line** (point-to-point) | "สายเสมือน" L2 ระหว่าง 2 จุด | AToM/pseudowire (LDP) → **EVPN-VPWS** |
| **VPLS / E-LAN** (multipoint) | "switch เสมือน" หลายจุดอยู่ใน broadcast domain เดียว | VPLS (LDP/BGP, flood-and-learn, full mesh PW) → **EVPN (MPLS หรือ VXLAN)** |
| E-Tree | hub-and-spoke L2 | EVPN-ETREE |

**ทำไม EVPN มาแทน VPLS:** ใช้ BGP เรียนรู้ MAC (control plane) แทน flood-and-learn, **active-active multihoming** (ESI) ซึ่ง VPLS ทำได้ยาก, MAC mobility, ARP suppression, รวม L2+L3 ใน protocol เดียว (เหมือนใน DC — Level 74)

---

## 7. Traffic Engineering: RSVP-TE → Segment Routing

### ปัญหา
IGP เลือก **shortest path เส้นเดียว** → ลิงก์ที่สั้นแน่น ลิงก์สำรองว่าง; บางบริการต้องการ path ที่ latency ต่ำ หรือหลีกเลี่ยงบางลิงก์ (disjoint path)

### RSVP-TE (ดั้งเดิม)
สร้าง **TE tunnel** ที่ระบุ path/bandwidth จองไว้ → **ทุก router ตลอดเส้นทางต้องเก็บ state ของทุก tunnel** → เมื่อ tunnel มีหลายหมื่น ดูแลยากมาก, scale ไม่ดี

### Segment Routing (SR) ⭐
**Source routing:** router ต้นทางใส่ "รายการคำสั่ง" (segment list) ลงใน packet → router กลางทางทำตามโดย **ไม่ต้องเก็บ state ต่อ flow/tunnel**

| ประเภท Segment | ความหมาย |
|---|---|
| **Prefix-SID** (Node-SID) | "ไปหา router X ด้วย shortest path" — ค่า **global** (index + SRGB เช่น 16000 + 1 = 16001) |
| **Adjacency-SID** | "ออกทางลิงก์นี้" — ค่า local |
| Binding-SID, Anycast-SID | อ้างอิง policy/กลุ่ม |

```
 ต้องการไป PE2 แต่บังคับให้ผ่าน P3 (หลีกลิงก์ที่แน่น):
 segment list = [16003 (ไป P3), 16002 (ไป PE2)]
 ไม่มี router ใดต้องเก็บ state ของ path นี้ — อยู่ใน header ของ packet
```
- **SR-MPLS:** segment = MPLS label, label แจกโดย **IGP (IS-IS/OSPF extensions)** → **ไม่ต้องใช้ LDP/RSVP** (protocol น้อยลง)
- **SRv6:** segment = **IPv6 address** (SID) ใน Segment Routing Header — ไม่ต้องมี MPLS เลย, รองรับ "network programming" (SID แทน function เช่น End.DT4 = decap แล้ว lookup VRF) → ทำ L3VPN/EVPN บน IPv6 ล้วน
- **SR-TE Policy:** คำนวณ path ตามเงื่อนไข (latency ต่ำสุด, หลีกลิงก์, disjoint) โดย headend หรือ **PCE** (controller — SDN, Level 88) + **Flex-Algo** (IGP คำนวณหลาย topology ตาม metric ต่างกัน เช่น latency)
```
! IOS-XR: เปิด SR-MPLS ใน IS-IS + Prefix-SID
router isis CORE
 address-family ipv4 unicast
  segment-routing mpls
 interface Loopback0
  address-family ipv4 unicast
   prefix-sid index 1                    ! → label 16001 (SRGB เริ่ม 16000)
!
show isis segment-routing label table
show mpls forwarding
```

### TI-LFA (Topology-Independent Loop-Free Alternate)
คำนวณ **เส้นทางสำรองล่วงหน้า** สำหรับทุก prefix (ใช้ segment list บังคับ path สำรองที่ไม่ loop ได้ในทุก topology) → ลิงก์/โหนดเสีย สลับได้ **< 50 ms** โดยไม่รอ IGP converge
```
router isis CORE
 interface GigabitEthernet0/0/0/0
  address-family ipv4 unicast
   fast-reroute per-prefix
   fast-reroute per-prefix ti-lfa
```

### เปรียบเทียบ

| | LDP + RSVP-TE | Segment Routing |
|---|---|---|
| Protocols | IGP + LDP + RSVP | **IGP อย่างเดียว** (+ BGP สำหรับ VPN) |
| State ใน core | ต่อ tunnel | **ไม่มี** (อยู่ใน packet) |
| Fast reroute | RSVP FRR (ต้องตั้ง bypass) / LFA (ครอบคลุมไม่หมด) | **TI-LFA ครอบคลุม 100%** |
| SDN/controller | ยาก | ออกแบบมาให้ทำงานกับ PCE/controller |

---

## 8. QoS ใน MPLS

- **TC bits (3 บิต)** ใน label → 8 class
- โหมด DiffServ tunneling: **Uniform** (QoS ของลูกค้ากับ SP ใช้ค่าเดียวกัน), **Pipe/Short-pipe** (SP ใช้ QoS ของตัวเองใน core แต่รักษา DSCP ของลูกค้าไว้)
- SP ขายบริการเป็น class (เช่น Real-time/Business/Best-effort) → ลูกค้าต้อง **mark DSCP ให้ตรงกับที่ SP กำหนด** (Level 54/57)

---

## 9. Lab แนะนำ

| แพลตฟอร์ม | หมายเหตุ |
|---|---|
| **Cisco XRd** (container ของ IOS-XR) / IOS-XRv 9000 | ดีที่สุดสำหรับ SR/TI-LFA/EVPN แบบ SP (ต้องมีสิทธิ์ใช้ image) |
| **Nokia SR Linux** (ฟรี) | EVPN, MPLS/SR ใน DC และกำลังเพิ่มฟีเจอร์ SP |
| Juniper vMX/cRPD/vJunos | MPLS/L3VPN/SR ครบ |
| **FRRouting** (ฟรี) | IS-IS SR, LDP, L3VPN, BGP บน Linux — ทดลองแนวคิดได้ดี |
| containerlab | สร้าง topology หลาย router จาก YAML (Level 84) |

**ลำดับ lab:** IS-IS core 4 router → LDP + ping PE loopback ด้วย label → L3VPN 2 ลูกค้า IP ซ้ำ → แทน LDP ด้วย SR-MPLS → TI-LFA (ตัดลิงก์ วัด loss) → EVPN-VPWS → SR-TE policy

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| MPLS ใช้เพราะเร็วกว่า IP routing | ปัจจุบันใช้เพื่อ VPN, TE, BGP-free core, FRR |
| RD กับ RT คือสิ่งเดียวกัน | RD ทำให้ prefix ไม่ซ้ำ, RT ควบคุม import/export |
| P router ต้องรู้ route ของลูกค้า | รู้แค่ loopback ของ PE/label |
| SR ต้องเปลี่ยนฮาร์ดแวร์ทั้งหมด | SR-MPLS ใช้ data plane MPLS เดิมได้ — เปลี่ยน control plane |
| VPLS ดีพอ ไม่ต้องใช้ EVPN | EVPN ดีกว่าเรื่อง multihoming, control plane, scale |

---

## 11. Cheat Sheet

```
CE (ลูกค้า) · PE (VRF, push/pop, MP-BGP) · P (swap only, ไม่รู้ route ลูกค้า) · RR
Label 32 บิต: label 20 · TC 3 · S 1 · TTL 8 · local significance · stack · LSP ทิศเดียว
Push (ingress) · Swap (P) · Pop (egress) · PHP: implicit-null (3) / explicit-null (0)
IS-IS: L1/L2, NET 49.xxxx..., TLV, IPv4+IPv6 · LDP: mpls ip, LDP-IGP sync
L3VPN: VRF · RD (unique prefix) · RT (import/export) · MP-BGP VPNv4 + send-community extended
       label 2 ชั้น (transport + VPN) · as-override/allowas-in
L2VPN: VPWS (E-Line) · VPLS (E-LAN) → EVPN (BGP MAC, multihoming)
TE: RSVP-TE (state ต่อ tunnel) → SR (source routing, ไม่มี state) · Prefix-SID (global) · Adj-SID (local)
SR-MPLS (label จาก IGP, ไม่ต้อง LDP) · SRv6 (SID = IPv6) · SR-TE policy · PCE · Flex-Algo
TI-LFA < 50 ms · QoS: TC bits, uniform/pipe
```

---

## 12. แบบทดสอบ 10 ข้อ

1. PE, P, CE ทำหน้าที่อะไร
2. โครงสร้างของ MPLS label มีกี่ส่วน อะไรบ้าง
3. PHP คืออะไร มีประโยชน์อย่างไร
4. ทำไม SP นิยม IS-IS
5. RD กับ RT ต่างกันอย่างไร
6. ทำไม P router ไม่ต้องรู้ route ของลูกค้า (อธิบายด้วย label 2 ชั้น)
7. ลูกค้าใช้ AS 65101 ทุกสาขา route ไม่ข้ามสาขา เพราะอะไร แก้อย่างไร
8. Segment Routing ต่างจาก RSVP-TE อย่างไร
9. Prefix-SID กับ Adjacency-SID ต่างกันอย่างไร
10. TI-LFA ให้ประโยชน์อะไร

<details><summary><b>เฉลย</b></summary>

1. CE = router ของลูกค้า (ไม่รู้ MPLS); PE = ขอบ SP มี VRF ใส่/ถอด label คุย MP-BGP; P = core ที่ swap label อย่างเดียว
2. 4 ส่วน: label 20 บิต, TC 3 บิต, S (bottom of stack) 1 บิต, TTL 8 บิต
3. Router ก่อนสุดท้ายถอด label บนสุดออก (PE ประกาศ implicit-null) ทำให้ PE ไม่ต้อง lookup สองครั้ง
4. ทำงานบน L2 ไม่ใช่ IP, ใช้ TLV ขยายง่าย (TE/SR), รองรับ IPv4/IPv6 ใน instance เดียว, scale ดี
5. RD ทำให้ prefix ที่ซ้ำกันของลูกค้าต่างรายไม่ชนกันใน BGP (VPNv4); RT ควบคุมว่า route ถูก import/export ไปยัง VRF ใด
6. Packet มี transport label (ไป PE ปลายทาง) อยู่บน VPN label — P ดูแค่ transport label จึงต้องรู้แค่เส้นทางไป loopback ของ PE
7. eBGP loop prevention: CE เห็น AS ของตัวเองใน AS path จึงทิ้ง — ใช้ `as-override` บน PE หรือ `allowas-in` บน CE
8. SR ใส่ segment list ใน packet (source routing) ไม่ต้องเก็บ state ต่อ tunnel ใน core และไม่ต้องใช้ LDP/RSVP; RSVP-TE ต้องเก็บ state ทุก tunnel ทุก router
9. Prefix-SID = ไปยัง router/prefix ด้วย shortest path ค่า global; Adjacency-SID = ออกทางลิงก์เฉพาะ ค่า local
10. มีเส้นทางสำรองที่คำนวณไว้ล่วงหน้าครอบคลุมทุก topology สลับได้ภายใน < 50 ms โดยไม่รอ IGP converge
</details>

---

➡️ ต่อไป: **Level 98 — Networking for AI / HPC Data Centers**
