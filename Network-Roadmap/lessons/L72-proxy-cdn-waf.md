# บทเรียน Level 72 — Proxy, Reverse Proxy, CDN & WAF (ฉบับละเอียด)

> อ่านจบแล้วจะ: แยก forward proxy กับ reverse proxy · ตั้ง explicit/transparent proxy, PAC/WPAD · เข้าใจ Secure Web Gateway · CDN และ cache-control · Anycast · WAF และ OWASP Top 10 · ข้อควรระวังเมื่อใช้ CDN/WAF กับระบบจริง

---

## 1. Proxy คืออะไร

**Proxy** = ตัวกลางที่รับ request แทนอีกฝ่าย แล้วสร้างการเชื่อมต่อใหม่ไปยังปลายทาง

```
 Forward proxy (แทนผู้ใช้ — ออกไปข้างนอก):
   [ผู้ใช้ในองค์กร] ──► [Forward Proxy] ──► อินเทอร์เน็ต
   เว็บปลายทางเห็น IP ของ proxy ไม่ใช่ของผู้ใช้

 Reverse proxy (แทน server — รับจากข้างนอก):
   อินเทอร์เน็ต ──► [Reverse Proxy] ──► [Web/App server ภายใน]
   ผู้ใช้เห็นแค่ reverse proxy ไม่รู้ว่ามี server กี่ตัวอยู่ข้างหลัง
```

| | Forward Proxy | Reverse Proxy |
|---|---|---|
| ทำงานแทน | **client** | **server** |
| อยู่ที่ | ฝั่งองค์กรผู้ใช้ | หน้า server/แอป |
| ใช้ทำ | กรองเว็บ, cache, บันทึก, ควบคุมการออกอินเทอร์เน็ต, DLP | load balancing, SSL termination, WAF, cache, ซ่อน server, routing |
| ตัวอย่าง | Squid, Zscaler/Netskope (cloud SWG), proxy ใน NGFW, Blue Coat/Symantec | Nginx, HAProxy, Apache, Envoy, Traefik, F5, Cloudflare |

---

## 2. Forward Proxy ในองค์กร

### Explicit Proxy
browser/OS **ถูกตั้งค่าให้รู้จัก proxy** (IP:port เช่น `proxy.corp:8080`)
- HTTPS ผ่าน explicit proxy ใช้คำสั่ง **HTTP CONNECT** สร้าง tunnel (proxy เห็นชื่อปลายทางแต่ไม่เห็นเนื้อหา เว้นแต่ทำ SSL inspection)
- ✅ รองรับการยืนยันตัวตน (Kerberos/NTLM — รู้ว่าเป็นผู้ใช้ใด), ควบคุมได้ละเอียด
- ❌ ต้องตั้งค่าทุกเครื่อง/แอป, แอปบางตัวไม่รองรับ proxy

**วิธีแจกการตั้งค่า**
- **GPO/Intune/MDM**
- **PAC file (Proxy Auto-Config)** — JavaScript บอกว่า URL ใดใช้ proxy ใด/ไปตรง
```javascript
function FindProxyForURL(url, host) {
  if (isPlainHostName(host) || shExpMatch(host, "*.corp.local") ||
      isInNet(dnsResolve(host), "10.0.0.0", "255.0.0.0"))
    return "DIRECT";                                   // ระบบภายในไปตรง
  if (shExpMatch(host, "*.office.com") || shExpMatch(host, "*.microsoft.com"))
    return "DIRECT";                                   // (ตัวอย่าง) bypass SaaS ที่เชื่อถือ
  return "PROXY proxy1.corp:8080; PROXY proxy2.corp:8080; DIRECT";
}
```
- **WPAD** — ค้นหา PAC อัตโนมัติผ่าน DHCP option 252 หรือ DNS `wpad.<domain>` (ระวังความเสี่ยง: ผู้โจมตีปลอม WPAD ได้ถ้าไม่ควบคุม)

### Transparent (Intercepting) Proxy
traffic ถูก **ดักโดยอัตโนมัติ** ที่ firewall/router (policy-based redirect, WCCP) — ผู้ใช้ไม่ต้องตั้งค่าอะไร
- ✅ ครอบคลุมทุกเครื่อง · ❌ ยืนยันตัวตนผู้ใช้ยากกว่า, HTTPS ต้องทำ SSL inspection ถึงจะเห็นเนื้อหา

### Secure Web Gateway (SWG)
forward proxy ด้าน security: **URL categorization**, block มัลแวร์/phishing, **SSL inspection**, sandbox, DLP, ควบคุมแอป SaaS (CASB) — บน appliance, ใน NGFW หรือ **บน cloud (SSE — Level 60)** ซึ่งเหมาะกับผู้ใช้ที่ทำงานนอกสำนักงาน

