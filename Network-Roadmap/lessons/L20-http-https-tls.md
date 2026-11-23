# บทเรียน Level 20 — HTTP, HTTPS & TLS พื้นฐาน (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจ HTTP request/response, method, status code, header, cookie · HTTP/1.1 vs 2 vs 3 · TLS handshake, certificate, SNI · ใช้ curl/openssl/DevTools แก้ปัญหาเว็บได้ · ตอบคำถามสัมภาษณ์ "พิมพ์ URL แล้วเกิดอะไรขึ้น" ได้ครบ

---

## 1. HTTP คืออะไร

**HTTP (HyperText Transfer Protocol)** คือโปรโตคอลชั้น Application ที่ browser/แอปใช้คุยกับ web server แบบ **request–response**
- **Stateless:** server ไม่จำ request ก่อนหน้าเอง (จึงต้องใช้ cookie/token จำสถานะการ login)
- **HTTP** port 80 (ไม่เข้ารหัส) · **HTTPS** = HTTP + TLS port 443 (เข้ารหัส)

### โครงสร้าง URL
```
 https://shop.example.com:443/products/list?page=2&sort=price#top
 └scheme┘└──── host ──────┘└port┘└─── path ───┘└──── query ────┘└fragment┘
```

---

## 2. HTTP Request และ Response

### Request
```
GET /products/list?page=2 HTTP/1.1          ← method, path, version
Host: shop.example.com                       ← จำเป็น (server เดียวมีหลายเว็บ)
User-Agent: Mozilla/5.0 ...
Accept: text/html
Cookie: session=abc123
Authorization: Bearer eyJ...
                                             ← บรรทัดว่าง
(body — สำหรับ POST/PUT)
```

### Response
```
HTTP/1.1 200 OK                              ← status code
Content-Type: text/html; charset=utf-8
Content-Length: 5120
Set-Cookie: session=abc123; Secure; HttpOnly
Cache-Control: max-age=3600
Strict-Transport-Security: max-age=31536000

<html>...                                    ← body
```

### HTTP Methods
| Method | ใช้ทำ | ตัวอย่าง |
|---|---|---|
| **GET** | ขอข้อมูล | เปิดหน้าเว็บ |
| **POST** | ส่งข้อมูล/สร้างใหม่ | ส่งฟอร์ม, login |
| **PUT / PATCH** | แก้ไขทั้งหมด / บางส่วน | แก้ข้อมูลผ่าน API |
| **DELETE** | ลบ | ลบรายการผ่าน API |
| **HEAD** | ขอเฉพาะ header | ตรวจว่าไฟล์มีไหม |
| **OPTIONS** | ถามว่ารองรับอะไร | CORS preflight |

### Status Codes — ต้องจำเป็นกลุ่ม
| กลุ่ม | ความหมาย | ที่เจอบ่อย |
|---|---|---|
| **1xx** | กำลังดำเนินการ | 101 Switching Protocols (WebSocket) |
| **2xx** | สำเร็จ | **200 OK**, 201 Created, 204 No Content |
| **3xx** | เปลี่ยนเส้นทาง | **301** ย้ายถาวร, **302** ชั่วคราว, 304 Not Modified (ใช้ cache) |
| **4xx** | **ฝั่ง client ผิด** | 400 Bad Request, **401** ยังไม่ยืนยันตัวตน, **403** ไม่มีสิทธิ์, **404** ไม่พบ, 429 ขอถี่เกิน |
| **5xx** | **ฝั่ง server ผิด** | **500** แอป error, **502** Bad Gateway, **503** ไม่พร้อมให้บริการ, **504** Gateway Timeout |

> 🔑 **502 vs 504 (ถูกถามบ่อยมาก):** ทั้งคู่เกิดที่ **proxy/load balancer** ที่อยู่หน้า server
> - **502 Bad Gateway** = upstream (server หลังบ้าน) **ตอบผิดรูปแบบหรือปฏิเสธการเชื่อมต่อ** (แอปล่ม, port ปิด)
> - **504 Gateway Timeout** = upstream **ตอบช้าเกิน** เวลาที่ proxy รอ (แอปค้าง, DB ช้า, firewall drop)

### Headers ที่ควรรู้
- `Host` — ชื่อเว็บ (virtual hosting) · `Cookie`/`Set-Cookie` — สถานะ session
- `Cache-Control`, `ETag` — การ cache · `Content-Type` — ชนิดข้อมูล
- `X-Forwarded-For` — IP จริงของ client เมื่อผ่าน proxy/LB
- `Location` — ปลายทางของ redirect
- Security headers: `Strict-Transport-Security` (บังคับ HTTPS), `Content-Security-Policy`, `X-Frame-Options`

