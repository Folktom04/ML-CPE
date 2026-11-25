# บทเรียน Level 94 — Capacity Planning, Cost & Vendor Management (ฉบับละเอียด)

> อ่านจบแล้วจะ: วางแผน capacity (baseline → trend → forecast → upgrade trigger) · คำนวณ lead time · ประเมิน TCO (CAPEX/OPEX) · จัดการ lifecycle (EoS/EoL, refresh) · ทำ RFI/RFP/RFQ, POC, evaluation matrix · เจรจาและจัดการ SLA กับ ISP/vendor · เขียน business case ให้ผู้บริหารเข้าใจ

---

## 1. ทำไม Network Engineer ต้องรู้เรื่องเงินและ capacity

- งบประมาณองค์กรวางแผน **ล่วงหน้า 6–12 เดือน** → ถ้ารอให้ลิงก์เต็มก่อนค่อยขอ จะช้าเกินไป
- ผู้บริหารตัดสินใจด้วย **ตัวเลขและผลกระทบทางธุรกิจ** ไม่ใช่ศัพท์เทคนิค
- วิศวกรอาวุโส/architect ถูกคาดหวังให้ **เลือกผลิตภัณฑ์อย่างมีเหตุผล** และควบคุมค่าใช้จ่ายได้

---

## 2. Capacity Planning

```
 ① Baseline   → ปัจจุบันใช้เท่าไร (ช่วงปกติ/ช่วงพีค)
 ② Trend      → โตเร็วแค่ไหน (% ต่อเดือน/ปี)
 ③ Forecast   → อนาคตจะถึงจุดไหนเมื่อไร (+ เหตุการณ์ธุรกิจที่รู้ล่วงหน้า)
 ④ Trigger    → ถึงระดับไหนต้องเริ่มดำเนินการ (คำนึงถึง lead time)
 ⑤ Action     → upgrade / optimize / เปลี่ยนสถาปัตยกรรม
```
### ① Baseline — วัดอะไร

| ทรัพยากร | ตัวชี้วัด |
|---|---|
| WAN/Internet | **95th percentile** in/out ต่อลิงก์ (Level 86) |
| Uplink/core | utilization + **output discards** |
| Firewall | throughput, **concurrent sessions, new connections/sec**, CPU, จำนวน VPN users |
| Wireless | client ต่อ AP, channel utilization, airtime |
| DHCP/IP | **pool utilization** ต่อ scope, IP ว่างใน subnet (NetBox — Level 89) |
| Switch ports | พอร์ตว่างต่อ IDF (รวม PoE budget) |
| Routing/TCAM | จำนวน route/MAC/ARP เทียบขีดจำกัด hardware |
| Cloud | egress GB, NAT GW, TGW (ค่าใช้จ่าย — Level 78) |

### ② ③ Trend & Forecast
```
 WAN สาขา CNX: 95th percentile 6 เดือนย้อนหลัง
   มิ.ย. 120 · ก.ค. 128 · ส.ค. 135 · ก.ย. 146 · ต.ค. 152 · พ.ย. 160 Mbps (ลิงก์ 200 Mbps)
   โตเฉลี่ย ~6% ต่อเดือน
   เดือนถัดไป: 160 × 1.06^n → ถึง 70% (140) แล้ว · ถึง 85% (170) ≈ 1 เดือน · ถึง 100% (200) ≈ 4 เดือน
```
- ใช้ linear regression / Excel FORECAST / Python (pandas, Prophet) — แต่ **ข้อมูลธุรกิจสำคัญกว่าสูตร**:
  - สาขาจะเพิ่มพนักงาน 50 คน · ย้าย file server ขึ้น SharePoint · เริ่มใช้กล้อง CCTV ส่งภาพไป cloud · เปลี่ยนเป็น VDI · M&A
- คุยกับฝ่ายธุรกิจ/แอปเป็นประจำ (capacity review รายไตรมาส)