---

## 3. Reverse Proxy

หน้าที่ที่พบบ่อย (มักรวมกับ load balancer — Level 71):
- **SSL/TLS termination** และจัดการ certificate ที่เดียว (+ ACME อัตโนมัติ)
- **Routing** ตาม host/path ไปยัง backend ต่าง ๆ (หลายแอปบน IP เดียว)
- **ซ่อน server จริง** และ topology ภายใน
- **Caching, compression** (gzip/brotli), HTTP/2–3 ให้ client
- **Rate limiting**, authentication (เช่น OIDC ก่อนเข้าแอปภายใน — แนวทาง ZTNA)
- **WAF** (ข้อ 5)

```nginx
# Nginx reverse proxy
server {
    listen 443 ssl http2;
    server_name app.company.example;
    ssl_certificate     /etc/ssl/app/fullchain.pem;     # leaf + intermediate
    ssl_certificate_key /etc/ssl/app/privkey.pem;
    location / {
        proxy_pass http://10.0.1.20:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        limit_req zone=perip burst=20;                  # (ประกาศ zone ใน http {})
    }
}
```

---

## 4. CDN — Content Delivery Network

**CDN** = เครือข่ายของ server (**PoP — Point of Presence / edge**) กระจายทั่วโลก ที่ **cache เนื้อหาไว้ใกล้ผู้ใช้**
```
 ผู้ใช้ในเชียงใหม่ ──► [CDN edge กรุงเทพ] ──(cache miss เท่านั้น)──► [Origin server ที่สิงคโปร์]
                         cache hit → ตอบทันที (RTT สั้น)
```

| ประโยชน์ | อธิบาย |
|---|---|
| **เร็วขึ้น** | latency ต่ำ (edge ใกล้ผู้ใช้), TLS handshake สั้นลง |
| **ลดโหลด origin และค่า bandwidth** | cache hit ไม่ต้องไปถึง origin |
| **รับ traffic พุ่ง** | flash sale, ข่าวสำคัญ |
| **ป้องกัน DDoS** | ความจุมหาศาลกระจายหลายพื้นที่, ซ่อน origin IP |
| **ความสามารถเสริม** | WAF, bot management, image optimization, edge compute |

ผู้ให้บริการ: Cloudflare, Akamai, AWS CloudFront, Fastly, Google Cloud CDN, Azure Front Door

### Anycast
**IP เดียวกันถูกประกาศ (BGP) จากหลาย PoP** → routing ของอินเทอร์เน็ตพาผู้ใช้ไป PoP ที่ "ใกล้" ที่สุดเอง (ใช้กับ CDN, public DNS 1.1.1.1/8.8.8.8) → ถ้า PoP หนึ่งล่ม route หายและผู้ใช้ไปที่อื่นอัตโนมัติ

### Cache Control (ต้องเข้าใจเพื่อแก้ปัญหา "แก้เว็บแล้วผู้ใช้ยังเห็นของเก่า")

| Header | ความหมาย |
|---|---|
| `Cache-Control: public, max-age=86400` | cache ได้ 1 วัน |
| `Cache-Control: private` | cache ได้เฉพาะ browser ของผู้ใช้ ไม่ใช่ CDN (ข้อมูลส่วนตัว) |
| `Cache-Control: no-store` | ห้าม cache (หน้าที่มีข้อมูลอ่อนไหว) |
| `s-maxage` | อายุ cache สำหรับ shared cache (CDN) |
| `ETag` / `Last-Modified` | ตรวจว่าเปลี่ยนไหม (304 Not Modified) |

- **Cache hit ratio** = ตัวชี้วัดประสิทธิภาพของ CDN
- **Purge/Invalidate** — ล้าง cache เมื่อแก้เนื้อหา · หรือใช้ **ชื่อไฟล์แบบมี version/hash** (`app.3f9a2c.js`) เพื่อไม่ต้อง purge
- ⚠️ **ระวัง cache ข้อมูลส่วนตัว:** ถ้า CDN cache หน้าที่มีข้อมูลของผู้ใช้คนหนึ่งแล้วส่งให้คนอื่น = ข้อมูลรั่ว (ตั้ง `private/no-store` ให้ถูก)

### ข้อควรระวังเมื่อใช้ CDN/Cloud proxy
- **ปิดการเข้าถึง origin โดยตรง** — อนุญาตเฉพาะ IP ของ CDN (หรือใช้ tunnel/authenticated origin pull) ไม่เช่นนั้นผู้โจมตีอ้อม CDN ได้
- เว็บเห็น IP ของ CDN → อ่าน header IP จริง (`CF-Connecting-IP`, `X-Forwarded-For`) จาก IP ของ CDN ที่เชื่อถือเท่านั้น
- พิจารณา **data residency/PDPA** และการถอดรหัสที่ edge

