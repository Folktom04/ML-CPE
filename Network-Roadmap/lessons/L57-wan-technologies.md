# บทเรียน Level 57 — WAN Technologies (ฉบับละเอียด)

> อ่านจบแล้วจะ: รู้จักบริการ WAN ทุกแบบ (Leased line, MPLS, Metro Ethernet, Broadband, 4G/5G, ดาวเทียม, Internet VPN) · เข้าใจ SLA และคำนวณ availability · topology hub-and-spoke vs mesh · MTU/MSS กับ PPPoE/VPN · DMVPN · เลือก WAN ให้เหมาะกับสาขาแต่ละแบบ

---

## 1. WAN คืออะไร

**WAN (Wide Area Network)** เชื่อมเครือข่ายที่อยู่ไกลกัน (สำนักงานใหญ่ ↔ สาขา ↔ data center ↔ cloud) โดย **องค์กรไม่ได้เป็นเจ้าของสาย** ต้อง **เช่าบริการจากผู้ให้บริการ (Service Provider/ISP/Telco)**

ศัพท์
- **CPE (Customer Premises Equipment)** — อุปกรณ์ที่ไซต์ลูกค้า (router/firewall/ONT)
- **Demarcation point (Demarc)** — จุดแบ่งความรับผิดชอบระหว่างผู้ให้บริการกับลูกค้า
- **Local loop / Last mile** — ช่วงสายจากผู้ให้บริการถึงอาคารลูกค้า
- **CE / PE / P** (ใน MPLS) — Customer Edge / Provider Edge / Provider core

---

## 2. บริการ WAN แต่ละแบบ

### 2.1 Leased Line (Private Line / Dedicated)
- ลิงก์ **ส่วนตัวจุดต่อจุด** ระหว่าง 2 สถานที่ ความเร็วคงที่ ใช้คนเดียว
- ✅ เสถียร ปลอดภัย latency คงที่ · ❌ แพง เชื่อมได้แค่ 2 จุด
- ปัจจุบันมักให้บริการผ่านไฟเบอร์/Metro Ethernet แทนวงจรแบบเก่า (E1/T1, SDH)

### 2.2 MPLS L3VPN ⭐ (WAN องค์กรแบบดั้งเดิม)
```
 สาขา A [CE] ── [PE] ═══ MPLS core ของผู้ให้บริการ ═══ [PE] ── [CE] สำนักงานใหญ่
 สาขา B [CE] ── [PE] ═══         (P routers)       ═══ [PE] ── [CE] สาขา C
```
- ผู้ให้บริการสร้าง **เครือข่ายส่วนตัวเสมือน (VPN) ให้ลูกค้าแต่ละราย** แยกกันด้วย **VRF** บน PE
- CE แลก route กับ PE ด้วย **static/BGP/OSPF** → ทุกสาขาคุยกันได้ (any-to-any)
- ✅ **SLA** (latency/jitter/loss/availability), **QoS class** (รองรับ voice/video), ไม่ผ่านอินเทอร์เน็ต, ผู้ให้บริการดูแล routing ระหว่างสาขา
- ❌ **แพง** ต่อ Mbps, ติดตั้งนาน (หลายสัปดาห์), เปลี่ยน bandwidth ช้า, ผูกกับผู้ให้บริการรายเดียว
- (รายละเอียด MPLS/VRF/RD/RT อยู่ใน Level 97)

### 2.3 Metro Ethernet / Carrier Ethernet
- บริการ **Ethernet (L2)** ข้ามเมือง/ประเทศ ส่งมอบเป็นพอร์ต Ethernet ธรรมดา
- **E-Line (EPL/EVPL)** — point-to-point · **E-LAN (EP-LAN/EVP-LAN, VPLS)** — หลายจุดเหมือนอยู่ switch เดียวกัน · E-Tree — hub-and-spoke
- ✅ ความเร็วสูง (100M–100G), ลูกค้าคุม routing เอง · ❌ ต้องระวัง L2 loop/broadcast ข้ามไซต์

