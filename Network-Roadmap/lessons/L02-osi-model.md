# บทเรียน Level 2 — OSI Model 7 Layers (ฉบับละเอียด)

> อ่านจบแล้วจะ: จำ 7 ชั้นได้ · รู้ว่าแต่ละชั้นทำอะไร มี protocol/อุปกรณ์อะไร · เข้าใจ Encapsulation · ใช้ OSI เป็นกรอบในการแก้ปัญหาได้

---

## 1. OSI Model คืออะไร และทำไมต้องมี

**OSI (Open Systems Interconnection) Model** คือ **กรอบแนวคิด (reference model)** ที่ ISO กำหนดขึ้น เพื่อแบ่งการสื่อสารในเครือข่ายออกเป็น **7 ชั้น (Layers)** แต่ละชั้นมีหน้าที่ชัดเจน และทำงานร่วมกับชั้นที่อยู่ติดกันเท่านั้น

**ทำไมต้องแบ่งเป็นชั้น?**
- **แยกปัญหาใหญ่เป็นปัญหาเล็ก**: คนทำ Wi-Fi ไม่ต้องรู้ว่าเว็บเขียนอย่างไร คนเขียนเว็บไม่ต้องรู้ว่าสายเป็นทองแดงหรือไฟเบอร์
- **ผู้ผลิตต่างยี่ห้อทำงานร่วมกันได้**: ทุกรายทำตามหน้าที่ของแต่ละชั้นเหมือนกัน
- **เปลี่ยนเทคโนโลยีชั้นหนึ่งได้โดยไม่กระทบชั้นอื่น**: เปลี่ยนจากสาย LAN เป็น Wi-Fi แล้ว browser ยังทำงานเหมือนเดิม
- **เป็นภาษากลางในการทำงาน**: วิศวกรพูดว่า "ปัญหาอยู่ที่ Layer 2" แล้วทุกคนเข้าใจตรงกัน

> 💡 **เปรียบเทียบ:** การส่งจดหมายระหว่างบริษัท
> ผู้บริหารเขียนเนื้อหา (L7) → เลขาแปลภาษาและจัดรูปแบบ (L6) → นัดหมายช่วงเวลาการติดต่อ (L5) → แผนกเอกสารแบ่งเป็นหลายซองและใส่เลขลำดับ (L4) → ใส่ที่อยู่ปลายทาง (L3) → ไปรษณีย์ส่งต่อทีละจุด (L2) → รถ/เครื่องบินขนจริง (L1)

---

## 2. 7 ชั้นของ OSI (จากบนลงล่าง)

```
 ┌───────────────────────┐
 │ 7 Application          │  ← ผู้ใช้/แอปพลิเคชันคุยกับเครือข่าย
 │ 6 Presentation         │  ← รูปแบบข้อมูล, เข้ารหัส, บีบอัด
 │ 5 Session              │  ← เปิด/คุม/ปิดการสนทนา
 │ 4 Transport            │  ← ส่งครบ/ถูกลำดับ, แยกแอปด้วย port
 │ 3 Network              │  ← ที่อยู่ IP, เลือกเส้นทางข้ามเครือข่าย
 │ 2 Data Link            │  ← ส่งในเครือข่ายเดียวกันด้วย MAC
 │ 1 Physical             │  ← สัญญาณไฟฟ้า/แสง/คลื่นบนสื่อกลาง
 └───────────────────────┘
```

**วิธีจำ (บน→ล่าง):** **A**ll **P**eople **S**eem **T**o **N**eed **D**ata **P**rocessing
**วิธีจำ (ล่าง→บน):** **P**lease **D**o **N**ot **T**hrow **S**ausage **P**izza **A**way

### Layer 1 — Physical (กายภาพ)

