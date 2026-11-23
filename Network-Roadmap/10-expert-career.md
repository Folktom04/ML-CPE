# Tier 10 — Expert, Architecture & Career (Level 91–100)

> เป้าหมายของ Tier: คิดแบบ Network Architect — ออกแบบ, บริหารความเสี่ยง, เทคโนโลยีระดับ Service Provider/AI DC และเติบโตในอาชีพ

---

## Level 91 — Advanced Troubleshooting ระดับองค์กร

**สิ่งที่ต้องรู้**
- ปัญหาแบบ intermittent: เก็บหลักฐานต่อเนื่อง (ring capture, flow, syslog correlation)
- Asymmetric routing + stateful firewall, MTU black hole, ECMP hash polarization
- Control-plane issues: CoPP drop, CPU punt, TCAM exhaustion
- Packet walk ผ่านอุปกรณ์ (packet-tracer ของ ASA, `diagnose debug flow` FortiGate)
- การจับ packet หลายจุดพร้อมกัน แล้ว align เวลา
- ทำงานกับ vendor TAC: เก็บ show tech, timeline, เลข case

**แบบทดสอบ**
1. traffic ขาไปผ่าน FW1 ขากลับผ่าน FW2 เกิดอะไร
2. เว็บบางเว็บค้าง แต่ ping ได้ สงสัยอะไร
3. ECMP polarization คืออะไร
4. CPU router สูงผิดปกติ ตรวจอะไรก่อน
5. ข้อมูลอะไรควรมีเมื่อเปิด TAC case

<details><summary>เฉลย</summary>

1. FW2 ไม่มี session (ไม่เห็น SYN) → drop
2. MTU/PMTUD black hole (ICMP ถูก block) — แก้ MSS clamping
3. ทุกชั้นใช้ hash แบบเดียวกัน → traffic ไปกระจุกบางลิงก์
4. process ที่ใช้ CPU, traffic ที่ punt ขึ้น CPU (ARP storm, TTL expire, ACL log), CoPP counters
5. รุ่น/version, show tech, log, timeline, topology, ผลกระทบ, สิ่งที่ลองแล้ว
</details>

**5 โปรเจค**
- ⭐⭐ P1: Lab asymmetric routing ผ่าน 2 firewall + แก้ (state sync/route design)
- ⭐⭐⭐ P2: Lab MTU black hole ใน GRE/IPsec + พิสูจน์ด้วย capture 2 จุด
- ⭐⭐⭐ P3: Troubleshooting challenge 20 โจทย์ ใน lab ใหญ่ (ให้เพื่อน break)
- ⭐⭐⭐ P4: สคริปต์ multi-point capture พร้อมกันหลายเครื่อง + merge (mergecap)
- ⭐⭐⭐ P5: Post-mortem จาก outage สาธารณะ 3 เหตุการณ์ (Cloudflare, AWS, Rogers 2022) วิเคราะห์บทเรียน

---

## Level 92 — Network Design Methodology

**สิ่งที่ต้องรู้**
- Requirements: business, technical, constraints (งบ, เวลา, ทีม), ความต้องการด้าน compliance
- Top-down design, PPDIOO / Plan-Build-Manage
- HLD (High-Level Design) vs LLD (Low-Level Design)
- Design principles: modularity, hierarchy, redundancy, simplicity, scalability, security
- Trade-offs: cost vs availability vs complexity; build vs buy; single vs multi-vendor
- Architecture Decision Record (ADR)

**แบบทดสอบ**
1. HLD กับ LLD ต่างกันอย่างไร
2. คำถาม requirement 5 ข้อที่ต้องถามลูกค้าก่อนออกแบบ
3. ADR คืออะไร
4. ทำไมความซับซ้อนคือศัตรูของ availability
5. Multi-vendor ข้อดีข้อเสีย

<details><summary>เฉลย</summary>

