# บทเรียน Level 61 — Security Fundamentals (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจหลักการพื้นฐานความมั่นคงปลอดภัย (CIA, AAA, Least privilege, Defense in depth, Zero Trust) · แยก Threat / Vulnerability / Risk ได้ · อ่าน CVE/CVSS · รู้จักการโจมตีที่พบบ่อยและ Kill Chain/MITRE ATT&CK · รู้จัก framework และกฎหมายไทยที่เกี่ยวข้อง

---

## 1. ทำไม Network Engineer ต้องรู้ Security

- **เครือข่ายคือเส้นทางของการโจมตี** — ผู้โจมตีต้องเข้ามา เคลื่อนที่ภายใน และส่งข้อมูลออก ผ่านเครือข่ายเสมอ
- งาน network ส่วนใหญ่ **มีผลต่อความปลอดภัยโดยตรง**: VLAN/segmentation, ACL, firewall, VPN, Wi-Fi security, AAA, logging
- config ผิดพลาดเพียงจุดเดียว (เปิด RDP สู่อินเทอร์เน็ต, ลืมเปลี่ยนรหัสเริ่มต้น) อาจเป็นต้นเหตุของ ransomware ทั้งองค์กร

---

## 2. CIA Triad — เป้าหมาย 3 ข้อของความมั่นคงปลอดภัย

| | ความหมาย | ภัยคุกคาม | มาตรการ |
|---|---|---|---|
| **Confidentiality** (ความลับ) | เฉพาะผู้มีสิทธิ์เท่านั้นที่เข้าถึงข้อมูลได้ | ดักฟัง, ข้อมูลรั่ว, เข้าถึงโดยไม่ได้รับอนุญาต | เข้ารหัส (TLS/IPsec), access control, segmentation |
| **Integrity** (ความถูกต้อง) | ข้อมูลไม่ถูกแก้ไขโดยไม่ได้รับอนุญาต | แก้ไขระหว่างทาง (MITM), ปลอมแปลง | hash, digital signature, HMAC, change control |
| **Availability** (ความพร้อมใช้) | ใช้งานได้เมื่อต้องการ | **DDoS**, ransomware, อุปกรณ์เสีย, config ผิด | redundancy, backup, DDoS protection, patch |

เพิ่มเติม: **Authenticity** (ยืนยันแหล่งที่มา), **Non-repudiation** (ปฏิเสธไม่ได้ว่าทำ — digital signature, log)

---

## 3. หลักการสำคัญ

### Defense in Depth (ป้องกันหลายชั้น)
ไม่มีมาตรการใดสมบูรณ์ → วางหลายชั้น ถ้าชั้นหนึ่งพลาด ชั้นอื่นยังป้องกันได้
```
 นโยบาย/การฝึกอบรม → Physical (ห้อง server ล็อก) → Perimeter (NGFW, DDoS, email gateway)
 → Network (segmentation, NAC, IDS/IPS) → Endpoint (EDR, patch, hardening)
 → Application (WAF, secure coding) → Data (encryption, DLP, backup) → Monitoring (SIEM/SOC)
```

### Least Privilege (สิทธิ์น้อยที่สุดที่จำเป็น)
ผู้ใช้/ระบบ/บริการได้สิทธิ์เท่าที่จำเป็นต่องานเท่านั้น — ใช้กับบัญชี admin, firewall rule, VPN, service account

### Separation of Duties
งานสำคัญต้องใช้มากกว่า 1 คน (คนขอ change ≠ คนอนุมัติ ≠ คนตรวจสอบ)

### Zero Trust ("Never trust, always verify")
ไม่เชื่อใจเพียงเพราะอยู่ "ในเครือข่ายภายใน" — ตรวจ identity, อุปกรณ์ และบริบททุกครั้ง, ให้สิทธิ์น้อยที่สุด, **assume breach** (คิดว่าถูกเจาะแล้ว จึงจำกัดความเสียหาย) — Level 66

### AAA และ Accountability
ทุกการกระทำต้องระบุตัวคนได้ (ไม่ใช้บัญชีร่วม) และมี log (Level 56)

### Secure by Default / Attack Surface Reduction
ปิดบริการ/port ที่ไม่ใช้, เปลี่ยนค่าเริ่มต้น, ลบบัญชีที่ไม่ใช้ — ยิ่งเปิดน้อยยิ่งโจมตียาก

---

## 4. ศัพท์ที่ต้องแยกให้ออก

