# บทเรียน Level 67 — Segmentation, DMZ & Secure Architecture (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจว่าทำไมต้องแบ่งส่วนเครือข่าย · ออกแบบ zone model และ policy matrix · ออกแบบ DMZ (single/dual firewall) · ทำ management network/OOB, jump host, PAM · micro-segmentation · แยก OT/ICS ตาม Purdue model/IEC 62443 · ใช้ VRF แยก routing domain

---

## 1. ทำไมต้อง Segmentation

**Flat network** (ทุกเครื่องคุยกันได้หมด) → เครื่องเดียวที่ติดมัลแวร์ **ลามไปทั้งองค์กร** (lateral movement) ซึ่งเป็นรูปแบบของ ransomware เกือบทุกเหตุการณ์

**Segmentation** = แบ่งเครือข่ายเป็นส่วน (zone/segment) แล้ว **ควบคุมการสื่อสารระหว่างส่วน** ด้วย policy
| ประโยชน์ | อธิบาย |
|---|---|
| **จำกัดความเสียหาย (blast radius)** | เครื่องที่ถูกยึดเข้าถึงได้แค่ใน segment ของมัน |
| **ป้องกันทรัพย์สินสำคัญ** | AD, database, backup, OT แยกไว้หลัง policy เข้มงวด |
| **Compliance** | PCI DSS กำหนดให้แยก cardholder data environment (CDE) ลดขอบเขตการตรวจ |
| **Visibility** | traffic ข้าม zone ผ่านจุดที่ log/ตรวจได้ |
| **ประสิทธิภาพ** | ลด broadcast, จำกัดปัญหา |

---

## 2. ระดับของ Segmentation

| ระดับ | วิธี | ความละเอียด |
|---|---|---|
| **Macro-segmentation** | VLAN/subnet + **firewall ระหว่าง zone**, **VRF** | ระดับ zone (Users, Servers, DMZ, OT) |
| **Micro-segmentation** | policy ต่อ **workload/แอป/อุปกรณ์** (แม้อยู่ VLAN เดียวกัน) — host firewall, NSX DFW, Illumio, Cilium, SGT, cloud security group | ระดับเครื่อง/แอป |

**แนวทาง:** เริ่มจาก macro (ได้ผลเร็ว) แล้วค่อยทำ micro สำหรับทรัพย์สินสำคัญ (ringfence)

---

## 3. Zone Model และ Policy Matrix

### Zone ที่พบบ่อยในองค์กร
| Zone | ตัวอย่าง | ความเชื่อถือ |
|---|---|---|
| **Internet** | ภายนอก | ต่ำสุด |
| **DMZ** | web server สาธารณะ, reverse proxy, mail gateway, VPN | ต่ำ |
| **Guest** | Wi-Fi ผู้มาติดต่อ | ต่ำ |
| **IoT / CCTV / Building** | กล้อง, ระบบอาคาร, อุปกรณ์ IoT | ต่ำ |
| **Users** | เครื่องพนักงาน | ปานกลาง |
| **Servers (App)** | application server | ปานกลาง–สูง |
| **Database / Restricted** | ฐานข้อมูล, ข้อมูลอ่อนไหว (PCI/HIS) | สูง |
| **Identity (Tier 0)** | Domain Controller, PKI, IdP | สูงสุด |
| **Management** | interface จัดการอุปกรณ์, iDRAC/iLO, hypervisor management | สูงสุด |
| **Backup** | backup server/repository | สูงสุด |
| **OT/ICS** | ระบบควบคุมการผลิต | แยกเฉพาะ |

### Policy Matrix (ตัวอย่าง — ใครเริ่มเชื่อมต่อไปหาใครได้)
| จาก \ ไป | Internet | DMZ | Users | Servers | DB | Mgmt | Backup |
|---|---|---|---|---|---|---|---|
| **Internet** | — | 443 เฉพาะ web | ❌ | ❌ | ❌ | ❌ | ❌ |
| **DMZ** | จำกัด (update) | — | ❌ | port ที่ app ต้องใช้ | ❌ | ❌ | ❌ |
| **Users** | ✅ ผ่าน web filter | 443 | ❌ (ยกเว้นที่จำเป็น) | port ของแอป | ❌ | ❌ | ❌ |
| **Servers** | จำกัด | — | — | ตามที่ต้องการ | port DB | ❌ | agent |
| **Mgmt (jump host)** | update | SSH/HTTPS | RDP (helpdesk) | SSH/RDP | ✅ | — | ✅ |
| **Guest** | ✅ เท่านั้น | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

**หลัก:** **default deny** ระหว่าง zone · อนุญาตเฉพาะที่ระบุ (ต้นทาง/ปลายทาง/แอป/port) · log ทุก rule

