# บทเรียน Level 25 — dig, curl, openssl, nc, iperf (ฉบับละเอียด)

> อ่านจบแล้วจะ: มี "ชุดเครื่องมือพกพา" 5 ตัวที่วิศวกรใช้ทุกวัน · ทดสอบ DNS, HTTP, TLS/cert, port และ bandwidth จาก command line ได้ · วิเคราะห์ว่าความช้าเกิดที่ขั้นไหน

---

## 1. ภาพรวม: เครื่องมือไหนตอบคำถามอะไร

| คำถาม | เครื่องมือ |
|---|---|
| ชื่อนี้ resolve เป็นอะไร? DNS ตอบถูกไหม? | **dig** / nslookup / Resolve-DnsName |
| เว็บ/API ตอบอะไร? ช้าที่ขั้นไหน? | **curl** |
| Certificate ถูก/หมดอายุเมื่อไร? TLS version? | **openssl s_client** |
| Port นี้เปิดไหม? ส่งข้อมูลดิบทดสอบ | **nc (netcat)** / Test-NetConnection |
| ลิงก์นี้รับ-ส่งได้กี่ Mbps จริง? | **iperf3** |

---

## 2. dig — ทดสอบ DNS

```bash
dig example.com                    # A record + รายละเอียด
dig example.com +short             # เฉพาะคำตอบ
dig @8.8.8.8 example.com           # ถาม DNS server ที่ระบุ
dig example.com AAAA / MX / TXT / NS / SOA / CAA
dig -x 203.0.113.10                # reverse lookup (PTR)
dig +trace example.com             # ไล่จาก root → TLD → authoritative
dig example.com +noall +answer     # เฉพาะ answer section
dig _ldap._tcp.dc._msdcs.corp.local SRV   # ตรวจ SRV ของ Active Directory
```

**เทคนิคแก้ปัญหา**
- **เทียบคำตอบ 2 server:** `dig @10.0.0.53 app.corp.com` vs `dig @8.8.8.8 app.corp.com` → ถ้าต่างกัน อาจเป็น split-horizon (ตั้งใจ) หรือ record ไม่ตรงกัน (ผิดพลาด)
- **ตรวจ TTL ที่เหลือ:** ตัวเลขหลังชื่อใน answer ลดลงเรื่อย ๆ เมื่อถาม resolver ที่ cache อยู่
- **ถาม authoritative โดยตรง** (`dig @ns1.example.com example.com`) เพื่อดูค่าจริงล่าสุดโดยไม่ผ่าน cache
- Windows ที่ไม่มี dig: `Resolve-DnsName example.com -Type MX -Server 8.8.8.8`

---

## 3. curl — ทดสอบเว็บและ API

```bash
curl https://example.com                         # ดึงเนื้อหา
curl -I https://example.com                      # เฉพาะ header (HEAD)
curl -v https://example.com                      # verbose: DNS, connect, TLS, request, response header
curl -L http://example.com                       # ตาม redirect
curl -o /dev/null -s -w "%{http_code}\n" URL     # แสดงแค่ status code
curl -k https://10.0.0.5                         # ข้ามการตรวจ cert (ทดสอบเท่านั้น)
curl -H "Host: shop.example.com" http://10.0.0.5 # ส่ง Host header เอง
curl --resolve shop.example.com:443:10.0.0.5 https://shop.example.com   # บังคับชื่อ→IP (ทดสอบก่อนย้าย DNS)
curl -x http://proxy.corp:8080 https://example.com    # ผ่าน proxy
curl -u user:pass https://api.example.com        # basic auth
curl -X POST -H "Content-Type: application/json" -d '{"name":"test"}' https://api.example.com/items
curl -4 / -6 URL                                 # บังคับ IPv4 / IPv6
curl --http2 / --http3 URL                       # บังคับเวอร์ชัน
```

### วัดเวลาแต่ละขั้น (สำคัญมาก)
```bash
curl -o /dev/null -s -w "\
dns=%{time_namelookup}s\n\
connect=%{time_connect}s\n\
tls=%{time_appconnect}s\n\
ttfb=%{time_starttransfer}s\n\
total=%{time_total}s\n\
code=%{http_code} ip=%{remote_ip}\n" https://example.com
```
```
dns=0.012s        ← DNS
connect=0.030s    ← +TCP handshake (≈ RTT)
tls=0.075s        ← +TLS handshake
ttfb=0.420s       ← +รอ server ประมวลผล (Time To First Byte)
total=0.510s      ← +ดาวน์โหลดเนื้อหา
```

