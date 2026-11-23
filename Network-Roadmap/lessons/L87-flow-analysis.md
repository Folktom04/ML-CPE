# บทเรียน Level 87 — Flow Analysis: NetFlow, sFlow, IPFIX (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจว่า flow คืออะไรต่างจาก SNMP และ packet capture · NetFlow v5/v9, IPFIX, sFlow, J-Flow · สถาปัตยกรรม exporter–collector–analyzer · ตั้ง Flexible NetFlow บน Cisco และ sFlow บน switch · sampling และผลต่อความแม่นยำ · active/inactive timeout · ใช้ flow หา top talkers, capacity, DDoS, forensics · ใช้ nfdump/ntopng/Akvorado · ข้อควรระวังด้านความเป็นส่วนตัว

---

## 1. สามมุมมองของ Traffic

| | **SNMP counters** | **Flow** ⭐ | **Packet capture** |
|---|---|---|---|
| ตอบคำถาม | "ลิงก์ใช้เท่าไร" | "**ใคร** คุยกับ **ใคร** ด้วย **อะไร** เท่าไร" | "เกิดอะไรขึ้นใน packet ทุกตัว" |
| รายละเอียด | ตัวเลขรวมต่อ interface | metadata ต่อ conversation | ครบทุก byte รวม payload |
| ขนาดข้อมูล | เล็กมาก | กลาง (~1–2% ของ traffic หรือน้อยกว่าด้วย sampling) | ใหญ่มาก |
| เก็บย้อนหลัง | ปี | เดือน–ปี | ชั่วโมง–วัน |
| ใช้ | utilization, trending | top talkers, capacity, security, billing | debug protocol เชิงลึก (Level 22) |

```
 SNMP:  "WAN สาขา A ใช้ 95% ช่วง 10:00"
 Flow:  "→ 70% มาจาก 10.1.5.23 ส่งไป OneDrive (TCP 443) และ 15% เป็น Windows Update"
 PCAP:  "→ TCP window ของ 10.1.5.23 เล็ก มี retransmission เพราะ..."
```

---

## 2. Flow คืออะไร

**Flow** = กลุ่ม packet ที่มีคุณสมบัติ (key) เหมือนกันในช่วงเวลาหนึ่ง — ปกติใช้ **5-tuple** (+ อื่น ๆ)
```
 Key fields:       src IP, dst IP, src port, dst port, protocol (+ ingress interface, ToS/DSCP)
 Non-key fields:   bytes, packets, start/end time, TCP flags, next-hop, src/dst AS, egress interface
 ตัวอย่าง record:
   10.1.5.23:51544 → 52.108.10.5:443 TCP  in=Gi0/1 out=Gi0/0  pkts=18,400  bytes=24.3MB  10:00:05–10:01:05  flags=.AP.S.
```
- Flow **ทิศทางเดียว** (unidirectional) — conversation หนึ่งมี 2 flow (ไปและกลับ) ใน NetFlow/IPFIX ส่วนใหญ่
- **ไม่มี payload** → ไม่เห็นเนื้อหา (แต่ยังเป็นข้อมูลอ่อนไหว — ใครคุยกับใคร)

---

## 3. มาตรฐาน/รูปแบบ

| รูปแบบ | ลักษณะ |
|---|---|
| **NetFlow v5** | Cisco ดั้งเดิม, field คงที่, **IPv4 เท่านั้น**, ไม่มี template |
| **NetFlow v9** | **template-based** — กำหนด field ได้, รองรับ IPv6/MPLS |
| **IPFIX (RFC 7011)** ⭐ | มาตรฐาน IETF พัฒนาจาก v9 (บางครั้งเรียก NetFlow v10) — ยืดหยุ่น, รองรับ field ของ vendor, ข้อความความยาวแปรผัน |
| **Flexible NetFlow (FNF)** | การตั้งค่าบน Cisco ที่กำหนด record/exporter/monitor เองได้ ส่งเป็น v9/IPFIX |
| **sFlow** | **sampling ของ packet header** (เช่น 1 ใน 1000) + **counter sampling** — stateless, เบา, เหมาะกับ switch ความเร็วสูง (Arista, Juniper, Aruba, Dell, HPE) |
| J-Flow, NetStream, cflowd | ชื่อของผู้ผลิตอื่น (คล้าย NetFlow) |
| Cloud flow logs | AWS/Azure/GCP VPC Flow Logs (Level 78) — แนวคิดเดียวกัน |

