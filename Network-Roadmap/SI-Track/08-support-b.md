# Part 4 — บริการสนับสนุน 24x7 (Support & Maintenance) ตอน B: Preventive Maintenance & Service Excellence (Level 91–100)

---

## Level 91 — Preventive Maintenance (PM)

**สิ่งที่ต้องรู้**
- PM = ตรวจสุขภาพตามรอบ (รายเดือน/ไตรมาส/ครึ่งปี) ก่อนเกิดปัญหา ตามที่สัญญา MA กำหนด
- Checklist ตามประเภทอุปกรณ์:
  - Network/Firewall: CPU/mem, interface error, HA sync, log, license/subscription, firmware/advisory, config backup, rule review
  - Server: hardware log (iDRAC/iLO), ดิสก์/PSU/fan, firmware, OS patch
  - Storage/HCI: health check (NCC/vSAN health), capacity, latency, replication, firmware
  - Virtualization: snapshot ค้าง, HA/DRS, datastore, vCenter/Prism backup
  - Backup: job success rate, restore test, immutable storage
  - Environment: อุณหภูมิ, UPS battery, ฝุ่น, สายหลวม, label
- PM report: สถานะ, findings, ความเสี่ยง, คำแนะนำ, ภาพประกอบ, ลูกค้าเซ็นรับ

**แบบทดสอบ**
1. PM ต่างจาก corrective maintenance อย่างไร
2. รายการตรวจ firewall 5 ข้อใน PM
3. ทำไมต้องตรวจแบตเตอรี่ UPS
4. Finding ระดับสูงใน PM ควรทำอย่างไร
5. PM report ควรเขียนให้ใครอ่าน

<details><summary>เฉลย</summary>

1. PM ทำตามรอบเพื่อป้องกัน; corrective ทำหลังเกิดปัญหา
2. HA status/sync, CPU/memory/session, firmware vs advisory, license/subscription expiry, config backup (+ rule hit/any-any)
3. แบตเสื่อมตามอายุ (3–5 ปี) อาจทำงานไม่ได้เมื่อไฟดับ
4. แจ้งลูกค้าทันที (ไม่รอรายงาน), เสนอวิธีแก้/นัด change, เปิด ticket ติดตาม
5. ทั้ง IT ลูกค้า (รายละเอียด) และผู้บริหาร (executive summary + ความเสี่ยง)
</details>

**5 โปรเจค**
- ⭐ P1: PM checklist ครบ 6 หมวด (Excel/Google Sheet)
- ⭐⭐ P2: PM health-check script: FortiGate/Cisco (SSH) + Linux + vCenter/Prism API → ผลเป็น JSON
- ⭐⭐ P3: แปลงผล P2 เป็น PM report (HTML/PDF) อัตโนมัติ
- ⭐⭐ P4: ทำ PM จริงกับ lab ทั้งชุดแล้วออกรายงาน
- ⭐⭐⭐ P5: PM calendar สำหรับ 10 ลูกค้า (ทรัพยากร/วิศวกร/รอบ) + tracking findings

---

## Level 92 — Patch & Firmware Lifecycle Management

**สิ่งที่ต้องรู้**
- Inventory version ทุกอุปกรณ์ → เทียบ recommended release (Fortinet, Palo Alto preferred release, Cisco suggested)
- PSIRT/advisory monitoring (ต่อยอด L56), CISA KEV → emergency patch
- Compatibility matrix: firmware server ↔ hypervisor ↔ HCI ↔ storage ↔ backup
- Pilot → staged rollout, maintenance window, rollback/backup
- EoS/EoL tracking และแผน refresh

**แบบทดสอบ**
1. "Recommended/preferred release" สำคัญอย่างไร
2. ทำไมไม่ควร upgrade เป็น version ล่าสุดทันทีที่ออก
3. แต่ถ้ามีช่องโหว่ critical ที่ถูกโจมตีจริงล่ะ
4. ทำไมต้องตรวจ compatibility ข้ามระบบ
5. EoL ส่งผลต่อสัญญา support อย่างไร

