# บทเรียน Level 17 — NAT / PAT (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจว่าทำไมเครื่องหลายร้อยเครื่องใช้ public IP เดียวออกเน็ตได้ · Static NAT, Dynamic NAT, PAT · Port forwarding · Hairpin NAT · CGNAT · ปัญหาที่ NAT ก่อให้เกิด และตั้งค่าบน Cisco/Linux ได้

---

## 1. NAT คืออะไร ทำไมต้องมี

**NAT (Network Address Translation)** คือการ **แปลง IP (และ/หรือ port) ใน header ของ packet** ขณะผ่าน router/firewall

**เหตุผลหลัก:** IPv4 มีแค่ ~4.3 พันล้านหมายเลข ไม่พอสำหรับทุกอุปกรณ์ องค์กรจึงใช้ **Private IP (RFC 1918)** ภายใน แล้ว NAT แปลงเป็น **Public IP** ตอนออกอินเทอร์เน็ต (Private IP route บนอินเทอร์เน็ตไม่ได้)

> 💡 **เปรียบเทียบ:** NAT คือ **โอเปอเรเตอร์ตู้สาขาโทรศัพท์ของบริษัท** — พนักงานมีเบอร์ภายใน (private) เวลาโทรออก คนนอกเห็นเป็นเบอร์กลางของบริษัท (public) โอเปอเรเตอร์จดไว้ว่าสายไหนเป็นของใคร เมื่อมีสายตอบกลับมาจึงโอนกลับได้ถูกคน

---

## 2. ศัพท์ของ NAT (มุมมองของ Cisco)

| คำ | ความหมาย | ตัวอย่าง |
|---|---|---|
| **Inside Local** | IP จริงของเครื่องภายใน | 192.168.1.10 |
| **Inside Global** | IP ที่ใช้แทนเครื่องภายในเมื่อมองจากภายนอก | 203.0.113.5 |
| **Outside Global** | IP จริงของปลายทางภายนอก | 8.8.8.8 |
| **Outside Local** | IP ของปลายทางภายนอกเมื่อมองจากภายใน (ปกติเท่ากับ outside global) | 8.8.8.8 |

**Local** = มองจากฝั่งใน · **Global** = มองจากฝั่งนอก · **Inside/Outside** = เครื่องนั้นอยู่ฝั่งไหน

---

## 3. ประเภทของ NAT

### 3.1 Static NAT (1 : 1)
จับคู่ private IP หนึ่งตัวกับ public IP หนึ่งตัว **ถาวร** ใช้กับ server ที่ต้องให้คนภายนอกเข้าถึง

```
 192.168.1.100 (Web server) ◄──► 203.0.113.10   (ตลอดเวลา ทั้งเข้าและออก)
```

### 3.2 Dynamic NAT (Pool)
มี **pool ของ public IP** เครื่องภายในได้ IP จาก pool ตามลำดับ (1:1 ชั่วคราว) ถ้า pool หมด เครื่องถัดไปออกไม่ได้ **ปัจจุบันไม่นิยม**

### 3.3 PAT / NAT Overload / NAPT (Many : 1) ⭐ ใช้มากที่สุด
**หลายเครื่องใช้ public IP เดียว** โดยแยกด้วย **port** — router บ้านและองค์กรเกือบทั้งหมดใช้แบบนี้

```
 Inside Local          Inside Global (หลังแปลง)       ปลายทาง
 192.168.1.10:51000 ─► 203.0.113.5:40001          ─► 8.8.8.8:443
 192.168.1.11:51000 ─► 203.0.113.5:40002          ─► 8.8.8.8:443
 192.168.1.12:62000 ─► 203.0.113.5:40003          ─► 1.1.1.1:443

 NAT translation table:
 ┌──────────────────────┬──────────────────────┬──────────────┐
 │ Inside Local         │ Inside Global        │ Outside      │
 │ 192.168.1.10:51000   │ 203.0.113.5:40001    │ 8.8.8.8:443  │
 │ 192.168.1.11:51000   │ 203.0.113.5:40002    │ 8.8.8.8:443  │
 └──────────────────────┴──────────────────────┴──────────────┘
 คำตอบที่กลับมาที่ 203.0.113.5:40002 → router เปิดตาราง → ส่งต่อให้ 192.168.1.11:51000
```
- 1 public IP รองรับได้หลายหมื่น session พร้อมกัน (port มีประมาณ 64,000 ต่อ IP ต่อปลายทาง)
- องค์กรใหญ่ที่ session มากมาก (เช่น มหาวิทยาลัย) ต้องใช้ public IP หลายตัวเป็น pool

### 3.4 Port Forwarding (Static PAT / Destination NAT / VIP)
เปิดให้ **ภายนอกเข้ามาหาเครื่องภายใน** ผ่าน port ที่กำหนด

```
 Internet → 203.0.113.5:443  ──►  192.168.1.100:443 (Web server)
 Internet → 203.0.113.5:2222 ──►  192.168.1.50:22   (SSH — ตัวอย่าง ไม่แนะนำให้เปิดจริง)
```
- FortiGate เรียกว่า **VIP**, Palo Alto เรียก **Destination NAT**, router บ้านเรียก **Port Forwarding / Virtual Server**
- ต้องมี **firewall policy อนุญาต** ด้วย ไม่ใช่แค่ทำ NAT

