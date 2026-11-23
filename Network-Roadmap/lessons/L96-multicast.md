# บทเรียน Level 96 — Multicast (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจ unicast/broadcast/multicast และเมื่อไรต้องใช้ multicast · ช่วงที่อยู่ IPv4/IPv6 และการ map เป็น MAC · IGMP v2/v3 และ MLD · IGMP snooping/querier · PIM Dense vs Sparse vs SSM · RP, shared tree vs shortest-path tree · RPF check · ตั้งค่า PIM-SM/SSM บน Cisco · multicast ใน use case จริง (IPTV, CCTV, ตลาดหุ้น, imaging) · troubleshooting

---

## 1. ทำไมต้องมี Multicast

ส่งข้อมูลเดียวกันไปหาผู้รับหลายราย:
```
 Unicast   : ส่ง 1 ชุดต่อผู้รับ 1 คน → 100 คนดู IPTV 8 Mbps = 800 Mbps จาก server
 Broadcast : ส่งถึงทุกเครื่องใน subnet (แม้ไม่ต้องการ) และไม่ข้าม router
 Multicast : ส่ง 1 ชุด → เครือข่าย "ทำสำเนา" ที่จุดแยกทาง เฉพาะไปยังผู้ที่สมัครรับ → 8 Mbps ต่อลิงก์ไม่ว่าผู้ชมกี่คน
```
| Use case | เหตุผล |
|---|---|
| **IPTV/ทีวีในโรงแรม/โรงพยาบาล** | หลายห้องดูช่องเดียวกัน |
| **ตลาดหุ้น/financial market data** | ราคาส่งถึงผู้รับทุกรายพร้อมกัน latency ต่ำ |
| **กล้อง CCTV/VMS** บางระบบ | หลาย client ดูกล้องเดียวกัน |
| **OS imaging** (WDS/SCCM multicast, Ghost) | ลง Windows 100 เครื่องพร้อมกัน |
| **Routing protocols** | OSPF 224.0.0.5/6, EIGRP 224.0.0.10, PIM 224.0.0.13, VRRP 224.0.0.18 |
| Service discovery | mDNS 224.0.0.251 (AirPlay/Chromecast/printer), SSDP 239.255.255.250 |
| VXLAN underlay (flood-and-learn), video conferencing ภายใน, ระบบประกาศเสียง (paging) | |

**ข้อจำกัด:** ใช้บน **อินเทอร์เน็ตสาธารณะแทบไม่ได้** (ISP ส่วนใหญ่ไม่ route multicast) → ใช้ในเครือข่ายองค์กร/ผู้ให้บริการ; เป็น **UDP** (ไม่มี retransmission — แอปต้องจัดการ loss เอง เช่น FEC)

---

## 2. Multicast Addressing

### IPv4: 224.0.0.0/4 (224.0.0.0 – 239.255.255.255)
| ช่วง | ความหมาย |
|---|---|
| **224.0.0.0/24** | **Link-local** (TTL=1, ไม่ข้าม router) — OSPF, VRRP, PIM, mDNS |
| 224.0.1.0 – 238.255.255.255 | Globally scoped (ใช้บนอินเทอร์เน็ต/ระหว่างองค์กร — ต้องจัดสรร) |
| **232.0.0.0/8** | **SSM (Source-Specific Multicast)** |
| 233.0.0.0/8 | GLOP (ตาม AS number) |
| **239.0.0.0/8** | **Administratively scoped** — ใช้ภายในองค์กร (เหมือน "private" ของ multicast) ⭐ |
### IPv6: ff00::/8
`ff02::1` (all nodes — แทน broadcast), `ff02::2` (all routers), `ff02::5`/`::6` (OSPFv3), `ff02::1:ff00:0/104` (solicited-node — ใช้ใน NDP), `ff05::/16` site-local, `ff3x::/32` SSM