---

## 3. HTTP Versions

| เวอร์ชัน | Transport | จุดเด่น | ปัญหา |
|---|---|---|---|
| **HTTP/1.1** (1997) | TCP | keep-alive (ใช้ connection ซ้ำ) | ทีละ request ต่อ connection → browser เปิดหลาย connection |
| **HTTP/2** (2015) | TCP + TLS | **Multiplexing** หลาย request ใน connection เดียว, header compression, binary | packet หาย 1 ตัวทำให้ทุก stream ใน TCP รอ (head-of-line blocking) |
| **HTTP/3** (2022) | **QUIC บน UDP 443** | แก้ HoL blocking, handshake เร็ว (รวม TLS 1.3), ย้ายเครือข่ายได้ไม่หลุด (Wi-Fi→4G) | firewall บางแห่ง block UDP 443 → browser ย้อนไปใช้ HTTP/2 |

---

## 4. HTTPS และ TLS

**TLS (Transport Layer Security)** ให้ 3 อย่าง
1. **Confidentiality** — เข้ารหัส คนกลางทางอ่านไม่ได้
2. **Integrity** — แก้ไขระหว่างทางไม่ได้โดยไม่ถูกจับได้
3. **Authentication** — ยืนยันว่าเป็นเว็บจริงด้วย **certificate**

(SSL คือชื่อรุ่นเก่า ปัจจุบันใช้ **TLS 1.2 และ 1.3** — SSLv3, TLS 1.0, 1.1 ควรปิดทั้งหมด)

### การเข้ารหัส 2 แบบที่ TLS ใช้ร่วมกัน
- **Asymmetric (public/private key):** ใช้ตอน handshake เพื่อยืนยันตัวตนและตกลงกุญแจอย่างปลอดภัย (ช้า)
- **Symmetric (เช่น AES):** ใช้เข้ารหัสข้อมูลจริงหลังตกลงกุญแจแล้ว (เร็ว)

### TLS 1.3 Handshake (ย่อ) — ใช้ 1 RTT
```
 Client                                                Server
  │ ClientHello: TLS versions, cipher suites,           │
  │   key share (ECDHE), SNI = shop.example.com ─────────►│
  │                                                      │
  │◄────── ServerHello: เลือก cipher + key share          │
  │        {Certificate, CertificateVerify, Finished}   │  ← เข้ารหัสแล้ว
  │                                                      │
  │ ตรวจ certificate → {Finished} ───────────────────────►│
  │ ═══════════ ข้อมูล HTTP เข้ารหัสด้วยกุญแจ symmetric ═══════════ │
```
- TLS 1.2 ใช้ 2 RTT · TLS 1.3 ใช้ **1 RTT** (และ 0-RTT เมื่อกลับมาเชื่อมต่อซ้ำ)
- **ECDHE** ให้ **Forward Secrecy**: กุญแจแต่ละ session สร้างใหม่ ถ้า private key ของ server รั่วในอนาคต ก็ถอดรหัสข้อมูลที่ดักไว้ก่อนหน้าไม่ได้

### SNI (Server Name Indication)
- server/IP เดียวโฮสต์หลายเว็บ แต่ละเว็บมี certificate ของตัวเอง → client บอกชื่อเว็บใน ClientHello เพื่อให้ server เลือก cert ถูกตัว
- SNI ปกติ **ไม่ได้เข้ารหัส** firewall จึงใช้ SNI ระบุเว็บได้แม้ไม่ถอดรหัส (ECH เป็นเทคโนโลยีใหม่ที่เข้ารหัสส่วนนี้)

---

## 5. Certificate และ Chain of Trust

```
 Root CA (อยู่ในเครื่อง/browser แล้ว — trust store)
   └── Intermediate CA  (server ต้องส่งให้ client ด้วย)
         └── Server certificate: CN/SAN = shop.example.com
```
Browser ตรวจว่า
1. cert ลงลายเซ็นต่อกันจนถึง Root CA ที่เชื่อถือ
2. **ชื่อใน SAN ตรงกับ hostname** ที่เปิด
3. **ยังไม่หมดอายุ** และยังไม่ถูกเพิกถอน (revoke)