### NetFlow/IPFIX vs sFlow
| | NetFlow/IPFIX | sFlow |
|---|---|---|
| ทำงาน | อุปกรณ์สร้าง **flow cache** รวม packet เป็น flow แล้วส่งเมื่อ flow จบ/timeout | **สุ่ม packet** ส่ง header ไปทันที collector รวมเอง |
| โหลดอุปกรณ์ | ใช้ memory/CPU (cache) | น้อย (ทำใน ASIC) |
| ความแม่นยำ | สูง (ถ้าไม่ sample) | ประมาณการทางสถิติ — แม่นสำหรับ traffic ปริมาณมาก |
| เวลา | รอ timeout (ล่าช้า) | **ใกล้ real-time** (ดีสำหรับตรวจ DDoS) |
| เห็น L2 | จำกัด | เห็น header ดิบ (MAC, VLAN) |

---

## 4. สถาปัตยกรรม

```
 [Router/FW/Switch: Exporter] ──UDP 2055/9995/4739 (IPFIX)/6343 (sFlow)──► [Collector]
                                                                          │ เก็บ (nfcapd, ClickHouse, Elastic)
                                                                          ▼
                                                                     [Analyzer/UI]
                                                                     dashboard, query, alert
```
- **Exporter:** อุปกรณ์ที่สร้างและส่ง flow — เลือกจุดที่เห็น traffic สำคัญ (WAN edge, internet edge, DC border, core)
- **Collector:** รับและเก็บ — ต้องรองรับ **flow/วินาที** ที่เข้ามา (ระวัง UDP drop)
- **Analyzer:** ตีความ เพิ่มบริบท (enrichment): ชื่อ host (DNS), ชื่อ site/interface (จาก SNMP/NetBox), **ASN/ประเทศ** (GeoIP), ชื่อแอป

### เครื่องมือ
| เครื่องมือ | ลักษณะ |
|---|---|
| **nfdump/nfcapd (+ nfsen)** | CLI open source คลาสสิก ทรงพลัง |
| **pmacct** | collector ยืดหยุ่น (NetFlow/IPFIX/sFlow + BGP) ส่งไป DB/Kafka |
| **Akvorado** ⭐ | open source สมัยใหม่ (ClickHouse) enrichment ด้วย BGP/GeoIP/SNMP, UI ดี |
| **ntopng** | UI ใช้ง่าย, เห็น host/app |
| ElastiFlow | ส่งเข้า Elastic/OpenSearch |
| Kentik, Plixer Scrutinizer, SolarWinds NTA, ManageEngine NetFlow Analyzer, PRTG | เชิงพาณิชย์ |
| softflowd, nprobe, yaf | สร้าง flow จาก Linux/mirror port (เมื่ออุปกรณ์ส่งเองไม่ได้) |

---

## 5. ตั้งค่า Flexible NetFlow บน Cisco IOS-XE

```
flow record FR-IPV4
 match ipv4 source address
 match ipv4 destination address
 match transport source-port
 match transport destination-port
 match ipv4 protocol
 match ipv4 tos
 match interface input
 collect interface output
 collect counter bytes long
 collect counter packets long
 collect transport tcp flags
 collect timestamp absolute first
 collect timestamp absolute last
 collect routing next-hop address ipv4
!
flow exporter FE-COLLECTOR
 destination 10.0.0.60
 source Loopback0                 ! IP คงที่ — collector ใช้ระบุอุปกรณ์
 transport udp 2055
 export-protocol ipfix
 template data timeout 60
 option interface-table           ! ส่งชื่อ interface (ifIndex → ชื่อ)
!
flow monitor FM-IPV4
 record FR-IPV4
 exporter FE-COLLECTOR
 cache timeout active 60          ! flow ยาวส่งทุก 60 วินาที
 cache timeout inactive 15        ! flow ที่เงียบ 15 วินาทีถือว่าจบ
!
interface GigabitEthernet0/0/0
 description WAN-ISP1
 ip flow monitor FM-IPV4 input
 ip flow monitor FM-IPV4 output
```
```
show flow monitor FM-IPV4 cache format table | head
show flow exporter statistics
show flow monitor FM-IPV4 statistics
```
### Active/Inactive timeout
- **Active timeout** (เช่น 60 วินาที): flow ที่ยังทำงานยาว (ดาวน์โหลดใหญ่) จะถูกส่งออกเป็นระยะ → ไม่อย่างนั้นกราฟจะเห็นข้อมูลก้อนใหญ่ตอนจบเท่านั้น (spike ปลอม)
- **Inactive timeout** (เช่น 15 วินาที): flow ที่ไม่มี packet ถือว่าจบ
- ค่าเริ่มต้นบางรุ่น active = 30 นาที → **ปรับเป็น 60 วินาที** สำหรับกราฟที่แม่นยำ

