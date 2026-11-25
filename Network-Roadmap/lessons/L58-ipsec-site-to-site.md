# บทเรียน Level 58 — Site-to-Site VPN (IPsec) (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจ IPsec ทั้ง IKE Phase 1/2, ESP/AH, tunnel/transport mode · เลือก parameter ที่ปลอดภัย (AES-GCM, SHA-2, DH group, PFS) · ทำ policy-based vs route-based (VTI) · ทำ VPN ข้ามยี่ห้อ · แก้ปัญหา tunnel ไม่ขึ้นได้อย่างเป็นระบบ

---

## 1. Site-to-Site VPN คืออะไร

**VPN (Virtual Private Network)** สร้าง **"อุโมงค์" ที่เข้ารหัส** ผ่านเครือข่ายที่ไม่น่าไว้ใจ (อินเทอร์เน็ต) ให้ 2 เครือข่ายเชื่อมกันเหมือนมีสายส่วนตัว
- **Site-to-site:** เชื่อม **เครือข่ายกับเครือข่าย** (HQ ↔ สาขา, DC ↔ cloud, บริษัท ↔ คู่ค้า) — ผู้ใช้ไม่ต้องติดตั้งอะไร อุปกรณ์ขอบ (router/firewall) ทำให้
- **Remote access:** เชื่อม **ผู้ใช้คนเดียว** เข้าเครือข่าย (Level 59)

```
 [LAN HQ 10.1.0.0/16]──[FW-HQ 203.0.113.10]═══ IPsec tunnel (เข้ารหัส) ═══[FW-BR 198.51.100.20]──[LAN สาขา 10.21.0.0/16]
                                       └──────────── ผ่านอินเทอร์เน็ต ────────────┘
```

**IPsec ให้:** Confidentiality (เข้ารหัส) · Integrity (ห้ามแก้ไข) · Authentication (ยืนยันว่าอีกฝั่งเป็นของจริง) · Anti-replay (ป้องกันการส่งซ้ำ)

---

## 2. องค์ประกอบของ IPsec

### IKE — Internet Key Exchange (UDP 500, และ 4500 เมื่อผ่าน NAT)
ทำหน้าที่ **เจรจา parameter + ยืนยันตัวตน + สร้างกุญแจ** — **IKEv2** (แนะนำ: เร็วกว่า ทนกว่า รองรับ EAP/MOBIKE) · IKEv1 (เก่า ยังพบบ่อย)

### 2 Phase
```
 Phase 1 (IKE SA / IKEv2: IKE_SA_INIT + IKE_AUTH)
   → สร้าง "ช่องทางปลอดภัยสำหรับคุยกันเอง" ระหว่าง 2 gateway
   → ตกลง: encryption, integrity/PRF, DH group, authentication (PSK/cert), lifetime
   → ยืนยันตัวตน (pre-shared key หรือ certificate)
 Phase 2 (IPsec SA / IKEv2: CHILD_SA)
   → สร้าง "อุโมงค์สำหรับข้อมูลผู้ใช้จริง"
   → ตกลง: encryption/integrity ของ ESP, PFS (DH group), lifetime
   → ⭐ Traffic Selector / Proxy ID: วงใดคุยกับวงใด (เช่น 10.1.0.0/16 ↔ 10.21.0.0/16)
```

| | Phase 1 | Phase 2 |
|---|---|---|
| ปกป้อง | การเจรจาของ IKE เอง | ข้อมูลผู้ใช้ |
| ผลลัพธ์ | IKE SA (1 คู่) | IPsec SA (อย่างน้อย 1 คู่ ขาเข้า/ขาออก) |
| Lifetime ทั่วไป | 8–24 ชม. (เช่น 28800/86400 วินาที) | 1 ชม. (3600 วินาที) |

### ESP vs AH

| | **ESP** (IP protocol **50**) ⭐ | AH (IP protocol 51) |
|---|---|---|
| เข้ารหัส | ✅ | ❌ |
| Integrity/Auth | ✅ | ✅ (รวม IP header) |
| ผ่าน NAT | ✅ (กับ NAT-T) | ❌ |
| ใช้จริง | **เกือบทั้งหมด** | แทบไม่ใช้ |

### Tunnel Mode vs Transport Mode
```
 Tunnel mode (site-to-site ⭐): [New IP: GW-A → GW-B][ESP][ Original IP + Data (เข้ารหัส) ][ESP trailer/ICV]
 Transport mode:                [Original IP][ESP][ Data (เข้ารหัส) ]   ← ใช้ระหว่าง host-host หรือกับ GRE (GRE over IPsec)
```

