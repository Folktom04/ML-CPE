# บทเรียน Level 56 — AAA: RADIUS & TACACS+ (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจ Authentication / Authorization / Accounting · เลือกระหว่าง RADIUS และ TACACS+ ได้ถูกงาน · ตั้งค่า AAA บน Cisco พร้อม local fallback · กำหนดสิทธิ์ตามบทบาท (privilege/command authorization) · เชื่อมกับ Active Directory · ทำ audit trail ว่าใครแก้อะไร

---

## 1. AAA คืออะไร

| A | คำถาม | ตัวอย่าง |
|---|---|---|
| **Authentication** (ยืนยันตัวตน) | **คุณคือใคร?** | username/password, certificate, MFA |
| **Authorization** (กำหนดสิทธิ์) | **คุณทำอะไรได้บ้าง?** | helpdesk ใช้ได้แค่ `show`, network admin แก้ config ได้, ผู้ใช้ Wi-Fi ได้ VLAN 20 |
| **Accounting** (บันทึก) | **คุณทำอะไรไปแล้วบ้าง?** | login เมื่อไร, พิมพ์คำสั่งอะไร, ใช้ VPN นานเท่าไร ส่งข้อมูลเท่าไร |

### ทำไมไม่ใช้ local user ในทุกอุปกรณ์
- อุปกรณ์ 300 ตัว × พนักงาน 10 คน = ต้องสร้าง/ลบ/เปลี่ยนรหัสผ่าน 3,000 ครั้ง
- พนักงานลาออก → ต้องไล่ลบทุกเครื่อง (ลืมเครื่องเดียวก็เป็นช่องโหว่)
- ไม่มี log กลางว่าใครเข้าเครื่องไหนทำอะไร · ทำ MFA ยาก

**AAA server กลาง** → บัญชีเดียว (มักเชื่อมกับ **Active Directory**), ปิดบัญชีที่เดียวมีผลทุกอุปกรณ์, สิทธิ์ตามกลุ่ม, log ครบ, เพิ่ม MFA ได้

---

## 2. AAA ใช้กับ 2 งานหลัก

| งาน | ตัวอย่าง | โปรโตคอลที่นิยม |
|---|---|---|
| **Device Administration** — ผู้ดูแลเข้าจัดการอุปกรณ์ | SSH เข้า switch/router/firewall | **TACACS+** |
| **Network Access** — ผู้ใช้/อุปกรณ์เข้าใช้เครือข่าย | 802.1X (สาย/Wi-Fi), VPN, Wi-Fi Enterprise | **RADIUS** |

---

## 3. RADIUS vs TACACS+

| | **RADIUS** | **TACACS+** |
|---|---|---|
| มาตรฐาน | เปิด (RFC 2865/2866) | เดิมของ Cisco (ปัจจุบันมี RFC 8907) — รองรับหลายยี่ห้อ |
| Transport | **UDP 1812** (auth) / **1813** (accounting) (เดิม 1645/1646) | **TCP 49** |
| การเข้ารหัส | เข้ารหัสเฉพาะ **password** | เข้ารหัส **ทั้ง payload** |
| AuthN / AuthZ | **รวมกัน** ในคำตอบเดียว | **แยกกัน** (ใช้วิธียืนยันตัวตนหนึ่ง สิทธิ์อีกที่ได้) |
| **Command authorization** | ไม่รองรับละเอียด | ✅ **อนุญาต/ปฏิเสธทีละคำสั่ง** |
| Accounting | ดี (session, bytes) | ดี + **บันทึกทุกคำสั่งที่พิมพ์** |
| เหมาะกับ | **Network access** (802.1X, VPN, Wi-Fi) | **Device administration** |

**สรุปง่าย ๆ:** ผู้ใช้เข้าเครือข่าย → **RADIUS** · ผู้ดูแลเข้าอุปกรณ์ → **TACACS+**

### AAA Server ที่พบบ่อย
Cisco **ISE** (RADIUS + TACACS+ + NAC), Aruba **ClearPass**, Microsoft **NPS** (RADIUS, มากับ Windows Server), **FreeRADIUS** (open source), **tac_plus/tacacs+ (shrubbery/Pro-bono)**, Fortinet FortiAuthenticator, cloud RADIUS (JumpCloud, Okta RADIUS agent)

---

