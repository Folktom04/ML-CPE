# บทเรียน Level 60 — SD-WAN & SASE (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจว่า SD-WAN แก้ปัญหาอะไรของ WAN แบบเดิม · สถาปัตยกรรม (controller, edge, overlay/underlay) · application-aware routing และ SLA probe · ZTP · ออกแบบ SD-WAN หลายสาขา · เข้าใจ SASE = SD-WAN + SSE (SWG, CASB, ZTNA, FWaaS) · ประเมินผู้ผลิตและวางแผนย้ายจาก MPLS

---

## 1. ปัญหาของ WAN แบบเดิม

| ปัญหา | รายละเอียด |
|---|---|
| **MPLS แพง** | ต้นทุนต่อ Mbps สูง เพิ่ม bandwidth ช้า |
| **Traffic ย้ายไป cloud** | Microsoft 365, SaaS, IaaS อยู่บนอินเทอร์เน็ต — การ backhaul ผ่าน HQ ทำให้ช้า |
| **ใช้ลิงก์สำรองไม่เต็มที่** | ลิงก์ที่ 2 รอเฉย ๆ (active/standby) |
| **Failover ช้าและไม่ฉลาด** | ลิงก์ยัง up แต่คุณภาพแย่ (loss/jitter สูง) ก็ยังใช้ต่อ |
| **จัดการยาก** | config router ทีละสาขา (CLI) เปลี่ยน policy ทั้งองค์กรต้องแก้หลายร้อยเครื่อง |
| **เปิดสาขาใหม่ช้า** | ต้องส่งวิศวกรไปตั้งค่าหน้างาน |

---

## 2. SD-WAN คืออะไร

**SD-WAN (Software-Defined WAN)** = WAN ที่ **จัดการจากศูนย์กลางด้วยซอฟต์แวร์** ใช้ **หลายลิงก์ทุกประเภทพร้อมกัน** (MPLS, broadband, DIA, 4G/5G) สร้าง **overlay tunnel ที่เข้ารหัส** และ **เลือกเส้นทางให้แต่ละแอปตามคุณภาพลิงก์แบบ real-time**

```
                    ┌──────────── Controller / Orchestrator (cloud หรือ on-prem) ────────────┐
                    │  policy กลาง · ZTP · monitoring · จัดการ key                            │
                    └───────────┬───────────────────────────┬────────────────────────────────┘
                                │ control                   │
   สาขา A [SD-WAN Edge]═══ overlay (IPsec) ═══[SD-WAN Edge/Hub] DC/HQ
            ├─ ลิงก์ 1: MPLS ─────────────┐        │
            ├─ ลิงก์ 2: Broadband ────── underlay ──┤
            └─ ลิงก์ 3: 5G (สำรอง) ───────┘        └─ Cloud/SaaS (direct breakout)
```

### องค์ประกอบ

| ส่วน | หน้าที่ |
|---|---|
| **Orchestrator/Manager** | GUI/API ตั้ง policy, template, ดูภาพรวม (Management plane) |
| **Controller** | แจกจ่าย route/policy/key ให้ edge (Control plane) |
| **Edge** | อุปกรณ์ที่สาขา/DC สร้าง tunnel และส่งต่อ traffic (Data plane) |
| **Underlay** | ลิงก์จริง (MPLS, อินเทอร์เน็ต, 4G/5G) |
| **Overlay** | tunnel เข้ารหัสที่สร้างบน underlay ทุกเส้น |

---

## 3. ความสามารถหลักของ SD-WAN

### 3.1 Application-Aware Routing ⭐
- **ระบุแอป** ด้วย DPI/signature (Teams, Zoom, Microsoft 365, SAP, YouTube …) ไม่ใช่แค่ IP/port
- **วัดคุณภาพแต่ละลิงก์ต่อเนื่อง** ด้วย **SLA probe** (latency, jitter, packet loss) ทุกไม่กี่วินาที
- **เลือกลิงก์ที่ผ่าน SLA ของแอปนั้น** และย้ายอัตโนมัติเมื่อคุณภาพตก (ก่อนลิงก์จะ down จริง)

```
 Policy ตัวอย่าง:
 - Voice/Teams: latency < 150 ms, jitter < 30 ms, loss < 1% → ใช้ลิงก์ที่ดีที่สุดที่ผ่าน SLA, สำรอง 5G
 - ERP/SAP: ผ่าน MPLS เป็นหลัก, ถ้าไม่ผ่าน SLA → broadband
 - Microsoft 365: local breakout ผ่าน broadband (ไม่ backhaul)
 - YouTube/Update: broadband เท่านั้น, จำกัด bandwidth, ห้ามใช้ 5G
```