### Multicast IP → MAC
```
 IPv4 multicast MAC = 01:00:5E + 0 + 23 บิตล่างของ IP
 239.1.1.1 → 01:00:5E:01:01:01
 224.1.1.1 → 01:00:5E:01:01:01   ← MAC เดียวกัน!
```
IP multicast มี 28 บิตที่ใช้ระบุกลุ่ม แต่ map ได้ 23 บิต → **5 บิตหายไป → 2⁵ = 32 กลุ่ม IP ใช้ MAC เดียวกัน** (overlap) → host อาจรับ frame ที่ไม่ต้องการแล้วทิ้งที่ IP layer · หลีกเลี่ยงการเลือกกลุ่มที่ชนกับ 224.0.0.x (x.0.0.x / x.128.0.x) เพราะ switch อาจ flood
IPv6: `33:33` + 32 บิตล่าง

---

## 3. IGMP — Host บอก Router ว่าต้องการกลุ่มไหน

**IGMP (Internet Group Management Protocol)** ระหว่าง **host ↔ router** (first-hop) บน subnet เดียวกัน (IPv6 ใช้ **MLD**)
| Version | ความสามารถ |
|---|---|
| IGMPv1 | Join (Membership Report) + Query — ไม่มี Leave (รอ timeout) |
| **IGMPv2** | + **Leave Group** (ออกเร็ว), group-specific query, เลือก querier |
| **IGMPv3** | + **Source filtering** (INCLUDE/EXCLUDE source) → ใช้กับ **SSM** ⭐ |
| MLDv1 / MLDv2 | IPv6 เทียบเท่า IGMPv2 / v3 |
```
 1. Host เปิดช่อง TV → ส่ง IGMP Membership Report "ขอ 239.1.1.10"
 2. Router บันทึกว่ามีผู้รับบน interface นี้ → ขอ traffic จาก upstream (PIM)
 3. Router ส่ง General Query เป็นระยะ (ทุก 60–125 วินาที) "ยังมีใครต้องการอยู่ไหม"
 4. Host เปลี่ยนช่อง → ส่ง Leave → router ถาม group-specific query → ไม่มีใครตอบ → หยุดส่ง
```

---

## 4. IGMP Snooping — ทำให้ Switch ฉลาด

ปกติ switch ปฏิบัติต่อ multicast เหมือน **broadcast (flood ทุกพอร์ตใน VLAN)** → IPTV 20 ช่อง × 8 Mbps = 160 Mbps ไปถึงทุกเครื่อง (รวมเครื่องพิมพ์!)
**IGMP snooping:** switch "แอบฟัง" IGMP report/leave → ส่ง multicast **เฉพาะพอร์ตที่มีผู้สมัคร** + พอร์ตที่ไปหา router (mrouter port)
```
ip igmp snooping                       ! ปกติเปิดเป็นค่าเริ่มต้นบน Catalyst
ip igmp snooping vlan 50 immediate-leave   ! (v2) ตัดทันทีเมื่อ Leave — เหมาะกับพอร์ตที่มี host เดียว (IPTV set-top box)
show ip igmp snooping groups vlan 50
show ip igmp snooping mrouter
```
### IGMP Querier ⭐ (ปัญหาที่พบบ่อยมาก)
snooping ต้องการ **Query** เป็นระยะเพื่อรักษา membership — ถ้า VLAN **ไม่มี router ที่ทำ PIM/IGMP** (multicast ภายใน L2 อย่างเดียว เช่น imaging, CCTV ใน VLAN เดียว) → ไม่มี querier → entry หมดอายุ → **stream หยุดหลัง ~3–5 นาที** หรือ flood
```
ip igmp snooping querier               ! ให้ switch ทำหน้าที่ querier เอง (ใน VLAN ที่ไม่มี router)
ip igmp snooping querier address 10.50.0.2
```
อาการคลาสสิก: "ภาพกล้อง/ทีวีหยุดทุก ๆ ไม่กี่นาทีแล้วกลับมา" → ตรวจ querier

---

## 5. Multicast Routing — PIM