<details><summary>เฉลย</summary>

1. Vendor แนะนำว่าเสถียรผ่านการใช้งานจริงแล้ว
2. Version ใหม่อาจมี bug ยังไม่ถูกพบ
3. ทำ emergency patch (หรือ workaround) ตามความเสี่ยง ทดสอบเท่าที่ทำได้และมี rollback
4. เช่น backup software ยังไม่รองรับ hypervisor version ใหม่ ทำให้ backup พัง
5. หลัง EoL ไม่มี patch/support จาก vendor ทำให้ SI ให้ SLA ไม่ได้ ต้องเสนอ refresh
</details>

**5 โปรเจค**
- ⭐⭐ P1: Version inventory อัตโนมัติ (Ansible/Nornir/API) ของทุกอุปกรณ์ใน lab
- ⭐⭐ P2: เปรียบเทียบกับ recommended release (ตารางที่ดูแลเอง) แล้วแสดงสิ่งที่ต้อง upgrade
- ⭐⭐ P3: EoL report ของ inventory ลูกค้าสมมติ + แผน refresh 3 ปี
- ⭐⭐ P4: Patch plan รายไตรมาส (pilot → production) สำหรับ server 200 เครื่อง
- ⭐⭐⭐ P5: Emergency patch playbook (CVE critical บน firewall ที่เปิด internet)

---

## Level 93 — Backup Verification & DR Drill เป็นบริการ

**สิ่งที่ต้องรู้**
- Backup monitoring รายวัน: success/warning/fail, เหตุผล, re-run
- Restore test ตามรอบ (ไฟล์, VM, application), Veeam SureBackup/Instant recovery
- DR drill รายปี/ครึ่งปี: plan, scope, ผู้เกี่ยวข้อง, ผลลัพธ์ RTO/RPO จริง, รายงาน
- เอกสารที่ auditor ต้องการ (ธปท., ISO 27001): หลักฐานการทดสอบ
- ปรับปรุง runbook หลัง drill

**แบบทดสอบ**
1. Backup job "warning" ต้องสนใจหรือไม่
2. SureBackup ทำอะไร
3. DR drill ที่ "ผ่าน" ต้องพิสูจน์อะไร
4. หลักฐานอะไรที่ auditor ต้องการ
5. ทำไมต้องอัปเดต runbook หลัง drill ทุกครั้ง

<details><summary>เฉลย</summary>

1. ต้อง — อาจมีบาง VM/ไฟล์ไม่ถูก backup
2. เปิด VM จาก backup ใน isolated environment แล้วตรวจว่า boot/app ทำงาน (อัตโนมัติ)
3. ระบบกลับมาใช้งานได้จริงภายใน RTO และข้อมูลหายไม่เกิน RPO
4. แผน, ผลการทดสอบ (เวลา, ภาพ), ผู้อนุมัติ, ปัญหาและการแก้ไข
5. ระบบเปลี่ยนตลอด; สิ่งที่พบใน drill ต้องถูกแก้ก่อนเหตุจริง
</details>

**5 โปรเจค**
- ⭐⭐ P1: Daily backup report อัตโนมัติ (Veeam API/PowerShell) ส่งอีเมล
- ⭐⭐ P2: Restore test schedule + บันทึกผล (ไฟล์/VM/DB)
- ⭐⭐ P3: SureBackup-like: สคริปต์ restore VM ไป isolated network แล้ว ping/HTTP check
- ⭐⭐⭐ P4: DR drill ใน lab ตาม runbook (L32) แล้วออก drill report
- ⭐⭐ P5: Audit evidence package template

---

## Level 94 — Change Management & Maintenance Window

> พื้นฐานจาก Roadmap หลัก [L95](../10-expert-career.md)

