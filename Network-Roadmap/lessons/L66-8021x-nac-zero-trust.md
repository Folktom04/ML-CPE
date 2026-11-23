# บทเรียน Level 66 — 802.1X, NAC & Zero Trust (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจ 802.1X 3 บทบาทและ EAP methods · MAB สำหรับอุปกรณ์ที่ไม่รองรับ · Dynamic VLAN/dACL/SGT · CoA · วางแผน rollout แบบ monitor → low-impact → closed · ใช้ NAC (profiling, posture, guest) · เข้าใจ Zero Trust ตาม NIST 800-207 และนำไปใช้กับเครือข่าย

---

## 1. ปัญหา: ใครเสียบสายก็เข้าเครือข่ายได้

Port security จำกัดแค่ MAC (ปลอมได้), VLAN แบ่งได้แต่ไม่รู้ว่าเป็นใคร
**802.1X** = **ยืนยันตัวตนผู้ใช้/อุปกรณ์ "ก่อน" ให้เข้าเครือข่าย** ที่พอร์ต switch หรือ Wi-Fi และกำหนดสิทธิ์ตามตัวตนนั้น

---

## 2. 802.1X — 3 บทบาท

```
 [Supplicant]              [Authenticator]                 [Authentication Server]
 PC/โน้ตบุ๊ก/โทรศัพท์       Switch / AP / WLC                RADIUS (ISE, ClearPass, NPS, FreeRADIUS)
 (โปรแกรม 802.1X ใน OS)    (ประตู — ไม่ตัดสินเอง)            ตรวจกับ AD/LDAP/CA แล้วตัดสิน
        │──── EAPoL (EAP over LAN) ────►│────── RADIUS (EAP ห่อใน RADIUS) ──────►│
        │◄──────────────────────────────│◄── Access-Accept (+VLAN/dACL/SGT) ──────│
                                         │     หรือ Access-Reject
 ก่อนผ่าน: พอร์ตอนุญาตแค่ EAPoL (และสิ่งที่ตั้งไว้ใน pre-auth)
 หลังผ่าน: พอร์ตเปิดตามสิทธิ์ที่ server ส่งมา
```

---

## 3. EAP Methods

| Method | ยืนยันด้วย | ความปลอดภัย | หมายเหตุ |
|---|---|---|---|
| **EAP-TLS** ⭐ | **certificate ทั้ง client และ server** | **สูงสุด** — ไม่มีรหัสผ่านให้ขโมย/phish | ต้องมี PKI และแจก cert ให้ทุกเครื่อง (auto-enrollment/MDM) |
| **PEAP-MSCHAPv2** | username/password (ใน TLS tunnel) | ปานกลาง | ใช้แพร่หลาย (AD) · **ต้องบังคับตรวจ cert ของ RADIUS server** ไม่เช่นนั้นถูก evil-twin AP ขโมยรหัส (hash) ได้ |
| EAP-TTLS | username/password หรืออื่น ๆ ใน TLS tunnel | ปานกลาง | |
| EAP-FAST / TEAP | tunnel + หลายวิธี (TEAP รองรับ machine + user chaining) | ดี | TEAP เป็นมาตรฐานใหม่ |

**Machine vs User authentication:** ยืนยันเครื่องตอนบูต (ก่อน login — ให้ GPO/script ทำงาน) แล้วยืนยันผู้ใช้หลัง login (หรือใช้ chaining)

---

## 4. MAB — MAC Authentication Bypass

อุปกรณ์ที่ **ไม่มี supplicant** (printer, IP camera, IoT, อุปกรณ์การแพทย์, เครื่องรุ่นเก่า)
- switch รอ EAP ช่วงหนึ่ง ไม่มีคำตอบ → ส่ง **MAC address** ไปเป็น username ให้ RADIUS ตรวจ
- ⚠️ **MAC ปลอมได้ง่าย** → ต้องใช้ร่วมกับ:
  - **Profiling** (ตรวจว่าอุปกรณ์เป็นชนิดที่อ้างจริง จาก DHCP fingerprint, CDP/LLDP, HTTP user-agent, NMAP scan)
  - **ให้สิทธิ์จำกัด** (VLAN/dACL ของ IoT/printer เข้าได้แค่ server ที่จำเป็น)

### ลำดับบนพอร์ตเดียว (flexible authentication)
```
 interface Gi1/0/5
  authentication order dot1x mab        ! ลอง 802.1X ก่อน ถ้าไม่มีการตอบ → MAB
  authentication priority dot1x mab
```

---

## 5. Authorization — ให้สิทธิ์ตามตัวตน