### sFlow บน switch (ตัวอย่างแนวคิด — syntax ต่างตามยี่ห้อ)
```
sflow sample 4096                  ! 1:4096 สำหรับพอร์ต 10G+
sflow polling-interval 30
sflow destination 10.0.0.60 6343
sflow source-interface Loopback0
sflow run
```

---

## 6. Sampling

```
 Sampling 1:1000 → วิเคราะห์ 1 ใน 1000 packet แล้วคูณกลับ (× 1000)
```
| ผล | อธิบาย |
|---|---|
| ✅ ลดโหลด CPU/memory/ปริมาณ export | จำเป็นบนลิงก์ 10/100G |
| ✅ แม่นยำสำหรับ **traffic ปริมาณมาก** (top talkers, DDoS) | สถิติของ sample จำนวนมาก |
| ❌ **flow เล็ก/สั้นอาจไม่ถูกเห็นเลย** | ไม่เหมาะกับ forensics ที่ต้องเห็นทุกการเชื่อมต่อ (เช่น beaconing ของ malware) |
| ⚠️ ต้องตั้ง sampling rate ให้ collector รู้ | ไม่เช่นนั้นตัวเลขเล็กกว่าจริง 1000 เท่า |
**แนวทาง:** edge/WAN ความเร็วต่ำ → unsampled (1:1) ถ้าอุปกรณ์รับไหว · DC/core 10–100G → 1:1000–1:8192 (sFlow)

---

## 7. Use Cases

### ① Top Talkers / Top Apps
```bash
nfdump -R /var/cache/nfdump/router1/2026/11/23 -s srcip/bytes -n 10          # top 10 src IP ตาม bytes
nfdump -R ... -s dstport/bytes -n 10 'net 10.1.0.0/16'                       # port ปลายทางยอดนิยมของสาขา
nfdump -R ... -s record/bytes -n 20 -o "fmt:%ts %sa %da %dp %pr %byt"        # conversation ใหญ่สุด
nfdump -R ... 'src ip 10.1.5.23 and dst port 443' -o long                    # รายละเอียดของ host
```
### ② Capacity Planning
- แยก traffic ตาม **แอป/ปลายทาง/ASN** → รู้ว่าโตเพราะอะไร (Microsoft 365? backup? video?)
- ตัดสินใจ: เพิ่ม bandwidth vs ใช้ local breakout (SD-WAN — Level 60) vs QoS vs ย้าย backup ไปกลางคืน
- ร่วมกับ 95th percentile ของ SNMP (Level 86) และ forecast (Level 94)

### ③ ตรวจจับ DDoS / Anomaly
| สัญญาณ | อาจหมายถึง |
|---|---|
| pps/bps ไป **IP ปลายทางเดียว** พุ่ง จาก src จำนวนมาก | volumetric DDoS (Level 70) |
| UDP src port 53/123/11211/1900 ปริมาณมากเข้ามา | reflection/amplification |
| TCP SYN จำนวนมากโดยไม่มี ACK | SYN flood |
| host ภายในเชื่อมต่อ **หลาย IP/port** ในเวลาสั้น | scanning/worm |
| ภายในส่งข้อมูลออกปริมาณผิดปกติไปปลายทางที่ไม่รู้จัก | data exfiltration |
| การเชื่อมต่อออกสม่ำเสมอทุก N วินาที ขนาดเท่ากัน | C2 beaconing (ต้องใช้ unsampled) |
- เครื่องมือ: FastNetMon (ตรวจ DDoS จาก flow/sFlow และสั่ง **RTBH/FlowSpec** อัตโนมัติ — Level 70), Kentik, NDR (Level 64)

