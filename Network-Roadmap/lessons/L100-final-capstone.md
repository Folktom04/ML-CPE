# บทเรียน Level 100 — Final Capstone: Enterprise Network End-to-End (ฉบับละเอียด)

> อ่านจบแล้วจะ: มีแผนลงมือทำ capstone ครบทุกส่วน (design → build → secure → operate → present) · เห็นตัวอย่าง requirement, HLD, IP plan, policy matrix, QoS, HA test plan, BOM/TCO ของบริษัทสมมติ "ThaiTech Co." · รู้ว่าแต่ละส่วนเชื่อมกับบทเรียนใดใน roadmap · มี checklist ตรวจคุณภาพก่อนนำเสนอ · ได้ผลงานที่ใช้เป็น portfolio ระดับมืออาชีพ

---

## 1. โจทย์

**บริษัท "ThaiTech Co." (สมมติ)**
- พนักงาน **1,500 คน**
- **HQ กรุงเทพฯ** อาคาร 5 ชั้น + **data center ขนาดเล็ก** ในอาคาร
- **4 สาขา:** เชียงใหม่ ขอนแก่น ชลบุรี หาดใหญ่
- **AWS** สำหรับแอปลูกค้า (web/API)
- **โรงงาน 1 แห่ง** (ระบบ **OT**: PLC, SCADA, HMI)
- รองรับ **remote work 40%**

> ทุกอย่างในบทนี้เป็นข้อมูลสมมติเพื่อการเรียนรู้ — เมื่อทำจริงให้ใช้ requirement ของคุณเองหรือปรับตัวเลขได้ แต่ต้องบันทึก assumption ทุกข้อ

### สิ่งที่ต้องส่งมอบ (10 รายการ)
| # | Deliverable | บทที่เกี่ยวข้อง |
|---|---|---|
| 1 | Requirements document + assumptions | L92 |
| 2 | HLD: topology, ADR, security zones | L40, L67, L92 |
| 3 | LLD: IP plan (v4+v6), VLAN, routing, WAN/SD-WAN, Wi-Fi, policy matrix, QoS, AAA/802.1X, DNS/DHCP, NTP/logging/monitoring | Tier 1–7 |
| 4 | Lab ย่อส่วน: HQ + 2 สาขา + cloud VPC | L73–79, L84 |
| 5 | Automation: NetBox (SoT) + Ansible/Nornir + CI (Batfish) | L81–89 |
| 6 | Monitoring: Grafana dashboard + alert | L86–87 |
| 7 | Security: IDS, SIEM, IR playbook | L61–70 |
| 8 | HA/DR test report (failover 10 กรณี) | L93 |
| 9 | BOM + TCO 5 ปี | L94 |
| 10 | Presentation 20 นาที (ผู้บริหาร + ทีมเทคนิค) | L92, L94, L99 |

---

## 2. Phase 1 — Design: Requirements (ตัวอย่าง)

### Business requirements
| ID | Requirement | Priority |
|---|---|---|
| BR-1 | ระบบขาย/ERP ใช้งานได้ทุกสาขา ≥ 99.9%/เดือน | Must |
| BR-2 | พนักงาน remote 40% (600 คน) เข้าถึงแอปภายในอย่างปลอดภัย | Must |
| BR-3 | แอปลูกค้าบน AWS พร้อมใช้ 99.95%, ป้องกัน DDoS/web attack | Must |
| BR-4 | โรงงานผลิตต่อเนื่องได้แม้ IT network/อินเทอร์เน็ตมีปัญหา | Must |
| BR-5 | ปฏิบัติตาม PDPA และเก็บ log ตาม พ.ร.บ.คอมพิวเตอร์ (≥ 90 วัน) | Must |
| BR-6 | เปิดสาขาใหม่ได้ภายใน 2 สัปดาห์ (template) | Should |
| BR-7 | ลดค่า WAN เทียบ MPLS เดิม | Should |

### Technical requirements (วัดได้)
| ID | Requirement |
|---|---|
| TR-1 | ไม่มี SPOF ที่ core/firewall/WAN ของ HQ; failover ≤ 3 วินาที |
| TR-2 | สาขา dual ISP; failover WAN ≤ 1 วินาทีสำหรับ voice (SD-WAN) |
| TR-3 | latency สาขา → HQ ERP ≤ 40 ms (p95); MOS ของ Teams/VoIP ≥ 4.0 |
| TR-4 | ทุกอุปกรณ์ในสำนักงาน ผ่าน 802.1X/MAB + NAC; guest แยก 100% |
| TR-5 | OT แยกจาก IT ด้วย DMZ (IEC 62443 zones/conduits); ไม่มีการเชื่อมต่อจาก internet ตรงถึง OT |
| TR-6 | IPv6 dual-stack สำหรับ internet edge และ AWS (phase 1), ภายใน (phase 2) |
| TR-7 | config ทุกอุปกรณ์อยู่ใน Git, deploy ผ่าน pipeline, drift ตรวจทุกวัน |
| TR-8 | Wi-Fi รองรับ 2 อุปกรณ์/คน, ห้องประชุม 50 คน, roaming ไม่หลุด voice |

