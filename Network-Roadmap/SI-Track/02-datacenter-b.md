# Part 1 — วางระบบศูนย์ข้อมูล (Data Center) ตอน B: Backup, DR, DC Network & Delivery (Level 31–40)

---

## Level 31 — Backup & Recovery

**สิ่งที่ต้องรู้**
- กฎ 3-2-1-1-0: 3 สำเนา, 2 สื่อ, 1 นอกสถานที่, 1 immutable/offline, 0 error (ต้อง verify)
- ประเภท: full, incremental, differential, synthetic full, forever-forward incremental
- Software: Veeam, Commvault, Veritas NetBackup, Rubrik, Cohesity, Nakivo
- Repository: disk, deduplication appliance (Data Domain), hardened Linux repository, tape (LTO), object storage (S3 Object Lock)
- Application-aware backup (SQL, Exchange, AD), instant VM recovery, file-level restore
- Ransomware: immutable, air gap, MFA บน backup console, แยก account/domain

**แบบทดสอบ**
1. อธิบาย 3-2-1-1-0
2. Incremental ต่างจาก Differential อย่างไร
3. ทำไม backup server ไม่ควร join domain เดียวกับ production
4. Immutable backup ป้องกันอะไร
5. ทำไมต้องทดสอบ restore สม่ำเสมอ

<details><summary>เฉลย</summary>

1. 3 สำเนา, 2 สื่อต่างชนิด, 1 นอกสถานที่, 1 immutable หรือ offline, 0 error จากการ verify
2. Incremental เก็บเฉพาะที่เปลี่ยนจาก backup ครั้งล่าสุด; Differential เก็บที่เปลี่ยนจาก full ครั้งล่าสุด
3. ถ้า domain ถูกยึด ผู้โจมตีจะลบ backup ได้ด้วย
4. ป้องกันการลบหรือเข้ารหัส backup ภายในช่วงเวลาที่กำหนด (ransomware, คนในทำผิด)
5. Backup ที่ไม่เคย restore ไม่รู้ว่าใช้ได้จริงหรือไม่ และจะไม่รู้เวลา RTO จริง
</details>

**5 โปรเจค**
- ⭐ P1: Veeam Community Edition (ฟรี) backup VM ใน lab แล้ว restore ไฟล์และทั้ง VM
- ⭐⭐ P2: Hardened Linux Repository (immutable) สำหรับ Veeam
- ⭐⭐ P3: Backup copy ไป S3-compatible (MinIO) พร้อม Object Lock
- ⭐⭐ P4: Backup policy document (ระดับข้อมูล, retention, RPO, schedule)
- ⭐⭐⭐ P5: Ransomware recovery drill: จำลอง VM โดนเข้ารหัส แล้ว restore จาก immutable copy พร้อมจับเวลา RTO

---

## Level 32 — Disaster Recovery

**สิ่งที่ต้องรู้**
- BIA (Business Impact Analysis), RTO/RPO ตามระบบ, BCP vs DRP
- DR site: hot/warm/cold, DR in cloud (DRaaS)
- Replication: storage-based, hypervisor-based (vSphere Replication, Zerto, Veeam Replication, Nutanix Protection Domain/Leap), application-based (AG, Data Guard)
- Orchestration: VMware SRM / Live Site Recovery, Zerto, Nutanix Leap; recovery plan, re-IP vs stretched network
- DR drill: test failover แบบไม่กระทบ production (isolated network), failback

**แบบทดสอบ**
1. BIA ได้ผลลัพธ์อะไร
2. ข้อดีของ DR orchestration
3. Re-IP กับ stretched L2 ต่างกันอย่างไร
4. Test failover ควรทำใน network แบบไหน
5. Failback คืออะไร ทำไมมักถูกลืม

<details><summary>เฉลย</summary>

