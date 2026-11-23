# Part 4 — บริการสนับสนุน 24x7 (Support & Maintenance) ตอน A: Incident & Troubleshooting (Level 81–90)

> ตามบริการ: **ทีมวิศวกรผู้เชี่ยวชาญพร้อมดูแลระบบฉุกเฉินและบำรุงรักษาเชิงป้องกันตลอดเวลา**

---

## Level 81 — Service Mindset, SLA & Severity

**สิ่งที่ต้องรู้**
- SLA (กับลูกค้า), OLA (ภายในทีม), UC (underpinning contract กับ vendor)
- Severity/Priority: P1 ระบบหลักล่มทั้งหมด, P2 กระทบมากแต่มีทางเลี่ยง, P3 กระทบบางส่วน, P4 คำถาม/คำขอ
- เวลา: Response time, On-site time, Workaround time, Resolution time; 24x7 vs 8x5
- Impact × Urgency = Priority
- ทัศนคติ: ลูกค้าอยู่ในภาวะกดดัน — สื่อสารชัด, สุภาพ, ไม่โทษใคร, ไม่สัญญาเกินจริง

**แบบทดสอบ**
1. SLA กับ OLA ต่างกันอย่างไร
2. Core switch ของลูกค้าล่ม ทั้งสำนักงานใช้งานไม่ได้ คือ priority อะไร
3. Response time กับ Resolution time ต่างกันอย่างไร
4. ทำไม SI ต้องมี UC กับ vendor
5. ประโยคที่ไม่ควรพูดกับลูกค้าระหว่าง P1

<details><summary>เฉลย</summary>

1. SLA = ข้อตกลงกับลูกค้า; OLA = ข้อตกลงระหว่างทีมภายในเพื่อให้ทำ SLA ได้
2. P1 (Critical)
3. Response = เวลาที่ตอบรับและเริ่มดำเนินการ; Resolution = เวลาที่แก้หรือกู้คืนบริการได้
4. SLA ที่ให้ลูกค้าต้องมี vendor support (อะไหล่ 4 ชม., TAC) รองรับ
5. "ไม่รู้ว่าจะเสร็จเมื่อไร", "เป็นปัญหาของ vendor ไม่เกี่ยวกับเรา", "น่าจะมีคนในทีมคุณไปแก้อะไร" (ควรให้ข้อเท็จจริงและเวลาอัปเดตครั้งถัดไป)
</details>

**5 โปรเจค**
- ⭐ P1: Severity matrix (ตัวอย่างเหตุการณ์ 20 ข้อ จัด P1–P4)
- ⭐⭐ P2: SLA template 3 ระดับ (Gold/Silver/Bronze) พร้อมเวลาแต่ละ priority
- ⭐⭐ P3: Mapping SLA ลูกค้า ↔ สัญญา vendor (UC) ของอุปกรณ์ทุกชิ้น
- ⭐⭐ P4: Role play รับแจ้ง P1 ทางโทรศัพท์ (บันทึก + feedback)
- ⭐⭐ P5: สคริปต์คำนวณ SLA compliance จาก ticket export (CSV)

---

## Level 82 — ITIL 4 สำหรับทีม Support

> พื้นฐานจาก Roadmap หลัก [L95](../10-expert-career.md)

**สิ่งที่ต้องรู้**
- Practices: Service Desk, Incident, Problem, Change Enablement, Service Request, Knowledge, Monitoring & Event, Service Level, Configuration (CMDB)
- Incident = กู้บริการให้เร็วที่สุด; Problem = หา root cause และป้องกันซ้ำ; Known error + workaround
- Major Incident process: incident commander, war room/bridge call, communication cadence
- Change: standard / normal / emergency (ECAB)
- Continual improvement

**แบบทดสอบ**
1. Incident กับ Problem ต่างกันอย่างไร
2. Known error คืออะไร
3. Major incident ต้องมีบทบาทอะไร
4. Emergency change ต่างจาก normal change อย่างไร
5. CMDB ช่วย Support อย่างไร

<details><summary>เฉลย</summary>