### SNAT vs DNAT (ศัพท์ของ firewall/Linux)
- **SNAT (Source NAT):** แปลง **IP ต้นทาง** — ตอนภายในออกนอก (PAT คือ SNAT แบบหนึ่ง)
- **DNAT (Destination NAT):** แปลง **IP ปลายทาง** — ตอนภายนอกเข้ามาหา server (port forwarding)

---

## 4. ตัวอย่างการตั้งค่า

### Cisco IOS — PAT ออกอินเทอร์เน็ต + Static NAT ให้ web server
```
interface GigabitEthernet0/0
 description WAN
 ip address 203.0.113.5 255.255.255.248
 ip nat outside
interface GigabitEthernet0/1
 description LAN
 ip address 192.168.1.1 255.255.255.0
 ip nat inside
!
access-list 1 permit 192.168.1.0 0.0.0.255
ip nat inside source list 1 interface GigabitEthernet0/0 overload      ! PAT
ip nat inside source static tcp 192.168.1.100 443 203.0.113.5 443      ! port forward
!
show ip nat translations
show ip nat statistics
clear ip nat translation *
```

### Linux (nftables) — ทำเครื่อง Linux เป็น NAT router
```bash
sysctl -w net.ipv4.ip_forward=1
nft add table ip nat
nft add chain ip nat postrouting '{ type nat hook postrouting priority 100; }'
nft add rule ip nat postrouting oifname "eth0" masquerade          # PAT ขาออก
nft add chain ip nat prerouting '{ type nat hook prerouting priority -100; }'
nft add rule ip nat prerouting iifname "eth0" tcp dport 443 dnat to 192.168.1.100:443   # DNAT
```

---

## 5. Hairpin NAT (NAT Reflection / NAT Loopback)

**ปัญหา:** พนักงานในสำนักงานเปิด `https://www.company.com` ซึ่ง DNS ตอบเป็น public IP ของบริษัทเอง แต่ server อยู่ในเครือข่ายเดียวกัน → packet ออกไปที่ firewall แล้วต้องย้อนกลับเข้ามา ถ้า firewall ไม่รองรับจะเข้าไม่ได้

**แก้ได้ 2 วิธี**
1. ตั้ง **Hairpin NAT** บน firewall
2. ใช้ **Split-horizon DNS** ให้ผู้ใช้ภายในได้ IP ภายในของ server โดยตรง (มักดีกว่า)

---

## 6. CGNAT (Carrier-Grade NAT)

- ISP เองก็ขาด IPv4 จึงทำ **NAT อีกชั้น** ลูกค้าบ้านได้ IP ในช่วง **100.64.0.0/10** (หรือ private) ที่ขา WAN แทน public IP จริง
- **ผลกระทบ:** เปิด port forwarding ให้คนนอกเข้ามาที่บ้านไม่ได้ (กล้อง, NAS, เกม server), บางเกม/แอป P2P มีปัญหา
- **ทางแก้:** ขอ public IP จาก ISP (บางรายมีค่าบริการ), ใช้ IPv6, ใช้บริการ tunnel (Cloudflare Tunnel, Tailscale, ZeroTier)
- ตรวจ: ดู IP ที่ขา WAN ของ router เทียบกับที่เว็บ "What is my IP" แสดง ถ้าไม่ตรงกัน = อยู่หลัง CGNAT

---

## 7. ปัญหาที่เกิดจาก NAT

| ปัญหา | สาเหตุ / ทางแก้ |
|---|---|
| **IPsec VPN** ผ่าน NAT ไม่ได้ | ESP ไม่มี port และ NAT ทำให้ integrity check พัง → ใช้ **NAT-T** (ห่อด้วย UDP 4500) |
| **SIP/VoIP** เสียงทางเดียว | IP ภายในฝังอยู่ใน payload → ใช้ SIP ALG (บางครั้งต้อง **ปิด** ALG เพราะทำงานผิด), SBC, STUN |
| **FTP active mode** | ส่ง IP/port ใน payload → ใช้ passive mode/ALG |
| **การเชื่อมต่อหลุดเมื่อ idle** | NAT/firewall ลบ session ที่เงียบเกินเวลา → ตั้ง keepalive |
| **ระบุตัวผู้ใช้ยาก** | หลายคนใช้ IP เดียว → ต้องเก็บ **NAT log** (ตาม พ.ร.บ.คอมฯ) |
| **NAT table เต็ม / port หมด** | session มากเกิน → เพิ่ม public IP ใน pool, ลด timeout |
| **Failover ISP แล้ว session หลุด** | public IP เปลี่ยน → ผู้ใช้ต้องเชื่อมต่อใหม่ (ปกติ) |

