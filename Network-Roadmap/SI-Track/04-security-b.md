# Part 2 — ความปลอดภัยไซเบอร์ (Cybersecurity) ตอน B: ระบบเฝ้าระวังภัยคุกคาม (Level 51–60)

---

## Level 51 — Endpoint Security: EDR / XDR

**สิ่งที่ต้องรู้**
- AV → EPP → EDR (บันทึกพฤติกรรม, ตรวจจับ, ตอบสนอง) → XDR (รวม endpoint, network, email, identity, cloud)
- Vendor: Microsoft Defender for Endpoint, CrowdStrike Falcon, SentinelOne, Trend Micro Vision One, Sophos, Cortex XDR, FortiEDR
- Response: isolate host, kill process, rollback (บางยี่ห้อ), live response
- Deployment: GPO/Intune/SCCM, exclusion อย่างระมัดระวัง, server vs workstation policy
- MDR (Managed Detection & Response) — บริการเฝ้าระวัง 24x7 ที่ SI นำเสนอ

**แบบทดสอบ**
1. EDR ต่างจาก antivirus อย่างไร
2. Host isolation ทำงานอย่างไร
3. ความเสี่ยงของการใส่ exclusion มากเกินไป
4. XDR เพิ่มอะไรจาก EDR
5. MDR เหมาะกับลูกค้าแบบไหน

<details><summary>เฉลย</summary>

1. EDR บันทึกพฤติกรรมต่อเนื่อง ตรวจจับเทคนิคที่ไม่มี signature และตอบสนองได้
2. ตัดเครื่องออกจากเครือข่าย ยกเว้นการเชื่อมต่อกับ console ของ EDR
3. ผู้โจมตีซ่อนมัลแวร์ในโฟลเดอร์ที่ถูก exclude
4. Correlation ข้ามแหล่งข้อมูล (email, network, identity, cloud) ในเหตุการณ์เดียว
5. องค์กรที่ไม่มีทีม SOC 24x7 ของตัวเอง
</details>

**5 โปรเจค**
- ⭐⭐ P1: Microsoft Defender for Endpoint (trial) หรือ Wazuh agent บน Windows/Linux lab
- ⭐⭐ P2: Atomic Red Team (lab) ทดสอบว่า EDR ตรวจจับเทคนิคใดได้บ้าง → map MITRE ATT&CK
- ⭐⭐ P3: Deployment plan EDR 1,000 เครื่อง (pilot, rollout, exclusion policy)
- ⭐⭐ P4: เปรียบเทียบ EDR 3 ยี่ห้อจากผล MITRE ATT&CK Evaluations
- ⭐⭐⭐ P5: Playbook "EDR alert: ransomware behavior" → isolate → investigate → recover

---

## Level 52 — Email & Identity Security

**สิ่งที่ต้องรู้**
- Email: SPF, DKIM, DMARC (p=none → quarantine → reject), Secure Email Gateway (Proofpoint, Mimecast, FortiMail, Defender for O365), sandbox attachment, URL rewrite
- BEC (Business Email Compromise), phishing simulation & awareness
- Identity: Active Directory hardening (tiering model, LAPS, ปิด NTLMv1, Kerberoasting), Entra ID (MFA, conditional access, PIM)
- Identity Threat Detection & Response (ITDR): Defender for Identity
- Privileged accounts: ไม่ใช้ Domain Admin ทำงานประจำ

**แบบทดสอบ**
1. DMARC p=reject หมายความว่าอะไร
2. BEC คืออะไร ป้องกันอย่างไร
3. LAPS ช่วยอะไร
4. AD tiering model คืออะไร
5. Kerberoasting โจมตีอะไร

<details><summary>เฉลย</summary>