- **หน้าที่:** ส่ง **บิต (0/1)** ในรูปสัญญาณ ได้แก่ ไฟฟ้าในสายทองแดง, แสงในไฟเบอร์, คลื่นวิทยุใน Wi-Fi
- **กำหนดเรื่อง:** ชนิดสาย, หัวต่อ, ระดับแรงดัน, ความถี่, ความเร็ว, ระยะทาง
- **ตัวอย่าง:** สาย UTP Cat6, ไฟเบอร์, หัว RJ45/LC, SFP, Hub, Repeater, Media converter, คลื่น 2.4/5 GHz
- **PDU:** **Bits**
- **ปัญหาที่พบ:** สายขาด/หลวม, หัวต่อเสีย, ไฟพอร์ตไม่ติด, สัญญาณ Wi-Fi อ่อน, สายยาวเกิน 100 m

### Layer 2 — Data Link (เชื่อมโยงข้อมูล)

- **หน้าที่:** ส่งข้อมูล **ภายในเครือข่ายเดียวกัน (hop ต่อ hop)** โดยใช้ **MAC Address**
  - จัดบิตเป็น **Frame**
  - ตรวจความผิดพลาดด้วย **FCS/CRC** (พบ frame เสียก็ทิ้ง)
  - ควบคุมการเข้าใช้สื่อกลาง (ใครส่งเมื่อไร)
- **ชั้นย่อย:** LLC (ติดต่อกับชั้นบน) และ MAC (ติดต่อกับสื่อกลาง)
- **ตัวอย่าง:** Ethernet (802.3), Wi-Fi (802.11), **Switch**, Bridge, VLAN (802.1Q), STP, ARP (ทำงานระหว่าง L2/L3)
- **PDU:** **Frame**
- **ปัญหาที่พบ:** VLAN ผิด, loop ใน switch, MAC flapping, duplex ไม่ตรงกัน, CRC error

### Layer 3 — Network (เครือข่าย)

- **หน้าที่:** ส่งข้อมูล **ข้ามเครือข่าย จากต้นทางถึงปลายทาง** ด้วย **IP Address** และ **เลือกเส้นทาง (Routing)**
- **ตัวอย่าง:** IPv4, IPv6, ICMP (ping), **Router**, L3 Switch, OSPF, BGP
- **PDU:** **Packet**
- **ปัญหาที่พบ:** IP/subnet ผิด, ไม่มี default gateway, ไม่มี route, routing loop

### Layer 4 — Transport (ขนส่ง)

- **หน้าที่:** ส่งข้อมูล **ระหว่างแอปพลิเคชันบน 2 เครื่อง**
  - แยกแอปด้วย **Port number** (เว็บ 443, SSH 22)
  - **TCP**: เชื่อถือได้ ส่งครบ เรียงลำดับ ส่งซ้ำเมื่อหาย ควบคุมความเร็ว
  - **UDP**: เร็ว เบา ไม่รับประกัน
  - แบ่งข้อมูลก้อนใหญ่เป็นชิ้น (segmentation) แล้วประกอบคืน
- **ตัวอย่าง:** TCP, UDP, QUIC (วิ่งบน UDP), Firewall ที่กรองตาม port
- **PDU:** **Segment** (TCP) / **Datagram** (UDP)
- **ปัญหาที่พบ:** port ถูก firewall บล็อก, ไม่มีโปรแกรมรอรับที่ port นั้น, retransmission มาก

### Layer 5 — Session (เซสชัน)

- **หน้าที่:** **เปิด–ดูแล–ปิด** การสนทนาระหว่างสองฝั่ง, จัดการ checkpoint/การกลับมาต่อ
- **ตัวอย่าง:** NetBIOS, RPC, SMB session, การ login ค้างไว้, PPTP, SOCKS
- **ในทางปฏิบัติ:** โปรโตคอลจริงมักรวมหน้าที่ L5–L7 ไว้ในตัวเดียว (เช่น HTTP, TLS)

### Layer 6 — Presentation (นำเสนอ)

