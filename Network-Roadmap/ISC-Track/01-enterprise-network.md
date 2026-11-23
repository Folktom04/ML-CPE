# Part 1 — Enterprise Network, Bandwidth Management & WAN Optimization (Level 1–20)

> ตามขอบเขตงาน ISC: **Core/Distribution/Access, Backbone 10G/40G/100G แบบไม่มี SPOF, Wi-Fi 6/7 High-Density, SD-WAN Multi-Branch, QoS, Bandwidth Management, WAN Optimization, Load Balancing**
> แบรนด์ที่ ISC ใช้: Cisco, Alcatel-Lucent Enterprise, Extreme Networks, Fortinet (FortiGate/FortiSwitch/FortiAP), HPE Aruba, Avaya

## Level ที่ใช้เนื้อหาเดิม (เรียนจาก Roadmap หลัก แล้วตอบ ISC Checkpoint)

**เกณฑ์ผ่าน:** ทำแบบทดสอบของ Level ต้นทางได้ ≥ 4/5 ข้อ ทำโปรเจคต้นทางอย่างน้อย 3 ชิ้น และตอบ ISC Checkpoint ได้

| Level | หัวข้อ | เรียนจาก | ISC Checkpoint |
|---|---|---|---|
| 1 | OSI & TCP/IP | [Roadmap L2–L3](../01-foundations.md) | อธิบายให้ลูกค้าภาครัฐฟังว่าปัญหาอยู่ที่ layer ไหน |
| 2 | สาย, ไฟเบอร์, SFP, อุปกรณ์ | [Roadmap L4–L5](../01-foundations.md) | เลือก SFP/QSFP (SR/LR, 10/40/100G) สำหรับ backbone ระหว่างอาคารได้ |
| 3 | IPv4, Subnetting, VLSM | [Roadmap L8–L10](../01-foundations.md) | ทำ IP plan โรงพยาบาลที่มี 30 VLAN ได้ใน 1 ชั่วโมง |
| 4 | ARP, ICMP, TCP/UDP, DHCP, DNS, NAT | [Roadmap L11–L17](../02-core-protocols.md) | ตั้ง DHCP relay ไป server กลางสำหรับทุก VLAN |
| 5 | IPv6 | [Roadmap L18–L19](../02-core-protocols.md) | ตอบ TOR ภาครัฐที่กำหนดว่าอุปกรณ์ต้องรองรับ IPv6 ได้ |
| 6 | Wireshark, tcpdump, nmap, iperf | [Roadmap L21–L25](../03-tools-and-troubleshooting.md) | วัด throughput backbone ด้วย iperf3 ก่อนส่งมอบ |
| 7 | Lab, Cisco IOS, Troubleshooting | [Roadmap L28–L30](../03-tools-and-troubleshooting.md) | แก้ปัญหาตาม bottom-up แล้วเขียนรายงานส่งลูกค้า |
| 8 | VLAN, Trunk, Inter-VLAN | [Roadmap L32–L34](../04-switching.md) | ออกแบบ VLAN ตามแผนก, ประเภทอุปกรณ์ (CCTV, IP phone, IoT) และ Guest |
| 9 | STP, EtherChannel, Port Security | [Roadmap L35–L38](../04-switching.md) | กำหนด STP root ที่ core และใส่ BPDU Guard ที่ access ทุกพอร์ต |
| 12 | Static, OSPF | [Roadmap L41–L46](../05-routing.md) | ทำ OSPF ระหว่าง core กับ firewall/WAN router |
| 13 | BGP & HSRP/VRRP | [Roadmap L48–L50](../05-routing.md) | ทำ gateway redundancy ที่ core ให้ทุก VLAN |
| 17 | QoS, NTP/Syslog/SNMP, AAA | [Roadmap L54–L56](../06-services-wireless-wan.md) | ตั้ง QoS voice (Avaya/Cisco IP phone), TACACS+/RADIUS สำหรับ admin, ส่ง log/SNMP เข้า NOC |

