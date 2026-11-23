# บทเรียน Level 13 — TCP (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจว่า TCP ส่งข้อมูลให้ครบและเรียงลำดับได้อย่างไร · 3-way handshake / การปิดการเชื่อมต่อ · Sequence/ACK · Window, Flow control, Congestion control · อ่าน TCP state และวิเคราะห์ปัญหาจาก Wireshark ได้

---

## 1. TCP คืออะไร

**TCP (Transmission Control Protocol)** คือโปรโตคอลชั้น **Transport (L4)** ที่ให้การส่งแบบ
- **Connection-oriented:** ต้องสร้างการเชื่อมต่อก่อนส่ง
- **Reliable:** รับประกันว่าข้อมูลถึง **ครบ** (หายก็ส่งใหม่)
- **Ordered:** ประกอบกลับ **ตามลำดับ** ที่ถูกต้อง
- **Flow & Congestion control:** ไม่ส่งเร็วเกินกว่าที่ผู้รับและเครือข่ายรับได้
- **Full-duplex:** สองฝั่งส่งพร้อมกันได้

**ใช้กับ:** เว็บ (HTTP/1.1, HTTP/2), อีเมล, SSH, FTP, ฐานข้อมูล, SMB, RDP — งานที่ข้อมูลต้องครบทุกไบต์

> 💡 **เปรียบเทียบ:** TCP = **ส่งพัสดุลงทะเบียนพร้อมใบตอบรับ** มีเลขลำดับทุกกล่อง ผู้รับเซ็นยืนยัน ถ้ากล่องไหนหายก็ส่งใหม่

---

## 2. TCP Header (ส่วนที่สำคัญ)

```
 ┌─────────────────┬─────────────────┐
 │ Source Port (16)│ Dest Port (16)  │
 ├─────────────────┴─────────────────┤
 │       Sequence Number (32)         │  ← ลำดับไบต์ของข้อมูลชุดนี้
 ├────────────────────────────────────┤
 │   Acknowledgment Number (32)       │  ← "ได้รับถึงไบต์นี้แล้ว ส่งไบต์ถัดไปมา"
 ├──────┬──────────┬──────────────────┤
 │ Hdr  │  Flags   │   Window (16)    │  ← พื้นที่รับที่ยังว่าง
 ├──────┴──────────┼──────────────────┤
 │ Checksum        │ Urgent Pointer   │
 ├─────────────────┴──────────────────┤
 │ Options (MSS, Window Scale, SACK, Timestamps) │
 └────────────────────────────────────┘
```

**Flags สำคัญ:** **SYN** (ขอเริ่มการเชื่อมต่อ) · **ACK** (ยืนยันการรับ) · **FIN** (ขอปิดแบบสุภาพ) · **RST** (ตัดทันที/ปฏิเสธ) · **PSH** (ส่งให้แอปทันที) · URG

---

## 3. 3-Way Handshake — การเปิดการเชื่อมต่อ

```
   Client (port 51000)                              Server (port 443)
        │  ① SYN  seq=100                                  │
        │ ────────────────────────────────────────────────► │
        │                    ② SYN+ACK  seq=300, ack=101    │
        │ ◄──────────────────────────────────────────────── │
        │  ③ ACK  seq=101, ack=301                          │
        │ ────────────────────────────────────────────────► │
        │            ESTABLISHED — เริ่มส่งข้อมูล            │
```

1. **SYN:** client ขอเชื่อมต่อ บอกเลข sequence เริ่มต้น (ISN สุ่ม)
2. **SYN-ACK:** server ตกลง บอก ISN ของตัวเอง และ ack = ISN ของ client + 1
3. **ACK:** client ยืนยัน

ระหว่าง handshake ยังแลกตัวเลือกกัน เช่น **MSS** (ขนาดข้อมูลสูงสุดต่อ segment ปกติ 1460 บน Ethernet = 1500 − 20 IP − 20 TCP), **Window Scale**, **SACK**

**ผลที่เห็นในการแก้ปัญหา**
| สิ่งที่เห็น | ความหมาย |
|---|---|
| ส่ง SYN แล้วเงียบ (ส่งซ้ำหลายครั้ง) | firewall **drop** หรือ server ไม่มีอยู่/ทางกลับไม่มี route |
| ส่ง SYN ได้ **RST** กลับทันที | port **ปิด** (ไม่มีโปรแกรมรอรับ) หรือ firewall ส่ง reject |
| ครบ 3 ขั้นแล้วตัด | ปัญหาที่แอป/TLS |

---

## 4. Sequence และ Acknowledgment — ส่งให้ครบและเรียงลำดับ

- **Sequence number** นับเป็น **ไบต์** (ไม่ใช่นับ packet)
- **ACK number** = "ไบต์ถัดไปที่ฉันคาดว่าจะได้รับ" (cumulative)

```
 Client ส่ง seq=1001 ข้อมูล 500 ไบต์ (ไบต์ 1001-1500)
 Server ตอบ ack=1501   ← ได้ครบถึง 1500 ขอ 1501 ต่อ
 Client ส่ง seq=1501 ข้อมูล 500 ไบต์
 ...
```

