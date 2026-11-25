# บทเรียน Level 59 — Remote Access VPN (SSL VPN, IPsec, WireGuard, OpenVPN) (ฉบับละเอียด)

> อ่านจบแล้วจะ: เลือก remote access VPN ให้เหมาะสม · เข้าใจ full tunnel vs split tunnel · ตั้ง WireGuard และเข้าใจ AllowedIPs · บังคับ MFA และ posture check · hardening VPN portal · เข้าใจว่า ZTNA แตกต่างจาก VPN อย่างไร

---

## 1. Remote Access VPN คืออะไร

ให้ **ผู้ใช้แต่ละคน** (ทำงานจากบ้าน/เดินทาง/ผู้รับเหมา) เชื่อมต่อเข้าเครือข่ายองค์กรอย่างปลอดภัยผ่านอินเทอร์เน็ต
```
 [โน้ตบุ๊กที่บ้าน + VPN client] ═══ tunnel เข้ารหัส ═══ [VPN gateway/Firewall ขององค์กร] ── ระบบภายใน
   ได้ IP ภายในจาก pool (เช่น 10.99.0.0/22)
```

**ความเสี่ยงสำคัญ:** VPN gateway **เปิดสู่อินเทอร์เน็ต 24 ชั่วโมง** และให้สิทธิ์เข้าเครือข่ายภายใน จึงเป็น **เป้าหมายอันดับต้นของผู้โจมตีและ ransomware** (รหัสผ่านรั่ว, ช่องโหว่ของอุปกรณ์ VPN ที่ไม่ได้ patch)

---

## 2. ประเภทของ Remote Access VPN

| ประเภท | โปรโตคอล | ตัวอย่าง | จุดเด่น |
|---|---|---|---|
| **SSL/TLS VPN (client)** | TLS (TCP 443) + DTLS (UDP) | Cisco Secure Client (AnyConnect), Palo Alto GlobalProtect, FortiClient (ดูหมายเหตุ), Pulse/Ivanti | ผ่าน firewall/proxy ได้ง่าย (443) |
| **Clientless SSL VPN (web portal)** | HTTPS | เปิดผ่าน browser | ไม่ต้องติดตั้ง แต่ใช้ได้กับบางแอป — ผู้ผลิตหลายรายเลิกสนับสนุนแล้ว |
| **IPsec IKEv2 (client)** | UDP 500/4500 + ESP | Windows/macOS/iOS built-in, FortiClient, strongSwan | มาตรฐาน มีใน OS ไม่ต้องติดตั้ง |
| **WireGuard** | UDP (ค่าเริ่มต้น 51820) | WireGuard, Tailscale, Netbird | เรียบง่าย เร็ว โค้ดน้อย |
| **OpenVPN** | UDP/TCP (1194 หรือ 443) | OpenVPN Community/Access Server | ยืดหยุ่น open source ใช้แพร่หลาย |

> ⚠️ **หมายเหตุ:** Fortinet ประกาศเลิกฟีเจอร์ SSL VPN tunnel mode ใน FortiOS รุ่นใหม่ และแนะนำให้ย้ายไปใช้ **IPsec VPN (IKEv2)** หรือ **ZTNA** — ก่อนออกแบบให้ตรวจ roadmap ของผู้ผลิตที่ใช้เสมอ

---

## 3. Full Tunnel vs Split Tunnel

```
 Full tunnel:   ทุก traffic ของผู้ใช้ (รวม YouTube/อินเทอร์เน็ต) → วิ่งเข้า VPN → ออกอินเทอร์เน็ตที่องค์กร
 Split tunnel:  เฉพาะ traffic ไประบบภายใน (10.0.0.0/8) → VPN · อินเทอร์เน็ตทั่วไป → ออกจากบ้านผู้ใช้โดยตรง
```

| | Full tunnel | Split tunnel |
|---|---|---|
| ความปลอดภัย | ✅ ทุก traffic ผ่าน security stack ขององค์กร (web filter, IPS, DLP, log) | ❌ traffic อินเทอร์เน็ตไม่ถูกตรวจ (ต้องพึ่ง EDR/SSE) |
| Bandwidth องค์กร | ❌ ใช้มาก (ทุกคนดู video ผ่าน HQ) | ✅ ประหยัด |
| ประสบการณ์ผู้ใช้ | ❌ ช้ากว่า (โดยเฉพาะ Teams/Zoom/M365) | ✅ เร็ว |
| ทางสายกลาง | — | **Split tunnel + exclude เฉพาะ SaaS ที่เชื่อถือ** (เช่น Microsoft 365, Teams media) หรือใช้ **SSE/SASE** ตรวจ traffic อินเทอร์เน็ตจาก cloud |