### 2.4 Broadband Internet (FTTx, DSL, Cable)
- เน็ตไฟเบอร์ (FTTH/FTTB ผ่าน **GPON/XGS-PON**) ราคาถูก ความเร็วสูง
- ✅ ถูกมาก ติดตั้งเร็ว · ❌ **best effort** (ไม่มี SLA หรือ SLA ต่ำ), มักเป็น asymmetric, ใช้ร่วมกับผู้ใช้อื่น, ซ่อมช้ากว่า (เทียบกับบริการ enterprise)
- เชื่อมสาขาด้วย **VPN บนอินเทอร์เน็ต** (IPsec/SD-WAN)
- **Dedicated Internet Access (DIA)** = อินเทอร์เน็ตแบบองค์กร bandwidth รับประกัน symmetric มี SLA (แพงกว่า broadband)

### 2.5 4G / 5G (Cellular)
- ✅ ติดตั้งทันที ไม่ต้องลากสาย · ใช้เป็น **ลิงก์สำรอง** หรือไซต์ชั่วคราว/เคลื่อนที่
- ❌ ความเร็ว/latency แปรผัน, มักอยู่หลัง CGNAT, คิดตามปริมาณข้อมูล (บางแพ็กเกจ)

### 2.6 ดาวเทียม
- **GEO** (วงโคจรค้างฟ้า ~36,000 km): latency **600+ ms** ไม่เหมาะกับงาน interactive
- **LEO** (วงโคจรต่ำ เช่น Starlink): latency ~25–60 ms ใช้ในพื้นที่ห่างไกล/เรือ/สำรอง
- ข้อกำหนดการใช้งานในประเทศต้องตรวจกับหน่วยงานกำกับ

### 2.7 เปรียบเทียบ

| บริการ | ต้นทุน | SLA | ความเร็ว | ติดตั้ง | ใช้ที่ |
|---|---|---|---|---|---|
| Leased line | สูงมาก | สูง | คงที่ | นาน | จุดต่อจุดสำคัญ |
| **MPLS** | สูง | **สูง + QoS** | ปานกลาง | นาน | WAN หลักองค์กรเดิม, ธนาคาร |
| Metro-E | ปานกลาง–สูง | สูง | สูง | ปานกลาง | ระหว่างอาคาร/DC ในเมือง |
| DIA | ปานกลาง | ปานกลาง–สูง | สูง | ปานกลาง | อินเทอร์เน็ตหลักของ HQ/DC |
| **Broadband** | **ต่ำ** | ต่ำ (best effort) | สูง | เร็ว | สาขาเล็ก, ลิงก์ที่ 2 ของ SD-WAN |
| 4G/5G | ต่ำ–ปานกลาง | ต่ำ | แปรผัน | ทันที | สำรอง, ไซต์ชั่วคราว |
| ดาวเทียม LEO | ปานกลาง | ต่ำ | ปานกลาง | เร็ว | พื้นที่ห่างไกล |

> 💡 **แนวโน้มปัจจุบัน:** องค์กรจำนวนมากย้ายจาก MPLS ล้วน → **SD-WAN บน broadband/DIA หลายเส้น + 4G/5G สำรอง** (Level 60) หรือแบบผสม MPLS + Internet

---

## 3. SLA และ Availability

**SLA (Service Level Agreement)** — ข้อตกลงคุณภาพบริการกับผู้ให้บริการ: **availability**, latency, jitter, packet loss, **MTTR (เวลาซ่อม)**, เวลาตอบสนอง, ค่าปรับ (service credit)

### Availability → Downtime ต่อปี

| Availability | Downtime ต่อปี | ต่อเดือน (โดยประมาณ) |
|---|---|---|
| 99% | 3.65 วัน | 7.3 ชม. |
| 99.5% | 1.83 วัน | 3.65 ชม. |
| **99.9%** ("three nines") | **8.76 ชม.** | 43.8 นาที |
| **99.95%** | 4.38 ชม. | 21.9 นาที |
| **99.99%** ("four nines") | **52.6 นาที** | 4.4 นาที |
| 99.999% | 5.26 นาที | 26 วินาที |

