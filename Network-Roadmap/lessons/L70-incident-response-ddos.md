# บทเรียน Level 70 — Incident Response & DDoS Mitigation (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจกระบวนการ Incident Response ตาม NIST · บทบาทของ network ในการตรวจจับ/จำกัดวง/กู้คืน · เก็บหลักฐานอย่างถูกต้อง · รับมือ ransomware ในมุมเครือข่าย · เข้าใจ DDoS ทุกประเภทและวิธีป้องกัน (scrubbing, CDN, RTBH, rate limit, SYN cookies) · เขียน playbook และทำ tabletop exercise

---

## 1. Incident Response คืออะไร

**Security Incident** = เหตุการณ์ที่กระทบหรือคุกคาม Confidentiality/Integrity/Availability ของระบบหรือข้อมูล (เช่น ransomware, บัญชีถูกยึด, ข้อมูลรั่ว, DDoS, มัลแวร์)
**Incident Response (IR)** = กระบวนการที่วางแผนไว้ล่วงหน้าเพื่อ **ตรวจพบ จำกัดความเสียหาย กำจัด กู้คืน และเรียนรู้**

> 🔑 **ช่วงเกิดเหตุไม่ใช่เวลาคิดแผน** — องค์กรที่ฟื้นตัวเร็วคือองค์กรที่ **เตรียมการและฝึกซ้อมไว้ก่อน**

---

## 2. วงจร IR ตาม NIST SP 800-61

```
 ┌─► ① Preparation ──► ② Detection & Analysis ──► ③ Containment, Eradication & Recovery ──► ④ Post-Incident Activity ─┐
 └────────────────────────────────────────────── (นำบทเรียนกลับไปปรับการเตรียมการ) ◄───────────────────────────────────┘
```
(NIST SP 800-61 Rev.3 ปี 2025 ปรับให้สอดคล้องกับ NIST CSF 2.0 แต่วงจรหลักยังใช้ได้เป็นกรอบ)

### ① Preparation (เตรียมการ)
- **IR plan + playbook** ต่อประเภทเหตุ (ransomware, DDoS, phishing, บัญชีถูกยึด, ข้อมูลรั่ว)
- **ทีมและบทบาท:** incident commander, ทีมเทคนิค (network, server, security), สื่อสาร, กฎหมาย/DPO, ผู้บริหาร, ผู้ให้บริการภายนอก (IR retainer, ISP, vendor)
- **Contact list** (รวมเบอร์โทรนอกระบบ — อีเมล/แชทอาจใช้ไม่ได้ระหว่างเหตุ)
- **เครื่องมือพร้อม:** SIEM, EDR, packet capture, jump host สำรอง, บัญชี break-glass
- **Log พร้อม** (เวลาตรง, เก็บนานพอ), **network diagram และ asset inventory ที่เป็นปัจจุบัน**
- **Backup ที่ทดสอบแล้ว + immutable/offline copy**
- **Tabletop exercise** อย่างน้อยปีละครั้ง

### ② Detection & Analysis (ตรวจพบและวิเคราะห์)
- แหล่ง: SIEM/EDR/IDS alert, ผู้ใช้แจ้ง, ผู้ให้บริการ/ThaiCERT แจ้ง, ข่าว
- **Triage:** ยืนยันว่าเป็นเหตุจริง → **ประเมินขอบเขตและผลกระทบ** → จัด **severity**
- **บันทึกทุกอย่างพร้อมเวลา** (timeline) ตั้งแต่นาทีแรก

### ③ Containment, Eradication & Recovery
- **Containment (จำกัดวง):** หยุดการลุกลาม — *short-term* (แยกเครื่อง/บล็อกทันที) และ *long-term* (ระบบชั่วคราวที่ปลอดภัยระหว่างแก้)
- **Eradication (กำจัด):** ลบมัลแวร์, ปิดช่องทางเข้า, reset credential, patch
- **Recovery (กู้คืน):** คืนระบบจาก backup ที่สะอาด, เฝ้าดูใกล้ชิด, ค่อย ๆ เปิดใช้งาน

