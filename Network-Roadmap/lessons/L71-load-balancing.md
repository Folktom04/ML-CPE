# บทเรียน Level 71 — Load Balancing (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจว่า load balancer แก้ปัญหาอะไร · L4 vs L7 · อัลกอริทึมกระจายโหลด · health check · session persistence · SSL offload/re-encryption · SNAT vs DSR · X-Forwarded-For/PROXY protocol · GSLB · ทำ HA ของ load balancer · ตั้ง HAProxy/Nginx ได้

---

## 1. Load Balancer แก้ปัญหาอะไร

```
 ไม่มี LB:  ผู้ใช้ ──► [Web server ตัวเดียว]   ← ล่ม = บริการล่ม · รับโหลดได้จำกัด · ปิดเพื่อ patch ไม่ได้

 มี LB:     ผู้ใช้ ──► [ VIP บน Load Balancer ] ──► Web1
                                              ├──► Web2
                                              └──► Web3     ← ตัวใดล่ม LB หยุดส่งไปตัวนั้นอัตโนมัติ
```
| ประโยชน์ | อธิบาย |
|---|---|
| **Scalability** | เพิ่ม server ได้เมื่อโหลดเพิ่ม (scale out) |
| **High availability** | server ล่ม → ส่งไปตัวที่เหลือ (ผ่าน health check) |
| **Maintenance ไม่มี downtime** | ถอด server ออกทีละตัวเพื่อ patch/deploy (drain) |
| **SSL offload** | ย้ายภาระเข้ารหัสไปที่ LB |
| **Security** | ซ่อน server จริง, WAF, rate limit, DDoS บางระดับ |
| **Traffic management** | routing ตาม URL/host, blue-green/canary deployment |

**ศัพท์:** **VIP (Virtual IP)** = IP ที่ผู้ใช้เชื่อมต่อ · **Pool/Backend/Server farm** = กลุ่ม server จริง · **Member/Real server** · **Listener/Frontend**

---

## 2. L4 vs L7 Load Balancing

| | **L4 (Transport)** | **L7 (Application)** |
|---|---|---|
| ตัดสินใจจาก | IP + port (TCP/UDP) | **เนื้อหา HTTP**: host, URL path, header, cookie, method |
| ต้องถอด TLS | ไม่ต้อง (passthrough ได้) | ต้อง (เพื่ออ่าน HTTP) |
| ความเร็ว | เร็วมาก ใช้ทรัพยากรน้อย | ช้ากว่า ใช้ CPU มากกว่า |
| ความสามารถ | กระจายโหลดพื้นฐาน | routing ตามเนื้อหา, แก้ header, cookie persistence, WAF, compression, caching |
| ใช้กับ | DB, protocol ที่ไม่ใช่ HTTP, เกม, throughput สูงมาก | เว็บ, API, microservices |
| ตัวอย่าง | AWS NLB, HAProxy (mode tcp), LVS/IPVS | AWS ALB, HAProxy (mode http), Nginx, Envoy, F5 LTM, Citrix |

```
 L7 routing ตัวอย่าง:
   shop.example.com/api/*      → pool API
   shop.example.com/images/*   → pool static/CDN
   admin.example.com           → pool ADMIN (อนุญาตเฉพาะ IP ภายใน)
```

---

## 3. อัลกอริทึมการกระจายโหลด

| อัลกอริทึม | หลักการ | เหมาะกับ |
|---|---|---|
| **Round Robin** | วนทีละตัว | server เท่ากัน request ใกล้เคียงกัน |
| **Weighted Round Robin** | ตัวแรงได้มากกว่าตามน้ำหนัก | server สเปกต่างกัน |
| **Least Connections** | ส่งไปตัวที่มี connection น้อยสุด | session ยาวไม่เท่ากัน (เช่น WebSocket, DB) |
| **Weighted Least Connections** | + น้ำหนัก | ผสม |
| **Least Response Time** | ตัวที่ตอบเร็วสุด | เน้นประสบการณ์ผู้ใช้ |
| **Source IP Hash** | hash ของ IP ผู้ใช้ → server เดิมเสมอ | ต้องการ persistence แบบง่าย (ระวังผู้ใช้หลัง NAT เดียวกันไปกองตัวเดียว) |
| **Consistent Hashing** | เพิ่ม/ลด server แล้วกระทบการจับคู่น้อย | cache, distributed systems |
| Random / Power of two choices | สุ่ม 2 ตัวเลือกตัวที่โหลดน้อยกว่า | ระบบใหญ่ |

---

## 4. Health Check