### คำนวณ Availability ของ 2 ลิงก์
```
 ลิงก์ A 99.5% + ลิงก์ B 99.5% (คนละผู้ให้บริการ คนละเส้นทาง — ไม่มี shared fate)
 ขนาน (สำรองกัน): 1 − (0.005 × 0.005) = 1 − 0.000025 = 99.9975% ✅
 อนุกรม (ต้องผ่านทั้งคู่):  0.995 × 0.995 = 99.0%
```
> 🔑 ลิงก์ราคาถูก 2 เส้นที่เป็นอิสระต่อกัน มักได้ availability สูงกว่าลิงก์แพงเส้นเดียว — แต่ต้อง **ไม่มี shared fate** (ผู้ให้บริการต่างกัน ท่อร้อยสาย/เส้นทางต่างกัน, เข้าอาคารต่างจุด)

---

## 4. WAN Topology

| Topology | ลักษณะ | ข้อดี | ข้อเสีย |
|---|---|---|---|
| **Hub-and-spoke** | สาขาต่อเข้าศูนย์กลาง (HQ/DC) | ง่าย ควบคุม/ตรวจ traffic ที่ศูนย์กลาง ถูก | สาขาคุยกันต้องผ่าน hub (latency เพิ่ม), hub เป็นจุดเสีย |
| **Full mesh** | ทุกไซต์ต่อกันตรง | latency ต่ำสุด ทนทาน | จำนวน tunnel = n(n−1)/2 จัดการยาก |
| **Partial mesh** | ไซต์สำคัญต่อกันตรง | สมดุล | ออกแบบซับซ้อนกว่า |
| **Dynamic mesh** (DMVPN Phase 2/3, SD-WAN ADVPN) | hub-and-spoke แต่สร้าง tunnel ตรงระหว่างสาขา **เมื่อมี traffic** | ได้ข้อดีทั้งสองแบบ | ต้องใช้เทคโนโลยีเฉพาะ |

### Internet Breakout
- **Centralized (backhaul):** สาขาออกอินเทอร์เน็ตผ่าน HQ (ผ่าน firewall กลาง) — ควบคุมง่าย แต่เพิ่ม latency ไป SaaS/cloud และใช้ WAN มาก
- **Local (direct) breakout:** สาขาออกอินเทอร์เน็ตเอง — เร็วสำหรับ Microsoft 365/SaaS แต่ **ต้องมี security ที่สาขา** (NGFW ที่สาขา หรือ SSE/SASE จาก cloud)

---

## 5. MTU และ MSS บน WAN — ปัญหาที่พบบ่อยที่สุด

overhead ที่เพิ่มขึ้นบน WAN ทำให้ packet 1500 byte ใส่ไม่ได้

| เทคโนโลยี | Overhead โดยประมาณ | MTU ที่เหลือ |
|---|---|---|
| **PPPoE** (เน็ตบ้าน/broadband หลายราย) | 8 byte | **1492** |
| GRE | 24 byte | 1476 |
| IPsec (tunnel mode) | ~50–73 byte (ขึ้นกับ cipher) | ~1400–1438 |
| GRE over IPsec | ~80–100 byte | ~1400 |
| VXLAN | 50 byte | (ต้องเพิ่ม MTU ของ underlay) |

**อาการ MTU black hole:** ping ได้, เว็บบางเว็บเปิดได้บางส่วนแล้วค้าง, SSH ได้แต่ SCP ไฟล์ใหญ่ค้าง, อีเมลไฟล์แนบใหญ่ส่งไม่ได้ (เพราะ packet ใหญ่หาย และ ICMP "fragmentation needed" ถูก block — Level 12)

