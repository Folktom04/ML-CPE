# บทเรียน Level 15 — DHCP (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจกระบวนการ DORA · lease/renew · scope, exclusion, reservation, option · DHCP relay เมื่อ server อยู่คนละวง · ตั้งค่าบน Cisco/Windows/Linux · แก้ปัญหา "ไม่ได้ IP" และรู้จัก rogue DHCP

---

## 1. DHCP คืออะไร

**DHCP (Dynamic Host Configuration Protocol)** คือบริการที่ **แจกการตั้งค่าเครือข่ายให้อุปกรณ์อัตโนมัติ** ได้แก่
- IP address + Subnet mask
- Default gateway
- DNS server(s), Domain name
- ค่าอื่น ๆ (NTP, TFTP สำหรับ boot, controller ของ AP ฯลฯ)

ใช้ **UDP port 67 (server)** และ **68 (client)**

> 💡 **เปรียบเทียบ:** DHCP คือ **พนักงานต้อนรับโรงแรม** แขกมาถึงก็ได้กุญแจห้อง (IP) พร้อมแผนที่ (gateway/DNS) มีกำหนดเช็กเอาต์ (lease) อยากอยู่ต่อก็ขอต่ออายุ

**ถ้าไม่มี DHCP:** ต้องตั้ง IP ทีละเครื่องด้วยมือ เสี่ยง IP ซ้ำ และมือถือ/โน้ตบุ๊กที่ย้ายวงบ่อยใช้งานลำบาก

---

## 2. DORA — 4 ขั้นตอนการขอ IP

```
 Client (ยังไม่มี IP: 0.0.0.0)                       DHCP Server (192.168.1.1)
     │ ① DISCOVER  "มี DHCP server ไหม?"                        │
     │   src 0.0.0.0:68 → dst 255.255.255.255:67 (broadcast)     │
     │ ─────────────────────────────────────────────────────────►│
     │                ② OFFER  "ให้ 192.168.1.50 ไหม?"           │
     │ ◄─────────────────────────────────────────────────────────│
     │ ③ REQUEST  "ขอรับ 192.168.1.50 จาก server 192.168.1.1"     │
     │   (broadcast เพื่อบอก server อื่นที่ offer มาว่าไม่เลือก)    │
     │ ─────────────────────────────────────────────────────────►│
     │                ④ ACK  "ยืนยัน ใช้ได้ 8 วัน"                │
     │ ◄─────────────────────────────────────────────────────────│
  ตั้งค่า IP แล้ว (มักส่ง Gratuitous ARP ตรวจว่า IP ไม่ซ้ำ)
```

| ขั้น | ใครส่ง | แบบ | สาระสำคัญ |
|---|---|---|---|
| **D**iscover | Client | Broadcast | ค้นหา server |
| **O**ffer | Server | Broadcast หรือ Unicast (ตาม flag) | เสนอ IP + ค่าต่าง ๆ |
| **R**equest | Client | Broadcast | ขอรับข้อเสนอที่เลือก |
| **A**cknowledge | Server | Broadcast หรือ Unicast | ยืนยัน (หรือ **NAK** ปฏิเสธ) |

---

## 3. Lease — สัญญาเช่า IP

- IP ที่ได้มี **อายุ (lease time)** เช่น 8 ชั่วโมง / 1 วัน / 8 วัน
- **T1 = 50% ของ lease:** client ขอต่ออายุกับ server เดิมโดยตรง (unicast)
- **T2 = 87.5%:** ถ้ายังไม่ได้ ขอต่อจาก server ใดก็ได้ (broadcast)
- หมดอายุแล้วยังต่อไม่ได้ → ปล่อย IP แล้วเริ่ม DORA ใหม่
- **เลือก lease time:** วงที่คนเข้าออกบ่อย (Guest Wi-Fi, ร้านกาแฟ) ใช้ lease สั้น (1–4 ชม.) เพื่อไม่ให้ pool เต็ม; วงสำนักงานใช้ 1–8 วัน

```bash
ipconfig /release && ipconfig /renew     # Windows ขอใหม่
sudo dhclient -r && sudo dhclient        # Linux (บาง distro ใช้ nmcli/networkctl)
ipconfig /all                            # ดู DHCP server, lease obtained/expires
```

---

## 4. ศัพท์ที่ต้องรู้ในการตั้งค่า

| คำ | ความหมาย |
|---|---|
| **Scope / Pool** | ช่วง IP ที่แจกได้ในหนึ่ง subnet เช่น 192.168.10.100–200 |
| **Exclusion** | IP ที่ **ห้ามแจก** เพราะใช้ static อยู่ (gateway, server, printer) |
| **Reservation** | **จอง** IP เดิมให้อุปกรณ์หนึ่งเสมอ (ผูกกับ MAC/client-ID) |
| **Option** | ค่าเพิ่มเติมที่แจกไปด้วย |