---

## Level 10 — Campus Core & 10G/40G/100G Backbone แบบไม่มี Single Point of Failure

**สิ่งที่ต้องรู้**
- 3-tier vs collapsed core; access → distribution 10/25G, distribution → core 40/100G
- Core redundancy: core คู่ (VSS/StackWise Virtual, VSF ของ Aruba/HPE, Virtual Chassis ของ ALE, MLAG/vPC) + dual-homed uplink + LACP
- Optics: SFP+ (10G), SFP28 (25G), QSFP+ (40G), QSFP28 (100G); SR (multimode ใกล้) / LR (single-mode 10 km); BiDi; ตรวจ DOM (rx/tx power)
- Fiber backbone ระหว่างอาคาร: 2 เส้นทาง (ring/ไม่ใช้ท่อเดียวกัน), OTDR test
- SPOF checklist: core, uplink, fiber path, power (PSU คู่ + UPS), firewall, ISP, DHCP/DNS
- Oversubscription และการขยายในอนาคต (พอร์ตว่าง ≥ 20–30%)

**แบบทดสอบ**
1. Core คู่แบบ StackWise Virtual/VSF ต่างจาก MLAG อย่างไร
2. ลิงก์ระหว่างอาคารห่าง 2 km ความเร็ว 10G ใช้ optic อะไร
3. ค่า DOM rx power ต่ำผิดปกติบอกอะไร
4. ทำไม fiber 2 เส้นวิ่งท่อเดียวกันยังเป็น SPOF
5. Access switch 48×1G uplink 2×10G oversubscription เท่าไร ยอมรับได้หรือไม่

<details><summary>เฉลย</summary>

1. StackWise Virtual/VSF รวมเป็น control plane เดียว (จัดการเหมือนเครื่องเดียว); MLAG แยก control plane 2 เครื่องแต่ประสานกันทำ LAG ข้ามเครื่อง
2. 10GBASE-LR (single-mode)
3. สายหรือหัวต่อสกปรก/เสีย, งอเกินรัศมี หรือระยะเกิน spec ของ optic
4. ถ้าท่อถูกขุดหรือไฟไหม้ ทั้ง 2 เส้นขาดพร้อมกัน (shared fate)
5. 48/20 = 2.4:1 ยอมรับได้สำหรับ access ทั่วไป (แนวทางทั่วไปคือไม่เกินประมาณ 20:1)
</details>

**5 โปรเจค**
- ⭐⭐ P1: ออกแบบ campus 5 อาคาร (core คู่, distribution ต่ออาคาร, ring fiber) พร้อม diagram
- ⭐⭐ P2: Lab core คู่ (MLAG/vPC บน cEOS หรือ StackWise Virtual ใน Packet Tracer) + access dual uplink LACP
- ⭐⭐ P3: Optics & fiber BOM (ชนิด optic, patch cord, ODF) สำหรับ P1
- ⭐⭐ P4: SPOF analysis ของ P1 (ตาราง component, ผลกระทบ, การป้องกัน)
- ⭐⭐⭐ P5: Failover test plan + ทดสอบใน lab (ปิด core 1 ตัว, ดึง uplink) วัด packet loss ด้วย ping 100 ms

---

## Level 11 — Multi-vendor Switching (Cisco, Alcatel-Lucent, Extreme, Aruba, FortiSwitch)

**สิ่งที่ต้องรู้**
- Cisco Catalyst (IOS-XE), Catalyst Center (DNA Center)
- Alcatel-Lucent Enterprise OmniSwitch (AOS 8), OmniVista; Virtual Chassis
- Extreme Networks (Switch Engine/EXOS, Fabric Engine/VOSS ใช้ SPB), ExtremeCloud IQ
- HPE Aruba CX (AOS-CX), VSX; Aruba Central
- Fortinet FortiSwitch จัดการผ่าน FortiGate (FortiLink): VLAN, NAC, security fabric
- เทียบคำสั่งพื้นฐาน: สร้าง VLAN, access/trunk port, LACP, STP, show MAC/interface