1. Incident = เหตุที่ต้องกู้บริการ; Problem = สาเหตุของ incident (อาจเกิดซ้ำหลายครั้ง)
2. Problem ที่รู้ root cause แล้วแต่ยังแก้ถาวรไม่ได้ มี workaround
3. Incident commander/manager, technical lead, communication lead, ผู้บันทึก
4. ทำทันทีเพื่อแก้เหตุฉุกเฉิน อนุมัติโดย ECAB/ผู้มีอำนาจแบบเร็ว แล้วบันทึกย้อนหลัง
5. รู้ว่า CI ไหนเชื่อมกับอะไร ประเมินผลกระทบและหาสาเหตุได้เร็ว
</details>

**5 โปรเจค**
- ⭐ P1: Flowchart incident → problem → change
- ⭐⭐ P2: Major incident procedure (บทบาท, ช่องทาง, ความถี่การอัปเดต)
- ⭐⭐ P3: Problem record ตัวอย่าง 3 เคส (เกิดซ้ำ → RCA → fix)
- ⭐⭐ P4: Standard change catalog 10 รายการของทีม Network/DC
- ⭐⭐ P5: สรุป ITIL 4 Foundation เป็นภาษาไทย + ข้อสอบตัวอย่าง 20 ข้อ

---

## Level 83 — Ticketing & Documentation ระหว่างทำงาน

**สิ่งที่ต้องรู้**
- เครื่องมือ: ServiceNow, Jira Service Management, Zendesk, Freshservice, GLPI, iTop
- Ticket ที่ดี: อาการ, ผลกระทบ, เวลาเริ่ม, สิ่งที่ตรวจแล้ว (คำสั่ง + ผล), สิ่งที่ทำ, สถานะ, next action
- Work note (ภายใน) vs customer-facing note
- Categorization, assignment group, SLA timer, pending reason
- Closing: resolution code, root cause (ถ้ารู้), ยืนยันกับลูกค้า

**แบบทดสอบ**
1. ทำไมต้องบันทึกคำสั่งและผลที่ตรวจไว้ใน ticket
2. ข้อมูลอะไรห้ามใส่ใน customer-facing note
3. Pending reason มีผลกับ SLA อย่างไร
4. Ticket ที่ปิดโดยเขียนว่า "แก้แล้ว" มีปัญหาอะไร
5. ทำไมต้องจัด category ให้ถูก

<details><summary>เฉลย</summary>

1. คนรับต่อ (shift ถัดไป/escalation) ไม่ต้องทำซ้ำ และใช้ทำ RCA/knowledge
2. รหัสผ่าน, ข้อมูลภายใน, ความเห็นส่วนตัว, การโทษผู้อื่น
3. หยุดนับ SLA เมื่อรอข้อมูลจากลูกค้า (ตามสัญญา) — ต้องใช้อย่างซื่อสัตย์
4. ไม่มีความรู้สำหรับครั้งหน้า วิเคราะห์ปัญหาซ้ำไม่ได้
5. ใช้ทำรายงาน/แนวโน้ม และจัดคิวไปทีมที่ถูก
</details>

**5 โปรเจค**
- ⭐ P1: ติดตั้ง GLPI หรือ Jira SM (free) ตั้ง category, SLA และ assignment group
- ⭐⭐ P2: Ticket writing guideline + ตัวอย่างดี/ไม่ดี 5 คู่
- ⭐⭐ P3: Email/Webhook → สร้าง ticket อัตโนมัติจาก monitoring alert
- ⭐⭐ P4: Ticket template ตามประเภทปัญหา (network down, VPN, storage, firewall)
- ⭐⭐⭐ P5: Dashboard ticket (open by priority, SLA breach, aging) จาก API

---

## Level 84 — NOC Monitoring 24x7

> พื้นฐานจาก Roadmap หลัก [L86](../09-automation-operations.md)

**สิ่งที่ต้องรู้**
- เครื่องมือ: Zabbix, PRTG, LibreNMS, SolarWinds, Datadog, Grafana + Prometheus, vendor tools (FortiAnalyzer, Prism, vCenter, OpenManage)
- Multi-tenant monitoring สำหรับหลายลูกค้า (proxy/collector ที่ไซต์ลูกค้า + VPN กลับ NOC)
- Event → alert → dedupe/correlation → ticket → on-call
- สิ่งที่ต้อง monitor: availability, interface/error, CPU/mem/temp, HA status, BGP/VPN tunnel, storage capacity/latency, backup job, cert expiry, license expiry
- Dashboard บนจอ NOC, alert severity