- **หน้าที่:** แปลง **รูปแบบข้อมูล** ให้ทั้งสองฝั่งเข้าใจตรงกัน
  - Encoding (ASCII, UTF-8 ที่รองรับภาษาไทย)
  - **Encryption/Decryption** (TLS/SSL มักถูกจัดไว้ที่ชั้นนี้)
  - Compression, รูปแบบไฟล์ (JPEG, MP4, JSON, XML)
- **ปัญหาที่พบ:** ภาษาไทยเป็นตัวต่างดาว (encoding ผิด), certificate/การเข้ารหัสไม่ตรงกัน

### Layer 7 — Application (แอปพลิเคชัน)

- **หน้าที่:** **บริการเครือข่ายที่แอปพลิเคชันเรียกใช้** (ไม่ใช่ตัวโปรแกรม เช่น Chrome แต่เป็น protocol ที่ Chrome ใช้)
- **ตัวอย่าง:** HTTP/HTTPS, DNS, SMTP/IMAP (อีเมล), FTP/SFTP, SSH, DHCP, SNMP, RDP
- **PDU:** **Data**
- **ปัญหาที่พบ:** DNS resolve ไม่ได้, เว็บ error 500, login ไม่ผ่าน, cert หมดอายุ

---

## 3. ตารางสรุปที่ต้องจำ

| Layer | ชื่อ | หน้าที่ (คำเดียว) | PDU | Address | อุปกรณ์/ตัวอย่าง |
|---|---|---|---|---|---|
| 7 | Application | บริการให้แอป | Data | ชื่อ (URL, DNS) | HTTP, DNS, SMTP, SSH |
| 6 | Presentation | รูปแบบ/เข้ารหัส | Data | — | TLS, UTF-8, JPEG |
| 5 | Session | คุมการสนทนา | Data | — | RPC, NetBIOS |
| 4 | Transport | ส่งระหว่างแอป | Segment/Datagram | **Port** | TCP, UDP, firewall |
| 3 | Network | ข้ามเครือข่าย | **Packet** | **IP** | Router, IP, ICMP |
| 2 | Data Link | ภายในเครือข่าย | **Frame** | **MAC** | Switch, Ethernet, Wi-Fi |
| 1 | Physical | สัญญาณ | **Bits** | — | สาย, Hub, SFP |

---

## 4. Encapsulation & De-encapsulation — ข้อมูลถูก "ห่อ" ทีละชั้น

ตอนส่ง ข้อมูลจะเดินจาก L7 ลงไป L1 และ **แต่ละชั้นแปะ header ของตัวเอง** เหมือนใส่ซองซ้อนกันหลายชั้น

```
 L7-5  [              DATA (เช่น HTTP GET)              ]
 L4    [TCP Hdr: port 51000→443][        DATA          ]           = Segment
 L3    [IP Hdr: 192.168.1.10→142.250.x.x][TCP][  DATA  ]          = Packet
 L2    [Eth Hdr: MAC→MAC][IP][TCP][   DATA   ][FCS]               = Frame
 L1    0101101001011100101010...                                   = Bits
```

ฝั่งรับทำกลับกัน (**De-encapsulation**) คือแกะทีละชั้นจาก L1 ขึ้นไป L7 แต่ละชั้นอ่าน header ของตัวเองแล้วส่งที่เหลือให้ชั้นบน

**อุปกรณ์กลางทางแกะถึงชั้นไหน?**

```
 PC ต้นทาง        Switch         Router          Switch       Server ปลายทาง
 L7 ─────────────────────────────────────────────────────────── L7
 L4 ─────────────────────────────────────────────────────────── L4
 L3 ─────────────────── L3 ──────── L3 ──────────────────────── L3
 L2 ──── L2 ──── L2 ─── L2          L2 ──── L2 ──── L2 ──────── L2
 L1 ──── L1 ──── L1 ─── L1          L1 ──── L1 ──── L1 ──────── L1
```

