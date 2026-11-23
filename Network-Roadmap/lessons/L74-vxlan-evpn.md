# บทเรียน Level 74 — VXLAN & EVPN (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจว่าทำไมต้องมี overlay · โครงสร้าง VXLAN header และ MTU · VTEP/VNI · ปัญหา flood-and-learn · EVPN คือ control plane บน BGP · route type 2/3/5 · L2VNI vs L3VNI (symmetric IRB) · distributed anycast gateway · ARP suppression · EVPN multihoming · config ตัวอย่างบน NX-OS · การ troubleshoot

---

## 1. ทำไมต้องมี Overlay

จากบทที่ 73: fabric ใช้ **L3 underlay** (ไม่มี STP ใช้ ECMP ได้ทุกเส้น) — แต่หลายงานยังต้องการ **L2 ข้าม rack**
- VM live migration (vMotion) ต้องใช้ IP เดิมหลังย้ายไป rack อื่น
- cluster/แอปเก่าที่ต้องการอยู่ subnet เดียวกัน
- multi-tenant: ลูกค้า/แผนกหลายรายใช้ IP ซ้อนกันได้

ข้อจำกัดของ VLAN: มีแค่ **4,094 ID** และต้องขยาย L2 (STP) ไปทั่ว DC

**Overlay** = สร้างเครือข่ายเสมือนวางทับบน underlay โดย **ห่อ (encapsulate)** frame L2 ไว้ใน packet UDP/IP
```
   Overlay:   VM-A (10.1.1.10) ◄──── L2 segment เดียวกัน ────► VM-B (10.1.1.20)
                    │                                              │
   Underlay:  [Leaf1 VTEP 10.0.0.11] ══ IP routed (ECMP) ══ [Leaf5 VTEP 10.0.0.15]
```

---

## 2. VXLAN (Virtual eXtensible LAN — RFC 7348)

### โครงสร้าง packet
```
 ┌───────────┬──────────┬──────────┬───────────────┬─────────────────────────────┐
 │ Outer ETH │ Outer IP │ Outer UDP│ VXLAN header  │  Original L2 frame          │
 │   14 B    │  20 B    │ 8 B      │ 8 B (VNI 24b) │  (ETH + IP + data ของ VM)   │
 │           │ src=VTEP1│ dst 4789 │               │                             │
 │           │ dst=VTEP2│ src=hash │               │                             │
 └───────────┴──────────┴──────────┴───────────────┴─────────────────────────────┘
          Overhead ≈ 50 bytes (IPv4)
```
| ส่วน | หน้าที่ |
|---|---|
| **VNI** (VXLAN Network Identifier) **24 bit** | ระบุ segment — **~16 ล้าน** ค่า (เทียบ VLAN 4,094) |
| **UDP dst port 4789** | port มาตรฐาน |
| **UDP src port = hash ของ inner flow** | ทำให้ underlay ECMP กระจาย flow ต่าง ๆ ไปหลายเส้นได้ |
| Outer IP | IP ของ **VTEP** ต้นทาง/ปลายทาง |

### VTEP (VXLAN Tunnel Endpoint)
อุปกรณ์ที่ห่อ/แกะ VXLAN — ปกติคือ **leaf switch** (hardware VTEP) หรือ hypervisor (software VTEP เช่น NSX, OVS)
- ใช้ **loopback** เป็น source IP (`interface nve1 source-interface loopback1`)

### MTU — จุดที่ทำให้ระบบล่มบ่อยที่สุด
```
 VM ส่ง frame 1500 + overhead 50 = 1550 bytes บน underlay
 → underlay ทุกลิงก์ต้องรองรับ MTU ≥ 1550 (แนะนำ 9216 jumbo)
```
อาการ MTU ผิด: **ping เล็กผ่าน แต่แอป/โอนไฟล์/SSH ค้าง** — ทดสอบ `ping <vtep> df-bit packet-size 1600` (หรือ `ping -M do -s 8972`)

---

## 3. ปัญหาของ VXLAN แบบ Flood-and-Learn

VXLAN ดั้งเดิม (ไม่มี control plane):
- VTEP ต้องรู้ว่า MAC ปลายทางอยู่หลัง VTEP ไหน → **เรียนรู้จาก data plane** เหมือน switch
- BUM traffic (Broadcast, Unknown unicast, Multicast เช่น ARP) ต้อง **flood** ไปทุก VTEP ผ่าน **multicast ใน underlay** หรือ **ingress replication** (static list ของ VTEP)
- ❌ flood มาก, scale ไม่ดี, ต้องตั้ง multicast ใน underlay, ตั้ง peer ด้วยมือ, ไม่มี routing ระหว่าง VNI ที่ดี