### ④ Post-Incident Activity
- **Lessons learned** (ภายใน 1–2 สัปดาห์) แบบ blameless
- รายงานเหตุ (ภายใน/ผู้บริหาร/หน่วยงานกำกับ), ปรับ control/playbook/use case

---

## 3. บทบาทของ Network ในแต่ละขั้น

| ขั้น | สิ่งที่ทีม network ทำ |
|---|---|
| **Detect** | firewall/IDS/DNS/flow log, ตรวจ traffic ผิดปกติ (C2, exfiltration, scan ภายใน) |
| **Analyze** | หาว่า IP คือเครื่องใคร (DHCP/ARP/MAC table/NAC), ใครคุยกับใคร (flow, firewall log), packet capture |
| **Contain** | **แยกเครื่อง** (shutdown port, ย้ายไป quarantine VLAN, NAC CoA, EDR isolate), **บล็อก** IP/domain/port ที่ firewall/DNS (sinkhole), ตัดการเชื่อมต่อระหว่าง segment, ปิด VPN ของบัญชีที่ถูกยึด, ตัดลิงก์ไปสาขาที่ติดเชื้อ |
| **Eradicate** | ปิดช่องโหว่ (patch firewall/VPN), ลบ rule/บัญชีที่ผู้โจมตีสร้าง, เปลี่ยนรหัส/key/PSK ของอุปกรณ์เครือข่าย |
| **Recover** | เปิดการเชื่อมต่อทีละส่วนพร้อม monitor เข้มข้น, ตรวจ config อุปกรณ์เทียบกับ backup ที่ทราบว่าดี |
| **Lessons** | ปรับ segmentation, L2 security, logging, การตรวจจับ |

### Containment แบบต่าง ๆ (เลือกตามสถานการณ์)
| วิธี | ข้อดี | ข้อควรระวัง |
|---|---|---|
| ย้ายเครื่องไป **quarantine VLAN** / EDR isolate | แยกได้แต่ยังเก็บหลักฐาน/เข้าตรวจได้ | ต้องเตรียม VLAN/policy ไว้ก่อน |
| Shutdown switch port / ถอดสาย | เร็ว ชัดเจน | อาจกระทบอุปกรณ์อื่นบนพอร์ตเดียวกัน |
| บล็อก IP/domain ที่ firewall + **DNS sinkhole** | หยุด C2/exfiltration ทั้งองค์กร | ผู้โจมตีอาจสลับ infrastructure |
| ตัดการเชื่อมต่อระหว่าง segment/สาขา | หยุดการลาม | กระทบธุรกิจ — ต้องมีผู้มีอำนาจตัดสินใจ |
| ตัดอินเทอร์เน็ตทั้งองค์กร | หยุดทุกการติดต่อภายนอก | ผลกระทบสูงมาก — ใช้เมื่อจำเป็นจริง |

> ⚠️ **อย่าปิดเครื่องที่สงสัยว่าถูกโจมตีโดยไม่จำเป็น** — หลักฐานใน memory (process, การเชื่อมต่อ, กุญแจเข้ารหัสบางครั้ง) จะหาย ให้ **แยกจากเครือข่ายแทน** และปรึกษาทีม forensics (ยกเว้นกรณีที่การเข้ารหัสกำลังดำเนินอยู่และต้องหยุดทันที)

---

## 4. การเก็บหลักฐาน (Evidence)

- **ลำดับความผันผวน (order of volatility):** memory → network connections/state → disk → log ระยะไกล → backup
- เก็บ: **packet capture**, firewall/proxy/DNS/VPN/AD log ช่วงเวลาที่เกี่ยวข้อง, **config ของอุปกรณ์เครือข่าย ณ ขณะนั้น** (`show running-config`, `show tech`, ARP/MAC/routing table, session table), NetFlow
- **Chain of custody:** บันทึกว่าใครเก็บอะไร เมื่อไร อย่างไร เก็บที่ไหน ส่งต่อให้ใคร — จำเป็นหากต้องใช้ทางกฎหมาย
- คำนวณ **hash** ของไฟล์หลักฐานทันทีที่เก็บ
- ตรวจว่าเวลาของแหล่งต่าง ๆ ตรงกัน (NTP) เพื่อสร้าง timeline