1. ความสำคัญของแต่ละระบบ, ผลกระทบเมื่อหยุด, RTO/RPO ที่ต้องการ
2. ลำดับการเปิดระบบอัตโนมัติ, re-IP อัตโนมัติ, ทดสอบได้ซ้ำ, ลด human error
3. Re-IP เปลี่ยน IP ที่ DR (ต้องแก้ DNS/app); stretched L2 ใช้ IP เดิม (ซับซ้อน, failure domain ใหญ่)
4. Isolated/bubble network เพื่อไม่ให้ IP ชนกับ production
5. ย้ายกลับมา site หลักหลังเหตุการณ์จบ ต้องมี reverse replication และแผนรองรับ
</details>

**5 โปรเจค**
- ⭐⭐ P1: BIA template + ตัวอย่าง 10 ระบบ (ERP, email, file, web…)
- ⭐⭐ P2: Veeam Replication หรือ Proxmox replication ระหว่าง 2 host (จำลอง 2 site)
- ⭐⭐ P3: DR runbook ของระบบ 3 tier (ลำดับเปิด, DNS, ตรวจสอบ)
- ⭐⭐⭐ P4: DR drill จริงใน lab: failover → ตรวจ app → failback แล้วเขียนรายงาน RTO/RPO ที่ได้
- ⭐⭐⭐ P5: DR design เสนอลูกค้า 3 ทางเลือก (DR site เอง / colocation / DRaaS) พร้อมราคาและความเสี่ยง

---

## Level 33 — Data Center Network: Spine-Leaf & Server Connectivity

> พื้นฐานจาก Roadmap หลัก [L73](../08-datacenter-cloud.md)

**สิ่งที่ต้องรู้**
- 3-tier เดิม → spine-leaf, ToR switch คู่ (vPC/MLAG) สำหรับ server dual-homed
- รุ่นที่เจอในงาน SI: Cisco Nexus, Arista, Dell PowerSwitch, HPE Aruba CX, Huawei CloudEngine
- Server connectivity: 2×25G data + 1G iDRAC; DAC/AOC/SFP28; breakout 100G → 4×25G
- Teaming บน hypervisor: active/active ด้วย port ID/LBT หรือ LACP ผ่าน MLAG
- Border leaf → firewall → WAN/Internet; OOB management switch แยก

**แบบทดสอบ**
1. ทำไม server ต้องต่อ ToR 2 ตัว
2. vPC/MLAG ต้องมีลิงก์อะไรระหว่าง ToR คู่
3. DAC กับ AOC ต่างกันอย่างไร
4. Breakout cable ใช้ทำอะไร
5. ทำไมต้องมี OOB management switch

<details><summary>เฉลย</summary>

1. ToR ตัวใดเสียหรือ upgrade ได้โดย server ไม่หลุด
2. Peer-link (และ peer-keepalive)
3. DAC = สายทองแดง twinax (สั้น ถูก กินไฟน้อย); AOC = สาย optical หัวติดตาย (ยาวกว่า)
4. แบ่งพอร์ต 100G เป็น 4×25G (หรือ 40G → 4×10G)
5. ยังเข้าจัดการอุปกรณ์ได้แม้ production network ล่ม
</details>

**5 โปรเจค**
- ⭐⭐ P1: Containerlab spine-leaf + MLAG (Arista cEOS) + Linux server bond LACP
- ⭐⭐ P2: Port map/cabling plan สำหรับ 2 rack (server, storage, ToR, OOB)
- ⭐⭐ P3: BOM network DC สำหรับ 16 host (ToR, SFP, DAC, OOB) และเหตุผลการเลือก
- ⭐⭐ P4: Config template ToR (VLAN, MLAG, port profile ของ server) ด้วย Jinja2
- ⭐⭐⭐ P5: ทดสอบ failover: ปิด ToR 1 ตัวระหว่าง vMotion/iperf แล้ววัด packet loss

---

## Level 34 — DC Fabric & SDN: VXLAN-EVPN, Cisco ACI, VMware NSX

> พื้นฐานจาก Roadmap หลัก [L74](../08-datacenter-cloud.md), [L88](../09-automation-operations.md)