| งาน | Cisco IOS-XE | ALE AOS 8 | Aruba AOS-CX |
|---|---|---|---|
| สร้าง VLAN | `vlan 10` | `vlan 10 admin-state enable` | `vlan 10` |
| Access port | `switchport access vlan 10` | `vlan 10 members port 1/1/1 untagged` | `vlan access 10` |
| Trunk | `switchport mode trunk` | `vlan 10 members port 1/1/24 tagged` | `vlan trunk allowed 10,20` |
| ดู MAC | `show mac address-table` | `show mac-learning` | `show mac-address-table` |

**แบบทดสอบ**
1. FortiLink คืออะไร มีข้อดีอย่างไร
2. ALE ใช้แนวคิดใดในการกำหนด access/trunk ต่างจาก Cisco
3. Extreme Fabric Engine ใช้ protocol อะไรสร้าง fabric
4. Aruba VSX เทียบได้กับเทคโนโลยีใดของ Cisco
5. เมื่อลูกค้ามีหลายยี่ห้อ อะไรต้องตรวจเพื่อให้ทำงานร่วมกันได้

<details><summary>เฉลย</summary>

1. การจัดการ FortiSwitch จาก FortiGate โดยตรง ได้ policy/NAC/visibility รวมกับ firewall ในที่เดียว
2. กำหนดที่ VLAN ว่ามี port ใดเป็นสมาชิก untagged/tagged (VLAN-centric) แทนการตั้งที่ interface
3. SPB (Shortest Path Bridging, IEEE 802.1aq)
4. vPC (หรือ MLAG)
5. มาตรฐานเปิด: 802.1Q, LACP 802.3ad, RSTP/MSTP (ระวัง PVST+ ของ Cisco), LLDP, MTU, native VLAN
</details>

**5 โปรเจค**
- ⭐⭐ P1: Cheat sheet คำสั่งเทียบ 5 ยี่ห้อ (30 งานพื้นฐาน)
- ⭐⭐ P2: Lab Cisco ↔ Aruba CX (GNS3/EVE-NG มี image AOS-CX simulator) trunk + LACP + MSTP
- ⭐⭐ P3: FortiGate VM + FortiLink (หรือทำเอกสารขั้นตอนจาก Fortinet docs ถ้าไม่มี FortiSwitch)
- ⭐⭐ P4: Interoperability checklist สำหรับเครือข่ายหลายยี่ห้อ (STP mode, LACP, LLDP, VLAN)
- ⭐⭐⭐ P5: Config generator (Jinja2) สร้าง config access switch ได้ทั้ง 3 ยี่ห้อจาก YAML เดียว

---

## Level 14 — High-Density Wi-Fi 6/7 Design

**สิ่งที่ต้องรู้**
- Wi-Fi 6 (802.11ax): OFDMA, MU-MIMO, BSS coloring, TWT; Wi-Fi 6E เพิ่ม 6 GHz; Wi-Fi 7 (802.11be): 320 MHz, MLO (Multi-Link Operation), 4K-QAM
- High-density (หอประชุม, ห้องเรียน, โรงพยาบาล): ออกแบบตาม **capacity** ไม่ใช่แค่ coverage — clients/AP (ประมาณ 30–50 active ต่อ radio), channel 20/40 MHz, ลด TX power, ปิด low data rate
- Channel plan: 2.4 GHz (1/6/11), 5 GHz (UNII + DFS), 6 GHz
- AP placement: เพดาน, directional antenna ในห้องโถง, ระวังผนังคอนกรีต/กระจก/โลหะ
- Wired requirement: mGig uplink (2.5/5G) สำหรับ Wi-Fi 6E/7, PoE++ (802.3bt)
- Site survey: predictive (Ekahau/Hamina), post-install validation; requirement: RSSI ≥ -67 dBm, SNR ≥ 25 dB สำหรับ voice/video