### Constraints & Assumptions
- งบ CAPEX 3 ปีแรก (สมมติ) ~25 ล้านบาท, ทีม network 4 คน (2 คนมีประสบการณ์ Fortinet), สัญญา MPLS เดิมหมด 9 เดือน
- **Assumption:** ISP ทุกสาขาให้ 500 Mbps–1 Gbps ได้ภายใน 60 วัน; อาคาร HQ มี riser fiber ทุกชั้น; โรงงานอยู่ชลบุรีใกล้สาขา

---

## 3. Phase 1 — HLD

### Topology ภาพรวม
```
                              ┌──────────────── Internet ────────────────┐
                              │                                          │
             ┌───────── ISP-A (1G DIA) ─────────┐  ┌──── ISP-B (1G DIA) ─┘
             │                                  │  │
        [Edge/SD-WAN hub + NGFW HA pair (HQ)] ◄─┴──┘ ── BGP (PI /24 + /48 หรือ PA)
             │ inside zones: USERS / SERVERS / DMZ / MGMT / GUEST / VOICE / OT-DMZ
        [Core: 2 × L3 (MLAG/EVPN collapsed core) + DC leaf คู่]
         │       │        │
   [Access ชั้น 1–5]  [DC: hypervisor cluster, AD/DNS/DHCP, ERP, file, NAC, SIEM]
   (802.1X, PoE AP/โทรศัพท์)
             │
   SD-WAN overlay (IPsec, dual ISP ต่อสาขา) ──► สาขา CNX / KKC / CBI / HDY (SD-WAN edge + switch + AP)
             │                                       │
             └──► AWS: TGW + inspection VPC + VPC prod/dev (Site-to-Site VPN ×2 → ภายหลัง Direct Connect)
                                                     │
   โรงงาน (ชลบุรี): [IT zone] ─ [OT-DMZ (historian, jump host, patch server)] ─ [OT: Level 3/2/1 cell zones]
   Remote users: ZTNA/SSE (SASE) หรือ SSL/IPsec VPN + MFA → เข้าถึงเฉพาะแอปที่อนุญาต
```
### ADR ตัวอย่างที่ควรมี (เขียนตามแบบ L92)
| ADR | การตัดสินใจ |
|---|---|
| ADR-001 | SD-WAN (dual internet) แทน MPLS — ราคา/ความเร็ว, ยอมรับเพราะใช้ dual ISP + SLA probe |
| ADR-002 | Collapsed core (2 ตัว) แทน 3-tier — ขนาด 1,500 คน 5 ชั้น ไม่จำเป็นต้องมี distribution แยก |
| ADR-003 | L3 routed access หรือ L2 access + L3 core — (เลือกและให้เหตุผล: failure domain vs ความง่าย) |
| ADR-004 | NGFW ยี่ห้อเดียวทั้ง HQ/สาขา/SD-WAN — ทีมมีทักษะ, management รวม; ความเสี่ยง vendor lock-in ยอมรับ |
| ADR-005 | Remote access: ZTNA แทน full-tunnel VPN สำหรับผู้ใช้ทั่วไป; VPN เฉพาะ IT admin |
| ADR-006 | OT แยกด้วย firewall + OT-DMZ, ไม่มี remote access ตรงสู่ OT (ผ่าน jump host + MFA + session recording) |
| ADR-007 | AWS: Transit Gateway + inspection VPC, VPN ก่อน แล้ว DX เมื่อ traffic > X |
| ADR-008 | NetBox เป็น SoT + Ansible/Nornir + GitHub Actions/Batfish |

### Security zones
```
 INTERNET ─ [NGFW] ─┬─ DMZ (reverse proxy/WAF, mail relay)
                    ├─ USERS (corp) · VOICE · PRINTERS/IoT · GUEST (internet only)
                    ├─ SERVERS (app, DB แยก sub-zone) · INFRA (AD/DNS/DHCP/NAC)
                    ├─ MGMT (jump host, NetBox, monitoring, OOB) ← เข้าได้จาก IT admin ผ่าน MFA เท่านั้น
                    ├─ OT-DMZ ─ [OT firewall] ─ OT (cell/area zones)
                    └─ SD-WAN branches / AWS (ตาม policy matrix)
```

---

## 4. Phase 1 — LLD (ตัวอย่างส่วนสำคัญ)