**สิ่งที่ต้องรู้**
- VXLAN-EVPN fabric (NX-OS, EOS, SONiC), anycast gateway, multi-tenant VRF
- Cisco ACI: APIC, tenant/VRF/BD/EPG, contract, L3Out
- VMware NSX: overlay segment, T0/T1 gateway, Distributed Firewall (DFW)
- Multi-site / DCI: EVPN multi-site, ACI Multi-Site, NSX Federation
- Fabric management: Nexus Dashboard, Arista CloudVision, Juniper Apstra

**แบบทดสอบ**
1. EPG ใน ACI เทียบได้กับอะไรในเครือข่ายทั่วไป
2. Contract ใน ACI ทำหน้าที่อะไร
3. NSX DFW ต่างจาก firewall ปกติอย่างไร
4. T0 กับ T1 gateway ต่างกันอย่างไร
5. ทำไม DCI ไม่ควรขยาย L2 ไปทุก VLAN

<details><summary>เฉลย</summary>

1. กลุ่ม endpoint ที่มี policy เดียวกัน (คล้าย VLAN/security group)
2. Policy อนุญาต traffic ระหว่าง EPG (default deny)
3. บังคับ policy ที่ vNIC ของ VM ทุกตัว (east-west, micro-segmentation)
4. T0 เชื่อมภายนอก (north-south, BGP); T1 เป็น gateway ของ tenant/segment
5. Broadcast domain ใหญ่ ปัญหาลามข้าม site (failure domain ใหญ่)
</details>

**5 โปรเจค**
- ⭐⭐⭐ P1: EVPN-VXLAN fabric 2 spine 4 leaf (cEOS/SR Linux) + 2 VRF
- ⭐⭐ P2: Cisco DevNet ACI Sandbox: สร้าง tenant, BD, EPG และ contract
- ⭐⭐ P3: NSX hands-on lab (VMware HOL ฟรี): segment, T1 และ DFW rule
- ⭐⭐ P4: เปรียบเทียบ ACI / NSX / EVPN แบบ open (ราคา, ความซับซ้อน, ทักษะทีม)
- ⭐⭐⭐ P5: ออกแบบ DCI 2 site (DC/DR) สำหรับลูกค้า พร้อมเหตุผล L2 vs L3

---

## Level 35 — DC Security & Segmentation พื้นฐาน

**สิ่งที่ต้องรู้**
- Zone: DMZ, App, DB, Management, Backup, Storage; north-south firewall + east-west segmentation
- Management plane: jump host, MFA, PAM, ไม่เปิด iDRAC/vCenter/Prism ให้ user LAN
- Hardening: vSphere Security Configuration Guide, Nutanix SCMA, CIS Benchmark
- Backup network และ storage network ห้าม route ปะปน
- เชื่อมไปต่อที่ Part 2 (Zero Trust Segmentation)

**แบบทดสอบ**
1. ทำไม vCenter/iDRAC ไม่ควรเข้าถึงได้จาก user VLAN
2. East-west กับ north-south traffic ต่างกันอย่างไร
3. PAM คืออะไร
4. ใครควรเข้าถึง backup console ได้บ้าง
5. ตัวอย่าง hardening ESXi 3 ข้อ

<details><summary>เฉลย</summary>

1. เป็นเป้าหมายหลักของ ransomware: ยึด vCenter ได้ก็เข้ารหัส VM ได้ทั้งหมด
2. East-west = ภายใน DC (server ↔ server); north-south = เข้าออก DC
3. Privileged Access Management: ควบคุม, บันทึก และหมุนรหัสบัญชีสิทธิ์สูง
4. เฉพาะทีม backup ผ่าน MFA จาก jump host แยก account จาก domain production
5. ปิด SSH/ESXi Shell เมื่อไม่ใช้, lockdown mode, ตั้ง NTP/syslog, ใช้ secure boot, ปิดบริการที่ไม่ใช้
</details>

