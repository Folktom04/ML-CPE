# บทเรียน Level 16 — DNS (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจลำดับการแปลงชื่อโดเมนเป็น IP ทุกขั้น · รู้จัก record ทุกชนิดที่ใช้ในงาน · TTL และ cache · Split-horizon DNS · ใช้ dig/nslookup แก้ปัญหาได้ · รู้จัก DoH/DoT/DNSSEC

---

## 1. DNS คืออะไร

**DNS (Domain Name System)** คือ **ระบบแปลงชื่อที่คนจำได้ (www.example.com) เป็น IP ที่คอมพิวเตอร์ใช้ (93.184.216.34)** และในทางกลับกัน

> 💡 **เปรียบเทียบ:** DNS คือ **สมุดโทรศัพท์ของอินเทอร์เน็ต** — เรารู้ชื่อร้าน แต่โทรได้ต้องรู้เบอร์

- ใช้ **UDP 53** เป็นหลัก และ **TCP 53** เมื่อคำตอบใหญ่หรือทำ zone transfer
- เป็นระบบ **กระจายศูนย์และเป็นลำดับชั้น** ไม่มี server ตัวเดียวที่รู้ทุกชื่อ

> ⚠️ **"It's always DNS"** — คำพูดติดตลกในวงการ เพราะปัญหาระบบล่มจำนวนมากมีต้นเหตุจาก DNS

---

## 2. โครงสร้างชื่อโดเมน (อ่านจากขวาไปซ้าย)

```
            www  .  example  .  co  .  th  .
            │       │           │      │    └─ Root (จุดท้ายสุด มักไม่เขียน)
            │       │           │      └────── TLD (Top-Level Domain): .th
            │       │           └───────────── Second-level: .co.th
            │       └───────────────────────── ชื่อโดเมนที่จดทะเบียน: example
            └───────────────────────────────── Host / Subdomain: www
```
- **FQDN (Fully Qualified Domain Name):** ชื่อเต็ม เช่น `mail.corp.example.com.`
- **TLD:** gTLD (.com .org .net), ccTLD (.th .jp), ใหม่ (.app .cloud)
- `.th` บริหารโดย THNIC

---

## 3. ประเภทของ DNS Server

| ประเภท | หน้าที่ | ตัวอย่าง |
|---|---|---|
| **Recursive Resolver** | รับคำถามจาก client แล้ว **ไปหาคำตอบให้จนจบ** และ cache ไว้ | DNS ของ ISP, 8.8.8.8, 1.1.1.1, DNS ภายในองค์กร (AD) |
| **Root Server** | รู้ว่า TLD แต่ละตัวอยู่ที่ server ใด | 13 ชื่อ (a–m.root-servers.net) กระจายหลายร้อยแห่งด้วย anycast |
| **TLD Server** | รู้ว่าโดเมนในอยู่ที่ authoritative server ใด | server ของ .com, .th |
| **Authoritative Server** | **เจ้าของคำตอบจริง** ของโดเมนนั้น | Cloudflare DNS, Route 53, BIND ขององค์กร |

---

## 4. ลำดับการ Resolve ชื่อ (ต้องเข้าใจให้ขึ้นใจ)

ผู้ใช้เปิด `www.example.com`

```
 [Browser/OS]
   ① ดู cache ของ browser → cache ของ OS → ไฟล์ hosts
   ② ไม่พบ → ถาม Recursive Resolver (เช่น 10.0.0.53 หรือ 1.1.1.1)   ← Recursive query

 [Recursive Resolver]  (ถ้า cache ไม่มี จึงไล่ถามเองแบบ Iterative)
   ③ ถาม Root:  "www.example.com อยู่ไหน?"   → "ไม่รู้ ไปถาม .com ที่ server นี้"
   ④ ถาม .com TLD                             → "ไปถาม ns1.example.com"
   ⑤ ถาม Authoritative ns1.example.com         → "www.example.com = 93.184.216.34 (TTL 3600)"
   ⑥ เก็บ cache ตาม TTL แล้วตอบกลับ client

 [Browser] ⑦ เชื่อมต่อ 93.184.216.34:443
```
- **Recursive query:** client ขอคำตอบสุดท้ายจาก resolver
- **Iterative query:** resolver ถามทีละชั้น แต่ละชั้นตอบว่า "ไปถามที่นั่นต่อ" (referral)
- ครั้งต่อไปที่มีคนถามชื่อเดิม resolver ตอบจาก cache ได้ทันที