1. ให้ผู้รับปฏิเสธอีเมลที่อ้างโดเมนนี้แต่ไม่ผ่าน SPF/DKIM alignment
2. หลอกเป็นผู้บริหาร/คู่ค้าให้โอนเงิน ป้องกันด้วย DMARC, ยืนยันทางโทรศัพท์, awareness, MFA
3. สุ่มรหัส local admin ของแต่ละเครื่องไม่ให้ซ้ำกัน ลดการลามด้วย pass-the-hash
4. แยกบัญชี/เครื่องตามระดับ (Tier 0 = DC/AD, Tier 1 = server, Tier 2 = workstation) ไม่ให้ใช้ข้ามระดับ
5. ขอ service ticket ของ service account แล้วนำไป crack รหัสแบบ offline
</details>

**5 โปรเจค**
- ⭐ P1: ตรวจ SPF/DKIM/DMARC ของโดเมนตัวอย่าง 20 โดเมน (ต่อยอด Roadmap หลัก L16)
- ⭐⭐ P2: PingCastle/Purple Knight scan AD lab แล้วแก้ findings
- ⭐⭐ P3: ตั้ง LAPS + ปิด NTLMv1/SMBv1 ใน AD lab
- ⭐⭐ P4: Phishing simulation ภายในทีม (GoPhish, ได้รับอนุญาต) + awareness deck
- ⭐⭐⭐ P5: Identity security roadmap ให้ลูกค้า (AD hardening + Entra + PAM)

---

## Level 53 — Log Management & SIEM

> พื้นฐานจาก Roadmap หลัก [L68](../07-security.md)

**สิ่งที่ต้องรู้**
- Log sources ลำดับความสำคัญ: firewall, VPN, AD/Entra, EDR, DNS, proxy, email, cloud, server
- SIEM: Splunk, IBM QRadar, Microsoft Sentinel, FortiSIEM, Elastic, Wazuh, Google SecOps
- Pipeline: collect (syslog/agent/API) → parse/normalize → enrich → correlate → alert → case
- Sizing: EPS (events per second), GB/day, retention (hot/warm/cold), ค่า license
- Use case development, ลด false positive, log ตาม พ.ร.บ.คอมฯ

**แบบทดสอบ**
1. EPS ใช้ทำอะไร
2. Log source 5 อันดับแรกที่ควรส่งเข้า SIEM
3. Normalize log มีประโยชน์อย่างไร
4. ทำไมต้อง tune use case
5. Hot / cold storage ต่างกันอย่างไร

<details><summary>เฉลย</summary>

1. ใช้ sizing SIEM และคิด license
2. Firewall/VPN, AD/identity, EDR, DNS/proxy, email (และ cloud)
3. ทำให้ field ต่างยี่ห้อเป็นชื่อเดียวกัน ค้นหาและ correlate ข้ามแหล่งได้
4. ลด false positive / alert fatigue ให้ analyst โฟกัส alert จริง
5. Hot = ค้นหาเร็ว ราคาแพง ใช้ช่วงล่าสุด; Cold = ราคาถูก ค้นช้า เก็บตามกฎหมาย
</details>

**5 โปรเจค**
- ⭐⭐ P1: Wazuh/Elastic รับ log จาก FortiGate + Windows + Linux ใน lab
- ⭐⭐ P2: Microsoft Sentinel (trial) + data connector + workbook
- ⭐⭐ P3: SIEM sizing calculator (จำนวนอุปกรณ์ × EPS → GB/day, storage, retention)
- ⭐⭐⭐ P4: เขียน use case 10 ข้อ (rule + ทดสอบ + playbook) map MITRE ATT&CK
- ⭐⭐⭐ P5: SIEM onboarding plan ลูกค้า (log source, parser, use case, รายงานรายเดือน)

---

## Level 54 — SOC Operations & Threat Hunting

**สิ่งที่ต้องรู้**
- โครงสร้าง SOC: Tier 1 (triage), Tier 2 (investigation), Tier 3 (hunting/IR), SOC manager
- Alert triage: true/false positive, severity, enrichment (VirusTotal, AbuseIPDB, threat intel)
- SOAR (Cortex XSOAR, Splunk SOAR, Sentinel Logic Apps, Shuffle) ทำ playbook อัตโนมัติ
- Threat hunting: hypothesis-based, MITRE ATT&CK, ค้นหา IoC/IoA
- KPI: MTTD, MTTR, จำนวน alert/analyst, false positive rate
- Shift 24x7, handover, การบันทึก case