**PIM (Protocol Independent Multicast)** = router คุยกันเพื่อสร้าง **distribution tree** จาก source ไปยังผู้รับ — "protocol independent" เพราะใช้ **unicast routing table (OSPF/BGP/static) ที่มีอยู่** ในการตรวจ RPF

### RPF Check (Reverse Path Forwarding) ⭐ หัวใจของ multicast routing
```
 Router รับ multicast packet จาก source S บน interface X
 ตรวจ unicast routing table: "เส้นทางกลับไปหา S ออกทาง interface ไหน?"
   ถ้าเป็น X → ผ่าน RPF → ส่งต่อ (ไปยัง interface ที่มีผู้รับ)
   ถ้าไม่ใช่ X → RPF fail → ทิ้ง (ป้องกัน loop และ duplicate)
```
ปัญหาที่พบบ่อย: unicast routing ไม่สมมาตรกับ path ของ multicast, PIM ไม่ได้เปิดบน interface ที่ unicast ใช้กลับหา source → **RPF failure** → แก้ด้วยเปิด PIM ให้ครบ หรือ `ip mroute` (static mroute) / MBGP

### ประเภทของ Tree
| Tree | ลักษณะ | สัญลักษณ์ |
|---|---|---|
| **Source tree / SPT (Shortest Path Tree)** | จาก source ตรงไปหาผู้รับ (path สั้นสุด) | **(S, G)** — source เจาะจง, group |
| **Shared tree / RPT (RP Tree)** | ทุก source ส่งผ่านจุดกลาง **RP (Rendezvous Point)** | **(\*, G)** — source ใดก็ได้ |

### PIM Modes
| Mode | หลักการ | เหมาะกับ |
|---|---|---|
| **Dense Mode (PIM-DM)** | **flood ทั่วเครือข่ายก่อน แล้ว prune** ส่วนที่ไม่มีผู้รับ (ทุก 3 นาที flood ใหม่) | ผู้รับหนาแน่นทุกที่ — **ไม่แนะนำ** ในปัจจุบัน (สิ้นเปลือง) |
| **Sparse Mode (PIM-SM)** ⭐ | **ไม่ส่งจนกว่าจะมีคนขอ (explicit join)** — ผู้รับ join ไปที่ **RP** (shared tree) แล้ว last-hop router อาจ **สลับไป SPT** ตรงไปหา source | ใช้ทั่วไปในองค์กร |
| **SSM (Source-Specific Multicast)** ⭐ | ผู้รับระบุ **source + group** เอง (IGMPv3) → สร้าง SPT ตรงทันที **ไม่ต้องมี RP** | IPTV/market data ที่รู้ source แน่นอน — ง่ายและปลอดภัยที่สุด |
| Bidir-PIM | shared tree สองทิศ | many-to-many (ผู้ส่งจำนวนมาก) |

### PIM-SM ทำงานอย่างไร (ย่อ)
```
 1. ผู้รับส่ง IGMP join (*,G) → last-hop router (DR) ส่ง PIM Join ไปทาง RP → สร้าง shared tree
 2. Source เริ่มส่ง → first-hop router (DR ฝั่ง source) ส่ง **PIM Register** (unicast ห่อ packet) ไปหา RP
 3. RP ส่ง Join ไปหา source → สร้าง (S,G) tree จาก source ถึง RP → ส่ง Register-Stop
 4. Traffic ไหล source → RP → shared tree → ผู้รับ
 5. Last-hop router เห็น source แล้ว → join (S,G) ตรงไปหา source (SPT switchover) → prune ออกจาก RPT
```
### การกำหนด RP
| วิธี | หมายเหตุ |
|---|---|
| **Static RP** (`ip pim rp-address`) | ง่าย ต้องตั้งทุก router |
| **Auto-RP** (Cisco) | RP announce/mapping agent (224.0.1.39/40) |
| **BSR** (Bootstrap Router — มาตรฐาน) | กระจาย RP อัตโนมัติ |
| **Anycast RP** (+ MSDP หรือ PIM anycast RP) | RP หลายตัวใช้ IP เดียวกัน → redundancy + load sharing ⭐ |