1. HLD = ภาพรวมสถาปัตยกรรม/เหตุผล; LLD = รายละเอียดติดตั้ง (IP, port, config)
2. ผู้ใช้/อุปกรณ์กี่ราย, แอปสำคัญ, SLA/downtime ที่รับได้, งบ/เวลา, security/compliance, การเติบโต 3–5 ปี
3. เอกสารบันทึกการตัดสินใจ: บริบท, ทางเลือก, เหตุผล, ผลที่ตามมา
4. จุดเสียมากขึ้น, ทีมเข้าใจยาก, change ผิดพลาดง่าย
5. ข้อดี: ต่อรองราคา, ลด vendor risk; ข้อเสีย: interop, ทักษะทีมหลายแบบ, troubleshoot ยาก
</details>

**5 โปรเจค**
- ⭐⭐ P1: Requirement gathering template + ตัวอย่างกรอกจริง
- ⭐⭐⭐ P2: HLD เครือข่ายโรงพยาบาล 500 เตียง
- ⭐⭐⭐ P3: LLD ของ P2 (IP plan, VLAN, routing, security, wireless)
- ⭐⭐ P4: เขียน ADR 5 ฉบับจากการตัดสินใจใน lab
- ⭐⭐⭐ P5: Design review: ให้เพื่อนตรวจ design กันและกัน พร้อม checklist

---

## Level 93 — High Availability & Disaster Recovery

**สิ่งที่ต้องรู้**
- Availability = MTBF / (MTBF + MTTR); serial vs parallel availability
- Redundancy ทุกชั้น: link, device, power, path, site, provider, DNS
- Failure domain, blast radius, shared fate (สาย 2 เส้นในท่อเดียวกัน)
- RPO/RTO, DR site (hot/warm/cold), active-active vs active-standby
- Chaos engineering / failover test ตามแผน (game day)
- Graceful restart, NSF, ISSU, BFD

**แบบทดสอบ**
1. อุปกรณ์ 2 ตัว availability 99% ต่ออนุกรม รวมเท่าไร ขนานล่ะ
2. RPO vs RTO
3. Shared fate คืออะไร ยกตัวอย่าง
4. ทำไมต้องทดสอบ failover จริง
5. Active-active ข้อควรระวัง

<details><summary>เฉลย</summary>

1. อนุกรม 0.99×0.99 = 98.01%; ขนาน 1−(0.01×0.01) = 99.99%
2. RPO = ข้อมูลหายได้มากสุด (ย้อนเวลา); RTO = เวลากู้คืนระบบ
3. สองระบบที่ดูเหมือนแยกแต่เสียพร้อมกัน เช่น ISP สองเจ้าใช้ท่อร้อยสายเดียวกัน
4. redundancy ที่ไม่เคยทดสอบมักใช้ไม่ได้จริง (config drift, ไม่มีใครรู้ขั้นตอน)
5. แต่ละฝั่งต้องรับโหลดรวมได้เมื่ออีกฝั่งล่ม (ใช้ไม่เกิน 50%), state sync, split-brain
</details>

**5 โปรเจค**
- ⭐⭐ P1: คำนวณ availability end-to-end ของเครือข่าย lab (spreadsheet)
- ⭐⭐⭐ P2: Failure mode analysis (FMEA) ของ design Level 92
- ⭐⭐⭐ P3: Game day: ทดสอบ failover 10 สถานการณ์ใน lab บันทึกผล
- ⭐⭐ P4: แผน DR เครือข่าย (runbook ย้ายไป DR site)
- ⭐⭐⭐ P5: Chaos script: ปิด link/node สุ่มใน containerlab + วัดผลกระทบต่อแอปอัตโนมัติ

---

## Level 94 — Capacity Planning, Cost & Vendor Management

**สิ่งที่ต้องรู้**
- Baseline + trend + forecast, upgrade trigger (เช่น 95th > 70%)
- TCO: CAPEX + OPEX (license, support, power, คน), subscription model
- Lifecycle: EoS/EoL, refresh cycle 5–7 ปี, support contract (SmartNet ฯลฯ)
- RFP/RFI/RFQ, POC, evaluation matrix (weighted scoring)
- SLA และ penalty กับ ISP/vendor

