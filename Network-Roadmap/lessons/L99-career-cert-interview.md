# บทเรียน Level 99 — Career Path, Certifications & Interview (ฉบับละเอียด)

> อ่านจบแล้วจะ: เห็นเส้นทางอาชีพสาย network และสายที่แยกออกไป · รู้ว่าแต่ละระดับถูกคาดหวังอะไร · เลือก certification ให้ตรงเป้าหมาย (ไม่สะสมเกินจำเป็น) · สร้าง portfolio จาก roadmap นี้ · เขียน CV/LinkedIn · เตรียมสัมภาษณ์ (technical, troubleshooting, scenario, behavioral/STAR) · ตอบคำถามยอดฮิตได้อย่างมีโครงสร้าง · วางแผนพัฒนาตัวเองระยะยาว

---

## 1. เส้นทางอาชีพ

```
 Helpdesk / IT Support ─► NOC Engineer ─► Network Administrator ─► Network Engineer ─► Senior Network Engineer
                                                                                         │
           ┌──────────────────────┬──────────────────────┬────────────────────┬──────────┴──────────┐
     Network Architect     Network Security Eng.   Cloud Network Eng.   Network Automation/   Pre-sales / Solution
     (design, strategy)    (firewall, SASE, SOC)   (AWS/Azure/GCP)      NetDevOps / SRE       Architect (SI/vendor)
           │                                                                                    │
     Principal / Head of Infrastructure / CTO track                          Technical Account Manager, Consultant
```

| ระดับ | ถูกคาดหวังให้ | Tier ใน roadmap นี้ |
|---|---|---|
| **Helpdesk/NOC** | แก้ปัญหาพื้นฐาน ทำตาม runbook, monitoring, escalate ให้ถูก | 1–3 |
| **Network Admin** | ดูแลระบบที่มี: VLAN, Wi-Fi, firewall rule, VPN user, backup config | 2–5 |
| **Network Engineer** | ออกแบบ/ติดตั้งส่วนย่อย, routing/WAN/security, troubleshoot ข้ามชั้น, ทำ change ที่ซับซ้อน | 4–8 |
| **Senior** | รับผิดชอบระบบทั้งหมด, design, mentor, automation, คุยกับ vendor/ธุรกิจ, incident lead | 6–10 |
| **Architect** | กลยุทธ์ 3–5 ปี, สถาปัตยกรรมทั้งองค์กร, business case, governance | 9–10 |

### ประเภทนายจ้าง (ในบริบทไทย)

| ประเภท | ลักษณะงาน | ข้อดี/ข้อควรรู้ |
|---|---|---|
| **องค์กร (end-user)** — ธนาคาร, โรงพยาบาล, โรงงาน, ค้าปลีก | ดูแลเครือข่ายขององค์กรเดียวลึก ๆ | งานต่อเนื่อง, เห็นผลระยะยาว, compliance เข้ม (ธนาคาร) |
| **System Integrator (SI)** | ติดตั้ง/ออกแบบให้ลูกค้าหลายราย, โปรเจคหลายยี่ห้อ (ดู SI-Track / ISC-Track ใน repo นี้) | เรียนรู้เร็วมาก หลากหลาย, งานเร่ง/เดินทาง, ต้องสอบ cert ตาม partner |
| **ISP/Telco/Data center provider** | MPLS/SR, BGP ขนาดใหญ่, DC | สเกลใหญ่, เทคโนโลยี SP |
| **Vendor/Distributor** | pre-sales, TAC, consulting | รู้ผลิตภัณฑ์ลึก, ทักษะนำเสนอ |
| **Cloud/Tech company, MSP/MSSP** | cloud networking, automation, NOC/SOC 24×7 | DevOps culture, กะ (MSP) |

---

## 2. ทักษะที่ตลาดต้องการ (นอกจาก routing/switching)

