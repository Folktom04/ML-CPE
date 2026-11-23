# บทเรียน Level 5 — อุปกรณ์เครือข่าย (ฉบับละเอียด)

> อ่านจบแล้วจะ: รู้หน้าที่ของ Hub, Switch, Router, L3 Switch, AP, WLC, Firewall, Load Balancer, Modem/ONT · เข้าใจ Collision domain vs Broadcast domain · วางอุปกรณ์ตามโครงสร้าง Core–Distribution–Access ได้

---

## 1. ภาพรวม: อุปกรณ์แต่ละตัวทำงานที่ชั้นไหน

| อุปกรณ์ | Layer | ตัดสินใจจาก | หน้าที่หลัก |
|---|---|---|---|
| Repeater / Hub | L1 | ไม่ดูอะไรเลย | ทวนสัญญาณ / กระจายออกทุกพอร์ต |
| Bridge / **Switch** | L2 | **MAC address** | ส่ง frame ไปพอร์ตที่ถูกต้องในเครือข่ายเดียวกัน |
| **Router** | L3 | **IP address** | ส่ง packet ข้ามเครือข่าย, เลือกเส้นทาง |
| **L3 Switch** | L2 + L3 | MAC + IP | switch ที่ route ระหว่าง VLAN ได้ด้วยความเร็วสูง |
| Access Point | L1–L2 | MAC | เชื่อมอุปกรณ์ไร้สายเข้ากับเครือข่ายสาย |
| **Firewall** | L3–L7 | IP, port, แอป, ผู้ใช้ | อนุญาต/ปฏิเสธการเชื่อมต่อตามนโยบาย |
| Load Balancer | L4–L7 | IP/port หรือ URL/header | กระจายผู้ใช้ไปหลาย server |

---

## 2. Hub (ฮับ) — อุปกรณ์รุ่นเก่า

```
         PC1 ส่งถึง PC3
  [PC1] ──►[  HUB  ]──► PC2 (ได้รับด้วย)
              │ └────► PC3 (ปลายทางจริง)
              └──────► PC4 (ได้รับด้วย)
```
- รับสัญญาณเข้ามาแล้ว **ทวนออกทุกพอร์ต** ไม่รู้จัก MAC
- ทุกพอร์ตใช้สื่อกลางร่วมกันเหมือนสายเส้นเดียว จึงส่งได้ทีละเครื่อง (half-duplex) และ **ชนกัน (collision)** บ่อย
- ทุกเครื่องเห็นข้อมูลของทุกคน จึงไม่ปลอดภัย
- 📍 ปัจจุบันเลิกใช้แล้ว ใช้ switch แทนทั้งหมด

## 3. Switch (สวิตช์) — หัวใจของ LAN

```
 MAC Address Table
 ┌──────────────┬──────┐
 │ MAC          │ Port │
 │ AA:..:01     │  1   │
 │ AA:..:03     │  3   │
 └──────────────┴──────┘
  [PC1]─1─[ SWITCH ]─3─[PC3]     PC1 ส่งถึง PC3 → ส่งออกพอร์ต 3 พอร์ตเดียว
          2│     │4
         [PC2] [PC4]              PC2, PC4 ไม่ได้รับ
```

- **เรียนรู้ (Learn):** จำว่า MAC ต้นทางอยู่พอร์ตไหน เก็บในตาราง MAC
- **ส่งต่อ (Forward):** ถ้ารู้จัก MAC ปลายทาง ส่งออกเฉพาะพอร์ตนั้น
- **กระจาย (Flood):** ถ้ายังไม่รู้จักปลายทาง หรือเป็น broadcast ส่งออกทุกพอร์ต (ใน VLAN เดียวกัน)
- **Full-duplex:** ส่งและรับพร้อมกันได้ ไม่มีการชน
- **Managed vs Unmanaged:**
  - *Unmanaged:* เสียบแล้วใช้ได้เลย ตั้งค่าไม่ได้ (บ้าน/ร้านเล็ก)
  - *Managed:* ตั้ง VLAN, STP, QoS, port security, ดูสถิติ, SNMP ได้ (องค์กรใช้แบบนี้)
