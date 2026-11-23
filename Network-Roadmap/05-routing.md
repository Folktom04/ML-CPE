# Tier 5 — Routing (Level 41–50)

> เป้าหมายของ Tier: เข้าใจ routing ตั้งแต่ static ถึง BGP พร้อม redundancy ของ gateway

---

## Level 41 — Routing Table & Static Routing

**สิ่งที่ต้องรู้**
- Router เลือก route ด้วย: **Longest prefix match** → Administrative Distance → Metric
- AD: Connected 0, Static 1, eBGP 20, EIGRP 90, OSPF 110, IS-IS 115, RIP 120, iBGP 200
- Route codes: C, L, S, O, D, B, `*` candidate default
- Static route แบบ next-hop vs exit-interface vs fully specified
- Recursive lookup

```
ip route 10.2.0.0 255.255.0.0 192.168.1.2
show ip route
show ip route 10.2.3.4
```

**แบบทดสอบ**
1. มี route 10.0.0.0/8 (OSPF) และ 10.1.0.0/16 (static) packet ไป 10.1.5.5 ใช้ตัวไหน
2. OSPF กับ EIGRP เรียน prefix เดียวกัน ตัวไหนลง table
3. ทำไม static route ชี้ exit-interface บน Ethernet ไม่แนะนำ
4. Recursive lookup คืออะไร
5. Local route (L) คืออะไร

<details><summary>เฉลย</summary>

1. 10.1.0.0/16 (longest prefix ชนะก่อน AD)
2. EIGRP (AD 90 < 110)
3. ต้อง proxy ARP ทุกปลายทาง ARP table ใหญ่
4. หา next-hop ที่ไม่ได้ต่อตรง โดย lookup route ของ next-hop อีกรอบ
5. /32 ของ IP บน interface ตัวเอง
</details>

**5 โปรเจค**
- ⭐ P1: 3 router เส้นตรง static route ให้ ping end-to-end
- ⭐⭐ P2: ทำ static route แบบ summary + null0 route
- ⭐⭐ P3: FRR/Linux router ทำ static routing ด้วย containerlab
- ⭐⭐ P4: Python: จำลอง longest prefix match จาก routing table ใน CSV
- ⭐⭐⭐ P5: ทำ "routing table explainer" อ่าน `show ip route` → อธิบายแต่ละบรรทัดเป็นภาษาไทย

---

## Level 42 — Default Route, Floating Static & IP SLA

**สิ่งที่ต้องรู้**
- Default route `0.0.0.0/0`, Gateway of last resort
- Floating static: AD สูงกว่าเพื่อเป็น backup
- IP SLA + track: ตรวจ reachability จริง ไม่ใช่แค่ link up
- Dual ISP: active/standby, load-sharing, PBR
- `default-information originate` ใน IGP

```
ip sla 1
 icmp-echo 8.8.8.8 source-interface g0/0
 frequency 5
ip sla schedule 1 life forever start-time now
track 1 ip sla 1 reachability
ip route 0.0.0.0 0.0.0.0 203.0.113.1 track 1
ip route 0.0.0.0 0.0.0.0 198.51.100.1 250
```

**แบบทดสอบ**
1. ทำไม floating static อย่างเดียวไม่พอสำหรับ dual ISP
2. AD ของ floating ควรตั้งเท่าไร
3. IP SLA target ควรเลือกอย่างไร
4. ปัญหาเมื่อ failover แล้ว NAT session เดิม
5. วิธีกระจาย default route ให้ router ภายในใน OSPF

<details><summary>เฉลย</summary>

1. link ยัง up แต่ ISP เสียข้างใน route หลักไม่หายไป
2. มากกว่า route หลักและ routing protocol (เช่น 250)
3. ปลายทางที่เสถียร หลายจุด (ไม่ใช่แค่ gateway ISP) และต้องบังคับ source interface
4. session เดิมใช้ public IP ISP1 → ต้องเริ่ม session ใหม่ (clear NAT)
5. `default-information originate` (always ถ้าต้องการ)
</details>