**แบบทดสอบ**
1. CAPEX vs OPEX
2. ทำไมต้องติดตาม EoL
3. evaluation matrix ทำอย่างไร
4. upgrade trigger ที่เหมาะสมควรตั้งจากอะไร
5. POC ควรมีเกณฑ์อะไร

<details><summary>เฉลย</summary>

1. CAPEX = ลงทุนซื้อสินทรัพย์; OPEX = ค่าใช้จ่ายดำเนินงานต่อเนื่อง
2. ไม่มี patch security/support → ความเสี่ยงและ compliance
3. กำหนดเกณฑ์ + น้ำหนัก → ให้คะแนนแต่ละ vendor → รวมคะแนนถ่วงน้ำหนัก
4. แนวโน้มการใช้ + lead time จัดซื้อ (เช่น ถึง 70% ภายในกี่เดือน)
5. Success criteria วัดผลได้, test cases, ระยะเวลา, ผู้รับผิดชอบ
</details>

**5 โปรเจค**
- ⭐⭐ P1: ทำ EoL report ของอุปกรณ์ใน inventory (สคริปต์ + ตาราง)
- ⭐⭐ P2: TCO 5 ปี เปรียบเทียบ 2 ทางเลือก (on-prem firewall vs SASE)
- ⭐⭐ P3: เขียน RFP สำหรับ Wi-Fi refresh
- ⭐⭐⭐ P4: Forecast bandwidth 12 เดือนจากข้อมูล monitoring
- ⭐⭐ P5: Evaluation matrix + POC plan สำหรับ NGFW 3 ยี่ห้อ

---

## Level 95 — Change Management, ITIL & Documentation

**สิ่งที่ต้องรู้**
- ITIL 4: Incident, Problem, Change, Configuration (CMDB), Service Request
- Change types: Standard, Normal (CAB), Emergency
- Change plan: scope, risk, impact, implementation steps, verification, **rollback plan**, communication
- Maintenance window, `reload in 10` / `commit confirmed`
- เอกสาร: diagram, IP plan, runbook, SOP, as-built, knowledge base
- Blameless postmortem culture

**แบบทดสอบ**
1. Standard change คืออะไร
2. องค์ประกอบสำคัญที่สุดของ change plan ที่มักถูกลืม
3. `commit confirmed` (Junos) / `reload in` ช่วยอะไร
4. Incident vs Problem
5. เอกสาร as-built คืออะไร

<details><summary>เฉลย</summary>

1. Change ความเสี่ยงต่ำ ทำซ้ำบ่อย อนุมัติล่วงหน้า (pre-approved)
2. Rollback plan + verification steps
3. ถ้าแก้ผิดจนตัวเองหลุด อุปกรณ์จะ rollback/reload อัตโนมัติ
4. Incident = เหตุขัดข้องที่ต้องกู้ด่วน; Problem = สาเหตุที่แท้จริงของ incident (ป้องกันซ้ำ)
5. เอกสารสภาพที่ติดตั้งจริงหลังโปรเจคเสร็จ
</details>

**5 โปรเจค**
- ⭐ P1: Change request template + ตัวอย่าง (เพิ่ม VLAN, upgrade firmware)
- ⭐⭐ P2: Runbook 10 งานประจำ (เพิ่ม user VPN, เปลี่ยน cert, upgrade switch)
- ⭐⭐ P3: Upgrade IOS ใน lab ตาม change plan จริง (pre-check, backup, upgrade, post-check, rollback test)
- ⭐⭐ P4: Wiki เอกสารเครือข่าย lab (MkDocs/BookStack) ครบ L1–L3
- ⭐⭐⭐ P5: Postmortem template + ฝึกเขียนจากเหตุการณ์จำลอง

---

## Level 96 — Multicast