### IP Plan (IPv4) — ออกแบบให้ summarize ได้ (L10, L79)
```
 10.0.0.0/8   ThaiTech ทั้งหมด
 ├── 10.0.0.0/12   On-prem
 │   ├── 10.0.0.0/16   HQ กรุงเทพ (BKK)
 │   │   ├── 10.0.0.0/24      Infra loopbacks / P2P (/32, /31)
 │   │   ├── 10.0.10.0/24     MGMT
 │   │   ├── 10.0.20.0/22     USERS ชั้น 1–5 (หรือ /24 ต่อชั้น: 10.0.20–24)
 │   │   ├── 10.0.30.0/23     VOICE
 │   │   ├── 10.0.40.0/24     PRINTERS/IoT
 │   │   ├── 10.0.50.0/22     WIRELESS-CORP
 │   │   ├── 10.0.100.0/22    SERVERS (DC)  · 10.0.104.0/24 INFRA · 10.0.110.0/24 DMZ
 │   │   └── 172.31.0.0/22    GUEST (NAT ออกเน็ตเท่านั้น, ไม่ route ภายใน)
 │   ├── 10.1.0.0/16   CNX   ├── 10.2.0.0/16 KKC   ├── 10.3.0.0/16 CBI   ├── 10.4.0.0/16 HDY
 │   │   (template สาขา: .10 MGMT /24, .20 USERS /23, .30 VOICE /24, .50 WLAN /23)
 │   └── 10.8.0.0/16   Factory: 10.8.0.0/20 IT · 10.8.100.0/24 OT-DMZ · 10.8.128.0/17 OT (ไม่ route ไป IT ตรง)
 ├── 10.16.0.0/12  AWS (10.16.0.0/16 prod-vpc · 10.17.0.0/16 dev-vpc · 10.18.0.0/16 inspection/shared)
 └── 10.64.0.0/16  Remote users (ZTNA/VPN pool)
 IPv6: 2001:db8:1000::/36 (ตัวอย่างเอกสาร — ใช้ prefix จริงจาก ISP/APNIC) → /48 ต่อ site, /64 ต่อ VLAN (L18/19)
```
### VLAN template (สาขา)
| VLAN | ชื่อ | Subnet | หมายเหตุ |
|---|---|---|---|
| 10 | MGMT | 10.x.10.0/24 | อุปกรณ์ network |
| 20 | USERS | 10.x.20.0/23 | 802.1X → dynamic VLAN |
| 30 | VOICE | 10.x.30.0/24 | QoS EF |
| 40 | IOT | 10.x.40.0/24 | printer, CCTV — ACL จำกัด |
| 50 | WLAN-CORP | 10.x.50.0/23 | WPA3-Enterprise |
| 99 | GUEST | 172.31.x.0/24 | internet only, client isolation |
| 999 | BLACKHOLE/parking | — | พอร์ตที่ไม่ใช้ |

### Routing
- HQ ภายใน: OSPF area 0 (core ↔ firewall ↔ DC) หรือ static + BGP ไป SD-WAN (เลือกและเหตุผลใน ADR)
- SD-WAN: overlay BGP (hub = HQ, iBGP/eBGP ตามผลิตภัณฑ์), สาขาประกาศ /16 ของตัวเอง, HQ ประกาศ summary + default
- Internet: eBGP กับ ISP-A/B (ถ้ามี PI/ASN) หรือ dual default + IP SLA (L42/49)
- AWS: BGP ผ่าน VPN (2 tunnel × 2 router) → TGW, prefix-list จำกัดทั้งสองทิศ (L79)
- **BFD** บนลิงก์ core/WAN ที่รองรับ

### Firewall policy matrix (ย่อ — ฉบับเต็มต้องครบทุกคู่ zone)
| From \ To | INFRA | SERVERS | DMZ | AWS-PROD | INTERNET | MGMT | OT-DMZ |
|---|---|---|---|---|---|---|---|
| USERS | DNS, DHCP, AD (Kerberos/LDAPS) | ERP 443, File 445 | 443 | 443 (แอปภายใน) | Web ผ่าน SWG/SSE | ✖ | ✖ |
| GUEST | DHCP/DNS (เฉพาะ guest) | ✖ | ✖ | ✖ | 80/443 (+rate limit) | ✖ | ✖ |
| VOICE | DNS/NTP | call manager/SBC | ✖ | ✖ | SIP trunk ผ่าน SBC | ✖ | ✖ |
| MGMT (jump) | ✔ admin | ✔ admin | ✔ admin | ✔ admin | updates | — | jump→OT-DMZ |
| SERVERS | ✔ | ตาม app flow | ✖ | API ที่กำหนด | updates allowlist | ✖ | ✖ |
| OT-DMZ | NTP | ✖ | ✖ | ✖ | ✖ (patch ผ่าน WSUS ภายใน) | log → SIEM | — |
(+ log ทุก deny, IPS profile บน policy ที่ไปหา server/internet, SSL inspection ตามนโยบายและข้อยกเว้น PDPA — L62)