### DHCP Options ที่ใช้บ่อย

| Option | ค่า |
|---|---|
| 1 | Subnet mask |
| **3** | **Router (default gateway)** |
| **6** | **DNS servers** |
| 15 | Domain name |
| 42 | NTP servers |
| **43** | Vendor-specific — บอก AP ว่า **Wireless Controller** อยู่ที่ไหน |
| **66/67** | TFTP server / boot file — สำหรับ **PXE boot** และ IP phone ดึง config |
| 150 | TFTP server (Cisco IP phone) |

---

## 5. DHCP Relay — เมื่อ server อยู่คนละวง

ปัญหา: DHCP Discover เป็น **broadcast** และ **router ไม่ส่ง broadcast ข้ามวง** แต่องค์กรมักมี DHCP server กลางที่ data center

**ทางแก้:** ตั้ง **DHCP Relay Agent** (Cisco เรียก `ip helper-address`) บน gateway ของแต่ละ VLAN

```
 VLAN 10 (192.168.10.0/24)           Data Center
 [PC] ─broadcast Discover─► [L3 Switch / Router] ─unicast─► [DHCP Server 10.0.0.10]
                             gateway 192.168.10.1
                             ip helper-address 10.0.0.10
   relay ใส่ "giaddr = 192.168.10.1" ลงใน packet → server รู้ว่าต้องแจกจาก scope ของวง 192.168.10.0
```

---

## 6. ตัวอย่างการตั้งค่า

### Cisco IOS (router/L3 switch เป็น DHCP server)
```
ip dhcp excluded-address 192.168.10.1 192.168.10.20
ip dhcp pool VLAN10-USERS
 network 192.168.10.0 255.255.255.0
 default-router 192.168.10.1
 dns-server 10.0.0.53 1.1.1.1
 domain-name corp.local
 lease 1
!
interface vlan 20
 ip helper-address 10.0.0.10      ! relay วงนี้ไป server กลาง
!
show ip dhcp binding               ! ใครได้ IP อะไร
show ip dhcp pool                  ! ใช้ไปเท่าไร
show ip dhcp conflict
```

### Windows Server
DHCP role → New Scope (range, exclusion, lease) → Options 003/006/015 → Authorize ใน AD
- รองรับ **DHCP Failover** (2 server แบ่งโหลดหรือสำรองกัน)

### Linux (dnsmasq แบบง่าย / ISC Kea สำหรับองค์กร)
```
# /etc/dnsmasq.conf
interface=eth1
dhcp-range=192.168.50.100,192.168.50.200,255.255.255.0,12h
dhcp-option=3,192.168.50.1
dhcp-option=6,1.1.1.1
dhcp-host=AA:BB:CC:DD:EE:FF,192.168.50.20   # reservation
```

---

## 7. การแก้ปัญหา "เครื่องไม่ได้ IP"

**อาการ:** ได้ **169.254.x.x** (APIPA) หรือ "No valid IP configuration"

```
 1) L1/L2: สายเสียบ? ไฟพอร์ตติด? Wi-Fi เชื่อมต่อแล้ว?
 2) VLAN: พอร์ต/SSID อยู่ VLAN ที่ถูกต้อง? VLAN นั้นมีบน trunk ถึง gateway หรือยัง?
 3) Relay: gateway ของ VLAN ตั้ง ip helper-address แล้ว? ชี้ IP server ถูก?
 4) Server: บริการทำงาน? scope เปิดใช้งาน (activate)? Windows ต้อง authorize ใน AD
 5) Pool เต็ม? → show ip dhcp pool / ดูใน console (แก้: ขยาย scope, ลด lease, ลบ lease เก่า)
 6) Firewall/ACL ระหว่าง relay กับ server บล็อก UDP 67/68?
 7) DHCP snooping บล็อกเพราะพอร์ต uplink ไม่ได้ trust?
 8) จับ packet: เห็น Discover ออกไปไหม? มี Offer กลับไหม?
```

**อาการได้ IP ผิดวง** (เช่น องค์กรใช้ 10.x แต่ได้ 192.168.0.x)
→ มี **Rogue DHCP server** เช่น พนักงานเสียบ router บ้านเข้าระบบ (ขา LAN เข้า) ทำให้แจก IP ผิดให้ทุกคนที่ตอบเร็วกว่า

---

## 8. ความปลอดภัย