### 3.2 ใช้ทุกลิงก์ (Active/Active) + Per-packet/Per-flow steering
บางผลิตภัณฑ์มี **FEC (Forward Error Correction)** และ **packet duplication** สำหรับ voice บนลิงก์คุณภาพต่ำ

### 3.3 Zero-Touch Provisioning (ZTP)
ส่งอุปกรณ์ไปสาขา → พนักงานหน้างานเสียบไฟและสาย → อุปกรณ์ติดต่อ orchestrator เอง (ผ่าน serial number) → ดึง config และ policy อัตโนมัติ → **เปิดสาขาได้ภายในไม่กี่ชั่วโมงโดยไม่ต้องส่งวิศวกร**

### 3.4 Centralized Policy & Visibility
เปลี่ยน policy ครั้งเดียวมีผลทุกสาขา · dashboard แสดงแอป ผู้ใช้ คุณภาพลิงก์ ทุกไซต์

### 3.5 Security ในตัว
tunnel เข้ารหัส, segmentation (VRF/VPN ต่อแผนก), NGFW ในตัว edge (บางผลิตภัณฑ์) หรือส่งต่อไปยัง cloud security (SASE)

### 3.6 Dynamic Spoke-to-Spoke
สาขาสร้าง tunnel ตรงหากันเมื่อมี traffic (เช่น Fortinet ADVPN, Cisco dynamic tunnels) — เหมาะกับ voice/video ระหว่างสาขา

---

## 4. ผู้ผลิตและแนวทาง

| ผู้ผลิต | ผลิตภัณฑ์ | ลักษณะเด่น |
|---|---|---|
| **Fortinet** | FortiGate Secure SD-WAN + FortiManager | **SD-WAN อยู่ในตัว NGFW** — คุ้มค่าสำหรับสาขาที่ต้องมี firewall อยู่แล้ว |
| **Cisco** | Catalyst SD-WAN (Viptela) · Meraki SD-WAN | องค์กรขนาดใหญ่ / cloud-managed |
| **HPE Aruba** | EdgeConnect (Silver Peak) | WAN optimization แข็งแรง |
| **Palo Alto** | Prisma SD-WAN (CloudGenix) | app-defined, ผสานกับ Prisma Access (SASE) |
| **VMware/Broadcom** | VeloCloud SD-WAN | cloud gateway |
| **Versa, Juniper (Mist WAN), Cato Networks** | | Versa/Cato เน้น single-vendor SASE |

> เลือกตาม: ฟีเจอร์ security ที่ต้องการ, ความสามารถของทีม, ระบบเดิม, การจัดการ (cloud/on-prem), license model, การสนับสนุนในไทย, ราคา 5 ปี

---

## 5. ออกแบบ SD-WAN (ตัวอย่าง 30 สาขา)

```
 ① Hub: DC/HQ มี edge คู่ (HA) + DIA 2 ผู้ให้บริการ (+ MPLS ช่วงเปลี่ยนผ่าน)
 ② สาขาใหญ่ (5 แห่ง): broadband 2 ผู้ให้บริการ + 5G สำรอง, edge คู่
 ③ สาขาเล็ก (25 แห่ง): broadband 1 + 5G, edge ตัวเดียว
 ④ Overlay: hub-and-spoke + dynamic spoke-to-spoke · BGP บน overlay (หรือ routing ของผู้ผลิต)
 ⑤ Segmentation: VPN/VRF แยก Corporate, POS/Payment (PCI), Guest, IoT
 ⑥ Internet: local breakout สำหรับ SaaS ที่เชื่อถือ + traffic เว็บทั่วไปผ่าน SSE/NGFW ที่สาขา
 ⑦ QoS: marking ที่ LAN + shaping ตามความเร็วจริงของลิงก์ (Level 54)
 ⑧ Monitoring: SLA, application performance, alert เมื่อลิงก์เสื่อม
 ⑨ ZTP: template ต่อประเภทสาขา, ตั้งชื่อ/IP plan มาตรฐาน (summarize ต่อภูมิภาค)
```

