# บทเรียน Level 65 — Cryptography & PKI สำหรับ Network Engineer (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจ symmetric/asymmetric encryption, hash, HMAC, digital signature, key exchange · โครงสร้าง certificate X.509, CA, chain of trust · ขั้นตอนขอ cert (CSR) · CRL/OCSP · รูปแบบไฟล์ PEM/DER/PFX · ใช้ openssl จัดการ cert · ตั้ง internal CA และต่ออายุ cert อัตโนมัติ (ACME)

---

## 1. ทำไม Network Engineer ต้องรู้ Crypto/PKI

ใช้แทบทุกวันในงาน:
- **HTTPS/TLS** (เว็บ, หน้า admin ของอุปกรณ์, API)
- **IPsec VPN** (cert-based authentication)
- **802.1X EAP-TLS** (cert ของผู้ใช้/เครื่อง และ RADIUS server)
- **SSH** (host key, user key)
- **SSL inspection** บน firewall (CA ภายในที่ต้อง deploy ไปทุกเครื่อง)
- **Wi-Fi WPA3**, **SNMPv3**, **NTP/RADIUS shared secret**

ปัญหายอดฮิตในงาน: **cert หมดอายุทำระบบล่ม**, chain ไม่ครบ, ชื่อไม่ตรง, เวลาเครื่องผิด

---

## 2. Symmetric Encryption

**ใช้กุญแจเดียวกัน** ทั้งเข้ารหัสและถอดรหัส
```
 ข้อความ + กุญแจ K → [AES] → ciphertext → [AES] + กุญแจ K → ข้อความ
```
- ✅ **เร็วมาก** เหมาะกับข้อมูลปริมาณมาก (ทุก byte ของ VPN/HTTPS)
- ❌ **ปัญหาการแจกกุญแจ:** จะส่งกุญแจให้อีกฝั่งอย่างปลอดภัยได้อย่างไร?
- อัลกอริทึม: **AES-128/256** (มาตรฐาน), **ChaCha20** (เร็วบนอุปกรณ์ไม่มี AES hardware) · ❌ DES, 3DES, RC4 (เลิกใช้)
- โหมด: **GCM** (AEAD — เข้ารหัส + ตรวจความถูกต้องในตัว ⭐), CBC (เก่ากว่า ต้องใช้ HMAC แยก)

---

## 3. Asymmetric (Public-Key) Encryption

ใช้ **คู่กุญแจ**: **Public key** (เปิดเผยได้) และ **Private key** (เก็บเป็นความลับ ห้ามรั่วเด็ดขาด)
```
 เข้ารหัสด้วย Public key ของ B → ถอดได้ด้วย Private key ของ B เท่านั้น   (ความลับ)
 ลงนามด้วย Private key ของ A → ตรวจได้ด้วย Public key ของ A             (ยืนยันตัวตน/ลายเซ็น)
```
- ✅ แก้ปัญหาการแจกกุญแจ, ใช้ทำ digital signature
- ❌ **ช้ามาก** — ไม่ใช้เข้ารหัสข้อมูลจำนวนมาก
- อัลกอริทึม: **RSA** (2048 บิตขั้นต่ำ, 3072/4096), **ECC/ECDSA** (P-256/P-384 — กุญแจสั้นกว่า เร็วกว่า ความปลอดภัยเทียบเท่า), **Ed25519**
- (Post-quantum crypto เช่น ML-KEM กำลังเริ่มถูกนำมาใช้ร่วมใน TLS/VPN รุ่นใหม่)

### ใช้ร่วมกัน (Hybrid) — วิธีที่ TLS/IPsec ทำจริง
```
 1) ใช้ asymmetric (cert + ECDHE) ยืนยันตัวตนและ "ตกลงกุญแจ" อย่างปลอดภัย
 2) ใช้ symmetric (AES-GCM) เข้ารหัสข้อมูลจริงด้วยกุญแจที่ตกลงได้ (เร็ว)
```