### ④ Upgrade Trigger และ Lead Time
```
 Trigger = จุดที่ต้อง "เริ่ม" ดำเนินการ ไม่ใช่จุดที่ "ต้องเสร็จ"
 Lead time: ขออนุมัติงบ (1–2 เดือน) + จัดซื้อ (1 เดือน) + ISP ติดตั้งวงจร (1–3 เดือน, ต่างจังหวัด/ต้องลากสายใหม่นานกว่า)
          + อุปกรณ์ส่งมอบ (สัปดาห์–หลายเดือนเมื่อ supply chain ตึง)
 ถ้า lead time = 4 เดือน และลิงก์จะถึง 85% ภายใน 4 เดือน → ต้องเริ่มตอนนี้
```

| ทรัพยากร | Trigger ตัวอย่าง |
|---|---|
| WAN/Internet | 95th percentile > 70% ต่อเนื่อง หรือคาดว่าถึง 85% ภายใน lead time |
| Firewall | CPU/session > 60–70% ที่พีค (เผื่อเปิดฟีเจอร์ security เพิ่ม และ HA ต้องรับโหลดตัวเดียว) |
| DHCP scope | > 80% |
| Switch ports | ว่าง < 10–15% ต่อ IDF |
| Active-active pair | รวม > 50% (Level 93) |

### ⑤ ทางเลือกนอกจาก "ซื้อเพิ่ม"
- **Optimize:** QoS, ย้าย backup/update ไปนอกเวลา, ใช้ CDN/cache, WAN optimization, local internet breakout (SD-WAN)
- **ตรวจว่า traffic จำเป็นไหม** (flow analysis — Level 87): บางครั้งเป็นการ backup ผิดเวลา หรือ streaming ที่ไม่เกี่ยวกับงาน
- **เปลี่ยนสถาปัตยกรรม:** SaaS ตรงจากสาขาแทน backhaul ไป HQ

---

## 3. Cost — TCO (Total Cost of Ownership)

### CAPEX vs OPEX

| | **CAPEX** (Capital Expenditure) | **OPEX** (Operating Expenditure) |
|---|---|---|
| ความหมาย | ลงทุนซื้อสินทรัพย์ (คิดค่าเสื่อมหลายปี) | ค่าใช้จ่ายดำเนินงานต่อเนื่อง |
| ตัวอย่าง | ซื้อ switch, firewall, สายไฟเบอร์, งานติดตั้ง | ค่าวงจร ISP, subscription/license รายปี, support contract, cloud, ไฟฟ้า, เงินเดือน, managed service |

- แนวโน้ม: ผู้ผลิตเปลี่ยนเป็น **subscription** (license รายปีแยกจากฮาร์ดแวร์ — ถ้าไม่ต่อ บางฟีเจอร์/การจัดการหยุดทำงาน), **NaaS/managed** = OPEX ล้วน
- ฝ่ายการเงินบางองค์กรชอบ CAPEX บางแห่งชอบ OPEX — ถามก่อนเสนอ

### องค์ประกอบ TCO (5 ปี)
```
 Hardware + optics/สาย + อุปกรณ์เสริม (rack, PDU)
+ Software license / subscription (ทุกปี)
+ Support/maintenance contract (SmartNet/FortiCare/... ทุกปี)
+ Installation/professional services + migration
+ Training/certification ของทีม
+ Power + cooling + พื้นที่ rack
+ ค่าวงจร/bandwidth
+ ค่าแรงดูแล (FTE × ชั่วโมง) — มักถูกลืม แต่เป็นต้นทุนใหญ่
+ ความเสี่ยง/ค่า downtime (ถ้าเทียบทางเลือกที่ availability ต่างกัน)
− มูลค่าคงเหลือ/trade-in
```
### ตัวอย่าง: Firewall on-prem vs SASE (5 ปี, 4 สาขา + 300 remote users) — ตัวเลขสมมติ