### QoS (L54)
| Class | DSCP | Queue | ตัวอย่าง |
|---|---|---|---|
| Voice | EF (46) | Priority ≤ 10–20% | VoIP, Teams audio |
| Interactive video | AF41 | 20% | Teams/Zoom video |
| Business-critical | AF31 | 25% | ERP, POS |
| Default | 0 | ที่เหลือ | ทั่วไป |
| Scavenger | CS1 | ≤ 5% | backup, update, streaming |
SD-WAN: application-aware routing — voice ไปลิงก์ที่ jitter/loss ต่ำสุด, backup ไปลิงก์ที่ถูกกว่า

### AAA/802.1X/NAC (L66)
- RADIUS (ISE/ClearPass/FortiNAC/PacketFence) คู่ HA; EAP-TLS (cert จาก PKI ภายใน) สำหรับเครื่องบริษัท, PEAP เฉพาะช่วง transition
- MAB + profiling สำหรับ printer/IoT/โทรศัพท์ → dynamic VLAN/dACL
- TACACS+ สำหรับ admin อุปกรณ์ (command authorization + accounting)

### Services (L15/16/55)
- DNS: AD-integrated ×2 (HQ) + ×1 ต่อ region/AWS (Route 53 Resolver endpoints สำหรับ hybrid)
- DHCP: failover pair ที่ HQ, relay จากทุก SVI; สาขาใช้ DHCP บน SD-WAN edge หรือส่วนกลาง (เลือก)
- NTP: 2 แหล่งภายใน (sync กับ NTP สาธารณะ/GPS) → ทุกอุปกรณ์ (สำคัญต่อ log/cert/802.1X)
- Syslog → SIEM (เก็บ ≥ 90 วัน), SNMPv3/telemetry → monitoring, NetFlow/IPFIX จาก firewall/SD-WAN

### Wi-Fi (L51–52)
- Predictive + post-install survey; 5/6 GHz เป็นหลัก, 20/40 MHz ในพื้นที่หนาแน่น
- SSID: CORP (WPA3-Enterprise), GUEST (OWE/WPA3-SAE + portal), IOT (WPA2/3-PSK ต่ออุปกรณ์ — iPSK/MPSK ถ้ามี)
- 802.11r/k/v สำหรับ voice roaming, multicast-to-unicast

---

## 5. Phase 2 — Build: Lab ย่อส่วน

### ขอบเขต lab
```
 containerlab (หรือ EVE-NG):
   HQ: core1, core2 (Arista cEOS / Nokia SR Linux / FRR), fw-hq (FortiGate VM / pfSense / OPNsense / VyOS)
   Branch CNX, Branch KKC: edge router/firewall + switch
   "ISP-A", "ISP-B": router FRR จำลอง internet + netem (delay/loss)
   AWS: VPC จริง (free tier/ค่าใช้จ่ายต่ำ ลบหลังทดสอบ) หรือจำลองด้วย router อีกตัว
   Servers: Linux containers (DNS, web, iperf3, syslog)
```
```yaml
# topology.clab.yml (ตัวอย่างย่อ)
name: thaitech
topology:
  kinds:
    linux: { image: frrouting/frr:v9.1.0 }
  nodes:
    core1:  { kind: arista_ceos, image: ceos:4.32.0F }
    core2:  { kind: arista_ceos, image: ceos:4.32.0F }
    fw-hq:  { kind: linux, image: vyos/vyos:1.4 }   # หรือ firewall VM ใน EVE-NG
    isp-a:  { kind: linux }
    isp-b:  { kind: linux }
    br-cnx: { kind: linux }
    br-kkc: { kind: linux }
    srv-dns:{ kind: linux, image: alpine:3.20 }
  links:
    - endpoints: ["core1:eth1", "core2:eth1"]
    - endpoints: ["core1:eth2", "fw-hq:eth1"]
    - endpoints: ["core2:eth2", "fw-hq:eth2"]
    - endpoints: ["fw-hq:eth3", "isp-a:eth1"]
    - endpoints: ["fw-hq:eth4", "isp-b:eth1"]
    - endpoints: ["isp-a:eth2", "br-cnx:eth1"]
    - endpoints: ["isp-b:eth2", "br-cnx:eth2"]
    - endpoints: ["isp-a:eth3", "br-kkc:eth1"]
    - endpoints: ["isp-b:eth3", "br-kkc:eth2"]
```
(เลือก image ที่คุณมีสิทธิ์ใช้งาน; ตรวจ tag ของ image ที่มีจริงก่อนใช้)