**5 โปรเจค**
- ⭐ P1: Dual ISP failover ด้วย floating static ใน Packet Tracer
- ⭐⭐ P2: เพิ่ม IP SLA + track ใน GNS3 ทดสอบ ISP เสียภายใน
- ⭐⭐ P3: Linux dual WAN failover ด้วย script + `ip route` metrics
- ⭐⭐ P4: วัดเวลา failover และเขียนรายงานพร้อมคำแนะนำ tuning
- ⭐⭐⭐ P5: Dual ISP + PBR (แผนก A ใช้ ISP1, B ใช้ ISP2) + failover ข้ามกัน

---

## Level 43 — แนวคิด Dynamic Routing

**สิ่งที่ต้องรู้**
- IGP vs EGP; Distance Vector vs Link State vs Path Vector
- Metric ของแต่ละ protocol, Convergence
- Loop prevention: split horizon, route poisoning, hold-down, SPF
- ECMP (Equal-Cost Multi-Path)
- Passive interface, authentication, route filtering
- Control plane vs Data plane vs Management plane; RIB vs FIB, CEF

**แบบทดสอบ**
1. OSPF เป็นแบบไหน BGP เป็นแบบไหน
2. Split horizon คืออะไร
3. RIB กับ FIB ต่างกันอย่างไร
4. passive-interface ใช้เมื่อไร
5. ECMP มีประโยชน์อะไร

<details><summary>เฉลย</summary>

1. OSPF = Link-state, BGP = Path-vector
2. ไม่โฆษณา route กลับออกไปทาง interface ที่เรียนมา
3. RIB = routing table (control plane), FIB = ตารางที่ใช้ forward จริง (data plane)
4. interface ที่ไม่มี neighbor (LAN ผู้ใช้) แต่ต้องการโฆษณา network
5. ใช้หลายเส้นพร้อมกัน ได้ bandwidth + redundancy
</details>

**5 โปรเจค**
- ⭐ P1: ตารางเปรียบเทียบ RIP/OSPF/EIGRP/IS-IS/BGP
- ⭐⭐ P2: Python: implement Dijkstra บน graph เครือข่าย
- ⭐⭐ P3: Python: implement Bellman-Ford + แสดงปัญหา count-to-infinity
- ⭐⭐ P4: Animation/visualization การ converge ของ distance vector (เว็บ/Jupyter)
- ⭐⭐⭐ P5: บทความ "control/data/management plane" + ตัวอย่าง CoPP

---

## Level 44 — RIP (เพื่อเข้าใจ Distance Vector)

**สิ่งที่ต้องรู้**
- RIPv2: metric = hop count (max 15, 16 = unreachable), update 30 วินาที, multicast 224.0.0.9
- `no auto-summary`, passive-interface, authentication
- RIPng สำหรับ IPv6
- ในงานจริงแทบไม่ใช้แล้ว แต่ยังเจอในอุปกรณ์เก่า/ออกข้อสอบ

```
router rip
 version 2
 network 10.0.0.0
 no auto-summary
 passive-interface g0/1
```

**แบบทดสอบ**
1. metric สูงสุดที่ใช้ได้
2. ข้อเสียหลักของ hop count
3. RIPv2 ส่ง update ไปที่ address อะไร
4. ทำไมต้อง `no auto-summary`
5. ทำไมองค์กรเลิกใช้ RIP

<details><summary>เฉลย</summary>

1. 15
2. ไม่สนใจ bandwidth — เลือกเส้นช้าที่ hop น้อยกว่า
3. 224.0.0.9
4. ป้องกันการสรุปตาม classful ซึ่งพังเมื่อใช้ discontiguous network
5. converge ช้า, scale ไม่ได้, metric ไม่ฉลาด
</details>

**5 โปรเจค**
- ⭐ P1: RIPv2 4 router วงแหวน
- ⭐⭐ P2: Wireshark ดู RIP update + ทดลองตัดลิงก์ จับเวลา converge
- ⭐⭐ P3: Lab discontiguous network กับ auto-summary (ปัญหา + แก้)
- ⭐⭐ P4: Migrate RIP → OSPF ใน lab โดยลด downtime (ใช้ AD)
- ⭐⭐⭐ P5: เขียน RIP-like protocol ง่าย ๆ ด้วย Python UDP บน netns

---

## Level 45 — OSPF Single Area