| รายการ | On-prem NGFW (HA ที่ HQ + สาขา) | SASE/SSE (cloud) |
|---|---|---|
| Hardware | 2,400,000 | 200,000 (SD-WAN edge) |
| Subscription/security services 5 ปี | 1,800,000 | 4,500,000 |
| Support | 600,000 | รวมใน subscription |
| ติดตั้ง/migration | 300,000 | 400,000 |
| ค่าแรงดูแล (FTE) | 0.5 FTE × 5 ปี = 2,500,000 | 0.2 FTE × 5 ปี = 1,000,000 |
| **รวม** | **7,600,000** | **6,100,000** |
| ไม่ใช่ตัวเงิน | ควบคุมเอง, ข้อมูลอยู่ในองค์กร | remote user ได้ policy เดียวกัน, scale ง่าย, พึ่งผู้ให้บริการ |

→ ตัดสินใจด้วยทั้งตัวเลขและ **ความเสี่ยง/ความสามารถ/requirement** (PDPA, data residency, ทักษะทีม)

### Cost Optimization ที่ทำได้
- รวม support contract ให้หมดอายุพร้อมกัน (co-terming) → ต่อรองได้ดีขึ้น
- ตรวจ license ที่ไม่ได้ใช้ (shelfware), อุปกรณ์ที่ปลดระวางแล้วแต่ยังจ่าย support
- เทียบราคาวงจร ISP ทุก 2–3 ปี (ราคาตลาดลดลง)
- cloud: ลด cross-AZ/NAT/egress (Level 78)

---

## 4. Lifecycle Management

| คำ | ความหมาย |
|---|---|
| **EoS (End of Sale)** | หยุดขาย — ยังได้ support |
| **End of SW Maintenance** | หยุดออก bug fix |
| **End of Vulnerability/Security Support** | หยุดออก **security patch** ⚠️ |
| **EoL / LDoS (Last Date of Support)** | หมด support ทั้งหมด — ไม่มี TAC, ไม่มีอะไหล่ |

**ทำไมต้องติดตาม:**
- ไม่มี security patch → **ช่องโหว่ที่ไม่มีทางแก้** (ผู้โจมตีชอบอุปกรณ์ EoL — Level 61), **ไม่ผ่าน audit/compliance**
- อุปกรณ์เสียแล้วไม่มีอะไหล่ → MTTR ยาวมาก (Level 93)
- ฟีเจอร์ใหม่ (Wi-Fi 7, 25G, TLS 1.3 inspection) ไม่รองรับ

### Refresh Cycle
- ทั่วไป: **switch/router 5–7 ปี**, firewall 4–5 ปี (ประสิทธิภาพต้องตามภัยคุกคาม/การเข้ารหัสที่เพิ่ม), AP 4–5 ปี (มาตรฐาน Wi-Fi ใหม่)
- วางแผน **refresh แบบกระจาย** (ไม่ให้ทุกอย่างครบกำหนดพร้อมกัน → งบก้อนใหญ่ปีเดียว)
### EoL Report (ทำอัตโนมัติได้)
```
 inventory (NetBox/สคริปต์ get_facts: model, serial, version)
   + ข้อมูล EoL จากผู้ผลิต (Cisco EoX API, ประกาศของผู้ผลิตอื่น, endoflife.date)
   → ตาราง: อุปกรณ์ / รุ่น / วัน EoS / วันหมด security / LDoS / จำนวน / site / งบประมาณที่ต้องเตรียม (ต่อปี)
```

---

## 5. การจัดหา: RFI → RFP → RFQ → POC