### ④ Security Forensics
"เครื่องที่ติด malware คุยกับ IP ใดบ้างใน 30 วันที่ผ่านมา" → flow ตอบได้แม้ไม่มี pcap (ต้องเก็บ unsampled/ย้อนหลังนานพอ) → ส่ง flow เข้า SIEM (Level 68)

### ⑤ Billing / Chargeback, Peering Analysis
แยกค่าใช้จ่ายตามแผนก/ลูกค้า · ISP ดูว่า traffic ไป AS ไหนมาก → ตัดสินใจ peering (Level 49)

---

## 8. Enrichment ที่ทำให้ Flow มีความหมาย

| ข้อมูลดิบ | Enrich เป็น |
|---|---|
| 52.108.10.5 | **AS8075 Microsoft** / ประเทศ / hostname |
| ifIndex 3 | **Gi0/0/0 "WAN-ISP1"** (จาก SNMP/option template) |
| 10.1.5.23 | **PC-ACC-023, ฝ่ายบัญชี, site BKK** (จาก DNS/DHCP/NetBox/NAC) |
| port 443 | แอป (ต้องมี NBAR/AVC/DPI หรือ SNI เพื่อแยก Teams/YouTube) |
- **NBAR2/AVC (Cisco), App-ID (Palo Alto)** ส่ง field ชื่อแอปใน IPFIX ได้

---

## 9. ความเป็นส่วนตัวและธรรมาภิบาล

flow บอก "ใครเข้าเว็บ/บริการใด เมื่อไร" = **ข้อมูลส่วนบุคคล** ในบริบท PDPA
- กำหนดวัตถุประสงค์ (security/capacity), จำกัดผู้เข้าถึง, ระยะเวลาเก็บ (retention), แจ้งพนักงานตามนโยบาย
- ส่ง flow บนเครือข่าย management ที่แยก/เข้ารหัสเมื่อจำเป็น

---

## 10. Troubleshooting

| อาการ | ตรวจ |
|---|---|
| Collector ไม่ได้รับข้อมูล | `show flow exporter statistics` (ส่งไหม), firewall/ACL บล็อก UDP, ที่อยู่/port ผิด, tcpdump ที่ collector `udp port 2055` |
| ได้แต่ decode ไม่ได้ | ยังไม่ได้รับ **template** (v9/IPFIX ส่ง template เป็นระยะ — รอ/ลด template timeout) |
| ตัวเลขน้อยกว่า SNMP มาก | sampling rate ไม่ถูกตั้ง/ไม่ถูกส่งให้ collector, เปิด monitor แค่ทิศเดียว |
| ตัวเลขมากกว่าจริง (ซ้ำ) | เปิดทั้ง input และ output บนหลาย interface ใน path เดียวกัน (นับซ้ำ) → นับเฉพาะ ingress หรือ dedupe |
| กราฟมี spike แปลก | active timeout ยาวเกิน |
| CPU อุปกรณ์สูงหลังเปิด | ใช้ sampling, ลด field, ใช้ hardware NetFlow |

---

## 11. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| Flow เก็บเนื้อหา packet | มีแค่ metadata (ไม่มี payload) |
| sFlow กับ NetFlow เหมือนกัน | sFlow สุ่ม packet header (stateless); NetFlow สร้าง flow cache |
| Sampling ไม่มีผลต่อความแม่นยำ | flow เล็ก/สั้นอาจไม่ถูกเห็น |
| เปิด NetFlow ทุก interface ทั้งสองทิศดีที่สุด | อาจนับซ้ำ — ออกแบบจุดเก็บให้เหมาะ |
| Flow แทน packet capture ได้ทั้งหมด | debug ระดับ protocol ยังต้องใช้ pcap |

---

## 12. Cheat Sheet

