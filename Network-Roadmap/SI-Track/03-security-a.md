# Part 2 — ความปลอดภัยไซเบอร์ (Cybersecurity) ตอน A: Next-Gen Firewall (Level 41–50)

> ตามบริการ: **Next-Gen Firewall, Zero Trust Segmentation และระบบเฝ้าระวังภัยคุกคาม**
>
> ⚠️ Lab ด้านการโจมตีให้ทำในเครือข่ายของตัวเองหรือที่ได้รับอนุญาตเป็นลายลักษณ์อักษรเท่านั้น

---

## Level 41 — Security Fundamentals สำหรับงาน SI

> พื้นฐานจาก Roadmap หลัก [L61](../07-security.md)

**สิ่งที่ต้องรู้**
- CIA, defense in depth, least privilege, assume breach
- Framework ที่ลูกค้าอ้างถึงใน TOR: ISO/IEC 27001, NIST CSF 2.0, CIS Controls v8
- กฎหมายไทย: พ.ร.บ.คอมพิวเตอร์ (เก็บ log ≥ 90 วัน), PDPA, พ.ร.บ.การรักษาความมั่นคงปลอดภัยไซเบอร์ 2562 (CII), ประกาศ ธปท./คปภ./ก.ล.ต. สำหรับลูกค้าการเงิน
- ภัยคุกคามที่ลูกค้าไทยเจอบ่อย: ransomware, phishing/BEC, ช่องโหว่ VPN/firewall ที่ไม่ patch, credential stuffing
- บทบาท SI: ออกแบบ, ติดตั้ง, ดูแล (MSSP), ไม่ใช่แค่ขายกล่อง

**แบบทดสอบ**
1. องค์กรหน่วยงาน CII ต้องปฏิบัติตามกฎหมายใด
2. ระยะเวลาเก็บ log ตาม พ.ร.บ.คอมฯ
3. ทำไม firewall/VPN ที่ไม่ patch เป็นช่องทางหลักของ ransomware
4. NIST CSF 2.0 มี function อะไรบ้าง
5. MSSP คืออะไร

<details><summary>เฉลย</summary>

1. พ.ร.บ.การรักษาความมั่นคงปลอดภัยไซเบอร์ พ.ศ. 2562 (และประกาศของ สกมช./หน่วยงานกำกับ)
2. ไม่น้อยกว่า 90 วัน
3. เปิดสู่อินเทอร์เน็ตโดยตรง ช่องโหว่ถูกเผยแพร่และถูกสแกนหาอัตโนมัติ
4. Govern, Identify, Protect, Detect, Respond, Recover
5. Managed Security Service Provider: ผู้ให้บริการดูแล/เฝ้าระวังความปลอดภัยให้ลูกค้า
</details>

**5 โปรเจค**
- ⭐ P1: สรุปกฎหมาย/มาตรฐานที่เกี่ยวข้องกับลูกค้า 4 กลุ่ม (รัฐ, ธนาคาร, โรงพยาบาล, โรงงาน)
- ⭐⭐ P2: Security assessment questionnaire สำหรับลูกค้าใหม่ (30 ข้อตาม CIS Controls)
- ⭐⭐ P3: Map บริการของ SI (NGFW, ZTS, SOC) กับ NIST CSF function
- ⭐⭐ P4: สคริปต์ติดตาม CVE ของ FortiOS/PAN-OS/Ivanti/Cisco ASA (CISA KEV + NVD API) แจ้งเตือนทุกวัน
- ⭐⭐ P5: Case study ransomware ในไทยหรือ ASEAN 1 เหตุการณ์ (ช่องทางเข้า, ผลกระทบ, บทเรียน)

---

## Level 42 — Next-Gen Firewall Concepts

> พื้นฐานจาก Roadmap หลัก [L62](../07-security.md)

**สิ่งที่ต้องรู้**
- Stateful firewall → NGFW: Application identification (App-ID), User-ID (AD/Entra integration), Content inspection
- Security profiles: IPS, Antivirus, Anti-spyware/C2, URL filtering, DNS security, File blocking, Sandbox (WildFire/FortiSandbox)
- SSL/TLS inspection (outbound forward proxy, inbound inspection)
- Zone-based policy, NAT, VPN, SD-WAN ในกล่องเดียว
- Vendor ในไทย: Fortinet, Palo Alto Networks, Check Point, Cisco Secure Firewall (FTD), Sophos, Huawei
- Sizing: throughput ที่ต้องดูคือ **Threat Protection / NGFW throughput + SSL inspection** ไม่ใช่ firewall throughput