---

## 5. Ransomware — Playbook ในมุมเครือข่าย (ย่อ)

```
 0) ยืนยันเหตุ → ประกาศ incident → เรียก incident commander + ทีม (ใช้ช่องทางสื่อสารสำรอง)
 1) CONTAIN ทันที
    - แยกเครื่องที่ติด (EDR isolate / quarantine VLAN)
    - ตัดการเชื่อมต่อระหว่าง segment/สาขาที่ยังไม่ติด (ตามที่ผู้มีอำนาจอนุมัติ)
    - ⭐ ปกป้อง BACKUP: ตัด backup network/repository ออกจากเครือข่ายที่ติด, ระงับบัญชี backup admin ที่อาจรั่ว
    - บล็อก C2 IP/domain ที่ firewall/DNS · ปิด/จำกัด VPN, reset รหัสบัญชีที่ใช้ remote access
    - ปกป้อง management plane (vCenter/hypervisor/storage/อุปกรณ์เครือข่าย) — เปลี่ยนรหัส, จำกัดการเข้าถึงเหลือ jump host ที่ปลอดภัย
 2) ANALYZE: patient zero, ช่องทางเข้า (VPN? phishing? RDP?), ขอบเขต, ข้อมูลถูกขโมยออกไปหรือไม่ (flow/firewall: ปริมาณข้อมูลขาออกผิดปกติ)
 3) ERADICATE: ปิดช่องทางเข้า (patch, MFA), ลบ persistence/บัญชีที่ผู้โจมตีสร้าง,
    reset credential สำคัญทั้งหมด (รวม krbtgt 2 ครั้งตามขั้นตอน, service account, PSK/รหัสอุปกรณ์เครือข่าย)
 4) RECOVER: สร้างระบบหลักใหม่/restore จาก backup ที่ตรวจแล้วว่าสะอาด (immutable copy) ตามลำดับความสำคัญ
    (identity → network/security → ระบบหลักทางธุรกิจ) · เปิดใช้ทีละส่วน + monitor เข้มข้น
 5) แจ้งเหตุตามกฎหมาย (ดูข้อ 9) · สื่อสารกับผู้มีส่วนได้เสีย · lessons learned
```

---

## 6. DDoS (Distributed Denial of Service)

**DDoS** = ใช้เครื่องจำนวนมาก (botnet, ทรัพยากรที่ถูกยึด, IoT) ส่ง traffic ท่วมเป้าหมายจนให้บริการไม่ได้ (โจมตี **Availability**)

### ประเภทของ DDoS
| ประเภท | ชั้น | ตัวอย่าง | วัดด้วย |
|---|---|---|---|
| **Volumetric** | L3/L4 | UDP flood, **amplification/reflection** (DNS, NTP, memcached, CLDAP, SSDP — ส่ง request เล็กโดยปลอม IP ต้นทางเป็นเหยื่อ ให้ server ตอบกลับขนาดใหญ่ไปหาเหยื่อ) | **bps** (Gbps–Tbps) |
| **Protocol / State exhaustion** | L3/L4 | **SYN flood**, ACK flood, fragment attack — ทำให้ session table ของ firewall/LB/server เต็ม | **pps** |
| **Application layer** | L7 | HTTP GET/POST flood, slowloris, โจมตี endpoint ที่ประมวลผลหนัก (search/login) | **rps** (requests/s) — ตรวจยากเพราะดูเหมือน traffic ปกติ |

### ทำไม Firewall ในองค์กรกัน DDoS ขนาดใหญ่ไม่ได้
```
 ลิงก์อินเทอร์เน็ตขององค์กร = 1 Gbps · การโจมตี = 50 Gbps
 → ลิงก์เต็มตั้งแต่ฝั่ง ISP ก่อนถึง firewall → firewall ดีแค่ไหนก็ไม่ช่วย
 → ต้องกรองที่ "ต้นน้ำ" (ISP/cloud scrubbing) ที่มีความจุมากกว่าการโจมตี
```