LB ต้องรู้ว่า server ตัวไหนพร้อม — ส่ง probe เป็นระยะ
| ระดับ | ตรวจ | ข้อจำกัด |
|---|---|---|
| ICMP ping | เครื่องเปิดอยู่ | แอปอาจล่มแต่ ping ได้ |
| TCP connect | port เปิด | แอปอาจตอบ error |
| **HTTP(S)** ⭐ | `GET /health` ได้ **200** (และอาจตรวจเนื้อหา) | ต้องออกแบบ endpoint |

**Health endpoint ที่ดี:** ตรวจสิ่งที่แอปต้องพึ่งจริง (เชื่อมต่อ DB ได้ไหม) แต่เร็วและเบา · ระวัง: ถ้าทุก server พึ่ง DB เดียวกันแล้ว DB ล่ม ทุก server จะ fail health check พร้อมกัน
**ค่าที่ตั้ง:** interval (เช่น 5 วินาที), timeout, **rise/fall** (ผ่านกี่ครั้งถึงนับว่าขึ้น / ล้มเหลวกี่ครั้งถึงถอดออก — กัน flap)

**Connection draining / graceful shutdown:** ก่อนถอด server ให้หยุดรับ connection ใหม่แต่ปล่อยให้ connection เดิมทำงานจนจบ

---

## 5. Session Persistence (Sticky Session)

แอปบางแบบเก็บ **session ไว้ใน memory ของ server** → ผู้ใช้ต้องกลับไป server เดิม ไม่เช่นนั้นหลุด login/ตะกร้าสินค้าหาย
| วิธี | หลักการ |
|---|---|
| **Cookie-based** (L7) | LB แทรก cookie ระบุ server (หรือใช้ cookie ของแอป) — แม่นยำ |
| Source IP | จับคู่จาก IP ผู้ใช้ — ผู้ใช้หลัง NAT/CGNAT เดียวกันไปกองตัวเดียว, IP มือถือเปลี่ยน |
| SSL session ID | (เก่า ไม่น่าเชื่อถือกับ TLS 1.3) |

**ข้อเสียของ sticky:** โหลดไม่สมดุล, server ล่มแล้ว session ของผู้ใช้หาย
**แนวทางที่ดีกว่า:** ออกแบบแอปให้ **stateless** — เก็บ session ใน **Redis/DB กลาง** หรือใช้ token (JWT) → server ตัวไหนก็ตอบได้

---

## 6. SSL/TLS ที่ Load Balancer

| แบบ | การทำงาน | ข้อดี | ข้อเสีย |
|---|---|---|---|
| **SSL Passthrough** | LB ไม่ถอดรหัส (L4) ส่งต่อทั้งก้อน | end-to-end encryption, ไม่ต้องดูแล cert ที่ LB | ทำ L7 routing/WAF ไม่ได้ |
| **SSL Offload/Termination** | LB ถอดรหัส แล้วส่ง HTTP ธรรมดาไป server | server เบา, L7 routing/WAF ได้, จัดการ cert ที่เดียว | ช่วง LB → server ไม่เข้ารหัส (ยอมรับได้เฉพาะเครือข่ายที่ควบคุมได้) |
| **SSL Bridging/Re-encryption** | ถอดที่ LB ตรวจ แล้วเข้ารหัสใหม่ไป server | ได้ทั้ง L7 และเข้ารหัสตลอดทาง (นิยมใน zero trust/compliance) | ใช้ทรัพยากรมากที่สุด |

LB รุ่นใหม่ยังทำ **HTTP/2, HTTP/3**, TLS 1.3, OCSP stapling, HSTS ให้ได้

---

## 7. การส่ง Traffic กลับ: SNAT vs DSR

### SNAT (Source NAT / Proxy mode) — ค่าเริ่มต้นส่วนใหญ่
```
 Client 1.2.3.4 → VIP 203.0.113.10 → LB เปลี่ยน src เป็น IP ของ LB (10.0.1.5) → Web1
 Web1 ตอบกลับไปหา 10.0.1.5 (LB) → LB ส่งกลับ client
```
- ✅ server ไม่ต้องตั้งอะไรพิเศษ, ทางกลับผ่าน LB แน่นอน
- ❌ **server เห็น IP ของ LB แทน IP จริงของผู้ใช้** → แก้ด้วย:
  - **X-Forwarded-For** (HTTP header ที่ L7 LB แทรก IP จริง) — server/แอปต้องอ่าน header นี้ (และเชื่อเฉพาะเมื่อมาจาก LB ของเรา)
  - **PROXY protocol** (สำหรับ L4/TCP — LB ส่งข้อมูล IP จริงนำหน้า connection, server ต้องรองรับ)

### DSR (Direct Server Return)
```
 Client → LB → server · server ตอบกลับหา client **โดยตรง** (ไม่ผ่าน LB)
```
- ✅ LB รับแค่ขาเข้า (ซึ่งมักเล็ก) → รองรับ throughput ขาออกสูงมาก (video, download)
- ❌ ตั้งค่าซับซ้อน (server ต้องมี VIP บน loopback และปิด ARP ของ VIP), L7 ทำไม่ได้, ตรวจปัญหายาก

