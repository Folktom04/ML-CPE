# บทเรียน Level 54 — QoS (Quality of Service) (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจว่าทำไมต้องมี QoS และมันช่วยเมื่อไร · Classification & Marking (CoS, DSCP) · Trust boundary · Queuing (LLQ/CBWFQ) · Policing vs Shaping · WRED · ตั้งค่า MQC บน Cisco และ tc บน Linux · ออกแบบ QoS สำหรับ voice/video

---

## 1. ทำไมต้องมี QoS

เครือข่ายส่งทุก packet แบบ **best effort** (มาก่อนส่งก่อน) — เมื่อลิงก์ **แน่น (congestion)** packet ต้องรอคิวหรือถูกทิ้ง ซึ่งกระทบแอปแต่ละแบบต่างกัน

| แอป | ทนต่ออะไรได้ | ต้องการ |
|---|---|---|
| **Voice (VoIP)** | ทน loss เล็กน้อย, **ไม่ทน delay/jitter** | bandwidth น้อยแต่ **ต้องได้ก่อนเสมอ** |
| **Video conference** | ทน loss น้อย, ไม่ทน delay | bandwidth ปานกลาง–สูง, latency ต่ำ |
| **แอปธุรกิจ (ERP, HIS)** | ทน delay ได้บ้าง | ไม่ควรช้าเมื่อมีคนดาวน์โหลด |
| **Bulk (backup, update, ดาวน์โหลด)** | ทน delay ได้มาก (TCP ส่งซ้ำได้) | ได้ bandwidth ที่เหลือ |
| Scavenger (YouTube/เกม/P2P) | อะไรก็ได้ | ได้น้อยที่สุด |

**เกณฑ์สำหรับ voice (ITU-T G.114 และแนวปฏิบัติทั่วไป):** one-way latency **< 150 ms**, jitter **< 30 ms**, loss **< 1%**

> 🔑 **QoS ไม่ได้สร้าง bandwidth เพิ่ม** — มันแค่ **จัดลำดับว่าใครได้ก่อน/ใครถูกทิ้งก่อน** เมื่อเกิด congestion
> **ถ้าลิงก์ไม่เคยแน่น QoS ก็ไม่มีผลอะไร** (ไม่มีคิวให้จัดลำดับ) · และถ้าลิงก์แน่นตลอดเวลา → ต้องเพิ่ม bandwidth ไม่ใช่แค่ทำ QoS

**จุดที่มักเกิด congestion:** WAN/อินเทอร์เน็ต (ลิงก์ช้ากว่า LAN มาก), uplink ที่ oversubscribe, จุดที่ความเร็วลดลง (10G → 1G), Wi-Fi

---

## 2. ขั้นตอนของ QoS

```
 ① Classification  → แยกว่า packet นี้คือ traffic ประเภทไหน (ACL, NBAR/DPI, port, DSCP เดิม)
 ② Marking         → แปะป้ายความสำคัญ (DSCP/CoS) ให้อุปกรณ์ถัดไปรู้โดยไม่ต้องแยกใหม่
 ③ Policing        → จำกัดอัตรา: เกินแล้วทิ้ง/ลดความสำคัญ
 ④ Queuing         → จัดคิวตอนลิงก์แน่น (ใครได้ก่อน ได้เท่าไร)
 ⑤ Congestion Avoidance (WRED) → ทิ้ง packet ความสำคัญต่ำล่วงหน้าก่อนคิวเต็ม
 ⑥ Shaping         → ส่งไม่ให้เกินอัตราที่กำหนด (หน่วงส่วนเกินไว้)
```

---

## 3. Marking: CoS และ DSCP

| | **CoS (Class of Service)** | **DSCP (Differentiated Services Code Point)** |
|---|---|---|
| ชั้น | **L2** — อยู่ใน **802.1Q tag** (PCP 3 บิต) | **L3** — อยู่ใน **IP header** (6 บิตของ ToS/Traffic Class) |
| ค่า | 0–7 | 0–63 |
| อยู่รอดข้าม router | ❌ (tag หายเมื่อผ่าน router/ลิงก์ access) | ✅ ไปตลอดเส้นทาง (ถ้าไม่ถูก remark) |
| ใช้ | ภายใน switch/trunk | **end-to-end (มาตรฐานหลัก)** |