- **PoE switch:** จ่ายไฟให้ AP/กล้อง/IP phone ได้
- **Stackable:** ต่อหลายตัวรวมเป็นตัวเดียวในการจัดการ

## 4. Router (เราเตอร์) — เชื่อมระหว่างเครือข่าย

```
  LAN 192.168.1.0/24          LAN 10.0.0.0/24            อินเทอร์เน็ต
  [PCs]──[Switch]──(G0/1)[ ROUTER ](G0/2)──[Switch]──[Servers]
                                  │(G0/0)
                                  └────────── ISP
```
- แต่ละขา (interface) อยู่ในเครือข่าย (subnet) ต่างกัน
- ดู **IP ปลายทาง** แล้วเปิด **routing table** หาว่าต้องส่งออกขาไหนและส่งต่อให้ใคร
- **ไม่ส่ง broadcast ข้ามเครือข่าย** จึงเป็นตัวแบ่ง broadcast domain
- งานอื่นที่มักทำ: NAT, DHCP, VPN, ACL, QoS
- **Router ในบ้าน** = router + switch + Wi-Fi AP + firewall + DHCP + modem รวมในกล่องเดียว

## 5. L3 Switch (Multilayer Switch)

- เป็น switch ที่ **route ระหว่าง VLAN** ได้ด้วยชิป hardware ความเร็วสูง
- ใช้เป็น **Core/Distribution** ขององค์กร (แต่ละ VLAN มี gateway อยู่บน L3 switch)
- ต่างจาก router ตรงที่ปกติมีพอร์ต Ethernet จำนวนมาก แต่ฟีเจอร์ WAN/NAT/VPN น้อยกว่า

## 6. Access Point (AP) และ Wireless LAN Controller (WLC)

- **AP:** แปลงคลื่น Wi-Fi ↔ Ethernet ให้อุปกรณ์ไร้สายเข้าเครือข่ายได้
- **Autonomous AP:** ตั้งค่าทีละตัว เหมาะกับจำนวนน้อย
- **Controller-based / Cloud-managed:** มี **WLC** หรือ cloud กลางจัดการ AP นับร้อยตัวพร้อมกัน (ตั้ง SSID ครั้งเดียว, ปรับ channel/power อัตโนมัติ, roaming)
- **Wi-Fi router ในบ้าน ≠ AP องค์กร**: AP องค์กรรองรับผู้ใช้และการจัดการจากศูนย์กลางได้มากกว่ามาก

## 7. Firewall และ NGFW

- **Firewall:** ตรวจทุกการเชื่อมต่อแล้วอนุญาต/ปฏิเสธตาม **นโยบาย (policy)** เช่น "อนุญาตให้ทุกคนออกเว็บ 443, ห้ามเข้าจากอินเทอร์เน็ตยกเว้น web server"
- **Stateful:** จำสถานะการเชื่อมต่อ ให้ข้อมูลตอบกลับผ่านเข้ามาได้อัตโนมัติ
- **NGFW (Next-Generation Firewall):** เพิ่มความสามารถ
  - รู้จัก **แอปพลิเคชัน** (เช่น block Facebook แต่ให้ใช้ LINE ได้)
  - รู้จัก **ผู้ใช้** (นโยบายตามแผนก)
  - **IPS**, Anti-virus, URL filtering, SSL inspection, Sandbox
- **ตำแหน่ง:** ระหว่างอินเทอร์เน็ตกับเครือข่ายภายใน และระหว่างโซนที่มีความเสี่ยงต่างกัน (เช่น DMZ, Server zone)
- ยี่ห้อที่พบบ่อยในไทย: Fortinet (FortiGate), Palo Alto, Check Point, Cisco, Sophos

## 8. อุปกรณ์อื่นที่ต้องรู้จัก