**แบบทดสอบ**
1. App-ID ต่างจากการเปิด port อย่างไร
2. ทำไม sizing ต้องดู threat protection throughput
3. User-ID ทำงานอย่างไร
4. Security profile ที่ควรเปิดใน policy ขาออกอินเทอร์เน็ต
5. ทำไมการ allow port 443 อย่างเดียวไม่พอ

<details><summary>เฉลย</summary>

1. ระบุแอปจากเนื้อหา traffic ไม่ว่าจะใช้ port อะไร (เช่น block BitTorrent ที่วิ่ง 443)
2. เมื่อเปิด IPS/AV/SSL inspection throughput จะลดลงมากจากค่า firewall throughput
3. Map IP → user จาก AD event log, agent, captive portal, RADIUS/802.1X
4. IPS, AV, Anti-spyware/C2, URL filtering, DNS security, file blocking (+ sandbox)
5. มัลแวร์, C2 และแอปที่ไม่อนุญาตส่วนใหญ่ก็ใช้ 443 จึงต้องระบุแอปและตรวจเนื้อหา
</details>

**5 โปรเจค**
- ⭐ P1: ตารางเปรียบเทียบ NGFW 4 ยี่ห้อ (ฟีเจอร์, license bundle, รุ่นเริ่มต้น)
- ⭐⭐ P2: Sizing NGFW สำหรับบริษัท 500 users (bandwidth, SSL %, sessions, เผื่อโต)
- ⭐⭐ P3: Policy design มาตรฐาน (outbound, inbound DMZ, inter-zone) + security profile
- ⭐⭐ P4: เขียน "Firewall Policy Standard" ขององค์กร (naming, logging, review, expiry)
- ⭐⭐⭐ P5: ทดสอบประสิทธิภาพ NGFW VM (trial) ด้วย iperf/TRex เปิด/ปิด IPS และ SSL inspection

---

## Level 43 — Fortinet FortiGate Hands-on

**สิ่งที่ต้องรู้**
- FortiOS: interface/zone, firewall policy, address/service object, NAT (central NAT vs policy NAT), VIP
- Security profile: AV, Web filter, Application control, IPS, DNS filter, SSL inspection profile
- VPN: IPsec (wizard/custom), SSL VPN (ฟอร์ติเนตกำลังเลิก SSL VPN tunnel mode ในรุ่นใหม่ ให้ย้ายไป IPsec/ZTNA), FortiClient EMS
- SD-WAN: member, zone, performance SLA, rules
- HA (FGCP): active-passive/active-active, heartbeat, session pickup, monitor interface
- VDOM, Security Fabric, FortiAnalyzer (log), FortiManager (จัดการหลายเครื่อง)
- CLI ที่ต้องใช้: `diagnose debug flow`, `diagnose sniffer packet`, `get system status`, `diagnose sys session list`

**แบบทดสอบ**
1. คำสั่งดูว่า packet ถูก policy ไหน allow/deny
2. VIP ใน FortiGate ใช้ทำอะไร
3. FGCP heartbeat ควรต่ออย่างไร
4. VDOM คืออะไร
5. FortiAnalyzer กับ FortiManager ต่างกันอย่างไร

<details><summary>เฉลย</summary>

1. `diagnose debug flow` (filter + trace) หรือ Policy lookup ใน GUI
2. Destination NAT (publish server ภายในออกอินเทอร์เน็ต)
3. อย่างน้อย 2 ลิงก์ ต่อตรงหรือผ่าน switch แยก ไม่ปนกับ data
4. Virtual Domain: แบ่ง FortiGate เป็นหลาย firewall เสมือน (multi-tenant)
5. FAZ = เก็บ/วิเคราะห์ log, report; FMG = จัดการ config/policy/firmware ศูนย์กลาง
</details>

**5 โปรเจค**
- ⭐⭐ P1: FortiGate VM (eval) ใน EVE-NG/GNS3: 3 zone + outbound policy + security profile
- ⭐⭐ P2: Publish web server ด้วย VIP + IPS inbound
- ⭐⭐ P3: SD-WAN 2 ISP + performance SLA + rule ตามแอป
- ⭐⭐⭐ P4: HA FGCP 2 เครื่อง + ทดสอบ failover ขณะมี session
- ⭐⭐⭐ P5: Troubleshooting lab 10 โจทย์ (policy, NAT, route, VPN) แก้ด้วย `debug flow` และ `sniffer`