### DSCP ที่ต้องจำ (แนวทางตาม RFC 4594)
| DSCP | ชื่อ | ค่า | ใช้กับ | CoS |
|---|---|---|---|---|
| **EF** | Expedited Forwarding | **46** | **Voice (เสียง)** | 5 |
| **AF41** | Assured Forwarding 4,1 | **34** | **Video conference** | 4 |
| CS5 | Class Selector 5 | 40 | Signaling เสียง (บางแนวใช้ CS3) | 5 |
| **CS3** | | 24 | **Call signaling (SIP)** | 3 |
| AF31 | | 26 | Multimedia streaming | 3 |
| AF21 | | 18 | **แอปธุรกิจสำคัญ (transactional)** | 2 |
| AF11 | | 10 | Bulk data | 1 |
| **CS6** | | 48 | **Network control (OSPF, BGP)** | 6 |
| CS1 | | 8 | **Scavenger** (ต่ำกว่า best effort) | 1 |
| **0 (DF/BE)** | Default | 0 | **Best effort (ทุกอย่างที่ไม่ได้จัด)** | 0 |

**AFxy:** x = class (1–4 ยิ่งสูงยิ่งสำคัญ), y = drop precedence (1–3 ยิ่งสูงยิ่งถูกทิ้งก่อนเมื่อแน่น)

---

## 4. Trust Boundary — เชื่อ marking ของใคร

ถ้าเชื่อ DSCP ที่เครื่องผู้ใช้แปะมาทั้งหมด → ผู้ใช้ตั้ง EF ให้ BitTorrent ได้ → แย่ง queue ของเสียง

**Trust boundary** = จุดที่เริ่มเชื่อ marking — **ควรอยู่ใกล้ต้นทางที่สุดที่ควบคุมได้**
```
 [PC] ── [IP Phone] ── [Access Switch] ── Distribution ── WAN
   ✗        ✓ เชื่อ phone (CoS 5 / EF)       เชื่อ DSCP ที่ access ตรวจแล้ว
   PC ที่ต่อผ่าน phone: phone remark เป็น 0
 Access switch: trust เฉพาะเมื่อพบ IP phone (ผ่าน CDP/LLDP — "conditional trust")
                พอร์ตอื่น: ไม่ trust → classify ด้วย ACL/NBAR แล้ว mark เอง
```

---

## 5. Queuing — จัดการคิวเมื่อแน่น

| วิธี | หลักการ | หมายเหตุ |
|---|---|---|
| FIFO | มาก่อนส่งก่อน | ไม่มี QoS |
| PQ (Priority Queue) | คิวสำคัญได้ก่อนเสมอ | คิวอื่นอาจไม่ได้ส่งเลย (starvation) |
| WFQ | แบ่งยุติธรรมตาม flow | อัตโนมัติ ปรับไม่ได้ละเอียด |
| **CBWFQ** | แบ่ง **bandwidth ขั้นต่ำที่รับประกัน** ต่อ class | ไม่เหมาะกับ voice (ไม่ได้ก่อนเสมอ) |
| **LLQ (Low Latency Queuing)** ⭐ | **CBWFQ + priority queue สำหรับ voice/video** โดย **จำกัดเพดาน** priority queue ไว้ | **มาตรฐานสำหรับองค์กร** |

**แนวทางการแบ่งบน WAN (ตัวอย่าง):** Voice (priority) ≤ ~33% ของลิงก์ · Video 20–30% · Business critical 15–25% · Best effort ≥ 25% · Scavenger ≤ 5%
> ⚠️ ถ้า priority queue ใหญ่เกินไป คิวอื่นจะอดอยาก จึงต้องกำหนดเพดาน (policer ในตัว)

---

## 6. Policing vs Shaping

```
 อัตราที่เข้ามา ↗↘↗↗↘ (เกินเส้นบางช่วง)
 ─────────────── เส้นที่กำหนด (เช่น 50 Mbps)

 Policing: ส่วนที่เกิน → ทิ้ง (หรือ remark ลดความสำคัญ) ทันที  → กราฟ "ตัดยอด"
 Shaping : ส่วนที่เกิน → เก็บไว้ใน buffer แล้วค่อยส่ง         → กราฟ "เรียบ" แต่มี delay เพิ่ม
```
| | Policing | Shaping |
|---|---|---|
| ส่วนเกิน | ทิ้ง/remark | หน่วงไว้ (buffer) |
| เพิ่ม delay | ไม่ | ใช่ |
| TCP | ทำให้ส่งซ้ำ (ไม่ราบรื่น) | ราบรื่นกว่า |
| ทิศทาง | in หรือ out | **out เท่านั้น** |
| ใช้ที่ | ISP บังคับตามสัญญา, จำกัด guest/scavenger ขาเข้า | **ฝั่งลูกค้าก่อนส่งเข้า ISP** |