---

## 6. ตั้งค่าตัวอย่าง (Cisco IOS)

### PIM-SM + Static RP
```
ip multicast-routing                          ! (บางแพลตฟอร์ม: ip multicast-routing distributed)
!
interface Loopback0
 ip address 10.255.0.1 255.255.255.255
 ip pim sparse-mode                           ! RP ต้องเปิด PIM บน loopback ที่ใช้เป็น RP address
!
interface GigabitEthernet0/0                  ! ทุก interface ใน path multicast (รวม uplink)
 ip pim sparse-mode
interface Vlan50                              ! ฝั่งผู้รับ (IPTV clients)
 ip pim sparse-mode                           ! เปิด IGMP โดยอัตโนมัติ
 ip igmp version 3
!
ip pim rp-address 10.255.0.1                  ! ทุก router ชี้ไปที่ RP เดียวกัน
```
### PIM-SSM
```
ip pim ssm default                            ! 232.0.0.0/8 เป็นช่วง SSM
interface Vlan50
 ip pim sparse-mode
 ip igmp version 3                            ! ผู้รับต้องใช้ IGMPv3 (หรือใช้ SSM mapping สำหรับ client ที่เป็น v2)
```
### คำสั่งตรวจสอบ
```
show ip pim neighbor                          ! PIM neighbor ครบไหม
show ip pim rp mapping                        ! ทุก router รู้ RP เดียวกันไหม
show ip igmp groups                           ! มีผู้รับกลุ่มไหนบน interface ไหน
show ip mroute 239.1.1.10                     ! (*,G) และ (S,G): incoming interface, RPF nbr, outgoing interface list (OIL)
show ip mroute count                          ! packets/ที่ส่งจริง
show ip rpf 10.1.1.100                        ! RPF ไปหา source ผ่าน interface ไหน
mtrace 10.1.1.100 10.50.0.25 239.1.1.10       ! trace path ของ multicast
```
อ่าน `show ip mroute`:
```
(10.1.1.100, 239.1.1.10), 00:05:12/00:03:20, flags: sT
  Incoming interface: GigabitEthernet0/0, RPF nbr 10.0.12.1        ← ต้องตรงกับทางกลับหา source
  Outgoing interface list:
    Vlan50, Forward/Sparse, 00:05:12/00:02:40                       ← มีผู้รับ → ส่งออก
```

---

## 7. Multicast บน Layer 2 และ Wireless

- **mDNS/Bonjour (AirPlay, Chromecast, printer)** เป็น link-local → ไม่ข้าม VLAN → องค์กรที่แยก VLAN ผู้ใช้กับอุปกรณ์ใช้ **mDNS gateway/service discovery gateway** บน controller/switch (Cisco Service Discovery Gateway, Aruba AirGroup) — อย่า "ขยาย VLAN" เพื่อแก้
- **Wi-Fi:** multicast ส่งที่ **data rate ต่ำสุด** (basic rate) และไม่มี ACK → กิน airtime มาก, ภาพแตก → ใช้ **multicast-to-unicast conversion** (ทุกผู้ผลิตรายใหญ่มี) และกรอง multicast ที่ไม่จำเป็น
- **VXLAN/EVPN:** BUM ใช้ ingress replication (ไม่ต้องมี multicast underlay) หรือ multicast underlay (PIM) สำหรับ fabric ใหญ่ (Level 74)

---

## 8. ออกแบบ IPTV โรงแรม 300 ห้อง (ตัวอย่างย่อ)

