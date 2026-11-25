# บทเรียน Level 73 — Data Center Design: Spine-Leaf (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจว่าทำไม DC เปลี่ยนจาก 3-tier เป็น spine-leaf (Clos) · คำนวณจำนวนพอร์ต/oversubscription/ขนาด fabric · ออกแบบ L3 fabric ด้วย eBGP (RFC 7938) และ ECMP · border leaf/service leaf · ToR vs EoR · การเชื่อม server (dual-homed) · OOB · ขยาย fabric เป็น super-spine

---

## 1. Traffic ใน Data Center เปลี่ยนไป

| | ยุคก่อน | ปัจจุบัน |
|---|---|---|
| แอป | monolithic, ผู้ใช้ ↔ server | **microservices, virtualization, distributed storage, AI** |
| ทิศทาง traffic หลัก | **North-South** (เข้า-ออก DC) | **East-West** (server ↔ server ภายใน DC) — มากกว่า N-S หลายเท่า |
| ตัวอย่าง | ผู้ใช้เปิดเว็บ | web → app → DB → cache, vMotion, vSAN/Ceph replication, backup, GPU all-reduce |

### ปัญหาของ 3-tier (Core–Aggregation–Access) แบบเดิมใน DC
```
              [Core]
            /        \
        [Agg]──────[Agg]
        /  \  STP  /  \
     [Acc][Acc]  [Acc][Acc]
```
- **STP block ลิงก์สำรอง** → ใช้ bandwidth ได้ครึ่งเดียว
- server คนละ access ต้องขึ้นไปถึง agg/core → **จำนวน hop และ latency ไม่เท่ากัน**
- **คอขวดที่ agg/core** เมื่อ east-west เพิ่ม
- **failure domain ใหญ่** (L2 กว้าง, loop ลามทั้ง DC)
- ขยายยาก

---

## 2. Spine-Leaf (Clos Topology)

```
        [Spine1]   [Spine2]   [Spine3]   [Spine4]
         │ │ │ │    │ │ │ │    │ │ │ │    │ │ │ │      ← ทุก leaf ต่อกับทุก spine
   ┌─────┘ │ │ └────┼─┼─┼─┼────┼─┼─┼─┼────┘ │ │ │
 [Leaf1] [Leaf2] [Leaf3] ... [Leaf N]  [Border Leaf]   ← leaf = ToR ของแต่ละ rack
   │ │     │ │     │ │                    │
  servers servers servers               firewall/WAN/Internet
```
### กฎของ Clos
1. **Leaf ทุกตัวต่อกับ Spine ทุกตัว**
2. **Spine ไม่ต่อกันเอง** · **Leaf ไม่ต่อกันเอง** (ยกเว้นลิงก์ MLAG peer ระหว่าง leaf คู่ในบางแบบ)
3. อุปกรณ์ปลายทาง (server, firewall, WAN, storage) ต่อที่ **leaf เท่านั้น**

### ผลลัพธ์

| คุณสมบัติ | อธิบาย |
|---|---|
| **Latency คาดเดาได้** | server คู่ใดก็ตามที่อยู่คนละ leaf ห่าง **leaf → spine → leaf** เสมอ (3 hop ของ switch) |
| **ใช้ทุกลิงก์ (ECMP)** | ไม่มี STP block — routing กระจาย flow ผ่านทุก spine |
| **ทนทาน** | spine 1 ใน 4 ล่ม → เสีย bandwidth แค่ 25% ไม่ใช่ทั้งหมด |
| **ขยายแนวนอน (scale-out)** | ต้องการพอร์ต server เพิ่ม → เพิ่ม leaf · ต้องการ bandwidth เพิ่ม → เพิ่ม spine |
| **Failure domain เล็ก** | L3 ถึง leaf — ปัญหาจำกัดใน rack |
| **ง่ายต่อ automation** | โครงสร้างสม่ำเสมอ config เป็น template |

---

## 3. Sizing — คำนวณขนาด Fabric

### จำนวน Leaf สูงสุด = จำนวนพอร์ตต่อ Spine
```
 Spine มี 32 พอร์ต 100G → รองรับ leaf ได้สูงสุด 32 ตัว (leaf ละ 1 พอร์ตต่อ spine)
```
### จำนวน Spine สูงสุด = จำนวน uplink ต่อ Leaf
```
 Leaf มี uplink 100G 8 พอร์ต → spine ได้สูงสุด 8 ตัว
```
### Oversubscription ของ Leaf
```
 Leaf: 48 × 25G (server) + 8 × 100G (uplink) แต่ใช้ spine 4 ตัว (ใช้ uplink 4 พอร์ต)
 downlink = 48 × 25 = 1,200 Gbps · uplink = 4 × 100 = 400 Gbps → 3 : 1
 เพิ่ม spine เป็น 8 ตัว → uplink 800 Gbps → 1.5 : 1
```

