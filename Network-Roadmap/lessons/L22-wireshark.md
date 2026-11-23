# บทเรียน Level 22 — Wireshark (ฉบับละเอียด)

> อ่านจบแล้วจะ: จับ packet ได้ถูกที่ · ใช้ capture filter และ display filter · อ่านหน้าจอ 3 ส่วน · Follow Stream · ใช้ Statistics/Expert Info หาปัญหา · วิเคราะห์ปัญหาจริง 5 แบบ

> ⚠️ จับ packet เฉพาะเครือข่ายที่ตนดูแลหรือได้รับอนุญาต เพราะ packet อาจมีข้อมูลส่วนบุคคล (PDPA) และรหัสผ่านของโปรโตคอลที่ไม่เข้ารหัส

---

## 1. Wireshark คืออะไร

**Wireshark** คือโปรแกรม **packet analyzer** ฟรีและ open-source ที่จับ packet จาก interface แล้วถอดรหัสให้เห็นทุก header ของทุกชั้น เปรียบเหมือน **กล้องเอกซเรย์ของเครือข่าย** — เมื่อทุกคนเถียงกันว่าใครผิด packet คือหลักฐานที่ชี้ขาด

**เกี่ยวข้อง:** `tshark` (CLI ของ Wireshark), `tcpdump` (Level 23), ไฟล์ **.pcap / .pcapng**

---

## 2. จับ packet ที่ไหน

Switch ส่ง frame เฉพาะพอร์ตปลายทาง การเปิด Wireshark บนเครื่องเราจึงเห็นแค่ traffic **ของเครื่องเราเอง** + broadcast/multicast

| วิธี | ใช้เมื่อ |
|---|---|
| **จับบนเครื่องที่มีปัญหาเอง** | ง่ายที่สุด (client หรือ server) |
| **SPAN / Port Mirroring** | ให้ switch สำเนา traffic จากพอร์ต/VLAN หนึ่งมาที่พอร์ตที่ต่อเครื่องจับ |
| **Network TAP** | อุปกรณ์แทรกกลางสาย ได้ทุก packet แม่นยำ ใช้ในงาน production/security |
| **จับบนอุปกรณ์เครือข่าย** | Firewall/router หลายรุ่นจับเป็น pcap ได้ (FortiGate `diagnose sniffer`, Palo Alto, Cisco EPC) |
| **จับ 2 จุดพร้อมกัน** | เทียบว่า packet หายตรงไหน (เช่น ก่อนและหลัง firewall) |

```
 Cisco SPAN:
 monitor session 1 source interface Gi1/0/10 both
 monitor session 1 destination interface Gi1/0/48
```

---

## 3. หน้าจอ Wireshark 3 ส่วน

```
 ┌──────────────────────────────────────────────────────────────────┐
 │ [Display filter: tcp.port == 443                         ] Apply │
 ├──────────────────────────────────────────────────────────────────┤
 │ ① Packet List  No. Time  Source  Destination  Protocol  Info     │ ← 1 บรรทัด = 1 packet
 ├──────────────────────────────────────────────────────────────────┤
 │ ② Packet Details                                                  │ ← แยกทีละชั้น
 │   > Frame 42: 74 bytes                                            │   (L1 ข้อมูลการจับ)
 │   > Ethernet II, Src: ..., Dst: ...                               │   (L2)
 │   > Internet Protocol Version 4, Src: ..., Dst: ...               │   (L3)
 │   > Transmission Control Protocol, Src Port: ..., Dst Port: 443   │   (L4)
 │   > Transport Layer Security                                      │   (L5-7)
 ├──────────────────────────────────────────────────────────────────┤
 │ ③ Packet Bytes  0000  00 1a 2b 3c 4d 5e ...  (hex + ASCII)        │
 └──────────────────────────────────────────────────────────────────┘
```
คลิก field ใดใน ② จะไฮไลต์ไบต์ที่ตรงกันใน ③ · **คลิกขวาที่ field → Apply as Filter** ได้ filter ทันที (วิธีเรียนรู้ชื่อ field ที่เร็วที่สุด)

---

## 4. Capture Filter vs Display Filter

| | Capture Filter | Display Filter |
|---|---|---|
| ทำงานเมื่อ | **ก่อนจับ** (ไม่ตรงก็ไม่เก็บ) | **หลังจับ** (ซ่อน/แสดง) |
| Syntax | BPF (เหมือน tcpdump) | ภาษาของ Wireshark |
| ข้อดี | ไฟล์เล็ก ไม่หน่วงเครื่อง | ยืดหยุ่น แก้ได้ตลอด |
| ข้อเสีย | กรองผิด = ข้อมูลหายไปเลย | ไฟล์ใหญ่ |
| ตัวอย่าง | `host 10.0.0.5 and port 443` | `ip.addr == 10.0.0.5 && tcp.port == 443` |