### Quick wins ที่ลด ransomware ได้มาก
- **บล็อก SMB (445), RDP (3389), WinRM (5985/5986), RPC (135) ระหว่างเครื่องผู้ใช้ด้วยกัน** (workstation-to-workstation) — ผู้ใช้แทบไม่ต้องใช้ แต่มัลแวร์ใช้ลาม
- อนุญาต RDP/SSH ไปยัง server **จาก jump host เท่านั้น**
- แยก **backup network** และ management network ออกจากทุกอย่าง

---

## 4. DMZ (Demilitarized Zone)

**DMZ** = zone สำหรับ **server ที่ต้องให้บริการภายนอก** — ถ้าถูกเจาะ ผู้โจมตีไม่ได้อยู่ในเครือข่ายภายในทันที

### Single firewall (three-legged)
```
 Internet ──[ FW ]── Internal
              │
            [DMZ]
```
ง่าย ประหยัด (firewall เดียวมี 3 zone) — นิยมในองค์กรทั่วไป

### Dual firewall (back-to-back)
```
 Internet ──[ FW ภายนอก ]── [ DMZ ] ──[ FW ภายใน ]── Internal
             (มักต่างยี่ห้อ — defense in depth)
```
ปลอดภัยกว่า (ต้องเจาะ 2 ชั้น) แต่แพงและซับซ้อน — ใช้ในองค์กรความเสี่ยงสูง (การเงิน/รัฐ)

### แนวปฏิบัติของ DMZ
- **ห้าม DMZ เริ่มการเชื่อมต่อเข้าภายใน** (ยกเว้นที่จำเป็นจริง เช่น web → app port เดียว) — ถ้าทำได้ให้ภายในเป็นฝ่ายดึงข้อมูล
- **ไม่เก็บข้อมูลอ่อนไหวไว้ใน DMZ** — ใช้ 3-tier (web ใน DMZ → app ใน server zone → DB ใน restricted zone)
- ใช้ **reverse proxy/WAF** หน้า web server
- server ใน DMZ **ไม่ควร join domain ภายใน** (หรือใช้ domain แยก)
- **Hardening** เข้มงวด, patch เร็ว, monitor ละเอียด
- ใช้ **Private VLAN/micro-segmentation** ไม่ให้ server ใน DMZ คุยกันเอง

---

## 5. Management Network และการเข้าถึงสิทธิ์สูง

**Management plane** (SSH/HTTPS ของอุปกรณ์, vCenter, iDRAC/iLO, storage, hypervisor) = **กุญแจของทั้งระบบ** ผู้โจมตีที่ได้สิทธิ์นี้ควบคุมได้ทุกอย่าง (เช่น เข้ารหัส VM ทั้ง cluster)

### แยก Management
- **Management VLAN/VRF แยก** ไม่ให้ user/server zone เข้าถึง interface จัดการ
- **OOB (Out-of-Band) network** — เครือข่ายจัดการแยกทางกายภาพ (switch แยก, console server) ยังเข้าถึงได้แม้ production ล่ม
- อุปกรณ์จัดการผ่าน **ACL ที่ VTY/management interface** อนุญาตเฉพาะ jump host/NMS

### Jump Host / Bastion
```
 ผู้ดูแล ──(VPN/ZTNA + MFA)──► [Jump host / Bastion / PAM] ──► อุปกรณ์/server ใน management zone
                                  บันทึก session, ควบคุมสิทธิ์
```
- จุดเข้าเดียวที่ควบคุมและ **บันทึก** ได้ (Apache Guacamole, Windows jump server ที่ hardening, Teleport)
- **PAM (Privileged Access Management)** — CyberArk, Delinea, BeyondTrust: เก็บรหัส admin ใน vault, หมุนรหัสอัตโนมัติ, **just-in-time access**, session recording

### AD Tiering Model (สำหรับ Windows)
Tier 0 (DC/AD/PKI) · Tier 1 (server) · Tier 2 (workstation) — **บัญชี admin ของ tier สูงห้าม login เครื่อง tier ต่ำ** (ป้องกันการขโมย credential จากเครื่องผู้ใช้)

---

## 6. Micro-Segmentation

ควบคุมการสื่อสาร **ระหว่าง workload แต่ละตัว** — แม้อยู่ VLAN/subnet เดียวกัน
| วิธี | ตัวอย่าง |
|---|---|
| Hypervisor-based | VMware NSX Distributed Firewall, Nutanix Flow |
| Host/agent-based | Illumio, Akamai Guardicore, Windows Firewall ผ่าน GPO |
| Network-based (tag) | Cisco TrustSec/SGT, Aruba dynamic segmentation |
| Cloud | AWS Security Group, Azure NSG/ASG |
| Container | Kubernetes NetworkPolicy, Cilium |