---

## Level 44 — Palo Alto Networks Hands-on

**สิ่งที่ต้องรู้**
- PAN-OS: zone, security policy (App-ID + User-ID + Content-ID), NAT policy (pre-NAT IP, post-NAT zone)
- Single-Pass Parallel Processing, Security profile group
- App-ID: application dependency, `application-default` service
- Decryption policy, GlobalProtect (VPN/ZTNA), WildFire
- HA active/passive (HA1 control, HA2 data/session sync), Panorama (device group, template stack)
- CLI: `show session all filter`, `test security-policy-match`, `debug dataplane packet-diag`, `show counter global filter delta yes`

**แบบทดสอบ**
1. NAT policy ใน Palo Alto ใช้ IP ฝั่งไหนในการ match security policy
2. `application-default` หมายความว่าอะไร
3. HA1 กับ HA2 ต่างกันอย่างไร
4. Panorama device group กับ template ต่างกันอย่างไร
5. คำสั่งทดสอบว่า traffic จะเข้า policy ไหน

<details><summary>เฉลย</summary>

1. Security policy ใช้ pre-NAT IP แต่ใช้ post-NAT zone (สำหรับ destination NAT)
2. อนุญาตแอปเฉพาะบน port มาตรฐานของแอปนั้น
3. HA1 = control link (hello, heartbeat, config sync); HA2 = data link (session sync)
4. Device group = policy/object; Template = network/device settings
5. `test security-policy-match from <zone> to <zone> source <ip> destination <ip> protocol 6 destination-port 443`
</details>

**5 โปรเจค**
- ⭐⭐ P1: PA-VM (eval) หรือ Palo Alto lab ฟรี (Beacon/Hands-on labs): zone + App-ID policy
- ⭐⭐ P2: Inbound DNAT + decryption inbound สำหรับ web server
- ⭐⭐ P3: User-ID กับ AD lab แล้วทำ policy ตามกลุ่มผู้ใช้
- ⭐⭐⭐ P4: Migration จาก port-based → App-ID-based policy (ใช้ Policy Optimizer)
- ⭐⭐⭐ P5: เปรียบเทียบการตั้งงานเดียวกันบน FortiGate vs Palo Alto (คู่มือ side-by-side 15 งาน)

---

## Level 45 — Firewall HA, Upgrade & Migration

**สิ่งที่ต้องรู้**
- HA design: A/P vs A/A, session sync, link/path monitoring, preempt, split-brain
- Firmware upgrade: upgrade path ตามที่ vendor กำหนด, อ่าน release notes/known issues, backup config, upgrade ทีละเครื่องใน HA
- Firewall migration (เช่น Cisco ASA/Check Point → FortiGate/Palo Alto): FortiConverter, Palo Alto Expedition (end-of-life ปี 2025 ตรวจเครื่องมือที่ vendor แนะนำปัจจุบัน), ตรวจ rule ด้วยมือ
- Rule cleanup: unused rules (hit count 0), shadowed, any-any, object ซ้ำ
- Cutover plan: maintenance window, rollback (สลับสายกลับ), test matrix

**แบบทดสอบ**
1. ทำไมต้องดู upgrade path
2. ลำดับการ upgrade firewall HA
3. Rule ที่ hit count = 0 นาน 90 วันควรทำอย่างไร
4. Rollback plan ของการเปลี่ยน firewall คืออะไร
5. ข้อมูลอะไรต้องเก็บก่อน cutover

<details><summary>เฉลย</summary>

1. บาง version ข้ามตรงไม่ได้ ต้องผ่าน version กลาง ไม่เช่นนั้น config อาจเสียหาย
2. Backup → upgrade passive → ตรวจ → failover → upgrade อีกเครื่อง → ตรวจ sync (หรือตามขั้นตอน vendor)
3. ยืนยันกับเจ้าของ → disable ก่อน → ติดตามผล → ลบ
4. ต่อสาย/เปิด firewall เดิมกลับมา (ไม่ทิ้งของเดิมจนกว่าจะผ่าน acceptance)
5. Config/route/NAT/session table/ARP/IP ของ VIP เดิม, รายการแอปสำคัญ, test case
</details>