---

## 4. WireGuard (เข้าใจง่ายที่สุด)

- โปรโตคอล VPN สมัยใหม่ (อยู่ใน Linux kernel) โค้ดน้อย เร็ว ใช้ cryptography สมัยใหม่ (Curve25519, ChaCha20-Poly1305) ไม่มีตัวเลือกให้ตั้งผิด
- แต่ละเครื่องมี **key pair** (private/public) — ยืนยันตัวตนด้วย public key ของ peer

```ini
# Server: /etc/wireguard/wg0.conf
[Interface]
Address    = 10.99.0.1/24
ListenPort = 51820
PrivateKey = <server-private-key>

[Peer]                         # ผู้ใช้ Somchai
PublicKey  = <somchai-public-key>
AllowedIPs = 10.99.0.2/32      # IP ที่อนุญาตให้ peer นี้ใช้เป็น source

# Client: wg0.conf
[Interface]
Address    = 10.99.0.2/32
PrivateKey = <somchai-private-key>
DNS        = 10.0.0.53

[Peer]
PublicKey  = <server-public-key>
Endpoint   = vpn.company.example:51820
AllowedIPs = 10.0.0.0/8, 10.99.0.0/24   # split tunnel · ใส่ 0.0.0.0/0 = full tunnel
PersistentKeepalive = 25                # รักษา NAT mapping
```
```bash
wg genkey | tee privatekey | wg pubkey > publickey
sudo wg-quick up wg0 ; sudo wg show
```

### AllowedIPs — แนวคิดสำคัญ ("Cryptokey Routing")
- **ขาออก (ทำหน้าที่เหมือน routing):** ปลายทางที่ตรงกับ AllowedIPs ของ peer ใด → ส่งเข้า peer นั้น
- **ขาเข้า (ทำหน้าที่เหมือน ACL):** packet ที่มาจาก peer ใด ต้องมี source IP อยู่ใน AllowedIPs ของ peer นั้น ไม่เช่นนั้นทิ้ง
- ฝั่ง client: AllowedIPs = วงที่จะส่งเข้า VPN (split/full) · ฝั่ง server: AllowedIPs = IP ของ client

**ข้อจำกัดสำหรับองค์กร:** WireGuard ล้วนไม่มีระบบจัดการผู้ใช้/MFA/posture ในตัว → ใช้ผลิตภัณฑ์ที่สร้างบน WireGuard (Tailscale/Headscale, Netbird, Firezone) หรือ VPN gateway เชิงพาณิชย์

---

## 5. OpenVPN (ภาพรวม)
- ใช้ TLS กับ **PKI (CA + certificate ของ server และ client)** + ทางเลือก username/password/MFA
- รองรับ UDP (เร็วกว่า) และ **TCP 443** (ผ่าน firewall เข้มงวดได้)
- จัดการ certificate ด้วย easy-rsa หรือ PKI ขององค์กร · เพิกถอน cert ของผู้ใช้ที่ลาออกด้วย CRL

---

## 6. การยืนยันตัวตนและความปลอดภัย

### MFA — บังคับเสมอ
รหัสผ่านอย่างเดียว **ไม่พอ** (phishing, รหัสซ้ำ, รหัสรั่วจากเว็บอื่น) → ต้องมี **MFA**
- **ดี:** แอป authenticator/push (FortiToken, Duo, Microsoft Authenticator) ผ่าน RADIUS/SAML
- **ดีที่สุด:** **phishing-resistant** — certificate บนเครื่อง + FIDO2/passkey (ผ่าน SAML/IdP)
- **หลีกเลี่ยง:** SMS OTP (SIM swap) — ใช้เมื่อไม่มีทางเลือก

### ยืนยันตัวตนผ่าน IdP (SAML/OIDC)
เชื่อม VPN กับ **Entra ID/Okta/Keycloak** → ใช้ MFA และ **conditional access** (ประเทศ, ความเสี่ยงของบัญชี) ของ IdP ได้

### Device Certificate + Posture Check (Host Checking)
ตรวจเครื่องก่อนให้เชื่อมต่อ: เป็นเครื่องขององค์กร (มี cert), OS อัปเดต, EDR/AV ทำงาน, disk encryption เปิด, firewall เปิด → ไม่ผ่านให้เข้าเฉพาะ remediation network หรือปฏิเสธ