| คำ | ความหมาย | ตัวอย่าง |
|---|---|---|
| **Asset** | สิ่งที่มีคุณค่าต้องปกป้อง | ฐานข้อมูลลูกค้า, ระบบ HIS, firewall |
| **Threat** | สิ่งที่อาจก่ออันตราย | กลุ่ม ransomware, พนักงานไม่พอใจ, น้ำท่วม |
| **Vulnerability** | **จุดอ่อน** ที่ถูกใช้ได้ | VPN ไม่ได้ patch, รหัสผ่านเริ่มต้น, ไม่มี MFA |
| **Exploit** | วิธี/โค้ดที่ใช้ประโยชน์จากจุดอ่อน | สคริปต์โจมตีช่องโหว่ VPN |
| **Risk** | **โอกาส × ผลกระทบ** เมื่อ threat ใช้ vulnerability กับ asset | "มีโอกาสสูงที่ ransomware จะเข้ามาทาง VPN ไม่มี MFA และหยุดโรงพยาบาลหลายวัน" |
| **Control** | มาตรการลดความเสี่ยง | MFA, patch, segmentation, backup |
| **Zero-day** | ช่องโหว่ที่ยังไม่มี patch | |

### การจัดการความเสี่ยง (Risk Treatment)
**Mitigate** (ลด — เพิ่ม control) · **Transfer** (โอน — ประกันภัย/outsource) · **Avoid** (หลีกเลี่ยง — เลิกทำกิจกรรมนั้น) · **Accept** (ยอมรับ — ผู้บริหารลงนามรับทราบ)

---

## 5. CVE, CVSS, EPSS, KEV

- **CVE (Common Vulnerabilities and Exposures):** หมายเลขอ้างอิงของช่องโหว่ เช่น `CVE-2024-XXXXX`
- **CVSS (Common Vulnerability Scoring System):** คะแนนความรุนแรง 0.0–10.0

| คะแนน | ระดับ |
|---|---|
| 0.1–3.9 | Low |
| 4.0–6.9 | Medium |
| 7.0–8.9 | High |
| **9.0–10.0** | **Critical** |

- **EPSS:** ความน่าจะเป็นที่ช่องโหว่จะถูกใช้โจมตีจริงใน 30 วัน
- **CISA KEV (Known Exploited Vulnerabilities):** รายการช่องโหว่ที่ **ถูกโจมตีจริงแล้ว** → ควร patch ก่อน
- **Vendor PSIRT advisory:** ประกาศของผู้ผลิต (Cisco, Fortinet, Palo Alto) — ต้องติดตามสม่ำเสมอ

> 🔑 จัดลำดับ patch ด้วย **ความเสี่ยงจริง** (เปิดสู่อินเทอร์เน็ตไหม, อยู่ใน KEV ไหม, asset สำคัญแค่ไหน) ไม่ใช่ CVSS อย่างเดียว

---

## 6. การโจมตีที่พบบ่อย (ในมุม Network)

| การโจมตี | ลักษณะ | ป้องกัน |
|---|---|---|
| **Phishing / BEC** | หลอกให้คลิก/กรอกรหัส/โอนเงิน | email security, MFA (phishing-resistant), awareness |
| **Ransomware** | เข้ารหัสข้อมูลแล้วเรียกค่าไถ่ + ขโมยข้อมูลขู่เปิดเผย | MFA, patch, segmentation, EDR, **immutable backup** |
| **Credential stuffing / Brute force** | ใช้รหัสที่รั่วจากที่อื่น/เดารหัส | MFA, lockout, ตรวจจับ |
| **Exploit ช่องโหว่อุปกรณ์ขอบ** (VPN, firewall) | โจมตีอุปกรณ์ที่เปิดสู่อินเทอร์เน็ต | patch ทันที, ปิดบริการที่ไม่ใช้, ปิดหน้า admin |
| **DDoS** | ท่วม bandwidth/ทรัพยากร | ISP/cloud scrubbing, CDN, rate-limit (Level 70) |
| **MITM** (ARP spoofing, rogue AP, rogue DHCP) | ดัก/แก้ข้อมูลกลางทาง | DAI, DHCP snooping, 802.1X, การเข้ารหัส |
| **Lateral movement** | เคลื่อนจากเครื่องที่ยึดได้ไปยังเครื่องอื่น | segmentation, least privilege, ปิด SMB/RDP ข้ามวง, EDR |
| **Data exfiltration** | ส่งข้อมูลออก (รวมผ่าน DNS tunneling) | egress filtering, DLP, DNS monitoring |
| **Supply chain** | โจมตีผ่านผู้ให้บริการ/ซอฟต์แวร์ที่ใช้ | ควบคุมการเข้าถึงของ vendor, ตรวจสอบ |
| **Insider threat** | คนในตั้งใจหรือพลั้งเผลอ | least privilege, logging, DLP |
| **Social engineering** | หลอกทางโทรศัพท์/หน้างาน | ขั้นตอนยืนยันตัวตน, awareness |