| อุปกรณ์ | หน้าที่ |
|---|---|
| **Modem** | แปลงสัญญาณดิจิทัล ↔ สัญญาณบนสายของผู้ให้บริการ (DSL/เคเบิล) |
| **ONT (Optical Network Terminal)** | แปลงไฟเบอร์ FTTH → Ethernet (กล่องเน็ตไฟเบอร์ในบ้าน) |
| **Media Converter** | แปลงสายทองแดง ↔ ไฟเบอร์ |
| **Load Balancer / ADC** | กระจายผู้ใช้ไปหลาย server, ตรวจสุขภาพ server |
| **IDS/IPS** | ตรวจจับ/ป้องกันการโจมตี (มักรวมอยู่ใน NGFW) |
| **Proxy** | เป็นตัวกลางเชื่อมต่อแทนผู้ใช้ กรองเว็บ/cache |
| **WAN Optimizer** | เร่งความเร็วการรับส่งข้อมูลข้ามสาขา |
| **Patch Panel** | แผงรวมปลายสาย LAN ในตู้ rack (ไม่มีวงจร เป็นแค่จุดเชื่อมต่อ) |

---

## 9. Collision Domain vs Broadcast Domain — แนวคิดสำคัญ

### Collision Domain
พื้นที่ที่ **ถ้าสองเครื่องส่งพร้อมกันจะชนกัน**
- **Hub:** ทุกพอร์ตรวมเป็น 1 collision domain
- **Switch:** **แต่ละพอร์ตเป็น 1 collision domain** (และเมื่อ full-duplex ก็ไม่มีการชนเลย)

### Broadcast Domain
พื้นที่ที่ **broadcast (ส่งถึงทุกคน) ไปถึง** เช่น ARP request, DHCP Discover
- **Switch (VLAN เดียว):** ทุกพอร์ตรวมเป็น 1 broadcast domain
- **VLAN:** แต่ละ VLAN = 1 broadcast domain
- **Router:** **แต่ละ interface = 1 broadcast domain** (router ไม่ส่ง broadcast ต่อ)

```
                   [ ROUTER ]
                   /        \
            [SWITCH A]    [HUB B]
           /  |  |  \      /  |  \
          PC PC PC PC     PC PC PC

  Broadcast domain = 2 (ขาละ 1)
  Collision domain = Switch A: 4 พอร์ต + uplink 1 = 5  · Hub B: 1 (ทั้ง hub รวมกัน)
                     + ลิงก์ hub↔router นับรวมใน domain ของ hub
```

> 💡 **ทำไมต้องสนใจ:** broadcast domain ใหญ่เกินไป (เครื่องหลายพันเครื่องใน VLAN เดียว) ทำให้ทุกเครื่องต้องประมวลผล broadcast จำนวนมาก และปัญหาลามได้กว้าง จึงแบ่งเป็น VLAN/subnet ย่อย ๆ

---

## 10. วางอุปกรณ์ในองค์กร: Hierarchical Design

```
                    [Internet]
                        │
                   [ Firewall ]  (คู่ HA)
                        │
         ┌──── CORE (L3 switch คู่) ────┐       ← เร็วที่สุด ทนทานที่สุด
         │                              │
  [Distribution A]              [Distribution B]  ← รวมแต่ละอาคาร/ชั้น, policy, routing ระหว่าง VLAN
     │       │                     │       │
 [Access] [Access]             [Access] [Access]  ← เสียบผู้ใช้, AP, IP phone (PoE)
   PCs      APs                  PCs     Printers
```

| ชั้น | หน้าที่ | อุปกรณ์ |
|---|---|---|
| **Core** | backbone ความเร็วสูง ส่งเร็วที่สุด ไม่ทำ policy ซับซ้อน | L3 switch ระดับสูง 40/100G (คู่) |
| **Distribution** | รวม access, routing ระหว่าง VLAN, ACL, QoS | L3 switch |
| **Access** | จุดเชื่อมผู้ใช้, PoE, port security, VLAN | L2/L3 switch, AP |

องค์กรขนาดเล็ก–กลางมักรวม Core กับ Distribution เป็นชั้นเดียว เรียกว่า **Collapsed Core**

---