| เอกสาร | ใช้เมื่อ | เนื้อหา |
|---|---|---|
| **RFI** (Request for Information) | ยังไม่รู้ว่าตลาดมีอะไร | "เล่าให้ฟังว่าผลิตภัณฑ์คุณทำอะไรได้" |
| **RFP** (Request for Proposal) ⭐ | รู้ requirement แล้ว ต้องการข้อเสนอ solution | requirement (must/should), ขอบเขตงาน, SLA, เงื่อนไข, เกณฑ์การประเมิน, กำหนดเวลา |
| **RFQ** (Request for Quotation) | รู้แน่นอนว่าต้องการอะไร (รุ่น/จำนวน) | ขอราคา |
| (หน่วยงานรัฐ) TOR | ตามระเบียบจัดซื้อจัดจ้างภาครัฐ | spec ต้องไม่ล็อกยี่ห้อ ฯลฯ |

### RFP ที่ดี
- requirement **วัดได้และไม่ล็อกยี่ห้อ** (เขียนจาก requirement — Level 92 ไม่ใช่ copy datasheet ของยี่ห้อที่ชอบ)
- แยก **mandatory** (ไม่ผ่าน = ตกรอบ) vs **desirable** (ให้คะแนน)
- ขอ **ราคาแยกรายการ** (hardware, license แต่ละปี, support, services) + ราคาปีที่ 4–5 (กันราคาต่ออายุพุ่ง)
- ขอ reference ลูกค้า, แผนการติดตั้ง, ทีมงาน, SLA ของ support (เวลาตอบสนอง/อะไหล่)

### Evaluation Matrix (Weighted Scoring)

| เกณฑ์ | น้ำหนัก | Vendor A | Vendor B | Vendor C |
|---|---|---|---|---|
| ตรง requirement ทางเทคนิค | 30% | 9 → 2.7 | 7 → 2.1 | 8 → 2.4 |
| TCO 5 ปี | 25% | 6 → 1.5 | 9 → 2.25 | 7 → 1.75 |
| ผล POC | 20% | 8 → 1.6 | 6 → 1.2 | 8 → 1.6 |
| Support/partner ในประเทศ | 15% | 9 → 1.35 | 6 → 0.9 | 7 → 1.05 |
| ความง่ายในการดูแล/ทักษะทีม | 10% | 8 → 0.8 | 7 → 0.7 | 6 → 0.6 |
| **รวม** | 100% | **7.95** | **7.15** | **7.40** |

- **กำหนดเกณฑ์และน้ำหนักก่อนเห็นข้อเสนอ** (กันอคติ) · ให้คะแนนหลายคนแล้วเฉลี่ย · บันทึกเหตุผล

### POC (Proof of Concept)
- **Success criteria ที่วัดได้** ตกลงล่วงหน้า (เช่น "throughput ≥ 2 Gbps เมื่อเปิด IPS + SSL inspection ด้วย traffic mix ของเรา", "failover HA < 3 วินาที", "integrate กับ AD/SIEM ได้")
- test cases + ระยะเวลา (2–4 สัปดาห์) + ผู้รับผิดชอบ + **ใช้ traffic/use case จริงขององค์กร**
- ระวัง POC ที่ผู้ขายตั้งค่าให้ทั้งหมด → ทีมเราต้องลงมือเองด้วยเพื่อประเมินความง่ายในการใช้งาน

---

## 6. Vendor & ISP Management

### SLA ที่ต้องอ่านให้ละเอียด

| หัวข้อ | ตรวจ |
|---|---|
| **Availability** | % ต่อเดือน, วัดอย่างไร, ไม่นับ planned maintenance? |
| **MTTR/เวลาซ่อม** | 4 ชั่วโมง? ต่างจังหวัด 8 ชั่วโมง? นับจากเมื่อไร |
| **Latency/loss/jitter** (MPLS/วงจรเช่า) | วัดระหว่างจุดไหน |
| **Penalty/service credit** | ได้คืนเท่าไรเมื่อไม่ถึง (มักน้อยกว่าความเสียหายจริงมาก) |
| **Support** | 24×7? ช่องทาง? escalation matrix? |
| **อะไหล่** (vendor) | NBD (next business day) vs 4 ชั่วโมง |

> SLA ไม่ได้ป้องกันเหตุ — แค่ชดเชยบางส่วน **design ต้องรองรับความล้มเหลวเอง** (ISP คู่ — Level 93)