→ จึงต้องมี **control plane = EVPN**

---

## 4. EVPN (Ethernet VPN — RFC 7432, 8365)

**EVPN = ใช้ BGP (address family `l2vpn evpn`) แจ้งข้อมูล MAC/IP ระหว่าง VTEP** แทนการ flood เพื่อเรียนรู้
```
 Leaf1 เรียนรู้ VM-A (MAC aa:aa, IP 10.1.1.10) จาก port ของตัวเอง
   → ประกาศผ่าน BGP EVPN: "MAC aa:aa / IP 10.1.1.10 อยู่ที่ VTEP 10.0.0.11, VNI 10010"
   → Spine (route reflector) กระจายให้ทุก leaf
 Leaf5 รู้ทันทีว่าจะส่งไป VM-A ต้องห่อไป VTEP 10.0.0.11 — ไม่ต้อง flood
```
### EVPN Route Types ที่สำคัญ
| Type | ชื่อ | ใช้ทำ |
|---|---|---|
| **1** | Ethernet Auto-Discovery | multihoming (ESI), fast convergence |
| **2** ⭐ | **MAC/IP Advertisement** | ประกาศ MAC (และ IP) ของ host — หัวใจของ EVPN |
| **3** ⭐ | **Inclusive Multicast Ethernet Tag (IMET)** | ประกาศว่า VTEP ใดสนใจ VNI ใด → สร้าง flood list อัตโนมัติ (ingress replication) |
| 4 | Ethernet Segment | เลือก DF (designated forwarder) ใน multihoming |
| **5** ⭐ | **IP Prefix** | ประกาศ subnet/route (เช่น default route จาก border leaf, route ภายนอก) |

### การแยก tenant: RD และ RT (เหมือน MPLS L3VPN — Level 56)
- **RD (Route Distinguisher)** ทำให้ route ซ้ำกันของ VRF ต่างกันแยกกันได้
- **RT (Route Target)** import/export ควบคุมว่า route ไปเข้า VNI/VRF ไหน (มักตั้ง `auto`)

### Underlay + Overlay ของ BGP
```
 Underlay: eBGP (IPv4 unicast) หรือ OSPF/IS-IS → ให้ loopback ของ VTEP ทุกตัวเห็นกัน
 Overlay : BGP l2vpn evpn
   - แบบ iBGP: spine เป็น route reflector (underlay OSPF)
   - แบบ eBGP: ใช้ session เดียวกับ underlay หรือ multihop ระหว่าง loopback (next-hop unchanged)
```

---

## 5. L2VNI, L3VNI และ Symmetric IRB

| | **L2VNI** | **L3VNI** |
|---|---|---|
| แทน | VLAN/subnet หนึ่ง (bridging) | **VRF** หนึ่ง (routing ระหว่าง subnet ใน tenant) |
| ตัวอย่าง | VLAN 10 ↔ VNI 10010 | VRF PROD ↔ VNI 50001 |

### Symmetric IRB (Integrated Routing and Bridging) ⭐ ที่นิยม
```
 VM-A (VLAN 10, Leaf1) → VM-C (VLAN 20, Leaf5)
 1. Leaf1 (gateway ของ VLAN 10) route packet ใน VRF PROD
 2. ห่อ VXLAN ด้วย L3VNI 50001 ส่งไป Leaf5
 3. Leaf5 แกะ → route ใน VRF PROD → ส่งออก VLAN 20 ไปหา VM-C
 → แต่ละ leaf ต้องมีเฉพาะ VLAN/VNI ของ host ที่ต่อกับตัวเอง (scale ดี)
```
(Asymmetric IRB: route ที่ leaf ต้นทางแล้วส่งด้วย L2VNI ปลายทาง — ทุก leaf ต้องมีทุก VNI → scale แย่กว่า)

---

## 6. Distributed Anycast Gateway

**ทุก leaf เป็น default gateway ของทุก subnet ด้วย IP และ MAC เดียวกัน**
```
 VLAN 10 gateway = 10.1.1.1, MAC 0000.2222.3333 บน Leaf1, Leaf2, ... Leaf N
 VM ย้ายจาก Leaf1 ไป Leaf5 → gateway ยังเป็น IP/MAC เดิม (อยู่บน leaf ใหม่ทันที)
```
- ✅ routing เกิดที่ leaf แรก (first hop) → ไม่ต้องอ้อมไปหา gateway ตัวเดียว (ไม่มี hair-pinning)
- ✅ ไม่ต้องใช้ HSRP/VRRP
- ✅ VM mobility ไม่สะดุด

