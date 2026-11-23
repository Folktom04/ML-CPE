# บทเรียน Level 64 — IDS/IPS (ฉบับละเอียด)

> อ่านจบแล้วจะ: แยก IDS กับ IPS · signature-based vs anomaly-based · วางตำแหน่ง sensor (inline/SPAN/TAP) · เขียนและอ่าน Suricata/Snort rule · ใช้ Zeek ทำ network security monitoring · tuning เพื่อลด false positive · รู้ข้อจำกัดเมื่อ traffic เข้ารหัส

---

## 1. IDS กับ IPS

| | **IDS (Intrusion Detection System)** | **IPS (Intrusion Prevention System)** |
|---|---|---|
| หน้าที่ | **ตรวจจับและแจ้งเตือน** | **ตรวจจับและบล็อกทันที** |
| ตำแหน่ง | **นอกเส้นทาง (out-of-band)** — รับสำเนา traffic จาก SPAN/TAP | **อยู่บนเส้นทาง (inline)** — traffic ต้องวิ่งผ่าน |
| ผลกระทบต่อ traffic | ไม่มี (ถ้า IDS ล่ม traffic ไม่กระทบ) | เพิ่ม latency เล็กน้อย, ถ้าล่ม/บล็อกผิด → กระทบผู้ใช้ |
| False positive | ได้แค่ alert ที่ไม่จำเป็น | **บล็อก traffic ที่ถูกต้อง** (ผลเสียมากกว่า) |
| ตัวอย่าง | Suricata/Snort (IDS mode), Zeek, Security Onion | IPS ใน **NGFW** (FortiGate, Palo Alto), Suricata inline, Cisco Secure IPS |

```
 IDS:  [Internet]──[Firewall]──[Switch]──[Servers]          IPS: [Internet]──[FW/IPS inline]──[Servers]
                                  │ SPAN/TAP (สำเนา)                    ↑ traffic ผ่านและถูกตัดสินที่นี่
                               [IDS sensor] → alert → SIEM
```

> 💡 ปัจจุบัน **IPS ส่วนใหญ่อยู่ใน NGFW** (เปิด IPS profile บน policy) ส่วน IDS/NSM แยก (Suricata, Zeek, NDR) ใช้เพื่อ **มองเห็น** traffic ภายใน (east-west) และเก็บหลักฐาน

### Fail-open vs Fail-closed (สำหรับ IPS inline)
- **Fail-open:** IPS ล่ม → ปล่อย traffic ผ่าน (รักษา availability) — นิยมสำหรับระบบที่ต้องทำงานต่อเนื่อง
- **Fail-closed:** IPS ล่ม → บล็อกทั้งหมด (รักษา security) — สำหรับ zone ความเสี่ยงสูงมาก
- ใช้ **bypass switch/NIC** หรือ HA เพื่อลดผลกระทบ

---

## 2. วิธีตรวจจับ

| วิธี | หลักการ | ข้อดี | ข้อเสีย |
|---|---|---|---|
| **Signature-based** | เปรียบเทียบกับ **ลายเซ็น** ของการโจมตีที่รู้จัก (pattern ใน packet) | แม่นยำ อธิบายได้ว่าเจออะไร | จับ **zero-day/รูปแบบใหม่** ไม่ได้, ต้องอัปเดต signature |
| **Anomaly/Behavior-based** | เรียนรู้ **"ค่าปกติ"** แล้วแจ้งเมื่อผิดปกติ (ปริมาณ, เวลา, ปลายทางใหม่) — มัก ใช้ ML | จับสิ่งใหม่ได้ | **false positive สูง**, ต้องมีช่วงเรียนรู้ |
| **Protocol analysis** | ตรวจว่า traffic ทำตามมาตรฐานของโปรโตคอลหรือไม่ | จับการใช้โปรโตคอลผิดปกติ | |
| **Reputation/Threat intel** | เทียบ IP/domain/hash กับฐานข้อมูลภัย | เร็ว ง่าย | ข้อมูลต้องทันสมัย |

### ผลลัพธ์ของการตรวจจับ (สำคัญมาก)
| | มีการโจมตีจริง | ไม่มีการโจมตี |
|---|---|---|
| **มี alert** | ✅ **True Positive** | ⚠️ **False Positive** (แจ้งผิด) |
| **ไม่มี alert** | ❌ **False Negative** (หลุดรอด — อันตรายที่สุด) | ✅ True Negative |
- False positive มากเกินไป → **alert fatigue** ทีมเลิกสนใจ alert แล้วพลาด true positive
- จึงต้อง **tuning** อย่างต่อเนื่อง

---