### NAT-T (NAT Traversal)
ESP ไม่มี port → ผ่าน PAT ไม่ได้ และ NAT แก้ IP header ทำให้ตรวจไม่ผ่าน → IKE ตรวจพบ NAT ระหว่างทางแล้ว **ห่อ ESP ด้วย UDP 4500** อัตโนมัติ
**Firewall ระหว่างทางต้องเปิด:** **UDP 500, UDP 4500, ESP (protocol 50)**

---

## 3. เลือก Parameter (Crypto Suite)

| ส่วน | ✅ แนะนำ | ❌ เลิกใช้ |
|---|---|---|
| Encryption | **AES-256-GCM** (AEAD = เข้ารหัส + integrity ในตัว), AES-128-GCM, AES-256-CBC | DES, 3DES |
| Integrity / PRF | **SHA-256, SHA-384, SHA-512** | MD5, SHA-1 |
| DH Group (key exchange) | **19, 20 (ECP 256/384)**, 21, **14 (2048-bit MODP)** ขั้นต่ำ | 1, 2, 5 |
| Authentication | **Certificate** (หลายไซต์/ปลอดภัยกว่า) หรือ PSK ที่ยาวและสุ่ม (≥ 20 ตัวอักษร) | PSK สั้น/เดาง่าย |
| PFS | **เปิด** (ใช้ DH group เดียวกับ Phase 1) | ปิด |
| IKE version | **IKEv2** | IKEv1 aggressive mode |

> 🔑 **ทั้งสองฝั่งต้องตกลง parameter ตรงกันอย่างน้อยหนึ่งชุด** — ความไม่ตรงกันคือสาเหตุอันดับต้น ๆ ที่ VPN ไม่ขึ้น

**PFS (Perfect Forward Secrecy):** สร้างกุญแจ Phase 2 ใหม่ด้วย DH ทุกครั้ง → ถ้ากุญแจชุดหนึ่งรั่ว ไม่กระทบชุดอื่นหรือข้อมูลในอดีต

---

## 4. Policy-Based vs Route-Based VPN

### Policy-based (crypto map / proxy ID)
- กำหนด **"traffic ใดต้องเข้ารหัส"** ด้วย ACL/policy (interesting traffic) เช่น `10.1.0.0/16 → 10.21.0.0/16`
- ❌ เพิ่ม subnet ต้องแก้ policy ทั้งสองฝั่ง, ไม่มี interface จึงใช้ dynamic routing ไม่ได้, traffic selector หลายคู่ซับซ้อน
- ✅ รองรับอุปกรณ์เก่า/บางยี่ห้อ

### Route-based ⭐ (VTI — Virtual Tunnel Interface)
- สร้าง **tunnel interface** แล้วใช้ **routing ตัดสินใจ** ว่าอะไรวิ่งเข้า tunnel (static หรือ **BGP/OSPF บน tunnel**)
- traffic selector ปกติเป็น `0.0.0.0/0 ↔ 0.0.0.0/0`
- ✅ เพิ่ม subnet แค่เพิ่ม route, ใช้ dynamic routing + failover หลาย tunnel ได้, monitor ได้เหมือน interface ทั่วไป
- ใช้กับ cloud (AWS/Azure VPN ใช้ route-based + BGP), FortiGate, Palo Alto, Cisco VTI

### GRE over IPsec
GRE รองรับ **multicast** (OSPF/EIGRP hello) และ protocol อื่น แล้วห่อด้วย IPsec เพื่อเข้ารหัส — ใช้กับอุปกรณ์ที่ไม่มี VTI หรือ DMVPN

---

## 5. ตัวอย่าง Config: Cisco IKEv2 + VTI

```
! ===== HQ (203.0.113.10) =====
crypto ikev2 proposal PROP-AES256
 encryption aes-gcm-256
 prf sha384
 group 20
crypto ikev2 policy POL-1
 proposal PROP-AES256
crypto ikev2 keyring KR-BR1
 peer BR1
  address 198.51.100.20
  pre-shared-key Xy9!vQ2#Lm7@Rt4$Pz8&
crypto ikev2 profile PROF-BR1
 match identity remote address 198.51.100.20 255.255.255.255
 authentication remote pre-share
 authentication local pre-share
 keyring local KR-BR1
 dpd 10 3 on-demand                                  ! Dead Peer Detection
!
crypto ipsec transform-set TS-GCM esp-gcm 256
 mode tunnel
crypto ipsec profile IPSEC-BR1
 set transform-set TS-GCM
 set pfs group20
 set ikev2-profile PROF-BR1
!
interface Tunnel1
 description VPN-TO-BRANCH1
 ip address 172.31.255.1 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 tunnel source GigabitEthernet0/0
 tunnel destination 198.51.100.20
 tunnel mode ipsec ipv4
 tunnel protection ipsec profile IPSEC-BR1
!
ip route 10.21.0.0 255.255.0.0 Tunnel1               ! หรือ BGP/OSPF บน tunnel
! ===== สาขาทำแบบเดียวกัน สลับ IP =====
```
```
show crypto ikev2 sa            ! Phase 1 (READY = ขึ้นแล้ว)
show crypto ipsec sa            ! Phase 2: #pkts encaps/decaps (ตัวนับต้องเพิ่มทั้งสองทาง)
show interface Tunnel1
```