**5 โปรเจค**
- ⭐⭐ P1: Zone diagram + policy matrix ของ DC ลูกค้าสมมติ
- ⭐⭐ P2: ตั้ง jump host (Apache Guacamole) + MFA สำหรับเข้า management network
- ⭐⭐ P3: Hardening checklist ESXi/vCenter แล้วตรวจ lab ตาม checklist
- ⭐⭐ P4: สคริปต์ตรวจ host ที่เปิด SSH ค้างไว้ (PowerCLI/Ansible)
- ⭐⭐⭐ P5: Security review ของ DC lab แล้วเขียน findings + remediation plan

---

## Level 36 — DC Monitoring & DCIM

**สิ่งที่ต้องรู้**
- Monitor hardware: iDRAC/iLO SNMP trap, Redfish, OpenManage Enterprise, HPE OneView
- Virtualization: vCenter alarms, vRealize/Aria Operations, Nutanix Prism, Veeam ONE
- Storage: capacity, latency, path, controller
- Environment: temperature, humidity, UPS (SNMP card), PDU, water leak sensor
- DCIM: NetBox, Device42, Sunbird; asset, rack, power, cabling
- เชื่อมกับ Support 24x7 (Part 4): alert → ticket อัตโนมัติ

**แบบทดสอบ**
1. Metric storage 3 ตัวที่ต้องมี alert
2. อุณหภูมิห้อง server ที่แนะนำ (ASHRAE)
3. UPS ส่ง alert ได้ทางไหน
4. DCIM ช่วยงาน SI อย่างไร
5. Alert ที่ดีควรมีข้อมูลอะไร

<details><summary>เฉลย</summary>

1. Capacity (%), latency, path/controller status (รวม hardware fault)
2. ประมาณ 18–27°C ที่ช่องลมเข้า (ASHRAE recommended)
3. SNMP card (trap), email, Modbus, software agent (PowerChute)
4. รู้ตำแหน่ง/สาย/ไฟของทุกอุปกรณ์ วางแผนเพิ่มอุปกรณ์และแก้ปัญหาได้เร็ว
5. อุปกรณ์, ปัญหา, ความรุนแรง, เวลา, ผลกระทบ, ลิงก์ไป runbook
</details>

**5 โปรเจค**
- ⭐⭐ P1: Zabbix + template iDRAC/iLO (SNMP) + vCenter
- ⭐⭐ P2: Grafana dashboard "DC Health" (host, datastore, temp, UPS)
- ⭐⭐ P3: ใส่ข้อมูล rack/device/power ของ lab ลง NetBox
- ⭐⭐ P4: Alert → LINE/Teams/email พร้อมลิงก์ runbook
- ⭐⭐⭐ P5: Monthly DC health report อัตโนมัติ (PDF) จากข้อมูล monitoring

---

## Level 37 — Pre-sales: Assessment, Sizing & Solution Design

**สิ่งที่ต้องรู้**
- Discovery: interview ลูกค้า (pain point, งบ, timeline), เก็บข้อมูลด้วย Live Optics, RVTools, Nutanix Collector
- Solution design: ทางเลือก 2–3 แบบ (good/better/best), architecture diagram, BOM
- Sizing tools ของ vendor: Dell Sizer, HPE Sizer, Nutanix Sizer, vSAN ReadyNode Sizer
- เอกสาร: proposal, Statement of Work (SoW), scope/out-of-scope, assumptions
- TOR ภาครัฐ, spec ล็อก, การแข่งขันราคา

**แบบทดสอบ**
1. ข้อมูลอะไรที่ต้องเก็บก่อน sizing virtualization
2. ทำไมต้องเสนอหลายทางเลือก
3. SoW ต้องมีอะไร
4. "Out-of-scope" สำคัญอย่างไร
5. ทำไมต้องเก็บข้อมูล performance อย่างน้อย 7–30 วัน

<details><summary>เฉลย</summary>