---

## 5. WAF — Web Application Firewall

**WAF** ตรวจ **HTTP/HTTPS ระดับแอปพลิเคชัน (L7)** เพื่อป้องกันการโจมตีเว็บที่ firewall ทั่วไป (L3/L4) มองไม่เห็น

### OWASP Top 10 (2021 — ฉบับที่ใช้อ้างอิงแพร่หลาย; ตรวจฉบับล่าสุดเมื่อใช้งาน)

| # | หมวด | ตัวอย่าง |
|---|---|---|
| A01 | Broken Access Control | เปลี่ยน id ใน URL แล้วเห็นข้อมูลคนอื่น |
| A02 | Cryptographic Failures | ส่ง/เก็บข้อมูลอ่อนไหวไม่เข้ารหัส |
| A03 | **Injection** | **SQL injection**, command injection, (XSS รวมอยู่ในหมวดนี้) |
| A04 | Insecure Design | ออกแบบไม่มีการป้องกัน |
| A05 | Security Misconfiguration | หน้า admin เปิด, debug เปิด |
| A06 | Vulnerable Components | library เก่ามีช่องโหว่ |
| A07 | Identification & Authentication Failures | brute force, session ไม่หมดอายุ |
| A08 | Software & Data Integrity Failures | อัปเดต/CI ไม่ตรวจสอบ |
| A09 | Logging & Monitoring Failures | ไม่มี log ตรวจไม่พบการโจมตี |
| A10 | SSRF | ให้ server เรียก URL ภายในแทนผู้โจมตี |

### WAF ทำอะไรได้
- **Signature/rule set:** OWASP **Core Rule Set (CRS)** กับ ModSecurity/Coraza, managed rules ของ cloud WAF
- **Positive security model:** อนุญาตเฉพาะ request ที่ตรงรูปแบบที่กำหนด (เข้มงวด แต่ดูแลยาก)
- **Virtual patching:** บล็อกการโจมตีช่องโหว่ที่ยังแก้โค้ดไม่ทัน
- Rate limiting, bot management, geo-blocking, API protection (schema validation)
- ผลิตภัณฑ์: Cloudflare WAF, AWS WAF, Azure WAF (Front Door/App Gateway), Akamai, F5 Advanced WAF, FortiWeb, Imperva, ModSecurity/Coraza (open source)

### การใช้ WAF ให้ได้ผล
- เริ่มใน **detection/log mode** → ปรับ (tuning) false positive → เปลี่ยนเป็น **block**
- ปรับ **paranoia level/threshold** ตามความเสี่ยงของแอป
- ⚠️ **WAF ไม่ได้แทน secure coding** — เป็นชั้นป้องกันเพิ่ม (defense in depth)

---

## 6. วางสถาปัตยกรรมเว็บสาธารณะ (ตัวอย่าง)

```
 ผู้ใช้ ──► [CDN + WAF + DDoS (cloud)] ──► [Firewall (อนุญาตเฉพาะ IP ของ CDN)]
        ──► [Reverse proxy/LB คู่ (DMZ)] ──► [App servers (app zone)] ──► [Database (restricted zone)]
 ผู้ใช้ภายในออกอินเทอร์เน็ต ──► [SWG/forward proxy หรือ SSE] ──► อินเทอร์เน็ต
```

---

## 7. แก้ปัญหา

| อาการ | ตรวจ |
|---|---|
| ผู้ใช้เข้าเว็บภายนอกไม่ได้หลังเปิด proxy | PAC/bypass list, การยืนยันตัวตนกับ proxy, SSL inspection exemption, แอปไม่รองรับ proxy |
| แก้เว็บแล้วผู้ใช้ยังเห็นของเก่า | CDN/browser cache → purge, ตรวจ Cache-Control, versioned filename |
| WAF บล็อกผู้ใช้จริง (403) | ดู log ของ WAF หา rule ID → exclusion เฉพาะ path/parameter (ไม่ปิดทั้ง rule set) |
| เว็บหลัง CDN ช้า/ error 52x (Cloudflare) | origin ตอบช้า/ปิด/firewall บล็อก IP ของ CDN, cert ของ origin |
| log ของ server เห็นแต่ IP ของ proxy/CDN | อ่าน X-Forwarded-For/CF-Connecting-IP จากแหล่งที่เชื่อถือ |

---