**แบบทดสอบ**
1. ห้องประชุม 600 คน (คาดว่าอุปกรณ์ 1.5 เครื่อง/คน, active 60%) ใช้ AP กี่ตัวโดยประมาณ ถ้า 1 AP รับได้ 100 active clients (2 radio)
2. ทำไม high-density ต้องใช้ channel แคบ
3. MLO ของ Wi-Fi 7 คืออะไร
4. ทำไม AP Wi-Fi 7 ต้องการ PoE++ และ uplink mGig
5. Predictive survey ต่างจาก validation survey อย่างไร

<details><summary>เฉลย</summary>

1. 600 × 1.5 × 0.6 = 540 active → ประมาณ 6 AP (เผื่อเพิ่มเป็น 7–8 AP และวาง channel ไม่ทับกัน)
2. ได้ channel ใช้ซ้ำได้มากขึ้น ลด co-channel interference
3. อุปกรณ์เชื่อมต่อหลายย่าน (เช่น 5 + 6 GHz) พร้อมกัน เพิ่ม throughput และลด latency
4. Radio หลายตัวกินไฟมากกว่า PoE+ และ throughput เกิน 1G
5. Predictive = จำลองจากแบบแปลนก่อนติดตั้ง; Validation = วัดสัญญาณจริงหลังติดตั้งเพื่อยืนยันผล
</details>

**5 โปรเจค**
- ⭐⭐ P1: Capacity planning spreadsheet (users, devices, app bandwidth → จำนวน AP)
- ⭐⭐ P2: Predictive design ชั้นโรงพยาบาลหรือหอประชุมด้วย Hamina/Ekahau (free/trial)
- ⭐⭐ P3: Channel plan + TX power plan สำหรับ 20 AP
- ⭐⭐ P4: Switch/PoE budget สำหรับ AP Wi-Fi 7 (802.3bt, mGig)
- ⭐⭐⭐ P5: Wireless design document ฉบับส่งลูกค้า (requirement, survey, AP map, SSID, security, acceptance criteria)

---

## Level 15 — Wireless Controller, Multi-vendor WLAN & Operations

**สิ่งที่ต้องรู้**
- Centralized control: Cisco Catalyst 9800 WLC, Aruba (Mobility Controller/Central), Extreme (ExtremeCloud IQ), ALE OmniVista/OmniAccess Stellar, Fortinet (FortiGate เป็น controller ของ FortiAP)
- SSID design: Corp (WPA3-Enterprise/802.1X), Guest (captive portal, isolation), IoT (PSK แยก VLAN/iPSK/MPSK), ไม่ควรเกิน 3–4 SSID ต่อ radio
- Roaming 802.11k/v/r, band steering, airtime fairness
- Operation: client troubleshooting (association, auth, DHCP, DNS), RF report, rogue AP detection, firmware upgrade
- Location/analytics (ตามความต้องการลูกค้า)

**แบบทดสอบ**
1. ทำไมไม่ควรมี SSID มากเกินไป
2. ผู้ใช้เชื่อม Wi-Fi ได้แต่ไม่ได้ IP ตรวจอะไร
3. iPSK/MPSK แก้ปัญหาอะไร
4. Rogue AP คืออะไร ตรวจจับอย่างไร
5. ใช้ FortiGate เป็น controller เหมาะกับลูกค้าแบบไหน

<details><summary>เฉลย</summary>