---

## 8. HA ของ Load Balancer เอง

LB เป็นจุดศูนย์กลาง ถ้าล่มบริการล่มทั้งหมด → ต้องมี **2 ตัวขึ้นไป**
- **Active/Standby + VRRP** (เช่น HAProxy + **keepalived**) — VIP ย้ายไปตัวสำรอง (Level 50)
- **Active/Active** + ECMP/anycast หรือ DNS
- LB เชิงพาณิชย์ (F5, Citrix, FortiADC) มี HA ในตัว + sync config/session
- **Cloud LB** (AWS ELB, Azure LB, GCP LB) เป็นบริการ HA ในตัว (กระจายหลาย AZ)

---

## 9. GSLB — Global Server Load Balancing

กระจายผู้ใช้ไป **หลาย data center/region** โดยใช้ **DNS**
```
 ผู้ใช้ถาม www.example.com
 GSLB (authoritative DNS อัจฉริยะ) ตอบ IP ของ DC ที่:
   - ยังทำงาน (health check ทั้ง site)
   - ใกล้ผู้ใช้ที่สุด (geo/latency)
   - หรือตามนโยบาย active/standby (DC หลัก / DR)
```
- ใช้ทำ **DR site failover อัตโนมัติ** และ active-active ข้ามภูมิภาค
- ข้อจำกัด: ขึ้นกับ **DNS TTL** และ resolver ที่ cache (ตั้ง TTL สั้น เช่น 30–60 วินาที), ผู้ใช้เห็น IP ของ resolver ไม่ใช่ของตัวเอง (EDNS Client Subnet ช่วยได้)
- ผลิตภัณฑ์: F5 DNS (GTM), Citrix ADC GSLB, Route 53 (health check + routing policy), Cloudflare Load Balancing, NS1, Azure Traffic Manager

---

## 10. ตัวอย่าง: HAProxy

```
# /etc/haproxy/haproxy.cfg
global
    log /dev/log local0
    maxconn 50000
defaults
    mode http
    timeout connect 5s
    timeout client  30s
    timeout server  30s
    option httplog
    option forwardfor                        # แทรก X-Forwarded-For
frontend fe_https
    bind :443 ssl crt /etc/haproxy/certs/shop.pem alpn h2,http/1.1
    http-request redirect scheme https unless { ssl_fc }
    acl is_api path_beg /api/
    use_backend be_api if is_api
    default_backend be_web
backend be_web
    balance roundrobin
    option httpchk GET /health
    http-check expect status 200
    cookie SRV insert indirect nocache       # sticky ด้วย cookie
    server web1 10.0.1.11:8080 check cookie w1 inter 5s fall 3 rise 2
    server web2 10.0.1.12:8080 check cookie w2 inter 5s fall 3 rise 2
backend be_api
    balance leastconn
    option httpchk GET /api/health
    server api1 10.0.2.11:9000 check
    server api2 10.0.2.12:9000 check
listen stats
    bind 10.0.99.5:8404
    stats enable
    stats uri /stats
```
```bash
haproxy -c -f /etc/haproxy/haproxy.cfg    # ตรวจ config
systemctl reload haproxy                   # reload โดยไม่ตัด connection
```
**Nginx** ใช้ `upstream { least_conn; server ...; }` + `proxy_pass`, **Envoy** นิยมในโลก microservices/service mesh

---

## 11. Deployment Strategies ที่อาศัย LB

- **Blue-Green:** มี 2 ชุด (blue = ปัจจุบัน, green = ใหม่) → สลับ LB ไป green ทีเดียว → มีปัญหาสลับกลับทันที
- **Canary:** ส่ง 5–10% ของ traffic ไปเวอร์ชันใหม่ก่อน ตรวจ error แล้วค่อยเพิ่ม
- **Rolling:** อัปเดตทีละ server (drain → update → เปิดคืน)

---

## 12. แก้ปัญหา Load Balancer

| อาการ | ตรวจ |
|---|---|
| **502 Bad Gateway** | backend ปฏิเสธ/ปิด/ตอบผิดรูปแบบ, ทุก server fail health check, port ผิด |
| **503 Service Unavailable** | ไม่มี server ที่ healthy ใน pool |
| **504 Gateway Timeout** | backend ตอบช้าเกิน timeout ของ LB |
| ผู้ใช้หลุด login บ่อย | ไม่มี persistence (แอปเก็บ session ใน memory) |
| โหลดไม่สมดุล | source-IP hash กับผู้ใช้หลัง NAT, sticky, server สเปกต่างกันแต่ไม่ตั้ง weight |
| log ของแอปเห็นแต่ IP ของ LB | ไม่ได้อ่าน X-Forwarded-For/PROXY protocol |
| server ขึ้นลงใน pool บ่อย | health check timeout สั้นเกิน/endpoint หนัก, ปรับ rise/fall |