### เมื่อข้อมูลหาย
- **Retransmission timeout (RTO):** รอ ACK นานเกินกำหนดแล้วส่งซ้ำ
- **Fast retransmit:** ผู้รับได้ segment ที่มาข้าม จึงส่ง **ACK ซ้ำ (duplicate ACK)** ของไบต์ที่ขาด เมื่อผู้ส่งเห็น **3 duplicate ACK** ก็ส่งซ้ำทันทีโดยไม่ต้องรอ timeout
- **SACK (Selective ACK):** บอกได้ว่าได้รับช่วงไหนแล้วบ้าง ส่งซ้ำเฉพาะส่วนที่ขาด

---

## 5. Window — Flow Control

- **Receive Window (rwnd):** ผู้รับบอกผู้ส่งว่า "ฉันยังมีที่ว่างรับได้อีก X ไบต์"
- ผู้ส่งส่งได้หลาย segment ติดกันโดยไม่ต้องรอ ACK ทีละอัน (**sliding window**) ตราบที่ไม่เกิน window
- ผู้รับแอปช้า ประมวลผลไม่ทัน → window เล็กลง → ถึงขั้น **Zero Window** = ผู้ส่งต้องหยุดรอ
- **Window Scaling:** field window มี 16 บิต (สูงสุด 65,535 ไบต์) จึงต้องคูณขยายเพื่อรองรับลิงก์เร็ว/ไกล

### Bandwidth-Delay Product (BDP) — ทำไมลิงก์ไกลโหลดช้า
```
 BDP = Bandwidth × RTT = ข้อมูลที่ "ลอยอยู่บนสาย" โดยยังไม่ได้ ACK

 1 Gbps × 100 ms = 1,000,000,000 × 0.1 ÷ 8 = 12.5 MB
 → ต้องมี window ≥ 12.5 MB จึงจะใช้ลิงก์ได้เต็ม
 ถ้า window แค่ 64 KB: throughput สูงสุด = 64 KB ÷ 0.1 s ≈ 5.2 Mbps เท่านั้น!
```
นี่คือเหตุผลที่การเชื่อมต่อเดียวไปต่างประเทศมักไม่เต็มสาย และทำไม TCP tuning/window scaling สำคัญ

---

## 6. Congestion Control — ไม่ให้เครือข่ายล่ม

**Flow control** ป้องกัน **ผู้รับ** ล้น ส่วน **Congestion control** ป้องกัน **เครือข่ายกลางทาง** ล้น

- ผู้ส่งมี **congestion window (cwnd)** ของตัวเอง ส่งได้จริง = min(rwnd, cwnd)
- **Slow Start:** เริ่มส่งน้อย แล้วเพิ่มเป็นเท่าตัวทุก RTT
- **Congestion Avoidance:** เมื่อถึงเกณฑ์ เพิ่มทีละน้อย
- **เมื่อพบ packet หาย:** ลด cwnd ลง (ตีความว่าเครือข่ายแน่น)
- อัลกอริทึม: **CUBIC** (ค่าเริ่มต้นของ Linux/Windows), **BBR** (Google, วัดแบนด์วิดท์และ RTT แทนการรอ packet หาย เหมาะกับลิงก์ไกล/มี loss)

> 🔑 **ผลในงานจริง:** packet loss เพียง 1% ทำให้ throughput ของ TCP ลดลงมาก โดยเฉพาะเมื่อ RTT สูง

---

## 7. การปิดการเชื่อมต่อ

### ปิดแบบปกติ (4-way)
```
 A ── FIN ──► B        A: ฉันส่งเสร็จแล้ว
 A ◄── ACK ── B
 A ◄── FIN ── B        B: ฉันก็เสร็จแล้ว
 A ── ACK ──► B        A เข้าสถานะ TIME_WAIT ช่วงหนึ่ง แล้วปิด
```
### ปิดทันที (RST)
ตัดการเชื่อมต่อโดยไม่ต้องรอ เช่น port ปิด, แอป crash, firewall ตัด session, idle timeout

---

## 8. TCP States ที่เจอบ่อย

| State | ความหมาย | ถ้ามีจำนวนมากผิดปกติ |
|---|---|---|
| **LISTEN** | server รอรับการเชื่อมต่อ | — |
| **SYN_SENT** | ส่ง SYN แล้วรอตอบ | ปลายทางไม่ตอบ/ถูก firewall drop |
| **SYN_RECEIVED** | ได้ SYN ตอบ SYN-ACK แล้วรอ ACK | อาจถูก **SYN flood** |
| **ESTABLISHED** | เชื่อมต่อแล้ว | — |
| **TIME_WAIT** | ฝั่งที่ปิดก่อนรอช่วงหนึ่ง | ปกติบน server/proxy ที่รับงานมาก (ถ้ามากเกินอาจ port หมด) |
| **CLOSE_WAIT** | อีกฝั่งปิดแล้ว แต่ **แอปเรายังไม่ปิด socket** | **bug ในแอป** (ลืม close) |