---

## 7. Cyber Kill Chain และ MITRE ATT&CK

### Lockheed Martin Cyber Kill Chain (7 ขั้นของการโจมตี)
```
 1 Reconnaissance (สำรวจเป้าหมาย) → 2 Weaponization (เตรียมอาวุธ) → 3 Delivery (ส่ง — อีเมล/เว็บ/ช่องโหว่)
 → 4 Exploitation (ใช้ช่องโหว่) → 5 Installation (ติดตั้งมัลแวร์/persistence)
 → 6 Command & Control (C2 ติดต่อกลับ) → 7 Actions on Objectives (ขโมย/เข้ารหัส/ทำลาย)
```
**แนวคิด:** ตัดได้ขั้นใดขั้นหนึ่ง การโจมตีก็ล้มเหลว — network ช่วยได้มากที่ขั้น 3 (email/web filter, IPS), 6 (block C2, DNS filtering), 7 (egress filter, segmentation)

### MITRE ATT&CK
ฐานความรู้ **tactics (เป้าหมาย) และ techniques (วิธีการ)** ของผู้โจมตีจริง เช่น Initial Access, Execution, Persistence, Privilege Escalation, Defense Evasion, Credential Access, Discovery, **Lateral Movement**, Collection, **Command and Control**, **Exfiltration**, Impact
ใช้: map ว่าเครื่องมือของเราตรวจจับเทคนิคใดได้/ไม่ได้, เขียน use case ของ SIEM, วางแผน threat hunting (attack.mitre.org)

---

## 8. Framework และมาตรฐาน

| Framework | ใช้ทำอะไร |
|---|---|
| **NIST CSF 2.0** | กรอบบริหารความเสี่ยง 6 function: **Govern, Identify, Protect, Detect, Respond, Recover** |
| **ISO/IEC 27001:2022** | ระบบบริหารความมั่นคงปลอดภัยสารสนเทศ (ISMS) — ขอรับรองได้ · Annex A มี 93 control |
| **CIS Controls v8** | รายการ 18 control ที่ทำได้จริงตามลำดับความสำคัญ (inventory, config, access, logging …) |
| **CIS Benchmarks** | แนวทาง hardening รายผลิตภัณฑ์ (Windows, Linux, Cisco, FortiGate …) |
| **PCI DSS v4** | องค์กรที่ประมวลผลบัตรชำระเงิน |
| **NIST SP 800-207** | Zero Trust Architecture |

---

## 9. กฎหมายและหน่วยงานในประเทศไทย (ที่ network engineer ควรรู้)

| กฎหมาย/หน่วยงาน | สาระที่เกี่ยวข้อง |
|---|---|
| **พ.ร.บ.ว่าด้วยการกระทำความผิดเกี่ยวกับคอมพิวเตอร์ พ.ศ. 2550 (แก้ไข 2560)** | ห้ามเข้าถึงระบบโดยไม่ได้รับอนุญาต · ผู้ให้บริการต้อง **เก็บข้อมูลจราจรคอมพิวเตอร์ไม่น้อยกว่า 90 วัน** (ขยายได้ตามคำสั่ง) |
| **พ.ร.บ.คุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562 (PDPA)** | ต้องมีมาตรการรักษาความปลอดภัยที่เหมาะสม · **แจ้งเหตุละเมิดต่อ สคส. ภายใน 72 ชั่วโมง** (เมื่อมีความเสี่ยงต่อสิทธิของเจ้าของข้อมูล) · packet capture/log ก็มีข้อมูลส่วนบุคคล |
| **พ.ร.บ.การรักษาความมั่นคงปลอดภัยไซเบอร์ พ.ศ. 2562** | หน่วยงานโครงสร้างพื้นฐานสำคัญทางสารสนเทศ (**CII**) ต้องปฏิบัติตามมาตรฐานและรายงานเหตุ · หน่วยงานกำกับ **สกมช. (NCSA)** |
| **ThaiCERT** (ภายใต้ สกมช.) | ประสานและแจ้งเตือนเหตุภัยคุกคามไซเบอร์ |
| หน่วยงานกำกับเฉพาะ | ธปท. (ธนาคาร), ก.ล.ต., คปภ. (ประกันภัย), กสทช. (โทรคมนาคม) มีแนวปฏิบัติด้าน IT risk เพิ่มเติม |