---

## 13. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| มี LB แล้วไม่มี single point of failure | LB เองต้องมี HA |
| Health check ด้วย ping เพียงพอ | ใช้ HTTP health check ที่สะท้อนสถานะแอป |
| Sticky session คือวิธีที่ดีที่สุด | ออกแบบแอป stateless ดีกว่า |
| SSL offload ปลอดภัยเท่า end-to-end | ช่วงหลัง LB ไม่เข้ารหัส — ใช้ re-encryption เมื่อจำเป็น |
| GSLB failover ทันที | ขึ้นกับ DNS TTL และ cache |

---

## 14. Cheat Sheet

```
LB = VIP → pool/members · scalability · HA · maintenance · SSL offload · security
L4 (IP/port, เร็ว, passthrough) vs L7 (host/path/header/cookie, ต้องถอด TLS)
Algo: round robin · weighted · least conn · least response · source hash · consistent hash
Health check: HTTP /health + expect 200 · interval/timeout/rise/fall · draining
Persistence: cookie (L7) / source IP · ดีกว่า: stateless + Redis
SSL: passthrough · offload · re-encryption
SNAT (server เห็น IP ของ LB → X-Forwarded-For / PROXY protocol) · DSR (ตอบกลับตรง)
HA: keepalived/VRRP, active/active, cloud LB · GSLB = DNS-based ข้าม DC (TTL สั้น)
502 backend ตอบผิด · 503 ไม่มี server healthy · 504 backend ช้า
Blue-green · canary · rolling
```

---

## 15. แบบทดสอบ 10 ข้อ

1. Load balancer ให้ประโยชน์อะไรบ้าง (4 ข้อ)
2. L4 กับ L7 load balancing ต่างกันอย่างไร ยกตัวอย่างงานที่เหมาะกับแต่ละแบบ
3. Least connections เหมาะกับงานแบบใด
4. Health check แบบ HTTP ดีกว่า TCP connect อย่างไร
5. Sticky session มีข้อเสียอะไร และทางเลือกที่ดีกว่าคืออะไร
6. SSL passthrough, offload และ re-encryption ต่างกันอย่างไร
7. ทำไม web server หลัง LB เห็นแต่ IP ของ LB และแก้อย่างไร
8. DSR ข้อดีและข้อจำกัด
9. GSLB ทำงานอย่างไร มีข้อจำกัดอะไร
10. ผู้ใช้ได้ 503 จาก LB ควรตรวจอะไรเป็นอย่างแรก

<details><summary><b>เฉลย</b></summary>

1. Scale out, high availability (ถอด server ที่ล่มอัตโนมัติ), maintenance โดยไม่มี downtime, SSL offload, ซ่อน server/WAF, routing ตามเนื้อหา
2. L4 ตัดสินจาก IP/port (เร็ว — DB, protocol ที่ไม่ใช่ HTTP); L7 อ่าน HTTP (host/path/header/cookie) — เว็บ/API/microservices
3. Session ยาวและไม่เท่ากัน เช่น WebSocket, connection ฐานข้อมูล
4. ตรวจว่าแอปตอบได้จริง (เช่น ได้ 200) ไม่ใช่แค่ port เปิด
5. โหลดไม่สมดุลและ session หายเมื่อ server ล่ม — ออกแบบแอป stateless เก็บ session ใน Redis/DB กลางหรือใช้ token
6. Passthrough ไม่ถอดรหัส (L4); offload ถอดที่ LB แล้วส่ง HTTP ธรรมดา; re-encryption ถอดที่ LB แล้วเข้ารหัสใหม่ไป server
7. LB ทำ SNAT — แก้ด้วย X-Forwarded-For (HTTP) หรือ PROXY protocol (TCP) และให้แอปอ่านค่านั้น
8. Server ตอบกลับหา client ตรง ทำให้รองรับ throughput ขาออกสูง — แต่ตั้งค่าซับซ้อน ทำ L7 ไม่ได้ แก้ปัญหายาก
9. ใช้ DNS ตอบ IP ของ DC ที่ยังทำงาน/ใกล้ผู้ใช้/ตามนโยบาย — ขึ้นกับ TTL และ cache ของ resolver
10. ดูว่า pool มี server ที่ผ่าน health check หรือไม่ (ทุกตัว down?) และสาเหตุที่ health check ล้มเหลว
</details>

---

➡️ ต่อไป: **Level 72 — Proxy, Reverse Proxy, CDN & WAF**
