# บทเรียน Level 14 — UDP & Port Numbers (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจ UDP และเมื่อไรควรใช้แทน TCP · เข้าใจ port, socket และ 5-tuple · จำ port สำคัญที่ใช้ในงานได้ · ตรวจว่าเครื่องเปิด port อะไรอยู่

---

## 1. UDP คืออะไร

**UDP (User Datagram Protocol)** คือโปรโตคอลชั้น **Transport (L4)** แบบ
- **Connectionless:** ไม่ต้อง handshake ส่งได้ทันที
- **Unreliable (best effort):** ไม่มี ACK, ไม่ส่งซ้ำ, ไม่เรียงลำดับ
- **เบามาก:** header แค่ **8 ไบต์** (TCP อย่างน้อย 20 ไบต์)
- รองรับ **broadcast/multicast** (TCP ทำไม่ได้)

```
 ┌───────────────┬────────────────┐
 │ Source Port   │ Dest Port      │
 ├───────────────┼────────────────┤
 │ Length        │ Checksum       │   ← ทั้งหมดแค่ 8 ไบต์
 └───────────────┴────────────────┘
```

> 💡 **เปรียบเทียบ:** TCP = พัสดุลงทะเบียนมีใบตอบรับ · **UDP = แจกใบปลิว/ประกาศเสียงตามสาย** ส่งออกไปเลย ไม่รอใครตอบ ไม่ตามว่าถึงหรือไม่

### ทำไมต้องใช้ UDP ทั้งที่ไม่รับประกัน

| งาน | เหตุผลที่ใช้ UDP |
|---|---|
| **DNS** | ถาม-ตอบสั้น ๆ ไม่คุ้มที่จะ handshake (หายก็ถามใหม่) |
| **VoIP / วิดีโอคอล / เกม** | ข้อมูลที่มาช้าไร้ประโยชน์ เสียงที่ส่งซ้ำมาช้าแย่กว่าเสียงขาดนิดเดียว |
| **Live streaming / IPTV** | เวลาสำคัญกว่าความครบ, ใช้ multicast ได้ |
| **DHCP** | เครื่องยังไม่มี IP ต้อง broadcast |
| **SNMP, Syslog, NTP, TFTP** | ข้อความสั้น overhead ต่ำ |
| **QUIC / HTTP/3** | สร้างความน่าเชื่อถือเองในระดับแอป เร็วกว่า TCP+TLS |
| **VPN (WireGuard, IPsec NAT-T)** | ห่อ traffic ด้านในที่จัดการความน่าเชื่อถือเองอยู่แล้ว |

### TCP vs UDP

| | TCP | UDP |
|---|---|---|
| การเชื่อมต่อ | ต้อง handshake | ไม่ต้อง |
| รับประกันการถึง/ลำดับ | ✅ | ❌ |
| Header | 20–60 byte | 8 byte |
| ความเร็ว/latency | ช้ากว่า | เร็วกว่า |
| Flow/Congestion control | ✅ | ❌ (แอปต้องทำเอง) |
| Broadcast/Multicast | ❌ | ✅ |
| ตัวอย่าง | HTTP/1-2, SSH, SMTP, DB | DNS, VoIP, DHCP, QUIC |

> ⚠️ เพราะ UDP ไม่มี handshake **การทดสอบ port UDP จึงยากกว่า**: ส่งไปแล้วไม่มีคำตอบ อาจเป็นได้ทั้ง "เปิดอยู่แต่ไม่ตอบ" หรือ "ถูก firewall drop" (ถ้า port ปิด ปลายทางมักตอบ ICMP Port Unreachable)

---

## 2. Port Number คืออะไร

IP พาข้อมูลไปถึง **เครื่อง** ส่วน **port** พาไปถึง **โปรแกรม** ในเครื่องนั้น

> 💡 IP = ที่อยู่อาคาร · Port = เลขห้อง (ห้อง 443 คือแผนกเว็บ, ห้อง 22 คือแผนก SSH)

- เป็นตัวเลข **16 บิต** → 0–65535 แยกกันระหว่าง TCP และ UDP (TCP 53 กับ UDP 53 เป็นคนละ port)

| ช่วง | ชื่อ | ใช้ทำอะไร |
|---|---|---|
| **0–1023** | Well-known | บริการมาตรฐาน (ต้องใช้สิทธิ์ admin/root จึงจะ listen ได้บน Linux) |
| **1024–49151** | Registered | แอปพลิเคชันที่ลงทะเบียนกับ IANA (เช่น 3306 MySQL, 3389 RDP) |
| **49152–65535** | Dynamic/Ephemeral | **port ฝั่ง client** ที่ OS สุ่มให้ชั่วคราว (Linux มักใช้ 32768–60999) |