---

## 5. DNS Record ที่ต้องรู้

| Record | ความหมาย | ตัวอย่าง |
|---|---|---|
| **A** | ชื่อ → **IPv4** | `www  A  93.184.216.34` |
| **AAAA** | ชื่อ → **IPv6** | `www  AAAA  2606:2800:220:1::248` |
| **CNAME** | ชื่อเล่น → **ชื่ออื่น** (alias) | `shop  CNAME  shops.myplatform.com.` |
| **MX** | **mail server** ของโดเมน (มี priority, ตัวเลขน้อยก่อน) | `@  MX 10 mail1.example.com.` |
| **NS** | authoritative name server ของโดเมน | `@  NS  ns1.example.com.` |
| **TXT** | ข้อความอิสระ: **SPF, DKIM, DMARC**, ยืนยันความเป็นเจ้าของโดเมน | `@ TXT "v=spf1 include:_spf.google.com -all"` |
| **PTR** | **IP → ชื่อ** (reverse lookup) | `34.216.184.93.in-addr.arpa PTR www.example.com.` |
| **SOA** | ข้อมูลหลักของ zone (serial, refresh, TTL ขั้นต่ำ) | มี 1 ตัวต่อ zone |
| **SRV** | บริการ + port + host | `_ldap._tcp.corp.local SRV 0 100 389 dc1.corp.local.` (AD ใช้หา DC) |
| **CAA** | CA ใดออก cert ให้โดเมนนี้ได้ | `@ CAA 0 issue "letsencrypt.org"` |

**ข้อควรรู้**
- **CNAME ห้ามอยู่ที่ zone apex** (`example.com` เปล่า ๆ) เพราะ apex ต้องมี SOA/NS อยู่แล้ว ผู้ให้บริการบางรายจึงมี **ALIAS/ANAME/CNAME flattening** แทน
- **PTR สำคัญกับ mail server**: ไม่มี PTR หรือ PTR ไม่ตรง อีเมลมักถูกปฏิเสธว่าเป็นสแปม
- **SPF/DKIM/DMARC** ป้องกันการปลอมอีเมลในนามโดเมนเรา (Level 52 ของ SI-Track)

---

## 6. TTL และ Cache

- **TTL (Time To Live)** = วินาทีที่ resolver/เครื่องเก็บคำตอบไว้ใน cache
- TTL ยาว (เช่น 86400 = 1 วัน): ลดโหลด ตอบเร็ว แต่ **เปลี่ยน IP แล้วกระจายช้า**
- TTL สั้น (เช่น 300 = 5 นาที): เปลี่ยนได้เร็ว แต่ query มากขึ้น
- **Negative caching:** คำตอบว่า "ไม่มีชื่อนี้" (NXDOMAIN) ก็ถูก cache ด้วย

> 🏢 **แนวปฏิบัติก่อนย้าย server/เปลี่ยน IP:** ลด TTL เหลือ 300 วินาที **ล่วงหน้าอย่างน้อยเท่ากับ TTL เดิม** (เช่น TTL เดิม 1 วัน ต้องลดก่อน 1 วัน) → วันย้ายเปลี่ยน record แล้วทุกคนเห็นภายใน 5 นาที → หลังย้ายเสร็จค่อยเพิ่ม TTL กลับ

**ล้าง cache ที่เครื่อง**
```bash
ipconfig /flushdns                   # Windows
ipconfig /displaydns                 # ดู cache
sudo resolvectl flush-caches         # Linux (systemd-resolved)
sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder   # macOS
```

---

## 7. เครื่องมือ: dig และ nslookup

```bash
nslookup www.example.com                 # ใช้ DNS ที่เครื่องตั้งไว้
nslookup www.example.com 8.8.8.8         # ถาม server ที่ระบุ
nslookup -type=mx gmail.com

dig www.example.com                      # แสดงรายละเอียด (Linux/macOS)
dig www.example.com +short               # แสดงแค่คำตอบ
dig @1.1.1.1 example.com AAAA
dig example.com MX +short
dig -x 8.8.8.8                           # reverse lookup (PTR)
dig +trace www.example.com               # ไล่ตั้งแต่ root ทีละขั้น
dig example.com NS / SOA / TXT
```