**สิ่งที่ต้องรู้**
- Link-state, Dijkstra SPF, cost = reference BW / interface BW (ควรตั้ง `auto-cost reference-bandwidth 100000`)
- Router ID, Hello/Dead (10/40), Neighbor states: Down → Init → 2-Way → ExStart → Exchange → Loading → Full
- DR/BDR บน broadcast network, network type point-to-point
- Neighbor ต้องตรงกัน: area, subnet/mask, hello/dead, authentication, MTU, stub flag
- multicast 224.0.0.5 / 224.0.0.6

```
router ospf 1
 router-id 1.1.1.1
 auto-cost reference-bandwidth 100000
 passive-interface default
 no passive-interface g0/0
interface g0/0
 ip ospf 1 area 0
 ip ospf network point-to-point
```

**แบบทดสอบ**
1. neighbor ค้างที่ ExStart/Exchange สาเหตุยอดฮิต
2. Router ID เลือกจากอะไร
3. ทำไมต้องปรับ reference bandwidth
4. ลิงก์ระหว่าง 2 router ควรตั้ง network type อะไร
5. ค้างที่ 2-Way บน broadcast network ปกติหรือไม่

<details><summary>เฉลย</summary>

1. MTU mismatch
2. กำหนดเอง → loopback IP สูงสุด → interface IP สูงสุด
3. ค่า default 100 Mbps ทำให้ 1G/10G/100G cost = 1 เท่ากันหมด
4. point-to-point (ไม่ต้องเลือก DR เร็วกว่า)
5. ปกติ ระหว่าง DROTHER ด้วยกัน
</details>

**5 โปรเจค**
- ⭐ P1: OSPF area 0 4 router + loopback
- ⭐⭐ P2: Debug neighbor ที่ไม่ขึ้น 6 สาเหตุ (break/fix lab)
- ⭐⭐ P3: Containerlab FRR OSPF + ECMP ทดสอบด้วย traceroute
- ⭐⭐ P4: ปรับ cost ทำ traffic engineering ให้ traffic เดินเส้นที่ต้องการ
- ⭐⭐⭐ P5: Python parse `show ip ospf database` → วาด topology จาก LSA

---

## Level 46 — OSPF Multi-Area & LSA

**สิ่งที่ต้องรู้**
- ABR, ASBR, Backbone area 0 (ทุก area ต้องต่อ area 0 หรือใช้ virtual link)
- LSA Type 1 Router, 2 Network, 3 Summary, 4 ASBR Summary, 5 External, 7 NSSA
- Area types: Standard, Stub, Totally stubby, NSSA, Totally NSSA
- Summarization ที่ ABR (`area X range`) และ ASBR (`summary-address`)
- OSPFv3 สำหรับ IPv6, BFD สำหรับตรวจ failure เร็ว

**แบบทดสอบ**
1. Stub area ไม่รับ LSA type ไหน
2. NSSA ใช้เมื่อไร
3. Summarize ที่ ABR ใช้คำสั่งอะไร
4. ทำไม multi-area ช่วย scale
5. BFD ช่วยอะไร

<details><summary>เฉลย</summary>

1. Type 5 (totally stubby ไม่รับ 3,4,5 ยกเว้น default)
2. area ที่อยากเป็น stub แต่มี ASBR (เช่น redistribute จาก connected/static ของสาขา)
3. `area X range <prefix> <mask>`
4. จำกัด LSDB/SPF ภายใน area, ลด flooding
5. ตรวจลิงก์เสียระดับ ms แทนรอ dead timer
</details>

**5 โปรเจค**
- ⭐⭐ P1: OSPF 3 area + ABR summarization
- ⭐⭐ P2: เปลี่ยน area เป็น stub/totally stubby/NSSA เปรียบเทียบ LSDB
- ⭐⭐ P3: Redistribute static → OSPF ผ่าน NSSA ดู LSA 7 → 5
- ⭐⭐⭐ P4: ใส่ BFD แล้ววัด convergence ก่อน/หลัง
- ⭐⭐⭐ P5: ออกแบบ OSPF สำหรับองค์กร 20 สาขา (area design, summarization, IP plan)

---

## Level 47 — EIGRP