**สิ่งที่ต้องรู้**
- Change request: เหตุผล, scope, risk, impact, ขั้นตอน, pre-check/post-check, rollback, ผู้อนุมัติ, เวลา
- Maintenance window: นัดลูกค้า, แจ้งผู้ใช้ล่วงหน้า, freeze period (ปิดงบ, เทศกาล)
- Safety net: `commit confirmed`, `reload in`, config backup, console access/OOB, ทำทีละ site
- Peer review / four-eyes principle
- Change ที่ล้มเหลว: rollback ทันทีเมื่อถึงเงื่อนไข, ไม่ "ลองอีกนิด" เกินเวลา

**แบบทดสอบ**
1. องค์ประกอบสำคัญที่สุด 3 อย่างของ change plan
2. Freeze period คืออะไร
3. ทำไมต้องมี console/OOB ก่อนแก้ firewall/router จากระยะไกล
4. เกณฑ์ตัดสินใจ rollback ควรกำหนดเมื่อไร
5. Four-eyes principle คืออะไร

<details><summary>เฉลย</summary>

1. ขั้นตอนที่ชัดเจน, verification (pre/post check), rollback plan (+ เกณฑ์และเวลา)
2. ช่วงที่ห้ามเปลี่ยนแปลงระบบ (ยกเว้นฉุกเฉิน) เพราะธุรกิจสำคัญ
3. ถ้าแก้ผิดจนเข้า SSH ไม่ได้ ยังมีทางเข้าแก้ไข
4. ก่อนเริ่ม change (เช่น "ถ้าถึง 02:30 ยังไม่ผ่าน test ให้ rollback")
5. มีอีกคนตรวจ/อนุมัติ/ดูขณะทำ change สำคัญ
</details>

**5 โปรเจค**
- ⭐ P1: Change request template (ไทย/อังกฤษ)
- ⭐⭐ P2: Change plan 3 ตัวอย่าง: upgrade firewall HA, เพิ่ม node HCI, เปลี่ยน core switch
- ⭐⭐ P3: Pre/post check script + diff อัตโนมัติ (ต่อยอด Roadmap หลัก L84)
- ⭐⭐ P4: Customer notification template (ล่วงหน้า 7 วัน / 1 วัน / เสร็จสิ้น)
- ⭐⭐⭐ P5: ทำ change จริงใน lab ตาม plan พร้อมเพื่อนเป็น reviewer และจำลองการ rollback

---

## Level 95 — Knowledge Management & Runbooks

**สิ่งที่ต้องรู้**
- Knowledge base: KCS (Knowledge-Centered Service) — เขียน/ปรับ article ระหว่างแก้ปัญหา
- Runbook vs SOP vs Playbook vs KB article
- เอกสารต่อลูกค้า: customer profile (topology, contact, สัญญา, access, ข้อควรระวัง)
- เครื่องมือ: Confluence, BookStack, Wiki.js, MkDocs, IT Glue/Hudu (สำหรับ MSP)
- ทำให้ค้นหาง่าย: tag, template, ภาษาเดียวกัน, review รอบปี

**แบบทดสอบ**
1. Runbook กับ KB article ต่างกันอย่างไร
2. KCS คืออะไร
3. Customer profile ควรมีอะไร
4. ทำไมเอกสารต้องมีวันที่ review
5. วัดคุณภาพ knowledge base อย่างไร

<details><summary>เฉลย</summary>

1. Runbook = ขั้นตอนทำงานเฉพาะ (step-by-step); KB article = ความรู้/วิธีแก้ปัญหาเฉพาะอาการ
2. วิธีที่สร้างและปรับปรุง knowledge เป็นส่วนหนึ่งของการแก้ ticket
3. Topology, IP สำคัญ, อุปกรณ์/version, contact/escalation, สัญญา/SLA, วิธีเข้าถึง, ข้อควรระวัง
4. ระบบเปลี่ยน เอกสารเก่าที่ผิดอันตรายกว่าไม่มีเอกสาร
5. % ticket ที่แก้ได้จาก KB, เวลาแก้ลดลง, จำนวนครั้งที่ใช้, feedback
</details>

