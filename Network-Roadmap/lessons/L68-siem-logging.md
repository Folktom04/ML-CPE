# บทเรียน Level 68 — Logging, SIEM & Visibility (ฉบับละเอียด)

> อ่านจบแล้วจะ: รู้ว่าต้องเก็บ log อะไรบ้างและเก็บนานเท่าไร · เข้าใจสถาปัตยกรรม SIEM (collect → parse → normalize → enrich → correlate → alert) · เขียน use case และ correlation rule · ตรวจจับ brute force, impossible travel, DNS tunneling, beaconing · คำนวณ EPS/storage · ใช้ threat intelligence

---

## 1. ทำไมต้องรวบรวม Log

| เหตุผล | ตัวอย่าง |
|---|---|
| **ตรวจจับภัย** | VPN login ล้มเหลว 500 ครั้งจาก IP ต่างประเทศ |
| **สืบสวนเหตุการณ์ (forensics)** | ใครเข้าถึง server นี้ก่อนข้อมูลรั่ว? |
| **แก้ปัญหา (troubleshooting)** | interface flap เมื่อไร สัมพันธ์กับอะไร |
| **Compliance/กฎหมาย** | **พ.ร.บ.คอมพิวเตอร์ฯ เก็บข้อมูลจราจร ≥ 90 วัน**, ISO 27001, PCI DSS (≥ 1 ปี, 3 เดือนค้นได้ทันที) |
| **Audit** | ใครแก้ config firewall (TACACS+ accounting) |

> 🔑 **Log ที่ไม่ได้ถูกเก็บไว้ ไม่มีวันสืบย้อนได้** — ผู้โจมตีมักอยู่ในระบบนานหลายสัปดาห์ก่อนถูกพบ ต้องมี log ย้อนหลังพอ

---

## 2. แหล่ง Log ที่สำคัญ (เรียงตามคุณค่า)

| แหล่ง | ได้ข้อมูลอะไร |
|---|---|
| **Firewall / NGFW** | การเชื่อมต่อที่ allow/deny, แอป, ผู้ใช้, IPS/AV/URL event, NAT (ต้องมีเพื่อหาผู้ใช้จาก public IP) |
| **VPN / Remote access** | ใคร login จากที่ไหน เมื่อไร สำเร็จ/ล้มเหลว |
| **Identity: Active Directory / Entra ID / IdP** | login (4624/4625), account lockout (4740), เพิ่มสมาชิกกลุ่ม admin (4728/4732/4756), สร้างบัญชี, Kerberos ผิดปกติ |
| **EDR / Antivirus** | process, การตรวจพบมัลแวร์ |
| **DNS (query log)** | เครื่องไหนถามชื่ออะไร — หา C2, phishing domain, DNS tunneling |
| **Proxy / Secure Web Gateway** | URL ที่เข้าถึง, ไฟล์ที่ดาวน์โหลด |
| **Email security** | phishing, attachment อันตราย |
| **DHCP** | IP ↔ MAC ↔ hostname ณ เวลาหนึ่ง (จำเป็นต่อการหาว่า IP นั้นคือเครื่องใคร) |
| **Network devices** (syslog) | login, config change, interface/routing event |
| **NetFlow/IPFIX, Zeek, NDR** | ใครคุยกับใคร ปริมาณเท่าไร (ไม่ต้องมี payload) |
| **Cloud (AWS CloudTrail, Azure Activity, M365 audit)** | การเปลี่ยนแปลงใน cloud, การเข้าถึงข้อมูล |
| Server/application/database | การเข้าถึงข้อมูล, error |

---

## 3. SIEM คืออะไร

**SIEM (Security Information and Event Management)** = ระบบ **รวม log จากทุกแหล่ง → ทำให้อยู่ในรูปแบบเดียวกัน → วิเคราะห์ความสัมพันธ์ข้ามแหล่ง → แจ้งเตือน → สืบสวน → รายงาน**

### สถาปัตยกรรม (Pipeline)
```
 ① Collect   : syslog (UDP/TCP/TLS), agent (Winlogbeat, Wazuh agent, AMA), API (cloud/SaaS)
 ② Parse     : แยก field จากข้อความดิบ
 ③ Normalize : ใช้ชื่อ field มาตรฐานเดียวกัน (src_ip, dst_ip, user, action) — ข้ามยี่ห้อได้
               (schema เช่น ECS ของ Elastic, ASIM ของ Sentinel, CIM ของ Splunk, OCSF)
 ④ Enrich    : เพิ่มข้อมูล: geo-IP, ASN, threat intel, ชื่อผู้ใช้จาก DHCP/AD, ความสำคัญของ asset
 ⑤ Store     : hot (ค้นเร็ว) → warm → cold/archive (ถูก เก็บตามกฎหมาย)
 ⑥ Correlate : rule/analytics/ML จับรูปแบบข้ามเหตุการณ์และแหล่ง
 ⑦ Alert → Case → Investigate → Respond (ร่วมกับ SOAR)
 ⑧ Dashboard / Report / Compliance
```