**สิ่งที่ต้องรู้**
- Multicast address 224.0.0.0/4, SSM 232/8, ff00::/8; IP → MAC mapping (01:00:5E + 23 บิต)
- IGMP v2/v3 (host ↔ router), IGMP snooping (switch), MLD (IPv6)
- PIM Dense mode vs Sparse mode (RP, shared tree/RPT vs SPT), PIM-SSM
- RPF check
- Use case: IPTV, ตลาดหุ้น, video surveillance, software imaging, financial feeds

**แบบทดสอบ**
1. IGMP snooping ช่วยอะไร
2. RPF check คืออะไร
3. PIM-SM ต้องมีอะไรที่ PIM-SSM ไม่ต้อง
4. ทำไม multicast 32 กลุ่มอาจ map เป็น MAC เดียวกัน
5. IGMPv3 เพิ่มอะไร

<details><summary>เฉลย</summary>

1. ส่ง multicast เฉพาะพอร์ตที่มีผู้สมัคร แทนการ flood
2. ตรวจว่า multicast เข้ามาจาก interface ที่ unicast route กลับไปหา source → ป้องกัน loop
3. Rendezvous Point (RP)
4. map เฉพาะ 23 บิตล่าง (5 บิตหายไป) → 2^5 = 32
5. Source-specific join (include/exclude source) รองรับ SSM
</details>

**5 โปรเจค**
- ⭐⭐ P1: Multicast ใน LAN: VLC stream + IGMP snooping (ดูผลก่อน/หลัง)
- ⭐⭐⭐ P2: PIM-SM 4 router + static RP
- ⭐⭐⭐ P3: PIM-SSM + IGMPv3
- ⭐⭐ P4: Python multicast sender/receiver + วัด loss
- ⭐⭐⭐ P5: ออกแบบ IPTV สำหรับโรงแรม 300 ห้อง (multicast end-to-end)

---

## Level 97 — MPLS & Segment Routing (Service Provider)

**สิ่งที่ต้องรู้**
- MPLS label (20 บิต), LSR/LER, push/swap/pop, PHP, LDP
- L3VPN: VRF, RD, RT, MP-BGP VPNv4, PE/P/CE
- L2VPN: VPWS, VPLS, EVPN
- Traffic Engineering: RSVP-TE → Segment Routing (SR-MPLS, SRv6), TI-LFA
- IS-IS (IGP ที่ SP นิยม)

**แบบทดสอบ**
1. RD กับ RT ต่างกันอย่างไร
2. PHP คืออะไร
3. Segment Routing ดีกว่า RSVP-TE อย่างไร
4. VRF ทำหน้าที่อะไร
5. P router ต้องรู้ route ของลูกค้าหรือไม่

<details><summary>เฉลย</summary>

1. RD ทำให้ prefix ไม่ซ้ำกันใน BGP; RT ควบคุมว่า VRF ไหน import/export route
2. Penultimate Hop Popping — router ก่อนสุดท้ายถอด label ลดงาน egress
3. ไม่ต้องเก็บ state ต่อ tunnel ใน core, ใช้ IGP กระจาย label, TI-LFA
4. แยก routing table หลายชุดบน router เดียว
5. ไม่ — รู้แค่ label/route ไป PE loopback
</details>

**5 โปรเจค**
- ⭐⭐ P1: MPLS LDP core 4 router (IS-IS underlay)
- ⭐⭐⭐ P2: L3VPN 2 ลูกค้า IP ซ้ำกัน
- ⭐⭐⭐ P3: EVPN VPWS/ELAN บน SR Linux หรือ XRd
- ⭐⭐⭐ P4: SR-MPLS + TI-LFA วัดเวลา failover
- ⭐⭐⭐ P5: ออกแบบเครือข่าย ISP ระดับจังหวัด (core/aggregation/access + services)

---

## Level 98 — Networking for AI / HPC Data Centers