### Automation pipeline (L84–89)
```
 NetBox (sites, devices, prefixes, VLANs, IPs, config contexts)
   → render.py / Ansible templates (Jinja2) → rendered/*.cfg
   → GitHub Actions: yamllint + schema → Batfish tests:
        - guest ไม่ถึง 10.0.0.0/8
        - users ถึง ERP 443 ได้
        - ไม่มี undefined references / BGP session compatible
   → (manual approve) → Ansible/Nornir deploy ไป lab → post-check (pyATS/SuzieQ/ping mesh)
   → daily drift check (backup → diff กับ rendered)
```
**เกณฑ์ "เสร็จ":** ลบ lab ทิ้งแล้วสร้างใหม่ทั้งหมดจาก Git + NetBox ได้ด้วยคำสั่งไม่กี่คำสั่ง

---

## 6. Phase 3 — Secure

| สิ่งที่ต้องมี | วิธีใน lab |
|---|---|
| Firewall policy ตาม matrix + IPS profile | firewall VM; Batfish ทดสอบ policy |
| 802.1X/NAC | FreeRADIUS/PacketFence + switch ที่รองรับ (หรือ hostapd/wpa_supplicant จำลอง) |
| Management plane hardening | SSH เท่านั้น, AAA, ACL จาก MGMT, ปิดบริการที่ไม่ใช้, SNMPv3 (L53/55/56) |
| IDS/NSM | Suricata/Zeek บน SPAN/mirror ของ core (L64) |
| SIEM | Wazuh/Elastic/Graylog รับ syslog + Suricata alerts; dashboard + use case 5 ข้อ (brute force, port scan, admin login นอกเวลา, config change, DNS ผิดปกติ) (L68) |
| IR playbook | 3 ฉบับ: ransomware ในสาขา, DDoS ต่อแอปบน AWS, firewall config ผิดจนบริการล่ม (L70) |
| Self-pentest (เฉพาะ lab ของตัวเอง) | nmap ตรวจ segmentation จาก GUEST/USERS, ตรวจว่า management เข้าไม่ได้ (L69) |

> ⚠️ การสแกน/ทดสอบเจาะระบบทำได้เฉพาะ lab ของตัวเองหรือระบบที่ได้รับอนุญาตเป็นลายลักษณ์อักษรเท่านั้น

---

## 7. Phase 4 — Operate

### Monitoring (L86–87)
- Prometheus + snmp_exporter/gNMI + blackbox_exporter + Grafana
- Dashboard: **Executive** (สถานะ site, SLO ERP, incident) · **WAN/SD-WAN** (utilization, latency, loss, jitter ต่อสาขา) · **Core/DC** · **Firewall** (session, CPU, VPN, HA state) · **Services** (DNS/DHCP/RADIUS/NTP)
- Alert 10 ข้อที่ actionable (ตัวอย่าง): ISP down, BGP/OSPF neighbor down, HA failover, WAN > 85% 15 นาที, interface errors เพิ่ม, DHCP scope > 80%, cert หมดอายุใน 30 วัน, synthetic ERP ล้มเหลว, CPU firewall > 80% 10 นาที, config change นอก pipeline (drift)
- Flow: ntopng/Akvorado จาก firewall/SD-WAN

### Runbooks & Change process (L95)
- Runbook 10 ฉบับ (ISP ล่ม, core ล่ม, firewall failover, เพิ่มสาขาใหม่, เพิ่ม VLAN, เปลี่ยน cert, user VPN/ZTNA, upgrade firmware, DR failover, NAC ล้มเหลว)
- Change template + ตัวอย่าง 2 รายการ (standard และ normal)

### HA/DR Test (L93) — ทดสอบ 10 กรณี
| # | Scenario | วิธีทดสอบ | ผลที่คาดหวัง | วัดอย่างไร |
|---|---|---|---|---|
| 1 | ISP-A ของ HQ ขาด | ปิด link | traffic ไป ISP-B ≤ 3 วิ | ping ต่อเนื่อง + log |
| 2 | Core1 ล่ม | ปิด node | ไม่มีผลต่อผู้ใช้ > 3 วิ | ping จาก access, HSRP/VRRP/anycast log |
| 3 | Firewall active ล่ม | reboot | HA failover, session คงอยู่ | ssh/HTTP session ไม่หลุด |
| 4 | สาขา ISP หลักขาด | ปิด link | voice ย้ายลิงก์ ≤ 1 วิ | iperf UDP/jitter, SD-WAN log |
| 5 | Brownout: loss 5% บนลิงก์หลัก | netem | SD-WAN ย้าย app สำคัญ | SLA probe, MOS |
| 6 | VPN tunnel AWS 1 เส้นล่ม | ปิด tunnel | BGP ใช้อีก tunnel | curl ไปแอป AWS |
| 7 | DNS server หลักล่ม | stop service | client ใช้ตัวรอง | dig timing |
| 8 | RADIUS หลักล่ม | stop | auth ไปตัวรอง / critical VLAN | 802.1X log |
| 9 | Config ผิดถูก deploy | push config ที่ Batfish ควรจับได้ / rollback | pipeline บล็อก หรือ rollback ภายใน X นาที | CI log |
| 10 | DR: HQ DC ใช้ไม่ได้ | ปิด DC segment | แอปสำคัญเปิดที่ DR/AWS ตาม runbook ภายใน RTO | เวลาจริงเทียบ RTO |
บันทึก: ผลจริง vs คาดหวัง, ปัญหาที่พบ, การแก้ไข, ทดสอบซ้ำ