### ผลิตภัณฑ์
| ประเภท | ตัวอย่าง |
|---|---|
| Commercial | **Splunk**, **IBM QRadar**, **Microsoft Sentinel** (cloud), **Google SecOps**, **FortiSIEM**, Elastic Security, Exabeam, LogRhythm |
| Open source | **Wazuh** (SIEM + XDR agent), **Elastic/OpenSearch**, Graylog, Security Onion |
| Log management (ไม่ใช่ SIEM เต็มรูปแบบ) | Graylog, Loki, rsyslog ไปยัง storage |

---

## 4. Use Case และ Correlation Rule

**Use case** = สถานการณ์ภัยที่ต้องการตรวจจับ + log ที่ต้องใช้ + เงื่อนไข + การตอบสนอง

| Use Case | Logic (ตัวอย่าง) | Log ที่ต้องใช้ |
|---|---|---|
| **Brute force VPN/SSH** | login ล้มเหลว ≥ 20 ครั้งใน 5 นาทีจาก IP เดียว | VPN/firewall/server |
| **Password spraying** | IP เดียว login ล้มเหลวกับ **หลายบัญชี** (ครั้งละไม่กี่ครั้ง) | AD/IdP/VPN |
| **Brute force สำเร็จ** | ล้มเหลวหลายครั้ง **ตามด้วยสำเร็จ** จาก IP เดียวกัน | VPN/AD |
| **Impossible travel** | บัญชีเดียว login จากกรุงเทพฯ แล้วอีก 10 นาทีจากยุโรป | VPN/IdP + geo-IP |
| **Admin group change** | มีการเพิ่มสมาชิก Domain Admins นอก change window | AD |
| **Traffic ไป IP/domain อันตราย** | ปลายทางตรงกับ threat intel | firewall/DNS/proxy + TI |
| **DNS tunneling** | query ยาวผิดปกติ/entropy สูง/subdomain จำนวนมากไปโดเมนเดียว/TXT จำนวนมาก | DNS |
| **Beaconing (C2)** | เครื่องติดต่อปลายทางเดิมเป็นช่วงเวลาสม่ำเสมอ (เช่น ทุก 60 วินาที ± jitter น้อย) | firewall/proxy/Zeek |
| **Data exfiltration** | ส่งข้อมูลออกปริมาณมากผิดปกติไปปลายทางใหม่ | firewall/flow |
| **Lateral movement** | เครื่องผู้ใช้เชื่อมต่อ SMB/RDP ไปหลายเครื่องผู้ใช้ | firewall ภายใน/flow/EDR |
| **Firewall config change** | มีการแก้ policy นอก change window/โดยบัญชีที่ไม่ใช่ทีม | firewall/TACACS+ |
| **Break-glass account used** | มีการ login ด้วยบัญชีฉุกเฉิน | network devices |
| **Log source หยุดส่ง** | แหล่ง log สำคัญเงียบเกิน X นาที | ทุกแหล่ง (ผู้โจมตีมักปิด log) |

**ตัวอย่าง rule (แนวคิด — ภาษาแต่ละ SIEM ต่างกัน)**
```
// KQL (Microsoft Sentinel) — VPN brute force ตามด้วยสำเร็จ
let failures = VPNLogs | where Result == "Failure" | summarize Fail=count() by SrcIP, bin(TimeGenerated, 10m) | where Fail >= 20;
VPNLogs | where Result == "Success" | join kind=inner failures on SrcIP
| project TimeGenerated, User, SrcIP, Fail
```
แนวคิดเดียวกันใช้ได้กับ SPL (Splunk), Wazuh rule (XML), Sigma (รูปแบบกลางที่แปลงเป็นภาษาของ SIEM ต่าง ๆ ได้)

**Map use case กับ MITRE ATT&CK** เพื่อดูว่ายังขาดการตรวจจับเทคนิคใด

---

## 5. Tuning และ Alert Quality

