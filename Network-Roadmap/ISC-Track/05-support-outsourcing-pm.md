# Part 5 — 24x7 Support & MA · IT Outsourcing · Consulting, PM & ISO 9001 · Career (Level 88–100)

> ตามขอบเขตงาน ISC:
> - **24x7 Mission-Critical Support & Maintenance:** สัญญา MA, Hotline 24x7x365, Certified Support Engineers, SLA Response (Onsite ภายใน 2 ชั่วโมง), Quarterly PM, eSupport Ticket & Incident Tracking, Proactive Monitoring
> - **IT Outsourcing & Specialist Services:** IT Support / Network Engineer Outsourcing (PC/LAN, Network Management) แบบ onsite, part-time และ full-time
> - **Consulting, Project Management & QA:** Design/Consulting/Project Management, ISO 9001:2015, รายงานกำกับ, UAT ก่อนส่งมอบ

## Level ที่ใช้เนื้อหาเดิม

| Level | หัวข้อ | เรียนจาก | ISC Checkpoint |
|---|---|---|---|
| 88 | SLA, severity & service mindset | [SI L81](../SI-Track/07-support-a.md) | วางแผนให้ทำ SLA onsite ภายใน 2 ชม. ได้จริง (ทีม, อะไหล่สำรอง, เส้นทาง, กะ) |
| 89 | ITIL & eSupport ticketing | [SI L82–L83](../SI-Track/07-support-a.md) | เขียน ticket ที่ทีมอื่นรับต่อได้ทันที |
| 90 | Proactive monitoring / NOC 24x7 | [SI L84](../SI-Track/07-support-a.md) | Alert ถึงวิศวกรก่อนลูกค้าโทรแจ้ง |
| 91 | Triage & troubleshooting (network, security, server, storage, virtualization) | [SI L85–L87](../SI-Track/07-support-a.md), [ISC L66](03-security-hci-virtualization-cloud.md) | แก้ P1 ตาม runbook และเก็บหลักฐานก่อน reboot |
| 92 | Vendor TAC/RMA & remote support security | [SI L88–L89](../SI-Track/07-support-a.md) | เปิดเคส Dell/HPE/Fortinet/Cisco/VMware ได้ครบข้อมูลในครั้งเดียว |
| 93 | Quarterly PM & patch/firmware lifecycle | [SI L91–L92](../SI-Track/08-support-b.md) | PM report รายไตรมาสครบทุกหมวด (รวม UPS/PAC จาก ISC L22) |
| 94 | Change, communication, reporting & on-call | [SI L90](../SI-Track/07-support-a.md), [SI L94](../SI-Track/08-support-b.md), [SI L96–L97](../SI-Track/08-support-b.md) | Monthly service report + incident report ตามที่สัญญากำหนด |
| 98 | Knowledge base & support automation | [SI L95](../SI-Track/08-support-b.md), [SI L98](../SI-Track/08-support-b.md) | ทำ KB/runbook ของลูกค้าทุกรายให้ทีมกะดึกใช้ได้ |

---

## Level 95 — IT Outsourcing & Onsite Engineer (PC/LAN & Network Management)

**สิ่งที่ต้องรู้**
- รูปแบบบริการ: onsite ประจำ (full-time), part-time, on-demand; ขอบเขตตามสัญญา (SoW) และ KPI
- งาน PC/LAN: ติดตั้ง/ตั้งค่า Windows, image deployment (MDT/Intune/Autopilot), driver, printer/scanner, Outlook/M365/Zimbra client, VPN client, AV/EDR agent
- Active Directory พื้นฐาน: user/group/OU, reset password, GPO, join domain, DNS/DHCP
- Endpoint management: Intune/SCCM, patch, BitLocker, asset inventory (GLPI/Snipe-IT), license
- Network management ประจำไซต์: ตรวจ switch/AP/firewall รายวัน, port/VLAN request, เดินสาย/patch
- Service etiquette: บันทึก ticket ทุกงาน, ไม่แก้ระบบนอก scope โดยไม่อนุมัติ, ดูแลข้อมูลผู้ใช้ตาม PDPA, รายงานประจำเดือนให้ลูกค้า
- Workstation partner brands ของ ISC: Dell OptiPlex/Latitude, HP ProBook/EliteBook, Lenovo ThinkPad, Fujitsu, ASUS