**5 โปรเจค**
- ⭐ P1: BookStack/Wiki.js สำหรับทีม + โครงสร้างหมวดหมู่
- ⭐⭐ P2: Customer profile template + ตัวอย่าง 1 ลูกค้า
- ⭐⭐ P3: KB article 10 เรื่องจากเคสใน lab (รูปแบบเดียวกัน)
- ⭐⭐ P4: ย้าย runbook ทั้งหมดจาก Part 1–4 เข้า wiki พร้อม tag
- ⭐⭐⭐ P5: Chatbot ค้น KB ภายใน (RAG เล็ก ๆ บนเอกสารของทีม)

---

## Level 96 — Service Reporting & KPI

**สิ่งที่ต้องรู้**
- Monthly service report: ภาพรวม, จำนวน ticket ตาม priority/หมวด, SLA compliance, P1 summary, availability, capacity trend, PM findings, ความเสี่ยง, คำแนะนำ
- KPI: MTTA, MTTR, SLA %, first contact resolution, repeat incident, CSAT
- Availability calculation (planned vs unplanned downtime)
- QBR (Quarterly Business Review) กับลูกค้า: แนวโน้ม + roadmap + โอกาสต่อยอด
- Data → insight → recommendation (ไม่ใช่แค่ตัวเลข)

**แบบทดสอบ**
1. MTTA คืออะไร
2. ระบบ 30 วัน ล่ม 43 นาที availability เท่าไร
3. ทำไมรายงานต้องมี recommendation
4. QBR ต่างจาก monthly report อย่างไร
5. Repeat incident สูงบอกอะไร

<details><summary>เฉลย</summary>

1. Mean Time To Acknowledge: เวลาเฉลี่ยจาก alert/แจ้ง จนมีคนรับเรื่อง
2. 43,200 นาที → (43,200 − 43)/43,200 ≈ 99.90%
3. ลูกค้าต้องการรู้ว่าควรทำอะไรต่อ ไม่ใช่แค่ตัวเลข และเป็นโอกาสเสนอการปรับปรุง
4. QBR เน้นเชิงกลยุทธ์ แนวโน้ม แผนอนาคต คุยกับผู้บริหาร
5. แก้แค่อาการ ยังไม่แก้ root cause (ต้องทำ problem management)
</details>

**5 โปรเจค**
- ⭐⭐ P1: Monthly service report template (Word/PowerBI/Grafana)
- ⭐⭐ P2: สคริปต์ดึงข้อมูล ticket + monitoring → คำนวณ KPI อัตโนมัติ
- ⭐⭐ P3: Availability report จาก monitoring data
- ⭐⭐ P4: QBR deck 10 สไลด์ของลูกค้าสมมติ
- ⭐⭐⭐ P5: Dashboard KPI ของทีม Support ทั้งหมด (ทุกลูกค้า)

---

## Level 97 — On-call, Shift & Team Operations 24x7

**สิ่งที่ต้องรู้**
- รูปแบบ: 3 shift (8 ชม.), on-call rotation, follow-the-sun
- Shift handover: ticket ค้าง, เหตุการณ์ที่ต้องเฝ้า, change คืนนี้, ข้อมูลสำคัญ (เขียนเป็นลายลักษณ์อักษร)
- Escalation: L1 → L2 → L3 → vendor → management; เวลาที่ต้อง escalate
- Fatigue & well-being: จำกัดจำนวน page, ชดเชยเวลา, ลด alert ที่ไม่จำเป็น
- Tools: PagerDuty/Opsgenie/Grafana OnCall, ปฏิทิน rotation