## 11. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| Router กับ Wi-Fi router บ้านเหมือนกัน | กล่องบ้านรวมหลายอุปกรณ์ ในองค์กรแยกกันและแต่ละตัวมีความสามารถสูงกว่ามาก |
| Switch ส่ง broadcast ข้ามไปเครือข่ายอื่นได้ | Switch ส่ง broadcast ทุกพอร์ตใน VLAN เดียวกัน แต่ข้ามเครือข่ายไม่ได้ ต้องผ่าน router |
| Firewall กันได้ทุกอย่าง | กันได้ตามนโยบายและจุดที่ traffic ผ่าน ไม่เห็น traffic ภายใน VLAN เดียวกัน |
| ยิ่งพอร์ตเยอะยิ่งดี | ต้องดู uplink, PoE budget, ฟีเจอร์ และการรองรับในอนาคต |

---

## 12. Cheat Sheet

```
Hub L1 กระจายทุกพอร์ต (เลิกใช้) · Switch L2 ใช้ MAC · Router L3 ใช้ IP
L3 Switch = switch + route ระหว่าง VLAN · AP = Wi-Fi ↔ LAN · WLC = คุม AP จำนวนมาก
Firewall = policy อนุญาต/ปฏิเสธ · NGFW = + แอป + ผู้ใช้ + IPS/URL/SSL
ONT = ไฟเบอร์ → LAN · Load Balancer = กระจายไปหลาย server

Collision domain: Hub = 1 ทั้งตัว · Switch = 1 ต่อพอร์ต
Broadcast domain: Switch/VLAN = 1 ต่อ VLAN · Router = 1 ต่อ interface
Design: Core (เร็ว) → Distribution (policy/routing) → Access (ผู้ใช้/PoE)
```

---

## 13. แบบทดสอบ 10 ข้อ

1. Switch ใช้ข้อมูลใดในการตัดสินใจส่งต่อ Router ใช้ข้อมูลใด
2. Switch ได้รับ frame ที่ไม่รู้จัก MAC ปลายทาง จะทำอย่างไร
3. Switch 24 พอร์ต (VLAN เดียว) มีกี่ collision domain และกี่ broadcast domain
4. Switch เดิมแต่แบ่งเป็น 3 VLAN มีกี่ broadcast domain
5. Router 4 interface มีกี่ broadcast domain
6. L3 switch ต่างจาก router อย่างไรในการใช้งานจริง
7. ทำไมองค์กรใช้ WLC หรือ cloud management แทนการตั้ง AP ทีละตัว
8. NGFW ทำอะไรได้ที่ firewall แบบเก่าทำไม่ได้ (ยกมา 3 อย่าง)
9. ONT คืออะไร
10. อธิบายหน้าที่ของชั้น Core, Distribution, Access

<details><summary><b>เฉลย</b></summary>

1. Switch = MAC address, Router = IP address
2. Flood ออกทุกพอร์ตใน VLAN เดียวกัน (ยกเว้นพอร์ตที่รับเข้ามา)
3. 24 collision domain, 1 broadcast domain
4. 3
5. 4
6. L3 switch มีพอร์ต Ethernet จำนวนมาก route ระหว่าง VLAN ด้วยความเร็ว hardware ใช้เป็น core/distribution; router มีฟีเจอร์ WAN, NAT, VPN มากกว่า ใช้ที่ขอบเครือข่าย
7. จัดการ AP จำนวนมากจากจุดเดียว ตั้ง SSID ครั้งเดียว ปรับคลื่นอัตโนมัติ รองรับ roaming และดูสถานะรวม
8. ระบุแอปพลิเคชัน, ระบุผู้ใช้, IPS, URL filtering, anti-virus, SSL inspection, sandbox
9. Optical Network Terminal — แปลงไฟเบอร์ FTTH จากผู้ให้บริการเป็น Ethernet
10. Core = backbone ความเร็วสูง; Distribution = รวม access, routing ระหว่าง VLAN, policy; Access = จุดเชื่อมต่อผู้ใช้/อุปกรณ์, PoE, ความปลอดภัยระดับพอร์ต
</details>

---

➡️ ต่อไป: **Level 6 — เลขฐาน 2 / 16 สำหรับงานเน็ตเวิร์ก**