### Authorization — Least Privilege
ไม่ให้ผู้ใช้ VPN ทุกคนเข้าทั้งเครือข่าย → แบ่ง **กลุ่ม (role)** ตาม AD group แล้วใช้ firewall policy จำกัด เช่น
- พนักงานทั่วไป: เข้าได้เฉพาะ intranet, file server, ERP
- ผู้รับเหมา: เฉพาะ server ที่ดูแล ช่วงเวลาที่กำหนด
- IT admin: management network (ผ่าน jump host)

---

## 7. Hardening VPN Gateway (สำคัญมาก)

1. **Patch ทันที** เมื่อผู้ผลิตออก advisory (ติดตาม PSIRT/CISA KEV) — ช่องโหว่ของอุปกรณ์ VPN ถูกโจมตีจริงซ้ำแล้วซ้ำเล่า
2. **MFA ทุกบัญชี** ไม่มีข้อยกเว้น (รวมบัญชี admin และบัญชีบริการ)
3. **ปิดหน้า admin จากอินเทอร์เน็ต** — จัดการ firewall จาก management network เท่านั้น
4. **จำกัดความพยายาม login** (lockout/rate-limit) และ **geo-IP** (อนุญาตเฉพาะประเทศที่มีพนักงาน)
5. **ปิดบัญชี local ที่ไม่จำเป็น**, ปิด protocol/cipher เก่า
6. **ส่ง log เข้า SIEM** แจ้งเตือน: login ล้มเหลวจำนวนมาก, login จากประเทศแปลก, impossible travel, login นอกเวลา
7. **Session timeout** และ re-authenticate เป็นระยะ
8. ทบทวนบัญชี VPN รายไตรมาส ลบบัญชีที่ไม่ใช้/คนลาออก

---

## 8. Remote Access VPN vs ZTNA

| | VPN | **ZTNA (Zero Trust Network Access)** |
|---|---|---|
| ได้สิทธิ์ | **เข้าเครือข่าย** (network-level) — เห็นหลายระบบ | **เข้าเฉพาะแอปที่ได้รับอนุญาต** (application-level) |
| ตรวจสอบ | ตอน login | **ต่อเนื่อง** (identity + device posture ทุก request/session) |
| เปิดสู่อินเทอร์เน็ต | VPN gateway มี port เปิดรอ | แอปมักซ่อนอยู่หลัง connector (outbound only) |
| Lateral movement | เครื่องที่ติดมัลแวร์สแกนเครือข่ายได้ | จำกัดมาก |
| ตัวอย่าง | AnyConnect, GlobalProtect, IPsec | Zscaler Private Access, Cloudflare Access, Prisma Access, FortiClient ZTNA, Tailscale (กึ่ง) |

แนวโน้มคือย้ายจาก VPN แบบเดิมไปสู่ **ZTNA/SASE** เป็นลำดับ (รายละเอียด Level 66 และ ISC/SI Level 47–48)

---

## 9. แก้ปัญหา Remote Access VPN

| อาการ | ตรวจ |
|---|---|
| เชื่อมต่อไม่ได้เลย | อินเทอร์เน็ตของผู้ใช้, port ถูกบล็อก (โรงแรม/Wi-Fi สาธารณะ บล็อก UDP), DNS ของชื่อ VPN, cert ของ gateway หมดอายุ |
| Login ไม่ผ่าน | รหัสผ่าน/บัญชีล็อก, MFA (เวลาเครื่องไม่ตรง), ไม่อยู่ในกลุ่มที่อนุญาต, posture ไม่ผ่าน |
| เชื่อมต่อได้แต่เข้าระบบภายในไม่ได้ | route/split tunnel ไม่ครอบวงนั้น, firewall policy ของกลุ่ม, **IP วงบ้านผู้ใช้ชนกับวงองค์กร** (เช่น ใช้ 192.168.1.0/24 ทั้งคู่), DNS ภายใน |
| ใช้ได้แต่ช้า | full tunnel + bandwidth องค์กรเต็ม, MTU (ลด MTU ของ VPN), อินเทอร์เน็ตผู้ใช้ |
| Teams/Zoom กระตุก | media วิ่งผ่าน VPN (full tunnel/TCP) → exclude media ของ SaaS ออกจาก tunnel |

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| VPN เข้ารหัสแล้วปลอดภัยครบ | ยังต้องมี MFA, patch, least privilege, posture, monitoring |
| Split tunnel ไม่ปลอดภัยเสมอ | ใช้ได้ถ้ามี EDR/SSE และ exclude เฉพาะ SaaS ที่เชื่อถือ |
| SMS OTP เพียงพอ | เสี่ยง SIM swap/phishing — ใช้ app/FIDO2 |
| ผู้ใช้ VPN ควรเข้าได้ทุกระบบ | ให้สิทธิ์ตามบทบาท (least privilege) |
| ZTNA กับ VPN เหมือนกัน | ZTNA ให้สิทธิ์ระดับแอปและตรวจต่อเนื่อง |