**แบบทดสอบ**
1. ผู้ใช้ขอให้ติดตั้งโปรแกรมที่ไม่มี license ควรทำอย่างไร
2. ทำไมทุกงานที่ทำให้ผู้ใช้ต้องบันทึก ticket แม้เป็นงานเล็ก
3. เครื่องใหม่ 50 เครื่อง ควร deploy อย่างไรให้เร็วและเหมือนกัน
4. BitLocker recovery key ควรเก็บที่ไหน
5. KPI ทั่วไปของบริการ outsourcing มีอะไรบ้าง

<details><summary>เฉลย</summary>

1. ปฏิเสธอย่างสุภาพ อธิบายความเสี่ยงทางกฎหมาย แจ้งช่องทางขออนุมัติ/จัดซื้อ และบันทึก ticket
2. เป็นหลักฐานผลงาน ใช้ทำรายงาน/KPI และวิเคราะห์ปัญหาที่เกิดซ้ำ
3. ใช้ image มาตรฐาน + deployment tool (Autopilot/Intune/MDT) + script ติดตั้งแอป
4. AD หรือ Entra ID / Intune (ไม่ใช่ไฟล์ส่วนตัวหรือกระดาษบนโต๊ะ)
5. SLA response/resolution, จำนวน ticket, first-time fix rate, ความพึงพอใจผู้ใช้ (CSAT), uptime ของระบบที่ดูแล
</details>

**5 โปรเจค**
- ⭐ P1: Daily checklist ของ onsite engineer (เครือข่าย, server, backup, ticket)
- ⭐⭐ P2: Windows deployment lab (MDT หรือ Intune trial) + image มาตรฐาน
- ⭐⭐ P3: Snipe-IT/GLPI asset inventory + import ข้อมูลเครื่อง
- ⭐⭐ P4: PowerShell toolkit สำหรับ helpdesk (reset password, unlock account, รายงานเครื่องที่ไม่ได้ patch)
- ⭐⭐⭐ P5: Monthly outsourcing report (ticket, KPI, ปัญหาซ้ำ, ข้อเสนอปรับปรุง) ให้ลูกค้าสมมติ

---

## Level 96 — IT Consulting, Solution Design & Project Management

> พื้นฐานจาก [Roadmap L92](../10-expert-career.md), [SI L37](../SI-Track/02-datacenter-b.md)

**สิ่งที่ต้องรู้**
- Consulting: discovery workshop, current state assessment, gap, recommendation, roadmap
- Solution design: HLD/LLD, ADR, ทางเลือก good/better/best, BOM, TCO
- ภาครัฐ: TOR, ราคากลาง, e-bidding, spec ที่ไม่ล็อกยี่ห้อ, การส่งมอบเป็นงวดงาน, ค่าปรับ
- Project management: scope/WBS, timeline (Gantt), RACI, risk register, issue log, change request, kick-off/progress meeting, งวดงาน & ตรวจรับ
- การบริหารหลายฝ่าย: ลูกค้า, vendor/distributor, subcontractor (งานเดินสาย/ไฟฟ้า/แอร์)
- เครื่องมือ: MS Project, Jira, Excel, draw.io/Visio

**แบบทดสอบ**
1. RACI คืออะไร
2. ทำไม spec ใน TOR ภาครัฐต้องไม่ล็อกยี่ห้อ
3. Risk register ต้องมีอะไร
4. Change request ระหว่างโปรเจคควรจัดการอย่างไร
5. งวดงานและการตรวจรับมีผลต่อบริษัทอย่างไร

<details><summary>เฉลย</summary>