- **Switch** อ่านถึง L2 (ดู MAC แล้วส่งต่อ)
- **Router** อ่านถึง L3 (ดู IP แล้วเลือกเส้นทาง จากนั้น **สร้าง Frame L2 ใหม่** สำหรับ hop ถัดไป ทำให้ MAC เปลี่ยนทุก hop แต่ IP ต้นทาง/ปลายทางคงเดิม เว้นแต่มี NAT)
- **Firewall รุ่นใหม่/Load Balancer L7** อ่านลึกถึง L7

> 🔑 **ประเด็นสำคัญ:** **MAC เปลี่ยนทุก hop · IP คงที่ตลอดทาง** (ยกเว้นผ่าน NAT)

---

## 5. ใช้ OSI ในการแก้ปัญหา (Troubleshooting)

### Bottom-up (ล่างขึ้นบน) — นิยมที่สุดสำหรับมือใหม่

| ขั้น | ตรวจ | คำถาม / คำสั่ง |
|---|---|---|
| L1 | สาย, ไฟพอร์ต, Wi-Fi | ไฟติดไหม? สายเสียบแน่นไหม? สัญญาณกี่ขีด? |
| L2 | ได้เชื่อมต่อ switch/AP, VLAN | `ip link` / ดู MAC table, VLAN ถูกไหม |
| L3 | IP, gateway, route | `ipconfig` / `ip a`, `ping gateway`, `ping 8.8.8.8` |
| L4 | port เปิดไหม, firewall | `Test-NetConnection host -Port 443`, `nc -zv host 443` |
| L7 | DNS, แอป | `nslookup google.com`, เปิดเว็บ, ดู error |

### เทคนิคอื่น
- **Top-down:** เริ่มจากแอป (เหมาะเมื่อสงสัยแอป)
- **Divide & Conquer:** เริ่มที่ **L3 ด้วย ping** ถ้า ping ผ่าน ปัญหาน่าจะอยู่ชั้นบน ถ้าไม่ผ่าน ไล่ลงล่าง (เร็วที่สุดเมื่อมีประสบการณ์)

### ตัวอย่างสถานการณ์

| อาการ | น่าจะเป็น Layer |
|---|---|
| ไฟพอร์ตไม่ติด | L1 |
| ต่อ Wi-Fi ได้ แต่ได้ IP 169.254.x.x | L2/L3 (VLAN/DHCP) |
| ping 8.8.8.8 ได้ แต่เปิด google.com ไม่ได้ | L7 (DNS) |
| ping server ได้ แต่ remote desktop ไม่ได้ | L4 (port 3389 ถูกบล็อก) |
| เปิดเว็บได้แต่ขึ้นเตือน certificate | L6 (TLS/cert) |
| เว็บขึ้น error 500 | L7 (แอปฝั่ง server) |

---

## 6. OSI vs ของจริง

OSI เป็น **โมเดลอ้างอิง** โปรโตคอลจริงบนอินเทอร์เน็ตทำงานตาม **TCP/IP Model** (บทถัดไป) ซึ่งรวม L5–L7 เป็นชั้นเดียว แต่ในวงการยังพูดเลขชั้นตาม OSI เสมอ เช่น
- "**L2 switch**" / "**L3 switch**"
- "**L4 load balancer**" (ดู IP+port) vs "**L7 load balancer**" (ดู URL/header)
- "**L7 firewall**" (รู้จักแอปพลิเคชัน)

บาง protocol อยู่ "ระหว่างชั้น": ARP (L2/L3), TLS (L4–L6), MPLS (เรียก "Layer 2.5")

---

## 7. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| Layer 7 คือตัวโปรแกรม เช่น Chrome, Outlook | L7 คือ **protocol** ที่โปรแกรมใช้ (HTTP, SMTP) |
| Switch ทุกตัวเป็น L2 | มี **L3 switch** ที่ route ได้ด้วย |
| Router เปลี่ยน IP ปลายทางทุก hop | Router เปลี่ยน **MAC** (สร้าง frame ใหม่) แต่ IP คงเดิม |
| OSI คือสิ่งที่อินเทอร์เน็ตใช้จริง | อินเทอร์เน็ตใช้ TCP/IP; OSI ใช้เป็นกรอบอธิบาย/สื่อสาร |
| Hub ทำงานที่ L2 | Hub ทำงานที่ **L1** (แค่ทวนสัญญาณ ไม่รู้จัก MAC) |