```
 [Headend: encoder 60 ช่อง, 239.10.0.1-60 (หรือ SSM 232.10.0.x), ~6 Mbps/ช่อง HD]
        │ 10G
   [Core L3: PIM-SM/SSM, RP = core loopback (anycast ถ้ามี 2 core)]
        │ 10G (multicast สูงสุด 60 × 6 = 360 Mbps ต่อ uplink ถ้าทุกช่องมีคนดู)
   [Access ต่อชั้น: VLAN IPTV, IGMP snooping + immediate-leave (1 STB ต่อพอร์ต)]
        │
   [Set-top box แต่ละห้อง: IGMPv3]
 - QoS: IPTV = AF41/CS3 แยกจาก guest Wi-Fi
 - แยก VLAN IPTV จาก guest/corporate, ACL ให้รับเฉพาะ source headend (ป้องกัน multicast ปลอม)
 - Monitoring: จำนวน (S,G), packet loss ต่อช่อง (probe), IGMP join latency (เปลี่ยนช่องเร็วไหม)
```

---

## 9. Security ของ Multicast

- **กรอง source**: อนุญาตเฉพาะ source ที่ถูกต้อง (`ip pim accept-register list`, ACL บน interface ฝั่ง source) — ป้องกัน host ส่ง stream ปลอมทับ
- **จำกัดกลุ่มที่ join ได้**: `ip igmp access-group`
- **PIM neighbor filter**: `ip pim neighbor-filter` (ไม่ให้อุปกรณ์แปลกตั้งตัวเป็น PIM router)
- **Boundary**: `ip multicast boundary` ที่ขอบ site (กัน 239.x หลุดออกนอก)
- **Rate limit** multicast/broadcast บน access (storm-control — Level 63)
- SSM ปลอดภัยกว่าโดยธรรมชาติ (ผู้รับกำหนด source เอง)

---

## 10. Troubleshooting Multicast — ไล่จากผู้รับขึ้นไปหา source

```
 1. Receiver: แอปส่ง IGMP join ไหม (tcpdump igmp บน client) — firewall บนเครื่องบล็อก?
 2. Switch: IGMP snooping เห็น group ไหม, มี querier ไหม, mrouter port ถูกต้องไหม
 3. Last-hop router: show ip igmp groups → มี (*,G)/(S,G) ใน mroute ไหม
 4. ทุก hop: PIM neighbor ครบ, RP mapping ตรงกัน, RPF ชี้ไปถูก interface (show ip rpf <source>)
 5. RP: ได้ Register จาก source ไหม, มี (S,G)
 6. First-hop router: เห็น traffic จาก source ไหม (show ip mroute count), TTL ของ source พอไหม (บางแอปตั้ง TTL=1!)
 7. Data plane: ดู packet counters เพิ่มขึ้นจริง, MTU
```
| อาการ | สาเหตุที่พบบ่อย |
|---|---|
| ภาพหยุดทุก 3–5 นาที | ไม่มี IGMP querier ใน VLAN |
| ทั้ง VLAN ช้าเมื่อเปิด IPTV | ไม่มี IGMP snooping (flood) |
| ข้าม router ไม่ได้ แต่ใน VLAN เดียวกันได้ | ไม่ได้เปิด multicast-routing/PIM, **TTL=1 ที่ source**, RPF fail, RP ไม่ตรงกัน |
| (S,G) มีแต่ OIL ว่าง | ไม่มีผู้รับ join หรือ prune |
| ภาพแตกเฉพาะ Wi-Fi | multicast rate ต่ำ — เปิด multicast-to-unicast |
| เปลี่ยนช่องช้า | ไม่ได้เปิด immediate-leave/fast-leave, IGMP version |

---

## 11. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| Multicast = broadcast | multicast ส่งเฉพาะผู้ที่สมัคร (เมื่อมี IGMP snooping/PIM) |
| switch จัดการ multicast อัตโนมัติ | ต้องมี IGMP snooping และ querier |
| PIM เป็น routing protocol ที่หา route เอง | ใช้ unicast routing ที่มีอยู่ทำ RPF |
| ใช้ PIM dense mode ง่ายดี | flood/prune สิ้นเปลือง — ใช้ sparse/SSM |
| ส่ง multicast ผ่านอินเทอร์เน็ตไปสาขาได้ | ISP ส่วนใหญ่ไม่ route multicast — ใช้ GRE/overlay ที่รองรับ หรือ unicast |

---

## 12. Cheat Sheet