**Capture filter (BPF) ที่ใช้บ่อย**
```
host 10.0.0.5            net 192.168.1.0/24       port 53
tcp port 443             not port 22              host 10.0.0.5 and not port 3389
```

**Display filter ที่ต้องรู้**
| Filter | แสดง |
|---|---|
| `ip.addr == 10.0.0.5` | packet ที่มี IP นี้ (ต้นทางหรือปลายทาง) |
| `ip.src == 10.0.0.5` / `ip.dst == ...` | เฉพาะต้นทาง/ปลายทาง |
| `tcp.port == 443` / `udp.port == 53` | ตาม port |
| `dns` / `dhcp` / `arp` / `icmp` / `http` / `tls` | ตามโปรโตคอล |
| `tcp.flags.syn == 1 && tcp.flags.ack == 0` | SYN (เริ่มเชื่อมต่อ) |
| `tcp.flags.reset == 1` | RST |
| `tcp.analysis.retransmission` | ส่งซ้ำ (loss) |
| `tcp.analysis.flags` | ปัญหา TCP ทุกชนิด |
| `tcp.analysis.zero_window` | ผู้รับรับไม่ทัน |
| `dns.flags.rcode == 3` | DNS ตอบ NXDOMAIN |
| `http.response.code >= 400` | HTTP error |
| `tls.handshake.type == 1` | TLS ClientHello |
| `tls.handshake.extensions_server_name contains "example"` | SNI ที่มีคำนี้ |
| `eth.addr == 00:1a:2b:3c:4d:5e` | ตาม MAC |
| `!(arp or dns or icmp)` | ตัดสิ่งที่ไม่สนใจออก |
| `frame.time_delta_displayed > 1` | ช่องว่างเวลา > 1 วินาที (หาจุดค้าง) |

ตัวดำเนินการ: `==` `!=` `>` `<` `&&`(and) `||`(or) `!`(not) `contains` `matches`
แถบ filter เป็น **สีเขียว = ถูก, แดง = syntax ผิด**

---

## 5. เครื่องมือวิเคราะห์ที่ใช้บ่อย

| เมนู | ใช้ทำอะไร |
|---|---|
| **Follow → TCP/UDP/TLS/HTTP Stream** | ดูบทสนทนาเดียวเรียงกัน (เห็น request/response ทั้งหมด) |
| **Statistics → Conversations** | คู่ IP/port ไหนคุยกันมากที่สุด (top talkers) |
| **Statistics → Protocol Hierarchy** | สัดส่วนโปรโตคอลในไฟล์ |
| **Statistics → I/O Graphs** | กราฟปริมาณ traffic ตามเวลา หาช่วงพุ่ง/หยุด |
| **Statistics → TCP Stream Graphs** | Throughput/RTT/Window ของการเชื่อมต่อ |
| **Analyze → Expert Information** | Wireshark สรุปปัญหาที่พบ (retransmission, RST, malformed) |
| **View → Time Display Format** | เปลี่ยนเป็น "Seconds Since Previous Displayed Packet" หาช่วงที่รอนาน |
| **Name Resolution** | แปลง IP/MAC เป็นชื่อ (ปิดไว้จะเร็วกว่า) |
| **Coloring Rules** | สีดำ/แดง = TCP มีปัญหา |

---

## 6. ถอดรหัส TLS (สำหรับเครื่องของเราเอง)

HTTPS เข้ารหัส Wireshark จึงเห็นแค่ TLS ถ้าต้องการเห็น HTTP ข้างใน (บนเครื่อง lab ของตัวเอง):
1. ตั้ง environment variable `SSLKEYLOGFILE=C:\temp\keys.log` แล้วเปิด browser ใหม่
2. Wireshark: Edit → Preferences → Protocols → TLS → (Pre)-Master-Secret log filename = ไฟล์นั้น
3. จะเห็น HTTP/2 ภายในได้

---

## 7. วิเคราะห์ปัญหาจริง 5 แบบ

**① "เปิดเว็บภายในไม่ได้"** — filter `ip.addr == <server>`
- เห็น SYN ซ้ำหลายครั้ง ไม่มี SYN-ACK → firewall drop / server ไม่ตอบ / ไม่มีทางกลับ
- เห็น SYN → RST → port ปิด
- handshake ผ่าน แต่ TLS Alert → ปัญหา cert/TLS version

**② "เน็ตช้า"** — Expert Info + `tcp.analysis.retransmission`
- retransmission เยอะ → packet loss (สาย/Wi-Fi/congestion)
- zero window → ปลายทางรับไม่ทัน
- ดู RTT ของ handshake (เวลา SYN → SYN-ACK) = ความหน่วงเครือข่าย

**③ "เว็บโหลดนานก่อนจะเริ่ม"** — ดู DNS
- `dns` แล้วดู time ระหว่าง query กับ response, มี query ซ้ำ/timeout หรือ NXDOMAIN