1. ตารางบทบาท: Responsible, Accountable, Consulted, Informed ของแต่ละงาน
2. ตามระเบียบจัดซื้อจัดจ้างภาครัฐที่ต้องเปิดให้แข่งขันอย่างเป็นธรรม
3. ความเสี่ยง, โอกาส, ผลกระทบ, ระดับ, ผู้รับผิดชอบ, แผนลด/รับมือ, สถานะ
4. บันทึกเป็นลายลักษณ์อักษร ประเมินผลกระทบด้าน scope/เวลา/ต้นทุน ให้ลูกค้าอนุมัติก่อนทำ
5. การเบิกเงินผูกกับการตรวจรับแต่ละงวด ถ้าล่าช้ามีผลต่อกระแสเงินสดและค่าปรับ
</details>

**5 โปรเจค**
- ⭐⭐ P1: Discovery workshop agenda + แบบสอบถาม (network, DC, security, cloud)
- ⭐⭐ P2: Project plan (WBS + Gantt + RACI) สำหรับโปรเจค DC 3 เดือน
- ⭐⭐ P3: Risk register + issue log template พร้อมตัวอย่าง 10 รายการ
- ⭐⭐ P4: ร่าง spec อุปกรณ์ตามแบบ TOR (switch, firewall, server) ที่ไม่ล็อกยี่ห้อ
- ⭐⭐⭐ P5: Consulting report: current state → gap → roadmap 3 ปี ให้ลูกค้าสมมติ

---

## Level 97 — Quality Management (ISO 9001:2015), UAT & Documentation Delivery

**สิ่งที่ต้องรู้**
- ISO 9001:2015: Quality Management System, process approach, PDCA, risk-based thinking, documented information, customer satisfaction, nonconformity & corrective action, internal audit, management review
- ในงานโครงการ: procedure มาตรฐาน (installation, testing, handover), checklist, การควบคุมเอกสาร (version), การเก็บหลักฐาน
- UAT: test plan, test case, ผล, การแก้ข้อบกพร่อง, ลูกค้าเซ็นรับ
- เอกสารส่งมอบ: design document, as-built, test report, ผลทดสอบสาย, คู่มือผู้ดูแลระบบ, training record, warranty/MA information
- Customer satisfaction survey และ lessons learned

**แบบทดสอบ**
1. PDCA คืออะไร
2. Nonconformity คืออะไร และต้องทำอะไรต่อ
3. ทำไมต้องควบคุม version ของเอกสาร
4. ถ้า UAT ไม่ผ่านบาง test case จะทำอย่างไร
5. ISO 9001 ต่างจาก ISO/IEC 27001 อย่างไร

<details><summary>เฉลย</summary>

1. Plan-Do-Check-Act วงจรปรับปรุงอย่างต่อเนื่อง
2. สิ่งที่ไม่เป็นไปตามข้อกำหนด ต้องบันทึก แก้ไข หาสาเหตุ และทำ corrective action ป้องกันการเกิดซ้ำ
3. ทุกคนใช้ฉบับล่าสุดที่อนุมัติ และย้อนตรวจการเปลี่ยนแปลงได้
4. บันทึกข้อบกพร่อง แก้ไข ทดสอบซ้ำ ถ้าแก้ไม่ทันให้ตกลงเงื่อนไขกับลูกค้าเป็นลายลักษณ์อักษร (เช่น รับมอบแบบมีเงื่อนไข)
5. ISO 9001 = ระบบบริหารคุณภาพ; ISO/IEC 27001 = ระบบบริหารความมั่นคงปลอดภัยสารสนเทศ
</details>

**5 โปรเจค**
- ⭐⭐ P1: Process flow งานติดตั้งตามแนว ISO 9001 (input, activity, output, record)
- ⭐⭐ P2: Document control register + naming/version convention
- ⭐⭐ P3: UAT template + defect log + ใบตรวจรับ
- ⭐⭐ P4: Handover document set (สารบัญ + template ทุกเอกสาร)
- ⭐⭐⭐ P5: Internal audit จำลอง: ตรวจโปรเจค lab ของตัวเองตาม checklist แล้วออก corrective action