**ข้อผิดพลาดที่พบบ่อย**
| คำเตือน | สาเหตุ |
|---|---|
| `NET::ERR_CERT_DATE_INVALID` | cert หมดอายุ (หรือนาฬิกาเครื่องผิด) |
| `ERR_CERT_COMMON_NAME_INVALID` | ชื่อไม่ตรง SAN (เช่น cert ของ www แต่เปิดชื่อเปล่า) |
| `ERR_CERT_AUTHORITY_INVALID` | self-signed หรือ CA ภายในที่เครื่องไม่รู้จัก |
| ใช้ได้บน browser แต่ app/curl ฟ้อง | server **ไม่ส่ง intermediate cert** (browser บางตัวหาเองได้) |

> 🏢 cert จาก Let's Encrypt มีอายุ 90 วัน และอุตสาหกรรมกำลังลดอายุสูงสุดของ cert ลงเรื่อย ๆ → ต้อง **ต่ออายุอัตโนมัติ (ACME)** และ **monitor วันหมดอายุ** cert หมดอายุเป็นสาเหตุ outage ที่พบบ่อยมาก

---

## 6. เครื่องมือแก้ปัญหาเว็บ

```bash
curl -I https://example.com                 # ดูเฉพาะ header/status
curl -v https://example.com                 # ดูทุกขั้น: DNS, TCP, TLS, request, response
curl -L http://example.com                  # ตาม redirect
curl -k https://10.0.0.5                    # ข้ามการตรวจ cert (ใช้ทดสอบเท่านั้น)
curl --resolve shop.example.com:443:10.0.0.5 https://shop.example.com   # ทดสอบ server ใหม่ก่อนเปลี่ยน DNS
curl -o /dev/null -s -w "dns=%{time_namelookup} tcp=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer} total=%{time_total}\n" https://example.com

openssl s_client -connect example.com:443 -servername example.com    # ดู cert chain, TLS version
echo | openssl s_client -connect example.com:443 -servername example.com 2>/dev/null | openssl x509 -noout -dates -subject -ext subjectAltName
```
**Browser DevTools (F12) → Network tab:** ดู status, เวลาแต่ละขั้น (DNS, connect, SSL, waiting/TTFB), header, protocol (h2/h3), cookie

**วิเคราะห์ความช้าจาก curl timing**
| ส่วนที่ช้า | สงสัย |
|---|---|
| `time_namelookup` สูง | DNS |
| `time_connect` สูง | เครือข่าย/ระยะทาง/firewall |
| `time_appconnect` สูง | TLS (cert chain ยาว, OCSP, CPU server) |
| `time_starttransfer` (TTFB) สูง | แอป/ฐานข้อมูลหลังบ้านช้า |

---

## 7. "พิมพ์ URL แล้วเกิดอะไรขึ้น" (คำตอบสำหรับสัมภาษณ์)

```
 1. Browser แยก URL → scheme https, host shop.example.com, port 443
 2. DNS: cache browser/OS/hosts → resolver → root → TLD → authoritative → ได้ IP
 3. เครื่องตรวจว่า IP อยู่นอกวง → ARP หา MAC ของ default gateway
 4. TCP 3-way handshake ไปยัง IP:443 (ผ่าน NAT ที่ router, ผ่านหลาย router บนอินเทอร์เน็ต)
 5. TLS handshake: ClientHello (SNI) → cert ของ server → ตรวจ chain/ชื่อ/อายุ → ตกลงกุญแจ
 6. ส่ง HTTP GET (เข้ารหัส) พร้อม header/cookie
 7. Server (มักผ่าน CDN/Load balancer/WAF) ประมวลผล → ตอบ 200 + HTML
 8. Browser parse HTML → โหลด CSS/JS/รูปเพิ่ม (request อีกหลายสิบครั้ง ใช้ connection เดิมด้วย HTTP/2)
 9. Render หน้าเว็บ
 (HTTP/3: ขั้น 4-5 รวมกันใน QUIC บน UDP)
```

---

## 8. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| HTTPS = เว็บปลอดภัย ไม่ใช่เว็บปลอม | HTTPS แค่ยืนยันว่าเชื่อมต่อกับเจ้าของโดเมนนั้นจริงและเข้ารหัส เว็บ phishing ก็มี HTTPS ได้ |
| 401 กับ 403 เหมือนกัน | 401 = ยังไม่ login/ยืนยันตัวตน · 403 = รู้ว่าเป็นใครแต่ไม่มีสิทธิ์ |
| 5xx เป็นปัญหาเครือข่าย | 5xx เป็นปัญหาที่ server/แอป (502/504 อาจเกี่ยวกับการเชื่อมต่อระหว่าง proxy กับ backend) |
| ใช้ SSL อยู่ | ปัจจุบันคือ TLS 1.2/1.3 ส่วน SSL ต้องปิด |
| curl -k ใช้แก้ปัญหา cert ได้ | แค่ข้ามการตรวจ ปัญหายังอยู่ |