**PowerShell:** `Resolve-DnsName www.example.com -Type A -Server 1.1.1.1`

### อ่านผล dig
```
;; ->>HEADER<<- opcode: QUERY, status: NOERROR      ← NOERROR = พบ, NXDOMAIN = ไม่มีชื่อนี้, SERVFAIL = server มีปัญหา
;; ANSWER SECTION:
www.example.com.   3600  IN  A  93.184.216.34        ← ชื่อ  TTL(วินาที)  class  type  ค่า
;; Query time: 12 msec
;; SERVER: 1.1.1.1#53
```

| Status | ความหมาย |
|---|---|
| **NOERROR** | สำเร็จ (ถ้าไม่มี ANSWER = ชื่อมี แต่ไม่มี record ชนิดนั้น) |
| **NXDOMAIN** | ไม่มีชื่อนี้ (สะกดผิด, ยังไม่ได้สร้าง record) |
| **SERVFAIL** | resolver หาคำตอบไม่ได้ (authoritative ล่ม, DNSSEC fail) |
| **REFUSED** | server ปฏิเสธ (ไม่อนุญาตให้ถาม recursive) |

---

## 8. DNS ในองค์กร

- **Active Directory พึ่ง DNS ทั้งหมด** — เครื่องหา domain controller ผ่าน SRV record ถ้าเครื่อง client ตั้ง DNS เป็น 8.8.8.8 แทน DNS ของ AD จะ join domain/login ไม่ได้
- **Forwarder / Conditional forwarder:** DNS ภายในส่งต่อชื่อภายนอกไป resolver อื่น หรือส่งต่อเฉพาะบาง zone (เช่น zone ของบริษัทคู่ค้า/cloud)
- **Split-horizon (split-brain) DNS:** ตอบคำตอบต่างกันตามผู้ถาม เช่น `mail.company.com` ผู้ใช้ภายในได้ IP ภายใน 10.x ผู้ใช้ภายนอกได้ public IP
- **Primary/Secondary:** zone ต้นฉบับอยู่ที่ primary แล้ว **zone transfer (AXFR/IXFR, TCP 53)** ไปยัง secondary — ต้องจำกัดให้ transfer ได้เฉพาะ secondary ที่อนุญาต
- **Redundancy:** ทุกเครื่องควรมี DNS อย่างน้อย 2 ตัว

---

## 9. DNS กับความปลอดภัย

| หัวข้อ | สาระ |
|---|---|
| **DNS ไม่เข้ารหัส** (UDP 53 แบบเดิม) | ใครอยู่กลางทางเห็นว่าเราเข้าเว็บอะไร และปลอมคำตอบได้ |
| **DoT (DNS over TLS, TCP 853) / DoH (DNS over HTTPS, 443)** | เข้ารหัส query; องค์กรต้องมีนโยบาย เพราะ DoH ใน browser อาจข้าม DNS ขององค์กร |
| **DNSSEC** | ลงลายเซ็นดิจิทัลให้คำตอบ ป้องกันการปลอม (ไม่ได้เข้ารหัส) |
| **DNS filtering** | block โดเมนอันตราย/โฆษณา (Pi-hole, DNS security ของ NGFW, Cisco Umbrella, Cloudflare Gateway) |
| **DNS tunneling** | มัลแวร์ส่งข้อมูลออกผ่าน query DNS — ตรวจจาก query ยาว/ผิดปกติ |
| **DNS log** | เป็นหลักฐานสำคัญในการสืบสวนว่าเครื่องไหนติดต่อโดเมนอันตราย |

---

## 10. แก้ปัญหา DNS ทีละขั้น

```
 1) ping 8.8.8.8 ได้ แต่ ping google.com ไม่ได้ → ปัญหา DNS แน่นอน
 2) ipconfig /all → DNS server ที่เครื่องใช้คืออะไร ถูกต้องไหม
 3) nslookup google.com <DNS ของเครื่อง>  vs  nslookup google.com 8.8.8.8
      - ถามที่อื่นได้ แต่ถามของเราไม่ได้ → DNS server ภายในมีปัญหา/ถูก firewall บล็อก
 4) ชื่อภายใน resolve ไม่ได้ → เครื่องใช้ DNS ภายนอกแทน DNS ภายใน? DNS suffix ถูกไหม?
 5) บางคนเห็น IP เก่า → cache/TTL ยังไม่หมด → flushdns, ตรวจ TTL
 6) ตรวจไฟล์ hosts: C:\Windows\System32\drivers\etc\hosts หรือ /etc/hosts
```