### การจัดการความสัมพันธ์
- **Quarterly business review** กับ vendor/ISP: ทบทวน incident, SLA, roadmap
- ติดตาม **ticket ที่ค้าง** และ escalation path (account manager, duty manager)
- เก็บข้อมูลเชิงตัวเลข (จำนวนเหตุขัดข้อง, เวลาซ่อม) ไว้ใช้ต่อรองตอนต่อสัญญา
- **Vendor risk:** ผู้ผลิตถูกซื้อกิจการ/เลิกสายผลิตภัณฑ์, ช่องโหว่ร้ายแรงซ้ำ ๆ, supply chain — มีแผนสำรอง
- **Lock-in:** ใช้มาตรฐานเปิด (BGP, EVPN, OpenConfig, SAML) ลดการผูกขาด

---

## 7. Business Case — สื่อสารกับผู้บริหาร

```
 ❌ "ขอเปลี่ยน core switch เพราะเป็นรุ่น EoL และ CPU สูง"
 ✅ "Core switch ของ HQ จะหมดการออก security patch ใน มี.ค. ปีหน้า
     ความเสี่ยง: ช่องโหว่ที่แก้ไม่ได้ + ไม่ผ่าน audit ISO 27001
     ถ้าเสีย ไม่มีอะไหล่ → ระบบขายหยุด ~2 วัน (ประมาณการความเสียหาย 3.5 ล้านบาท/วัน)
     ทางเลือก: A) เปลี่ยนทั้งหมด 4.2 ล้าน  B) เปลี่ยนแบบ phase 2 ปี 4.5 ล้าน  C) ไม่ทำ (รับความเสี่ยง)
     แนะนำ A: ติดตั้งเสร็จใน Q1 พร้อมรองรับ 25G สำหรับระบบใหม่ที่ฝ่าย IT วางแผนไว้"
```
**โครงสร้าง:** ปัญหา/โอกาส → ผลกระทบทางธุรกิจ (เงิน/ความเสี่ยง/ลูกค้า) → ทางเลือก (รวม "ไม่ทำ") พร้อมต้นทุน/ประโยชน์ → ข้อเสนอแนะ → timeline → ตัวชี้วัดความสำเร็จ
**ใช้ภาษาธุรกิจ:** เวลาหยุดชะงัก, ความเสี่ยง, compliance, ประสิทธิภาพพนักงาน, ประสบการณ์ลูกค้า, ROI/payback

---

## 8. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| ขอ upgrade เมื่อลิงก์เต็มแล้ว | ต้องเริ่มก่อนตาม lead time |
| ราคาถูกที่สุดคือดีที่สุด | ดู TCO 5 ปี + ความเสี่ยง + ค่าแรงดูแล |
| อุปกรณ์ EoL ยังใช้ได้ไม่มีปัญหา | ไม่มี security patch/อะไหล่ — ความเสี่ยงและ compliance |
| SLA 99.9% ของ ISP = ไม่ต้องมีสำรอง | SLA ชดเชยบางส่วน ไม่ได้ป้องกัน downtime |
| POC ให้ vendor ทำทั้งหมดก็พอ | ใช้ use case/traffic ของเราและทีมเราต้องลงมือ |

---

## 9. Cheat Sheet