## 4. ตั้งค่า AAA บน Cisco (Device Administration ด้วย TACACS+)

```
aaa new-model                                         ! เปิดระบบ AAA (เปลี่ยนวิธี login ทันที — ระวัง!)
!
! 1) กำหนด server
tacacs server ISE-1
 address ipv4 10.0.0.71
 key T@cacsK3y!
tacacs server ISE-2
 address ipv4 10.0.0.72
 key T@cacsK3y!
aaa group server tacacs+ TAC-SERVERS
 server name ISE-1
 server name ISE-2
 ip tacacs source-interface Loopback0
!
! 2) Local fallback account (ใช้เมื่อ server ล่มทั้งหมดเท่านั้น)
username breakglass privilege 15 secret V3ry$tr0ngBr3akGl@ss
!
! 3) Authentication: ลอง TACACS ก่อน ถ้า server ไม่ตอบ → ใช้ local
aaa authentication login default group TAC-SERVERS local
aaa authentication enable default group TAC-SERVERS enable
!
! 4) Authorization: privilege level และ command authorization
aaa authorization exec default group TAC-SERVERS local if-authenticated
aaa authorization commands 1 default group TAC-SERVERS local if-authenticated
aaa authorization commands 15 default group TAC-SERVERS local if-authenticated
aaa authorization console                            ! (ถ้าต้องการให้ console ใช้ AAA ด้วย)
!
! 5) Accounting: บันทึกการ login และทุกคำสั่ง
aaa accounting exec default start-stop group TAC-SERVERS
aaa accounting commands 1 default start-stop group TAC-SERVERS
aaa accounting commands 15 default start-stop group TAC-SERVERS
!
line vty 0 15
 login authentication default
 transport input ssh
```

### ⚠️ ข้อควรระวังสำคัญ
- **`group ... local`** หมายถึง: ใช้ local **เฉพาะเมื่อ server ไม่ตอบ (unreachable)** — ถ้า server ตอบว่า "รหัสผิด" จะ **ไม่** ลอง local
- **ต้องมี local fallback account** ไม่เช่นนั้นถ้า AAA server/เครือข่ายไป server ล่ม → **ทุกคนเข้าอุปกรณ์ไม่ได้** (รวมตอนเกิดเหตุ ซึ่งเป็นเวลาที่ต้องเข้าที่สุด)
- **Break-glass account:** รหัสยาว เก็บใน vault/ซองปิดผนึก ใช้เมื่อฉุกเฉินเท่านั้น หมุนรหัสหลังใช้ และ **แจ้งเตือนทุกครั้งที่ถูกใช้**
- **ทดสอบใน session ใหม่ก่อนปิด session เดิม** (เปิด SSH อีกหน้าต่างหนึ่งไว้ ถ้า login ไม่ได้ยังแก้ได้) + `reload in 10`

### Privilege Levels ของ Cisco
- **Level 1** = user EXEC (`>`) · **Level 15** = privileged (`#`) ทำได้ทุกอย่าง · 2–14 กำหนดเองได้
- ใน TACACS+ server กำหนดว่ากลุ่ม AD ใดได้ privilege เท่าไร และอนุญาตคำสั่งใดบ้าง เช่น
  - **NOC/Helpdesk:** `show *`, `ping`, `traceroute`, `clear counters` — ห้าม `configure`
  - **Network Engineer:** ทุกคำสั่ง ยกเว้น `reload`, `erase`, `write erase` (ต้องขออนุมัติ)
  - **Network Admin:** ทั้งหมด

---

## 5. RADIUS สำหรับ Network Access (ภาพรวม)

```
 [ผู้ใช้/อุปกรณ์] ──EAP── [Switch/AP/VPN = NAS, RADIUS client] ──RADIUS (UDP 1812)── [RADIUS server] ── [AD/LDAP]
                                                                    ◄── Access-Accept + attributes
                                                                        (VLAN, dACL, role, session-timeout)
                                                                    ◄── หรือ Access-Reject
```
- **Messages:** Access-Request → **Access-Accept / Access-Reject / Access-Challenge** (สำหรับ MFA/EAP)
- **Attributes ที่ใช้ส่งสิทธิ์:** `Tunnel-Private-Group-ID` (VLAN), `Filter-Id`/dACL, `Class`, vendor-specific (VSA)
- **CoA (Change of Authorization, UDP 3799/1700)** — server สั่งเปลี่ยนสิทธิ์ session ที่กำลังใช้อยู่ได้ (เช่น ย้ายเครื่องที่ติดมัลแวร์ไป quarantine)
- **Shared secret** ระหว่าง NAS กับ server ต้องตรงกันและเดายาก
- รายละเอียด 802.1X/NAC อยู่ใน Level 66