> ⚠️ **การทดสอบเจาะระบบ/สแกนโดยไม่ได้รับอนุญาตเป็นความผิดตามกฎหมาย** — ต้องมีหนังสืออนุญาตและขอบเขตชัดเจนเสมอ แม้ในองค์กรของตัวเอง

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| มี firewall แล้วปลอดภัย | ต้องป้องกันหลายชั้น (defense in depth) |
| อยู่ในเครือข่ายภายในแล้วเชื่อถือได้ | Zero Trust — assume breach |
| CVSS สูงสุดต้อง patch ก่อนเสมอ | จัดลำดับตามความเสี่ยงจริง (exposure, KEV, asset) |
| Security เป็นงานของทีม security อย่างเดียว | network/system engineer เป็นผู้ทำ control ส่วนใหญ่ |
| ไม่มีใครสนใจโจมตีองค์กรเล็ก | การโจมตีส่วนใหญ่เป็นแบบอัตโนมัติ ไม่เลือกขนาด |

---

## 11. Cheat Sheet

```
CIA: Confidentiality · Integrity · Availability (+ authenticity, non-repudiation)
หลักการ: Defense in depth · Least privilege · Separation of duties · Zero Trust (assume breach) · ลด attack surface
Threat (ภัย) · Vulnerability (จุดอ่อน) · Exploit (วิธีใช้) · Risk = โอกาส × ผลกระทบ · Control (มาตรการ)
Risk treatment: Mitigate · Transfer · Avoid · Accept
CVE (หมายเลข) · CVSS 9-10 Critical · EPSS · CISA KEV (ถูกโจมตีจริง) · vendor PSIRT
Kill chain: Recon → Weaponize → Deliver → Exploit → Install → C2 → Actions
MITRE ATT&CK: tactics/techniques จริงของผู้โจมตี
NIST CSF 2.0 (Govern/Identify/Protect/Detect/Respond/Recover) · ISO 27001 · CIS Controls/Benchmarks
ไทย: พ.ร.บ.คอมฯ (log ≥ 90 วัน) · PDPA (แจ้ง 72 ชม.) · พ.ร.บ.ไซเบอร์ (CII, สกมช.)
```

---

## 12. แบบทดสอบ 10 ข้อ

1. CIA Triad คืออะไร DDoS กระทบข้อใด
2. Defense in depth คืออะไร ยกตัวอย่าง 4 ชั้น
3. Vulnerability กับ Risk ต่างกันอย่างไร
4. วิธีจัดการความเสี่ยง 4 แบบ
5. CVSS 9.8 อยู่ระดับใด และควรพิจารณาอะไรเพิ่มในการจัดลำดับ patch
6. CISA KEV คืออะไร
7. การโจมตีแบบ lateral movement คืออะไร ป้องกันด้วยมาตรการด้านเครือข่ายใด
8. เรียง Cyber Kill Chain และบอกขั้นที่เครือข่ายช่วยตัดได้
9. NIST CSF 2.0 มี function อะไรบ้าง
10. กฎหมายไทยกำหนดให้เก็บ log จราจรคอมพิวเตอร์กี่วัน และ PDPA กำหนดให้แจ้งเหตุละเมิดภายในกี่ชั่วโมง

<details><summary><b>เฉลย</b></summary>

1. Confidentiality, Integrity, Availability — DDoS กระทบ Availability
2. ป้องกันหลายชั้น เช่น firewall ที่ขอบ, segmentation/NAC, EDR บนเครื่อง, การเข้ารหัสข้อมูล + backup, monitoring
3. Vulnerability คือจุดอ่อน; Risk คือโอกาสที่ภัยจะใช้จุดอ่อนนั้นคูณผลกระทบที่เกิดกับ asset
4. Mitigate, Transfer, Avoid, Accept
5. Critical — พิจารณาว่าเปิดสู่อินเทอร์เน็ตหรือไม่, อยู่ใน KEV/มี exploit แล้วหรือไม่ (EPSS), ความสำคัญของ asset
6. รายการช่องโหว่ที่ถูกนำไปใช้โจมตีจริงแล้ว ควร patch เร่งด่วน
7. การเคลื่อนจากเครื่องที่ถูกยึดไปยังเครื่องอื่นภายใน — ป้องกันด้วย segmentation/micro-segmentation, จำกัด SMB/RDP/WinRM ข้ามวง, least privilege
8. Recon → Weaponization → Delivery → Exploitation → Installation → C2 → Actions on Objectives — เครือข่ายช่วยมากที่ Delivery (filter/IPS), C2 (block/DNS filtering), Actions (egress filter/segmentation)
9. Govern, Identify, Protect, Detect, Respond, Recover
10. ไม่น้อยกว่า 90 วัน; 72 ชั่วโมง (เมื่อมีความเสี่ยงต่อสิทธิของเจ้าของข้อมูล)
</details>

---

➡️ ต่อไป: **Level 62 — Firewall: Stateful, NGFW, iptables/nftables**
