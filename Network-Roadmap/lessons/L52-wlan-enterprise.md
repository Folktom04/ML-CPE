# บทเรียน Level 52 — WLAN องค์กร: Controller, Design & Security (ฉบับละเอียด)

> อ่านจบแล้วจะ: เลือกสถาปัตยกรรม (Autonomous / Controller / Cloud) · เข้าใจ CAPWAP, local mode vs FlexConnect · เลือก security (WPA2/WPA3-Personal/Enterprise, OWE) · ออกแบบ SSID และ Guest · ทำ site survey และวางแผน capacity · ใช้ RRM, band steering ได้เหมาะสม

---

## 1. สถาปัตยกรรม WLAN

| แบบ | ลักษณะ | ข้อดี | ข้อเสีย | เหมาะกับ |
|---|---|---|---|---|
| **Autonomous (standalone)** | AP แต่ละตัวตั้งค่าแยก | ถูก ง่ายเมื่อมีไม่กี่ตัว | จัดการทีละตัว roam ไม่ดี | ร้านเล็ก/สาขาเล็ก |
| **Controller-based** | **WLC (Wireless LAN Controller)** จัดการ AP ทั้งหมด (on-prem) | ศูนย์กลาง, RRM, roaming ดี, policy เดียว | ต้องดูแล controller (ควรมีคู่ HA) | องค์กรขนาดกลาง–ใหญ่, campus |
| **Cloud-managed** | จัดการผ่าน cloud dashboard | ติดตั้งง่าย, หลายสาขา, อัปเดตอัตโนมัติ | ค่า license รายปี, พึ่งอินเทอร์เน็ตในการจัดการ | หลายสาขา, ทีม IT เล็ก |
| (Controller บน firewall) | เช่น FortiGate คุม FortiAP | รวม security + Wi-Fi | ฟีเจอร์ wireless ขั้นสูงน้อยกว่า | SMB/สาขา |

ผู้ผลิตที่พบบ่อย: Cisco (Catalyst 9800, Meraki), HPE Aruba (Controller/Central), Juniper Mist, Extreme (ExtremeCloud IQ), Alcatel-Lucent (OmniAccess Stellar), Fortinet (FortiAP), Ubiquiti, Ruckus

---

## 2. Controller-based: CAPWAP และโหมดของ AP

**CAPWAP (Control And Provisioning of Wireless Access Points)** — tunnel ระหว่าง AP กับ WLC
- **UDP 5246** = control (เข้ารหัส DTLS) · **UDP 5247** = data
- AP หา WLC ได้จาก: DHCP **Option 43**, DNS (`CISCO-CAPWAP-CONTROLLER.<domain>`), broadcast ในวงเดียวกัน, ตั้งค่าตรง

### Local Mode vs FlexConnect

| | **Local (Central switching)** | **FlexConnect (Local switching)** |
|---|---|---|
| ข้อมูลผู้ใช้ | ส่งผ่าน CAPWAP **ไปที่ WLC** แล้วจึงออกเครือข่าย | **ออกที่ switch ของ AP โดยตรง** (VLAN ที่สาขา) |
| ใช้ที่ | Campus/HQ ที่ WLC อยู่ใกล้ | **สาขา** ที่ WLC อยู่ HQ (ไม่ต้องส่ง traffic ข้าม WAN) |
| ถ้า WAN ไป WLC ขาด | ใช้งานไม่ได้ | ผู้ใช้ที่เชื่อมอยู่ยังใช้ได้ (standalone mode) |

### High Availability ของ WLC
WLC เป็นศูนย์กลาง ถ้าล่ม AP ทั้งหมดหยุด → ใช้ **SSO (Stateful Switchover) คู่ active/standby** หรือ N+1 และตั้ง primary/secondary controller ใน AP

---

## 3. Wireless Security