### วิธีป้องกัน DDoS
| วิธี | ทำงานอย่างไร | กัน |
|---|---|---|
| **ISP DDoS protection / Cloud scrubbing** (Cloudflare, Akamai, AWS Shield, Azure DDoS Protection, บริการของ ISP ไทย) | เปลี่ยนเส้นทาง traffic (BGP/DNS) ไปผ่าน **scrubbing center** ที่กรองแล้วส่งเฉพาะ traffic ดีกลับมา | Volumetric, protocol |
| **CDN / Reverse proxy** | ซ่อน origin IP, กระจายโหลดไปหลาย PoP, cache | Volumetric ต่อเว็บ, L7 บางส่วน |
| **WAF + rate limiting + bot management** | จำกัด request/IP, challenge (CAPTCHA/JS), ตรวจ bot | L7 |
| **RTBH (Remotely Triggered Black Hole)** | ส่ง BGP community ให้ ISP **ทิ้ง traffic ทั้งหมด** ไปยัง IP ที่ถูกโจมตี | ปกป้องส่วนที่เหลือของเครือข่าย (แต่ IP เป้าหมายใช้ไม่ได้ — "ยอมเสียหนึ่งเพื่อรักษาทั้งหมด") |
| **Flowspec (BGP)** | ส่งกฎกรองละเอียด (port/protocol) ให้ router ของ ISP | กรองเจาะจงกว่า RTBH |
| **SYN cookies / SYN proxy** | ไม่จอง state จนกว่า handshake ครบ | SYN flood |
| **Rate limit / connection limit** บน firewall/LB | จำกัด session ต่อ IP | protocol, L7 เล็ก |
| **Anycast** | กระจายการโจมตีไปหลายที่ | Volumetric (สำหรับผู้ให้บริการ/DNS) |
| **Over-provisioning + redundancy** | ความจุเผื่อ, หลาย ISP | การโจมตีขนาดเล็ก |

### ไม่เป็นต้นทางของการโจมตี (ความรับผิดชอบต่อส่วนรวม)
- **ไม่เปิด DNS resolver/NTP/memcached/SSDP สู่สาธารณะ** (เป็นตัวขยายให้ amplification attack)
- **BCP 38 / uRPF** — กรอง packet ที่ source IP ปลอม (ไม่ใช่ของเครือข่ายเรา) ไม่ให้ออก
- อุปกรณ์ IoT เปลี่ยนรหัสเริ่มต้น ไม่ให้กลายเป็นส่วนหนึ่งของ botnet

### DDoS Response Playbook (ย่อ)
```
 1) ตรวจพบ: monitoring (bandwidth/pps พุ่ง, latency, บริการช้า), แจ้งจากผู้ใช้/ISP
 2) ระบุ: ประเภท (volumetric/protocol/L7), เป้าหมาย (IP/บริการ), แหล่งที่มา (flow/packet capture)
 3) ติดต่อ ISP/ผู้ให้บริการ DDoS ตามสัญญา (เบอร์และขั้นตอนเตรียมไว้ล่วงหน้า) → เปิด mitigation/scrubbing
 4) ชั่วคราว: rate limit, geo-block (ถ้าเหมาะสม), เปลี่ยนเป็น "under attack mode" ของ CDN, RTBH สำหรับ IP ที่ไม่สำคัญ
 5) สื่อสารกับผู้ใช้/ลูกค้า · เฝ้าระวังการโจมตีอื่นที่อาจแฝงมา (DDoS มักใช้เบี่ยงความสนใจ)
 6) หลังเหตุ: ทบทวนความจุ/สัญญา DDoS protection, ปรับ playbook
```

---

## 7. Tabletop Exercise