```
224.0.0.0/4 · 224.0.0.0/24 link-local · 232/8 SSM · 239/8 admin-scoped (ภายใน) · IPv6 ff00::/8
MAC = 01:00:5E + 23 บิตล่าง → 32 กลุ่มชน MAC เดียว · IPv6 33:33
IGMP v2 (leave) · v3 (source filter → SSM) · MLD (IPv6)
Snooping (ส่งเฉพาะพอร์ตที่ join) + Querier (ถ้าไม่มี router) · immediate-leave
PIM ใช้ unicast table → RPF check (เข้าทางเดียวกับทางกลับหา source)
(*,G) shared tree ผ่าน RP · (S,G) SPT · SM: join → RP → register → SPT switchover
Dense (flood/prune — เลี่ยง) · Sparse ⭐ · SSM ⭐ (ไม่ต้องมี RP) · Bidir
RP: static · Auto-RP · BSR · Anycast RP (+MSDP)
show ip pim neighbor / rp mapping · show ip igmp groups · show ip mroute · show ip rpf · mtrace
Wi-Fi: multicast→unicast · mDNS gateway · Security: source filter, igmp access-group, boundary
```

---

## 13. แบบทดสอบ 10 ข้อ

1. Multicast ประหยัด bandwidth กว่า unicast อย่างไร ยกตัวอย่าง use case 3 อย่าง
2. ช่วง 239.0.0.0/8 และ 232.0.0.0/8 ใช้ทำอะไร
3. ทำไม multicast 32 กลุ่มอาจได้ MAC เดียวกัน
4. IGMPv3 เพิ่มอะไรจาก v2
5. IGMP snooping ช่วยอะไร และ querier สำคัญอย่างไร
6. RPF check คืออะไร
7. (*,G) กับ (S,G) ต่างกันอย่างไร
8. PIM-SM ต้องมีอะไรที่ PIM-SSM ไม่ต้อง
9. ภาพจากกล้อง multicast ใน VLAN เดียวหยุดทุก ๆ 4 นาทีแล้วกลับมา สาเหตุน่าจะเป็นอะไร
10. Multicast ใน Wi-Fi มีปัญหาอะไรและแก้อย่างไร

<details><summary><b>เฉลย</b></summary>

1. Source ส่ง 1 ชุด เครือข่ายทำสำเนาที่จุดแยกทางเฉพาะไปยังผู้รับที่สมัคร — IPTV, market data, OS imaging, CCTV, routing protocol
2. 239/8 = administratively scoped ใช้ภายในองค์กร; 232/8 = ช่วงของ SSM
3. MAC multicast ใช้แค่ 23 บิตล่างของ IP ขณะที่ IP มี 28 บิตสำหรับกลุ่ม 5 บิตหายไป → 2⁵ = 32 กลุ่ม map ซ้ำกัน
4. Source filtering (INCLUDE/EXCLUDE source) ทำให้ใช้ SSM ได้
5. ส่ง multicast เฉพาะพอร์ตที่มีผู้สมัครแทนการ flood ทั้ง VLAN — querier ส่ง query รักษา membership ถ้าไม่มี entry จะหมดอายุ (stream หยุด/flood)
6. ตรวจว่า multicast เข้ามาทาง interface ที่ unicast routing ใช้กลับไปหา source ถ้าไม่ใช่ให้ทิ้ง ป้องกัน loop/ซ้ำ
7. (*,G) = shared tree ผ่าน RP สำหรับ source ใดก็ได้; (S,G) = tree จาก source เจาะจง (shortest path)
8. Rendezvous Point (RP)
9. ไม่มี IGMP querier ใน VLAN ทำให้ membership ของ IGMP snooping หมดอายุ — เปิด `ip igmp snooping querier`
10. ส่งที่ data rate ต่ำสุดไม่มี ACK กิน airtime และ loss สูง — เปิด multicast-to-unicast conversion และกรอง multicast ที่ไม่จำเป็น
</details>

---

➡️ ต่อไป: **Level 97 — MPLS & Segment Routing (Service Provider)**
