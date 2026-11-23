# บทเรียน Level 92 — Network Design Methodology (ฉบับละเอียด)

> อ่านจบแล้วจะ: ออกแบบเครือข่ายเป็นกระบวนการ (ไม่ใช่เริ่มจากเลือกยี่ห้อ) · เก็บ requirements (business/technical/constraints) · ใช้ top-down design และ lifecycle (PPDIOO/Plan-Build-Manage) · เขียน HLD และ LLD · ใช้หลักการออกแบบ (modularity, hierarchy, redundancy, simplicity, security) · ชั่งน้ำหนัก trade-off · เขียน ADR · ทำ design review

---

## 1. Design คืองานแปล "ความต้องการธุรกิจ" เป็น "เครือข่าย"

```
 ❌ "ซื้อ Cisco 9300 มา 20 ตัว แล้วค่อยคิดว่าจะใช้ยังไง"
 ✅ "ธุรกิจต้องการอะไร → เครือข่ายต้องทำอะไรได้ → สถาปัตยกรรม → เทคโนโลยี → ผลิตภัณฑ์"
```
**Top-down design:** เริ่มจาก **ชั้นบน (ธุรกิจ/แอป/ผู้ใช้)** ลงมาหา **ชั้นล่าง (เทคโนโลยี/อุปกรณ์)** — ไม่ใช่เริ่มจากอุปกรณ์ที่ชอบ

### Lifecycle
| Cisco PPDIOO (คลาสสิก) | ความหมาย |
|---|---|
| **P**repare | business case, งบ, กลยุทธ์ |
| **P**lan | requirements, gap analysis (เครือข่ายปัจจุบันขาดอะไร) |
| **D**esign | HLD, LLD |
| **I**mplement | ติดตั้งตาม plan + ทดสอบ |
| **O**perate | ดูแลประจำวัน, monitoring |
| **O**ptimize | ปรับปรุงจากข้อมูลจริง → วนกลับไป plan |
(ปัจจุบันมักเรียกย่อ: **Plan → Build → Manage**)

---

## 2. Requirements Gathering

### 3 กลุ่ม
| กลุ่ม | ตัวอย่างคำถาม |
|---|---|
| **Business** | เป้าหมายธุรกิจ (ขยายสาขา? ย้ายขึ้น cloud? ทำงานจากที่ไหนก็ได้?), แอปที่สร้างรายได้, ต้นทุน downtime ต่อชั่วโมง, แผน 3–5 ปี, กฎหมาย/compliance (PDPA, PCI DSS, ISO 27001, มาตรฐานของ ธปท./คปภ./กระทรวงสาธารณสุข) |
| **Technical** | ผู้ใช้/อุปกรณ์กี่ราย (โต % ต่อปี), แอป + ลักษณะ traffic (real-time? bulk?), availability ที่ต้องการ (SLA), performance (latency/bandwidth), security (zone, ใครเข้าถึงอะไร), manageability, IPv6, wireless density, IoT/OT |
| **Constraints** | **งบประมาณ** (CAPEX/OPEX), **เวลา** (ต้องเสร็จก่อนเปิดสาขา), **ทักษะทีม**, อุปกรณ์/สัญญาเดิม, นโยบายผู้ผลิต, อาคาร (ท่อ, ห้อง, ไฟ, แอร์), ผู้ให้บริการที่มีในพื้นที่ |