**แบบทดสอบ**
1. ทำไม monitoring หลายลูกค้าต้องใช้ proxy/collector ที่ไซต์
2. Alert ที่ควรเป็น P1 อัตโนมัติ 3 ตัวอย่าง
3. ทำไมต้อง monitor HA status ไม่ใช่แค่ up/down
4. Alert storm คืออะไร แก้อย่างไร
5. ทำไมต้อง monitor วันหมดอายุของ license/cert

<details><summary>เฉลย</summary>

1. เก็บข้อมูลในเครือข่ายลูกค้าแล้วส่งกลับผ่านช่องทางเดียวที่ปลอดภัย ไม่ต้องเปิด port มาก
2. Core/firewall ทั้งคู่ HA ล่ม, storage controller ล่ม/ datastore เต็ม, ISP หลักและสำรองขาดพร้อมกัน
3. ถ้าเครื่องสำรองเสียแบบเงียบ ระบบยัง up แต่ไม่มี redundancy เหลือ
4. Alert จำนวนมากจากต้นเหตุเดียว (เช่น uplink ขาด) แก้ด้วย dependency/parent-child, correlation, suppression
5. License/cert หมดทำให้บริการหยุด (VPN, HTTPS, security subscription)
</details>

**5 โปรเจค**
- ⭐⭐ P1: Zabbix + proxy จำลอง 2 ลูกค้า (multi-tenant)
- ⭐⭐ P2: Template monitoring FortiGate (HA, VPN, session), Nutanix/vCenter, Veeam job
- ⭐⭐ P3: Dependency/trigger ป้องกัน alert storm
- ⭐⭐ P4: NOC wall dashboard (Grafana) ภาพรวมทุกลูกค้า
- ⭐⭐⭐ P5: Alert → ticket → LINE/Teams on-call + escalation หากไม่มีคนรับใน 15 นาที

---

## Level 85 — First Response & Triage

**สิ่งที่ต้องรู้**
- 5W1H: อะไร, ใคร (กี่คน/ที่ไหน), เมื่อไร, มีอะไรเปลี่ยนล่าสุด, ทำอะไรไปแล้ว, กระทบธุรกิจอย่างไร
- เข้าระบบลูกค้า: VPN/jump host/remote tool ที่ได้รับอนุญาต (ไม่ใช้ช่องทางลับ), MFA, บันทึก session
- Quick health check ตาม checklist: monitoring, interface, HA, log ล่าสุด, change ล่าสุด
- ตัดสินใจ: แก้เองได้ / escalate / เรียก on-site / เปิด vendor case
- Golden rule: **กู้บริการก่อน (workaround) แล้วค่อยหา root cause** แต่เก็บหลักฐานไว้ก่อนแก้ถ้าทำได้

**แบบทดสอบ**
1. คำถามสำคัญที่สุดตอนรับแจ้ง
2. ทำไมต้องเก็บหลักฐาน (log/show tech) ก่อน reboot
3. เมื่อไรควร escalate ทันที
4. ทำไมห้ามใช้ remote tool ที่ไม่ได้รับอนุญาต
5. ข้อมูลอะไรที่ควรมีพร้อมก่อนโทรหาลูกค้ากลับ

<details><summary>เฉลย</summary>

1. "มีอะไรเปลี่ยนแปลงล่าสุดบ้าง" และขอบเขตผลกระทบ
2. Reboot ล้าง state/log ใน memory ทำให้หา root cause และเปิด vendor case ยาก
3. P1 ที่เกินขีดความสามารถ/เวลาที่กำหนด, ต้องใช้สิทธิ์/ความรู้เฉพาะ, สงสัย security incident
4. ผิดนโยบาย/สัญญา เสี่ยงความปลอดภัยของลูกค้า และไม่มี audit trail
5. ข้อมูลสัญญา/SLA, topology/as-built, contact, ticket ก่อนหน้า, change ล่าสุด
</details>

**5 โปรเจค**
- ⭐ P1: Triage question card (โทรศัพท์/แชท) สำหรับ 10 อาการ
- ⭐⭐ P2: Quick health check script (network + server + storage) ที่ให้ผลใน 1 นาที
- ⭐⭐ P3: "Collect before you fix" script: เก็บ show tech/log bundle อัตโนมัติ (Cisco, FortiGate, Linux)
- ⭐⭐ P4: Escalation matrix (ระดับ, เวลา, ใคร, ช่องทาง) ของทีม
- ⭐⭐⭐ P5: Simulation 5 เคส (เพื่อนเป็นลูกค้า) จับเวลา response และประเมินการสื่อสาร