1. แต่ละ SSID ส่ง beacon กิน airtime ทำให้ throughput รวมลดลง
2. VLAN ของ SSID มีบน trunk ถึง AP/controller หรือไม่, DHCP scope/relay, pool เต็ม
3. ให้อุปกรณ์ IoT แต่ละกลุ่มใช้ PSK ต่างกันบน SSID เดียว ตั้ง VLAN/policy แยกได้
4. AP ที่ไม่ได้รับอนุญาตต่อเข้าเครือข่าย ตรวจด้วย WIPS/scan ของ controller เทียบ MAC บน wired
5. สำนักงาน/สาขาขนาดเล็ก-กลาง ที่ใช้ FortiGate อยู่แล้ว ต้องการจัดการ security + Wi-Fi รวมกัน
</details>

**5 โปรเจค**
- ⭐⭐ P1: Packet Tracer WLC + 3 SSID (Corp 802.1X, Guest portal, IoT)
- ⭐⭐ P2: FreeRADIUS + WPA2/3-Enterprise + dynamic VLAN
- ⭐⭐ P3: Client troubleshooting flowchart (association → auth → DHCP → DNS → app)
- ⭐⭐ P4: เปรียบเทียบ WLAN 5 ยี่ห้อที่ ISC ใช้ (architecture, license, cloud/on-prem)
- ⭐⭐⭐ P5: Wi-Fi acceptance test (coverage, roaming, throughput) + รายงานส่งมอบ

---

## Level 16 — SD-WAN & Multi-Branch Interconnection

> พื้นฐานจาก Roadmap หลัก [L57–L60](../06-services-wireless-wan.md)

**สิ่งที่ต้องรู้**
- โครงสร้างสาขา: HQ hub + สาขา spoke; underlay = MPLS/broadband/4G-5G, overlay = IPsec
- FortiGate SD-WAN: SD-WAN member/zone, Performance SLA (ping/HTTP, latency/jitter/loss), SD-WAN rule (ตาม app/ISDB), ADVPN (spoke-to-spoke แบบ dynamic), BGP on loopback
- การจัดการหลายสาขา: FortiManager (template, ZTP), FortiAnalyzer
- Local internet breakout + security profile ที่สาขา
- เทียบผู้ผลิตอื่น: Cisco Catalyst SD-WAN, Aruba EdgeConnect, Palo Alto Prisma SD-WAN

**แบบทดสอบ**
1. Performance SLA ใช้ทำอะไร
2. ADVPN ช่วยอะไร
3. ทำไมต้องใช้ BGP บน loopback ใน SD-WAN overlay
4. Local breakout ต้องระวังอะไรด้าน security
5. ZTP ช่วยงาน rollout 50 สาขาอย่างไร

<details><summary>เฉลย</summary>

1. วัดคุณภาพแต่ละลิงก์เพื่อให้ rule เลือกลิงก์ที่ผ่านเกณฑ์ของแต่ละแอป
2. สร้าง tunnel ตรงระหว่างสาขาเมื่อมี traffic ไม่ต้องอ้อมผ่าน HQ
3. Session BGP ไม่ผูกกับ tunnel ใดเส้นหนึ่ง เมื่อ tunnel หนึ่งล่มยังคงอยู่
4. ต้องเปิด security profile (IPS, web filter, AV) ที่สาขาเหมือน HQ
5. ส่งอุปกรณ์ไปสาขา เสียบสายแล้วดึง config จาก FortiManager เอง ไม่ต้องส่งวิศวกรทุกสาขา
</details>

**5 โปรเจค**
- ⭐⭐ P1: Lab FortiGate SD-WAN HQ + 2 สาขา (2 ISP ต่อสาขา) + performance SLA
- ⭐⭐⭐ P2: เพิ่ม ADVPN + BGP แล้วทดสอบ spoke-to-spoke
- ⭐⭐ P3: SD-WAN rule ตามแอป (Microsoft 365 local breakout, ERP ผ่าน MPLS)
- ⭐⭐ P4: Branch standard design (อุปกรณ์, IP plan, template) สำหรับ 30 สาขา
- ⭐⭐⭐ P5: Rollout plan 30 สาขา (ZTP, ตารางเวลา, ทีมหน้างาน, test checklist ต่อสาขา)

---