**แก้ด้วย TCP MSS Clamping** — router แก้ค่า MSS ใน SYN ให้เล็กลง เพื่อให้ TCP ส่ง segment ที่ใส่ใน tunnel ได้
```
interface Dialer1                       ! PPPoE
 ip mtu 1492
 ip tcp adjust-mss 1452                  ! 1492 − 40
interface Tunnel1                       ! IPsec/GRE
 ip mtu 1400
 ip tcp adjust-mss 1360                  ! 1400 − 40
```
**MSS = MTU − 40** (IPv4 20 + TCP 20) — ใช้ได้กับ TCP เท่านั้น ส่วน UDP ขนาดใหญ่ต้องพึ่ง PMTUD/fragmentation

---

## 6. DMVPN — Dynamic Multipoint VPN (Cisco)

**DMVPN** = วิธีสร้าง WAN แบบ **hub-and-spoke ที่สร้าง tunnel ระหว่างสาขาโดยอัตโนมัติ** บนอินเทอร์เน็ต — เป็นต้นแบบของ SD-WAN

องค์ประกอบ
- **mGRE (multipoint GRE)** — tunnel interface เดียวต่อได้หลายปลายทาง
- **NHRP (Next Hop Resolution Protocol)** — spoke ลงทะเบียน public IP ของตัวเองกับ hub และถาม hub ว่า spoke อื่นอยู่ที่ IP ใด (เหมือน "ARP" ของ tunnel)
- **IPsec** — เข้ารหัส tunnel
- **Routing protocol** (EIGRP/OSPF/BGP) วิ่งบน tunnel

| Phase | การทำงาน |
|---|---|
| Phase 1 | hub-and-spoke อย่างเดียว (spoke-to-spoke ผ่าน hub) |
| Phase 2 | spoke-to-spoke tunnel ตรง (ต้องไม่ summarize ที่ hub) |
| **Phase 3** | spoke-to-spoke ตรง + **hub summarize ได้** (NHRP redirect/shortcut) — scale ดีที่สุด |

---

## 7. เลือก WAN ให้เหมาะกับไซต์ (ตัวอย่าง)

| ไซต์ | ข้อกำหนด | ตัวเลือก |
|---|---|---|
| Data center / HQ | สำคัญที่สุด, bandwidth สูง | DIA 2 ผู้ให้บริการ + MPLS/Metro-E ไป DR |
| สาขาใหญ่ (โรงพยาบาลเครือข่าย, สาขาธนาคาร) | voice/video, ระบบสำคัญ | MPLS หรือ DIA + broadband ผ่าน SD-WAN |
| สาขาเล็ก/ร้านค้า | ต้นทุนต่ำ | broadband + 4G/5G สำรองผ่าน SD-WAN |
| ไซต์ชั่วคราว/ก่อสร้าง | ติดตั้งเร็ว | 5G / ดาวเทียม LEO |
| เชื่อมไป cloud | latency/ปริมาณข้อมูล | VPN บนอินเทอร์เน็ต หรือ Direct Connect/ExpressRoute (Level 79) |

---

## 8. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| MPLS เข้ารหัสข้อมูล | MPLS แยกลูกค้าด้วย VRF แต่ **ไม่ได้เข้ารหัส** — ข้อมูลอ่อนไหวควรเข้ารหัสเพิ่ม |
| ลิงก์แพงเส้นเดียวดีกว่า 2 เส้นราคาถูก | 2 เส้นที่เป็นอิสระมักได้ availability สูงกว่า |
| 2 ISP = ไม่มี shared fate แน่นอน | อาจใช้ท่อ/เสาเดียวกัน หรือเช่าโครงข่ายเดียวกัน ต้องตรวจเส้นทางจริง |
| VPN ใช้ MTU 1500 ได้ | ต้องลด MTU/MSS ตาม overhead |

---

## 9. Cheat Sheet