### เทคนิคการเก็บข้อมูล
- **สัมภาษณ์** stakeholder: ผู้บริหาร (เป้าหมาย/งบ), เจ้าของแอป, ทีม IT/security, ผู้ใช้หลัก (ปัญหาปัจจุบัน)
- **Site survey:** ห้อง server/IDF, เส้นทางสาย, ไฟฟ้า/UPS, Wi-Fi survey (Level 52)
- **ข้อมูลเครือข่ายปัจจุบัน:** inventory, diagram, config, monitoring/flow (traffic จริง — Level 86/87), ticket ที่พบบ่อย
- **Workshop** สรุป requirement + ลำดับความสำคัญ (Must/Should/Could/Won't — MoSCoW)

### เขียน requirement ให้วัดได้
| ❌ คลุมเครือ | ✅ วัดได้ |
|---|---|
| "เครือข่ายต้องเร็ว" | "latency ไป ERP จากสาขา ≤ 30 ms (95th percentile)" |
| "ต้อง HA" | "ไม่มี single point of failure ที่ core/WAN ของ HQ; availability ≥ 99.95%/เดือน; failover ≤ 3 วินาที" |
| "ปลอดภัย" | "Guest แยกจาก corporate 100%; อุปกรณ์ต้องผ่าน 802.1X; log เก็บ 90 วัน (ตาม พ.ร.บ.คอมฯ)" |

### Assumptions และ Risks
บันทึกสิ่งที่ "สมมติ" ไว้ (เช่น "ISP สาขาให้ได้ 500 Mbps ภายใน 30 วัน") — ถ้าผิด design ต้องปรับ

---

## 3. HLD vs LLD

| | **HLD (High-Level Design)** | **LLD (Low-Level Design)** |
|---|---|---|
| ผู้อ่าน | ผู้บริหาร, architect, ผู้อนุมัติ | วิศวกรที่ติดตั้ง/ดูแล |
| ตอบ | **ทำอะไร และทำไม** | **ทำอย่างไร** (ละเอียดพอให้คนอื่นติดตั้งได้) |
| เนื้อหา | สถาปัตยกรรมภาพรวม, topology logical, zone ความปลอดภัย, เทคโนโลยีที่เลือก + เหตุผล, HA/DR concept, การเชื่อม cloud/WAN | **IP plan, VLAN, ชื่ออุปกรณ์, port mapping, routing (area, ASN, policy), firewall rule matrix, QoS class, SSID/การตั้งค่า Wi-Fi, config template**, cable schedule, rack elevation |
| ตัวอย่าง | "ใช้ SD-WAN ต่อ 4 สาขา dual ISP, local internet breakout ผ่าน SSE" | "สาขา CNX: ISP1 PPPoE 1G/500M, ISP2 DIA 300M, tunnel ไป HQ hub 2 ตัว, BGP AS 65102, prefix 10.12.0.0/16..." |

### โครงสร้าง HLD ที่แนะนำ
```
 1. Executive summary
 2. Business & technical requirements (สรุป) + constraints + assumptions
 3. Current state & gaps
 4. Target architecture (diagram) — campus, DC, WAN, internet edge, cloud, remote access
 5. Design decisions (ADR) — ทางเลือกและเหตุผล
 6. Security architecture — zones, trust boundaries, identity
 7. Availability/DR — failure domains, redundancy
 8. Management & operations — monitoring, automation, AAA
 9. Migration approach (phase), risks
 10. BOM ระดับสูง + ประมาณการ TCO (Level 94)
```

---

## 4. หลักการออกแบบ (Design Principles)

| หลักการ | ความหมาย | ตัวอย่าง |
|---|---|---|
| **Hierarchy** | แบ่งชั้นตามหน้าที่ | access–distribution–core (Level 40), spine-leaf |
| **Modularity** | แบ่งเป็นบล็อกที่ทำซ้ำได้ | "สาขาขนาด S/M/L" เป็น template, building block ของ DC (pod) |
| **Redundancy** | ไม่มี single point of failure ในจุดสำคัญ | dual core, dual ISP, dual PSU (Level 93) |
| **Simplicity** ⭐ | เลือกสิ่งที่ง่ายที่สุดที่ตอบ requirement | ไม่ใช้ protocol/feature ที่ไม่จำเป็น |
| **Scalability** | โตได้โดยไม่ต้องออกแบบใหม่ | IP plan เผื่อ, summarization, เพิ่ม leaf ได้ |
| **Security by design** | segmentation, least privilege, zero trust ตั้งแต่ต้น | zone, 802.1X, management plane แยก (Tier 7) |
| **Manageability** | ดูแลง่าย มองเห็น | naming standard, automation-ready, telemetry |
| **Standardization** | มาตรฐานเดียวกันทั่วองค์กร | template config, รุ่นอุปกรณ์จำกัด |
| **Failure domain ที่เล็ก** | ปัญหาหนึ่งกระทบน้อยที่สุด | L3 ที่ access/distribution, ไม่ขยาย VLAN ทั่วทั้งองค์กร |

### "Complexity is the enemy of availability"
- ทุก feature/protocol ที่เพิ่ม = จุดเสียใหม่, คนเข้าใจน้อยลง, change ผิดพลาดง่ายขึ้น, troubleshoot ช้าลง
- คำถามประจำ: "**ทีมของลูกค้าดูแลสิ่งนี้ได้ไหมตอนตี 3?**"
- RFC 1925 "The Twelve Networking Truths": *"It is always possible to add another level of indirection"* — แต่ไม่ได้แปลว่าควรทำ

---

## 5. Trade-offs — ทุกการออกแบบคือการแลก

```
          Cost
         /    \
 Availability ── Complexity     (และ Performance, Security, Time-to-deploy)
```
| การตัดสินใจ | ทางเลือก A | ทางเลือก B |
|---|---|---|
| **Build vs Buy** | สร้างเองด้วย open source (ยืดหยุ่น, ถูก, ต้องมีทักษะ) | ซื้อผลิตภัณฑ์/บริการ (เร็ว, มี support, แพง/ผูกขาด) |
| **Single vs Multi-vendor** | ยี่ห้อเดียว (บูรณาการดี, ทีมเรียนชุดเดียว, ผูกขาด/ต่อรองยาก) | หลายยี่ห้อ (ต่อรองราคา, ลดความเสี่ยงช่องโหว่เดียวกัน, interop/ทักษะหลายแบบ) |
| **On-prem vs Cloud/SaaS** | ควบคุมเอง, CAPEX | ยืดหยุ่น, OPEX, ขึ้นกับผู้ให้บริการ |
| **L2 ขยาย vs L3 routed** | ง่ายกับแอปเก่า (VM mobility) | failure domain เล็ก, scale ดี |
| **MPLS vs SD-WAN/Internet** | SLA, latency คงที่ | ราคาถูก bandwidth มาก, ต้องมี overlay ที่ดี |
| **Active-active vs Active-standby** | ใช้ทรัพยากรเต็ม | ง่าย คาดเดาได้ |
**ไม่มีคำตอบที่ถูกเสมอ** — คำตอบที่ดีคือคำตอบที่ **สอดคล้องกับ requirement และ constraint และอธิบายเหตุผลได้**

---

## 6. ADR — Architecture Decision Record

เอกสารสั้น ๆ บันทึก **การตัดสินใจสำคัญ** ทีละเรื่อง → คนในอนาคตเข้าใจว่า "ทำไมถึงเป็นแบบนี้"
```markdown
# ADR-007: ใช้ eBGP เป็น underlay ของ DC fabric
Status: Accepted (2026-11-23)
## Context
DC ใหม่ 20 rack, spine-leaf, ต้องการ EVPN-VXLAN, ทีมมีประสบการณ์ OSPF มากกว่า BGP
## Options
1. OSPF underlay + iBGP EVPN (spine เป็น RR)
2. eBGP underlay + eBGP EVPN (RFC 7938)
## Decision
เลือกตัวเลือก 2
## Rationale
- failure domain ชัดเจน, policy ต่อ leaf ได้, scale ตามแผน 5 ปี (80 rack)
- เครื่องมือ automation (Apstra/CloudVision template) รองรับดี
## Consequences
- ทีมต้องอบรม BGP (แผนอบรม Q1)
- ต้องกำหนด ASN plan (leaf 65101–65199)
```
เก็บ ADR ไว้ใน Git ร่วมกับเอกสาร design

---

## 7. เอกสารใน LLD ที่ต้องมี (Checklist)

- [ ] **IP addressing plan** (IPv4 + IPv6): supernet ต่อ site, subnet ต่อ VLAN, gateway, DHCP range, IP ของอุปกรณ์ (loopback, management, P2P)
- [ ] **VLAN/VRF plan** และ mapping กับ subnet/zone
- [ ] **Naming convention** (อุปกรณ์, interface description, SSID)
- [ ] **Physical:** rack elevation, cable schedule (A-end/B-end, port, ชนิดสาย/optic), power
- [ ] **Routing:** protocol, area/ASN, summarization, redistribution, route policy, timers/BFD
- [ ] **Switching:** STP mode/root, port-channel, port profile (access/trunk/AP/phone/printer)
- [ ] **Security:** firewall **policy matrix** (zone × zone → อนุญาตอะไร), NAT, VPN, 802.1X/NAC, port security, management plane hardening
- [ ] **QoS:** class, DSCP marking, queuing/policing ที่แต่ละจุด
- [ ] **Wireless:** SSID, security, VLAN, RF plan, AP placement
- [ ] **Services:** DNS, DHCP, NTP, AAA (TACACS+/RADIUS), syslog, SNMP, NetFlow, backup config
- [ ] **HA/failover behavior** ที่คาดหวัง + test plan
- [ ] **Config templates** (หรือ link ไป Git/NetBox)
- [ ] **Migration/cutover plan** + rollback (Level 95)

### Firewall Policy Matrix ตัวอย่าง
| From \ To | Users | Servers | DMZ | Internet | Mgmt |
|---|---|---|---|---|---|
| **Users** | — | HTTPS, RDP(IT group) | HTTPS | Web (ผ่าน SWG) | ✖ |
| **Guest** | ✖ | ✖ | ✖ | Web | ✖ |
| **Servers** | ✖ | ตาม app | ✖ | update (allowlist) | ✖ |
| **Mgmt (jump host)** | SSH | SSH/RDP | SSH | ✖ | — |

---

## 8. Design Review

ให้คนอื่นตรวจก่อนอนุมัติ — ใช้ checklist:
- requirement ทุกข้อถูกตอบหรือมีเหตุผลที่ไม่ตอบ?
- **single point of failure** ที่เหลือ? (Level 93)
- failure domain/blast radius เมื่อ X ล่ม?
- security: zone ครบ? management plane แยก? least privilege?
- scale 3–5 ปี? IP plan เผื่อพอ?
- ทีมดูแลได้? automation-ready? monitoring ครอบคลุม?
- ค่าใช้จ่ายรวม (TCO)? lead time อุปกรณ์?
- migration มีแผน rollback ทุกขั้น?
**"Pre-mortem":** สมมติว่าอีก 1 ปีโปรเจคล้มเหลว — สาเหตุน่าจะเป็นอะไร? → แก้ตั้งแต่ตอนนี้

---

## 9. ตัวอย่างย่อ: เครือข่ายโรงพยาบาล 500 เตียง

| Requirement | Design decision |
|---|---|
| ระบบ HIS/LIS/PACS ต้องพร้อมใช้ 24×7 | dual core (collapsed core + stacking/VSS-like/EVPN), dual DC room, dual ISP + DR |
| อุปกรณ์การแพทย์ (IoMT) จำนวนมาก แพตช์ไม่ได้ | segment แยก (VLAN/VRF/SGT) + NAC profiling + firewall เฉพาะ flow ที่ต้องใช้ |
| Wi-Fi สำหรับแพทย์/พยาบาลโรมมิ่งระหว่างหอผู้ป่วย, VoWiFi | WPA3-Enterprise + 802.11r/k/v, survey ความหนาแน่น, QoS voice |
| PACS (ภาพ X-ray/CT) ใหญ่มาก | 10G ถึง radiology, 25G ใน DC, storage network แยก |
| Guest/ญาติผู้ป่วย | SSID guest แยก, captive portal, rate limit, ออกเน็ตตรงไม่ผ่าน corporate |
| PDPA ข้อมูลผู้ป่วย | segmentation, encryption, log/SIEM, access control เข้ม |
| ทีม IT เล็ก | ยี่ห้อหลักน้อยราย, cloud-managed บางส่วน, template + automation พื้นฐาน |

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| ออกแบบ = เลือกยี่ห้อและรุ่น | เริ่มจาก requirement → architecture → เทคโนโลยี → ผลิตภัณฑ์ |
| ยิ่ง redundancy มากยิ่งดีเสมอ | redundancy เพิ่มความซับซ้อนและค่าใช้จ่าย — ใส่ตามความสำคัญ |
| HLD ละเอียดเท่า LLD | HLD บอก "อะไร/ทำไม", LLD บอก "อย่างไร" |
| เอกสาร design ทำครั้งเดียวจบ | ต้องอัปเดตตาม as-built และการเปลี่ยนแปลง (Level 95) |
| Design ที่ดีคือ design ที่ใช้เทคโนโลยีใหม่ที่สุด | design ที่ดีคือ design ที่ตอบ requirement ได้ง่ายที่สุดและทีมดูแลได้ |

---

## 11. Cheat Sheet

```
Top-down: business → app/user → architecture → technology → product
PPDIOO (Prepare, Plan, Design, Implement, Operate, Optimize) / Plan-Build-Manage
Requirements: business · technical · constraints (งบ เวลา ทักษะ อาคาร) · assumptions · MoSCoW · วัดได้
HLD = what/why (ผู้บริหาร) · LLD = how (IP, VLAN, routing, policy matrix, QoS, ports, cables)
Principles: hierarchy · modularity · redundancy · simplicity · scalability · security · manageability · small failure domain
Trade-offs: cost/availability/complexity · build vs buy · single vs multi-vendor · L2 vs L3
ADR: context · options · decision · rationale · consequences
Design review checklist + pre-mortem
```

---

## 12. แบบทดสอบ 10 ข้อ

1. Top-down design คืออะไร ทำไมดีกว่าเริ่มจากอุปกรณ์
2. Requirement 3 กลุ่มคืออะไร ยกตัวอย่างกลุ่มละ 1
3. เขียน requirement "เครือข่ายต้องเสถียร" ใหม่ให้วัดได้
4. HLD กับ LLD ต่างกันอย่างไร
5. ทำไม "complexity is the enemy of availability"
6. Single-vendor กับ multi-vendor มีข้อดีข้อเสียอย่างไร
7. ADR ประกอบด้วยอะไร และมีประโยชน์อย่างไร
8. Firewall policy matrix คืออะไร
9. Pre-mortem คืออะไร
10. ระบุ 5 เอกสาร/หัวข้อที่ต้องมีใน LLD

<details><summary><b>เฉลย</b></summary>

1. เริ่มจากความต้องการธุรกิจและแอปลงไปหาเทคโนโลยีและอุปกรณ์ — ทำให้ design ตอบโจทย์จริง ไม่ใช่ปรับธุรกิจให้เข้ากับอุปกรณ์
2. Business (เป้าหมายธุรกิจ, compliance), technical (จำนวนผู้ใช้, SLA, latency), constraints (งบ, เวลา, ทักษะทีม)
3. เช่น "availability ของ core/WAN HQ ≥ 99.95% ต่อเดือน ไม่มี SPOF และ failover ≤ 3 วินาที"
4. HLD บอกสถาปัตยกรรมและเหตุผล (อะไร/ทำไม) สำหรับผู้อนุมัติ; LLD บอกรายละเอียดติดตั้ง (IP, VLAN, port, policy, config) สำหรับวิศวกร
5. ความซับซ้อนเพิ่มจุดเสีย ทำให้เข้าใจยาก change ผิดพลาดง่าย และแก้ปัญหาช้า
6. Single: บูรณาการดี ทีมเรียนชุดเดียว แต่ผูกขาด/ต่อรองยาก; multi: ต่อรองราคา ลดความเสี่ยงช่องโหว่ร่วม แต่ interop และทักษะหลายแบบ
7. Context, options, decision, rationale, consequences (+status/วันที่) — บันทึกเหตุผลให้คนในอนาคตเข้าใจและไม่ถกเถียงซ้ำ
8. ตาราง zone ต้นทาง × zone ปลายทาง ระบุ traffic ที่อนุญาต ใช้เป็นข้อกำหนดของ firewall rule และทดสอบอัตโนมัติได้
9. สมมติว่าโปรเจคล้มเหลวในอนาคตแล้วหาสาเหตุที่เป็นไปได้ เพื่อแก้ไขตั้งแต่ช่วงออกแบบ
10. IP plan, VLAN/VRF plan, naming, routing design, firewall policy matrix, QoS, wireless, services (DNS/DHCP/NTP/AAA/logging), cable schedule/rack, migration plan
</details>

---

➡️ ต่อไป: **Level 93 — High Availability & Disaster Recovery**