## 3. ตำแหน่งวาง Sensor

| ตำแหน่ง | เห็นอะไร |
|---|---|
| **หลัง firewall ขาเข้า** (ฝั่งภายใน) | traffic ที่ผ่าน firewall มาแล้ว (alert ที่เกี่ยวข้องจริง) |
| **หน้า firewall** (ฝั่งอินเทอร์เน็ต) | การโจมตีทั้งหมด (noise สูงมาก — มักไม่คุ้ม) |
| **DMZ** | การโจมตี server สาธารณะ |
| **Data center core (east-west)** | lateral movement ระหว่าง server |
| **ระหว่าง user zone กับ server zone** | เครื่องผู้ใช้ที่ติดมัลแวร์โจมตี server |
| **Internet egress** | C2 callback, data exfiltration |
| **OT/ICS** | โปรโตคอลอุตสาหกรรม (passive เท่านั้น) |

**วิธีรับ traffic สำหรับ IDS**
- **SPAN/Port mirror** — ง่าย ไม่ต้องซื้อเพิ่ม แต่ switch อาจทิ้ง packet เมื่อโหลดสูง ไม่เห็น frame ที่มี error
- **Network TAP** — แม่นยำ ได้ทุก packet ไม่กระทบ switch เหมาะกับลิงก์สำคัญ
- **Packet broker** — รวม/กรอง/กระจาย traffic จาก TAP หลายจุดไปยังเครื่องมือหลายตัว

---

## 4. Suricata / Snort

**Suricata** (OISF) และ **Snort** (Cisco) — IDS/IPS open source ที่ใช้มากที่สุด (Snort 3, Suricata รองรับ multi-thread)
- ชุด rule ฟรี: **Emerging Threats Open (ET Open)**, Snort Community · แบบเสียเงิน: ET Pro, Snort Subscriber (Talos)
- Suricata ยังสร้าง **log metadata** ได้ (EVE JSON: flow, dns, http, tls, fileinfo) นำเข้า SIEM ได้ง่าย

### โครงสร้าง Rule
```
 action  proto  src_ip   src_port  ->  dst_ip      dst_port  (options)
 alert   tcp    $EXTERNAL_NET any  ->  $HOME_NET   22        (msg:"Possible SSH brute force";
         flow:to_server,established; threshold:type both, track by_src, count 10, seconds 60;
         classtype:attempted-admin; sid:1000001; rev:1;)
```
| ส่วน | ความหมาย |
|---|---|
| **action** | `alert` (แจ้ง), `drop` (บล็อก — IPS mode), `pass`, `reject` |
| proto / ip / port | header ที่ต้องตรง — ใช้ตัวแปร `$HOME_NET`, `$EXTERNAL_NET` |
| `->` / `<>` | ทิศทาง |
| **msg** | ข้อความใน alert |
| **content** | pattern ที่ต้องพบใน payload (`content:"/wp-login.php"; http.uri;`) |
| **flow** | ทิศทาง/สถานะของ session |
| **threshold** | จำกัดจำนวน alert / ตรวจจับตามความถี่ |
| **sid / rev** | หมายเลขและเวอร์ชันของ rule (custom ใช้ ≥ 1,000,000) |
| classtype, reference, metadata | หมวด/อ้างอิง (CVE)/ข้อมูลเสริม |

### ตัวอย่าง rule ที่ใช้งานได้
```
# DNS query ไปโดเมนต้องสงสัย
alert dns $HOME_NET any -> any any (msg:"DNS query to suspicious TLD .zip"; dns.query; content:".zip"; endswith; sid:1000010; rev:1;)
# ตรวจ user-agent ของเครื่องมือสแกน
alert http $EXTERNAL_NET any -> $HOME_NET any (msg:"Scanner UA sqlmap"; http.user_agent; content:"sqlmap"; nocase; sid:1000011; rev:1;)
# ตรวจ SMB จากวงผู้ใช้ไปยังวงผู้ใช้ด้วยกัน (lateral movement ที่ไม่ควรมี)
alert tcp $USER_NET any -> $USER_NET 445 (msg:"SMB between user hosts"; flow:to_server; flags:S; threshold:type limit, track by_src, count 1, seconds 300; sid:1000012; rev:1;)
```
```bash
suricata -T -c /etc/suricata/suricata.yaml        # ตรวจ config/rule
suricata-update                                     # อัปเดต rule
tail -f /var/log/suricata/fast.log                  # alert แบบย่อ
jq 'select(.event_type=="alert")' /var/log/suricata/eve.json
```

---

## 5. Zeek — Network Security Monitoring (NSM)