| ค่าที่สูงผิดปกติ | ปัญหาน่าจะอยู่ที่ |
|---|---|
| dns | DNS server ช้า/timeout (มักเห็นเป็น 5 วินาทีพอดี = timeout แล้วลอง server ถัดไป) |
| connect − dns | เครือข่าย/ระยะทาง/firewall |
| tls − connect | TLS (cert chain, OCSP, CPU server) |
| ttfb − tls | **แอปหรือฐานข้อมูลฝั่ง server** |
| total − ttfb | ขนาดเนื้อหาใหญ่/bandwidth ต่ำ |

---

## 4. openssl — ตรวจ TLS และ Certificate

```bash
# เชื่อมต่อแล้วดู cert chain, TLS version, cipher
openssl s_client -connect example.com:443 -servername example.com

# ดูวันหมดอายุ, subject, SAN แบบสั้น
echo | openssl s_client -connect example.com:443 -servername example.com 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates -ext subjectAltName

# ทดสอบว่ารองรับ TLS version ไหน
openssl s_client -connect example.com:443 -tls1_2
openssl s_client -connect example.com:443 -tls1_3

# ดูไฟล์ cert / ตรวจ chain / ตรวจว่า key ตรงกับ cert
openssl x509 -in cert.pem -text -noout
openssl verify -CAfile chain.pem cert.pem
openssl x509 -noout -modulus -in cert.pem | openssl md5
openssl rsa  -noout -modulus -in key.pem  | openssl md5     # ค่าต้องตรงกัน

# STARTTLS (อีเมล)
openssl s_client -connect mail.example.com:587 -starttls smtp
```
**สิ่งที่ดูในผล s_client:**
- `Certificate chain` — มี intermediate ครบไหม (depth 0 = server, 1 = intermediate)
- `Verify return code: 0 (ok)` — ผ่าน · เลขอื่น = มีปัญหา (เช่น 20/21 = chain ไม่ครบ, 10 = หมดอายุ)
- `Protocol : TLSv1.3`, `Cipher : TLS_AES_256_GCM_SHA384`
- **ต้องใส่ `-servername`** ไม่เช่นนั้นอาจได้ cert ผิดตัว (ไม่ส่ง SNI)

---

## 5. nc (netcat) — มีดพับสวิสของ TCP/UDP

```bash
nc -zv 10.0.0.5 443            # ทดสอบ port TCP เปิดไหม (z = ไม่ส่งข้อมูล)
nc -zv 10.0.0.5 20-25          # ช่วง port
nc -zvu 10.0.0.5 161           # UDP (ผลไม่แน่นอน)
nc -l 9000                     # เปิด listen ที่ port 9000 (ทดสอบ firewall ว่าผ่านมาถึงไหม)
nc 10.0.0.5 9000               # อีกเครื่องเชื่อมต่อแล้วพิมพ์ข้อความคุยกัน
printf 'GET / HTTP/1.0\r\nHost: example.com\r\n\r\n' | nc example.com 80   # ส่ง HTTP ด้วยมือ
nc -w 3 mail.example.com 25    # ดู SMTP banner
```
**เทคนิคทดสอบ firewall ก่อนติดตั้งบริการจริง:** เปิด `nc -l <port>` ที่ server ปลายทาง แล้ว `nc -zv` จากต้นทาง ถ้าเชื่อมต่อได้ = เส้นทางและ firewall พร้อมแล้ว

**Windows:** `Test-NetConnection host -Port 443` ทำงานแบบ `nc -zv`

---

## 6. iperf3 — วัด Bandwidth จริง

ต้องมี 2 เครื่อง: **server** และ **client**

```bash
# เครื่อง A (server)
iperf3 -s
# เครื่อง B (client)
iperf3 -c 10.0.0.5              # TCP 10 วินาที client → server (upload)
iperf3 -c 10.0.0.5 -R           # Reverse: server → client (download)
iperf3 -c 10.0.0.5 -P 4         # 4 stream พร้อมกัน (ใช้ลิงก์ได้เต็มขึ้น)
iperf3 -c 10.0.0.5 -t 60 -i 5   # 60 วินาที แสดงทุก 5 วินาที
iperf3 -c 10.0.0.5 --bidir      # ทั้งสองทางพร้อมกัน
iperf3 -c 10.0.0.5 -u -b 50M    # UDP ที่ 50 Mbps → ดู jitter และ loss
```
```
[ ID] Interval       Transfer     Bitrate         Retr
[  5] 0.00-10.00 sec 1.09 GBytes  938 Mbits/sec   12     ← ลิงก์ 1G ได้ ~940 Mbps = ปกติ
UDP: ... Jitter 0.120 ms  Lost/Total 3/43000 (0.007%)
```
**การตีความ**
- ลิงก์ 1 Gbps ได้ ~940 Mbps = ปกติ (หัก overhead)
- single stream ได้น้อย แต่ `-P 8` ได้เต็ม → ข้อจำกัดต่อ flow (window/RTT/CPU) ไม่ใช่ลิงก์
- `Retr` สูง = มี loss
- UDP test เหมาะวัดคุณภาพสำหรับ VoIP/วิดีโอ (jitter/loss)
- ⚠️ อย่ารัน iperf บนลิงก์ production เวลาทำงานโดยไม่แจ้ง เพราะใช้แบนด์วิดท์เต็ม; iperf3 server ที่เปิดทิ้งไว้ควรปิดหลังใช้