**5 โปรเจค**
- ⭐⭐ P1: Upgrade plan FortiGate HA (pre-check, step, rollback) แล้วทำจริงใน lab
- ⭐⭐ P2: สคริปต์วิเคราะห์ config export หา any-any, disabled, ไม่มี log, object ซ้ำ
- ⭐⭐⭐ P3: Migration lab: แปลง rule iptables/ASA ชุดเล็ก → FortiGate ด้วยมือ/สคริปต์
- ⭐⭐ P4: Cutover test matrix (src, dst, app, ผลที่คาดหวัง) + สคริปต์ทดสอบอัตโนมัติ
- ⭐⭐⭐ P5: Firewall rule review report ให้ลูกค้า (findings, risk, recommendation)

---

## Level 46 — SSL Inspection & Secure Web Gateway

**สิ่งที่ต้องรู้**
- Outbound inspection: firewall ออก cert แทนเว็บปลายทางด้วย CA ภายใน → ต้อง deploy CA ไปทุกเครื่อง (GPO/MDM)
- Exemption: ธนาคาร, สุขภาพ, ไม่รองรับ (cert pinning), ข้อพิจารณาตาม PDPA
- TLS 1.3, ECH (Encrypted Client Hello), QUIC → ต้อง block QUIC เพื่อบังคับ fallback เป็น TCP
- SWG: URL category, safe search, DLP, CASB (shadow IT)
- Cloud SWG/SSE: Zscaler, Netskope, Prisma Access, FortiSASE

**แบบทดสอบ**
1. ทำไมต้อง deploy CA cert ไปเครื่องผู้ใช้
2. ทำไมต้อง block QUIC (UDP 443) เมื่อทำ SSL inspection
3. ยกตัวอย่างหมวดที่ควร exempt
4. Cert pinning มีผลอย่างไร
5. SSE ต่างจาก SWG บน firewall อย่างไร

<details><summary>เฉลย</summary>

1. ให้ browser เชื่อ cert ที่ firewall ออกแทน ไม่ขึ้นคำเตือน
2. Firewall หลายรุ่นตรวจ QUIC ไม่ได้ การ block ทำให้ browser กลับมาใช้ TCP/TLS ซึ่งตรวจได้
3. Finance/banking, health, government, เว็บของ OS update/แอปที่ pin cert
4. แอปปฏิเสธ cert ที่ไม่ตรงกับที่ฝังไว้ ทำให้ใช้งานไม่ได้ ต้อง exempt
5. SSE ตรวจจาก cloud ใช้ได้ทั้งผู้ใช้ในและนอกสำนักงาน ไม่ต้อง backhaul
</details>

**5 โปรเจค**
- ⭐⭐ P1: เปิด SSL inspection บน FortiGate/PA lab + deploy CA ผ่าน GPO
- ⭐⭐ P2: Exemption list + นโยบายด้าน privacy (ร่างเอกสารให้ HR/Legal ลูกค้า)
- ⭐⭐ P3: ทดสอบ block QUIC แล้วตรวจว่า App-ID/URL filter ทำงานถูก
- ⭐⭐ P4: วัดผลกระทบ throughput/latency ก่อน/หลังเปิด SSL inspection
- ⭐⭐⭐ P5: เปรียบเทียบ SSE 3 เจ้า + PoC plan สำหรับลูกค้าที่มีพนักงาน remote 50%

---

## Level 47 — VPN, ZTNA & Secure Remote Access

> พื้นฐานจาก Roadmap หลัก [L58, L59](../06-services-wireless-wan.md)

**สิ่งที่ต้องรู้**
- Site-to-site IPsec ข้ามยี่ห้อ (FortiGate ↔ Palo Alto ↔ Cisco ↔ cloud): phase 1/2 ต้องตรงกัน
- Remote access: IPsec/SSL VPN (FortiClient, GlobalProtect, Cisco Secure Client)
- MFA (FortiToken, Duo, Entra ID, RADIUS + TOTP), certificate-based, posture check
- ZTNA: เข้าถึงระดับแอป, ตรวจ device posture ต่อเนื่อง (FortiClient ZTNA, Prisma Access, Zscaler ZPA, Cloudflare Access)
- Hardening VPN portal: patch ด่วน, จำกัด geo-IP, ปิด local admin login จาก WAN