---

## 7. ARP Suppression

leaf รู้ MAC/IP ของ host ทั้งหมดจาก EVPN Type-2 → **ตอบ ARP แทน** ได้เลยโดยไม่ต้อง flood ARP ไปทั่ว fabric → ลด BUM traffic มาก

---

## 8. EVPN Multihoming (ESI) vs MLAG

server ต่อกับ 2 leaf:
| | **MLAG/vPC** | **EVPN Multihoming (ESI-LAG)** |
|---|---|---|
| หลักการ | 2 switch จำลองเป็นตัวเดียว + peer link | ใช้มาตรฐาน EVPN (Type 1/4) — ไม่ต้องมี peer link |
| มาตรฐาน | proprietary ต่อผู้ผลิต | มาตรฐานเปิด |
| ขยาย | 2 ตัว | 2 ตัวขึ้นไป (ส่วนใหญ่ใช้ 2) |
- server เห็นเป็น LACP bond ปกติทั้งสองแบบ
- ESI (Ethernet Segment Identifier) 10 bytes ระบุลิงก์กลุ่มเดียวกัน

---

## 9. ตัวอย่าง Config — Cisco NX-OS Leaf

```
feature bgp
feature interface-vlan
feature vn-segment-vlan-based
feature nv overlay
nv overlay evpn
fabric forwarding anycast-gateway-mac 0000.2222.3333

vlan 10
  vn-segment 10010                         ! L2VNI
vlan 999
  vn-segment 50001                         ! สำหรับ L3VNI ของ VRF

vrf context PROD
  vni 50001
  rd auto
  address-family ipv4 unicast
    route-target both auto evpn

interface Vlan10
  vrf member PROD
  ip address 10.1.1.1/24
  fabric forwarding mode anycast-gateway   ! distributed anycast GW
  no shutdown
interface Vlan999
  vrf member PROD
  ip forward                               ! L3VNI SVI
  no shutdown

interface loopback1
  ip address 10.0.0.11/32                  ! VTEP source
interface nve1
  source-interface loopback1
  host-reachability protocol bgp           ! ใช้ EVPN control plane
  member vni 10010
    ingress-replication protocol bgp       ! BUM ผ่าน Type-3
    suppress-arp
  member vni 50001 associate-vrf

router bgp 65101
  router-id 10.0.0.11
  neighbor 10.255.0.1 remote-as 65000       ! spine (หรือ loopback)
    address-family ipv4 unicast
    address-family l2vpn evpn
      send-community extended
evpn
  vni 10010 l2
    rd auto
    route-target import auto
    route-target export auto
```
(Arista EOS, Juniper, SONiC/FRR ใช้แนวคิดเดียวกันต่าง syntax — Juniper Apstra/Arista CloudVision ช่วย generate ได้)

---

## 10. Border Leaf และการออกนอก Fabric

- border leaf รับ route ภายนอก (จาก firewall/WAN router ผ่าน eBGP ใน VRF) แล้วประกาศเข้า fabric เป็น **Type-5** (เช่น default route)
- traffic ระหว่าง VRF (PROD ↔ DMZ) มักบังคับ **ผ่าน firewall** ที่ border/service leaf (inter-VRF ผ่าน firewall)
- **DCI (Data Center Interconnect):** EVPN multi-site (border gateway) ต่อ 2 DC — ระวัง: การขยาย L2 ข้าม DC เพิ่มความเสี่ยงให้ failure ลามข้าม site

---

## 11. Troubleshooting

```
show nve peers                           ! เห็น VTEP อื่นไหม (Up?)
show nve vni                             ! VNI ทำงานไหม, mode (CP=control plane)
show bgp l2vpn evpn summary              ! session EVPN
show bgp l2vpn evpn                      ! route type 2/3/5
show l2route evpn mac all                ! MAC ที่เรียนรู้ (local/remote)
show ip route vrf PROD                   ! route ใน tenant
ping 10.0.0.15 source 10.0.0.11 df-bit packet-size 9000   ! ตรวจ underlay/MTU
```
| อาการ | สาเหตุที่พบบ่อย |
|---|---|
| NVE peer ไม่ขึ้น | underlay ไม่เห็น loopback, BGP EVPN ไม่ขึ้น, ไม่ได้ `send-community extended` |
| ping ได้แต่แอปค้าง | **MTU underlay** |
| VM คนละ leaf ใน VLAN เดียวกันคุยไม่ได้ | VNI mapping ไม่ตรง, RT ไม่ตรง, ไม่มี Type-3 |
| คนละ subnet คุยไม่ได้ | L3VNI/VRF ไม่ครบบน leaf, ไม่ได้ `ip forward` บน L3VNI SVI, anycast GW MAC ต่างกัน |
| ออกนอก fabric ไม่ได้ | ไม่มี Type-5 default จาก border leaf |