---

## 6. VPN ข้ามยี่ห้อ — Parameter Sheet

ก่อนตั้ง VPN กับคู่ค้า/ผู้ให้บริการ ต้องแลก **parameter sheet** ให้ตรงกันทุกช่อง

| หัวข้อ | ฝั่งเรา | ฝั่งคู่ค้า |
|---|---|---|
| Peer public IP | 203.0.113.10 | 198.51.100.20 |
| IKE version | IKEv2 | IKEv2 |
| Phase 1: Enc / PRF / DH / Lifetime | AES-256-GCM / SHA-384 / 20 / 28800 | (ต้องตรง) |
| Authentication | PSK (ส่งแยกช่องทาง) / Cert | |
| Local/Remote ID | IP address / FQDN | |
| Phase 2: Enc / Integrity / PFS / Lifetime | AES-256-GCM / — / 20 / 3600 | |
| **Encryption domain / Traffic selector** | **10.1.0.0/16** | **10.21.0.0/16** |
| DPD / NAT-T | เปิด | เปิด |
| Tunnel IP (ถ้า route-based) | 172.31.255.1/30 | 172.31.255.2/30 |
| ผู้ติดต่อ/ช่วงเวลาทดสอบ | | |

> ⚠️ **ส่ง PSK แยกช่องทาง** จาก parameter sheet (เช่น โทรศัพท์/SMS/ระบบแชร์รหัส) ไม่ส่งในอีเมลฉบับเดียวกัน

---

## 7. แก้ปัญหา IPsec อย่างเป็นระบบ

```
 ① Underlay: ping/ทดสอบ public IP ของอีกฝั่งได้ไหม? firewall ระหว่างทางเปิด UDP 500/4500/ESP ไหม?
 ② Phase 1 ขึ้นไหม?
     ไม่ขึ้น → proposal ไม่ตรง (enc/hash/DH), PSK ผิด, peer ID/identity ไม่ตรง, IKE version ไม่ตรง, cert หมดอายุ/เวลาไม่ตรง (NTP)
 ③ Phase 2 ขึ้นไหม?
     ไม่ขึ้น → ⭐ TRAFFIC SELECTOR / PROXY ID ไม่ตรง (สาเหตุอันดับหนึ่งข้ามยี่ห้อ), transform set ไม่ตรง, PFS ไม่ตรง
 ④ ขึ้นแล้วแต่ข้อมูลไม่ผ่าน
     → route ไม่ชี้เข้า tunnel, NAT ทำ traffic ภายในเป็น public IP ก่อนเข้า tunnel (ต้องมี NAT exemption/no-NAT),
       firewall policy ภายในไม่อนุญาต, ขากลับ route ไม่ครบ
     → ดูตัวนับ encaps/decaps: encaps เพิ่ม แต่ decaps ไม่เพิ่ม = อีกฝั่งไม่ส่งกลับ (ปัญหาอยู่ฝั่งตรงข้าม)
 ⑤ ใช้ได้แต่บางแอปค้าง → MTU/MSS (ลด ip mtu/adjust-mss)
 ⑥ หลุดเป็นช่วง → lifetime ไม่ตรง/rekey มีปัญหา, DPD, ISP มีปัญหา
```
**Log ที่ช่วยได้:** `debug crypto ikev2` (Cisco), `diagnose debug application ike -1` (FortiGate), `show vpn ike-sa` / system log (Palo Alto), `swanctl --log` (strongSwan)

---

## 8. HA และ Redundancy ของ VPN

- **2 tunnel ไป 2 ISP** (หรือ 2 gateway) + **BGP/OSPF บน tunnel** หรือ static + IP SLA → failover อัตโนมัติ
- **DPD (Dead Peer Detection)** ตรวจว่าอีกฝั่งยังอยู่
- Cloud VPN (AWS/Azure) ให้ **2 tunnel** ต่อการเชื่อมต่อเสมอ — ต้องตั้งทั้งคู่
- ใช้ **SD-WAN** เพื่อจัดการ tunnel จำนวนมากและเลือกเส้นตามคุณภาพ (Level 60)