### ย้ายจาก MPLS → SD-WAN (Migration)
1. ติดตั้ง edge และลิงก์อินเทอร์เน็ต **ขนานกับ MPLS** เดิม
2. ใช้ MPLS เป็นลิงก์หนึ่งของ SD-WAN (hybrid) — ทดสอบ policy กับสาขานำร่อง
3. ย้ายแอปทีละกลุ่มไปใช้อินเทอร์เน็ต วัดผล
4. ลด bandwidth MPLS ลง หรือยกเลิกเมื่อครบสัญญา
5. วัด ROI: ค่า WAN ที่ลดลง, เวลาเปิดสาขา, ประสบการณ์ผู้ใช้ SaaS

---

## 6. SASE — Secure Access Service Edge

**ปัญหาต่อจาก SD-WAN:** เมื่อสาขาและผู้ใช้ remote ออกอินเทอร์เน็ตโดยตรง → security ของ HQ ตามไปไม่ถึง

**SASE** (คำของ Gartner ปี 2019) = **รวม network + security ไว้เป็นบริการบน cloud** ใกล้ผู้ใช้ทุกที่
```
              SASE = SD-WAN (network)  +  SSE (Security Service Edge)
                                             ├─ SWG   Secure Web Gateway (กรองเว็บ, มัลแวร์, SSL inspection)
                                             ├─ CASB  Cloud Access Security Broker (ควบคุมการใช้ SaaS, shadow IT, DLP)
                                             ├─ ZTNA  Zero Trust Network Access (เข้าแอปภายในแบบ least privilege)
                                             └─ FWaaS Firewall as a Service
                                             (+ DLP, RBI, DNS security)
```
```
 ผู้ใช้สาขา ─(SD-WAN)─┐
 ผู้ใช้ที่บ้าน ─(agent)─┼──► [ SASE PoP บน cloud: SWG/CASB/ZTNA/FWaaS ] ──► อินเทอร์เน็ต/SaaS
 ผู้ใช้เดินทาง ─(agent)─┘                         └──(ZTNA connector)──► แอปภายใน DC/cloud
 → policy เดียวกัน ไม่ว่าผู้ใช้อยู่ที่ไหน
```

| ผู้ให้บริการ SSE/SASE | ตัวอย่าง |
|---|---|
| Zscaler (ZIA/ZPA), Netskope, Palo Alto Prisma Access, Fortinet FortiSASE, Cisco Secure Access, Cloudflare One, Cato Networks |

**Single-vendor SASE vs Dual-vendor:** single vendor บริหารง่ายกว่า; dual vendor (SD-WAN ยี่ห้อหนึ่ง + SSE อีกยี่ห้อ) เลือก best-of-breed ได้

### ข้อพิจารณา
- ตำแหน่ง **PoP (Point of Presence)** ใกล้ประเทศไทยไหม (latency)
- **Data residency/PDPA** — log และการ inspect เกิดที่ใด
- SSL inspection บน cloud: exemption และ privacy
- การผูกกับผู้ให้บริการ (vendor lock-in), ค่าใช้จ่ายต่อผู้ใช้ต่อปี

---

## 7. ข้อควรระวังของ SD-WAN

| ประเด็น | คำแนะนำ |
|---|---|
| Broadband เป็น best effort | ใช้ 2 ผู้ให้บริการ + 5G, ตรวจ shared fate |
| ความซับซ้อนของ policy | เริ่มจาก policy เรียบง่าย (4–6 กลุ่มแอป) แล้วค่อยเพิ่ม |
| MTU/MSS ของ overlay | ตั้งให้ถูก (Level 57) |
| Controller/Orchestrator ล่ม | data plane ทำงานต่อได้ (graceful) แต่แก้ policy ไม่ได้ — ตรวจ HA/SLA ของผู้ผลิต |
| ความปลอดภัยของ local breakout | ต้องมี NGFW/SSE เสมอ |
| ทักษะทีม | อบรม, เอกสาร, ทดลองใน lab/sandbox |

---

## 8. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| SD-WAN = VPN ราคาถูก | เป็นการจัดการ WAN แบบรวมศูนย์ที่เลือกเส้นตามแอปและคุณภาพลิงก์แบบ real-time |
| SD-WAN ทำให้ broadband มีคุณภาพเท่า MPLS | ช่วยเลือก/ชดเชย แต่ลิงก์ทุกเส้นแย่พร้อมกันก็ช่วยไม่ได้ |
| Local breakout ไม่ต้องมี security | ต้องมี NGFW/SSE |
| SASE คือผลิตภัณฑ์ชิ้นเดียว | เป็นสถาปัตยกรรมที่รวม SD-WAN + SSE |
| เปลี่ยนเป็น SD-WAN แล้วยกเลิก MPLS ได้ทันที | ควรทำแบบ hybrid และย้ายทีละขั้นพร้อมวัดผล |