---

## 11. Cheat Sheet

```
Remote access = ผู้ใช้รายคน · เป้าหมายหลักของผู้โจมตี
SSL VPN (TCP 443 + DTLS) · IPsec IKEv2 (UDP 500/4500) · WireGuard (UDP 51820) · OpenVPN (UDP/TCP 1194/443)
Full tunnel (ตรวจทุก traffic, เปลือง) vs Split (เร็ว, ต้องมี EDR/SSE) · exclude SaaS media
WireGuard: key pair · AllowedIPs = routing ขาออก + ACL ขาเข้า · PersistentKeepalive
MFA บังคับ (app/push, ดีสุด FIDO2/cert) · SAML/IdP · posture check · least privilege ตามกลุ่ม
Hardening: patch ทันที · ปิด admin จาก internet · lockout/geo-IP · log → SIEM · ทบทวนบัญชี
ZTNA = สิทธิ์ระดับแอป + ตรวจต่อเนื่อง (ทางเลือกแทน VPN)
ปัญหาบ่อย: IP บ้านชนกับองค์กร · UDP ถูกบล็อก · MTU · DNS ภายใน
```

---

## 12. แบบทดสอบ 10 ข้อ

1. ทำไม VPN gateway จึงเป็นเป้าหมายของผู้โจมตี
2. Full tunnel กับ split tunnel ต่างกันอย่างไร ข้อดีข้อเสีย
3. WireGuard ใช้ protocol/port อะไรเป็นค่าเริ่มต้น
4. AllowedIPs ใน WireGuard ทำหน้าที่อะไรทั้งสองทิศทาง
5. ตั้ง AllowedIPs ฝั่ง client ให้เป็น full tunnel อย่างไร
6. ทำไมต้องบังคับ MFA และวิธีใดปลอดภัยที่สุด
7. Posture check ตรวจอะไรบ้าง
8. Hardening VPN gateway 5 ข้อ
9. ผู้ใช้เชื่อมต่อ VPN ได้แต่เข้า file server 192.168.1.20 ไม่ได้ ส่วนเพื่อนเข้าได้ สาเหตุที่เป็นไปได้คืออะไร
10. ZTNA ต่างจาก VPN อย่างไร

<details><summary><b>เฉลย</b></summary>

1. เปิดสู่อินเทอร์เน็ตตลอดเวลาและให้สิทธิ์เข้าเครือข่ายภายใน — รหัสรั่วหรือช่องโหว่ที่ไม่ได้ patch ทำให้ผู้โจมตีเข้ามาได้
2. Full tunnel ส่งทุก traffic ผ่านองค์กร (ตรวจได้ครบ แต่ช้าและเปลือง bandwidth); split tunnel ส่งเฉพาะ traffic ภายใน (เร็ว ประหยัด แต่ traffic อินเทอร์เน็ตไม่ผ่านการตรวจขององค์กร)
3. UDP 51820
4. ขาออก: กำหนดว่าปลายทางใดส่งเข้า peer นั้น (routing); ขาเข้า: ยอมรับเฉพาะ source IP ที่อยู่ในรายการ (ACL)
5. `AllowedIPs = 0.0.0.0/0` (และ `::/0` สำหรับ IPv6)
6. รหัสผ่านรั่ว/ถูก phishing บ่อย — ปลอดภัยที่สุดคือ phishing-resistant MFA (FIDO2/passkey หรือ certificate บนเครื่อง)
7. เครื่องเป็นของบริษัท (cert), OS อัปเดต, EDR/AV ทำงาน, disk encryption, firewall เปิด
8. Patch ทันที, MFA ทุกบัญชี, ปิดหน้า admin จากอินเทอร์เน็ต, lockout/geo-IP, ส่ง log เข้า SIEM (รวมถึง session timeout, ทบทวนบัญชี)
9. วงเครือข่ายบ้านของผู้ใช้เป็น 192.168.1.0/24 ชนกับวงขององค์กร เครื่องจึงส่งไปที่ LAN บ้านแทน VPN
10. ZTNA ให้สิทธิ์เฉพาะแอปที่อนุญาตและตรวจ identity/device ต่อเนื่อง; VPN ให้สิทธิ์ระดับเครือข่ายเมื่อ login สำเร็จ
</details>

---

➡️ ต่อไป: **Level 60 — SD-WAN & SASE**