---

## 12. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| VXLAN = EVPN | VXLAN = data plane (encapsulation), EVPN = control plane (BGP) |
| VXLAN ไม่ต้องสนใจ MTU | overhead ~50 bytes — underlay ต้องใหญ่กว่า (ตั้ง jumbo) |
| ใช้ VXLAN แล้วไม่ต้องมี underlay ดี | underlay (IP reachability ระหว่าง VTEP + ECMP) ต้องมั่นคง |
| Anycast gateway ต้องใช้ HSRP | ทุก leaf มี IP/MAC เดียวกันโดยไม่ต้องใช้ FHRP |
| ขยาย L2 ข้าม DC เป็นเรื่องดีเสมอ | เพิ่มความเสี่ยงที่ failure ลามข้าม site — ใช้เมื่อจำเป็น |

---

## 13. Cheat Sheet

```
Overlay = L2 บน L3 underlay · VXLAN = MAC-in-UDP 4789 · VNI 24 bit (~16M) · overhead ~50 B → jumbo MTU
VTEP = leaf (loopback source) · src UDP port = hash → ECMP
Flood-and-learn ไม่ scale → EVPN = BGP l2vpn evpn
Type 2 MAC/IP · Type 3 IMET (flood list) · Type 5 IP prefix · Type 1/4 multihoming
RD/RT แยก tenant · L2VNI = VLAN · L3VNI = VRF · symmetric IRB
Anycast gateway: ทุก leaf IP/MAC เดียวกัน · ARP suppression
ESI multihoming = มาตรฐานแทน MLAG
show nve peers / nve vni / bgp l2vpn evpn / l2route evpn mac
```

---

## 14. แบบทดสอบ 10 ข้อ

1. ทำไม DC ที่ใช้ L3 underlay ยังต้องการ overlay
2. VNI มีกี่บิต รองรับกี่ segment เทียบกับ VLAN
3. ทำไม VXLAN ใช้ UDP source port เป็น hash ของ inner flow
4. ถ้า underlay MTU = 1500 จะเกิดอาการอะไร
5. VXLAN แบบ flood-and-learn มีปัญหาอะไร
6. EVPN route type 2, 3, 5 ใช้ทำอะไร
7. L2VNI กับ L3VNI ต่างกันอย่างไร
8. Distributed anycast gateway คืออะไร มีข้อดีอะไร
9. ARP suppression ทำงานอย่างไร
10. `show nve peers` ไม่เห็น peer ควรตรวจอะไรบ้าง

<details><summary><b>เฉลย</b></summary>

1. งานบางอย่างต้องการ L2 ข้าม rack (VM mobility ใช้ IP เดิม, cluster) และต้องการ multi-tenant โดยไม่ขยาย STP
2. 24 บิต ~16 ล้าน segment เทียบกับ VLAN 4,094
3. เพื่อให้ ECMP ของ underlay ที่ hash จาก outer header กระจาย flow ต่าง ๆ ไปหลายเส้นทาง
4. Packet ขนาดเต็มที่ห่อแล้วเกิน MTU ถูกทิ้ง — ping เล็กผ่าน แต่แอป/โอนไฟล์ค้าง
5. ต้อง flood BUM ไปทุก VTEP (multicast/ingress replication ตั้งด้วยมือ) เรียนรู้ MAC จาก data plane, scale ไม่ดี
6. Type 2 ประกาศ MAC/IP ของ host; Type 3 ประกาศ VTEP ที่สนใจ VNI (flood list); Type 5 ประกาศ IP prefix (เช่น default route)
7. L2VNI แทน VLAN/subnet สำหรับ bridging; L3VNI แทน VRF สำหรับ routing ระหว่าง subnet (symmetric IRB)
8. ทุก leaf เป็น gateway ด้วย IP/MAC เดียวกัน — route ที่ first hop ไม่ต้อง hair-pin, ไม่ต้องใช้ FHRP, VM ย้ายได้ไม่สะดุด
9. Leaf รู้ MAC/IP ของ host จาก EVPN Type-2 จึงตอบ ARP แทนโดยไม่ flood
10. Underlay เห็น loopback ของ VTEP อื่นหรือไม่ (ping จาก loopback), BGP EVPN session, send-community extended, source-interface ของ NVE, host-reachability bgp
</details>

---

➡️ ต่อไป: **Level 75 — Virtualization Networking**