**ขั้นตอน:** **visibility ก่อน** (application dependency mapping จาก flow) → กำหนด label (env/app/role) → policy แบบ test/monitor → enforce ทีละแอป → monitor
(รายละเอียดเชิงปฏิบัติใน SI-Track L49 / ISC L51)

---

## 7. VRF — แยก Routing Domain

**VRF (Virtual Routing and Forwarding)** = **routing table หลายชุดในอุปกรณ์เดียว** — เหมือนแบ่ง router เป็นหลายตัว
```
 Core switch:
   VRF CORP  : 10.1.0.0/16 (users, servers)  ── route ผ่าน firewall เท่านั้นเมื่อข้าม VRF
   VRF GUEST : 10.50.0.0/16                  ── default route ไป firewall/internet เท่านั้น
   VRF MGMT  : 10.99.0.0/16                  ── management
   VRF OT    : 10.200.0.0/16
```
- VRF ต่างกัน **คุยกันไม่ได้ (ไม่มี route ถึงกัน)** จนกว่าจะส่งผ่านจุดที่ควบคุม (firewall) หรือทำ route leaking อย่างตั้งใจ
- IP ซ้ำกันใน VRF ต่างกันได้
- ใช้กับ: Guest/IoT/OT แยกบน core เดียวกัน, **management VRF** บนอุปกรณ์เครือข่าย, MPLS L3VPN (Level 97), multi-tenant DC

```
vrf definition GUEST
 address-family ipv4
interface Vlan50
 vrf forwarding GUEST
 ip address 10.50.0.1 255.255.0.0
ip route vrf GUEST 0.0.0.0 0.0.0.0 10.255.50.1     ! ออกได้แค่ firewall
show ip route vrf GUEST
```

---

## 8. OT/ICS Segmentation

ระบบควบคุมอุตสาหกรรม (โรงงาน, โรงไฟฟ้า, ระบบน้ำ, ระบบอาคาร, อุปกรณ์การแพทย์บางชนิด) มีลักษณะพิเศษ: **availability สำคัญที่สุด**, อุปกรณ์อายุยาว patch ยาก, โปรโตคอลไม่มีความปลอดภัย (Modbus, S7, DNP3)

### Purdue Model (โครงสร้างอ้างอิง)
```
 Level 5  Enterprise network / Internet
 Level 4  Business/ERP
 ─────────── IT/OT DMZ (Level 3.5) ─────────── ← ทุกอย่างระหว่าง IT กับ OT ต้องผ่านที่นี่ (historian replica, patch server, jump host)
 Level 3  Site operations (historian, MES)
 Level 2  Supervisory control (SCADA, HMI)
 Level 1  Basic control (PLC, RTU)
 Level 0  Physical process (sensor, actuator)
```
**แนวปฏิบัติ:** ห้าม IT เชื่อมต่อตรงไป OT, ใช้ **IT/OT DMZ**, firewall ที่รู้จักโปรโตคอลอุตสาหกรรม, remote access ของ vendor ผ่าน jump host ที่ควบคุมเวลาและบันทึก, monitoring แบบ **passive** (Nozomi, Claroty, Dragos), มาตรฐาน **IEC 62443** (zones & conduits)

---

## 9. ออกแบบ Secure Architecture (สรุปเป็นขั้นตอน)

```
 1) Inventory: รู้ว่ามี asset/แอปอะไร คุยกับใคร (flow data)
 2) จัดกลุ่มตาม function + ความสำคัญ + compliance → zone
 3) วาง policy matrix (default deny) + ทำ quick wins (บล็อก SMB/RDP ระหว่าง workstation)
 4) เลือก enforcement point: firewall ระหว่าง zone, VRF, ACL, micro-segmentation
 5) แยก management/backup/identity ให้เข้มที่สุด + jump host + PAM + MFA
 6) Logging ทุก boundary → SIEM
 7) ทดสอบ (nmap จากแต่ละ zone ตาม policy matrix) และทบทวนเป็นระยะ
```

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| แบ่ง VLAN แล้วถือว่าแยกกันแล้ว | ถ้า routing ข้าม VLAN ได้อิสระก็ยังไม่ได้แยก ต้องมี policy |
| DMZ ปลอดภัยเพราะอยู่หลัง firewall | DMZ เป็น zone ความเชื่อถือต่ำ ต้องจำกัดการเชื่อมต่อเข้าภายใน |
| Management interface อยู่ใน user VLAN ได้ | ต้องแยก management + เข้าผ่าน jump host |
| Micro-segmentation ทำได้ทันทีด้วยการเขียน rule | ต้องมี visibility/dependency mapping ก่อน ไม่เช่นนั้นแอปพัง |
| OT ทำ security แบบเดียวกับ IT | OT ต้องการ availability สูงสุด ห้ามสแกน/patch แบบ IT |