```bash
ss -tan state established          # Linux
ss -s                              # สรุปจำนวนแต่ละ state
netstat -ano | findstr :443        # Windows
Get-NetTCPConnection -State Listen # PowerShell
```

---

## 9. วิเคราะห์ TCP ใน Wireshark

| Filter | ใช้หา |
|---|---|
| `tcp.flags.syn==1 && tcp.flags.ack==0` | SYN ทั้งหมด (การเริ่มเชื่อมต่อ) |
| `tcp.flags.reset==1` | RST (ถูกปฏิเสธ/ตัด) |
| `tcp.analysis.retransmission` | การส่งซ้ำ (บ่งบอก packet loss) |
| `tcp.analysis.duplicate_ack` | duplicate ACK |
| `tcp.analysis.zero_window` | ผู้รับรับไม่ทัน (ปัญหาที่ปลายทาง ไม่ใช่เครือข่าย) |
| `tcp.stream eq 5` | ดูการเชื่อมต่อเดียว |

เมนู **Statistics → TCP Stream Graphs** และ **Expert Information** ช่วยสรุปปัญหาได้เร็ว

**ตัวอย่างการตีความ**
- retransmission เยอะ → เครือข่ายมี loss (สาย, Wi-Fi, congestion)
- zero window เยอะ → ปลายทาง (server/client) ช้า ไม่ใช่เครือข่าย
- RTT handshake สูง → ไกล หรือคิวแน่น

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| Sequence นับเป็นจำนวน packet | นับเป็น **ไบต์** |
| TCP ช้าเพราะมี handshake อย่างเดียว | ช้าได้จาก RTT สูง + window เล็ก + loss |
| ลิงก์ 1 Gbps ทุกการเชื่อมต่อต้องได้ 1 Gbps | ถูกจำกัดด้วย window ÷ RTT และ loss |
| CLOSE_WAIT ค้างเป็นปัญหาเครือข่าย | เป็นปัญหาแอปที่ไม่ปิด socket |
| RST แปลว่าถูกโจมตี | ส่วนใหญ่คือ port ปิดหรือ timeout ตามปกติ |

---

## 11. Cheat Sheet

```
TCP = connection-oriented, reliable, ordered, flow+congestion control
Handshake: SYN → SYN/ACK → ACK · ปิด: FIN/ACK ×2 หรือ RST
SYN แล้วเงียบ = drop (firewall) · SYN แล้ว RST = port ปิด
Seq/Ack นับไบต์ · 3 dup ACK → fast retransmit · SACK ส่งซ้ำเฉพาะที่ขาด
rwnd = ผู้รับ (flow) · cwnd = เครือข่าย (congestion) · ส่งได้ = min(rwnd,cwnd)
BDP = BW × RTT · 1Gbps×100ms = 12.5MB · window 64KB/100ms ≈ 5 Mbps
CUBIC (default) · BBR (ลิงก์ไกล/มี loss)
CLOSE_WAIT ค้าง = bug แอป · TIME_WAIT = ปกติ
MSS ปกติ 1460
```

---

## 12. แบบทดสอบ 10 ข้อ

1. เรียง 3-way handshake
2. ส่ง SYN แล้วได้ RST ทันที หมายความว่าอะไร ต่างจากส่ง SYN แล้วเงียบอย่างไร
3. Sequence number นับอะไร
4. ผู้รับตอบ ack=5001 หมายความว่าอะไร
5. Fast retransmit ทำงานเมื่อใด
6. Flow control กับ Congestion control ต่างกันอย่างไร
7. ลิงก์ 100 Mbps, RTT 200 ms ต้องการ window ประมาณเท่าไรจึงใช้ได้เต็ม
8. server มี CLOSE_WAIT หลายพันรายการ สาเหตุคืออะไร
9. Wireshark พบ zero window จำนวนมาก ปัญหาอยู่ที่เครือข่ายหรือปลายทาง
10. MSS ปกติบน Ethernet เท่าไร คำนวณอย่างไร

<details><summary><b>เฉลย</b></summary>

1. SYN → SYN-ACK → ACK
2. RST = port ปิด/ถูก reject ทันที; เงียบ = ถูก drop (firewall) หรือปลายทาง/ทางกลับไม่มี
3. ไบต์ของข้อมูล
4. ได้รับครบถึงไบต์ 5000 แล้ว ขอไบต์ 5001 ต่อ
5. ผู้ส่งได้ duplicate ACK 3 ครั้ง
6. Flow = ป้องกันผู้รับล้น (rwnd); Congestion = ป้องกันเครือข่ายล้น (cwnd)
7. 100,000,000 × 0.2 ÷ 8 = 2.5 MB
8. แอปไม่ปิด socket หลังอีกฝั่งปิดแล้ว (bug ในแอป)
9. ปลายทาง — ผู้รับประมวลผลไม่ทัน
10. 1460 = MTU 1500 − IP header 20 − TCP header 20
</details>

---

➡️ ต่อไป: **Level 14 — UDP & Port Numbers**