### ทำไมต้อง Shape ก่อนส่งเข้า WAN
ลิงก์ Ethernet ไป ISP เป็น 1 Gbps แต่ซื้อบริการ 100 Mbps → router คิดว่ามี 1G จึงไม่มีคิว (QoS ไม่ทำงาน) แล้ว **ISP ทิ้ง packet ส่วนเกินแบบสุ่ม** (ไม่สนใจว่าเป็นเสียง)
→ **Shape ที่ 100 Mbps** ทำให้คิวเกิดที่ router ของเรา → LLQ ทำงาน → เราเป็นผู้เลือกว่าทิ้งอะไร (**hierarchical QoS: shaper + child policy LLQ**)

---

## 7. Congestion Avoidance: WRED

เมื่อคิวเต็ม จะทิ้ง packet ท้ายคิวทั้งหมด (**tail drop**) → TCP ทุก session ลดความเร็วพร้อมกันแล้วเร่งพร้อมกัน (**TCP global synchronization**) → ใช้ลิงก์ได้ไม่เต็ม
**WRED (Weighted Random Early Detection)** สุ่มทิ้ง packet **ความสำคัญต่ำก่อน** ตั้งแต่คิวเริ่มแน่น ให้ TCP บาง session ชะลอก่อน · **ห้ามใช้กับคิว voice** (UDP ไม่ชะลอตาม)

---

## 8. ตั้งค่า QoS บน Cisco (MQC)

**MQC = Modular QoS CLI**: `class-map` (แยก) → `policy-map` (ทำอะไร) → `service-policy` (ผูกกับ interface)

```
! 1) Classification
class-map match-any VOICE
 match dscp ef
class-map match-any VIDEO
 match dscp af41
class-map match-any SIGNALING
 match dscp cs3
class-map match-any BUSINESS
 match dscp af21
class-map match-any SCAVENGER
 match dscp cs1
!
! 2) Policy สำหรับลิงก์ WAN (child)
policy-map WAN-QUEUING
 class VOICE
  priority percent 20                      ! LLQ (มีเพดานในตัว)
 class VIDEO
  bandwidth percent 25
 class SIGNALING
  bandwidth percent 5
 class BUSINESS
  bandwidth percent 20
  random-detect dscp-based                 ! WRED
 class SCAVENGER
  bandwidth percent 1
 class class-default
  fair-queue
  random-detect
!
! 3) Shaper ตามอัตราที่ซื้อจาก ISP (parent)
policy-map WAN-SHAPE-100M
 class class-default
  shape average 95000000                   ! ~95% ของ 100 Mbps เผื่อ overhead
  service-policy WAN-QUEUING
!
interface GigabitEthernet0/0
 service-policy output WAN-SHAPE-100M
!
show policy-map interface GigabitEthernet0/0    ! ดู packet ต่อ class, drops, queue depth
```

### Marking ที่ access (ตัวอย่าง)
```
class-map match-any TEAMS-MEDIA
 match access-group name TEAMS-UDP                 ! หรือ match protocol (NBAR)
policy-map ACCESS-MARKING
 class TEAMS-MEDIA
  set dscp af41
interface range Gi1/0/1-46
 service-policy input ACCESS-MARKING
```

### Linux (tc)
```bash
tc qdisc add dev eth0 root cake bandwidth 95mbit diffserv4      # CAKE: shaping + จัดลำดับตาม DSCP อัตโนมัติ
tc -s qdisc show dev eth0
```