| งาน | Oversubscription ที่เหมาะ |
|---|---|
| Enterprise DC ทั่วไป | 3:1 หรือต่ำกว่า |
| Storage/HCI หนาแน่น | 2:1 – 1.5:1 |
| **AI/HPC (GPU training)** | **1:1 (non-blocking)** — Level 98 |

### ตัวอย่างความจุ
```
 Spine 4 ตัว × 32 พอร์ต 100G · Leaf 32 ตัว × (48 × 25G + 4 × 100G)
 พอร์ต server = 32 × 48 = 1,536 พอร์ต 25G · oversubscription 3:1
 ต้องการมากกว่านี้ → spine ที่พอร์ตมากกว่า หรือ 5-stage Clos (super-spine/pod)
```

### 5-Stage Clos (Super-spine)
หลาย **pod** (แต่ละ pod เป็น spine-leaf) เชื่อมกันด้วย **super-spine** — ใช้ใน DC ขนาดใหญ่มาก (hyperscaler, cloud)

---

## 4. Underlay Routing ของ Fabric

### L3 ถึง Leaf (routed fabric)
ลิงก์ leaf–spine เป็น **routed point-to-point** (ไม่มี L2/STP ระหว่าง leaf–spine) — gateway ของ server อยู่ที่ leaf

### เลือก Routing Protocol

| ตัวเลือก | หมายเหตุ |
|---|---|
| **eBGP** ⭐ (RFC 7938) | นิยมที่สุดใน DC ขนาดกลาง–ใหญ่: เรียบง่าย, scale ดี, policy ยืดหยุ่น, failure domain ชัด, ทำงานดีกับ EVPN |
| OSPF / IS-IS | ใช้ได้ดีใน fabric ขนาดเล็ก–กลาง (และเป็น underlay ร่วมกับ iBGP EVPN) |

### รูปแบบ eBGP ที่พบบ่อย
```
 Spine ทุกตัว: AS 65000 (เดียวกัน — ป้องกัน path วนผ่าน spine อื่น)
 Leaf แต่ละตัว (หรือแต่ละคู่ MLAG): AS ของตัวเอง 65101, 65102, ... (private ASN)
 → แต่ละ leaf ประกาศ subnet ของ server/loopback · spine เป็นตัวกลางกระจาย
 maximum-paths ≥ จำนวน spine → ECMP ใช้ทุกเส้นทาง
 BFD บนทุกลิงก์ → ตรวจลิงก์เสียระดับ ms
```
**BGP unnumbered** (FRR/Cumulus/SONiC/Arista): ใช้ IPv6 link-local บนลิงก์ ไม่ต้องจัดสรร IP /31 ให้ทุกลิงก์ → config ง่ายมาก

### ECMP ใน Fabric
- กระจาย **ต่อ flow** ด้วย hash (5-tuple) — flow เดียวผ่านเส้นเดียว (Level 37/43)
- ปัญหา **elephant flow** (flow ใหญ่ไม่กี่ตัว เช่น backup/storage/AI) อาจไปกองบางเส้น → แก้ด้วย flowlet/adaptive load balancing, จำนวนเส้นมากขึ้น (Level 98)

---

## 5. Overlay (เมื่อจำเป็นต้องมี L2 ข้าม Rack)

ถ้า VM/แอปต้องการ **VLAN เดียวกันข้ามหลาย leaf** (เช่น VM ย้ายข้าม rack โดยใช้ IP เดิม, cluster ที่ต้องการ L2) → ใช้ **VXLAN + EVPN** สร้าง L2 overlay บน L3 underlay (Level 74)
- underlay = L3 ล้วน (ไม่มี STP)
- overlay = VXLAN tunnel ระหว่าง leaf (VTEP)
- **distributed anycast gateway** — ทุก leaf เป็น gateway ของทุก VLAN ด้วย IP/MAC เดียวกัน

---

## 6. บทบาทของ Leaf

| Leaf | ต่อกับ |
|---|---|
| **Server/Compute leaf** | server, hypervisor host (เป็นส่วนใหญ่) |
| **Storage leaf** | storage array/HCI storage network (บางแบบแยก fabric) |
| **Service leaf** | firewall, load balancer, IDS (บริการที่ traffic ต้องผ่าน) |
| **Border leaf** | ทางออกจาก fabric: core/WAN router, อินเทอร์เน็ต, DC อื่น (DCI), cloud |
| **Management/OOB** | (แยกเป็นเครือข่ายต่างหาก) |