---

## 8. Phase 5 — Present: BOM, TCO, Presentation

### BOM (ระดับสูง — ตัวอย่างโครงสร้าง ไม่ใช่ราคาจริง)
| หมวด | รายการ | จำนวน |
|---|---|---|
| HQ Core | L3 switch 48×25G + 8×100G | 2 |
| HQ Access | 48-port PoE+ multigig (stack 2–3 ต่อชั้น) | ~15 |
| DC | leaf 25/100G | 2 |
| Firewall/SD-WAN | NGFW HQ (HA) | 2 |
| | SD-WAN edge สาขา (HA หรือเดี่ยว + LTE) | 4–8 |
| Wireless | AP Wi-Fi 6E/7 (HQ ~60, สาขา ~8–10 ต่อแห่ง) | ~100 |
| OT | Industrial firewall + switch | ตามโรงงาน |
| Services | NAC/RADIUS, SIEM, monitoring (VM/subscription) | — |
| Licenses/Subscriptions | security services, SD-WAN, NAC, ZTNA/SSE ต่อผู้ใช้ | 5 ปี |
| Circuits | ISP DIA ×2 ต่อ site, AWS VPN/DX | รายเดือน |
| Services | ติดตั้ง, migration, training | — |

### TCO 5 ปี (โครงสร้างตาม L94)
CAPEX (hardware, ติดตั้ง) + OPEX (subscription, support, วงจร, cloud, ค่าแรงดูแล) — แสดง **อย่างน้อย 2 ทางเลือก** (เช่น NGFW on-prem ทุกสาขา vs SASE) พร้อมข้อดี/ความเสี่ยง และ **ค่าใช้จ่ายรายปี** (ให้ฝ่ายการเงินวางงบ)

### Presentation 20 นาที
| ช่วง | ผู้บริหาร (10 นาที) | ทีมเทคนิค (10 นาที) |
|---|---|---|
| 1 | ปัญหา/เป้าหมายธุรกิจ, ความเสี่ยงปัจจุบัน | สถาปัตยกรรม HLD + เหตุผล (ADR) |
| 2 | Solution ภาพรวม (ภาษาธุรกิจ) | Demo: pipeline deploy การเปลี่ยนแปลง + Batfish จับ policy ผิด |
| 3 | ประโยชน์: availability, security, ค่า WAN, เปิดสาขาเร็ว | Demo: failover ISP/Core แบบ live + dashboard |
| 4 | ค่าใช้จ่าย 5 ปี + ทางเลือก + แนะนำ | Security: zones, NAC, SIEM use cases |
| 5 | Timeline/phase + ความเสี่ยง + สิ่งที่ต้องการให้อนุมัติ | Operations: runbook, monitoring, DR test results |
**ตัวอย่าง slide ปิด (ผู้บริหาร):** "อนุมัติ phase 1 (HQ + 2 สาขา) งบ X ล้าน เริ่ม Q1 — ผลลัพธ์: ERP availability 99.9% → 99.95%, ค่า WAN ลด ~30%, เปิดสาขาใหม่จาก 6 สัปดาห์เหลือ 2 สัปดาห์"

### Migration plan (สรุป)
```
 Phase 0: Discovery + NetBox + backup/Git + monitoring (เห็นสภาพปัจจุบัน)
 Phase 1: HQ core + firewall + internet edge (window สุดสัปดาห์, rollback เป็นขั้น)
 Phase 2: SD-WAN pilot 1 สาขา → ขยายอีก 3 สาขา (ทีละสาขา) → ยกเลิก MPLS ก่อนหมดสัญญา
 Phase 3: 802.1X (monitor mode → low-impact → closed mode ทีละกลุ่ม — L66)
 Phase 4: AWS hybrid (VPN → DX ถ้าจำเป็น), ZTNA สำหรับ remote
 Phase 5: โรงงาน OT segmentation (ร่วมกับทีม OT — ไม่หยุดการผลิต, ทำในช่วงหยุดซ่อมบำรุง)
```

