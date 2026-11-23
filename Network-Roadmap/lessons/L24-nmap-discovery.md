# บทเรียน Level 24 — Nmap & Network Discovery (ฉบับละเอียด)

> อ่านจบแล้วจะ: ใช้ nmap ค้นหาอุปกรณ์, port, service และ OS · เข้าใจสถานะ open/closed/filtered · เลือกชนิดการสแกนได้เหมาะสม · ใช้ nmap ตรวจ firewall rule และทำ asset inventory

> ⚠️ **กฎเหล็ก:** สแกนเฉพาะเครือข่ายที่ **ตนเป็นเจ้าของหรือได้รับอนุญาตเป็นลายลักษณ์อักษร** การสแกนระบบผู้อื่นโดยไม่ได้รับอนุญาตอาจผิด พ.ร.บ.คอมพิวเตอร์ฯ และนโยบายองค์กร แม้ในองค์กรของตัวเอง ควรแจ้งทีม security/NOC ก่อน เพื่อไม่ให้ถูกมองว่าเป็นการโจมตี

---

## 1. Nmap คืออะไร ใช้ทำอะไรในงาน

**Nmap (Network Mapper)** คือเครื่องมือสแกนเครือข่าย open-source ที่ใช้มากที่สุดในโลก

**งานที่ใช้จริง**
- **Asset inventory:** ในวงนี้มีอุปกรณ์อะไรบ้าง
- **ตรวจ firewall rule:** port ที่ควรเปิดเปิดจริงไหม ที่ควรปิดปิดจริงไหม
- **Security audit:** หา service ที่ไม่ควรเปิด (Telnet, SMBv1, database เปิดสู่ภายนอก)
- **Troubleshooting:** server เปิดบริการ port นี้อยู่หรือเปล่า
- **ตรวจ TLS:** server รองรับ TLS version/cipher เก่าที่ไม่ปลอดภัยหรือไม่

---

## 2. Host Discovery — หาว่ามีเครื่องไหนออนไลน์

```bash
nmap -sn 192.168.1.0/24          # ping scan (ไม่สแกน port) — เดิมเรียก -sP
```
- ในวงเดียวกัน nmap ใช้ **ARP** (แม่นยำมาก เพราะเครื่องต้องตอบ ARP แม้ firewall บล็อก ping)
- ข้ามวงใช้ ICMP echo, TCP SYN 443, TCP ACK 80, ICMP timestamp
- `-Pn` = **ข้ามการ discovery** ถือว่าทุกเครื่องออนไลน์ (ใช้เมื่อปลายทางบล็อก ping)

---

## 3. สถานะของ Port

| สถานะ | ความหมาย | สิ่งที่เกิดเบื้องหลัง |
|---|---|---|
| **open** | มีโปรแกรมรอรับ (listen) | ได้ SYN-ACK |
| **closed** | เครื่องตอบ แต่ไม่มีโปรแกรมรอที่ port นี้ | ได้ RST |
| **filtered** | ไม่รู้ เพราะมี **firewall กรอง** | ไม่มีคำตอบ หรือได้ ICMP unreachable (admin prohibited) |
| unfiltered | เข้าถึงได้แต่บอกไม่ได้ว่าเปิดหรือปิด | (ACK scan) |
| open\|filtered | อาจเปิดหรือถูกกรอง | (UDP scan มักได้ผลนี้) |

> 🔑 **closed กับ filtered ต่างกันมาก:** closed = เครื่องอยู่และ firewall ปล่อยผ่าน แค่ไม่มีบริการ · filtered = มี firewall ขวางอยู่

---

## 4. ชนิดของการสแกน

| Option | ชื่อ | หลักการ | หมายเหตุ |
|---|---|---|---|
| **`-sS`** | **SYN scan** (half-open) | ส่ง SYN ได้ SYN-ACK แล้วส่ง RST ไม่ทำ handshake ครบ | ค่าเริ่มต้นเมื่อเป็น root · เร็ว |
| **`-sT`** | TCP Connect | handshake ครบ | ใช้เมื่อไม่มีสิทธิ์ root · log ที่ปลายทางชัดเจน |
| **`-sU`** | UDP scan | ส่ง UDP รอคำตอบ/ICMP port unreachable | **ช้ามาก** (ต้องรอ timeout, ICMP ถูก rate-limit) |
| `-sA` | ACK scan | ตรวจว่า firewall เป็น stateful ไหม | ใช้ map firewall |
| **`-sV`** | Version detection | คุยกับบริการเพื่อระบุชื่อ/เวอร์ชัน | เช่น "OpenSSH 9.6" |
| **`-O`** | OS detection | วิเคราะห์ลักษณะ TCP/IP stack | ต้องมี port เปิด 1 และปิด 1 จะแม่นกว่า |
| **`-A`** | Aggressive | `-sV -O -sC --traceroute` | เห็นข้อมูลมาก แต่ดังและช้า |
| `-sC` | Default scripts | รัน NSE script พื้นฐาน | |