**ซ้อมแผนบนโต๊ะ** — ผู้เกี่ยวข้องนั่งร่วมกัน ผู้ดำเนินการเล่าสถานการณ์จำลองทีละช่วง แต่ละคนตอบว่าจะทำอะไร
```
 สถานการณ์: 02:00 น. วันเสาร์ — EDR แจ้งว่า server 3 เครื่องมีไฟล์ถูกเปลี่ยนนามสกุลจำนวนมาก
 Inject 1: ใครได้รับแจ้ง? ติดต่อใคร? ใครมีอำนาจตัดการเชื่อมต่อ?
 Inject 2: พบว่าบัญชี backup admin login จาก IP ต่างประเทศเมื่อ 2 วันก่อน
 Inject 3: สื่อมวลชนโทรมาสอบถาม
 → บันทึกช่องว่าง (ไม่มีเบอร์ผู้บริหาร, ไม่รู้ว่าใครตัดสินใจ, backup ไม่ได้แยก) → แก้ไขแผน
```

---

## 8. Metrics

**MTTD** (Mean Time To Detect) · **MTTC** (to Contain) · **MTTR** (to Recover/Respond) · dwell time (ผู้โจมตีอยู่ในระบบนานเท่าไรก่อนถูกพบ) — ใช้วัดการพัฒนาความสามารถ IR

---

## 9. การแจ้งเหตุตามกฎหมาย (ประเทศไทย — ภาพรวม)

| กรณี | ต้องทำ |
|---|---|
| **ข้อมูลส่วนบุคคลรั่ว** (PDPA) | แจ้ง **สำนักงานคณะกรรมการคุ้มครองข้อมูลส่วนบุคคล (สคส.) ภายใน 72 ชั่วโมง** นับแต่ทราบเหตุ (เว้นแต่ไม่มีความเสี่ยงต่อสิทธิเสรีภาพ) และแจ้งเจ้าของข้อมูลเมื่อมีความเสี่ยงสูง |
| **หน่วยงาน CII / หน่วยงานของรัฐ** | รายงานภัยคุกคามไซเบอร์ต่อ **สกมช.** และหน่วยงานกำกับดูแลตามที่กฎหมาย/ประกาศกำหนด |
| สถาบันการเงิน/ประกัน/หลักทรัพย์ | แจ้งหน่วยงานกำกับ (ธปท./คปภ./ก.ล.ต.) ตามระยะเวลาในประกาศ |
| คดีอาญา | แจ้งความ/ประสานเจ้าหน้าที่ (เก็บหลักฐานพร้อม chain of custody) |
(ตรวจรายละเอียดกฎหมาย/ประกาศฉบับล่าสุดกับฝ่ายกฎหมายและ DPO เสมอ)

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| เจอเครื่องติดมัลแวร์ให้ปิดเครื่องทันที | แยกจากเครือข่ายก่อนเพื่อรักษาหลักฐาน (ยกเว้นจำเป็น) |
| restore จาก backup ทันทีเมื่อเจอ ransomware | ต้องหาและปิดช่องทางเข้าก่อน และตรวจว่า backup สะอาด ไม่งั้นโดนซ้ำ |
| Firewall ขององค์กรป้องกัน DDoS ได้ | DDoS ขนาดใหญ่ท่วมลิงก์ก่อนถึง firewall — ต้องกรองที่ ISP/cloud |
| IR plan เขียนครั้งเดียวพอ | ต้องซ้อมและปรับปรุงสม่ำเสมอ |
| DDoS เป็นแค่การรบกวน | มักใช้เบี่ยงความสนใจจากการโจมตีอื่น |

---

## 11. Cheat Sheet

```
NIST IR: Preparation → Detection & Analysis → Containment/Eradication/Recovery → Post-Incident (lessons)
Prepare: plan + playbook · ทีม/บทบาท · contact list นอกระบบ · log/diagram/asset · backup immutable · tabletop
Network contain: quarantine VLAN/EDR isolate · block IP/domain + DNS sinkhole · ตัด segment · ปิด VPN · ปกป้อง backup & mgmt
อย่าปิดเครื่องโดยไม่จำเป็น (หลักฐานใน memory) · chain of custody · hash หลักฐาน · NTP
Ransomware: contain → ปกป้อง backup/mgmt → หาช่องทางเข้า → กำจัด + reset credential → restore ที่สะอาด → แจ้งเหตุ
DDoS: volumetric (bps, amplification) · protocol (pps, SYN flood) · L7 (rps)
ป้องกัน: ISP/cloud scrubbing · CDN · WAF/rate limit · RTBH · Flowspec · SYN cookies · anycast
ไม่เป็นตัวขยาย: ปิด open resolver/NTP/memcached · BCP 38/uRPF
MTTD / MTTC / MTTR · PDPA แจ้ง สคส. 72 ชม. · CII แจ้ง สกมช.
```