```
! Cisco: RADIUS server สำหรับ 802.1X
radius server ISE-1
 address ipv4 10.0.0.71 auth-port 1812 acct-port 1813
 key R@diusK3y!
aaa group server radius RAD-SERVERS
 server name ISE-1
aaa authentication dot1x default group RAD-SERVERS
aaa authorization network default group RAD-SERVERS
aaa accounting dot1x default start-stop group RAD-SERVERS
```

---

## 6. เชื่อมกับ Active Directory และ MFA

- AAA server ตรวจรหัสผ่านกับ **AD/LDAP** และใช้ **กลุ่ม AD** (เช่น `NET-ADMINS`, `NOC`) กำหนดสิทธิ์
- **MFA สำหรับผู้ดูแลอุปกรณ์:** RADIUS/TACACS+ ร่วมกับ OTP/push (Duo, Microsoft Entra MFA ผ่าน NPS extension, FortiToken) — แนะนำอย่างยิ่งสำหรับ VPN และการเข้าอุปกรณ์สำคัญ
- **PAM (Privileged Access Management)** เช่น CyberArk, Delinea: jump host + session recording + หมุนรหัสอัตโนมัติ (SI-Track L89)

---

## 7. Accounting — Audit Trail

ตัวอย่างข้อมูลที่ได้จาก TACACS+ accounting
```
 2026-11-23 10:15:02 user=somchai device=BKK-CORE-01 priv=15 cmd="interface Vlan20"
 2026-11-23 10:15:09 user=somchai device=BKK-CORE-01 priv=15 cmd="shutdown"        ← เจอสาเหตุ outage
```
- ใช้สืบสวนเหตุการณ์ ("ใครแก้อะไรก่อนระบบล่ม"), ตรวจสอบตามมาตรฐาน (ISO 27001, PCI DSS), เทียบกับ change ticket
- ส่ง accounting/log เข้า SIEM แจ้งเตือนเมื่อมีการใช้ break-glass หรือคำสั่งอันตราย

---

## 8. แก้ปัญหา AAA

| อาการ | ตรวจ |
|---|---|
| ทุกคน login ไม่ได้ | AAA server ล่ม/เข้าไม่ถึง? (local fallback ทำงานไหม) · source interface/ACL/firewall TCP 49/UDP 1812 · shared key ไม่ตรง |
| บางคน login ไม่ได้ | บัญชี AD ถูกล็อก/หมดอายุ, ไม่อยู่ในกลุ่มที่อนุญาต, policy บน server |
| login ได้แต่ได้ `>` ไม่ได้ `#` | authorization exec/privilege level ที่ server ส่งมา |
| พิมพ์คำสั่งแล้ว "Command authorization failed" | command authorization บน server ไม่อนุญาตคำสั่งนั้น |
| 802.1X ไม่ผ่าน | ดู reason ใน RADIUS log (ISE live log/NPS event), cert, เวลา (NTP) |

```
test aaa group TAC-SERVERS user1 Passw0rd legacy        ! ทดสอบจากอุปกรณ์
show tacacs ; show aaa servers ; show aaa sessions
debug aaa authentication / debug tacacs                 ! (lab/ช่วง maintenance)
```

---

## 9. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| `group TACACS local` = ถ้ารหัสผิดจะลอง local | ลอง local เฉพาะเมื่อ server **ไม่ตอบ** |
| RADIUS เข้ารหัสทั้ง packet | เข้ารหัสเฉพาะ password (TACACS+ เข้ารหัสทั้งหมด) |
| ใช้ AAA แล้วไม่ต้องมี local account | ต้องมี break-glass account เสมอ |
| TACACS+ ใช้กับ 802.1X | 802.1X ใช้ RADIUS |
| เปิด `aaa new-model` ได้โดยไม่มีผลทันที | เปลี่ยนวิธี login ทันที อาจตัดตัวเองออก |

---