**แบบทดสอบ**
1. Shift handover ที่ดีต้องมีอะไร
2. ทำไม handover ต้องเป็นลายลักษณ์อักษร
3. อาการ on-call fatigue และวิธีแก้
4. Follow-the-sun คืออะไร
5. ถ้า on-call ไม่รับสาย 15 นาที ระบบควรทำอะไร

<details><summary>เฉลย</summary>

1. Ticket ค้าง + สถานะ, เหตุการณ์ที่ยังเฝ้า, change ที่กำหนด, ปัญหาที่ต้องระวัง, ใครติดต่อได้
2. ไม่ลืม/ไม่ตกหล่น ตรวจสอบย้อนหลังได้
3. ตอบช้า ผิดพลาด หมดไฟ — ลด alert noise, หมุนเวียนให้เป็นธรรม, ชดเชยเวลาพัก, automation
4. ส่งต่องานระหว่างทีมในเขตเวลาต่างกันเพื่อให้มีคนทำงานในเวลากลางวันตลอด 24 ชม.
5. Escalate ไปคนถัดไป/หัวหน้าอัตโนมัติ
</details>

**5 โปรเจค**
- ⭐ P1: Shift handover template + ตัวอย่าง
- ⭐⭐ P2: On-call rotation (Grafana OnCall/Opsgenie free) + escalation policy
- ⭐⭐ P3: Alert noise review: หา alert ที่ไม่มี action แล้วเสนอปรับ
- ⭐⭐ P4: Team operations handbook (shift, escalation, การพัก, การเรียนรู้)
- ⭐⭐⭐ P5: จำลอง 24 ชม. (3 คน 3 shift) กับ lab ที่มีเหตุการณ์ถูกสร้างเป็นระยะ แล้วทำ retrospective

---

## Level 98 — Automation for Support (AIOps / ChatOps)

> พื้นฐานจาก Roadmap หลัก [L81–L84](../09-automation-operations.md)

**สิ่งที่ต้องรู้**
- Auto-remediation ที่ปลอดภัย: restart service, ล้าง disk/log, re-run backup job, failover ตาม runbook (มีเงื่อนไขและ log)
- ChatOps: bot ใน LINE/Teams/Slack ให้รันคำสั่ง read-only (show status, ping, health check)
- Enrichment อัตโนมัติ: alert มาพร้อม topology, ticket ก่อนหน้า, runbook
- AIOps: anomaly detection, event correlation, ใช้ LLM ช่วยสรุป log/ticket (ระวังข้อมูลลูกค้า — ห้ามส่งข้อมูลลับไปบริการภายนอกโดยไม่ได้รับอนุญาต)
- Guardrail: approval สำหรับคำสั่งที่เปลี่ยนแปลงระบบ, audit trail

**แบบทดสอบ**
1. Auto-remediation แบบไหนปลอดภัย แบบไหนไม่ควรทำ
2. ChatOps มีประโยชน์อย่างไร
3. ทำไมต้องมี audit trail สำหรับ automation
4. ข้อควรระวังเมื่อใช้ AI วิเคราะห์ log ลูกค้า
5. Alert enrichment ช่วยลด MTTR อย่างไร

<details><summary>เฉลย</summary>

1. ปลอดภัย: งานที่ผลชัด ย้อนได้ (restart service, ล้าง temp); ไม่ควร: เปลี่ยน config/routing/ลบข้อมูลโดยไม่มีคนอนุมัติ
2. ทีมเห็นการทำงานร่วมกันในที่เดียว ทำงานเร็วขึ้น มีประวัติ
3. รู้ว่าระบบทำอะไร เมื่อไร เพราะอะไร (ตรวจสอบและแก้ไขเมื่อผิดพลาด)
4. Data privacy/PDPA, สัญญากับลูกค้า, ใช้บริการที่อนุมัติ, ปิดบังข้อมูลอ่อนไหว, ตรวจผลก่อนใช้
5. วิศวกรได้ข้อมูลประกอบทันทีไม่ต้องค้นเอง เริ่มวิเคราะห์ได้เร็ว
</details>