## Level 18 — Bandwidth Management & Traffic Control

**สิ่งที่ต้องรู้**
- ปัญหาที่ลูกค้าเจอ: internet เต็มเพราะ streaming/อัปเดต/backup, แอปสำคัญ (ERP, HIS, VoIP) ช้า
- เครื่องมือ: traffic shaping บน FortiGate (shared/per-IP shaper, shaping policy), Palo Alto QoS, อุปกรณ์เฉพาะทาง (เช่น Sangfor IAM, Allot, Exinda/GFI)
- Policy: guaranteed/maximum bandwidth, priority, per-user/per-IP limit, ตามเวลา, ตามแอป (DPI)
- Visibility ก่อน control: top apps/users จาก FortiAnalyzer/NetFlow
- Fair use ใน Wi-Fi สาธารณะ/หอพัก/มหาวิทยาลัย

**แบบทดสอบ**
1. Guaranteed กับ Maximum bandwidth ต่างกันอย่างไร
2. ทำไมต้องดู visibility ก่อนตั้ง policy
3. Per-IP shaper ใช้เมื่อไร
4. Shaping ขาเข้า (download) ทำได้ดีเท่าขาออกหรือไม่ เพราะอะไร
5. ยกตัวอย่าง policy สำหรับโรงพยาบาล

<details><summary>เฉลย</summary>

1. Guaranteed = รับประกันขั้นต่ำเมื่อแย่งกัน; Maximum = เพดานสูงสุด
2. รู้ว่าอะไรใช้ bandwidth จริง ไม่ตั้ง policy ผิดจนกระทบแอปสำคัญ
3. จำกัดให้แต่ละผู้ใช้/อุปกรณ์ได้เท่ากัน (เช่น Guest Wi-Fi 5 Mbps ต่อเครื่อง)
4. ไม่ดีเท่า เพราะ packet มาถึงแล้ว ใช้ลิงก์ไปแล้ว ทำได้แค่ drop/delay ให้ TCP ลดความเร็วเอง
5. HIS/PACS/VoIP priority สูง + guaranteed, ระบบ update/streaming จำกัด maximum ในเวลาทำการ, Guest per-IP limit
</details>

**5 โปรเจค**
- ⭐⭐ P1: FortiGate traffic shaping lab (shared + per-IP + shaping policy ตามแอป)
- ⭐⭐ P2: Linux `tc` HTB สร้าง class ตาม subnet/port แล้ววัดผลด้วย iperf3
- ⭐⭐ P3: Visibility report: top apps/users จาก NetFlow (ntopng) ของ lab
- ⭐⭐ P4: Bandwidth policy document สำหรับมหาวิทยาลัย (นักศึกษา/บุคลากร/server)
- ⭐⭐⭐ P5: ทดลองก่อน/หลัง: VoIP MOS และเวลาโหลด ERP เมื่อมี download หนักพร้อมกัน

---

## Level 19 — WAN Optimization, Application Acceleration & Load Balancing

> พื้นฐานจาก Roadmap หลัก [L71–L72](../08-datacenter-cloud.md)

**สิ่งที่ต้องรู้**
- WAN optimization: data deduplication/byte caching, compression, TCP optimization, protocol acceleration (SMB, HTTP), ต้องติดตั้งคู่ทั้งสองฝั่ง (symmetric)
- ผู้ผลิต: Riverbed SteelHead, Sangfor WANO, Aruba EdgeConnect (Silver Peak), FortiGate WAN opt (ฟีเจอร์ในบางรุ่น/version — ตรวจ datasheet)
- Application Delivery Controller (ADC)/Load Balancer: F5 BIG-IP, Citrix NetScaler, FortiADC, Sangfor AD, HAProxy/Nginx
- Server load balancing (health check, persistence, SSL offload), Link load balancing (หลาย ISP), Global server load balancing (GSLB, DC/DR)
- วัดผลก่อน/หลัง: transfer time, latency, bandwidth saving %