---

## 7. ToR vs EoR / MoR (การวาง switch)

| | **ToR (Top of Rack)** ⭐ | **EoR/MoR (End/Middle of Row)** |
|---|---|---|
| ตำแหน่ง | switch อยู่บนสุดของแต่ละ rack | switch ใหญ่ (chassis) อยู่ปลาย/กลางแถว |
| สายจาก server | สั้น (DAC/AOC ในตู้) | ยาว (สายจากทุก rack ไปปลายแถว) |
| จำนวน switch | มาก (1–2 ต่อ rack) | น้อย |
| ข้อดี | สายน้อย/สั้น, rack เป็นโมดูล, ขยายง่าย | จัดการอุปกรณ์น้อย, ใช้พอร์ตได้เต็มกว่า |
| ข้อเสีย | อุปกรณ์มากต้องจัดการ (ต้องมี automation) | สายมากและยาว, เปลี่ยนแปลงยาก |
| ปัจจุบัน | **นิยมที่สุดใน spine-leaf** | DC เก่า, บางกรณี |

---

## 8. การเชื่อม Server

```
            [Leaf1A]════MLAG/EVPN-MH════[Leaf1B]      ← ToR คู่ต่อ rack
               │ 25G                       │ 25G
               └────────[ Server ]─────────┘
                    bond/LACP หรือ active-active (hypervisor)
               iDRAC/iLO 1G ──► OOB switch
```
- **Dual-homed** ไป ToR 2 ตัว (MLAG/vPC หรือ **EVPN multihoming (ESI)**) → ToR ตัวหนึ่งล่ม/upgrade ได้โดย server ไม่หลุด
- ความเร็วปัจจุบัน: server 25G/50G/100G, AI server 200/400G
- แยก traffic ด้วย VLAN/VNI: management, vMotion/live migration, storage (iSCSI/NVMe-oF/vSAN/Ceph), VM networks, backup
- **MTU 9000 (jumbo)** สำหรับ storage/overlay — ต้องตั้งเท่ากันทุก hop (และ underlay ต้องรองรับ overhead ของ VXLAN)

---

## 9. OOB Management Network

**เครือข่ายจัดการแยกทางกายภาพ** (switch 1G ราคาถูกต่อ rack + console server)
- ต่อพอร์ต management ของ switch/firewall/PDU/iDRAC/iLO
- ยังเข้าถึงได้แม้ production fabric ล่มหรือตั้งค่าผิด
- ใช้ใน ZTP (bootstrap switch ใหม่)
- จำกัดการเข้าถึงเฉพาะ jump host/NOC

---

## 10. Automation และการทำงานของ DC สมัยใหม่

fabric มีอุปกรณ์หลายสิบถึงหลายร้อยตัวที่ config คล้ายกัน → **ต้องใช้ automation**
- **ZTP** สำหรับ switch ใหม่
- **Source of Truth** (NetBox) → generate config (Jinja2) → deploy (Ansible/Nornir) → validate (Batfish/pyATS) (Tier 9)
- Fabric manager ของผู้ผลิต: **Cisco Nexus Dashboard/ACI**, **Arista CloudVision**, **Juniper Apstra** (intent-based), Dell SmartFabric, SONiC-based solutions
- **Telemetry** (gNMI) monitor ทุกลิงก์

---

## 11. ตัวอย่างการออกแบบ (DC ขนาดกลาง 20 rack)

```
 Spine: 4 × 32-port 100G (eBGP AS 65000) — ขยายได้ถึง 32 leaf
 Leaf : 20 คู่ ToR? (เลือก) — ตัวอย่าง: 1 คู่ MLAG ต่อ 2 rack = 10 คู่ (AS 65101-65110)
        48 × 25G downlink + 8 × 100G uplink (ใช้ 4 ไป spine)
 Border leaf คู่: ไป firewall คู่ (HA), WAN/Internet router, DCI ไป DR
 Service leaf: load balancer คู่
 Overlay: EVPN-VXLAN (VRF: PROD, DEV, DMZ) + anycast gateway
 OOB: 1G switch ต่อ rack → management firewall → jump host
 Underlay: /31 หรือ BGP unnumbered · BFD · MTU 9216 ที่ underlay
 Oversubscription: (48×25)/(4×100) = 3:1 · storage leaf ใช้ uplink 6 เส้น
```

---