| ทักษะ | ทำไม |
|---|---|
| **Security** (NGFW, SASE/ZTNA, NAC) | แทบทุกงาน network มี security ปน (Tier 7) |
| **Cloud networking** (AWS/Azure) | hybrid เป็นมาตรฐาน (Tier 8) |
| **Automation** (Python, Ansible, Git, API) | ทำงานในขนาดใหญ่ได้ — ตัวแยกระหว่าง engineer ทั่วไปกับคนที่ถูกจ้างเงินเดือนสูง (Tier 9) |
| **Wireless** | ทุกองค์กรต้องใช้ ผู้เชี่ยวชาญจริงหายาก (Tier 5) |
| **Troubleshooting อย่างเป็นระบบ** | ทักษะที่ถูกทดสอบในทุกสัมภาษณ์ (L30/L91) |
| **การสื่อสาร/เขียนเอกสาร/ภาษาอังกฤษ** | เอกสาร vendor, TAC, ลูกค้าต่างชาติ, ทำงานกับทีมอื่น (L92/L95) |
| **ความเข้าใจธุรกิจ/ต้นทุน** | ระดับ senior ขึ้นไป (L94) |

---

## 3. Certifications — เลือกให้ตรงเป้าหมาย

### ระดับเริ่มต้น

| Cert | เหมาะกับ |
|---|---|
| **CompTIA Network+** | พื้นฐานแบบไม่ผูกยี่ห้อ |
| **Cisco CCNA** ⭐ | มาตรฐานอุตสาหกรรมสำหรับ network engineer ระดับเริ่มต้น — HR รู้จักมากที่สุด |
| Juniper JNCIA-Junos | งานที่ใช้ Juniper/SP |
| Fortinet FCA/FCF (NSE 1–3 เดิม) | พื้นฐาน security ของ Fortinet (ฟรีบางส่วน) |
| AWS Cloud Practitioner / Azure Fundamentals (AZ-900) | พื้นฐาน cloud |

### ระดับกลาง (เลือกตามสายที่จะไป)

| สาย | Cert |
|---|---|
| Enterprise | **CCNP Enterprise** (ENCOR + concentration เช่น ENARSI, ENWLSI wireless), Aruba ACP/ACMP, Juniper JNCIS/JNCIP-ENT |
| Security | **Fortinet FCP/FCSS** (ซึ่งแทนชื่อ NSE 4–7 เดิม), **Palo Alto PCNSE**, Check Point CCSA/CCSE, CCNP Security |
| Cloud | **AWS Certified Advanced Networking – Specialty**, Azure **AZ-700** (Network Engineer Associate), Google Professional Cloud Network Engineer |
| Automation | **Cisco CCNP Automation** (เดิมชื่อ DevNet Professional), Red Hat Ansible (EX374/EX457) |
| Data center | CCNP Data Center, Arista ACE, Juniper JNCIP-DC |
| SP | CCNP Service Provider, JNCIP-SP, Nokia SRC |
| Wireless | CWNA → CWSP/CWDP/CWAP (CWNE) |

### ระดับสูง
**CCIE** (Enterprise Infrastructure, Security, Data Center, SP, Enterprise Wireless, Automation), **JNCIE**, **CCDE** (design), Fortinet FCX — ต้องใช้ประสบการณ์จริงหลายปี + lab ภาคปฏิบัติ

> ⚠️ ชื่อและรูปแบบ certification เปลี่ยนบ่อย (เช่น Cisco เปลี่ยนชื่อสาย DevNet, Fortinet ปรับ NSE เป็น FCA/FCP/FCSS/FCX) — **ตรวจเว็บไซต์ทางการก่อนวางแผนสอบเสมอ**

### หลักการเลือก
1. **ดูประกาศรับสมัครงานที่อยากได้ 20 ประกาศ** → นับว่า cert ไหนถูกขอบ่อย
2. **1 cert = 1 ทักษะที่ใช้ได้จริง** — สอบแล้วต้องลงมือทำ lab/โปรเจคในหัวข้อนั้น
3. ลำดับที่ใช้ได้กับคนส่วนใหญ่: **CCNA → (security หรือ cloud หรือ CCNP ตามสาย) → automation**
4. งาน SI: partner มักต้องการพนักงานที่มี cert ของยี่ห้อที่ขาย — บริษัทมักออกค่าสอบให้
5. Cert ช่วยผ่าน HR filter — **portfolio และการสัมภาษณ์เป็นตัวตัดสิน**