RADIUS ส่งผลลัพธ์มาใน Access-Accept

| วิธี | ลักษณะ |
|---|---|
| **Dynamic VLAN** | ย้ายพอร์ตเข้า VLAN ตามกลุ่ม (พนักงาน VLAN 10, ผู้รับเหมา VLAN 60, ไม่ผ่าน posture → remediation VLAN) |
| **dACL (downloadable ACL)** | ACL ที่ server ส่งมาให้พอร์ตนั้นเฉพาะ session |
| **SGT (Security Group Tag) / TrustSec / Group-based policy** | แปะ tag ตามบทบาท แล้วบังคับ policy ตาม tag ทั่วเครือข่าย (ไม่ผูกกับ IP/VLAN) — พื้นฐานของ micro-segmentation |
| Session timeout / re-auth | บังคับยืนยันตัวตนซ้ำเป็นระยะ |

### CoA — Change of Authorization (RFC 5176)
RADIUS server **สั่งเปลี่ยนสิทธิ์ของ session ที่กำลังใช้อยู่** ได้ทันที (re-authenticate, port bounce, ย้าย VLAN, ใส่ dACL ใหม่)
ใช้เมื่อ: posture เปลี่ยน, profiling รู้ชนิดอุปกรณ์แล้ว, **SIEM/EDR แจ้งว่าเครื่องติดมัลแวร์ → quarantine อัตโนมัติ**

---

## 6. ตัวอย่าง Config (Cisco IOS-XE แบบ legacy ที่อ่านเข้าใจง่าย)

```
aaa new-model
radius server ISE-1
 address ipv4 10.0.0.71 auth-port 1812 acct-port 1813
 key R@diusK3y!
aaa group server radius ISE
 server name ISE-1
aaa authentication dot1x default group ISE
aaa authorization network default group ISE
aaa accounting dot1x default start-stop group ISE
aaa server radius dynamic-author                  ! รับ CoA
 client 10.0.0.71 server-key R@diusK3y!
dot1x system-auth-control                         ! เปิด 802.1X ทั้งเครื่อง
!
interface range Gi1/0/1 - 46
 switchport mode access
 switchport access vlan 10
 switchport voice vlan 110
 authentication host-mode multi-domain           ! 1 data + 1 voice (phone + PC)
 authentication order dot1x mab
 authentication priority dot1x mab
 authentication port-control auto
 authentication open                              ! ⭐ monitor/low-impact mode (ดูข้อ 7)
 authentication periodic
 authentication timer reauthenticate server
 mab
 dot1x pae authenticator
 dot1x timeout tx-period 7
 spanning-tree portfast
!
show authentication sessions [interface Gi1/0/5 details]
show access-session
```
(IOS-XE รุ่นใหม่แนะนำรูปแบบ IBNS 2.0 — policy-map ชนิด control subscriber — หลักการเดียวกัน)

**Host modes:** single-host (1 อุปกรณ์), **multi-domain** (data 1 + voice 1 — ใช้กับ phone+PC), multi-auth (หลายอุปกรณ์ยืนยันแยก), multi-host (ผ่านคนแรกแล้วเปิดให้ทุกคน — ไม่แนะนำ)

---

## 7. Rollout แบบค่อยเป็นค่อยไป (สำคัญที่สุดในงานจริง)

เปิด 802.1X แบบบังคับทันที = **ทุกอุปกรณ์ที่ลืมสำรวจใช้งานไม่ได้** (printer, กล้อง, อุปกรณ์การแพทย์, เครื่องรุ่นเก่า)

| Phase | การตั้งค่า | ผล |
|---|---|---|
| **1. Monitor mode** | `authentication open` + ไม่มีการบังคับ | ทุกคนใช้งานได้ตามปกติ แต่ **เก็บข้อมูล** ว่าใครผ่าน/ไม่ผ่าน และอุปกรณ์อะไรอยู่ที่ไหน → แก้ไข supplicant/cert/profiling |
| **2. Low-impact mode** | `authentication open` + **pre-auth ACL** (อนุญาตแค่ DHCP/DNS/AD/บริการพื้นฐาน) แล้วเพิ่มสิทธิ์เมื่อผ่าน | ผู้ไม่ผ่านใช้ได้จำกัด |
| **3. Closed mode** | ไม่มี `open` — ไม่ผ่านก็ไม่ได้อะไรเลย (นอกจาก EAPoL) | บังคับเต็มรูปแบบ |