**แบบทดสอบ**
1. Tier 1 analyst ทำอะไร
2. IoC กับ IoA ต่างกันอย่างไร
3. SOAR ช่วยอะไร
4. ตัวอย่าง hypothesis ของ threat hunting
5. MTTD คืออะไร

<details><summary>เฉลย</summary>

1. ดู alert, คัดกรอง, enrich, ปิด false positive, escalate เคสจริง
2. IoC = หลักฐานที่เกิดแล้ว (hash, IP, domain); IoA = พฤติกรรมการโจมตี (เช่น dump LSASS)
3. ทำงานซ้ำอัตโนมัติ (enrich, block IP, isolate host, เปิด ticket) ลดเวลาตอบสนอง
4. "มีเครื่องใดติดต่อโดเมนที่เพิ่งจดทะเบียนในช่วงเวลาสม่ำเสมอ (beaconing) หรือไม่"
5. Mean Time To Detect: เวลาเฉลี่ยตั้งแต่เกิดเหตุจนตรวจพบ
</details>

**5 โปรเจค**
- ⭐⭐ P1: Triage playbook 5 alert ยอดฮิต (brute force, malware, phishing, impossible travel, port scan)
- ⭐⭐ P2: Shuffle/n8n SOAR: alert → enrich IP (AbuseIPDB) → เปิด ticket
- ⭐⭐ P3: Blue team lab (CyberDefenders/LetsDefend) 5 เคส + writeup
- ⭐⭐⭐ P4: Threat hunting 3 hypothesis บน log lab (Sigma rules)
- ⭐⭐⭐ P5: SOC service catalog + SLA (เวลาตอบตาม severity) สำหรับขายบริการ MDR/MSSP

---

## Level 55 — Network Detection & Response (NDR) / IDS / IPS

> พื้นฐานจาก Roadmap หลัก [L64](../07-security.md), [L87](../09-automation-operations.md)

**สิ่งที่ต้องรู้**
- NDR: วิเคราะห์ traffic (metadata + ML) ตรวจจับ lateral movement, C2, data exfiltration — Darktrace, ExtraHop, Vectra, Corelight (Zeek)
- Open-source: Suricata, Zeek, Security Onion, Arkime (full packet capture)
- จุดวาง sensor: core, DC east-west, internet edge, ผ่าน TAP/SPAN/packet broker
- Encrypted traffic analysis: JA3/JA4, cert, flow pattern
- OT/ICS monitoring: Nozomi, Claroty, Dragos (สำหรับลูกค้าโรงงาน)

**แบบทดสอบ**
1. NDR เห็นอะไรที่ EDR ไม่เห็น
2. Packet broker ใช้ทำอะไร
3. ตรวจ C2 beaconing จาก flow อย่างไร
4. JA3/JA4 คืออะไร
5. ทำไมโรงงานต้องใช้เครื่องมือ OT โดยเฉพาะ

<details><summary>เฉลย</summary>

1. อุปกรณ์ที่ลง agent ไม่ได้ (IoT, OT, printer, network device), traffic ระหว่างเครื่อง
2. รวม/กรอง/กระจาย traffic จาก TAP/SPAN ไปยังเครื่องมือหลายตัว
3. การเชื่อมต่อไปปลายทางเดียวกันเป็นช่วงเวลาสม่ำเสมอ ขนาดใกล้เคียงกัน
4. Fingerprint ของ TLS client/server จาก handshake ใช้ระบุมัลแวร์/แอปได้แม้เข้ารหัส
5. Protocol เฉพาะ (Modbus, S7, DNP3) และอุปกรณ์ที่ห้ามรบกวน ต้องใช้แบบ passive
</details>