**④ "ไม่ได้ IP"** — `dhcp` (หรือ `bootp` ใน Wireshark รุ่นเก่า)
- มีแค่ Discover ไม่มี Offer → server/relay ไม่ทำงาน
- มี Offer จาก IP แปลก → rogue DHCP

**⑤ "บางเว็บค้างกลางทาง"** — ดู packet ขนาดใหญ่ที่ส่งซ้ำ และ ICMP "Fragmentation needed"
- packet ใหญ่หายแต่เล็กผ่าน → MTU black hole

---

## 8. แนวปฏิบัติที่ดี

- กำหนด **ขอบเขตการจับ** (เวลา, ผู้ใช้, IP) และเริ่มจับ **ก่อน** ทำให้ปัญหาเกิดซ้ำ
- จับ **นานพอ** ครอบช่วงที่ปัญหาเกิด แต่ใช้ capture filter/ring buffer ไม่ให้ไฟล์ใหญ่เกินไป
- **ซิงก์เวลาเครื่อง (NTP)** เมื่อจับหลายจุด
- เก็บไฟล์ pcap อย่างปลอดภัย และลบเมื่อไม่ใช้ (มีข้อมูลอ่อนไหว)
- ไฟล์ใหญ่เปิดช้า → ใช้ `editcap`/`tshark` ตัดเฉพาะช่วงหรือ filter ก่อน

---

## 9. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| เปิด Wireshark บนเครื่องใดก็เห็นทุก traffic ของ switch | เห็นเฉพาะของตัวเอง + broadcast ต้องใช้ SPAN/TAP |
| Capture filter กับ display filter ใช้ syntax เดียวกัน | ต่างกัน (BPF vs Wireshark) |
| เห็นเนื้อหา HTTPS ได้เลย | เข้ารหัส ต้องมี key จึงถอดได้ |
| retransmission ทุกตัวเป็นปัญหาร้ายแรง | มีบ้างเป็นปกติ ต้องดูสัดส่วนและรูปแบบ |

---

## 10. Cheat Sheet

```
จับที่ไหน: เครื่องตัวเอง · SPAN (monitor session) · TAP · บน firewall · 2 จุดเทียบกัน
Capture filter (BPF): host X and port 443 · net 10.0.0.0/24 · not port 22
Display: ip.addr== · tcp.port== · dns · dhcp · arp · tcp.flags.reset==1
         tcp.analysis.retransmission · tcp.analysis.zero_window · dns.flags.rcode==3
         http.response.code>=400 · tls.handshake.type==1
Follow Stream · Statistics: Conversations / I/O Graph / Protocol Hierarchy · Expert Info
คลิกขวา field → Apply as Filter
SYN ซ้ำไม่มีตอบ = drop · SYN→RST = port ปิด · retrans เยอะ = loss · zero window = ปลายทางช้า
```

---

## 11. แบบทดสอบ 10 ข้อ

1. Capture filter กับ Display filter ต่างกันอย่างไร
2. เปิด Wireshark บน PC แล้วไม่เห็น traffic ของเครื่องอื่นใน switch เพราะอะไร แก้อย่างไร
3. Display filter แสดงเฉพาะ traffic ของ 10.1.1.5 ที่ port 443
4. Display filter หา TCP retransmission
5. Display filter หา DNS ที่ตอบว่าไม่มีชื่อนี้
6. เมนูใดใช้หาว่าใครคุยกันมากที่สุด
7. เห็น SYN จาก client ซ้ำ 3 ครั้งโดยไม่มีคำตอบ สรุปว่าอะไร
8. พบ zero window จำนวนมาก ปัญหาอยู่ที่ใด
9. จะดู request และ response ของการเชื่อมต่อเดียวเรียงกันใช้คำสั่งอะไร
10. ทำไมต้องระวังเรื่องการเก็บไฟล์ pcap

<details><summary><b>เฉลย</b></summary>

1. Capture filter กรองก่อนจับ (BPF, ไม่เก็บสิ่งที่ไม่ตรง); Display filter กรองตอนแสดงหลังจับ (syntax Wireshark)
2. Switch ส่ง frame เฉพาะพอร์ตปลายทาง — ใช้ SPAN/port mirror หรือ TAP หรือจับบนเครื่องที่มีปัญหาเอง
3. `ip.addr == 10.1.1.5 && tcp.port == 443`
4. `tcp.analysis.retransmission`
5. `dns.flags.rcode == 3`
6. Statistics → Conversations
7. ปลายทางไม่ตอบ — firewall drop, server ไม่ทำงาน หรือไม่มีเส้นทางกลับ
8. ปลายทาง (ผู้รับ) ประมวลผลไม่ทัน ไม่ใช่เครือข่าย
9. Follow → TCP Stream
10. อาจมีข้อมูลส่วนบุคคล/รหัสผ่าน/ข้อมูลธุรกิจ ต้องเก็บอย่างปลอดภัยตาม PDPA และลบเมื่อเลิกใช้
</details>

---

➡️ ต่อไป: **Level 23 — tcpdump & CLI capture**