> 🔑 **NAT ไม่ใช่ระบบความปลอดภัย** — แม้จะซ่อน IP ภายในและภายนอกเข้ามาเองไม่ได้ (คล้าย stateful firewall) แต่ไม่ได้ตรวจเนื้อหา ไม่ป้องกันมัลแวร์ที่เครื่องภายในเป็นฝ่ายเชื่อมต่อออกไปเอง ต้องมี firewall policy ที่ชัดเจนเสมอ

---

## 8. NAT กับ IPv6

IPv6 มี IP มากพอให้ทุกอุปกรณ์ใช้ global IP ได้ **จึงไม่จำเป็นต้องใช้ NAT** (ใช้ firewall ควบคุมแทน) ส่วน **NAT64** ใช้ให้เครือข่ายที่มีแต่ IPv6 เข้าถึงเว็บ IPv4 ได้ (Level 18)

---

## 9. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| NAT = firewall | NAT แปลงที่อยู่; firewall ตัดสินใจอนุญาต/ปฏิเสธ |
| ทำ port forwarding แล้วเข้าได้แน่นอน | ต้องมี firewall policy, server ต้องเปิดบริการ, ISP ต้องไม่ใช่ CGNAT |
| PAT ใช้ public IP เดียวรองรับได้ไม่จำกัด | จำกัดด้วยจำนวน port และทรัพยากรของอุปกรณ์ |
| Static NAT ใช้ได้เฉพาะขาเข้า | ใช้ได้ทั้งขาเข้าและขาออก (1:1 ถาวร) |

---

## 10. Cheat Sheet

```
NAT = แปลง IP/port · เหตุผล: IPv4 ไม่พอ → private ภายใน + public ภายนอก
Static NAT 1:1 (server) · Dynamic NAT pool (เลิกนิยม) · PAT/Overload many:1 (แยกด้วย port)
SNAT = แปลงต้นทาง (ออกเน็ต) · DNAT/Port forward/VIP = แปลงปลายทาง (เข้ามาหา server)
Inside local (IP จริงภายใน) · Inside global (IP ที่คนนอกเห็น)
Cisco: ip nat inside/outside · ip nat inside source list 1 interface X overload
Linux: masquerade (SNAT) · dnat to (DNAT)
Hairpin NAT หรือ Split DNS · CGNAT 100.64.0.0/10 → port forward ไม่ได้
IPsec ผ่าน NAT ใช้ NAT-T UDP 4500 · NAT ≠ security · เก็บ NAT log
```

---

## 11. แบบทดสอบ 10 ข้อ

1. ทำไมต้องมี NAT
2. PAT แยก session ของหลายเครื่องที่ใช้ public IP เดียวได้อย่างไร
3. Inside Local กับ Inside Global ต่างกันอย่างไร
4. Static NAT เหมาะกับอุปกรณ์แบบไหน
5. SNAT กับ DNAT ต่างกันอย่างไร
6. ตั้ง port forwarding แล้วจากภายนอกยังเข้าไม่ได้ ตรวจอะไรบ้าง (3 ข้อ)
7. Hairpin NAT แก้ปัญหาอะไร และมีทางเลือกอื่นอย่างไร
8. ผู้ใช้บ้านเห็น IP ขา WAN เป็น 100.72.x.x หมายความว่าอะไร
9. ทำไม IPsec ต้องใช้ NAT-T
10. ทำไมกล่าวว่า "NAT ไม่ใช่ security"

<details><summary><b>เฉลย</b></summary>

1. IPv4 ไม่พอ — ใช้ private IP ภายในแล้วแปลงเป็น public IP ตอนออกอินเทอร์เน็ต
2. แปลง source port ให้ไม่ซ้ำกันและบันทึกใน NAT translation table เพื่อแปลงกลับเมื่อมีคำตอบ
3. Inside Local = IP จริงของเครื่องภายใน; Inside Global = IP ที่ใช้แทนเครื่องนั้นเมื่อมองจากภายนอก
4. Server ที่ต้องให้ภายนอกเข้าถึงด้วย public IP คงที่
5. SNAT แปลง IP ต้นทาง (ภายในออกนอก); DNAT แปลง IP ปลายทาง (ภายนอกเข้ามาหา server)
6. Firewall policy อนุญาตหรือยัง, server เปิดบริการและ firewall ในเครื่องอนุญาต, ISP ใช้ CGNAT หรือ block port, NAT rule ถูก IP/port
7. ผู้ใช้ภายในเข้าถึง server ภายในผ่าน public IP ของบริษัท; ทางเลือกคือ split-horizon DNS
8. อยู่หลัง CGNAT ของ ISP — ไม่มี public IP จริง เปิด port forwarding ให้ภายนอกเข้ามาไม่ได้
9. ESP ไม่มี port ให้ PAT ใช้แยก session และการแก้ header ทำให้การตรวจความถูกต้องล้มเหลว — NAT-T ห่อด้วย UDP 4500
10. NAT แค่แปลงที่อยู่ ไม่ได้ตรวจเนื้อหาหรือควบคุมการเชื่อมต่อออกตามนโยบาย ต้องใช้ firewall ทำหน้าที่นั้น
</details>

---

➡️ ต่อไป: **Level 18 — IPv6 พื้นฐาน**