---

## Level 99 — Career at ISC: ตำแหน่ง, Certificate & สัมภาษณ์

**ตำแหน่งที่เปิดรับ (จากเว็บไซต์)**

| ตำแหน่ง | ต้องรู้ | ทำ Level ไหนให้ครบ |
|---|---|---|
| Senior System Engineer (Infrastructure & Cloud) | Server, Storage, VMware, HCI, Cloud; 3–5 ปี; MCP/VCP | 1–8, 21–43, 57–73, 88–97 |
| Network & Security Engineer | Switching, Routing, NGFW, VPN, security audit; TCP/IP + routing protocol ลึก; CCNA / Fortinet | 1–20, 44–56, 88–94 |

**Certificate ที่สอดคล้องกับทีม ISC และตลาดปัจจุบัน**
- Network: Cisco CCNA → CCNP Enterprise, Aruba (HPE) ACA/ACP, Extreme, ALE, CWNA (Wi-Fi)
- Security: Fortinet Certified Associate/Professional (FCA/FCP, เดิมชื่อ NSE), Palo Alto PCNSA/PCNSE
- System/Virtualization: Microsoft (Azure Administrator AZ-104, Windows Server Hybrid Administrator), VMware VCP-DCV/VCF, Nutanix NCP-MCI
- Storage/Server: Dell/HPE certifications ตามสินค้า
- Service: ITIL 4 Foundation

**แบบทดสอบ (คำถามสัมภาษณ์ตามบริการของ ISC)**
1. ลูกค้าโรงพยาบาลแจ้งตอนตี 2 ว่า HIS ใช้ไม่ได้ทั้งโรงพยาบาล ทำอะไรใน 30 นาทีแรก
2. อธิบาย HCI ให้ผู้อำนวยการฟังใน 1 นาที
3. ออกแบบ redundancy ของ core network และ firewall ไม่ให้มี SPOF
4. Ransomware เข้ารหัส VM ทั้ง cluster ลูกค้าจะกู้คืนอย่างไรถ้าเรามี immutable backup
5. คุณจะเตรียมตัวสำหรับ SLA onsite 2 ชั่วโมงอย่างไร

<details><summary>แนวคำตอบ</summary>

1. รับเรื่อง/ยืนยัน P1 → แจ้งหัวหน้า → remote เข้าดู monitoring (network/server/storage/DB) → ถามการเปลี่ยนแปลงล่าสุด → เริ่ม workaround/escalate vendor → ส่งอัปเดตทุก 30 นาที → เตรียมเดินทาง onsite ถ้าจำเป็น
2. รวม server กับ storage เป็นกล่องเดียวที่จัดการจากหน้าจอเดียว เพิ่มทีละกล่องเมื่อโต ลดอุปกรณ์และค่าดูแล ระบบสำรองข้อมูลในตัว
3. Core คู่ (StackWise Virtual/VSF/MLAG), uplink คู่ LACP, FHRP, firewall HA A/P + link monitoring, ISP 2 ราย/2 เส้นทาง, PSU คู่ + UPS, ทดสอบ failover
4. Contain (ตัดเครือข่าย, รักษาหลักฐาน) → หา/ปิดจุดเข้า → reset credential → ตรวจ backup สะอาด → restore ตามลำดับความสำคัญจาก immutable copy → ตรวจสอบ → ทำ IR report
5. อะไหล่สำรองสำคัญ, เวรกะ/ทีมใกล้ไซต์, ข้อมูลลูกค้า/as-built พร้อม, remote access ที่ใช้งานได้, escalation matrix, vendor contract 4-hour
</details>