---

## 12. แบบทดสอบ 10 ข้อ

1. เรียงขั้นตอน IR ตาม NIST SP 800-61
2. สิ่งที่ต้องเตรียมในขั้น Preparation (5 อย่าง)
3. ทีม network มีบทบาทอะไรในการ containment (3 วิธี)
4. ทำไมไม่ควรปิดเครื่องที่สงสัยว่าติดมัลแวร์ทันที
5. Chain of custody คืออะไร
6. ในเหตุ ransomware ทำไมต้องรีบปกป้อง backup และ management plane
7. DDoS มีกี่ประเภทหลัก วัดด้วยหน่วยใด
8. Amplification attack ทำงานอย่างไร และองค์กรช่วยป้องกันไม่ให้เป็นต้นทางได้อย่างไร
9. ทำไม firewall ขององค์กรป้องกัน DDoS ขนาดใหญ่ไม่ได้ และควรใช้อะไรแทน
10. RTBH คืออะไร ข้อดีข้อเสีย

<details><summary><b>เฉลย</b></summary>

1. Preparation → Detection & Analysis → Containment, Eradication & Recovery → Post-Incident Activity
2. IR plan/playbook, ทีมและบทบาท, contact list (ช่องทางสำรอง), เครื่องมือ (SIEM/EDR/capture), log และ diagram/asset ที่เป็นปัจจุบัน, backup ที่ทดสอบแล้ว (immutable), tabletop exercise
3. แยกเครื่อง (quarantine VLAN/shutdown port/NAC CoA), บล็อก IP/domain ที่ firewall/DNS sinkhole, ตัดการเชื่อมต่อระหว่าง segment/สาขา, ปิด VPN ของบัญชีที่ถูกยึด
4. หลักฐานใน memory (process, การเชื่อมต่อ) จะหาย — ควรแยกจากเครือข่ายแทน
5. การบันทึกการเก็บและส่งต่อหลักฐานทุกขั้น (ใคร อะไร เมื่อไร ที่ไหน) เพื่อให้หลักฐานน่าเชื่อถือและใช้ทางกฎหมายได้
6. ผู้โจมตีมักทำลาย backup และใช้ management plane (vCenter/hypervisor) เข้ารหัสทั้งระบบ — ถ้าสูญเสียสองสิ่งนี้จะกู้คืนไม่ได้
7. Volumetric (bps), Protocol/state exhaustion (pps), Application layer (rps)
8. ส่ง request เล็กโดยปลอม source เป็นเหยื่อไปยัง server สาธารณะที่ตอบกลับขนาดใหญ่ — ป้องกันโดยไม่เปิด DNS resolver/NTP/memcached/SSDP สู่สาธารณะ และทำ BCP 38/uRPF
9. Traffic ทำให้ลิงก์อินเทอร์เน็ตเต็มตั้งแต่ฝั่ง ISP ก่อนถึง firewall — ใช้ DDoS protection ของ ISP/cloud scrubbing/CDN
10. Remotely Triggered Black Hole — ส่ง BGP community ให้ ISP ทิ้ง traffic ไปยัง IP เป้าหมาย; ข้อดี: ปกป้องส่วนอื่นของเครือข่ายได้เร็ว ข้อเสีย: IP เป้าหมายใช้งานไม่ได้เลย (ผู้โจมตีบรรลุเป้าหมายกับ IP นั้น)
</details>

---

🎉 **จบ Tier 7** · ➡️ ต่อไป: **Level 71 — Load Balancing** · กลับไปทำโปรเจคใน [07-security.md](../07-security.md)