### เลือก port
```bash
nmap 10.0.0.5                     # 1,000 port ที่นิยม (ค่าเริ่มต้น)
nmap -p 22,80,443 10.0.0.5        # ระบุ port
nmap -p 1-1024 10.0.0.5           # ช่วง
nmap -p- 10.0.0.5                 # ทั้งหมด 65,535 port
nmap -F 10.0.0.5                  # Fast: 100 port ที่นิยม
nmap --top-ports 50 10.0.0.0/24
nmap -sU -p 53,123,161 10.0.0.5   # UDP เฉพาะที่สนใจ
```

### ความเร็วและความดัง
- `-T0`…`-T5` (ค่าเริ่มต้น T3) — **T4** เหมาะกับ LAN ที่เสถียร, T5 อาจพลาดผล
- สแกนเร็วเกินไปอาจทำให้อุปกรณ์รุ่นเก่า/เครื่องจักร/อุปกรณ์การแพทย์/OT มีปัญหา → **ห้ามสแกนเครือข่าย OT/อุปกรณ์การแพทย์โดยไม่ได้ประสานงาน**

---

## 5. อ่านผล

```
$ sudo nmap -sS -sV -O 10.0.0.5
PORT     STATE    SERVICE       VERSION
22/tcp   open     ssh           OpenSSH 9.6p1 Ubuntu
80/tcp   open     http          nginx 1.24.0
443/tcp  open     ssl/http      nginx 1.24.0
3306/tcp filtered mysql                              ← firewall กรองอยู่ (ดี)
3389/tcp closed   ms-wbt-server
MAC Address: 52:54:00:AB:CD:EF (QEMU virtual NIC)
OS details: Linux 5.x - 6.x
```

---

## 6. NSE — Nmap Scripting Engine

สคริปต์ (ภาษา Lua) หลายร้อยตัว แบ่งหมวด: `default`, `safe`, `discovery`, `vuln`, `auth`, `brute`, `intrusive`…

```bash
nmap --script ssl-enum-ciphers -p 443 example.com     # TLS version/cipher ที่ server รองรับ
nmap --script ssl-cert -p 443 10.0.0.5                # ดู certificate (วันหมดอายุ, SAN)
nmap --script smb-protocols -p 445 10.0.0.0/24        # หาเครื่องที่ยังเปิด SMBv1
nmap --script http-title -p 80,443 10.0.0.0/24        # ชื่อหน้าเว็บของทุกเครื่อง (inventory)
nmap --script dns-brute example.com                   # เฉพาะโดเมนของตัวเอง
```
> ⚠️ หมวด `vuln`, `brute`, `intrusive` อาจรบกวนหรือทำให้ระบบล่ม/บัญชีถูกล็อก ใช้เฉพาะในขอบเขตที่ได้รับอนุญาต

---

## 7. ส่งออกผลและใช้ในงาน

```bash
nmap -sV 10.0.0.0/24 -oN scan.txt       # normal
nmap -sV 10.0.0.0/24 -oX scan.xml       # XML (นำไปประมวลผลต่อ)
nmap -sV 10.0.0.0/24 -oA scan-2026-11   # ทุกรูปแบบพร้อมกัน
ndiff scan-old.xml scan-new.xml         # เปรียบเทียบว่ามีอะไรเปลี่ยน (port ใหม่เปิด)
```
**Use case: ตรวจ firewall rule หลัง change**
```
 Policy ที่ต้องการ: Guest VLAN เข้าได้เฉพาะ internet, ห้ามเข้า Server zone
 → จากเครื่องใน Guest VLAN:  nmap -Pn -p 22,445,3389,1433 10.0.10.0/24
 → ผลที่คาดหวัง: filtered ทั้งหมด  ถ้าพบ open = rule ผิด
```
**Use case: inventory รายสัปดาห์** — สแกนตามเวลา เก็บ XML แล้ว `ndiff` แจ้งเตือนเมื่อพบ port ใหม่เปิด