### Key Exchange — Diffie-Hellman (DH/ECDH)
สองฝั่ง **สร้างกุญแจร่วมกันได้โดยไม่ต้องส่งกุญแจข้ามเครือข่าย** แม้มีคนดักอยู่
- **Ephemeral (DHE/ECDHE)** = สร้างใหม่ทุก session → **Forward Secrecy**: private key ของ server รั่วในอนาคตก็ถอดรหัส session ในอดีตไม่ได้
- DH group ใน IPsec (14, 19, 20, 21) = ขนาด/ชนิดของ DH (Level 58)

---

## 4. Hash, HMAC และ Digital Signature

### Hash Function
แปลงข้อมูลขนาดใดก็ได้เป็น **ค่าความยาวคงที่ (digest)** แบบทางเดียว (ย้อนกลับไม่ได้) และข้อมูลเปลี่ยน 1 บิต hash เปลี่ยนทั้งหมด
- ✅ **SHA-256, SHA-384, SHA-512, SHA-3** · ❌ **MD5, SHA-1** (ชนกันได้ — เลิกใช้ด้านความปลอดภัย)
- ใช้: ตรวจความสมบูรณ์ของไฟล์ (firmware/ISO), เก็บรหัสผ่าน (ร่วมกับ salt + อัลกอริทึมช้า เช่น bcrypt/Argon2), ส่วนหนึ่งของลายเซ็น
```bash
sha256sum firmware.bin          # Linux
Get-FileHash firmware.bin -Algorithm SHA256   # Windows — เทียบกับค่าที่ผู้ผลิตประกาศก่อนติดตั้ง
```

### HMAC (Hash-based Message Authentication Code)
hash + **กุญแจลับร่วม** → พิสูจน์ทั้ง **integrity** และว่ามาจากผู้ที่มีกุญแจ — ใช้ใน IPsec, SNMPv3, routing protocol authentication, API

### Digital Signature
```
 ผู้ส่ง: hash(ข้อมูล) → เข้ารหัส hash ด้วย PRIVATE key ของตน = ลายเซ็น
 ผู้รับ: ถอดลายเซ็นด้วย PUBLIC key ของผู้ส่ง → เทียบกับ hash ที่คำนวณเอง → ตรงกัน = ของแท้ ไม่ถูกแก้
```
ให้ **Authentication + Integrity + Non-repudiation** — ใช้ใน certificate, code signing, firmware signing

---

## 5. PKI และ Certificate

**ปัญหา:** จะรู้ได้อย่างไรว่า public key ที่ได้รับเป็นของ `bank.example.com` จริง ไม่ใช่ของผู้โจมตี?
**ทางแก้:** **Certificate Authority (CA)** ที่ทุกคนเชื่อถือ **ลงลายเซ็นรับรอง** ว่า public key นี้เป็นของชื่อนี้ → **Certificate (X.509)**

### ข้อมูลใน Certificate X.509

| Field | ตัวอย่าง |
|---|---|
| **Subject** (CN) | CN=vpn.company.example |
| **SAN (Subject Alternative Name)** ⭐ | DNS:vpn.company.example, DNS:vpn2.company.example, IP:203.0.113.10 — **browser ใช้ SAN ตรวจชื่อ** (ไม่ดู CN แล้ว) |
| **Issuer** | CA ที่ออก cert |
| **Validity** | Not Before / **Not After (วันหมดอายุ)** |
| **Public Key** | RSA 2048 / ECDSA P-256 |
| **Key Usage / Extended Key Usage** | Digital Signature, Key Encipherment · **Server Authentication**, Client Authentication |
| Serial number, Signature algorithm | |
| CRL Distribution Point / AIA (OCSP) | ที่ตรวจสถานะการเพิกถอน |

### Chain of Trust
```
 Root CA (self-signed, อยู่ใน trust store ของ OS/browser แล้ว — เก็บ offline)
   └─ ลงนาม → Intermediate CA (ใช้ออก cert จริง)
                 └─ ลงนาม → Server/Leaf certificate (vpn.company.example)
```
- server ต้อง **ส่ง leaf + intermediate** ให้ client (client มี root อยู่แล้ว) — **ลืมส่ง intermediate = ปัญหาอันดับหนึ่ง** (บาง browser หาเองได้ แต่แอป/curl/มือถือจะ error)
- Root CA ถูกเก็บ **offline** เพื่อความปลอดภัย จึงใช้ intermediate ออก cert ประจำวัน