**5 โปรเจค**
- ⭐⭐ P1: Security Onion ใน lab + replay pcap จาก malware-traffic-analysis.net
- ⭐⭐ P2: Zeek + RITA หา beaconing ใน pcap ตัวอย่าง
- ⭐⭐ P3: Sensor placement design สำหรับ DC + สำนักงานใหญ่ลูกค้า
- ⭐⭐⭐ P4: Arkime full packet capture + ค้นย้อนหลังเหตุการณ์
- ⭐⭐⭐ P5: รายงานเปรียบเทียบ NDR เชิงพาณิชย์ vs open-source (ความสามารถ, ต้นทุน, ทีมที่ต้องใช้)

---

## Level 56 — Vulnerability Management & Threat Intelligence

**สิ่งที่ต้องรู้**
- Scanner: Tenable Nessus/Tenable.io, Qualys, Rapid7, OpenVAS; authenticated vs unauthenticated scan
- Prioritization: CVSS + EPSS + CISA KEV + ความสำคัญของ asset (risk-based)
- Patch management: WSUS/Intune/SCCM, Linux repo, firmware ของ network/server/storage
- Attack Surface Management (ASM): สิ่งที่เปิดสู่อินเทอร์เน็ต (Shodan, Censys)
- Threat intel: ThaiCERT, TB-CERT, CISA advisories, vendor PSIRT (Fortinet, Palo Alto)

**แบบทดสอบ**
1. ทำไม authenticated scan ได้ผลดีกว่า
2. EPSS คืออะไร
3. CISA KEV ใช้ทำอะไร
4. Firewall ของลูกค้ามี CVE critical ที่ถูกใช้โจมตีจริง ควรทำอะไร
5. ASM ต่างจาก vulnerability scan ภายในอย่างไร

<details><summary>เฉลย</summary>

1. ตรวจ patch/config ภายในเครื่องได้ ไม่ใช่แค่ service ที่เปิด
2. Exploit Prediction Scoring System: โอกาสที่ช่องโหว่จะถูกใช้โจมตีใน 30 วัน
3. รายการช่องโหว่ที่ถูกโจมตีจริงแล้ว ใช้จัดลำดับ patch ด่วน
4. แจ้งลูกค้าทันที, ใช้ workaround ระหว่างรอ, นัด emergency change เพื่อ patch, ตรวจ IoC ว่าโดนไปแล้วหรือยัง
5. ASM มองจากมุมผู้โจมตีภายนอก (asset ที่ไม่รู้ว่ามี, shadow IT)
</details>

**5 โปรเจค**
- ⭐⭐ P1: Nessus Essentials (ฟรี) scan lab + จัดลำดับด้วย CVSS/EPSS/KEV
- ⭐⭐ P2: สคริปต์ดึง PSIRT advisory ของ vendor ที่ลูกค้าใช้ → แจ้ง LINE/Teams
- ⭐⭐ P3: Patch policy (SLA ตาม severity, maintenance window, exception)
- ⭐⭐ P4: Monthly vulnerability report template ให้ลูกค้า
- ⭐⭐⭐ P5: External ASM ของโดเมนตัวเอง/lab (subfinder, httpx, nmap) + รายงาน

---

## Level 57 — Incident Response

> พื้นฐานจาก Roadmap หลัก [L70](../07-security.md)

**สิ่งที่ต้องรู้**
- NIST SP 800-61: Preparation, Detection & Analysis, Containment/Eradication/Recovery, Post-incident
- Ransomware IR: isolate (network/EDR), รักษาหลักฐาน, หาจุดเข้า (patient zero), reset credential (krbtgt 2 ครั้ง), restore จาก backup ที่สะอาด
- Forensics เบื้องต้น: memory, disk image, log timeline, chain of custody
- การสื่อสาร: ผู้บริหาร, legal, PDPA (แจ้ง สคส. ภายใน 72 ชั่วโมงเมื่อข้อมูลส่วนบุคคลรั่วและมีความเสี่ยง), สกมช. สำหรับ CII
- Retainer IR service, tabletop exercise