### ตัวอย่างการเชื่อมต่อ
```
 Client 192.168.1.10 : 51544   ───►   Server 93.184.216.34 : 443
        (ephemeral port สุ่ม)               (well-known port ของ HTTPS)
```
เปิดหลายแท็บพร้อมกัน แต่ละแท็บได้ port ต้นทางต่างกัน จึงแยกข้อมูลของแต่ละแท็บได้

---

## 3. Socket และ 5-Tuple

- **Socket** = IP + Protocol + Port (จุดปลายของการสื่อสาร) เช่น `TCP 93.184.216.34:443`
- **5-Tuple** = ตัวระบุการเชื่อมต่อหนึ่งรายการให้ไม่ซ้ำกัน
  1. Source IP
  2. Destination IP
  3. Source Port
  4. Destination Port
  5. Protocol (TCP/UDP)

**ใช้ที่ไหน:** firewall/NAT ใช้ 5-tuple ติดตาม session, load balancer/ECMP ใช้ hash ของ 5-tuple เลือกเส้นทาง, NetFlow บันทึก flow ตาม 5-tuple

---

## 4. Port ที่ต้องจำ (ถูกถามบ่อยในงานและการสอบ)

### บริการพื้นฐาน
| Port | Protocol | บริการ |
|---|---|---|
| 20/21 | TCP | FTP (data/control) |
| **22** | TCP | **SSH**, SFTP, SCP |
| 23 | TCP | Telnet (ไม่เข้ารหัส ห้ามใช้ในงานจริง) |
| **25** | TCP | **SMTP** (ส่งอีเมลระหว่าง server) |
| **53** | **UDP**/TCP | **DNS** |
| **67/68** | UDP | **DHCP** (server/client) |
| 69 | UDP | TFTP (backup config, PXE boot) |
| **80** | TCP | **HTTP** |
| 110 | TCP | POP3 |
| **123** | UDP | **NTP** (เวลา) |
| 143 | TCP | IMAP |
| **161/162** | UDP | **SNMP** / SNMP Trap |
| 389 | TCP/UDP | LDAP |
| **443** | TCP (+UDP สำหรับ QUIC) | **HTTPS** |
| 445 | TCP | SMB (แชร์ไฟล์ Windows) |
| **514** | UDP | **Syslog** |
| 587 | TCP | SMTP submission (client ส่งอีเมล) |
| 636 | TCP | LDAPS |
| 993/995 | TCP | IMAPS/POP3S |

### Enterprise / ระบบที่เจอในงาน
| Port | บริการ |
|---|---|
| 88 | Kerberos (Active Directory) |
| 500, 4500 (UDP) | IPsec IKE / NAT-T |
| 1194 (UDP) | OpenVPN |
| 51820 (UDP) | WireGuard |
| 1812/1813 (UDP) | RADIUS auth/accounting |
| 49 (TCP) | TACACS+ |
| 1433 | Microsoft SQL Server |
| 1521 | Oracle DB |
| 3306 | MySQL/MariaDB |
| 5432 | PostgreSQL |
| **3389** | **RDP** (Remote Desktop) |
| 5060/5061 | SIP (VoIP) |
| 5985/5986 | WinRM (PowerShell remoting) |
| 8080/8443 | HTTP/HTTPS ทางเลือก (proxy, หน้า admin) |
| 179 (TCP) | BGP |
| 830 (TCP) | NETCONF |

> 💡 **เคล็ดลับจำ:** ท่องเป็นกลุ่ม: "เว็บ 80/443 · รีโมต 22/3389 · ชื่อ 53 · เวลา 123 · แจก IP 67/68 · มอนิเตอร์ 161/162/514 · อีเมล 25/587/993"

---

## 5. ตรวจ port บนเครื่องและปลายทาง

### เครื่องเรากำลังเปิด (listen) port อะไรอยู่
```bash
ss -tulpn                         # Linux: t=TCP u=UDP l=listen p=process n=numeric
netstat -ano | findstr LISTENING  # Windows
Get-NetTCPConnection -State Listen | Sort LocalPort   # PowerShell
lsof -i -P | grep LISTEN          # macOS
```
**`0.0.0.0:22`** = รับจากทุก interface · **`127.0.0.1:5432`** = รับเฉพาะในเครื่อง (ปลอดภัยกว่า)

### ปลายทางเปิด port ไหม
```bash
Test-NetConnection 10.0.0.5 -Port 3389   # Windows
nc -zv 10.0.0.5 443                      # Linux/macOS (TCP)
nc -zvu 10.0.0.5 53                      # UDP (ผลไม่แน่นอน)
curl -v telnet://10.0.0.5:25             # ทางเลือก
nmap -p 22,80,443 10.0.0.5               # เครือข่ายของตัวเอง/ที่ได้รับอนุญาตเท่านั้น
```