| Security | การยืนยันตัวตน | ใช้เมื่อ | หมายเหตุ |
|---|---|---|---|
| Open | ไม่มี | ❌ ไม่ควรใช้ | ใครก็ดักอ่านได้ |
| WEP / WPA (TKIP) | — | ❌ **ห้ามใช้** | ถูกเจาะได้ง่าย |
| **WPA2-Personal (PSK)** | รหัสผ่านเดียว | บ้าน, อุปกรณ์ IoT ที่จำเป็น | รหัสรั่ว/คนลาออก ต้องเปลี่ยนทุกเครื่อง · โดน offline dictionary attack ได้ถ้ารหัสอ่อน |
| **WPA3-Personal (SAE)** | รหัสผ่าน (SAE handshake) | แทน WPA2-PSK | ป้องกัน offline dictionary attack, มี forward secrecy |
| **WPA2/WPA3-Enterprise (802.1X)** ⭐ | **บัญชีผู้ใช้/certificate ผ่าน RADIUS** | **พนักงานองค์กร** | แต่ละคนมีตัวตนของตัวเอง, ยกเลิกรายบุคคลได้, ได้ VLAN/policy ตามกลุ่ม |
| **OWE (Enhanced Open / Wi-Fi Certified Enhanced Open)** | ไม่ต้องใช้รหัส แต่ **เข้ารหัส** | Guest/สาธารณะ | ป้องกันการดักฟังแม้ไม่มีรหัสผ่าน |
| **iPSK / MPSK / DPSK** | PSK หลายตัวบน SSID เดียว (แต่ละอุปกรณ์/กลุ่มได้รหัสต่างกัน) | IoT ที่ไม่รองรับ 802.1X | ได้ VLAN ต่างกันตามรหัส |

### 802.1X บน Wi-Fi (ภาพรวม — รายละเอียด Level 66)
```
 [Laptop] ──EAP over Wi-Fi──► [AP/WLC] ──RADIUS──► [RADIUS: ISE/ClearPass/NPS/FreeRADIUS] ──► AD
 supplicant                    authenticator          authentication server
 → ผ่าน: ได้กุญแจเข้ารหัสเฉพาะตัว + VLAN/role ตามกลุ่มผู้ใช้
```
- **EAP-TLS** (certificate ทั้งสองฝั่ง) ปลอดภัยที่สุด · **PEAP-MSCHAPv2** (username/password) ต้องบังคับตรวจ cert ของ server ไม่เช่นนั้นถูกหลอกด้วย AP ปลอมได้

### WPA3 Transition Mode
รองรับทั้ง WPA2 และ WPA3 บน SSID เดียวในช่วงเปลี่ยนผ่าน (บางอุปกรณ์เก่ามีปัญหา ต้องทดสอบ)

---

## 4. ออกแบบ SSID

**หลักการ: SSID ให้น้อยที่สุด (≤ 3–4 ต่อ radio)** — แต่ละ SSID ส่ง beacon ทุก ~100 ms ด้วย data rate ต่ำ กิน airtime ทุก AP

| SSID | Security | VLAN/Policy |
|---|---|---|
| **CORP** | WPA3/WPA2-Enterprise (802.1X) | dynamic VLAN ตามกลุ่ม (พนักงาน/IT/ผู้บริหาร) |
| **GUEST** | Captive portal / OWE / PSK ที่เปลี่ยนเป็นระยะ | VLAN Guest → ออกได้เฉพาะอินเทอร์เน็ต, client isolation, จำกัด bandwidth |
| **IOT** | iPSK/MPSK หรือ PSK + MAC auth | VLAN IoT จำกัดการเข้าถึงเข้มงวด |
| (ไม่ควรมี SSID แยกต่อแผนก — ใช้ 802.1X + dynamic VLAN แทน) | | |

**Hidden SSID ไม่ใช่ความปลอดภัย** — ชื่อยังถูกเปิดเผยใน probe และทำให้ client ส่ง probe หาเครือข่ายตลอดเวลา

### Guest Wi-Fi Best Practice
- แยก VLAN และให้ gateway อยู่ที่ firewall (ออกได้แค่อินเทอร์เน็ต ห้ามเข้าภายใน)
- **Client isolation** — guest คุยกันเองไม่ได้
- Captive portal (ยอมรับเงื่อนไข/ลงทะเบียน/voucher/SMS OTP) + เก็บ log ตาม พ.ร.บ.คอมพิวเตอร์ฯ
- Rate limit ต่อผู้ใช้, lease DHCP สั้น
- DNS filtering บล็อกเว็บอันตราย

---

## 5. Radio Resource Management (RRM)

Controller/cloud ปรับ **channel และ TX power อัตโนมัติ** ตามสภาพแวดล้อม (Cisco RRM, Aruba ARM/AirMatch, Mist AI)
- **DCA (Dynamic Channel Assignment)** — เลือก channel ให้ AP ข้างเคียงไม่ชนกัน
- **TPC (Transmit Power Control)** — ปรับกำลังส่งให้พอดี
- **Coverage hole detection** — แจ้งจุดที่สัญญาณไม่ถึง