**5 โปรเจค**
- ⭐⭐ P1: Bot (Teams/Discord/LINE) รัน health check read-only ของ lab
- ⭐⭐ P2: Auto-remediation: disk > 90% → ล้าง log เก่า → แจ้งผล + บันทึก ticket
- ⭐⭐ P3: Alert enrichment: เพิ่ม runbook link + ticket ล่าสุดของอุปกรณ์ลงใน alert
- ⭐⭐⭐ P4: Anomaly detection บน interface traffic (Python, baseline + threshold แบบปรับตัว)
- ⭐⭐⭐ P5: LLM สรุป incident timeline จาก ticket/log ใน lab (ข้อมูลจำลองเท่านั้น) พร้อมขั้นตอนตรวจทานโดยคน

---

## Level 99 — Career ในบริษัท System Integrator

**สิ่งที่ต้องรู้**
- บทบาทใน SI: Pre-sales Engineer, Solution Architect, Implementation/Project Engineer, Support/NOC/SOC Engineer, Project Manager, Service Delivery Manager
- เส้นทาง: Support L1 → L2 → Implementation → Senior/Specialist → Architect/Pre-sales (หรือ SDM)
- Certifications ตาม 4 ด้าน:
  - Data Center: Dell/HPE server & storage certs, NetApp NCDA, VMware VCP-DCV/VCF, Cisco CCNP Data Center
  - Security: Fortinet FCP/FCSS (เดิม NSE 4–7), Palo Alto PCNSA/PCNSE, CompTIA Security+, CEH/OSCP (สำหรับสาย offensive), Splunk/Sentinel (SC-200)
  - Cloud & HCI: Nutanix NCA/NCP-MCI, AWS SAA/SAP, Azure AZ-104/AZ-305, CKA
  - Support: ITIL 4 Foundation, CCNA, CompTIA Network+
- Soft skill: สื่อสารไทย/อังกฤษ, เขียนเอกสาร, นำเสนอ, จัดการความคาดหวังลูกค้า
- Portfolio: lab + เอกสาร (HLD/LLD/runbook/report) จาก track นี้

**แบบทดสอบ (คำถามสัมภาษณ์งาน SI)**
1. ลูกค้าโทรมาตอนตี 2 บอกระบบ ERP ใช้ไม่ได้ คุณจะทำอะไร
2. อธิบายความต่าง HCI กับ 3-tier ให้ผู้บริหารฟังใน 1 นาที
3. ถ้าคุณทำ change แล้วระบบลูกค้าล่ม จะทำอย่างไร
4. ออกแบบ HA สำหรับ firewall และ core switch อย่างไร
5. ทำไมควรเลือกทำงาน SI แทน in-house IT

<details><summary>แนวคำตอบ</summary>

1. รับเรื่อง/ยืนยัน priority, ถาม scope และ change ล่าสุด, เข้าระบบผ่านช่องทางที่อนุญาต, health check, กู้บริการ/escalate, อัปเดตลูกค้าเป็นระยะ, บันทึก ticket
2. HCI รวม server+storage ในกล่องเดียว ขยายง่ายทีละ node จัดการจุดเดียว ลดความซับซ้อน; 3-tier แยกส่วน ยืดหยุ่นเมื่อ storage/compute โตไม่เท่ากัน
3. Rollback ตามแผนทันที, แจ้งหัวหน้าและลูกค้าตามจริง, ยืนยันระบบกลับมา, ทำ RCA และปรับขั้นตอน
4. Firewall HA (A/P, session sync, link monitoring), core switch คู่ (VSS/StackWise Virtual หรือ MLAG/vPC), FHRP, dual uplink, ทดสอบ failover
5. ได้เจอเทคโนโลยี/ลูกค้าหลากหลาย เรียนรู้เร็ว ได้ cert จาก partner program และเติบโตหลายสาย
</details>