---

## 6. Port กับความปลอดภัย

- **เปิดเฉพาะ port ที่จำเป็น** (หลัก least privilege) ทั้งที่ host firewall และ network firewall
- **ห้ามเปิด RDP (3389), SMB (445), Telnet (23), database port สู่อินเทอร์เน็ตโดยตรง** เป็นช่องทางหลักของ ransomware → ใช้ VPN/ZTNA แทน
- **การเปลี่ยน port** (เช่น SSH เป็น 2222) ลดการสแกนอัตโนมัติได้บ้าง แต่ **ไม่ใช่การป้องกันที่แท้จริง**
- NGFW ระบุ **แอปพลิเคชัน** ได้ไม่ว่าจะวิ่ง port ไหน เพราะมัลแวร์และแอปมักใช้ 443 หลบ

---

## 7. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| UDP แย่กว่า TCP เสมอ | เหมาะกับงาน real-time และ query สั้น ๆ มากกว่า |
| DNS ใช้ UDP อย่างเดียว | ใช้ TCP เมื่อคำตอบใหญ่ zone transfer และ DNS over TLS |
| HTTPS ใช้ TCP เท่านั้น | HTTP/3 ใช้ QUIC บน **UDP 443** |
| port ฝั่ง client คือ port เดียวกับ server | client ใช้ ephemeral port สุ่ม |
| ทดสอบ UDP แล้วไม่ตอบ = port ปิด | อาจเปิดอยู่แต่ไม่ตอบ หรือถูก drop |

---

## 8. Cheat Sheet

```
UDP: connectionless, ไม่รับประกัน, header 8B, รองรับ broadcast/multicast
ใช้กับ: DNS, DHCP, VoIP, video, game, NTP, SNMP, Syslog, QUIC, WireGuard
Port 16 บิต: 0-1023 well-known · 1024-49151 registered · 49152-65535 ephemeral
5-tuple: SrcIP DstIP SrcPort DstPort Protocol
22 SSH · 23 Telnet · 25 SMTP · 53 DNS · 67/68 DHCP · 80 HTTP · 123 NTP
161/162 SNMP · 443 HTTPS · 445 SMB · 514 Syslog · 3389 RDP · 1812 RADIUS
ดู listen: ss -tulpn / netstat -ano · ทดสอบ: Test-NetConnection -Port / nc -zv
```

---

## 9. แบบทดสอบ 10 ข้อ

1. UDP header มีกี่ไบต์ มี field อะไรบ้าง
2. ทำไม VoIP นิยมใช้ UDP
3. ทำไม DNS ใช้ UDP เป็นหลัก แต่บางกรณีใช้ TCP
4. ช่วง port well-known และ ephemeral คือเท่าไร
5. 5-tuple ประกอบด้วยอะไร
6. RDP, SNMP Trap, Syslog, NTP ใช้ port อะไร
7. HTTP/3 วิ่งบน TCP หรือ UDP
8. คำสั่งดูว่าเครื่อง Linux เปิด port อะไรพร้อมชื่อโปรแกรม
9. `127.0.0.1:5432` กับ `0.0.0.0:5432` ในผล `ss` ต่างกันอย่างไร
10. ทำไมไม่ควรเปิด RDP 3389 สู่อินเทอร์เน็ตโดยตรง ควรใช้อะไรแทน

<details><summary><b>เฉลย</b></summary>

1. 8 ไบต์: Source Port, Destination Port, Length, Checksum
2. latency ต่ำสำคัญกว่าความครบ ข้อมูลเสียงที่ส่งซ้ำมาช้าใช้ไม่ได้แล้ว
3. ถาม-ตอบสั้น ใช้ UDP เร็วและเบา; ใช้ TCP เมื่อคำตอบใหญ่ zone transfer หรือ DNS over TLS
4. Well-known 0–1023; ephemeral 49152–65535 (ตาม IANA)
5. Source IP, Destination IP, Source Port, Destination Port, Protocol
6. RDP 3389/TCP, SNMP Trap 162/UDP, Syslog 514/UDP, NTP 123/UDP
7. UDP (QUIC, port 443)
8. `ss -tulpn`
9. 127.0.0.1 รับเฉพาะในเครื่อง; 0.0.0.0 รับจากทุก interface (เข้าจากเครือข่ายได้)
10. ถูกสแกนและ brute force ตลอดเวลา มีช่องโหว่ร้ายแรงในอดีต เป็นทางเข้าของ ransomware — ใช้ VPN/ZTNA + MFA หรือ RD Gateway แทน
</details>

---

➡️ ต่อไป: **Level 15 — DHCP**