**แบบทดสอบ**
1. Deduplication ใน WAN opt ทำงานอย่างไร
2. ทำไม WAN opt ช่วยไฟล์ที่ถูกเข้ารหัส/บีบอัดแล้วได้น้อย
3. Link load balancing ต่างจาก server load balancing อย่างไร
4. GSLB ใช้ทำอะไร
5. SSL offload ช่วยอะไร

<details><summary>เฉลย</summary>

1. จำ pattern ข้อมูลที่เคยส่ง ครั้งต่อไปส่งแค่ reference แทนข้อมูลจริง
2. ข้อมูลดูเป็นสุ่ม ไม่มี pattern ซ้ำให้ลด
3. Link LB = กระจาย traffic ขาออกไปหลาย ISP; Server LB = กระจาย request ไปหลาย server
4. กระจาย/สลับผู้ใช้ไปยัง DC หลายแห่งด้วย DNS (เช่น DC/DR active-active หรือ failover)
5. ย้ายภาระเข้ารหัส TLS ออกจาก server ไป ADC และทำให้ ADC ตรวจ/ปรับ traffic L7 ได้
</details>

**5 โปรเจค**
- ⭐⭐ P1: HAProxy server LB + health check + SSL offload (ต่อยอด Roadmap L71)
- ⭐⭐ P2: Link load balancing 2 ISP บน FortiGate/Linux
- ⭐⭐ P3: จำลอง WAN (netem: 50 ms, 10 Mbps) แล้ววัดการโอนไฟล์ SMB ก่อน/หลังเปิด compression/cache (เช่น ใช้ rsync, Squid cache)
- ⭐⭐⭐ P4: GSLB ด้วย DNS (PowerDNS/BIND + health check script) สลับ DC → DR
- ⭐⭐ P5: ตารางเปรียบเทียบ ADC/WAN opt 4 ยี่ห้อ + เมื่อไรควรเสนอให้ลูกค้า

---

## Level 20 — Capstone: Enterprise Network (โรงพยาบาล/หน่วยงานรัฐ)

**โจทย์:** โรงพยาบาลรัฐ 5 อาคาร ผู้ใช้ 2,000 คน อุปกรณ์การแพทย์/IoT 800 เครื่อง Wi-Fi ผู้ป่วยและญาติ และมี 3 รพ.สต./สาขาเชื่อมเข้ามา ต้องการ backbone 40/100G ไม่มี SPOF, Wi-Fi 6/7 ทั่วทุกอาคาร, HIS/PACS ต้องลื่น และ Guest ต้องไม่กระทบระบบหลัก

**แบบทดสอบ (Self-review)**
1. มี SPOF เหลืออยู่ที่ใด (core, fiber path, power, firewall, ISP)
2. PACS (ไฟล์ภาพใหญ่) และ HIS ได้ bandwidth/priority เพียงพอหรือไม่
3. Wi-Fi ผ่านเกณฑ์ RSSI/SNR/roaming ในหอผู้ป่วยหรือไม่ (มีผล survey)
4. สาขาใช้ SD-WAN + backup link และ failover ทดสอบแล้วหรือยัง
5. Guest/IoT แยก VLAN, จำกัด bandwidth และเข้าระบบภายในไม่ได้หรือยัง

**5 โปรเจค**
- ⭐⭐⭐ P1: HLD + LLD (VLAN/IP, core/distribution/access, fiber, optics)
- ⭐⭐⭐ P2: Wi-Fi design + predictive survey + SSID/security
- ⭐⭐⭐ P3: SD-WAN สาขา + bandwidth policy + QoS
- ⭐⭐⭐ P4: Lab ย่อส่วน + failover test + UAT document
- ⭐⭐⭐ P5: BOM (Cisco/ALE/Extreme/Aruba/Fortinet ทางเลือก 2 แบบ) + proposal ตาม TOR ภาครัฐ