**ขั้นตอนเพิ่มเติม:** สำรวจ asset, เตรียม PKI/auto-enrollment, ตั้ง supplicant ผ่าน GPO/MDM, นำร่องที่แผนก IT ก่อน, ขยายทีละอาคาร/ชั้น, มีขั้นตอนข้อยกเว้นและ helpdesk พร้อม, สร้าง policy สำหรับ **critical auth VLAN** (เมื่อ RADIUS ล่ม ให้ใช้งานได้จำกัดแทนที่จะล่มทั้งหมด)

---

## 8. NAC (Network Access Control) — มากกว่า 802.1X

ผลิตภัณฑ์ NAC (Cisco ISE, Aruba ClearPass, Fortinet FortiNAC, Forescout, Portnox) รวมความสามารถ:
| ความสามารถ | รายละเอียด |
|---|---|
| **Authentication** | 802.1X, MAB, web auth |
| **Profiling** | ระบุชนิดอุปกรณ์อัตโนมัติ (Windows laptop, iPhone, Axis camera, printer HP) |
| **Posture** | ตรวจสถานะเครื่อง (OS patch, AV/EDR, disk encryption) ก่อนให้สิทธิ์เต็ม |
| **Guest / BYOD** | portal ลงทะเบียน, sponsor อนุมัติ, onboarding cert ให้เครื่องส่วนตัว |
| **Policy** | VLAN/dACL/SGT ตาม ผู้ใช้ + อุปกรณ์ + สถานที่ + เวลา + posture |
| **Integration** | รับ/ส่งข้อมูลกับ firewall (User-ID), SIEM, EDR, MDM → **quarantine อัตโนมัติ** |
| Visibility | รู้ว่าอุปกรณ์ใดอยู่ที่ไหน (asset inventory) |

---

## 9. Zero Trust

### แนวคิด
โมเดลเดิม "**castle-and-moat**": ข้างนอกอันตราย ข้างในเชื่อถือ → ผู้โจมตีที่เข้ามาได้หนึ่งจุด เคลื่อนที่ภายในได้อิสระ
**Zero Trust**: **ไม่เชื่อใครโดยอัตโนมัติ ไม่ว่าอยู่ที่ไหน** — ตรวจทุกครั้ง ให้สิทธิ์น้อยที่สุด และสมมติว่าถูกเจาะแล้ว

### หลักการ (NIST SP 800-207 / Microsoft / CISA)
1. **Verify explicitly** — ตรวจ identity, อุปกรณ์, ตำแหน่ง, ความเสี่ยง ทุก request
2. **Least privilege access** — just-in-time, just-enough, ระดับแอปไม่ใช่ทั้งเครือข่าย
3. **Assume breach** — แบ่งส่วนเล็ก ๆ (micro-segmentation), เข้ารหัส, monitor ต่อเนื่อง เพื่อลดผลกระทบ

### องค์ประกอบตาม NIST 800-207
```
 Subject (ผู้ใช้+อุปกรณ์) ──► [PEP: Policy Enforcement Point] ──► Resource
                                  ▲ allow/deny
                          [PDP: Policy Decision Point]
                          = Policy Engine + Policy Administrator
                          ใช้ข้อมูลจาก: IdP, device posture/MDM/EDR, threat intel, SIEM, ข้อมูลกิจกรรม
```
**PEP ในงานจริง:** NGFW, ZTNA gateway/connector, switch (802.1X/SGT), proxy, API gateway

### CISA Zero Trust Maturity Model — 5 Pillars
**Identity · Devices · Networks · Applications & Workloads · Data** (+ ฐานรากร่วม: Visibility & Analytics, Automation & Orchestration, Governance) — แต่ละ pillar มีระดับ Traditional → Initial → Advanced → Optimal

### Zero Trust ในงาน Network
| ด้าน | มาตรการ |
|---|---|
| เข้าเครือข่าย | **802.1X/NAC** + posture |
| เข้าแอปจากระยะไกล | **ZTNA** แทน VPN แบบเปิดทั้งเครือข่าย (Level 59) |
| ภายในเครือข่าย | **segmentation → micro-segmentation** (Level 67), จำกัด east-west |
| Identity | SSO + **phishing-resistant MFA** + conditional access |
| Visibility | log ทุกอย่างเข้า SIEM, NDR, flow |
| Encryption | เข้ารหัสแม้ภายใน (TLS, MACsec, IPsec) |