---

## 11. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| เปลี่ยน DNS record แล้วทุกคนเห็นทันที | ต้องรอ cache หมดอายุตาม TTL |
| DNS ใช้ UDP อย่างเดียว | TCP ใช้เมื่อคำตอบใหญ่/zone transfer/DoT |
| ใส่ CNAME ที่ example.com ได้ | ไม่ได้ตามมาตรฐาน (ใช้ ALIAS/flattening) |
| ตั้ง DNS เครื่องในโดเมน AD เป็น 8.8.8.8 ก็ได้ | ทำให้หา DC ไม่เจอ ต้องใช้ DNS ของ AD |
| DNSSEC เข้ารหัส query | DNSSEC ลงลายเซ็นยืนยัน ไม่ได้เข้ารหัส |

---

## 12. Cheat Sheet

```
DNS = ชื่อ ↔ IP · UDP 53 (TCP 53 คำตอบใหญ่/zone transfer)
ลำดับ: cache browser → cache OS → hosts → Resolver → Root → TLD → Authoritative
Record: A(IPv4) AAAA(IPv6) CNAME(alias) MX(mail) NS PTR(reverse) TXT(SPF/DKIM/DMARC) SOA SRV CAA
TTL = เวลา cache · ลด TTL ก่อนย้ายอย่างน้อยเท่า TTL เดิม
NOERROR / NXDOMAIN(ไม่มีชื่อ) / SERVFAIL(หาไม่ได้)
dig +short · dig +trace · dig -x · nslookup name server · Resolve-DnsName
AD ต้องใช้ DNS ภายใน (SRV) · Split-horizon = ตอบต่างกันใน/นอก
DoT 853 · DoH 443 · DNSSEC = ลายเซ็น ไม่ใช่การเข้ารหัส
```

---

## 13. แบบทดสอบ 10 ข้อ

1. เรียงลำดับ server ที่ resolver ไล่ถามเมื่อไม่มี cache
2. Recursive query ต่างจาก Iterative query อย่างไร
3. Record ใดใช้ระบุ mail server ของโดเมน
4. PTR record ใช้ทำอะไร สำคัญกับระบบใด
5. ทำไม CNAME ใส่ที่ zone apex ไม่ได้
6. จะย้ายเว็บไป IP ใหม่ TTL เดิม 86400 ควรทำอะไรล่วงหน้า
7. dig ได้ status NXDOMAIN หมายความว่าอะไร
8. คำสั่ง dig ดู MX ของ gmail.com แบบสั้น
9. Split-horizon DNS คืออะไร ยกตัวอย่าง
10. เครื่องในโดเมน AD ตั้ง DNS เป็น 8.8.8.8 จะเกิดปัญหาอะไร

<details><summary><b>เฉลย</b></summary>

1. Root → TLD → Authoritative
2. Recursive = client ขอคำตอบสุดท้ายจาก resolver; Iterative = resolver ถามทีละชั้นและได้ referral ไปชั้นถัดไป
3. MX
4. Reverse lookup (IP → ชื่อ) — สำคัญกับ mail server (ใช้ตรวจสแปม) และ log
5. Apex ต้องมี SOA/NS และ CNAME ห้ามอยู่ร่วมกับ record อื่นในชื่อเดียวกัน
6. ลด TTL เป็น ~300 วินาที ล่วงหน้าอย่างน้อย 1 วัน แล้วค่อยเปลี่ยน record ในวันย้าย
7. ไม่มีชื่อโดเมนนี้
8. `dig gmail.com MX +short`
9. ตอบคำตอบต่างกันตามผู้ถาม เช่น mail.company.com ภายในได้ IP 10.x ภายนอกได้ public IP
10. หา domain controller ไม่เจอ (SRV record อยู่ใน DNS ภายใน) → login/join domain/GPO ล้มเหลว และชื่อภายในทั้งหมด resolve ไม่ได้
</details>

---

➡️ ต่อไป: **Level 17 — NAT / PAT**