**แบบทดสอบ**
1. เมื่อพบ ransomware ขั้นแรกควรทำอะไร
2. ทำไมต้อง reset krbtgt 2 ครั้ง
3. ตาม PDPA ต้องแจ้งเหตุภายในกี่ชั่วโมง
4. ทำไมไม่ควร restore ทันทีก่อนรู้จุดเข้า
5. Chain of custody คืออะไร

<details><summary>เฉลย</summary>

1. Contain: แยกเครื่อง/segment ที่ติด (ไม่ปิดเครื่องถ้าไม่จำเป็น), ปกป้อง backup, แจ้งทีม IR
2. ทำให้ Kerberos ticket ที่ผู้โจมตีปลอม (golden ticket) ใช้ไม่ได้ เพราะระบบจำรหัสก่อนหน้าไว้ 1 ชุด
3. 72 ชั่วโมงนับจากทราบเหตุ (กรณีมีความเสี่ยงต่อสิทธิของเจ้าของข้อมูล)
4. ผู้โจมตียังอยู่/ช่องโหว่ยังเปิด ระบบจะโดนซ้ำ
5. บันทึกการเก็บ/ส่งต่อหลักฐานทุกขั้น เพื่อให้ใช้ทางกฎหมายได้
</details>

**5 โปรเจค**
- ⭐⭐ P1: IR plan template + contact list + severity matrix
- ⭐⭐ P2: Ransomware playbook (network, endpoint, AD, backup, communication)
- ⭐⭐ P3: Tabletop exercise กับเพื่อน 3–5 คน + after-action report
- ⭐⭐⭐ P4: Forensics lab: เก็บ memory (WinPmem) + วิเคราะห์ด้วย Volatility 3
- ⭐⭐⭐ P5: Timeline เหตุการณ์จาก log หลายแหล่ง (firewall, AD, EDR) ของเคสจำลอง

---

## Level 58 — Hardening, Compliance & Security Audit

**สิ่งที่ต้องรู้**
- CIS Benchmarks (Windows, Linux, ESXi, FortiGate, Palo Alto, Cisco), DISA STIG
- Configuration audit อัตโนมัติ: CIS-CAT, Nipper, Lynis, OpenSCAP, Ansible compliance
- ISO 27001:2022 Annex A, PCI DSS v4.0 (ลูกค้าที่รับบัตร), แนวปฏิบัติ ธปท.
- Evidence collection สำหรับ auditor, gap assessment, remediation tracking
- Penetration test ประจำปี (ทำโดยทีมที่ได้รับอนุญาต)

**แบบทดสอบ**
1. CIS Benchmark Level 1 vs Level 2
2. ทำไมต้องทำ config audit อัตโนมัติ
3. Gap assessment คืออะไร
4. Evidence สำหรับ "มีการ review firewall rule" คืออะไร
5. PCI DSS ใช้กับองค์กรแบบไหน

<details><summary>เฉลย</summary>

1. Level 1 = พื้นฐาน กระทบการใช้งานน้อย; Level 2 = เข้มงวดกว่า สำหรับระบบความเสี่ยงสูง
2. Config drift เกิดตลอด ตรวจด้วยมือไม่ทันและไม่สม่ำเสมอ
3. เปรียบเทียบสถานะปัจจุบันกับมาตรฐาน หาช่องว่างและจัดลำดับการแก้
4. รายงาน review ที่ลงวันที่/ผู้อนุมัติ, ticket การลบ rule, บันทึกการประชุม
5. องค์กรที่จัดเก็บ ประมวลผล หรือส่งข้อมูลบัตรชำระเงิน
</details>

**5 โปรเจค**
- ⭐⭐ P1: Lynis/OpenSCAP scan Linux lab → แก้ให้คะแนนเพิ่ม
- ⭐⭐ P2: Ansible role hardening ตาม CIS (Linux/Windows)
- ⭐⭐ P3: FortiGate/Palo Alto hardening checklist + สคริปต์ตรวจจาก config backup
- ⭐⭐ P4: ISO 27001 gap assessment ส่วน network/operations ของลูกค้าสมมติ
- ⭐⭐⭐ P5: Compliance dashboard (ผ่าน/ไม่ผ่านแต่ละ control ตามอุปกรณ์) อัปเดตอัตโนมัติ