- เริ่มจาก **use case ที่มีผลกระทบสูงและ log พร้อม** (10–20 use case แรก) ไม่ใช่เปิดทุก rule
- วัด **false positive rate** ของแต่ละ rule → ปรับ threshold/whitelist (เช่น vulnerability scanner ของเราเอง)
- ทุก alert ควรมี **severity, คำอธิบาย, ขั้นตอนตรวจสอบ (playbook)**
- รวม alert ที่เกี่ยวข้องเป็น **incident เดียว** ลดภาระ analyst
- ทบทวน use case เป็นระยะ (ภัยเปลี่ยน ระบบเปลี่ยน)

---

## 6. Sizing SIEM

**EPS (Events Per Second)** และ **ปริมาณข้อมูลต่อวัน (GB/day)** เป็นตัวกำหนดค่า license และ storage
```
 ตัวอย่างประมาณการ
 Firewall 2 ตัว × 1,500 EPS  = 3,000 EPS
 AD/DC 4 ตัว × 300 EPS       = 1,200 EPS
 Server 200 × 5 EPS           = 1,000 EPS
 Network devices 150 × 2 EPS  =   300 EPS
 รวม ≈ 5,500 EPS (เผื่อ peak ×1.5–2)
 ขนาดเฉลี่ย ~500 byte/event → 5,500 × 500 × 86,400 ≈ 237 GB/วัน (ก่อนบีบอัด)
 เก็บ hot 30 วัน + cold รวม 365 วัน (คำนวณ storage ตามอัตราบีบอัดของผลิตภัณฑ์)
```
> 💡 กรอง log ที่ไม่มีคุณค่า (debug, allow ที่ซ้ำซ้อนมาก) ก่อนส่งเข้า SIEM ที่คิดเงินตามปริมาณ — แต่ระวังทิ้งสิ่งที่ต้องใช้ตามกฎหมาย (ส่งไป archive ราคาถูกแทน)

---

## 7. Threat Intelligence

- **IoC (Indicators of Compromise):** IP, domain, URL, file hash ที่ทราบว่าอันตราย
- แหล่ง: abuse.ch (URLhaus, ThreatFox, Feodo Tracker), AlienVault OTX, MISP communities, vendor feed (ThaiCERT/TB-CERT สำหรับไทย)
- มาตรฐาน: **STIX** (รูปแบบข้อมูล), **TAXII** (การแลกเปลี่ยน)
- ใช้: enrich log, ตรวจ match, block อัตโนมัติ (firewall EDL/threat feed)
- ⚠️ IoC หมดอายุเร็ว (IP เปลี่ยนเจ้าของ) — ใช้ feed ที่มีการอัปเดตและระบุอายุ

---

## 8. คุณภาพของ Log (มักถูกมองข้าม)

- **เวลาถูกต้องทุกแหล่ง (NTP)** และ timezone ชัดเจน (Level 55)
- **ระบุตัวตนได้:** hostname/IP ต้นทางคงที่ (loopback/management IP)
- **ครบ:** ตรวจว่าทุก log source ส่งมาจริง (dashboard "log source health" + alert เมื่อเงียบ)
- **ป้องกันการแก้ไข:** สิทธิ์เข้าถึง SIEM จำกัด, เก็บแบบ immutable/WORM สำหรับหลักฐาน
- **ความเป็นส่วนตัว (PDPA):** log มีข้อมูลส่วนบุคคล — กำหนดสิทธิ์, retention, วัตถุประสงค์

---

## 9. SOC และ SOAR (ภาพรวม)

- **SOC (Security Operations Center):** ทีมเฝ้าระวัง 24x7 — Tier 1 (triage), Tier 2 (investigate), Tier 3 (hunting/IR) — องค์กรที่ไม่มีทีมเองใช้ **MDR/MSSP**
- **SOAR (Security Orchestration, Automation and Response):** ทำงานซ้ำอัตโนมัติ เช่น alert → enrich IP → ถ้าอันตรายให้ block ที่ firewall + isolate เครื่องด้วย EDR + เปิด ticket
(รายละเอียด SI-Track L53–54)

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| เก็บ log ทุกอย่างไว้ก็พอ | ต้องมี use case/การวิเคราะห์ ไม่เช่นนั้นเป็นแค่ที่เก็บข้อมูล |
| ซื้อ SIEM แล้วตรวจจับได้ทันที | ต้อง onboard log, parse, เขียน/ปรับ use case ต่อเนื่อง |
| Log ของ firewall allow ไม่สำคัญ | สำคัญมากสำหรับการสืบสวน (ใครคุยกับใคร) |
| ไม่ต้องสนใจถ้า log source เงียบ | log หายอาจหมายถึงผู้โจมตีปิด log หรือ pipeline เสีย |
| Log ไม่เกี่ยวกับ PDPA | log มีข้อมูลส่วนบุคคล ต้องควบคุมการเข้าถึงและ retention |