---

## 9. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| Phase 1 ขึ้นแล้ว VPN ใช้ได้แน่นอน | ต้องดู Phase 2 และตัวนับ encaps/decaps |
| เปิดแค่ UDP 500 ก็พอ | ต้องเปิด UDP 500, 4500 และ ESP (50) |
| ข้ามยี่ห้อ ตั้ง parameter ใกล้เคียงกันก็พอ | ต้องตรงกัน โดยเฉพาะ traffic selector |
| VPN ใช้ MTU 1500 ได้ | ต้องลด MTU/MSS |
| NAT ไม่เกี่ยวกับ VPN | ต้องยกเว้น NAT สำหรับ traffic ที่วิ่งเข้า tunnel |

---

## 10. Cheat Sheet

```
IPsec: IKE (UDP 500 / NAT-T 4500) + ESP (IP 50) · AH (51) แทบไม่ใช้
Phase 1 = IKE SA (enc, PRF, DH, auth, lifetime 8-24h) · Phase 2 = IPsec SA (ESP, PFS, lifetime 1h, traffic selector)
แนะนำ: IKEv2 · AES-GCM-256 · SHA-256/384 · DH 19/20/21 (≥14) · PFS · cert หรือ PSK ยาว
Tunnel mode (site-to-site) · Transport (GRE over IPsec)
Route-based (VTI + routing/BGP) ⭐ vs Policy-based (proxy ID/ACL)
แก้ปัญหา: underlay → P1 (proposal/PSK/ID) → P2 (traffic selector!) → route/NAT exemption/policy → MTU
show crypto ikev2 sa · show crypto ipsec sa (encaps/decaps)
ip mtu 1400 · ip tcp adjust-mss 1360 · DPD · 2 tunnel + BGP สำหรับ HA
```

---

## 11. แบบทดสอบ 10 ข้อ

1. IPsec ให้คุณสมบัติด้านความปลอดภัยอะไรบ้าง
2. Phase 1 และ Phase 2 ต่างกันอย่างไร
3. Firewall ระหว่างทางต้องเปิดอะไรให้ IPsec
4. ESP กับ AH ต่างกันอย่างไร ทำไมใช้ ESP
5. NAT-T คืออะไร
6. แนะนำ encryption, integrity และ DH group ที่ปลอดภัย
7. Policy-based กับ route-based VPN ต่างกันอย่างไร ทำไม route-based นิยมกว่า
8. Phase 1 ขึ้นแต่ Phase 2 ไม่ขึ้น สาเหตุที่พบบ่อยที่สุดคืออะไร
9. VPN ขึ้นครบแต่ ping ข้ามไม่ได้ ตรวจอะไรบ้าง (3 ข้อ)
10. ตัวนับ encaps เพิ่มแต่ decaps ไม่เพิ่ม บอกอะไร

<details><summary><b>เฉลย</b></summary>

1. Confidentiality, Integrity, Authentication (และ anti-replay)
2. Phase 1 สร้าง IKE SA เพื่อเจรจาอย่างปลอดภัยและยืนยันตัวตน; Phase 2 สร้าง IPsec SA สำหรับเข้ารหัสข้อมูลผู้ใช้จริง (กำหนด traffic selector)
3. UDP 500, UDP 4500 และ ESP (IP protocol 50)
4. ESP เข้ารหัสและตรวจความถูกต้องได้ ผ่าน NAT ได้ (NAT-T); AH ตรวจความถูกต้องอย่างเดียว ไม่เข้ารหัส และผ่าน NAT ไม่ได้
5. ห่อ ESP ด้วย UDP 4500 เมื่อตรวจพบ NAT ระหว่างทาง
6. AES-256-GCM (หรือ AES-128-GCM), SHA-256/384, DH group 19/20/21 (ขั้นต่ำ 14)
7. Policy-based ใช้ ACL/proxy ID ระบุ traffic; route-based ใช้ tunnel interface + routing — นิยมกว่าเพราะเพิ่ม subnet ง่าย ใช้ dynamic routing และ failover ได้
8. Traffic selector/proxy ID ไม่ตรงกัน (รวมถึง transform set/PFS ไม่ตรง)
9. Route ชี้เข้า tunnel ทั้งสองฝั่ง, NAT exemption, firewall policy ภายใน (และขากลับ)
10. เราส่งเข้า tunnel แล้วแต่ไม่ได้รับกลับ — ปัญหาอยู่ฝั่งตรงข้าม (route/policy/NAT ของอีกฝั่ง)
</details>

---

➡️ ต่อไป: **Level 59 — Remote Access VPN**