```
SNMP = เท่าไร · Flow = ใครคุยกับใคร เท่าไร · PCAP = รายละเอียดทุก byte
Flow key = 5-tuple (+ interface, ToS) · non-key = bytes, pkts, time, flags, next-hop, AS · ทิศเดียว
v5 (IPv4, คงที่) · v9 (template) · IPFIX (IETF, UDP 4739) · FNF · sFlow (sampling, UDP 6343)
Exporter → Collector → Analyzer · enrichment: ASN/GeoIP, ชื่อ interface, ชื่อ host, app
Cisco FNF: flow record → flow exporter (source Loopback, ipfix) → flow monitor (active 60/inactive 15) → interface
Sampling: ลดโหลด แม่นกับ traffic ใหญ่ · พลาด flow เล็ก · collector ต้องรู้ rate
Use: top talkers · capacity · DDoS/anomaly · forensics · billing/peering
nfdump -s srcip/bytes -n 10 · Akvorado · ntopng · pmacct · FastNetMon
PDPA: จำกัดสิทธิ์/retention
```

---

## 13. แบบทดสอบ 10 ข้อ

1. Flow, SNMP และ packet capture ตอบคำถามต่างกันอย่างไร
2. Flow record ประกอบด้วย key fields อะไรบ้าง
3. NetFlow v5 มีข้อจำกัดอะไรเมื่อเทียบกับ v9/IPFIX
4. NetFlow กับ sFlow ทำงานต่างกันอย่างไร
5. Active timeout ทำไมควรตั้งประมาณ 60 วินาที
6. Sampling 1:1000 มีผลดีและผลเสียอย่างไร
7. ใช้ flow ตรวจจับ DDoS แบบ amplification ได้อย่างไร
8. Collector ได้รับ packet แต่แสดงข้อมูลไม่ได้ สาเหตุที่เป็นไปได้คืออะไร
9. Enrichment คืออะไร ยกตัวอย่าง 2 อย่าง
10. ทำไมข้อมูล flow ต้องจัดการตาม PDPA

<details><summary><b>เฉลย</b></summary>

1. SNMP บอกปริมาณรวมต่อ interface; flow บอกใครคุยกับใครด้วยอะไรเท่าไร (metadata); packet capture เห็นรายละเอียดทุก byte รวม payload
2. Src/dst IP, src/dst port, protocol (และมักรวม ingress interface, ToS)
3. v5 มี field คงที่ รองรับ IPv4 เท่านั้น ไม่มี template; v9/IPFIX ใช้ template กำหนด field ได้ รองรับ IPv6/MPLS/field ของผู้ผลิต
4. NetFlow สร้าง flow cache รวม packet เป็น flow แล้ว export; sFlow สุ่ม packet header และ counter ส่งทันที (stateless) collector คำนวณเอง
5. ให้ flow ที่ยาวถูกส่งออกเป็นระยะ กราฟแม่นยำ ไม่เกิด spike ตอน flow จบ
6. ลดโหลดอุปกรณ์/ปริมาณข้อมูลและแม่นยำสำหรับ traffic ปริมาณมาก แต่ flow เล็ก/สั้นอาจไม่ถูกเห็น และต้องตั้ง rate ให้ collector ถูกต้อง
7. ดูปริมาณ bps/pps ที่พุ่งไปยัง IP ปลายทางเดียวจาก src จำนวนมาก โดย src port เป็น 53/123/11211/1900 ฯลฯ
8. ยังไม่ได้รับ template ของ v9/IPFIX (หรือ template ไม่ตรง) — รอหรือลด template timeout
9. การเพิ่มบริบทให้ข้อมูลดิบ เช่น แปลง IP เป็น ASN/ประเทศ, ifIndex เป็นชื่อ interface, IP ภายในเป็นชื่อเครื่อง/ฝ่าย/site
10. Flow บอกพฤติกรรมการใช้งานของบุคคล (ใครเข้าถึงอะไร เมื่อไร) จึงเป็นข้อมูลส่วนบุคคล ต้องมีวัตถุประสงค์ จำกัดผู้เข้าถึงและระยะเวลาเก็บ
</details>

---

➡️ ต่อไป: **Level 88 — SDN Concepts & Intent-Based Networking**