```
Capacity: baseline (95th, discards, sessions, DHCP, ports, TCAM) → trend → forecast (+ข้อมูลธุรกิจ) → trigger → action
Trigger คำนึง lead time (อนุมัติ + จัดซื้อ + ISP + ส่งมอบ) · WAN 70% · FW 60-70% · DHCP 80% · A-A 50%
Optimize ก่อนซื้อ: QoS, schedule, CDN, local breakout, flow analysis
TCO = HW + license/subscription + support + services + training + power/space + circuit + FTE − residual
CAPEX (ซื้อสินทรัพย์) vs OPEX (ต่อเนื่อง) · subscription/NaaS
Lifecycle: EoS → end SW maint → end security → LDoS · refresh 5-7 ปี (FW/AP 4-5) · EoL report อัตโนมัติ
RFI → RFP (must/should, ไม่ล็อกยี่ห้อ, ราคาแยก) → RFQ · evaluation matrix (กำหนดน้ำหนักก่อน) · POC (success criteria)
SLA: availability, MTTR, penalty, support · QBR · lock-in → มาตรฐานเปิด
Business case: ปัญหา → ผลกระทบธุรกิจ → ทางเลือก (+ไม่ทำ) → แนะนำ → timeline → KPI
```

---

## 10. แบบทดสอบ 10 ข้อ

1. ขั้นตอนของ capacity planning มีอะไรบ้าง
2. ลิงก์ 200 Mbps ตอนนี้ 95th percentile = 150 Mbps โต 5%/เดือน lead time 4 เดือน ควรเริ่มดำเนินการหรือยัง
3. นอกจากซื้อ bandwidth เพิ่ม มีทางเลือกอะไรอีก (3 ข้อ)
4. CAPEX กับ OPEX ต่างกันอย่างไร ยกตัวอย่าง
5. TCO มีองค์ประกอบอะไรที่มักถูกลืม
6. ทำไมต้องติดตาม End of Security Support
7. RFI, RFP, RFQ ใช้ต่างกันอย่างไร
8. Evaluation matrix ทำอย่างไรให้ยุติธรรม
9. POC ที่ดีต้องมีอะไร
10. เขียน business case ให้ผู้บริหารควรมีโครงสร้างอย่างไร

<details><summary><b>เฉลย</b></summary>

1. Baseline → trend → forecast (รวมข้อมูลธุรกิจ) → upgrade trigger (คำนึง lead time) → action (upgrade/optimize/เปลี่ยนสถาปัตยกรรม)
2. ควรเริ่มทันที — 150 = 75% แล้ว และภายใน 4 เดือนจะเป็น ~150×1.05⁴ ≈ 182 Mbps (91%) ก่อนวงจรใหม่มาถึง
3. QoS, ย้าย backup/update ไปนอกเวลา, CDN/cache, local internet breakout (SD-WAN), ตรวจ flow ตัด traffic ที่ไม่จำเป็น
4. CAPEX = ลงทุนซื้อสินทรัพย์ (switch, firewall, สาย); OPEX = ค่าใช้จ่ายต่อเนื่อง (วงจร ISP, subscription, support, cloud, เงินเดือน)
5. ค่าแรงดูแล (FTE), license/subscription รายปีในปีที่ 4–5, training, power/cooling/พื้นที่, migration
6. หลังวันนั้นไม่มี patch ช่องโหว่ — เสี่ยงถูกโจมตีโดยแก้ไม่ได้ และไม่ผ่าน audit/compliance
7. RFI ขอข้อมูลสำรวจตลาด; RFP ขอข้อเสนอ solution ตาม requirement; RFQ ขอราคาเมื่อรู้ spec/จำนวนแน่นอน
8. กำหนดเกณฑ์และน้ำหนักก่อนเห็นข้อเสนอ ให้คะแนนหลายคนแล้วเฉลี่ย บันทึกเหตุผล
9. Success criteria ที่วัดได้ตกลงล่วงหน้า, test cases ด้วย traffic/use case จริง, ระยะเวลา, ผู้รับผิดชอบ, ทีมเราลงมือใช้งานเอง
10. ปัญหา/โอกาส → ผลกระทบทางธุรกิจ (เงิน/ความเสี่ยง) → ทางเลือกพร้อมต้นทุน/ประโยชน์ (รวมการไม่ทำ) → ข้อเสนอแนะ → timeline → ตัวชี้วัดความสำเร็จ
</details>

---

➡️ ต่อไป: **Level 95 — Change Management, ITIL & Documentation**