---

## Level 59 — Security for Data Center, HCI & Cloud

**สิ่งที่ต้องรู้**
- Ransomware บน hypervisor: โจมตี ESXi/vCenter โดยตรง → ปิด SSH, lockdown, MFA vCenter, แยก management network, patch
- HCI security: Nutanix Flow, vSAN encryption, data-at-rest encryption + KMS
- Cloud: shared responsibility, IAM least privilege, CSPM (Defender for Cloud, Prisma Cloud, Wiz), CNAPP
- Cloud network security: security group/NSG, cloud firewall (Azure Firewall, AWS Network Firewall, NGFW VM), WAF
- Backup security: immutable, แยก credential

**แบบทดสอบ**
1. ทำไมผู้โจมตีชอบโจมตี ESXi โดยตรง
2. CSPM ทำอะไร
3. KMS ใช้ทำอะไรกับ encryption
4. Shared responsibility ใน IaaS ลูกค้ารับผิดชอบอะไร
5. ความผิดพลาดใน cloud ที่พบบ่อยที่สุด

<details><summary>เฉลย</summary>

1. เข้ารหัส VM ทั้ง host ได้ในครั้งเดียว และ ESXi มักไม่มี EDR
2. ตรวจ misconfiguration ของ cloud กับ best practice/compliance อย่างต่อเนื่อง
3. จัดการ key แยกจาก storage (สร้าง, หมุน, เก็บ)
4. OS, app, data, IAM, network config (security group), encryption
5. Storage bucket เปิด public, security group เปิด 0.0.0.0/0, IAM สิทธิ์เกิน, ไม่มี MFA
</details>

**5 โปรเจค**
- ⭐⭐ P1: Hardening vSphere lab ตาม Security Configuration Guide
- ⭐⭐ P2: Prowler/ScoutSuite scan บัญชี AWS lab + แก้ findings
- ⭐⭐ P3: Azure Firewall/AWS Network Firewall hub-and-spoke (lab แล้วลบทิ้ง)
- ⭐⭐ P4: Ransomware resilience checklist สำหรับ virtualization + backup
- ⭐⭐⭐ P5: Security architecture ของ hybrid (DC + HCI + cloud) พร้อม control ทุกชั้น

---

## Level 60 — Capstone Cybersecurity

**โจทย์:** บริษัทการเงินขนาดกลาง 800 คน มีสำนักงานใหญ่ + 10 สาขา, DC 1 แห่ง และใช้ Microsoft 365 ต้องการ NGFW ใหม่, Zero Trust Segmentation สำหรับ server 200 เครื่อง และบริการเฝ้าระวัง 24x7 ตามแนวปฏิบัติ ธปท.

**แบบทดสอบ (Self-review)**
1. Firewall policy ใหม่ตรวจ App-ID/User-ID/SSL และไม่มี any-any แล้วหรือยัง
2. Lateral movement ไปยัง AD/backup/DB ถูก ringfence แล้วหรือยัง
3. Log ครบทุกแหล่งสำคัญ เก็บ ≥ 90 วัน และมี use case ที่ทดสอบแล้วหรือยัง
4. มี IR playbook และทดสอบ tabletop แล้วหรือยัง
5. ลูกค้ารับรายงานรายเดือนที่ผู้บริหารอ่านเข้าใจหรือไม่

**5 โปรเจค**
- ⭐⭐⭐ P1: Assessment + Zero Trust roadmap + proposal
- ⭐⭐⭐ P2: NGFW design + migration plan + HA + cutover test matrix (lab)
- ⭐⭐⭐ P3: ZTS design (label taxonomy, policy, phase) + demo lab
- ⭐⭐⭐ P4: SOC/SIEM: log source, use case 15 ข้อ, SOAR playbook, SLA
- ⭐⭐⭐ P5: Executive security report + IR tabletop กับ "ลูกค้า"