## 8. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| Forward กับ reverse proxy เหมือนกัน | forward ทำงานแทน client, reverse ทำงานแทน server |
| Proxy เห็นเนื้อหา HTTPS ทั้งหมด | เห็นแค่ปลายทาง (CONNECT/SNI) จนกว่าจะทำ SSL inspection |
| ใช้ CDN แล้ว origin ปลอดภัยอัตโนมัติ | ต้องปิดการเข้าถึง origin โดยตรง |
| มี WAF แล้วไม่ต้องแก้โค้ด | WAF เป็นชั้นเสริม ไม่แทน secure coding |
| Cache ทุกอย่างทำให้เร็วดี | cache ข้อมูลส่วนตัวผิดพลาด = ข้อมูลรั่ว |

---

## 9. Cheat Sheet

```
Forward proxy (แทน client: กรองเว็บ/บันทึก) · Reverse proxy (แทน server: TLS, routing, LB, WAF, cache)
Explicit (ตั้งค่า/PAC/WPAD, HTTP CONNECT, รู้ผู้ใช้) vs Transparent (ดักอัตโนมัติ)
SWG = forward proxy ด้าน security (URL, malware, SSL inspection, DLP) · บน cloud = SSE
CDN: edge/PoP cache ใกล้ผู้ใช้ · anycast · cache hit ratio · purge · versioned files
Cache-Control: public/private/no-store/max-age/s-maxage · ระวัง cache ข้อมูลส่วนตัว
ปิด origin ให้รับเฉพาะ CDN · อ่าน IP จริงจาก header ที่เชื่อถือ
WAF: L7 · OWASP Top 10 (injection, broken access control...) · CRS/ModSecurity · virtual patching
WAF: detect → tune → block · ไม่แทน secure coding
```

---

## 10. แบบทดสอบ 10 ข้อ

1. Forward proxy กับ reverse proxy ต่างกันอย่างไร
2. Explicit proxy กับ transparent proxy ต่างกันอย่างไร
3. PAC file คืออะไร และทำไมนิยมให้ระบบภายในไป DIRECT
4. Proxy เห็นอะไรบ้างใน HTTPS โดยไม่ทำ SSL inspection
5. CDN ทำให้เว็บเร็วขึ้นได้อย่างไร (3 ข้อ)
6. Anycast คืออะไร
7. `Cache-Control: private` และ `no-store` ต่างกันอย่างไร ทำไมสำคัญ
8. ทำไมต้องปิดการเข้าถึง origin โดยตรงเมื่อใช้ CDN
9. WAF ป้องกันอะไรที่ firewall ทั่วไปป้องกันไม่ได้ ยกตัวอย่าง 2 หมวด
10. ควรเปิดใช้ WAF ในระบบจริงอย่างไรไม่ให้กระทบผู้ใช้

<details><summary><b>เฉลย</b></summary>

1. Forward proxy ทำงานแทน client ออกไปยังอินเทอร์เน็ต; reverse proxy ทำงานแทน server รับ request จากภายนอก
2. Explicit: client ถูกตั้งค่าให้ใช้ proxy (รู้ตัว, ยืนยันตัวตนได้); transparent: traffic ถูกดักอัตโนมัติโดยไม่ต้องตั้งค่า client
3. JavaScript บอก browser ว่า URL ใดใช้ proxy ใดหรือไปตรง — ระบบภายในไปตรงเพื่อไม่ให้ผ่าน proxy โดยไม่จำเป็น (และ proxy อาจเข้าถึงภายในไม่ได้)
4. ชื่อ/ที่อยู่ปลายทาง (CONNECT host หรือ SNI), IP, ปริมาณข้อมูล — ไม่เห็น URL เต็มและเนื้อหา
5. Cache ใกล้ผู้ใช้ (latency ต่ำ), ลดโหลด origin, TLS handshake สั้นลง, กระจายโหลด/รับ traffic พุ่ง
6. IP เดียวกันประกาศจากหลายตำแหน่ง routing จะพาผู้ใช้ไปยังตำแหน่งที่ใกล้ที่สุด และย้ายอัตโนมัติเมื่อจุดหนึ่งล่ม
7. Private = cache ได้เฉพาะใน browser ของผู้ใช้ (ไม่ใช่ CDN); no-store = ห้าม cache เลย — ป้องกันข้อมูลส่วนตัวถูกส่งให้ผู้อื่น
8. ไม่เช่นนั้นผู้โจมตีส่ง traffic ตรงไป origin อ้อม WAF/DDoS protection ของ CDN
9. การโจมตีระดับ HTTP/แอป เช่น SQL injection, XSS, broken access control/brute force login
10. เริ่ม detection/log mode → tuning false positive (exclusion เฉพาะจุด) → เปลี่ยนเป็น block ทีละส่วน และติดตาม log
</details>

---

➡️ ต่อไป: **Level 73 — Data Center Design: Spine-Leaf**