> 🔑 **Zero Trust ไม่ใช่สินค้าชิ้นเดียว** — เป็นกลยุทธ์ที่ทำทีละขั้น (roadmap หลายปี) ข้ามหลายทีม

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| Switch ตัดสินว่าใครผ่าน 802.1X | switch เป็นแค่ authenticator; RADIUS server ตัดสิน |
| PEAP ปลอดภัยเท่า EAP-TLS | PEAP ใช้รหัสผ่าน และเสี่ยงถ้าไม่ตรวจ cert ของ server |
| MAB ยืนยันตัวตนได้จริง | MAC ปลอมได้ ต้องใช้ profiling + สิทธิ์จำกัด |
| เปิด 802.1X แบบ closed ได้ทันที | ต้องเริ่ม monitor mode แล้วค่อยเข้มขึ้น |
| ซื้อ ZTNA = ทำ Zero Trust แล้ว | Zero Trust ครอบคลุม identity, device, network, app, data |

---

## 11. Cheat Sheet

```
802.1X: Supplicant (เครื่อง) — Authenticator (switch/AP) — Auth server (RADIUS) · EAPoL ↔ RADIUS
EAP-TLS (cert ทั้งสองฝั่ง ⭐) · PEAP-MSCHAPv2 (รหัสผ่าน — ต้องตรวจ cert server) · TEAP
MAB = MAC เป็น username (อุปกรณ์ไม่มี supplicant) + profiling + สิทธิ์จำกัด
Authorization: dynamic VLAN · dACL · SGT/TrustSec · re-auth · CoA (เปลี่ยนสิทธิ์ทันที/quarantine)
Host mode: multi-domain (phone+PC) · multi-auth
Rollout: monitor (open) → low-impact (open + pre-auth ACL) → closed · critical auth VLAN
NAC: auth + profiling + posture + guest/BYOD + integration (SIEM/EDR/FW)
Zero Trust: verify explicitly · least privilege · assume breach · PEP/PDP (NIST 800-207)
CISA pillars: Identity · Devices · Networks · Applications/Workloads · Data
```

---

## 12. แบบทดสอบ 10 ข้อ

1. 802.1X มี 3 บทบาทอะไรบ้าง ใครเป็นผู้ตัดสินว่าผ่านหรือไม่
2. EAP-TLS ต่างจาก PEAP-MSCHAPv2 อย่างไร
3. ทำไม PEAP ต้องบังคับตรวจ certificate ของ RADIUS server
4. MAB ใช้กับอุปกรณ์แบบใด และมีจุดอ่อนอะไร
5. RADIUS ให้สิทธิ์ผู้ใช้หลังยืนยันตัวตนได้ด้วยวิธีใดบ้าง (3 วิธี)
6. CoA คืออะไร ยกตัวอย่างการใช้งาน
7. อธิบาย 3 phase ของการ rollout 802.1X
8. Host mode แบบใดเหมาะกับพอร์ตที่มี IP phone + PC
9. หลักการ 3 ข้อของ Zero Trust
10. PEP และ PDP คืออะไร ยกตัวอย่าง PEP ในเครือข่าย

<details><summary><b>เฉลย</b></summary>

1. Supplicant, Authenticator, Authentication server — authentication server (RADIUS) เป็นผู้ตัดสิน
2. EAP-TLS ใช้ certificate ทั้งสองฝั่ง (ไม่มีรหัสผ่าน); PEAP-MSCHAPv2 ใช้ username/password ภายใน TLS tunnel
3. ถ้าไม่ตรวจ ผู้โจมตีตั้ง AP/RADIUS ปลอมแล้วดัก credential (challenge/response hash) ไปถอดรหัสได้
4. อุปกรณ์ที่ไม่มี 802.1X supplicant (printer, กล้อง, IoT) — MAC ปลอมได้ง่าย ต้องใช้ profiling และสิทธิ์จำกัด
5. Dynamic VLAN, dACL, SGT (รวมถึง session timeout/re-auth)
6. ให้ RADIUS เปลี่ยนสิทธิ์ session ที่ใช้งานอยู่ได้ทันที เช่น EDR แจ้งว่าติดมัลแวร์ → ย้ายเครื่องไป quarantine VLAN
7. Monitor (ไม่บังคับ เก็บข้อมูล) → Low-impact (อนุญาตบริการพื้นฐานก่อนผ่าน) → Closed (บังคับเต็มรูปแบบ)
8. Multi-domain
9. Verify explicitly, Least privilege, Assume breach
10. PEP = จุดบังคับใช้ policy, PDP = จุดตัดสินใจ (policy engine/administrator) — PEP เช่น NGFW, ZTNA gateway, switch ที่ทำ 802.1X/SGT, proxy
</details>

---

➡️ ต่อไป: **Level 67 — Segmentation, DMZ & Secure Architecture**