**Zeek** (เดิมชื่อ Bro) **ไม่ได้เน้น signature** แต่สร้าง **log ที่บรรยายทุกการเชื่อมต่อแบบมีโครงสร้าง** — ใช้สืบสวนย้อนหลังและ threat hunting

| Log | มีอะไร |
|---|---|
| `conn.log` | ทุก connection: เวลา, IP/port, protocol, ระยะเวลา, จำนวนไบต์ |
| `dns.log` | query/answer ทั้งหมด |
| `http.log` | host, URI, user-agent, status |
| `ssl.log` | TLS version, SNI, cert, JA3/JA4 |
| `files.log` | ไฟล์ที่ถ่ายโอน (hash) |
| `notice.log` | สิ่งผิดปกติที่ script ตรวจพบ |

**ใช้หา:** C2 beaconing (เชื่อมต่อสม่ำเสมอเป็นระยะ), DNS tunneling, ข้อมูลออกปริมาณมาก, cert แปลก, เครื่องที่คุยกับประเทศ/ASN ผิดปกติ
แพลตฟอร์มรวม: **Security Onion** (Suricata + Zeek + Elastic + case management), Arkime (full packet capture)

---

## 6. Tuning — หัวใจของ IDS/IPS ที่ใช้งานได้จริง

```
 1) เริ่มจากโหมด detect/alert (IDS) ก่อน แม้เป็นอุปกรณ์ IPS
 2) ตั้ง $HOME_NET, server variables ให้ถูกต้อง (ลด false positive มหาศาล)
 3) ปิด rule ที่ไม่เกี่ยวกับสภาพแวดล้อม (เช่น rule ของระบบที่ไม่มีใช้)
 4) วิเคราะห์ alert ที่เกิดบ่อย: จริงหรือไม่?
      → false positive: suppress เฉพาะ source/destination นั้น (ไม่ปิดทั้ง rule ถ้าไม่จำเป็น)
      → true positive: แก้ต้นเหตุ
 5) เปลี่ยน rule ที่มั่นใจ (critical, ไม่มี FP) เป็น block ทีละกลุ่ม
 6) อัปเดต signature อัตโนมัติ + ทบทวน alert เป็นประจำ
```
```
# suppress ตัวอย่าง (threshold.config ของ Suricata)
suppress gen_id 1, sig_id 2010935, track by_src, ip 10.0.99.20     # vulnerability scanner ของเราเอง
```

---

## 7. ข้อจำกัด: Traffic ที่เข้ารหัส

ปัจจุบัน traffic ส่วนใหญ่ (> 90% ของเว็บ) เป็น **TLS** → IDS/IPS **ไม่เห็น payload**
**ทางเลือก**
- **SSL/TLS inspection** บน NGFW/proxy (ถอดรหัส–ตรวจ–เข้ารหัสใหม่) — มีข้อพิจารณาด้าน privacy/PDPA และ exemption (ISC Level 46)
- **ตรวจจาก metadata** ที่ยังเห็น: SNI, certificate, **JA3/JA4 fingerprint**, ขนาด/จังหวะของ flow, ปลายทาง (IP/ASN reputation)
- **DNS monitoring** — ยังเห็นชื่อโดเมน (ถ้าไม่ใช่ DoH)
- **EDR** บน endpoint — เห็นก่อนเข้ารหัส (Level 51 SI/ISC)
- **NDR** (Darktrace, ExtraHop, Vectra, Corelight) — ใช้ behavior/ML กับ metadata

---

## 8. Workflow เมื่อเกิด Alert

```
 Alert: "ET MALWARE Known C2 domain" จาก 10.0.10.55
 1) Triage: rule นี้เชื่อถือได้ไหม? เคยเป็น FP ไหม?
 2) Context: 10.0.10.55 คือเครื่องใคร (DHCP/AD/asset), ติดต่อโดเมนนี้กี่ครั้ง (DNS log/Zeek)
 3) Scope: เครื่องอื่นติดต่อโดเมน/IP เดียวกันไหม?
 4) Contain: แยกเครื่อง (EDR isolate/NAC quarantine/ย้าย VLAN), block domain/IP ที่ firewall/DNS
 5) ส่งต่อ IR process (Level 70) · บันทึก case
```

---

## 9. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| IDS บล็อกการโจมตีได้ | IDS แค่ตรวจจับ/แจ้งเตือน IPS จึงบล็อก |
| ติดตั้งแล้วใช้ค่าเริ่มต้นได้ทันที | ต้อง tuning ไม่เช่นนั้น alert ท่วม |
| IPS กันได้ทุกอย่าง | signature จับ zero-day ไม่ได้ และมองไม่เห็นใน traffic เข้ารหัส |
| วาง sensor หน้า firewall ดีที่สุด | noise สูงมาก มักวางหลัง firewall/ระหว่าง zone |
| False negative ไม่สำคัญเท่า false positive | false negative อันตรายที่สุด (ภัยหลุดรอด) |