### Wi-Fi: WMM
802.11e/**WMM** มี 4 access category: **Voice, Video, Best effort, Background** — map จาก DSCP ให้ถูกต้องบน WLC/AP

---

## 9. ออกแบบ QoS end-to-end

1. **กำหนด class** ขององค์กร (4, 8 หรือ 12 class — เริ่มจาก 4–5 class ก็พอ)
2. **Marking ใกล้ต้นทาง** + กำหนด trust boundary
3. **Queuing ทุกจุดที่อาจแน่น** (WAN, uplink, Wi-Fi)
4. **Shape** ที่ขอบ WAN ตามอัตราที่ซื้อ
5. ตรวจว่า **ISP/MPLS รักษา DSCP** หรือ map เข้าคลาสของ ISP (MPLS มักมี 3–6 class)
6. **อินเทอร์เน็ตไม่รักษา DSCP** — QoS ควบคุมได้แค่ขาออกจากเรา (ขาเข้าควบคุมได้จำกัด — ดู bandwidth management ใน ISC Level 18)
7. **วัดผล:** MOS ของการโทร, jitter/loss, drops ต่อ class

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| QoS ทำให้เน็ตเร็วขึ้น | จัดลำดับเมื่อแน่นเท่านั้น ไม่เพิ่ม bandwidth |
| ตั้ง QoS บน interface 1G ที่ซื้อเน็ต 100M ก็พอ | ต้อง shape ที่ 100M ก่อน ไม่งั้นไม่มีคิวที่เรา |
| CoS อยู่ได้ตลอดเส้นทาง | CoS อยู่ใน 802.1Q tag หายเมื่อผ่าน router — ใช้ DSCP end-to-end |
| ให้ voice priority 100% ได้ | priority queue ต้องมีเพดาน ไม่งั้นคิวอื่นอดอยาก |
| อินเทอร์เน็ตเคารพ DSCP ของเรา | ไม่รับประกัน |

---

## 11. Cheat Sheet

```
QoS = จัดลำดับเมื่อ congestion · ไม่เพิ่ม bandwidth · voice: delay<150ms jitter<30ms loss<1%
Classify → Mark → Police → Queue → WRED → Shape
CoS (L2, 802.1Q, 0-7) · DSCP (L3, 0-63, end-to-end)
EF 46 voice · AF41 34 video · CS3 24 signaling · AF21 18 business · CS6 48 routing · CS1 8 scavenger · 0 BE
Trust boundary ใกล้ต้นทาง (trust IP phone, ไม่ trust PC)
LLQ = priority (มีเพดาน) + CBWFQ · WRED กันความแน่น (ไม่ใช้กับ voice)
Policing ทิ้ง/remark · Shaping หน่วง (out) · Shape ที่อัตรา ISP + child LLQ
MQC: class-map → policy-map → service-policy output · show policy-map interface
Wi-Fi WMM: Voice/Video/BE/Background · Linux: tc cake
```

---

## 12. แบบทดสอบ 10 ข้อ

1. QoS ช่วยได้เมื่อใด และไม่ช่วยเมื่อใด
2. เกณฑ์ latency, jitter, loss สำหรับ voice
3. CoS กับ DSCP ต่างกันอย่างไร ทำไมใช้ DSCP เป็นหลัก
4. DSCP ของ voice และ video conference คืออะไร (ชื่อและค่า)
5. Trust boundary คืออะไร ควรอยู่ที่ใด
6. LLQ ต่างจาก CBWFQ อย่างไร ทำไม priority queue ต้องมีเพดาน
7. Policing กับ Shaping ต่างกันอย่างไร
8. ทำไมต้อง shape ก่อนส่งเข้า WAN ที่ซื้อบริการต่ำกว่าความเร็ว interface
9. WRED แก้ปัญหาอะไร และไม่ควรใช้กับ class ใด
10. ลำดับ MQC 3 ขั้นตอน และคำสั่งดูผล

<details><summary><b>เฉลย</b></summary>

1. ช่วยเมื่อเกิด congestion (จัดลำดับ/เลือกทิ้ง); ไม่ช่วยเมื่อลิงก์ไม่แน่น และแก้ไม่ได้ถ้าลิงก์แน่นตลอด (ต้องเพิ่ม bandwidth)
2. Latency (ทางเดียว) < 150 ms, jitter < 30 ms, loss < 1%
3. CoS อยู่ใน 802.1Q tag (L2) หายเมื่อผ่าน router; DSCP อยู่ใน IP header (L3) อยู่ตลอดเส้นทาง จึงใช้ end-to-end
4. Voice = EF (46), Video conference = AF41 (34)
5. จุดที่เริ่มเชื่อ marking — ใกล้ต้นทางที่สุดที่ควบคุมได้ (access switch/IP phone) ไม่เชื่อ PC
6. LLQ เพิ่ม priority queue ที่ส่งก่อนเสมอให้ voice/video; ต้องมีเพดานเพื่อไม่ให้คิวอื่นอดอยาก (starvation)
7. Policing ทิ้ง/remark ส่วนเกินทันที; Shaping เก็บส่วนเกินไว้ใน buffer แล้วค่อยส่ง (ขาออกเท่านั้น เพิ่ม delay)
8. ให้คิวเกิดที่ router ของเรา (ซึ่งรู้จัก class) แทนที่ ISP จะทิ้ง packet แบบสุ่ม — QoS ของเราจึงทำงาน
9. Tail drop และ TCP global synchronization — ไม่ควรใช้กับ voice (UDP)
10. class-map → policy-map → service-policy (ผูกกับ interface) — `show policy-map interface <X>`
</details>

---

➡️ ต่อไป: **Level 55 — NTP, Syslog, SNMP**