---

## Level 86 — Troubleshooting Network & Security Incidents

> พื้นฐานจาก Roadmap หลัก [L30](../03-tools-and-troubleshooting.md), [L91](../10-expert-career.md)

**สิ่งที่ต้องรู้**
- เคสยอดฮิต: internet ล่ม (ISP/firewall/route), VPN site-to-site หลุด, remote VPN เข้าไม่ได้, Wi-Fi ช้า, loop/broadcast storm, DHCP/DNS ล่ม, HA firewall failover
- Firewall: `diagnose debug flow`, session table, policy hit, CPU/memory/conserve mode (FortiGate), dataplane counters (Palo Alto)
- VPN: phase 1/2 status, DPD, NAT-T, peer IP เปลี่ยน, PSK/cert หมดอายุ
- Loop: CPU switch สูง, MAC flapping, STP TCN → หา port ที่ทำ loop
- Security incident ระหว่าง support (traffic ผิดปกติ, account ถูกยึด) → ส่งต่อ IR process (L57)

**แบบทดสอบ**
1. FortiGate เข้า conserve mode หมายถึงอะไร
2. VPN หลุดทุก 8 ชั่วโมงสม่ำเสมอ สงสัยอะไร
3. อาการ broadcast storm และวิธีหาต้นเหตุ
4. Internet ล่มทั้งองค์กร ตรวจอะไรตามลำดับ
5. ระหว่างแก้ปัญหาพบว่ามี traffic ไป IP ต่างประเทศจำนวนมากผิดปกติ ควรทำอย่างไร

<details><summary>เฉลย</summary>

1. Memory ใกล้เต็ม ระบบจำกัดการทำงาน (อาจหยุดตรวจ security profile หรือ drop session ใหม่)
2. Lifetime/rekey ไม่ตรงกัน หรือ DPD/idle timeout ของอีกฝั่ง
3. ไฟ switch กระพริบถี่, CPU สูง, เครือข่ายช้ามาก — ดู MAC flapping log, interface ที่ broadcast สูง, TCN ล่าสุด แล้วไล่ปิดพอร์ต
4. Link/ONT → interface WAN ของ firewall → ping gateway ISP → ping IP ภายนอก (8.8.8.8) → DNS → policy/NAT → ติดต่อ ISP
5. เก็บหลักฐาน, แจ้งหัวหน้า/ทีม security, ทำตาม IR process (อาจ contain), ไม่ลบหลักฐาน
</details>

**5 โปรเจค**
- ⭐⭐ P1: Runbook 10 เคส network/security ยอดฮิต
- ⭐⭐ P2: Lab break/fix FortiGate: VPN, NAT, policy, routing (เพื่อน break)
- ⭐⭐ P3: Lab broadcast storm + ฝึกหา port ภายใน 5 นาที
- ⭐⭐⭐ P4: Packet capture หลายจุดหาสาเหตุเว็บบางเว็บช้า (MTU/MSS)
- ⭐⭐⭐ P5: Incident report ฉบับส่งลูกค้าจากเคสใน lab

---

## Level 87 — Troubleshooting Server, Storage & Virtualization Incidents

**สิ่งที่ต้องรู้**
- Server: hardware fault (ดิสก์, PSU, DIMM) จาก iDRAC/iLO log, เครื่อง boot ไม่ขึ้น, firmware bug
- VMware: host disconnected, PSOD (เก็บ core dump), datastore เต็ม, APD/PDL (storage หาย), snapshot ค้าง, HA ไม่ทำงาน
- Nutanix: CVM down, cluster health (NCC checks), disk/node failure, metadata ring
- Storage: path down, latency สูง (หา noisy VM), controller failover, LUN เต็ม (thin)
- Backup job fail: เต็ม, credential หมดอายุ, snapshot ค้าง, network
- เครื่องมือ: `esxtop`, vmkernel.log, `ncc health_checks run_all`, log bundle

**แบบทดสอบ**
1. APD กับ PDL ต่างกันอย่างไร
2. Datastore เต็มทำให้เกิดอะไรกับ VM
3. หา VM ที่ทำ storage latency สูงอย่างไร
4. NCC คืออะไร
5. PSOD แล้วต้องเก็บอะไรก่อนเปิด case

<details><summary>เฉลย</summary>