**สิ่งที่ต้องรู้**
- AI training traffic: east-west หนัก, collective ops (all-reduce), elephant flows, sync → tail latency สำคัญ
- RDMA, RoCEv2 (RDMA over UDP 4791), InfiniBand, Ultra Ethernet
- Lossless Ethernet: PFC, ECN, DCQCN; ปัญหา PFC deadlock/storm
- Rail-optimized topology, 400G/800G, non-blocking fabric (1:1)
- GPU/NIC: GPUDirect RDMA, SmartNIC/DPU
- Load balancing: ECMP polarization กับ flow ใหญ่ → adaptive routing, packet spraying

**แบบทดสอบ**
1. ทำไม AI cluster ต้องการ fabric non-blocking
2. RoCEv2 ใช้ protocol/port อะไร
3. PFC ทำงานอย่างไร และความเสี่ยงคือ
4. ECN ช่วย RoCE อย่างไร
5. ทำไม ECMP ปกติไม่เหมาะกับ AI traffic

<details><summary>เฉลย</summary>

1. GPU ทุกตัวต้องคุยพร้อมกัน ตัวที่ช้าที่สุดกำหนดความเร็วทั้งงาน
2. UDP 4791
3. ส่ง pause frame ต่อ priority เมื่อ buffer ใกล้เต็ม; เสี่ยง head-of-line blocking/deadlock/pause storm
4. แจ้ง congestion ล่วงหน้าให้ผู้ส่งลดอัตรา (DCQCN) ก่อนต้อง PFC
5. flow ใหญ่น้อยตัว (low entropy) → hash ชนกันลงลิงก์เดียว
</details>

**5 โปรเจค**
- ⭐⭐ P1: สรุป whitepaper AI fabric (NVIDIA, Arista, Meta) เป็นภาษาไทย
- ⭐⭐⭐ P2: Lab Soft-RoCE (rdma_rxe) บน 2 Linux VM + `ib_write_bw`
- ⭐⭐⭐ P3: ออกแบบ fabric 256 GPU (rail-optimized) + BOM
- ⭐⭐⭐ P4: Simulation ECMP collisions ของ elephant flows (Python) vs packet spraying
- ⭐⭐⭐ P5: ตั้งค่า QoS PFC/ECN บน SONiC หรือ cEOS (lab) + เอกสาร

---

## Level 99 — Career Path, Certifications & Interview

**สิ่งที่ต้องรู้**
- เส้นทางอาชีพ: Helpdesk → NOC → Network Admin → Network Engineer → Senior → Architect / แยกสาย Security, Cloud, Automation, SP, Wireless, Pre-sales
- Certifications:
  - เริ่มต้น: CompTIA Network+, Cisco CCNA, Juniper JNCIA
  - กลาง: CCNP Enterprise/Security, JNCIP, Fortinet NSE 4–7 / FCP–FCSS, Palo Alto PCNSE, AWS Advanced Networking, Aruba ACP/ACMP
  - สูง: CCIE / JNCIE, CCDE
  - Automation: Cisco DevNet / CCNP Automation
- Portfolio: GitHub (labs/scripts จากทุก Tier), blog, homelab
- สัมภาษณ์: subnetting, OSI, "พิมพ์ URL แล้วเกิดอะไรขึ้น", STP, OSPF neighbor, BGP selection, troubleshooting scenario, STAR method

**แบบทดสอบ (คำถามสัมภาษณ์จริง)**
1. อธิบาย TCP vs UDP พร้อมตัวอย่าง
2. ผู้ใช้บอก "เน็ตช้า" คุณจะทำอะไรบ้าง
3. เล่าประสบการณ์ที่เคยทำ change แล้วพัง (STAR)
4. VLAN กับ subnet ต่างกันอย่างไร
5. ทำไมควรจ้างคุณแทนคนที่มี cert มากกว่า

<details><summary>แนวคำตอบ</summary>