### วิธีเตรียมสอบ (ตัวอย่าง CCNA 3–4 เดือน)
```
 สัปดาห์ 1–8  : เรียนตาม blueprint ทางการ + lab ทุกหัวข้อ (Packet Tracer/CML/containerlab) — ใช้ Tier 1–4 ของ roadmap นี้
 สัปดาห์ 9–12 : subnetting ทุกวัน (L9/L10), ทำข้อสอบฝึก, จดหัวข้อที่อ่อน → กลับไปทำ lab
 สัปดาห์ 13–14: ทบทวน + ข้อสอบจำลองเต็มเวลา → นัดสอบ
 ห้ามใช้ "dumps" (ข้อสอบรั่ว) — ผิดเงื่อนไขการสอบ อาจถูกเพิกถอน cert และไม่ได้ความรู้จริง
```

---

## 4. Portfolio — หลักฐานว่าทำได้จริง

roadmap นี้มี **5 โปรเจคต่อ Level × 100 Level** → คัด **15–20 โปรเจคเด่น** ที่แสดงทักษะหลากหลาย
### GitHub Portfolio ที่ดี
```
 network-portfolio/
 ├── README.md                       ← หน้าแรก: แนะนำตัว, ทักษะ, ลิงก์ไปแต่ละโปรเจค (พร้อมภาพ diagram)
 ├── 01-campus-network-design/       ← L40: HLD/LLD + diagram + config + ผลทดสอบ
 ├── 02-ospf-bgp-lab/                ← containerlab topology + config + การทดสอบ failover
 ├── 03-firewall-policy-as-code/     ← Batfish tests ใน GitHub Actions
 ├── 04-netbox-ansible-automation/   ← SoT → render → deploy
 ├── 05-monitoring-stack/            ← Prometheus + Grafana dashboard (screenshot)
 ├── 06-aws-hybrid-vpn-terraform/    ← Terraform + diagram
 └── 07-troubleshooting-writeups/    ← "ปัญหา → วิธีคิด → หลักฐาน → วิธีแก้"
```
**README ของแต่ละโปรเจค:** ปัญหา/เป้าหมาย → diagram → สิ่งที่ทำ (เทคโนโลยี) → วิธีทดสอบ + ผล → สิ่งที่เรียนรู้ → วิธีรันซ้ำ
⚠️ **ห้ามใส่ข้อมูลจริงของนายจ้าง/ลูกค้า** (IP จริง, config, ชื่อลูกค้า, รหัสผ่าน) — ใช้ lab และข้อมูลสมมติเท่านั้น

### Homelab
ไม่จำเป็นต้องแพง: PC/mini PC ที่มี RAM 32–64 GB + Proxmox + containerlab/EVE-NG/GNS3 + switch managed มือสอง + AP — เพียงพอสำหรับ lab เกือบทั้งหมดใน roadmap

### Blog/การสอน
เขียนบทความจาก lab ที่ทำ (ภาษาไทยก็มีคนอ่านมาก) → "สอนคนอื่น = เข้าใจจริง" + ทำให้ผู้สัมภาษณ์เห็นวิธีคิดและการสื่อสาร

---

## 5. CV และ LinkedIn

### CV สาย network ที่ดี
- **1–2 หน้า** ภาษาอังกฤษ (หรือทั้งสองภาษาตามที่บริษัทต้องการ)
- **Summary 2–3 บรรทัด:** "Network engineer with 3 years in enterprise campus and SD-WAN; automating config with Ansible; CCNA, Fortinet FCP."
- **ประสบการณ์ = ผลลัพธ์ที่วัดได้** ไม่ใช่หน้าที่

| ❌ หน้าที่ | ✅ ผลลัพธ์ |
|---|---|
| "ดูแล switch และ firewall" | "Migrated 12 branches from MPLS to SD-WAN, cutting WAN cost 35% with zero unplanned downtime" |
| "ทำ backup config" | "Automated nightly config backup for 300 devices with Python/Git, reducing restore time from hours to minutes" |
| "แก้ปัญหา network" | "Resolved recurring VPN outage (MTU black hole) affecting 200 remote users; root-caused with multi-point capture" |