| ภัย | ป้องกัน |
|---|---|
| **Rogue DHCP** (แจก IP/gateway ปลอม → ดักข้อมูลได้) | **DHCP Snooping**: กำหนดให้ Offer/ACK มาได้เฉพาะจากพอร์ต **trusted** (uplink ไป server) |
| **DHCP Starvation** (ขอ IP ด้วย MAC ปลอมจนหมด pool) | DHCP snooping rate-limit, port security |
| ใครเสียบก็ได้ IP | 802.1X/NAC ก่อนเข้าเครือข่าย |

```
ip dhcp snooping
ip dhcp snooping vlan 10,20
interface gi1/0/48
 ip dhcp snooping trust          ! เฉพาะพอร์ต uplink
```

---

## 9. DHCP กับ IPv6 (ภาพรวม)
IPv6 ได้ IP ได้ทั้งจาก **SLAAC** (สร้างเองจาก router advertisement) และ **DHCPv6** (stateful/stateless) รายละเอียดใน Level 19

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| ต้องมี DHCP server ทุก VLAN | ใช้ server กลาง + relay (ip helper-address) ได้ |
| Reservation กับ static IP เหมือนกัน | Reservation ยังจัดการจาก server กลางและได้ option อื่นด้วย |
| ได้ 169.254.x.x = ปัญหาที่เครื่อง | ส่วนใหญ่เป็นที่เครือข่าย/VLAN/relay/server |
| ใส่ exclusion ไม่จำเป็น | ถ้าไม่ใส่ อาจแจก IP ที่ชนกับ static (gateway/server) |

---

## 11. Cheat Sheet

```
DHCP = แจก IP/mask/gateway/DNS อัตโนมัติ · UDP 67 server / 68 client
DORA: Discover(bcast) → Offer → Request(bcast) → Ack (NAK = ปฏิเสธ)
Lease: T1 50% ต่ออายุ unicast · T2 87.5% broadcast
Scope · Exclusion (ห้ามแจก) · Reservation (จองตาม MAC)
Option 3 gateway · 6 DNS · 15 domain · 43 WLC · 66/67 TFTP/PXE
ข้ามวงใช้ Relay: ip helper-address <server>
169.254.x.x = ไม่ได้ IP · ได้ IP ผิดวง = rogue DHCP
ป้องกัน: DHCP snooping (trust เฉพาะ uplink)
```

---

## 12. แบบทดสอบ 10 ข้อ

1. DORA ย่อมาจากอะไร ขั้นใดเป็น broadcast จาก client
2. DHCP ใช้ port อะไร
3. Client เริ่มขอต่ออายุ lease เมื่อใด
4. Exclusion กับ Reservation ต่างกันอย่างไร
5. Option 3, 6 และ 43 คืออะไร
6. ทำไมต้องมี DHCP relay และ Cisco ตั้งด้วยคำสั่งอะไร
7. ผู้ใช้ทั้ง VLAN 30 ไม่ได้ IP แต่ VLAN อื่นปกติ (ใช้ server เดียวกัน) ควรตรวจอะไรก่อน
8. ผู้ใช้หลายคนได้ IP 192.168.0.x ทั้งที่องค์กรใช้ 10.x สาเหตุคืออะไร ป้องกันอย่างไร
9. Guest Wi-Fi ที่มีคนเข้าออกมากควรตั้ง lease สั้นหรือยาว เพราะอะไร
10. ใน DHCP snooping พอร์ตใดต้องตั้งเป็น trusted

<details><summary><b>เฉลย</b></summary>

1. Discover, Offer, Request, Acknowledge — Discover และ Request เป็น broadcast จาก client
2. UDP 67 (server), 68 (client)
3. ที่ 50% ของ lease (T1)
4. Exclusion = ห้ามแจก IP ช่วงนั้น; Reservation = จอง IP ให้อุปกรณ์ที่ระบุ (ตาม MAC) เสมอ
5. 3 = default gateway, 6 = DNS server, 43 = ข้อมูลเฉพาะ vendor เช่น ที่อยู่ของ Wireless Controller
6. Discover เป็น broadcast ข้าม router ไม่ได้ จึงต้องให้ gateway ส่งต่อแบบ unicast ไปยัง server — `ip helper-address <IP server>`
7. ip helper-address บน gateway ของ VLAN 30, scope ของวงนั้น (มี/เปิด/เต็ม), VLAN 30 อยู่บน trunk ครบไหม
8. Rogue DHCP (เช่น router บ้านถูกเสียบเข้าระบบ) — ป้องกันด้วย DHCP snooping และ port security/802.1X
9. สั้น — ให้ IP ของคนที่ออกไปแล้วคืนเข้า pool เร็ว ไม่ให้ pool เต็ม
10. พอร์ต uplink ที่ไปหา DHCP server/relay จริง
</details>

---

➡️ ต่อไป: **Level 16 — DNS**