---

## 11. Cheat Sheet

```
แหล่งสำคัญ: Firewall (+NAT) · VPN · AD/IdP · EDR · DNS · Proxy · Email · DHCP · Network devices · Flow · Cloud
กฎหมาย: พ.ร.บ.คอมฯ ≥ 90 วัน · PCI 1 ปี · ระวัง PDPA
SIEM: Collect → Parse → Normalize → Enrich → Store (hot/cold) → Correlate → Alert/Case
Use case: brute force (+สำเร็จ) · password spraying · impossible travel · admin group change
          · TI match · DNS tunneling · beaconing · exfiltration · lateral movement · log source silent
Sigma = rule กลาง · KQL (Sentinel) · SPL (Splunk) · Wazuh rule
EPS × ขนาด event × 86,400 = GB/วัน · hot/cold retention
TI: IoC (IP/domain/hash) · STIX/TAXII · abuse.ch/MISP/ThaiCERT
คุณภาพ log: NTP · source คงที่ · ครบ (health) · immutable · PDPA
SOC (Tier 1-3) / MDR · SOAR = อัตโนมัติ
```

---

## 12. แบบทดสอบ 10 ข้อ

1. เหตุผลในการรวบรวม log 4 ข้อ
2. log ของแหล่งใดจำเป็นเพื่อระบุว่า IP ภายในหนึ่ง ณ เวลาหนึ่งคือเครื่องของใคร
3. เรียงขั้นตอน pipeline ของ SIEM
4. Normalize log มีประโยชน์อย่างไร
5. Password spraying ต่างจาก brute force อย่างไร และตรวจจับอย่างไร
6. Impossible travel คืออะไร ต้องใช้ข้อมูลอะไรเพิ่ม
7. ลักษณะของ beaconing และ DNS tunneling ที่ใช้ตรวจจับ
8. ระบบมี 3,000 EPS ขนาดเฉลี่ย 400 byte ต่อ event จะได้ข้อมูลประมาณกี่ GB ต่อวัน
9. ทำไมต้องมี alert เมื่อ log source หยุดส่ง
10. STIX และ TAXII คืออะไร

<details><summary><b>เฉลย</b></summary>

1. ตรวจจับภัย, สืบสวนเหตุการณ์, แก้ปัญหา, compliance/กฎหมาย (และ audit)
2. DHCP log (IP ↔ MAC ↔ hostname) ร่วมกับ AD/NAC/VPN log
3. Collect → Parse → Normalize → Enrich → Store → Correlate → Alert/Case/Investigate
4. ทำให้ log จากต่างยี่ห้อใช้ชื่อ field เดียวกัน จึงค้นหาและ correlate ข้ามแหล่งได้
5. Brute force ลองหลายรหัสกับบัญชีเดียว; password spraying ลองรหัสยอดนิยมไม่กี่ตัวกับหลายบัญชี — ตรวจจาก IP เดียวที่ล้มเหลวกับบัญชีจำนวนมาก
6. บัญชีเดียว login จาก 2 ตำแหน่งที่ไกลกันเกินกว่าจะเดินทางได้ในเวลานั้น — ต้องใช้ geo-IP (และเวลา)
7. Beaconing: เชื่อมต่อปลายทางเดิมเป็นช่วงเวลาสม่ำเสมอ ขนาดใกล้เคียงกัน; DNS tunneling: query ยาว/entropy สูง/subdomain จำนวนมากไปโดเมนเดียว/TXT จำนวนมาก
8. 3,000 × 400 × 86,400 ≈ 103.7 GB/วัน (ก่อนบีบอัด)
9. Log หายอาจหมายถึงผู้โจมตีปิด log หรือ pipeline มีปัญหา ทำให้เกิดจุดบอดในการตรวจจับ
10. STIX = รูปแบบมาตรฐานสำหรับบรรยายข้อมูล threat intelligence; TAXII = โปรโตคอลสำหรับแลกเปลี่ยนข้อมูล STIX
</details>

---

➡️ ต่อไป: **Level 69 — Penetration Testing สำหรับ Network (Authorized)**