- **Skills** จัดกลุ่ม: Routing & Switching / Security / Wireless / Cloud / Automation / Tools
- **Projects/Portfolio link** (GitHub)
- **Certifications** พร้อมปี
- ข้อมูลส่วนตัวเท่าที่จำเป็น

### LinkedIn
headline ชัด ("Network Engineer | SD-WAN • Fortinet • Automation"), ลิงก์ portfolio, โพสต์สิ่งที่เรียนรู้/โปรเจค เป็นระยะ, เชื่อมต่อกับคนในวงการและ recruiter

---

## 6. การสัมภาษณ์ — รูปแบบที่พบบ่อย

| รอบ | สิ่งที่ประเมิน |
|---|---|
| HR screen | ความสนใจ, เงินเดือน, ภาษา, ความพร้อม |
| **Technical (Q&A)** | ความรู้พื้นฐานถึงลึก |
| **Practical/Lab** | ทำ config/แก้ปัญหาใน lab, subnetting บนกระดาน, อ่าน output |
| **Scenario/Design** | "ออกแบบเครือข่ายสาขาใหม่ 50 คน", "ถ้า X ล่มคุณจะทำอะไร" |
| **Behavioral** | การทำงานร่วมกับคนอื่น, การรับมือแรงกดดัน, ความผิดพลาดที่เคยทำ |
| Manager/culture | ความเหมาะสมกับทีม, เป้าหมายอาชีพ |

### วิธีตอบคำถามเทคนิคให้ดี
1. **ตอบแก่นก่อน แล้วค่อยลงรายละเอียด** (ระดับ CCNA → CCNP ตามที่ผู้ถามสนใจ)
2. **ยกตัวอย่างจากประสบการณ์/lab** ("ใน lab ของผมเคยเจอ…")
3. **ไม่รู้ ให้บอกว่าไม่รู้ แล้วอธิบายว่าจะหาคำตอบอย่างไร** — ดีกว่าเดา (ผู้สัมภาษณ์มักรู้ว่าเดา)
4. **คิดดัง ๆ** ในโจทย์ troubleshooting — เขาประเมิน "วิธีคิด" มากกว่าคำตอบ

---

## 7. คำถามสัมภาษณ์ยอดฮิต + แนวคำตอบ

### "พิมพ์ www.example.com ใน browser แล้วเกิดอะไรขึ้น" ⭐ (คำถามที่แยกระดับได้ดีมาก)
```
 1. Browser ตรวจ cache/HSTS → OS resolver ตรวจ cache/hosts
 2. DNS: ถาม DNS server (UDP/TCP 53 หรือ DoH) → recursive → root → .com → authoritative → ได้ A/AAAA (L16)
 3. ปลายทางอยู่นอก subnet → ส่งไป default gateway → ARP หา MAC ของ gateway (L11)
 4. TCP 3-way handshake ไป port 443 (หรือ QUIC/UDP 443 สำหรับ HTTP/3) (L13/20)
 5. TLS handshake: ClientHello (SNI) → ServerHello + certificate → ตรวจ chain/ชื่อ/วันหมดอายุ → key exchange (L20/65)
 6. ระหว่างทาง: switch (MAC table), router (routing table, longest match), NAT (PAT ที่ edge), firewall (stateful/policy/IPS), อาจผ่าน proxy/CDN/LB (L71/72)
 7. HTTP GET → server/LB → response → browser render → โหลด resource อื่น (หลาย connection/HTTP2 multiplexing)
```
ยิ่งลงรายละเอียดถูกต้องในแต่ละชั้นได้มาก ยิ่งแสดงระดับความรู้

### คำถามพื้นฐานที่ต้องตอบได้คล่อง