---

## 10. Cheat Sheet

```
IDS = ตรวจจับ+แจ้ง (out-of-band, SPAN/TAP) · IPS = ตรวจจับ+บล็อก (inline, มักอยู่ใน NGFW)
Fail-open (availability) vs fail-closed (security)
Signature (แม่น, ไม่จับ zero-day) · Anomaly (จับใหม่, FP สูง) · Reputation
TP / FP (แจ้งผิด) / FN (หลุด — อันตรายสุด) / TN · alert fatigue → tuning
Sensor: หลัง FW, DMZ, DC east-west, user↔server, egress · TAP > SPAN
Suricata/Snort rule: action proto src port -> dst port (msg; content; flow; threshold; sid; rev;)
ET Open rules · suricata-update · eve.json
Zeek = NSM logs (conn, dns, http, ssl, files) · Security Onion · Arkime
Encrypted: SSL inspection · JA3/JA4 · SNI · DNS · EDR · NDR
```

---

## 11. แบบทดสอบ 10 ข้อ

1. IDS กับ IPS ต่างกันอย่างไร (ตำแหน่งและหน้าที่)
2. Fail-open กับ fail-closed คืออะไร
3. Signature-based กับ anomaly-based ต่างกันอย่างไร
4. False positive และ false negative คืออะไร อย่างไหนอันตรายกว่า
5. ทำไม SPAN อาจไม่เหมาะกับลิงก์สำคัญ และทางเลือกคืออะไร
6. ในตัวอย่าง rule ส่วน `content`, `flow`, `threshold`, `sid` ทำหน้าที่อะไร
7. Zeek ต่างจาก Suricata อย่างไร
8. ขั้นตอน tuning IDS/IPS ใหม่
9. IDS มีข้อจำกัดอย่างไรกับ traffic ที่เข้ารหัส และมีทางเลือกอะไรบ้าง
10. ได้รับ alert ว่าเครื่องติดต่อโดเมน C2 ควรทำอะไรต่อ

<details><summary><b>เฉลย</b></summary>

1. IDS อยู่นอกเส้นทาง รับสำเนา traffic ตรวจจับและแจ้งเตือน; IPS อยู่ inline ตรวจจับและบล็อกได้ทันที
2. Fail-open: เมื่อ IPS ล่มปล่อย traffic ผ่าน (รักษา availability); fail-closed: บล็อกทั้งหมด (รักษา security)
3. Signature เทียบกับลายเซ็นการโจมตีที่รู้จัก (แม่นแต่จับ zero-day ไม่ได้); anomaly เรียนรู้ค่าปกติแล้วแจ้งสิ่งผิดปกติ (จับสิ่งใหม่ได้แต่ FP สูง)
4. FP = แจ้งเตือนแต่ไม่ใช่การโจมตี; FN = มีการโจมตีแต่ไม่แจ้ง — FN อันตรายกว่า
5. Switch อาจทิ้งสำเนาเมื่อโหลดสูงและไม่ส่ง frame ที่มี error — ใช้ network TAP (+ packet broker)
6. content = pattern ใน payload; flow = ทิศทาง/สถานะ session; threshold = จำกัด/กำหนดความถี่ของ alert; sid = หมายเลขประจำ rule
7. Zeek สร้าง log metadata ของทุกการเชื่อมต่อสำหรับสืบสวน/hunting; Suricata เน้นตรวจจับด้วย signature (แต่สร้าง log ได้เช่นกัน)
8. เริ่ม detect mode → ตั้ง HOME_NET/ตัวแปร → ปิด rule ที่ไม่เกี่ยวข้อง → วิเคราะห์และ suppress FP เฉพาะจุด → ค่อยเปลี่ยน rule ที่มั่นใจเป็น block → อัปเดตและทบทวนสม่ำเสมอ
9. ไม่เห็น payload — ใช้ SSL inspection, metadata (SNI, cert, JA3/JA4, flow), DNS monitoring, EDR, NDR
10. ตรวจความน่าเชื่อถือของ alert → ระบุเครื่อง/ผู้ใช้ → หาขอบเขต (เครื่องอื่นติดต่อด้วยไหม) → แยกเครื่องและบล็อกโดเมน/IP → ส่งต่อ incident response และบันทึก
</details>

---

➡️ ต่อไป: **Level 65 — Cryptography & PKI สำหรับ Network Engineer**