## 10. Cheat Sheet

```
AAA = Authentication (ใคร) · Authorization (ทำอะไรได้) · Accounting (ทำอะไรไป)
RADIUS: UDP 1812/1813 · เข้ารหัสแค่ password · AuthN+AuthZ รวม · network access (802.1X, VPN, Wi-Fi)
TACACS+: TCP 49 · เข้ารหัสทั้งหมด · AuthN/AuthZ แยก · command authorization · device admin
aaa new-model → server/group → aaa authentication login default group X local
aaa authorization exec / commands 15 · aaa accounting commands 15 start-stop
local fallback = ใช้เมื่อ server ไม่ตอบเท่านั้น · break-glass account + แจ้งเตือน
ทดสอบใน session ใหม่ + reload in 10 · test aaa group
RADIUS: Access-Accept + attributes (VLAN/dACL) · CoA เปลี่ยนสิทธิ์ทันที
เชื่อม AD (กลุ่ม = สิทธิ์) · เพิ่ม MFA · accounting → SIEM
```

---

## 11. แบบทดสอบ 10 ข้อ

1. AAA ย่อมาจากอะไร แต่ละตัวตอบคำถามอะไร
2. ทำไมองค์กรควรใช้ AAA server แทน local user ในทุกอุปกรณ์ (3 เหตุผล)
3. RADIUS กับ TACACS+ ต่างกันอย่างไร (4 ข้อ)
4. ควรใช้โปรโตคอลใดสำหรับผู้ดูแลเข้าจัดการ switch และสำหรับ 802.1X
5. `aaa authentication login default group TAC-SERVERS local` ทำงานอย่างไร
6. ทำไมต้องมี break-glass account และควรจัดการอย่างไร
7. ข้อควรระวังเมื่อเปิด `aaa new-model` ผ่าน SSH
8. ยกตัวอย่างการกำหนดสิทธิ์คำสั่งสำหรับทีม NOC
9. RADIUS ส่ง VLAN ให้ผู้ใช้ได้อย่างไร และ CoA ใช้ทำอะไร
10. Accounting ของ TACACS+ มีประโยชน์อย่างไร

<details><summary><b>เฉลย</b></summary>

1. Authentication (คุณคือใคร), Authorization (ทำอะไรได้บ้าง), Accounting (ทำอะไรไปแล้วบ้าง)
2. จัดการบัญชีที่เดียว (ปิดบัญชีคนลาออกครั้งเดียว), กำหนดสิทธิ์ตามกลุ่ม, มี log กลาง และเพิ่ม MFA ได้
3. RADIUS UDP / TACACS+ TCP 49; RADIUS เข้ารหัสแค่ password / TACACS+ ทั้ง payload; RADIUS รวม AuthN+AuthZ / TACACS+ แยก; TACACS+ ทำ command authorization ได้
4. TACACS+ สำหรับ device administration; RADIUS สำหรับ 802.1X
5. ยืนยันตัวตนกับกลุ่ม TACACS+ ก่อน ถ้า server ไม่ตอบ (unreachable) จึงใช้ local user
6. เพื่อเข้าอุปกรณ์ได้เมื่อ AAA server หรือเครือข่ายไป server ล่ม — รหัสยาว เก็บใน vault/ซองปิดผนึก ใช้เฉพาะฉุกเฉิน แจ้งเตือนเมื่อใช้ และหมุนรหัสหลังใช้
7. วิธี login เปลี่ยนทันที อาจตัดตัวเองออก — เปิด session สำรองไว้, ตั้ง local fallback ก่อน, ทดสอบ login ใน session ใหม่, ใช้ `reload in`
8. อนุญาตเฉพาะ `show`, `ping`, `traceroute`, `clear counters` และห้าม `configure`, `reload`
9. ส่ง attribute เช่น Tunnel-Private-Group-ID ใน Access-Accept; CoA ให้ server เปลี่ยนสิทธิ์ session ที่ใช้งานอยู่ได้ทันที (เช่น ย้ายไป quarantine)
10. บันทึกว่าใคร login อุปกรณ์ใด พิมพ์คำสั่งอะไรเมื่อไร — ใช้สืบสวนเหตุการณ์ ตรวจสอบ compliance และเทียบกับ change
</details>

---

➡️ ต่อไป: **Level 57 — WAN Technologies**