| คำถาม | ประเด็นสำคัญ (บทที่ทบทวน) |
|---|---|
| OSI 7 layers + ตัวอย่างแต่ละชั้น | L2 |
| TCP vs UDP + ตัวอย่าง | L13/L14 |
| Subnetting เช่น "10.20.30.77/27 อยู่ subnet ไหน, broadcast, host range" | L9/L10 (ต้องคิดได้ในหัวภายใน 30 วินาที) |
| VLAN vs subnet, trunk, native VLAN | L32/L33 |
| STP ทำไมต้องมี, root election, PortFast/BPDU Guard | L35/L36 |
| OSPF neighbor ไม่ขึ้น ตรวจอะไร (area, hello/dead, subnet, MTU, auth, network type) | L45/46 |
| BGP best path selection (weight, local pref, AS path, origin, MED, eBGP>iBGP, IGP metric, router ID) | L49 |
| NAT/PAT ทำงานอย่างไร | L17 |
| DHCP DORA, DHCP relay | L15 |
| Stateful vs stateless firewall | L62 |
| IPsec phase 1/2, ทำไม tunnel ขึ้นแต่ traffic ไม่ผ่าน | L58 |
| HSRP/VRRP | L50 |
| QoS: ทำไมเสียงต้องใช้ EF, queuing | L54 |
| Wi-Fi: 2.4 vs 5 vs 6 GHz, channel planning, WPA3 | L51–52 |

### Troubleshooting scenario: "ผู้ใช้แจ้งว่าเน็ตช้า"
```
 1. ถามให้ชัด: ใคร (คนเดียว/ทั้งแผนก/ทั้งสาขา), แอปไหน (ทุกเว็บ/เฉพาะ ERP), เมื่อไร (ตลอด/บางเวลา), เริ่มเมื่อไร, มีอะไรเปลี่ยน
 2. ขอบเขต → ถ้าคนเดียว: เครื่อง/Wi-Fi/พอร์ต · ทั้งสาขา: WAN/ISP/firewall
 3. วัด: ping/mtr ไป gateway → ไป DNS → ไปปลายทาง (latency/loss แยกช่วง), speedtest, DNS response time
 4. ดู monitoring: utilization ลิงก์ (95th), errors/discards, CPU firewall, Wi-Fi channel utilization
 5. flow analysis: ใครกิน bandwidth
 6. สมมติฐาน → ทดสอบ → แก้ → ยืนยันกับผู้ใช้ → บันทึก/ป้องกัน
```
(โครงสร้างจาก L30/L91 — ผู้สัมภาษณ์ต้องการเห็น "วิธีคิดเป็นระบบ")

### Behavioral — ตอบด้วย STAR

| | |
|---|---|
| **S**ituation | บริบท |
| **T**ask | หน้าที่ของคุณ |
| **A**ction | สิ่งที่ **คุณ** ทำ (ไม่ใช่ "เรา") |
| **R**esult | ผลลัพธ์ (ตัวเลขถ้าได้) + **สิ่งที่เรียนรู้** |

ตัวอย่าง "เล่าความผิดพลาดที่เคยทำ":
> S: ผมเพิ่ม VLAN บน trunk ของ core ในช่วงกลางวัน · T: ต้องเพิ่ม VLAN ใหม่ให้ทีม CCTV · A: ผมพิมพ์ `switchport trunk allowed vlan 50` แทน `add 50` ทำให้ VLAN อื่นบน uplink หาย ชั้น 3 หลุด 4 นาที — ผมรู้ตัวจาก alert ทันที แก้กลับด้วย config จาก backup แล้วแจ้งหัวหน้าและ helpdesk ทันที · R: บริการกลับมาภายใน 4 นาที ผมเสนอให้ทีมใช้ template + `--check --diff` ใน Ansible สำหรับการแก้ trunk และทำ change ใน window — หลังจากนั้นไม่เกิดซ้ำ
(ซื่อสัตย์ + แสดงความรับผิดชอบ + แก้ที่ระบบ — Level 95)

### คำถามที่ควรถามกลับผู้สัมภาษณ์
- "ทีมดูแลอุปกรณ์กี่ตัว/กี่ site ใช้ยี่ห้ออะไรเป็นหลัก?"
- "งาน on-call เป็นอย่างไร?"
- "ทีมใช้ automation/Git อยู่ระดับไหน?"
- "การเรียนรู้/สอบ cert บริษัทสนับสนุนอย่างไร?"
- "90 วันแรก คุณคาดหวังอะไรจากตำแหน่งนี้?"

---

## 8. การเจรจาเงินเดือนและการเลือกงาน