**สิ่งที่ต้องรู้**
- Advanced distance vector (Cisco, เปิดเป็น informational RFC 7868)
- DUAL: Successor, Feasible Successor, Feasible Distance, Reported Distance, Feasibility condition
- Metric: bandwidth + delay (K-values), wide metrics
- Named mode, stub routing, unequal-cost load balancing (variance), summarization
- AD 90 internal, 170 external

**แบบทดสอบ**
1. Feasibility condition คืออะไร
2. variance ใช้ทำอะไร
3. EIGRP stub ประโยชน์คืออะไร
4. Stuck-in-Active คืออะไร
5. ค่า K-values default ใช้อะไรในการคำนวณ

<details><summary>เฉลย</summary>

1. RD ของเส้นสำรอง < FD ของเส้นปัจจุบัน → รับประกันไม่ loop
2. ทำ unequal-cost load balancing
3. ลด query scope → ป้องกัน SIA, เหมาะกับสาขา
4. ส่ง query แล้วไม่ได้ reply ทันเวลา
5. bandwidth และ delay
</details>

**5 โปรเจค**
- ⭐ P1: EIGRP named mode 4 router
- ⭐⭐ P2: คำนวณ FD/RD ด้วยมือแล้วเทียบ `show ip eigrp topology`
- ⭐⭐ P3: Unequal-cost load balancing ด้วย variance
- ⭐⭐ P4: Hub-and-spoke + stub ใน lab
- ⭐⭐⭐ P5: Migration EIGRP → OSPF แผนงาน + implement ใน lab (มี rollback plan)

---

## Level 48 — BGP พื้นฐาน

**สิ่งที่ต้องรู้**
- Path-vector, TCP 179, AS number (public/private 64512–65534, 4-byte)
- eBGP vs iBGP (iBGP ไม่ส่งต่อ route ที่ได้จาก iBGP → full mesh / route reflector)
- Neighbor states: Idle, Connect, Active, OpenSent, OpenConfirm, Established
- `network` statement ต้องตรงกับ RIB, eBGP multihop, update-source loopback
- next-hop-self
- อินเทอร์เน็ต = BGP ระหว่าง AS ประมาณ 1 ล้าน IPv4 prefix

```
router bgp 65001
 bgp router-id 1.1.1.1
 neighbor 203.0.113.1 remote-as 65000
 address-family ipv4
  network 198.51.100.0 mask 255.255.255.0
  neighbor 203.0.113.1 activate
```

**แบบทดสอบ**
1. neighbor ค้าง Active หมายถึงอะไร
2. ทำไม `network` ไม่โฆษณา
3. ทำไม iBGP ต้อง full mesh
4. next-hop-self ใช้เมื่อไร
5. Private ASN ใช้ทำอะไร

<details><summary>เฉลย</summary>

1. พยายามสร้าง TCP แต่ไม่สำเร็จ (IP/AS ผิด, ACL block 179, ไม่มี route)
2. prefix/mask ไม่ตรงกับที่มีใน routing table
3. split-horizon ของ iBGP ป้องกัน loop
4. iBGP peer ไม่รู้จัก next-hop ภายนอก (eBGP)
5. ภายในองค์กร/ลูกค้า ISP ที่ไม่ต้องมี public ASN
</details>

**5 โปรเจค**
- ⭐⭐ P1: eBGP ระหว่าง 2 AS + iBGP ภายใน
- ⭐⭐ P2: Containerlab: องค์กร multihomed 2 ISP (FRR)
- ⭐⭐ P3: ดู BGP table จริงจาก route server สาธารณะ (เช่น RIPEstat/bgp.tools) วิเคราะห์ AS path ของมหาวิทยาลัย
- ⭐⭐⭐ P4: Route Reflector design 6 router
- ⭐⭐⭐ P5: ศึกษา outage BGP จริง (Facebook 2021, Pakistan/YouTube 2008) เขียน case study

---

## Level 49 — BGP Path Selection & Policy