**ฟีเจอร์อื่น**
- **Band steering** — ชักจูง client ที่รองรับ 5/6 GHz ไม่ให้ใช้ 2.4 GHz
- **Airtime fairness** — แบ่งเวลาออกอากาศอย่างเป็นธรรม ไม่ให้ client ช้าถ่วงทุกคน
- **Minimum data rate** — ปิด data rate ต่ำ (เช่น ต่ำกว่า 12 หรือ 24 Mbps)
- **802.11k/v/r** — ช่วย roaming
- **WIPS/Rogue detection** — ตรวจ AP แปลกปลอม/AP ปลอมที่ใช้ SSID เรา

---

## 6. Site Survey และการออกแบบ

### ออกแบบตาม Coverage หรือ Capacity?
- **Coverage-based:** ให้สัญญาณถึงทุกจุด (โกดัง, ทางเดิน) — AP น้อย
- **Capacity-based:** ให้รองรับจำนวนผู้ใช้และ throughput ที่ต้องการ (ห้องประชุม, ห้องเรียน, หอประชุม, โรงพยาบาล) — AP มากขึ้น ลด power ลง ใช้ช่องแคบ
→ **องค์กรปัจจุบันส่วนใหญ่ต้องออกแบบตาม capacity**

### ขั้นตอน Site Survey

| ขั้น | ทำอะไร |
|---|---|
| **1. Requirements** | จำนวนผู้ใช้/อุปกรณ์ต่อพื้นที่, แอป (voice/video/data), พื้นที่ที่ต้องครอบคลุม, RSSI/SNR เป้าหมาย, อุปกรณ์ client ที่ใช้ |
| **2. Predictive survey** | ใช้ซอฟต์แวร์ (Ekahau, Hamina, iBwave) กับแบบแปลนอาคาร กำหนดวัสดุผนัง → คำนวณจำนวนและตำแหน่ง AP |
| **3. Pre-deployment (AP-on-a-stick)** | (พื้นที่สำคัญ/ซับซ้อน) ติด AP ชั่วคราวแล้ววัดจริง ยืนยันการลดทอนของวัสดุ |
| **4. ติดตั้ง** | ตามแบบ (ตำแหน่ง, ความสูง, ทิศทางเสาอากาศ) |
| **5. Post-deployment validation survey** | เดินวัดจริงทั่วพื้นที่ ยืนยันว่าผ่านเกณฑ์ (RSSI, SNR, channel overlap, roaming) แล้วปรับแก้ — ใช้เป็นเอกสารส่งมอบ |

### Capacity Planning (ตัวอย่าง)
```
 ห้องประชุม 200 คน × 1.5 อุปกรณ์ × ใช้งานพร้อมกัน 70% ≈ 210 active clients
 สมมติ 1 radio รองรับ ~35–50 active clients อย่างมีคุณภาพ
 AP dual-radio (ใช้ 5 GHz เป็นหลัก) → ~4–6 AP ในห้องนี้ ช่อง 20/40 MHz คนละช่อง
```
(ตัวเลขจริงขึ้นกับแอปและอุปกรณ์ — ใช้เครื่องมือ/คำแนะนำของ vendor ประกอบ)

### ข้อพิจารณาฝั่งสาย
- **PoE budget** ของ switch (AP Wi-Fi 6E/7 อาจต้องการ PoE++ 802.3bt)
- **Uplink mGig (2.5/5G)** สำหรับ AP รุ่นใหม่
- พอร์ต switch ของ AP: access (management VLAN) หรือ trunk (เมื่อ local switching หลาย SSID)

---

## 7. แก้ปัญหา WLAN องค์กร

| อาการ | ตรวจ |
|---|---|
| AP ไม่ join controller | Option 43/DNS, เส้นทางและ firewall UDP 5246/5247, เวลา/cert ของ AP, version |
| ผู้ใช้ 802.1X เชื่อมไม่ได้ | log ของ RADIUS (reject reason), cert ของ server/ client หมดอายุ, ผู้ใช้ไม่อยู่ในกลุ่ม, เวลา NTP |
| ต่อได้แต่ไม่มี IP | VLAN ของ SSID มีบน trunk ไหม, DHCP scope |
| ช้าในห้องประชุม | จำนวน client/AP, channel width กว้างเกิน, 2.4 GHz, co-channel |
| เสียง VoIP ขาด | RSSI < −67, roaming (802.11r), QoS (WMM), channel utilization |
| พบ rogue AP | ใช้ WIPS ระบุตำแหน่ง → ตรวจว่าต่อเข้า LAN หรือไม่ → ถอด |