## 12. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| Spine ต่อกันเองเพื่อสำรอง | spine ไม่ต่อกัน — redundancy มาจากการมีหลาย spine และ ECMP |
| Spine-leaf ต้องใช้ L2 + STP | underlay เป็น L3 + ECMP; L2 ข้าม rack ใช้ VXLAN/EVPN |
| เพิ่มพอร์ต server ต้องเปลี่ยน spine | เพิ่ม leaf (จนกว่าพอร์ตของ spine จะเต็ม) |
| ECMP ทำให้ flow เดียวใช้ทุก spine | กระจายต่อ flow — flow เดียวผ่านเส้นเดียว |
| ใช้ OSPF/BGP ไม่สำคัญเท่าไร | eBGP นิยมใน fabric ใหญ่เพราะ scale/policy/failure domain |

---

## 13. Cheat Sheet

```
DC traffic = east-west · 3-tier: STP block, hop ไม่เท่ากัน, คอขวด
Clos: leaf ทุกตัวต่อ spine ทุกตัว · spine ไม่ต่อกัน · leaf ไม่ต่อกัน · อุปกรณ์ต่อที่ leaf
leaf → spine → leaf เสมอ · ECMP · เพิ่ม leaf = เพิ่มพอร์ต · เพิ่ม spine = เพิ่ม bandwidth
max leaf = พอร์ตของ spine · max spine = uplink ของ leaf
Oversub = downlink ÷ uplink · enterprise ≤ 3:1 · storage 2:1-1.5:1 · AI 1:1
Underlay: L3 · eBGP (RFC 7938, spine AS เดียว, leaf AS ต่างกัน) · BGP unnumbered · BFD
Overlay: VXLAN/EVPN + anycast gateway (L2 ข้าม rack)
Leaf: compute · storage · service · border · ToR (นิยม) vs EoR
Server dual-homed (MLAG/EVPN-MH) · 25/100G · jumbo MTU · OOB แยก · automation/ZTP
```

---

## 14. แบบทดสอบ 10 ข้อ

1. ทำไม data center สมัยใหม่มี east-west traffic มาก
2. ปัญหาของ 3-tier ใน DC (3 ข้อ)
3. กฎการเชื่อมต่อของ spine-leaf
4. Server 2 เครื่องคนละ leaf ห่างกันกี่ hop ของ switch
5. Spine มี 64 พอร์ต leaf มี uplink 6 พอร์ต fabric รองรับ leaf และ spine ได้สูงสุดกี่ตัว
6. Leaf 48 × 25G, uplink 6 × 100G (ใช้ทั้งหมด) oversubscription เท่าไร
7. ทำไมนิยมใช้ eBGP ใน DC fabric และ AS วางอย่างไร
8. Border leaf ทำหน้าที่อะไร
9. ToR ต่างจาก EoR อย่างไร
10. ถ้าต้องการให้ VM ย้ายข้าม rack โดยใช้ IP เดิมบน fabric ที่เป็น L3 ทำได้อย่างไร

<details><summary><b>เฉลย</b></summary>

1. แอปเป็น microservices/distributed, virtualization (vMotion), distributed storage/HCI replication, backup, AI ทำให้ server คุยกันเองมากกว่าคุยกับภายนอก
2. STP block ลิงก์สำรอง, จำนวน hop/latency ไม่เท่ากัน, คอขวดที่ aggregation/core, failure domain ใหญ่, ขยายยาก
3. Leaf ทุกตัวต่อ spine ทุกตัว, spine ไม่ต่อกัน, leaf ไม่ต่อกัน, อุปกรณ์ปลายทางต่อที่ leaf
4. 3 hop (leaf → spine → leaf)
5. Leaf สูงสุด 64 ตัว, spine สูงสุด 6 ตัว
6. 1,200 ÷ 600 = 2 : 1
7. เรียบง่าย scale ได้ดี policy ยืดหยุ่น failure domain ชัดเจน และทำงานกับ EVPN — spine ใช้ AS เดียวกัน, leaf (หรือคู่ leaf) แต่ละตัวใช้ AS ของตัวเอง (private ASN)
8. เชื่อม fabric ออกไปภายนอก: firewall, WAN/Internet router, DC อื่น (DCI), cloud
9. ToR วาง switch บนแต่ละ rack (สายสั้น, เป็นโมดูล — นิยมใน spine-leaf); EoR วาง switch ใหญ่ปลายแถว (สายยาวจากทุก rack)
10. ใช้ overlay VXLAN + EVPN ขยาย L2 segment ข้าม leaf บน underlay L3 พร้อม distributed anycast gateway
</details>

---

➡️ ต่อไป: **Level 74 — VXLAN & EVPN**