**สิ่งที่ต้องรู้**
- ลำดับตัดสิน (Cisco): Weight → Local Preference → Locally originated → AS-path สั้น → Origin → MED → eBGP>iBGP → IGP metric ถึง next-hop → ... → Router ID
- Outbound traffic ควบคุมด้วย Local Pref/Weight; Inbound ควบคุมด้วย AS-path prepend, MED, community, more-specific
- Prefix-list, route-map, AS-path access-list, Communities (no-export, well-known, BGP blackhole)
- Security: RPKI/ROA, max-prefix, prefix filtering (MANRS), TTL security
- Redistribution ระหว่าง protocol + route tag ป้องกัน loop

**แบบทดสอบ**
1. ต้องการให้ traffic ขาออกใช้ ISP1 เป็นหลัก ใช้ attribute อะไร
2. ต้องการให้ traffic ขาเข้ามาทาง ISP1 เป็นหลัก ทำอย่างไร
3. RPKI ป้องกันอะไร
4. Weight มีผลภายในขอบเขตใด
5. ทำไมต้องใส่ max-prefix

<details><summary>เฉลย</summary>

1. Local Preference (สูงกว่าชนะ)
2. AS-path prepend ที่ ISP2 หรือประกาศ more-specific/community ของ ISP
3. Route hijack / origin ผิด
4. Router ตัวเดียว (ไม่ส่งต่อ)
5. ป้องกัน peer ส่ง route มาล้น (route leak) ทำ router พัง
</details>

**5 โปรเจค**
- ⭐⭐ P1: Lab dual ISP: outbound ด้วย Local Pref, inbound ด้วย prepend
- ⭐⭐ P2: Prefix filtering ขาเข้า/ขาออกตามหลัก MANRS
- ⭐⭐⭐ P3: ตั้ง RPKI validator (Routinator) + FRR ทำ origin validation
- ⭐⭐⭐ P4: BGP community-based policy (ลูกค้าเลือก prepend เอง)
- ⭐⭐⭐ P5: Redistribution OSPF ↔ BGP แบบ 2 จุด + tag ป้องกัน loop

---

## Level 50 — First Hop Redundancy (HSRP / VRRP / GLBP)

**สิ่งที่ต้องรู้**
- ปัญหา: default gateway เป็น single point of failure
- Virtual IP + virtual MAC; Active/Standby (HSRP), Master/Backup (VRRP มาตรฐาน), GLBP (load balance)
- Priority, Preempt, Interface tracking / object tracking
- จับคู่ HSRP active กับ STP root ใน VLAN เดียวกัน
- Anycast gateway ใน DC (Level 74)

```
interface vlan 10
 ip address 10.10.10.2 255.255.255.0
 standby version 2
 standby 10 ip 10.10.10.1
 standby 10 priority 110
 standby 10 preempt
 standby 10 track 1 decrement 20
```

**แบบทดสอบ**
1. ไม่ตั้ง preempt จะเกิดอะไรเมื่อ router หลักกลับมา
2. VRRP ต่างจาก HSRP อย่างไร
3. ทำไมต้อง track uplink
4. ทำไม HSRP active ควรเป็น STP root ด้วย
5. GLBP ทำ load balance อย่างไร

<details><summary>เฉลย</summary>

1. ไม่ยึดคืน — standby ยังเป็น active ต่อ
2. VRRP เป็นมาตรฐานเปิด, ใช้ IP จริงของ router เป็น VIP ได้, ศัพท์ master/backup
3. ถ้า uplink ตายแต่ LAN ยัง up router จะยังเป็น active แต่ส่ง traffic ไม่ได้
4. ให้ L2 path ตรงกับ L3 path ไม่อ้อม
5. AVG ตอบ ARP ด้วย virtual MAC ของ AVF ต่างกันแต่ละ client
</details>

**5 โปรเจค**
- ⭐ P1: HSRP 2 router 1 VLAN ทดสอบ failover
- ⭐⭐ P2: HSRP หลาย VLAN active สลับกัน (load-share) + STP root ตรงกัน
- ⭐⭐ P3: VRRP บน Linux ด้วย keepalived
- ⭐⭐ P4: วัด failover time ด้วย ping ทุก 100ms + ปรับ timer
- ⭐⭐⭐ P5: Capstone Tier 5: องค์กร HQ + 2 สาขา: OSPF multi-area, dual ISP BGP, HSRP, NAT — เอกสาร + test plan + failover test