---

## 8. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| ซ่อน SSID = ปลอดภัย | ไม่ใช่ความปลอดภัย และทำให้ client ส่ง probe ตลอด |
| SSID แยกทุกแผนกเพื่อแบ่ง VLAN | ใช้ 802.1X + dynamic VLAN แทน ลดจำนวน SSID |
| WPA2-PSK เพียงพอสำหรับองค์กร | ควรใช้ Enterprise (802.1X) สำหรับพนักงาน |
| ออกแบบแค่ให้สัญญาณถึงทุกจุดก็พอ | ต้องออกแบบตาม capacity และตรวจหลังติดตั้ง |
| Controller เดียวพอ | ต้องมี HA (SSO/N+1) |

---

## 9. Cheat Sheet

```
Autonomous (เล็ก) · Controller/WLC (campus) · Cloud (หลายสาขา) · FortiGate+FortiAP (SMB)
CAPWAP UDP 5246 control / 5247 data · AP หา WLC: DHCP option 43 / DNS
Local mode (ผ่าน WLC) vs FlexConnect (ออกที่สาขา)
Security: WPA2/3-Enterprise (802.1X, EAP-TLS) สำหรับพนักงาน · WPA3-SAE แทน PSK · OWE สำหรับ guest · iPSK สำหรับ IoT
SSID ≤ 3-4: CORP / GUEST / IOT · Guest: VLAN แยก + firewall + client isolation + portal + log
RRM: DCA + TPC · band steering · airtime fairness · ปิด low data rate · 802.11k/v/r
Survey: requirements → predictive → (AP-on-a-stick) → ติดตั้ง → validation
ออกแบบตาม capacity · PoE++ · mGig uplink
```

---

## 10. แบบทดสอบ 10 ข้อ

1. Controller-based ต่างจาก cloud-managed อย่างไร
2. CAPWAP ใช้ port อะไร AP หา controller ได้อย่างไร (2 วิธี)
3. FlexConnect เหมาะกับสถานการณ์ใด
4. ทำไมองค์กรไม่ควรใช้ WPA2-PSK กับพนักงาน
5. WPA3-SAE ปรับปรุงอะไรจาก WPA2-PSK
6. OWE คืออะไร เหมาะกับ SSID แบบใด
7. แนวปฏิบัติของ Guest Wi-Fi (4 ข้อ)
8. ทำไมควรมี SSID น้อย
9. ขั้นตอน site survey ที่ถูกต้อง
10. ห้องสัมมนา 300 คน ควรออกแบบตาม coverage หรือ capacity และควรใช้ channel width เท่าไร

<details><summary><b>เฉลย</b></summary>

1. Controller-based ใช้ WLC (มักติดตั้งในองค์กร) จัดการ AP; cloud-managed จัดการผ่าน cloud dashboard (license รายปี เหมาะกับหลายสาขา)
2. UDP 5246 (control) และ 5247 (data); DHCP option 43, DNS, broadcast ในวงเดียวกัน หรือตั้งค่าตรง
3. สาขาที่ controller อยู่ HQ — ให้ traffic ผู้ใช้ออกที่สาขาโดยตรง และยังทำงานได้เมื่อ WAN ขาด
4. รหัสผ่านเดียวกันทั้งองค์กร คนลาออก/รหัสรั่วต้องเปลี่ยนทุกเครื่อง ไม่รู้ว่าใครเป็นใคร — ควรใช้ 802.1X
5. ป้องกัน offline dictionary attack จาก handshake และมี forward secrecy
6. Enhanced Open — เข้ารหัสการเชื่อมต่อโดยไม่ต้องใช้รหัสผ่าน เหมาะกับ Guest/Wi-Fi สาธารณะ
7. VLAN แยก + firewall ให้ออกได้แค่อินเทอร์เน็ต, client isolation, captive portal + เก็บ log, rate limit/DNS filtering
8. แต่ละ SSID ส่ง beacon กิน airtime ทำให้ throughput รวมลดลง
9. Requirements → predictive survey → (pre-deployment AP-on-a-stick) → ติดตั้ง → post-deployment validation survey
10. Capacity — ใช้ 20 MHz (หรือ 40 MHz ถ้าช่องพอ) เพื่อให้มีช่องไม่ทับกันมากพอสำหรับ AP จำนวนมาก
</details>

---

➡️ ต่อไป: **Level 53 — ACL (Access Control List)**