### Public CA vs Private (Internal) CA

| | Public CA | Private/Internal CA |
|---|---|---|
| ตัวอย่าง | DigiCert, Sectigo, GlobalSign, **Let's Encrypt** (ฟรี) | **AD Certificate Services (AD CS)**, step-ca, EJBCA, HashiCorp Vault, CA ของ firewall |
| เชื่อถือโดย | ทุก browser/OS อัตโนมัติ | เฉพาะเครื่องที่ติดตั้ง root CA ขององค์กร (deploy ผ่าน GPO/MDM) |
| ใช้กับ | เว็บ/บริการที่คนภายนอกเข้า | ระบบภายใน, 802.1X EAP-TLS, VPN cert, SSL inspection, อุปกรณ์เครือข่าย |
| ชื่อ | ต้องเป็นโดเมนที่พิสูจน์ความเป็นเจ้าของได้ | ใช้ชื่อภายในได้ |

### Validation Level (Public CA)
**DV** (ยืนยันแค่ความเป็นเจ้าของโดเมน — Let's Encrypt) · **OV** (ยืนยันองค์กร) · **EV** (ยืนยันเข้มงวด)

---

## 6. ขั้นตอนขอ Certificate

```
 1) สร้าง private key บนเครื่อง/อุปกรณ์ (ไม่ส่ง key ให้ใคร)
 2) สร้าง CSR (Certificate Signing Request) = public key + subject/SAN + ลายเซ็นด้วย private key
 3) ส่ง CSR ให้ CA → CA ตรวจสอบ (DV/OV) → ออก certificate
 4) ติดตั้ง certificate + intermediate chain บนเครื่อง/อุปกรณ์ (คู่กับ private key เดิม)
 5) บันทึกวันหมดอายุ + ตั้งการแจ้งเตือน/ต่ออายุอัตโนมัติ
```
```bash
# สร้าง key + CSR พร้อม SAN
openssl req -new -newkey rsa:2048 -nodes -keyout vpn.key -out vpn.csr \
  -subj "/C=TH/O=Company/CN=vpn.company.example" \
  -addext "subjectAltName=DNS:vpn.company.example,DNS:vpn2.company.example"
openssl req -in vpn.csr -noout -text           # ตรวจ CSR
```

---

## 7. Revocation — เพิกถอน Certificate

เมื่อ private key รั่ว, พนักงานลาออก (client cert), อุปกรณ์หาย → ต้อง **เพิกถอน** ก่อนหมดอายุ
- **CRL (Certificate Revocation List):** รายการ serial ที่ถูกเพิกถอน ดาวน์โหลดเป็นระยะ (ใหญ่ ไม่ real-time)
- **OCSP (Online Certificate Status Protocol):** ถามสถานะของ cert ทีละใบแบบ online · **OCSP stapling** = server แนบผลตรวจมาให้ (เร็วและเป็นส่วนตัวกว่า)
- ⚠️ ถ้า RADIUS/VPN ตรวจ CRL/OCSP แต่เข้าถึง CRL/OCSP ไม่ได้ อาจปฏิเสธทุกการเชื่อมต่อ (หรือยอมทั้งหมด) — ต้องออกแบบให้เข้าถึงได้เสมอ

> 💡 แนวโน้ม: cert อายุสั้นลงเรื่อย ๆ (Let's Encrypt 90 วัน และอุตสาหกรรมตกลงลดอายุสูงสุดของ public TLS cert ลงเป็นขั้น ๆ ในอนาคต) → ลดความเสียหายจาก key รั่วและบังคับให้ใช้ **การต่ออายุอัตโนมัติ**

---

## 8. รูปแบบไฟล์ Certificate

| รูปแบบ | นามสกุล | ลักษณะ | ใช้กับ |
|---|---|---|---|
| **PEM** | .pem .crt .cer .key | **ข้อความ Base64** ขึ้นต้น `-----BEGIN CERTIFICATE-----` · ใส่หลาย cert ต่อกันได้ (chain) | Linux, Apache/Nginx, อุปกรณ์เครือข่ายส่วนใหญ่ |
| **DER** | .der .cer | binary | Java, Windows บางส่วน |
| **PKCS#12 / PFX** | .pfx .p12 | **binary รวม cert + private key + chain** มีรหัสผ่าน | Windows/IIS, import เข้า firewall/อุปกรณ์ |
| PKCS#7 | .p7b | cert + chain (ไม่มี key) | Windows |

```bash
openssl x509 -in cert.pem -noout -text                         # ดูรายละเอียด
openssl x509 -in cert.pem -noout -subject -issuer -dates -ext subjectAltName
openssl x509 -in cert.der -inform der -out cert.pem            # DER → PEM
openssl pkcs12 -export -inkey vpn.key -in vpn.crt -certfile chain.pem -out vpn.pfx   # → PFX
openssl pkcs12 -in vpn.pfx -nodes -out all.pem                 # PFX → PEM
openssl verify -CAfile root-and-intermediate.pem vpn.crt       # ตรวจ chain
# ตรวจว่า key ตรงกับ cert (ค่า hash ต้องเท่ากัน)
openssl x509 -noout -pubkey -in vpn.crt | openssl sha256
openssl pkey -pubout -in vpn.key | openssl sha256
# ดู cert ของ server จริง
echo | openssl s_client -connect vpn.company.example:443 -servername vpn.company.example 2>/dev/null | openssl x509 -noout -dates
```

---

## 9. Internal CA และ Automation

### Internal CA ที่ดี
- **Two-tier:** Root CA **offline** + Issuing (intermediate) CA online
- ป้องกัน private key ของ CA (HSM ถ้าเป็นไปได้), กำหนด template/อายุ cert, เผยแพร่ CRL/OCSP ให้เข้าถึงได้
- Deploy root CA ไปทุกเครื่องผ่าน **GPO/Intune/MDM**
- **Auto-enrollment** (AD CS) ให้เครื่อง/ผู้ใช้ได้ cert อัตโนมัติ (ใช้กับ 802.1X EAP-TLS, VPN)

### ACME — ต่ออายุอัตโนมัติ
- โปรโตคอลที่ Let's Encrypt ใช้ — client (certbot, acme.sh, Caddy, Traefik, cert-manager บน Kubernetes) ขอและต่ออายุ cert เอง
- ใช้กับ internal CA ได้ด้วย (step-ca, Vault, AD CS ผ่านเครื่องมือเสริม)

### Certificate Inventory & Monitoring
- รวบรายการ cert ทั้งหมด (สแกน port 443/8443/636/993 ฯลฯ, ดึงจากอุปกรณ์) พร้อม **วันหมดอายุ เจ้าของ ตำแหน่งติดตั้ง**
- **แจ้งเตือนล่วงหน้า 60/30/14/7 วัน** — cert หมดอายุเป็นสาเหตุ outage ที่ป้องกันได้ง่ายที่สุด

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| HTTPS ใช้ RSA เข้ารหัสข้อมูลทั้งหมด | ใช้ asymmetric ตกลงกุญแจ แล้วใช้ symmetric (AES) เข้ารหัสข้อมูล |
| Hash คือการเข้ารหัส | Hash เป็นทางเดียว ถอดกลับไม่ได้ |
| CSR มี private key | CSR มี public key; private key อยู่ที่ผู้ขอเท่านั้น |
| Browser ตรวจชื่อจาก CN | ตรวจจาก **SAN** |
| ติดตั้ง cert ใบเดียวก็พอ | ต้องติดตั้ง intermediate chain ด้วย |
| cert ภายในใช้ self-signed แยกทุกเครื่องได้ | ใช้ internal CA เพื่อจัดการและเชื่อถือได้จากศูนย์กลาง |

---

## 11. Cheat Sheet

```
Symmetric (AES-GCM, ChaCha20): เร็ว · ปัญหาแจกกุญแจ
Asymmetric (RSA ≥2048, ECDSA P-256, Ed25519): public/private · ช้า · ใช้ตกลงกุญแจ/ลายเซ็น
ECDHE = ตกลงกุญแจ + forward secrecy · TLS/IPsec = hybrid
Hash SHA-256+ (ไม่ใช้ MD5/SHA-1) · HMAC = hash + key · Signature = hash เข้ารหัสด้วย private key
X.509: Subject, SAN ⭐, Issuer, Validity, Public key, EKU · Chain: Root (offline) → Intermediate → Leaf
ส่ง intermediate ด้วยเสมอ · Public CA (Let's Encrypt/DigiCert) vs Internal CA (AD CS/step-ca)
CSR: key → CSR → CA → ติดตั้ง cert + chain · Revocation: CRL / OCSP (stapling)
PEM (text, base64) · DER (binary) · PFX/P12 (cert+key+chain, รหัสผ่าน)
openssl x509 -noout -text|-dates · openssl verify · openssl pkcs12 · s_client -servername
ACME ต่ออายุอัตโนมัติ · inventory + แจ้งเตือนก่อนหมดอายุ
```

---

## 12. แบบทดสอบ 10 ข้อ

1. Symmetric กับ asymmetric encryption ต่างกันอย่างไร TLS ใช้อย่างไหน
2. Forward secrecy คืออะไร ได้จากอะไร
3. Hash ต่างจาก encryption อย่างไร ยกตัวอย่างการใช้ hash ในงาน network
4. Digital signature ทำงานอย่างไร
5. SAN คืออะไร ทำไมสำคัญ
6. Chain of trust ประกอบด้วยอะไร และปัญหาที่พบบ่อยที่สุดคืออะไร
7. ขั้นตอนขอ certificate จาก CA
8. CRL กับ OCSP ต่างกันอย่างไร
9. PEM กับ PFX ต่างกันอย่างไร
10. ทำไมองค์กรต้องมี certificate inventory และการต่ออายุอัตโนมัติ

<details><summary><b>เฉลย</b></summary>

1. Symmetric ใช้กุญแจเดียว (เร็ว); asymmetric ใช้คู่กุญแจ (ช้า แก้ปัญหาแจกกุญแจ/ทำลายเซ็น) — TLS ใช้ทั้งคู่: asymmetric ยืนยันตัวตน/ตกลงกุญแจ แล้ว symmetric เข้ารหัสข้อมูล
2. กุญแจของแต่ละ session สร้างใหม่ ถ้า private key ของ server รั่วภายหลังก็ถอดข้อมูลในอดีตไม่ได้ — ได้จาก ephemeral DH (ECDHE/DHE)
3. Hash เป็นทางเดียว ย้อนกลับไม่ได้ ใช้ตรวจความถูกต้อง; encryption ถอดกลับได้ด้วยกุญแจ — เช่น ตรวจ SHA-256 ของ firmware ก่อนติดตั้ง, HMAC ใน SNMPv3/IPsec
4. ผู้ส่ง hash ข้อมูลแล้วเข้ารหัส hash ด้วย private key; ผู้รับถอดด้วย public key ของผู้ส่งแล้วเทียบกับ hash ที่คำนวณเอง
5. รายชื่อ (DNS/IP) ที่ cert ใช้ได้ — browser ตรวจชื่อจาก SAN ถ้าชื่อที่เปิดไม่อยู่ใน SAN จะขึ้นคำเตือน
6. Root CA → Intermediate CA → Leaf cert — ปัญหาที่พบบ่อยคือ server ไม่ส่ง intermediate
7. สร้าง private key → สร้าง CSR → ส่งให้ CA ตรวจและออก cert → ติดตั้ง cert + chain คู่กับ key → ติดตามวันหมดอายุ
8. CRL เป็นรายการเพิกถอนที่ดาวน์โหลดเป็นระยะ; OCSP ตรวจสถานะทีละใบแบบ online (stapling ให้ server แนบผลมา)
9. PEM เป็นข้อความ base64 แยกไฟล์ได้; PFX เป็น binary รวม cert + private key + chain และมีรหัสผ่าน
10. Cert หมดอายุเป็นสาเหตุ outage ที่พบบ่อยและป้องกันได้ — ต้องรู้ว่ามี cert อะไรอยู่ที่ไหน หมดเมื่อไร และต่ออายุอัตโนมัติ (cert มีอายุสั้นลงเรื่อย ๆ)
</details>

---

➡️ ต่อไป: **Level 66 — 802.1X, NAC & Zero Trust**