1. APD = storage หายชั่วคราวไม่รู้สาเหตุ (รอ); PDL = storage แจ้งว่า device หายถาวร
2. VM ที่ต้องเขียน (thin/snapshot) จะ pause/freeze
3. esxtop (แสดงผลแบบ disk VM), vCenter performance, storage array per-volume stats, Prism VM IO
4. Nutanix Cluster Check: ตรวจสุขภาพ cluster หลายร้อยรายการ
5. รูปหน้าจอ PSOD (iDRAC/iLO console), core dump, vm-support log bundle, version/build
</details>

**5 โปรเจค**
- ⭐⭐ P1: Runbook 10 เคส virtualization/storage ยอดฮิต
- ⭐⭐ P2: Lab: ทำ datastore เต็ม/snapshot ค้าง แล้วแก้
- ⭐⭐ P3: esxtop/iostat cheat sheet + เกณฑ์ค่า "ผิดปกติ"
- ⭐⭐ P4: สคริปต์เก็บ log bundle (vm-support/ncc/sosreport) อัตโนมัติ
- ⭐⭐⭐ P5: จำลองดิสก์เสียใน Ceph/Nutanix CE แล้วทำขั้นตอนเปลี่ยนดิสก์ครบ

---

## Level 88 — Vendor Escalation, TAC & RMA

**สิ่งที่ต้องรู้**
- เปิด case: serial/contract, severity, อาการ, timeline, สิ่งที่ทำแล้ว, log/show tech, topology
- ช่องทาง: portal (Cisco SCM, Fortinet Support, Palo Alto CSP, Dell/HPE/Nutanix/VMware/Broadcom support), โทรสำหรับ Sev1
- RMA: ยืนยันอาการ, ข้อมูลส่งของ, อะไหล่ 4-hour/NBD, ส่งคืนอะไหล่เสีย, ลบข้อมูล (disk retention option)
- Escalate case ใน vendor (duty manager) เมื่อไม่คืบ
- ติดตาม case อย่างสม่ำเสมอ และสื่อสารกับลูกค้าแทน

**แบบทดสอบ**
1. ข้อมูลอะไรต้องมีตอนเปิด case
2. ทำไมต้องเปิด Sev1 ทางโทรศัพท์
3. Disk retention option คืออะไร
4. Case ค้างไม่คืบ 2 วัน ควรทำอะไร
5. ทำไมต้องตรวจสัญญา support ก่อนหมดอายุ

<details><summary>เฉลย</summary>

1. Serial/contract, version, severity, อาการ, timeline, impact, สิ่งที่ทำแล้ว, log/show tech
2. ได้วิศวกรรับทันที (portal อาจคิวนาน)
3. สิทธิ์ไม่ต้องคืนดิสก์ที่เสีย (ข้อมูลไม่ออกนอกองค์กร)
4. Escalate ผ่าน duty manager/account team ของ vendor และแจ้งลูกค้า
5. ถ้าหมดจะเปิด case/RMA ไม่ได้ ผิด SLA ที่ให้ลูกค้า
</details>

**5 โปรเจค**
- ⭐ P1: Vendor case template (ภาษาอังกฤษ) + ตัวอย่าง 3 เคส
- ⭐⭐ P2: Vendor contact & portal directory ของทุก vendor ที่ทีมใช้
- ⭐⭐ P3: Contract/warranty tracker + แจ้งเตือนก่อนหมด 90/60/30 วัน
- ⭐⭐ P4: RMA process flow (รวมการเปลี่ยนอะไหล่หน้างานและการคืนของ)
- ⭐⭐ P5: Role play โทรเปิด Sev1 กับ "TAC" เป็นภาษาอังกฤษ

---

## Level 89 — Remote Support Infrastructure & Security

**สิ่งที่ต้องรู้**
- ช่องทางเข้าระบบลูกค้า: site-to-site VPN ไป NOC, ZTNA, jump host ที่ไซต์ลูกค้า, PAM (CyberArk, Delinea, BeyondTrust)
- Credential management: password vault (Bitwarden/Vaultwarden, 1Password, KeePass ทีม), ห้ามใช้ shared account แบบไม่บันทึก
- Session recording, MFA, least privilege, ลูกค้าอนุมัติการเข้าถึง
- ความเสี่ยง supply chain: MSP ถูกเจาะ → ลูกค้าทุกรายเสี่ยง
- Endpoint ของทีม support: EDR, disk encryption, แยกเครื่องทำงาน