---

## 11. Cheat Sheet

```
Flat network → lateral movement · Segmentation จำกัด blast radius
Macro (VLAN/VRF/firewall ระหว่าง zone) → Micro (ต่อ workload: NSX, Illumio, SGT, SG, K8s policy)
Zones: Internet · DMZ · Guest · IoT · Users · Servers · DB · Identity (Tier 0) · Mgmt · Backup · OT
Policy matrix: default deny · อนุญาตเฉพาะ · log
Quick win: block SMB/RDP/WinRM ระหว่าง workstation · admin ผ่าน jump host
DMZ: single (3 ขา) / dual firewall · DMZ ห้ามเริ่มเข้าภายใน · ไม่เก็บข้อมูลสำคัญ · WAF/reverse proxy
Management: VLAN/VRF แยก · OOB · jump host · PAM (vault, JIT, session recording) · AD tiering
VRF = routing table หลายชุด แยก domain · ข้ามได้ผ่าน firewall/route leaking
OT: Purdue model · IT/OT DMZ (L3.5) · IEC 62443 · passive monitoring
```

---

## 12. แบบทดสอบ 10 ข้อ

1. ทำไม flat network จึงเสี่ยงต่อ ransomware
2. Macro-segmentation กับ micro-segmentation ต่างกันอย่างไร
3. ยกตัวอย่าง zone ในองค์กรอย่างน้อย 6 zone
4. Quick win ด้าน segmentation ที่ลด ransomware ได้มาก
5. Single firewall DMZ กับ dual firewall DMZ ต่างกันอย่างไร
6. แนวปฏิบัติสำหรับ server ใน DMZ (4 ข้อ)
7. Jump host และ PAM ช่วยอะไร
8. VRF คืออะไร ใช้แยก Guest บน core switch เดียวกันได้อย่างไร
9. Purdue model คืออะไร และ IT/OT DMZ อยู่ระดับใด
10. ขั้นตอนแรกของการทำ micro-segmentation คืออะไร เพราะอะไร

<details><summary><b>เฉลย</b></summary>

1. ทุกเครื่องคุยกันได้หมด มัลแวร์จากเครื่องเดียวลาม (lateral movement) ไปทั้งองค์กรได้
2. Macro แบ่งระดับ zone (VLAN/VRF/firewall ระหว่าง zone); micro ควบคุมระดับ workload/แอปแม้อยู่ในวงเดียวกัน
3. Internet, DMZ, Guest, IoT/CCTV, Users, Servers, Database, Identity, Management, Backup, OT
4. บล็อก SMB/RDP/WinRM/RPC ระหว่างเครื่องผู้ใช้ด้วยกัน และอนุญาต RDP/SSH ไป server เฉพาะจาก jump host
5. Single ใช้ firewall ตัวเดียว 3 zone (ง่าย ประหยัด); dual วาง DMZ ระหว่าง firewall 2 ตัว (มักต่างยี่ห้อ ปลอดภัยกว่าแต่แพง)
6. ห้ามเริ่มเชื่อมต่อเข้าภายในโดยไม่จำเป็น, ไม่เก็บข้อมูลอ่อนไหว (ใช้ 3-tier), ใช้ WAF/reverse proxy, ไม่ join domain ภายใน, hardening/patch/monitor, แยก server ใน DMZ จากกัน
7. เป็นจุดเข้าจัดการระบบจุดเดียวที่ควบคุม/บันทึกได้; PAM เก็บรหัส admin ใน vault หมุนรหัส ให้สิทธิ์ชั่วคราว และบันทึก session
8. Routing table หลายชุดในอุปกรณ์เดียว — ใส่ SVI ของ Guest ใน VRF GUEST ที่มีแค่ default route ไป firewall จึงไม่มีทางไปเครือข่ายภายใน
9. โครงสร้างอ้างอิงแบ่งระบบ IT/OT เป็นระดับ 0–5 — IT/OT DMZ อยู่ระดับ 3.5
10. ทำ visibility/application dependency mapping — ต้องรู้ว่าแอปคุยกับอะไรก่อนเขียน policy ไม่เช่นนั้นจะบล็อก traffic ที่จำเป็นจนแอปพัง
</details>

---

➡️ ต่อไป: **Level 68 — Logging, SIEM & Visibility**