1. จำนวน VM, vCPU/RAM/disk, CPU/RAM utilization, IOPS/throughput, growth, workload สำคัญ, license
2. ให้ลูกค้าเลือกตามงบ/ความเสี่ยง และแสดงว่าเราเข้าใจ trade-off
3. Scope, deliverables, timeline, ความรับผิดชอบสองฝ่าย, acceptance criteria, assumptions
4. ป้องกัน scope creep และข้อพิพาท
5. ให้ครอบคลุม peak รายสัปดาห์/รายเดือน (เช่น ปิดงบ, batch job)
</details>

**5 โปรเจค**
- ⭐⭐ P1: Discovery questionnaire สำหรับโปรเจค DC refresh
- ⭐⭐ P2: ทดลองใช้ Nutanix Sizer หรือ vSAN ReadyNode Sizer กับข้อมูลสมมติ
- ⭐⭐ P3: Proposal 3 ทางเลือก (3-tier SAN / HCI / Cloud) พร้อม diagram และราคาประมาณ
- ⭐⭐ P4: SoW template ฉบับ SI
- ⭐⭐⭐ P5: Present proposal 15 นาทีให้เพื่อน (บทบาทลูกค้า) แล้วตอบคำถามเชิงเทคนิคและเชิงธุรกิจ

---

## Level 38 — Implementation: ติดตั้งหน้างาน

**สิ่งที่ต้องรู้**
- Project plan: kick-off, pre-requisite (IP, DNS, NTP, VLAN, rack space, power), เลื่อนงานเมื่อลูกค้าไม่พร้อม
- Rack & stack: ลำดับติดตั้ง (หนักไว้ล่าง), rail kit, cable management, labeling ทั้ง 2 ปลาย
- Firmware baseline ให้ตรง HCL ก่อนติดตั้ง software
- Configuration ตาม LLD, เก็บ screenshot/config backup ระหว่างทาง
- Burn-in test, อุปกรณ์ DOA (Dead on Arrival), safety (ESD, ยกของหนัก)
- การสื่อสารกับลูกค้าทุกวัน (daily update)

**แบบทดสอบ**
1. Pre-requisite ที่ลูกค้าต้องเตรียมก่อนติดตั้ง HCI
2. ทำไมต้อง update firmware ก่อนลง hypervisor
3. Label สายควรมีข้อมูลอะไร
4. DOA คืออะไร ทำอย่างไร
5. ทำไมต้องส่ง daily update

<details><summary>เฉลย</summary>

1. IP (host, CVM/VMkernel, cluster VIP, iDRAC), VLAN บน switch, DNS forward/reverse, NTP, rack/power, account AD
2. Firmware เก่าอาจไม่ตรง HCL ทำให้ไม่รองรับหรือเกิด bug; update ภายหลังต้องหยุดระบบ
3. ต้นทาง (อุปกรณ์/พอร์ต) และปลายทาง (อุปกรณ์/พอร์ต) ตามมาตรฐานเดียวกันทั้งไซต์
4. อุปกรณ์ใหม่ที่เสียตั้งแต่แกะกล่อง ต้องเปิด case กับ vendor เพื่อเปลี่ยน และแจ้ง PM/ลูกค้าเรื่อง timeline
5. ลูกค้าเห็นความคืบหน้า แจ้งปัญหา/ความเสี่ยงได้เร็ว สร้างความเชื่อมั่น
</details>

**5 โปรเจค**
- ⭐ P1: Pre-requisite checklist (ส่งลูกค้า) สำหรับ DC/HCI project
- ⭐⭐ P2: Implementation plan + Gantt chart สำหรับโปรเจค 4 สัปดาห์
- ⭐⭐ P3: Labeling standard + ตัวอย่างไฟล์พิมพ์ label จาก cable plan
- ⭐⭐ P4: "Day-0 build" ใน lab: ติดตั้งตาม LLD ทั้งชุด แล้วเก็บหลักฐานทุกขั้น
- ⭐⭐⭐ P5: Lessons-learned report จากโปรเจคจำลอง (ปัญหาที่เจอ, วิธีแก้, ป้องกันครั้งหน้า)

---

## Level 39 — Testing, Acceptance & Handover