**แบบทดสอบ**
1. ทำไม MSP เป็นเป้าหมายของผู้โจมตี
2. PAM ช่วยอะไร
3. ทำไมไม่ควรเก็บรหัสลูกค้าในไฟล์ Excel
4. Session recording มีประโยชน์อย่างไร
5. เมื่อพนักงาน support ลาออกต้องทำอะไร

<details><summary>เฉลย</summary>

1. เจาะได้ที่เดียว เข้าถึงลูกค้าได้หลายราย (supply chain)
2. ควบคุม/บันทึก/หมุนรหัสบัญชีสิทธิ์สูง และให้สิทธิ์เฉพาะช่วงเวลา
3. ไม่เข้ารหัส ไม่มี audit ว่าใครเปิด แชร์ต่อได้ง่าย
4. Audit, หลักฐานเมื่อเกิดข้อพิพาท, ใช้ฝึกทีม
5. ปิดบัญชีทั้งหมด, หมุนรหัสที่เคยเข้าถึง, เก็บอุปกรณ์คืน, ตรวจ access log
</details>

**5 โปรเจค**
- ⭐⭐ P1: Vaultwarden สำหรับทีม + collection แยกตามลูกค้า + MFA
- ⭐⭐ P2: Apache Guacamole jump host + MFA + session recording
- ⭐⭐ P3: Remote access policy ของทีม Support (เอกสารให้ลูกค้าเซ็น)
- ⭐⭐ P4: Offboarding checklist + สคริปต์หาบัญชีของคนลาออก
- ⭐⭐⭐ P5: Design remote support architecture สำหรับ 20 ลูกค้า (NOC ↔ ลูกค้า)

---

## Level 90 — Communication ระหว่างเหตุการณ์

**สิ่งที่ต้องรู้**
- Incident update template: สถานะ, ผลกระทบ, สิ่งที่ทำ, ขั้นต่อไป, เวลาอัปเดตครั้งถัดไป
- ความถี่: P1 ทุก 30–60 นาที แม้ไม่มีความคืบหน้า
- สื่อสารตามผู้ฟัง: ผู้บริหาร (ผลกระทบ/ETA), IT ลูกค้า (เทคนิค), ผู้ใช้ (สิ่งที่ต้องทำ)
- ภาษาไทยทางการ + ภาษาอังกฤษสำหรับ vendor/ลูกค้าต่างชาติ
- หลังเหตุการณ์: incident report ภายในเวลาที่สัญญากำหนด (เช่น 3–5 วันทำการ)

**แบบทดสอบ**
1. องค์ประกอบของ incident update ที่ดี
2. ทำไมต้องอัปเดตแม้ไม่มีความคืบหน้า
3. สิ่งที่ผู้บริหารต้องการรู้
4. ทำไมห้ามให้ ETA ที่ไม่มั่นใจ
5. Incident report หลังเหตุการณ์ต้องมีอะไร

<details><summary>เฉลย</summary>

1. สถานะปัจจุบัน, ผลกระทบ, สิ่งที่ทำไปแล้ว, ขั้นต่อไป, เวลาอัปเดตครั้งถัดไป
2. ลูกค้ารู้ว่ายังมีคนทำงานอยู่ ลดความกังวลและการโทรตามซ้ำ
3. ผลกระทบต่อธุรกิจ, เมื่อไรกลับมา, ต้องตัดสินใจอะไรไหม, ป้องกันซ้ำอย่างไร
4. ถ้าพลาดจะเสียความเชื่อมั่น ควรบอกเป็นช่วงหรือบอกเวลาอัปเดตครั้งถัดไปแทน
5. Summary, timeline, impact, root cause, การแก้ชั่วคราว/ถาวร, action items, ผู้รับผิดชอบ/วันที่
</details>

**5 โปรเจค**
- ⭐ P1: Template update (ไทย/อังกฤษ) สำหรับ email, LINE, Teams
- ⭐⭐ P2: ฝึกเขียน update 5 รอบของ P1 จำลอง (ให้เพื่อนประเมิน)
- ⭐⭐ P3: Incident report template + ตัวอย่างเต็ม 1 ฉบับ
- ⭐⭐ P4: Status page (Uptime Kuma/Cachet) สำหรับแจ้งลูกค้า
- ⭐⭐⭐ P5: Executive briefing 5 นาทีหลัง P1 (สไลด์ 3 หน้า) แล้วฝึกนำเสนอ