- สำรวจช่วงเงินเดือนของตำแหน่ง/ประสบการณ์/cert จากหลายแหล่ง (รายงานเงินเดือนของบริษัทจัดหางาน, คนในวงการ)
- พิจารณา **ทั้งแพ็กเกจ**: เงินเดือน, ค่าโทรศัพท์/เดินทาง, ค่า on-call/OT, ค่าสอบ cert/training, ประกัน, โบนัส, WFH
- **โอกาสเรียนรู้** ในช่วงต้นอาชีพมีค่ามาก (งาน SI ช่วง 2–3 ปีแรกให้ประสบการณ์หลากหลายเร็วมาก)

---

## 9. แผนพัฒนาตัวเองระยะยาว

```
 ปีที่ 0–1 : Tier 1–4 + CCNA + homelab + portfolio 5 โปรเจค → งาน Helpdesk/NOC/Junior
 ปีที่ 1–3 : Tier 5–7 + cert สายที่เลือก (security/wireless/CCNP) + Python/Ansible พื้นฐาน → Network Engineer
 ปีที่ 3–5 : Tier 8–9 + cloud networking + automation จริงในงาน + นำโปรเจค → Senior
 ปีที่ 5+  : Tier 10 + design/architecture + business skills + mentor คนอื่น (+ CCIE/CCDE ถ้าต้องการ) → Architect/Lead
```
**นิสัยที่ทำให้เติบโต:**
- lab สัปดาห์ละไม่กี่ชั่วโมงอย่างสม่ำเสมอ ดีกว่าหักโหมเป็นครั้งคราว
- อ่าน **release notes/security advisories** ของอุปกรณ์ที่ดูแล, RFC สำคัญ, blog ของผู้เชี่ยวชาญ, post-mortem สาธารณะ (Cloudflare, AWS, Meta ฯลฯ)
- เข้าร่วมชุมชน (กลุ่ม network ในไทย, งาน meetup/สัมมนาของผู้ผลิต, NOG ระดับภูมิภาค เช่น APNIC/APRICOT)
- **สอนและแบ่งปัน** — เขียน blog, ช่วยตอบคำถาม
- ดูแลสุขภาพ: งาน on-call และ maintenance กลางคืนต้องมีการพักผ่อนที่ดี

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| ยิ่งมี cert มากยิ่งได้งาน | cert ผ่าน HR — portfolio/ทักษะจริง/สัมภาษณ์ตัดสิน |
| ไม่มีประสบการณ์ทำงาน = ไม่มีอะไรจะโชว์ | homelab + portfolio + blog คือประสบการณ์ที่พิสูจน์ได้ |
| ตอบไม่รู้ = ตกสัมภาษณ์ | ตอบตรงและบอกวิธีหาคำตอบ ดีกว่าเดาผิด |
| Network engineer ไม่ต้องเขียนโค้ด | automation เป็นทักษะที่ตลาดต้องการสูง |
| Soft skills ไม่สำคัญในงานเทคนิค | การสื่อสาร/เอกสาร/ทำงานกับทีมเป็นตัวกำหนดการเติบโต |

---

## 11. Cheat Sheet

```
เส้นทาง: Helpdesk → NOC → Admin → Engineer → Senior → Architect | แยก Security/Cloud/Automation/Pre-sales
นายจ้าง: องค์กร · SI · ISP/Telco/DC · Vendor · Cloud/MSP
Cert: CCNA ⭐ → ตามสาย (CCNP/Fortinet FCP-FCSS/PCNSE/AWS ANS/AZ-700/Automation) → CCIE/JNCIE/CCDE
เลือกจากประกาศงานจริง · 1 cert = 1 ทักษะที่ใช้ได้ · ตรวจชื่อ cert ล่าสุดที่เว็บทางการ · ห้าม dumps
Portfolio: 15-20 โปรเจค + README (ปัญหา, diagram, ทำอะไร, ทดสอบ, เรียนรู้) · ไม่มีข้อมูลจริงของนายจ้าง
CV: ผลลัพธ์ที่วัดได้ ไม่ใช่หน้าที่
สัมภาษณ์: แก่นก่อนรายละเอียด · ยกตัวอย่าง · ไม่รู้บอกไม่รู้ · คิดดัง ๆ
"พิมพ์ URL แล้วเกิดอะไร" · subnetting 30 วินาที · OSPF/BGP/STP/NAT/IPsec · troubleshooting เป็นระบบ
Behavioral = STAR (+ สิ่งที่เรียนรู้) · ถามกลับ
```