**สิ่งที่ต้องรู้**
- Test plan / UAT: functional test, HA/failover test, performance test, backup/restore test
- Acceptance criteria ที่วัดได้, ลูกค้าเซ็นรับ
- As-built document: diagram, IP/VLAN, config, account (ส่งแบบปลอดภัย), serial/warranty
- Knowledge transfer / training ให้ทีมลูกค้า
- ส่งต่อทีม Support (Part 4): monitoring, contact, escalation matrix, เลขสัญญา

**แบบทดสอบ**
1. Test case ที่ดีต้องมีอะไร
2. As-built ต่างจาก design document อย่างไร
3. ส่งรหัสผ่านให้ลูกค้าอย่างปลอดภัยอย่างไร
4. ก่อนปิดโปรเจคต้องส่งอะไรให้ทีม Support
5. ทำไม HA test ต้องทำต่อหน้าลูกค้า

<details><summary>เฉลย</summary>

1. ID, ขั้นตอน, ผลที่คาดหวัง, ผลจริง, ผ่าน/ไม่ผ่าน, หลักฐาน, ผู้ทดสอบ/วันที่
2. As-built คือสิ่งที่ติดตั้งจริง (รวมการเปลี่ยนแปลงหน้างาน)
3. Password manager/ไฟล์เข้ารหัส แยกช่องทางส่งรหัสเปิด และให้ลูกค้าเปลี่ยนรหัสทันที
4. As-built, monitoring ที่ตั้งแล้ว, สัญญา/SLA, contact & escalation, serial/warranty, ปัญหาค้าง
5. ยืนยันว่า redundancy ใช้ได้จริง ลูกค้ายอมรับ ลดข้อโต้แย้งภายหลัง
</details>

**5 โปรเจค**
- ⭐⭐ P1: UAT document 30 test case สำหรับ cluster virtualization
- ⭐⭐ P2: As-built template (Word/Markdown) + ตัวอย่างจาก lab
- ⭐⭐ P3: สคริปต์ export config/inventory อัตโนมัติเพื่อแนบ as-built
- ⭐⭐ P4: สไลด์ training ทีม IT ลูกค้า (งานดูแลรายวัน 1 ชั่วโมง)
- ⭐⭐⭐ P5: Handover package ครบชุด (as-built, test result, ข้อมูล support, การเซ็นรับ)

---

## Level 40 — Capstone Data Center

**โจทย์:** โรงพยาบาลเอกชน 200 เตียง ต้องการเปลี่ยนระบบเก่า (server 20 เครื่องแยกกัน) เป็นระบบ virtualization ที่มี HA และ DR โดยมี VM 120 ตัว, HIS database 4 TB, PACS 60 TB และต้องการ RPO 15 นาที / RTO 4 ชั่วโมง

**แบบทดสอบ (Self-review)**
1. ทุก single point of failure (ไฟ, switch, host, storage, path) มีสำรองแล้วหรือยัง
2. Sizing เผื่อ N+1 และ growth 3–5 ปีแล้วหรือยัง
3. Backup ตาม 3-2-1-1-0 และทดสอบ restore แล้วหรือยัง
4. DR ทำ RPO/RTO ได้ตามที่ลูกค้าต้องการจริงหรือไม่ (มีผล drill)
5. Support team รับต่อได้ทันทีหรือไม่ (monitoring, docs)

**5 โปรเจค**
- ⭐⭐⭐ P1: Requirements + BIA + Sizing (VM, HIS, PACS)
- ⭐⭐⭐ P2: HLD/LLD: server, storage (SAN หรือ HCI พร้อมเหตุผล), network, backup และ DR
- ⭐⭐⭐ P3: BOM + TCO 5 ปี + proposal ฉบับผู้บริหาร
- ⭐⭐⭐ P4: Lab ย่อส่วน: cluster 3 node + backup + replication + HA/DR test
- ⭐⭐⭐ P5: Handover package + แผน PM รายไตรมาส (ส่งต่อ Part 4)