---

## 8. Cheat Sheet

```
7 Application   Data      ชื่อ/URL   HTTP DNS SMTP SSH DHCP
6 Presentation  Data      -          TLS UTF-8 JPEG (เข้ารหัส/รูปแบบ)
5 Session       Data      -          RPC NetBIOS (เปิด/ปิดการสนทนา)
4 Transport     Segment   PORT       TCP UDP · firewall
3 Network       Packet    IP         IP ICMP OSPF BGP · ROUTER
2 Data Link     Frame     MAC        Ethernet Wi-Fi VLAN STP · SWITCH
1 Physical      Bits      -          สาย ไฟเบอร์ คลื่น · HUB

ส่ง = ห่อ (Encapsulation) 7→1 · รับ = แกะ (De-encapsulation) 1→7
MAC เปลี่ยนทุก hop · IP คงที่ (ยกเว้น NAT)
แก้ปัญหา: Bottom-up / Top-down / Divide & Conquer (เริ่ม ping ที่ L3)
```

---

## 9. แบบทดสอบ 10 ข้อ

1. เรียง OSI จาก Layer 1 ถึง 7
2. PDU ของ Layer 2, 3 และ 4 เรียกว่าอะไร
3. Switch ทั่วไปอ่าน header ถึงชั้นไหน Router ถึงชั้นไหน
4. Address ประเภทใดใช้ที่ L2, L3, L4
5. ping 8.8.8.8 ได้ แต่เปิด www.google.com ไม่ได้ ปัญหาน่าจะอยู่ชั้นใด ตรวจอย่างไร
6. ข้อมูลส่งจาก PC ผ่าน router 3 ตัวถึง server: MAC ปลายทางใน frame กับ IP ปลายทางใน packet อะไรเปลี่ยน อะไรคงที่
7. การเข้ารหัส TLS มักถูกจัดอยู่ชั้นใด
8. Hub กับ Switch ทำงานที่ชั้นไหนตามลำดับ
9. L4 Load Balancer ต่างจาก L7 Load Balancer อย่างไร
10. ผู้ใช้แจ้ง "remote desktop เข้า server ไม่ได้ แต่ ping server ได้" ควรสงสัยชั้นใด และตรวจอะไร

<details><summary><b>เฉลย</b></summary>

1. Physical, Data Link, Network, Transport, Session, Presentation, Application
2. L2 = Frame, L3 = Packet, L4 = Segment (TCP) / Datagram (UDP)
3. Switch = L2, Router = L3
4. L2 = MAC, L3 = IP, L4 = Port
5. L7 (DNS) — `nslookup www.google.com`, ตรวจ DNS server ที่เครื่องใช้
6. MAC ปลายทางเปลี่ยนทุก hop (router สร้าง frame ใหม่); IP ปลายทางคงที่ (ถ้าไม่มี NAT)
7. Presentation (L6) — ในทางปฏิบัติคร่อมระหว่าง L4–L6
8. Hub = L1, Switch = L2
9. L4 ตัดสินจาก IP/port เท่านั้น; L7 อ่านเนื้อหา HTTP (URL, header, cookie) แล้วเลือก server ได้ละเอียดกว่า
10. L4 — port 3389 ถูก firewall บล็อก, บริการ RDP ไม่ได้เปิด, ตรวจด้วย `Test-NetConnection server -Port 3389`
</details>

---

➡️ ต่อไป: **Level 3 — TCP/IP Model** · กลับไปทำโปรเจคใน [01-foundations.md](../01-foundations.md)