---

## 8. เครื่องมือคล้ายกัน

| เครื่องมือ | จุดเด่น |
|---|---|
| **Zenmap** | GUI ของ nmap |
| **masscan / RustScan** | สแกน port จำนวนมากเร็วมาก |
| **Angry IP Scanner / Advanced IP Scanner** | GUI ง่าย สำหรับ helpdesk หาเครื่องในวง |
| **arp-scan** | หาเครื่องใน LAN ด้วย ARP |
| **Nessus / OpenVAS** | Vulnerability scanner (ลึกกว่า port scan, Level 54 ของ ISC/SI) |

---

## 9. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| ping ไม่ได้ = เครื่องไม่อยู่ | อาจบล็อก ICMP ใช้ `-Pn` หรือ ARP scan |
| filtered = port ปิด | filtered = มี firewall กรอง ไม่รู้ว่าเปิดหรือปิด |
| UDP scan เร็วเท่า TCP | ช้ามาก ควรระบุเฉพาะ port ที่สนใจ |
| สแกนเครือข่ายตัวเองไม่ต้องขออนุญาต | ควรแจ้ง/ขออนุญาต และระวังอุปกรณ์ OT/การแพทย์ |

---

## 10. Cheat Sheet

```
nmap -sn 10.0.0.0/24            host discovery (ARP ในวงเดียวกัน)
nmap -Pn host                   ข้าม discovery
sudo nmap -sS -p- host          SYN scan ทุก port
nmap -sV -O host                version + OS
nmap -sU -p 53,123,161 host     UDP (ช้า)
nmap --script ssl-enum-ciphers -p 443 host
-oA ชื่อไฟล์ · ndiff เทียบผล · -T4 ใน LAN
open = SYN-ACK · closed = RST · filtered = ไม่ตอบ/ถูกกรอง
สแกนเฉพาะที่ได้รับอนุญาต · ระวัง OT/อุปกรณ์การแพทย์
```

---

## 11. แบบทดสอบ 10 ข้อ

1. open, closed, filtered ต่างกันอย่างไร
2. ทำไม `-sS` เรียกว่า half-open scan
3. ทำไม UDP scan ช้า
4. ปลายทางบล็อก ping ทำให้ nmap รายงานว่า host down ควรใช้ option ใด
5. คำสั่งตรวจว่า server รองรับ TLS version/cipher ใดบ้าง
6. จะใช้ nmap ตรวจว่า firewall rule ใหม่ทำงานถูกต้องอย่างไร
7. คำสั่งบันทึกผลทุกรูปแบบ และเครื่องมือเปรียบเทียบผล 2 ครั้ง
8. ทำไม `-sn` ในวงเดียวกันจึงแม่นยำกว่าการ ping ธรรมดา
9. ข้อควรระวังเมื่อสแกนเครือข่ายโรงพยาบาลหรือโรงงาน
10. nmap ต่างจาก vulnerability scanner เช่น Nessus อย่างไร

<details><summary><b>เฉลย</b></summary>

1. open = มีบริการรอรับ (SYN-ACK); closed = เครื่องตอบแต่ไม่มีบริการ (RST); filtered = มี firewall กรอง ไม่ได้คำตอบหรือได้ ICMP prohibited
2. ส่ง SYN ได้ SYN-ACK แล้วส่ง RST ทันที ไม่ทำ handshake ครบ
3. ไม่มี handshake ต้องรอ timeout และ ICMP port unreachable มักถูกจำกัดอัตรา
4. `-Pn`
5. `nmap --script ssl-enum-ciphers -p 443 <host>`
6. สแกนจาก source ที่ควรถูกอนุญาต/ปฏิเสธ ไปยังปลายทางและ port ตาม policy แล้วเทียบผลกับที่คาดหวัง
7. `-oA <ชื่อ>`; `ndiff`
8. ใช้ ARP ซึ่งทุกเครื่องในวงต้องตอบ แม้ firewall ในเครื่องบล็อก ICMP
9. อุปกรณ์การแพทย์/OT อาจล่มหรือทำงานผิดพลาดเมื่อถูกสแกน ต้องประสานงาน ขออนุญาต ใช้ความเร็วต่ำ หรือหลีกเลี่ยง
10. nmap หา host/port/service/version; vulnerability scanner ตรวจลึกถึงช่องโหว่ (CVE), patch และการตั้งค่า
</details>

---

➡️ ต่อไป: **Level 25 — dig, curl, openssl, nc, iperf**