```
WAN = เช่าบริการผู้ให้บริการ · CPE · demarc · last mile · CE/PE/P
Leased line (จุดต่อจุด) · MPLS L3VPN (any-to-any, SLA, QoS, แพง) · Metro-E (L2: E-Line/E-LAN)
Broadband (ถูก, best effort) · DIA (อินเทอร์เน็ตองค์กร มี SLA) · 4G/5G (สำรอง) · LEO (ห่างไกล)
99.9% = 8.76 ชม./ปี · 99.99% = 52.6 นาที/ปี · ขนาน 1−(1−A)(1−B) · ระวัง shared fate
Hub-and-spoke · full mesh n(n−1)/2 · dynamic mesh (DMVPN/ADVPN)
Breakout: centralized vs local (ต้องมี security ที่สาขา/SASE)
PPPoE MTU 1492 · IPsec ~1400 · MSS = MTU − 40 · ip tcp adjust-mss
DMVPN = mGRE + NHRP + IPsec + routing · Phase 3 = spoke-to-spoke + summarize
```

---

## 10. แบบทดสอบ 10 ข้อ

1. ทำไม WAN ต้องเช่าจากผู้ให้บริการ และ demarc คืออะไร
2. ข้อดีและข้อเสียของ MPLS L3VPN
3. Broadband ต่างจาก DIA อย่างไร
4. Availability 99.9% และ 99.99% มี downtime ต่อปีเท่าไร
5. ลิงก์ 2 เส้น availability 99% และ 99.5% ใช้สำรองกัน (อิสระต่อกัน) ได้ availability รวมเท่าไร
6. Shared fate คืออะไร ยกตัวอย่างใน WAN
7. Centralized กับ local internet breakout ต่างกันอย่างไร
8. ทำไม PPPoE ต้องปรับ MSS และค่าที่เหมาะสมคือเท่าไร
9. อาการของ MTU black hole บน VPN
10. องค์ประกอบของ DMVPN และ Phase 3 มีข้อดีอย่างไร

<details><summary><b>เฉลย</b></summary>

1. องค์กรไม่ได้เป็นเจ้าของโครงข่ายระยะไกล — demarc คือจุดแบ่งความรับผิดชอบระหว่างผู้ให้บริการกับลูกค้า
2. ข้อดี: SLA, QoS, any-to-any, ไม่ผ่านอินเทอร์เน็ต, ผู้ให้บริการดูแล routing · ข้อเสีย: แพง ติดตั้งนาน เปลี่ยนช้า ผูกกับผู้ให้บริการ (และไม่ได้เข้ารหัส)
3. Broadband ราคาถูกแบบ best effort ใช้ร่วมกับผู้ใช้อื่น มักไม่ symmetric; DIA bandwidth รับประกัน symmetric และมี SLA
4. 99.9% ≈ 8.76 ชั่วโมง; 99.99% ≈ 52.6 นาที
5. 1 − (0.01 × 0.005) = 99.995%
6. สิ่งที่ดูเหมือนสำรองกันแต่เสียพร้อมกันได้ เช่น ISP 2 รายใช้ท่อร้อยสายเดียวกัน หรือเช่าโครงข่ายรายเดียวกัน
7. Centralized: สาขาออกอินเทอร์เน็ตผ่าน HQ (ควบคุมง่าย แต่ช้าและเปลือง WAN); Local: สาขาออกเอง (เร็วไป SaaS แต่ต้องมี security ที่สาขาหรือ SASE)
8. PPPoE ใช้ header 8 byte ทำให้ MTU เหลือ 1492 — MSS = 1452
9. Ping ได้แต่เว็บบางเว็บค้าง/โหลดไม่ครบ ไฟล์ใหญ่โอนไม่ได้ เพราะ packet ใหญ่หายและ ICMP frag-needed ถูกบล็อก
10. mGRE, NHRP, IPsec, routing protocol — Phase 3 ให้ spoke คุยกันตรงและ hub summarize route ได้ (scale ดี)
</details>

---

➡️ ต่อไป: **Level 58 — Site-to-Site VPN (IPsec)**