**แบบทดสอบ**
1. VPN ข้ามยี่ห้อขึ้นไม่ได้ ตรวจอะไรเป็นลำดับแรก
2. ทำไม VPN portal ต้องมี MFA
3. ZTNA ต่างจาก VPN อย่างไรในมุม least privilege
4. Posture check ตรวจอะไรบ้าง
5. การป้องกัน brute force บน VPN portal

<details><summary>เฉลย</summary>

1. IKE version, proposal (encryption/hash/DH), PSK, peer ID, traffic selector/proxy ID, NAT-T
2. รหัสรั่วบ่อย VPN เป็นทางเข้าหลักของผู้โจมตี
3. VPN ให้เข้าถึงทั้ง network; ZTNA ให้เฉพาะแอปที่ได้สิทธิ์
4. OS patch, AV/EDR ทำงาน, disk encryption, domain-joined, cert ของเครื่อง
5. MFA, lockout/rate-limit, geo-IP block, ปิด portal ที่ไม่ใช้, แจ้งเตือนผ่าน SIEM
</details>

**5 โปรเจค**
- ⭐⭐ P1: IPsec FortiGate ↔ Palo Alto (lab) พร้อมเอกสาร parameter sheet
- ⭐⭐ P2: Remote VPN + MFA (RADIUS + TOTP) ใน lab
- ⭐⭐ P3: Cloudflare Access / Tailscale ทำ ZTNA เข้าเว็บภายใน
- ⭐⭐ P4: VPN parameter sheet template สำหรับแลกกับคู่ค้า
- ⭐⭐⭐ P5: แผนย้ายจาก SSL VPN → ZTNA ให้ลูกค้า 1,000 users (phase, ความเสี่ยง, การสื่อสาร)

---

## Level 48 — Zero Trust Concepts

> พื้นฐานจาก Roadmap หลัก [L66](../07-security.md)

**สิ่งที่ต้องรู้**
- NIST SP 800-207: PE/PA/PEP, "never trust, always verify", assume breach
- CISA Zero Trust Maturity Model: 5 pillars (Identity, Devices, Networks, Applications & Workloads, Data) + visibility, automation, governance
- Identity เป็นศูนย์กลาง: SSO, MFA ป้องกัน phishing (FIDO2), conditional access
- Network pillar: segmentation (macro → micro), encrypted traffic, ZTNA
- Zero Trust เป็นกลยุทธ์ ไม่ใช่สินค้าชิ้นเดียว — ต้องทำเป็น roadmap

**แบบทดสอบ**
1. PEP คืออะไร
2. 5 pillars ของ CISA ZTMM
3. ทำไม MFA แบบ SMS ไม่พอ
4. Conditional access คืออะไร
5. ทำไมลูกค้าซื้อ "Zero Trust box" แล้วยังไม่ใช่ Zero Trust

<details><summary>เฉลย</summary>

1. Policy Enforcement Point: จุดบังคับใช้ policy (firewall, ZTNA gateway, agent)
2. Identity, Devices, Networks, Applications & Workloads, Data
3. SIM swap, phishing แบบ real-time proxy (AiTM) → ใช้ FIDO2/passkey
4. อนุญาตการเข้าถึงตามเงื่อนไข (user, device, location, risk)
5. Zero Trust ต้องครอบคลุม identity, device, data, process และมีการตรวจต่อเนื่อง
</details>

**5 โปรเจค**
- ⭐ P1: สรุป NIST 800-207 + CISA ZTMM เป็นภาษาไทย 2 หน้า
- ⭐⭐ P2: Zero Trust maturity assessment ของลูกค้าสมมติ (ให้คะแนน 5 pillars)
- ⭐⭐ P3: Zero Trust roadmap 3 ปี (quick win → advanced)
- ⭐⭐ P4: Lab conditional access ด้วย Entra ID (trial) หรือ Keycloak + MFA
- ⭐⭐⭐ P5: Workshop deck "Zero Trust สำหรับผู้บริหาร" 15 สไลด์

---

## Level 49 — Zero Trust Segmentation (Micro-segmentation)

**สิ่งที่ต้องรู้**
- ทำไมต้องมี: ransomware เคลื่อนที่ east-west (lateral movement) ผ่าน SMB/RDP/WinRM
- วิธีทำ: network-based (VLAN/firewall/VRF), hypervisor-based (NSX DFW, Nutanix Flow), host/agent-based (Illumio, Akamai Guardicore, Microsoft/Windows firewall ผ่าน policy), cloud (security group), Kubernetes NetworkPolicy
- ขั้นตอน: visibility/application dependency mapping → label (env, app, role, location) → policy test mode → enforce ทีละ app → monitor
- Ringfence app, ring-fence high-value assets (AD, backup, DB), block high-risk ports ทั้งองค์กร
- Policy แบบ label-based แทน IP-based