---

## 9. Self-Review Checklist ก่อนส่ง

**Design**
- [ ] requirement ทุกข้อ trace ไปยัง design decision ได้ (traceability matrix)
- [ ] ทุก **SPOF** ถูกระบุ และมีแผนรองรับหรือการยอมรับความเสี่ยงที่บันทึกไว้
- [ ] IP plan ไม่ชนกับ AWS/remote pool/partner, summarize ได้, มีที่ว่างโต 3–5 ปี
- [ ] ADR ครบสำหรับการตัดสินใจสำคัญ

**Build/Automation**
- [ ] ทุก config อยู่ใน Git และ **deploy ซ้ำได้** จาก NetBox + pipeline
- [ ] Policy matrix **ทดสอบอัตโนมัติ** ได้ครบ (Batfish)
- [ ] ไม่มี secret ใน repo

**Security**
- [ ] guest/IoT/OT แยกจริง (พิสูจน์ด้วย test)
- [ ] management plane เข้าถึงได้เฉพาะ jump host + MFA
- [ ] log ไปถึง SIEM และมี use case ที่ทำงาน

**Operate**
- [ ] ถ้าลิงก์ ISP หลักขาด ผู้ใช้สังเกตเห็นภายใน **กี่วินาที** — มีตัวเลขจากการทดสอบจริง
- [ ] alert ทุกตัวมี runbook
- [ ] **คนใหม่อ่านเอกสารแล้ว troubleshoot ได้ภายใน 1 วัน** (ลองให้เพื่อนอ่านจริง)

**Present**
- [ ] ตัวเลขค่าใช้จ่ายและ assumption ชัดเจน
- [ ] มีทางเลือกและเหตุผลที่แนะนำ
- [ ] demo ซ้อมแล้ว มีแผนสำรองถ้า demo ล้ม (วิดีโอบันทึกไว้)

---

## 10. โครงสร้าง Repository ของ Capstone

```
thaitech-capstone/
├── README.md                 ← สรุป 1 หน้า + diagram + ลิงก์ทุกส่วน + วิธีรัน lab
├── 01-requirements/          requirements.md, assumptions.md, traceability.csv
├── 02-hld/                   hld.md, diagrams/ (drawio/png), adr/ADR-001...md
├── 03-lld/                   ip-plan (export จาก NetBox), vlan.md, routing.md, policy-matrix.csv, qos.md, wifi.md, aaa.md, services.md
├── 04-lab/                   topology.clab.yml, configs/, scripts/
├── 05-automation/            netbox/ (seed data), templates/, playbooks/ or nornir/, tests/batfish/, .github/workflows/
├── 06-monitoring/            prometheus/, grafana-dashboards/*.json, alerts.yml
├── 07-security/              suricata/, siem-usecases.md, ir-playbooks/
├── 08-ha-dr/                 test-plan.md, results.md (+ screenshots/pcap)
├── 09-bom-tco/               bom.xlsx/csv, tco.xlsx, options-comparison.md
└── 10-presentation/          exec-deck.pdf, tech-deck.pdf, demo-video-link.md
```

---

## 11. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| Capstone = lab ที่ทำงานได้ | ต้องมี requirement, design, เหตุผล, ทดสอบ, ปฏิบัติการ และการนำเสนอ |
| ต้องใช้อุปกรณ์จริงราคาแพง | lab เสมือน + ข้อมูลสมมติที่สมเหตุสมผลเพียงพอ |
| ยิ่งใส่เทคโนโลยีมากยิ่งดี | ใส่เท่าที่ตอบ requirement — อธิบายได้ว่าทำไม |
| นำเสนอเหมือนกันทั้งผู้บริหารและทีมเทคนิค | ผู้บริหารต้องการผลกระทบ/ต้นทุน/ความเสี่ยง ทีมเทคนิคต้องการรายละเอียด/หลักฐาน |
| Failover "ควร" ทำงาน | ต้องมีตัวเลขจากการทดสอบจริง |

---

## 12. Cheat Sheet — Capstone Flow

```
1 Requirements (business/technical/constraints/assumptions, วัดได้, MoSCoW)
2 HLD (topology, zones, ADR) → 3 LLD (IP v4/v6, VLAN, routing, policy matrix, QoS, AAA, services, Wi-Fi)
4 Lab (containerlab: HQ + 2 สาขา + ISP จำลอง + AWS) → 5 Automation (NetBox → Jinja → CI Batfish → deploy → drift)
6 Monitoring (Prometheus/Grafana, 10 alerts + runbook) → 7 Security (FW, NAC, IDS, SIEM, IR, self-pentest ใน lab)
8 HA/DR test 10 กรณี (คาดหวัง vs จริง) → 9 BOM + TCO 5 ปี (≥2 ทางเลือก) → 10 Present (exec + tech + demo)
Checklist: SPOF · deploy ซ้ำได้ · policy test อัตโนมัติ · failover วินาที · คนใหม่ troubleshoot ได้ใน 1 วัน
```