---

## 9. Cheat Sheet

```
HTTP 80 · HTTPS 443 · stateless (ใช้ cookie/token)
Methods: GET POST PUT PATCH DELETE HEAD OPTIONS
2xx สำเร็จ · 301 ถาวร/302 ชั่วคราว · 401 ยังไม่ยืนยันตัวตน · 403 ไม่มีสิทธิ์ · 404 ไม่พบ
500 แอป error · 502 upstream ตอบผิด/ปฏิเสธ · 503 ไม่พร้อม · 504 upstream ตอบช้า
HTTP/1.1 keep-alive · HTTP/2 multiplexing (TCP) · HTTP/3 QUIC (UDP 443)
TLS = เข้ารหัส + integrity + ยืนยันตัวตน · ใช้ TLS 1.2/1.3 · 1.3 = 1 RTT · ECDHE = forward secrecy
SNI = บอกชื่อเว็บใน ClientHello · Chain: Root → Intermediate → Server (ส่ง intermediate ด้วย!)
ตรวจ: ชื่อตรง SAN · ไม่หมดอายุ · chain ครบ
curl -v / -I / --resolve / -w timing · openssl s_client -servername
```

---

## 10. แบบทดสอบ 10 ข้อ

1. HTTP กับ HTTPS ใช้ port อะไร ต่างกันอย่างไร
2. 401 กับ 403 ต่างกันอย่างไร
3. 502 กับ 504 ต่างกันอย่างไร
4. HTTP/2 ปรับปรุงอะไรจาก HTTP/1.1 และ HTTP/3 วิ่งบนโปรโตคอลใด
5. TLS ให้คุณสมบัติด้านความปลอดภัย 3 อย่างอะไรบ้าง
6. SNI มีไว้ทำอะไร
7. เว็บเปิดบน Chrome ได้ แต่ curl และแอปมือถือฟ้อง cert ไม่น่าเชื่อถือ สาเหตุที่พบบ่อยคืออะไร
8. คำสั่ง curl ทดสอบ server ใหม่ IP 10.0.0.5 ด้วยชื่อ shop.example.com ก่อนเปลี่ยน DNS
9. curl timing พบว่า time_starttransfer สูงมากแต่ส่วนอื่นปกติ ปัญหาน่าจะอยู่ที่ใด
10. อธิบายสั้น ๆ ว่าพิมพ์ https://www.example.com แล้วเกิดอะไรขึ้นจนเห็นหน้าเว็บ

<details><summary><b>เฉลย</b></summary>

1. HTTP 80, HTTPS 443 — HTTPS คือ HTTP ที่เข้ารหัสและยืนยันตัวตนด้วย TLS
2. 401 = ยังไม่ได้ยืนยันตัวตน (ต้อง login); 403 = ยืนยันแล้วแต่ไม่มีสิทธิ์
3. 502 = server หลังบ้านตอบผิดหรือปฏิเสธการเชื่อมต่อ; 504 = server หลังบ้านตอบช้าเกินเวลาที่ proxy รอ
4. HTTP/2 ทำ multiplexing หลาย request ใน connection เดียว + header compression; HTTP/3 วิ่งบน QUIC (UDP)
5. Confidentiality (เข้ารหัส), Integrity (ห้ามแก้ไข), Authentication (ยืนยันตัวตนด้วย cert)
6. บอกชื่อเว็บที่ต้องการตอน handshake ให้ server ที่โฮสต์หลายเว็บเลือก cert ถูกตัว
7. Server ไม่ส่ง intermediate certificate (chain ไม่ครบ)
8. `curl --resolve shop.example.com:443:10.0.0.5 https://shop.example.com`
9. แอปพลิเคชัน/ฐานข้อมูลฝั่ง server ประมวลผลช้า (TTFB)
10. DNS resolve → ARP หา gateway → TCP handshake → TLS handshake (SNI, ตรวจ cert) → HTTP GET → server ตอบ → browser โหลด resource เพิ่มและ render
</details>

---

🎉 **จบ Tier 2** · ➡️ ต่อไป: **Level 21 — คำสั่งเครือข่ายพื้นฐานบน OS** · กลับไปทำโปรเจคใน [02-core-protocols.md](../02-core-protocols.md)