**แบบทดสอบ**
1. ทำไม VLAN segmentation อย่างเดียวไม่พอสำหรับ Zero Trust
2. Application dependency mapping คืออะไร
3. ทำไมต้องเริ่มด้วย test/visibility mode
4. Port ที่ควรจำกัด east-west ก่อน (quick win)
5. Label-based policy ดีกว่า IP-based อย่างไร

<details><summary>เฉลย</summary>

1. Server ใน VLAN เดียวกันยังคุยกันได้ทั้งหมด ถ้า server หนึ่งถูกยึดก็ลามได้
2. การสำรวจว่าแต่ละแอปคุยกับอะไร port ไหน เพื่อเขียน policy ที่ถูกต้อง
3. ป้องกัน block traffic ที่จำเป็นจนแอปล่ม
4. RDP 3389, SMB 445, WinRM 5985/5986, SSH 22, RPC 135 (อนุญาตเฉพาะจาก jump host/admin)
5. Policy ตาม workload ไม่ผูกกับ IP ใช้ได้เมื่อย้าย/scale VM และอ่านเข้าใจง่าย
</details>

**5 โปรเจค**
- ⭐⭐ P1: Lab แอป 3 tier แล้วจำลอง lateral movement ก่อน/หลัง segmentation
- ⭐⭐ P2: Application dependency map จาก flow log/Zeek/NetFlow ของ lab (สคริปต์ + กราฟ)
- ⭐⭐ P3: Host-based segmentation ด้วย Windows Firewall GPO (block SMB/RDP ยกเว้น jump host)
- ⭐⭐⭐ P4: NSX DFW (HOL) หรือ Kubernetes NetworkPolicy/Cilium ทำ ringfence แบบ label-based
- ⭐⭐⭐ P5: ZTS project plan สำหรับลูกค้า 300 servers (phase, label taxonomy, rollout, KPI)

---

## Level 50 — NAC & 802.1X

> พื้นฐานจาก Roadmap หลัก [L66](../07-security.md)

**สิ่งที่ต้องรู้**
- NAC: Cisco ISE, Aruba ClearPass, FortiNAC, Forescout
- 802.1X (EAP-TLS, PEAP), MAB สำหรับ IoT/printer, profiling (DHCP fingerprint, CDP/LLDP, HTTP)
- Authorization: dynamic VLAN, dACL, SGT/TrustSec, CoA (Change of Authorization)
- Guest, BYOD onboarding, posture
- Rollout: monitor → low-impact → closed mode

**แบบทดสอบ**
1. CoA ใช้ทำอะไร
2. Profiling ช่วยอะไรกับ MAB
3. ทำไมต้องเริ่ม monitor mode
4. EAP-TLS ต้องเตรียมอะไร
5. NAC เกี่ยวกับ Zero Trust อย่างไร

<details><summary>เฉลย</summary>

1. ให้ NAC สั่ง switch/AP เปลี่ยนสิทธิ์ session ทันที (เช่น ย้ายไป quarantine)
2. ระบุประเภทอุปกรณ์จริง ลดการปลอม MAC
3. ดูผลกระทบและเก็บข้อมูลก่อน block ใคร
4. PKI (CA), cert ให้ทุกเครื่อง (auto-enrollment/MDM), RADIUS server cert
5. ตรวจตัวตนและอุปกรณ์ก่อนให้เข้าเครือข่าย (identity + device pillar)
</details>

**5 โปรเจค**
- ⭐⭐ P1: FreeRADIUS + switch 802.1X + dynamic VLAN (ต่อยอดจาก Roadmap หลัก L66)
- ⭐⭐ P2: Cisco ISE (DevNet sandbox/eval) policy set ง่าย ๆ
- ⭐⭐ P3: Device inventory + profiling ด้วย DHCP fingerprint (สคริปต์)
- ⭐⭐ P4: NAC rollout plan 800 พอร์ต
- ⭐⭐⭐ P5: Quarantine อัตโนมัติ: SIEM alert → NAC CoA → ย้ายเครื่องไป quarantine VLAN