---

## 13. แบบทดสอบสุดท้าย (Self-Review 10 ข้อ)

1. ทุก single point of failure ถูกระบุและมีแผนรองรับแล้วหรือยัง ยกตัวอย่าง SPOF ที่มักหลงเหลือ
2. Policy matrix ของคุณทดสอบอัตโนมัติได้ครบหรือไม่ ใช้วิธีใด
3. ทุก config อยู่ใน Git และ deploy ซ้ำได้หรือไม่ พิสูจน์อย่างไร
4. ถ้าลิงก์ ISP หลักขาด ผู้ใช้สังเกตเห็นภายในกี่วินาที (จากการทดสอบ)
5. คนใหม่อ่านเอกสารแล้ว troubleshoot ได้ภายใน 1 วันหรือไม่ ทดสอบอย่างไร
6. IP plan ของคุณรองรับการเชื่อม AWS และการเติบโตอย่างไร
7. OT ถูกแยกจาก IT อย่างไร และ remote access ไป OT ทำอย่างไร
8. ทางเลือกใน TCO ต่างกันอย่างไร และทำไมจึงแนะนำทางเลือกนั้น
9. Alert ใดของคุณที่ไม่จำเป็นต้องปลุกคนกลางดึก และจัดการอย่างไร
10. ถ้าทำ capstone ใหม่ คุณจะเปลี่ยนอะไร (retrospective)

<details><summary><b>แนวคำตอบ/สิ่งที่ผู้ตรวจมองหา</b></summary>

1. ตรวจทุกชั้น (power, link, device, gateway, ISP, services, site, คน) — SPOF ที่มักหลง: DNS/DHCP/RADIUS ตัวเดียว, PDU เดียว, ISP สองเจ้าท่อเดียว, firewall HA ที่ config sync ผิดทั้งคู่, คนที่รู้ระบบคนเดียว, controller/management ตัวเดียว
2. Batfish (reachability/filter tests) ใน CI ทุก PR ครอบคลุมทุกคู่ zone ในตาราง + การทดสอบจริงด้วย nmap/curl จากแต่ละ zone ใน lab
3. ลบ lab แล้วสร้างใหม่จาก NetBox + Git + pipeline ได้ทั้งหมด และ drift check รายวันไม่พบความต่าง
4. ตัวเลขจาก ping/synthetic ต่อเนื่องระหว่างทดสอบ (เช่น HQ ≤ 3 วินาที, voice สาขา ≤ 1 วินาที) พร้อม log ยืนยัน
5. ให้เพื่อนที่ไม่เคยเห็นระบบใช้ runbook/diagram แก้โจทย์ที่จำลองไว้ แล้วจับเวลาและเก็บ feedback ปรับเอกสาร
6. ใช้ supernet แยก on-prem/AWS/remote ไม่ชนกัน summarize ได้ เหลือพื้นที่ต่อ site และ VPC สำหรับ 3–5 ปี
7. Zones/conduits: IT ↔ OT-DMZ ↔ OT ผ่าน firewall, ไม่มีการเชื่อมต่อตรงจาก IT/internet สู่ OT, remote access ผ่าน jump host ใน OT-DMZ + MFA + บันทึก session + อนุมัติตามเวลา
8. แสดงตัวเลขต่อปีและรวม 5 ปี พร้อมปัจจัยไม่ใช่ตัวเงิน (ทักษะทีม, ความเสี่ยง, compliance, ความยืดหยุ่น) และเหตุผลที่สอดคล้องกับ requirement
9. เช่น interface ผู้ใช้ down, WAN สาขาใช้สูงแต่ไม่กระทบ SLO — ลดเป็น warning/report ในเวลาทำการ, ใช้ dependency/dedup และทบทวน alert เป็นประจำ
10. คำตอบที่ดีสะท้อนบทเรียนจริง เช่น เริ่ม NetBox ก่อนเขียน config, ทดสอบ failover เร็วขึ้น, ลดความซับซ้อนบางส่วน, เขียน ADR ระหว่างทาง ไม่ใช่ตอนจบ
</details>

---

🎓 **จบ Level 100 — ยินดีด้วย!** ถ้าทำครบทุก Tier และ capstone นี้ คุณมีทั้งความรู้และ portfolio ระดับที่ใช้สมัครงาน Network/Cloud/Security Engineer ได้อย่างมั่นใจ
· กลับไปทำโปรเจคใน [10-expert-career.md](../10-expert-career.md) · ดูภาพรวมทั้งหมดที่ [README.md](../README.md)