---

## 7. รวมพลัง: แก้ปัญหา "เว็บภายใน app.corp.com ใช้ไม่ได้"

```
 1) dig app.corp.com +short                    → ได้ IP ไหม ถูกต้องไหม
 2) nc -zv <IP> 443                            → port เปิดและผ่าน firewall ไหม
 3) openssl s_client -connect <IP>:443 -servername app.corp.com → cert ถูก/ไม่หมดอายุ
 4) curl -v https://app.corp.com               → status code / error ของแอป
 5) curl -w timing                             → ช้าที่ DNS / network / TLS / แอป
 6) iperf3 (ถ้าสงสัยเรื่อง bandwidth ระหว่างสาขา)
```

---

## 8. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| `curl -k` แก้ปัญหา cert | แค่ข้ามการตรวจ ปัญหายังอยู่ |
| openssl s_client ไม่ต้องใส่ -servername | ไม่ใส่ = ไม่ส่ง SNI อาจได้ cert ผิด |
| speedtest = iperf | speedtest วัดไป server อินเทอร์เน็ต; iperf วัดระหว่าง 2 จุดที่เราเลือก |
| iperf single stream ต่ำ = ลิงก์เสีย | อาจเป็นข้อจำกัดของ TCP window/RTT ลอง -P |

---

## 9. Cheat Sheet

```
dig name +short · dig @server name · dig -x IP · dig +trace name · dig name MX
curl -I · curl -v · curl -L · curl --resolve host:443:IP https://host
curl -o /dev/null -s -w "dns=%{time_namelookup} conn=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer}\n"
openssl s_client -connect h:443 -servername h | openssl x509 -noout -dates -ext subjectAltName
nc -zv host port · nc -l port (ทดสอบ firewall)
iperf3 -s · iperf3 -c IP [-R] [-P 4] [-u -b 50M]
```

---

## 10. แบบทดสอบ 10 ข้อ

1. คำสั่ง dig ถาม DNS server 1.1.1.1 ให้แสดงเฉพาะ IP ของ example.com
2. ต้องการทดสอบ server ใหม่ 10.0.0.9 ด้วยชื่อ www.example.com ก่อนเปลี่ยน DNS ใช้คำสั่งอะไร
3. curl timing พบว่า dns = 5.01 วินาที ส่วนอื่นปกติ สรุปว่าอะไร
4. ค่า TTFB สูงบอกอะไร
5. คำสั่งดูวันหมดอายุของ cert ของ mail.example.com port 443
6. openssl s_client แสดง `Verify return code: 21 (unable to verify the first certificate)` น่าจะเป็นปัญหาอะไร
7. จะทดสอบว่า firewall เปิด port 5000 จากเครื่อง A ไป B แล้ว ก่อนติดตั้งแอปจริงอย่างไร
8. iperf3 option ใดวัดทิศทาง server → client
9. iperf3 single stream ได้ 200 Mbps แต่ -P 8 ได้ 900 Mbps บนลิงก์ 1G หมายความว่าอะไร
10. วัด jitter และ packet loss สำหรับเตรียมระบบ VoIP ด้วย iperf3 อย่างไร

<details><summary><b>เฉลย</b></summary>

1. `dig @1.1.1.1 example.com +short`
2. `curl --resolve www.example.com:443:10.0.0.9 https://www.example.com`
3. DNS server แรกไม่ตอบ (timeout 5 วินาที) แล้วจึงลองตัวถัดไป — ตรวจ DNS server ตัวแรกที่เครื่องตั้งไว้
4. Server/แอป/ฐานข้อมูลประมวลผลช้า
5. `echo | openssl s_client -connect mail.example.com:443 -servername mail.example.com 2>/dev/null | openssl x509 -noout -dates`
6. Server ไม่ส่ง intermediate certificate (chain ไม่ครบ)
7. ที่ B รัน `nc -l 5000` แล้วที่ A รัน `nc -zv <B> 5000`
8. `-R`
9. ลิงก์ปกติ แต่การเชื่อมต่อเดียวถูกจำกัดด้วย TCP window/RTT หรือ CPU
10. `iperf3 -c <server> -u -b <อัตราที่ต้องการ>` แล้วดูค่า Jitter และ Lost/Total
</details>

---

➡️ ต่อไป: **Level 26 — Linux Networking Configuration**