1. TCP reliable/ordered (web, SSH, DB); UDP เร็ว ไม่ retransmit (DNS, VoIP, streaming, QUIC)
2. ถามรายละเอียด (ใคร/แอปไหน/เมื่อไร) → วัด (speedtest, ping/mtr, latency ไป GW และปลายทาง) → ดู utilization/errors บน path → Wi-Fi RSSI/channel → DNS → แยกปัญหา local/WAN/ปลายทาง
3. Situation, Task, Action, Result + สิ่งที่เรียนรู้ (เช่น ต้องมี rollback plan)
4. VLAN = แบ่ง broadcast domain ที่ L2; subnet = แบ่ง address ที่ L3 (ปกติจับคู่ 1:1)
5. ใช้ portfolio/โปรเจคจริงจาก roadmap นี้ แสดงทักษะ troubleshoot + automation + การสื่อสาร
</details>

**5 โปรเจค**
- ⭐ P1: CV + LinkedIn ที่เน้นโปรเจคจาก roadmap นี้
- ⭐⭐ P2: GitHub portfolio รวม 20 โปรเจคเด่น พร้อม README + diagram
- ⭐⭐ P3: Mock interview 3 รอบกับเพื่อน/รุ่นพี่ (บันทึก feedback)
- ⭐⭐ P4: แผนสอบ cert 12 เดือน (CCNA → specialization) + ตารางอ่านหนังสือ
- ⭐⭐⭐ P5: เขียน blog 10 บทความจาก lab ที่ทำ (สอนคนอื่น = เข้าใจจริง)

---

## Level 100 — Final Capstone: Enterprise Network End-to-End

**โจทย์:** บริษัท "ThaiTech Co." (สมมติ) มีพนักงาน 1,500 คน — HQ กรุงเทพ (5 ชั้น + data center เล็ก), 4 สาขา (เชียงใหม่ ขอนแก่น ชลบุรี หาดใหญ่), ใช้ AWS สำหรับแอปลูกค้า, มีโรงงาน 1 แห่ง (OT), ต้องรองรับ remote work 40%

**ต้องส่งมอบ**
1. Requirements document + assumptions
2. HLD: topology, design decisions (ADR), security zones
3. LLD: IP plan (IPv4+IPv6), VLAN, routing (OSPF/BGP), WAN/SD-WAN, Wi-Fi, firewall policy matrix, QoS, AAA/802.1X, DNS/DHCP, NTP/logging/monitoring
4. Lab implementation (containerlab/EVE-NG) ย่อส่วน: HQ + 2 สาขา + cloud VPC
5. Automation: NetBox เป็น SoT, Ansible/Nornir deploy, CI ด้วย Batfish
6. Monitoring: Grafana dashboard + alert
7. Security: IDS, SIEM, IR playbook
8. HA/DR test report (failover 10 กรณี)
9. BOM + TCO 5 ปี
10. Presentation 20 นาทีต่อ "ผู้บริหาร" และ "ทีมเทคนิค"

**แบบทดสอบสุดท้าย (Self-review checklist)**
1. ทุก single point of failure ถูกระบุและมีแผนรองรับ?
2. Policy matrix ทดสอบอัตโนมัติได้ครบ?
3. ทุก config อยู่ใน Git และ deploy ซ้ำได้?
4. ถ้าลิงก์ ISP หลักขาด ผู้ใช้สังเกตเห็นภายในกี่วินาที?
5. คนใหม่อ่านเอกสารแล้ว troubleshoot ได้ภายใน 1 วัน?

**5 โปรเจค (แบ่ง Capstone เป็น 5 ส่วน)**
- ⭐⭐⭐ P1: Design (Requirements + HLD + LLD + ADR)
- ⭐⭐⭐ P2: Build (lab implementation + automation pipeline)
- ⭐⭐⭐ P3: Secure (firewall, 802.1X, IDS, SIEM, pentest ตัวเอง)
- ⭐⭐⭐ P4: Operate (monitoring, runbooks, change process, DR test)
- ⭐⭐⭐ P5: Present (BOM/TCO, executive deck, technical demo, retrospective)

🎓 **จบ Level 100** — ถ้าทำครบ คุณมี portfolio ระดับที่ใช้สมัครงาน Network/Cloud/Security Engineer ได้จริง