**5 โปรเจค**
- ⭐ P1: เลือกเส้นทาง (DC / Security / Cloud-HCI / Support) + แผน cert 12 เดือน
- ⭐⭐ P2: CV + LinkedIn เน้นโปรเจคจาก SI-Track
- ⭐⭐ P3: Portfolio repo: HLD/LLD, runbook, report, script ที่ดีที่สุด 10 ชิ้น
- ⭐⭐ P4: Mock interview (เทคนิค + สถานการณ์ลูกค้า) 3 รอบ
- ⭐⭐⭐ P5: นำเสนอ solution 15 นาทีแบบ pre-sales ให้ "ลูกค้า" (เพื่อน/รุ่นพี่) แล้วรับ feedback

---

## Level 100 — Final Capstone: Customer Lifecycle ครบวงจร (Pre-sales → Implementation → Support 24x7)

**โจทย์:** มหาวิทยาลัยเอกชน (นักศึกษา 15,000 คน, บุคลากร 1,500 คน) ต้องการ
1. **Data Center:** ปรับปรุงห้อง server และย้าย server เก่า 40 เครื่องเข้าสู่ virtualization ที่มี HA
2. **Cybersecurity:** เปลี่ยน NGFW, ทำ Zero Trust Segmentation แยก network นักศึกษา/บุคลากร/ระบบทะเบียน/การเงิน และมีระบบเฝ้าระวัง
3. **Cloud & HCI:** ใช้ HCI สำหรับระบบภายใน, ย้าย e-Learning และ DR ไป cloud แบบไร้รอยต่อ (downtime ≤ 30 นาที/ระบบ)
4. **Support 24x7:** สัญญาดูแล 3 ปี: SLA P1 response 30 นาที, PM รายไตรมาส, รายงานรายเดือน

**ต้องส่งมอบ**
1. Pre-sales: discovery, assessment, proposal 2 ทางเลือก, BOM/TCO 5 ปี, SoW
2. Design: HLD/LLD ครบ 4 ด้าน (DC, security, HCI/cloud, operations)
3. Implementation (lab ย่อส่วน): HCI cluster, NGFW HA + segmentation, backup/DR, hybrid VPN, migration 2 VM
4. Testing & handover: UAT/HA/DR test report, as-built
5. Operations: monitoring + ticket + on-call + PM checklist + monthly report + IR playbook

**แบบทดสอบสุดท้าย (Self-review)**
1. ทุกบริการ 4 ด้านในภาพมี deliverable ที่ลูกค้าเห็นคุณค่าและวัดผลได้หรือยัง
2. ไม่มี single point of failure ที่ไม่ถูกบันทึกเป็นความเสี่ยง
3. Migration ทุกระบบมี runbook + rollback + เวลา downtime ที่พิสูจน์แล้ว
4. ทีม Support รับเรื่อง P1 ตอนตี 2 แล้วแก้ได้จากเอกสาร/monitoring ที่ส่งมอบ
5. ผู้บริหารลูกค้าอ่านรายงานแล้วเข้าใจความเสี่ยงและสิ่งที่ต้องลงทุนต่อ

**5 โปรเจค (Capstone 5 ระยะ)**
- ⭐⭐⭐ P1: **Pre-sales**: discovery → proposal → นำเสนอ
- ⭐⭐⭐ P2: **Design**: HLD/LLD + ADR + sizing ครบ 4 ด้าน
- ⭐⭐⭐ P3: **Build & Migrate**: lab implementation + migration + ทดสอบ
- ⭐⭐⭐ P4: **Handover**: as-built, test report, training, ส่งต่อทีม Support
- ⭐⭐⭐ P5: **Operate 24x7**: จำลอง 1 เดือน (ticket, PM, incident P1 1 ครั้ง, monthly report, QBR)

🎓 **จบ SI-Track Level 100** — พร้อมทำงานที่บริษัท System Integrator ทั้งสาย Data Center, Cybersecurity, Cloud & HCI และ Support 24x7