---

## 12. แบบทดสอบ 10 ข้อ (คำถามสัมภาษณ์จริง)

1. อธิบาย TCP vs UDP พร้อมตัวอย่างแอปที่ใช้
2. ผู้ใช้บอก "เน็ตช้า" คุณจะทำอะไรบ้าง
3. เล่าประสบการณ์ที่เคยทำ change แล้วเกิดปัญหา (ใช้ STAR)
4. VLAN กับ subnet ต่างกันอย่างไร
5. 172.16.45.200/26 อยู่ใน subnet ใด broadcast คืออะไร
6. OSPF neighbor ค้างที่ EXSTART/EXCHANGE สาเหตุที่พบบ่อยคืออะไร
7. อธิบายสั้น ๆ ว่าเกิดอะไรขึ้นเมื่อพิมพ์ URL ใน browser
8. ทำไมควรจ้างคุณแทนผู้สมัครที่มี cert มากกว่า
9. เขียน bullet ใน CV ใหม่จาก "ดูแล firewall ของบริษัท" ให้เป็นผลลัพธ์
10. คุณจะเลือก certification ถัดไปอย่างไร

<details><summary><b>แนวคำตอบ</b></summary>

1. TCP: connection-oriented, reliable, เรียงลำดับ, flow/congestion control (web/HTTPS, SSH, email, DB); UDP: ไม่มี connection ไม่ retransmit เร็ว overhead ต่ำ (DNS, VoIP/RTP, streaming, DHCP, QUIC ที่ทำ reliability เอง)
2. ถามขอบเขต (ใคร/แอปไหน/เมื่อไร/อะไรเปลี่ยน) → วัด ping/mtr แยกช่วง gateway/DNS/ปลายทาง, speedtest, DNS time → ดู monitoring (utilization, errors, firewall CPU, Wi-Fi) → flow หาผู้ใช้ bandwidth → สมมติฐานและทดสอบ → แก้และยืนยัน → บันทึก/ป้องกัน
3. ใช้โครงสร้าง Situation/Task/Action/Result และปิดด้วยสิ่งที่เรียนรู้และการแก้ที่ระบบ (เช่น template, check mode, change window)
4. VLAN แบ่ง broadcast domain ที่ L2; subnet แบ่ง address ที่ L3 — ปกติจับคู่ 1 VLAN : 1 subnet และต้องใช้ router/L3 switch สื่อสารข้ามกัน
5. /26 ขนาดบล็อก 64 → 172.16.45.192/26, broadcast 172.16.45.255, host 193–254
6. MTU ไม่ตรงกันระหว่างสองฝั่ง (DBD ใหญ่เกิน), router-ID ซ้ำ, ปัญหา unicast/ACL
7. DNS resolve → ARP หา gateway → TCP (หรือ QUIC) handshake → TLS handshake (SNI, cert) → ผ่าน switch/router/NAT/firewall/LB → HTTP request/response → browser render
8. ยกหลักฐานทักษะจริง: portfolio/โปรเจค, ตัวอย่างการแก้ปัญหาอย่างเป็นระบบ, automation, การสื่อสารและความรับผิดชอบ, ความพร้อมเรียนรู้ — เชื่อมโยงกับสิ่งที่ตำแหน่งต้องการ
9. เช่น "Managed HA FortiGate pair for 800 users; redesigned 400+ legacy rules into zone-based policy, removing 35% unused rules and passing ISO 27001 audit with no findings"
10. ดูประกาศงานเป้าหมายว่าขอ cert อะไรบ่อย, เลือกให้ตรงกับสายที่จะไปและเทคโนโลยีที่ใช้ในงาน, ตรวจชื่อ/รูปแบบล่าสุดที่เว็บทางการ, วางแผนพร้อม lab/โปรเจคในหัวข้อนั้น
</details>

---

➡️ ต่อไป: **Level 100 — Final Capstone: Enterprise Network End-to-End**