---

## 9. Cheat Sheet

```
SD-WAN = orchestrator/controller (control+mgmt) + edge (data) · overlay (IPsec) บน underlay (MPLS/Internet/5G)
App-aware routing: DPI + SLA probe (latency/jitter/loss) → เลือกลิงก์ต่อแอปแบบ real-time
Active/active · FEC/duplication · ZTP · policy กลาง · segmentation · dynamic spoke-to-spoke (ADVPN)
Fortinet (ใน FortiGate) · Cisco Catalyst/Meraki · Aruba EdgeConnect · Prisma SD-WAN · VeloCloud · Versa · Cato
Migration: ขนาน MPLS → hybrid → ย้ายทีละแอป → ลด/ยกเลิก MPLS
SASE = SD-WAN + SSE (SWG + CASB + ZTNA + FWaaS) บน cloud PoP · policy เดียวทุกที่
พิจารณา: PoP ใกล้ไทย · PDPA/data residency · SSL inspection · lock-in · ราคา/ผู้ใช้
```

---

## 10. แบบทดสอบ 10 ข้อ

1. WAN แบบเดิม (MPLS + router CLI) มีปัญหาอะไรบ้าง (4 ข้อ)
2. Underlay กับ overlay ต่างกันอย่างไร
3. Application-aware routing ทำงานอย่างไร
4. SLA probe วัดค่าอะไรบ้าง
5. ZTP คืออะไร มีประโยชน์อย่างไร
6. ทำไม local internet breakout ต้องมี security ที่สาขาหรือบน cloud
7. SASE ประกอบด้วยอะไร
8. SSE มีบริการอะไรบ้าง (4 อย่าง)
9. ขั้นตอนย้ายจาก MPLS ไป SD-WAN อย่างปลอดภัย
10. ปัจจัยที่ควรพิจารณาเมื่อเลือกผู้ให้บริการ SASE สำหรับองค์กรในไทย

<details><summary><b>เฉลย</b></summary>

1. MPLS แพงและเพิ่ม bandwidth ช้า, backhaul traffic cloud ทำให้ช้า, ลิงก์สำรองไม่ได้ใช้, failover ไม่ดูคุณภาพลิงก์, จัดการทีละเครื่อง, เปิดสาขาใหม่ช้า
2. Underlay คือลิงก์จริง (MPLS/อินเทอร์เน็ต/5G); overlay คือ tunnel เข้ารหัสที่สร้างบน underlay
3. ระบุแอปด้วย DPI วัดคุณภาพลิงก์ต่อเนื่อง แล้วส่ง traffic ของแต่ละแอปไปลิงก์ที่ผ่าน SLA ของแอปนั้น และย้ายอัตโนมัติเมื่อคุณภาพตก
4. Latency, jitter, packet loss
5. Zero-Touch Provisioning — อุปกรณ์ติดต่อ orchestrator เองแล้วดึง config อัตโนมัติ ทำให้เปิดสาขาได้เร็วโดยไม่ต้องส่งวิศวกร
6. Traffic อินเทอร์เน็ตไม่ผ่าน firewall/web filter ของ HQ แล้ว ต้องมี NGFW ที่สาขาหรือ SSE บน cloud ตรวจแทน
7. SD-WAN (network) + SSE (security บน cloud)
8. SWG, CASB, ZTNA, FWaaS (และ DLP/RBI/DNS security)
9. ติดตั้งขนานกับ MPLS → ใช้แบบ hybrid ทดสอบกับสาขานำร่อง → ย้ายแอปทีละกลุ่มพร้อมวัดผล → ลด/ยกเลิก MPLS เมื่อมั่นใจและครบสัญญา
10. ตำแหน่ง PoP ใกล้ไทย (latency), PDPA/data residency, ความสามารถ SSL inspection และ exemption, การผสานกับ SD-WAN/IdP เดิม, lock-in, ราคา และการสนับสนุนในประเทศ
</details>

---

🎉 **จบ Tier 6** · ➡️ ต่อไป: **Level 61 — Security Fundamentals** · กลับไปทำโปรเจคใน [06-services-wireless-wan.md](../06-services-wireless-wan.md)