**5 โปรเจค**
- ⭐ P1: เลือกตำแหน่งเป้าหมาย + gap analysis ตัวเองกับ requirement
- ⭐⭐ P2: แผน cert 12 เดือนตามตำแหน่ง
- ⭐⭐ P3: Portfolio 10 ชิ้นจาก ISC-Track (เน้น capstone L20/L38/L43/L56/L62)
- ⭐⭐ P4: Mock interview 3 รอบ (เทคนิค, สถานการณ์ลูกค้า, ภาษาอังกฤษ)
- ⭐⭐⭐ P5: นำเสนอ solution 15 นาทีแบบ pre-sales ให้ "ลูกค้าภาครัฐ"

---

## Level 100 — Final Capstone: ลูกค้าองค์กรครบทุก Service Line ของ ISC

**โจทย์:** กระทรวงแห่งหนึ่ง (หรือโรงพยาบาลศูนย์) มีบุคลากร 3,000 คน หน่วยงานภูมิภาค 12 แห่ง ต้องการโครงการ 3 ปี:
1. **Enterprise Network:** core 100G แบบไม่มี SPOF, Wi-Fi 7, SD-WAN 12 แห่ง, bandwidth management
2. **Data Center:** ปรับปรุงห้อง DC (UPS, PAC, FM-200, access control), server/storage ใหม่
3. **HCI & Virtualization:** ย้าย VM 250 ตัวจาก VMware เดิมไป HCI
4. **Backup & DR:** immutable backup + DR site, RTO ระบบหลัก ≤ 1 ชม.
5. **Cybersecurity:** NGFW, ZTNA, segmentation, EDR, SIEM ตาม พ.ร.บ.ไซเบอร์/27001
6. **Cloud:** ย้ายเว็บบริการประชาชนไป cloud (data residency ในไทย)
7. **Mail:** ย้าย Exchange 2016 (หมด support) ไป M365 หรือ Zimbra
8. **Big Data:** dashboard ผู้บริหารจากระบบงานหลัก
9. **Support:** MA 24x7, onsite ≤ 2 ชม., PM รายไตรมาส, onsite engineer 2 คน

**ต้องส่งมอบ**
1. Discovery + current state + roadmap 3 ปี
2. HLD/LLD ทุก service line + ADR
3. TOR/spec ที่ไม่ล็อกยี่ห้อ + BOM 2 ทางเลือก + TCO
4. Project plan (งวดงาน, RACI, risk register) ตามแนว ISO 9001
5. Lab ย่อส่วน: network + HCI + backup/DR + NGFW + migration 2 VM + mail 5 mailbox
6. UAT + as-built + training
7. Operations: monitoring, ticket, PM checklist, monthly report, IR playbook

**แบบทดสอบสุดท้าย (Self-review)**
1. ทุก service line ตอบ requirement ที่วัดผลได้ และมีหลักฐานจากการทดสอบหรือไม่
2. Migration ทุกระบบ (VM, mail, web) มี runbook, rollback และ downtime ที่ยืนยันแล้วหรือไม่
3. ไม่มี SPOF ที่ไม่ได้ระบุเป็นความเสี่ยงที่ลูกค้ารับทราบ
4. ทีม support รับเรื่อง P1 ตอนตี 2 แล้วแก้ได้จากเอกสาร/monitoring ที่ส่งมอบหรือไม่
5. ผู้บริหารลูกค้าอ่าน report แล้วเข้าใจความเสี่ยง ค่าใช้จ่าย และสิ่งที่ได้รับ

**5 โปรเจค (Capstone 5 ระยะ)**
- ⭐⭐⭐ P1: **Consult & Pre-sales:** discovery, roadmap, TOR/spec, proposal
- ⭐⭐⭐ P2: **Design:** HLD/LLD 9 service line + sizing + BOM/TCO
- ⭐⭐⭐ P3: **Build & Migrate:** lab implementation + migration + security
- ⭐⭐⭐ P4: **Quality & Handover:** UAT, as-built, training, ตรวจรับตาม ISO 9001
- ⭐⭐⭐ P5: **Operate 24x7:** จำลอง 1 เดือน (ticket, PM, P1 incident, monthly report, QBR)

🎓 **จบ ISC-Track Level 100** — ครอบคลุมทุก service line ที่ ISC ให้บริการตามเว็บไซต์
