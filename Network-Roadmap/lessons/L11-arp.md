# บทเรียน Level 11 — ARP (Address Resolution Protocol) (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจว่าเครื่องหา MAC จาก IP อย่างไร · อ่าน ARP table ได้ · รู้ว่าทำไมส่งไปนอกวงต้อง ARP หา gateway · รู้จัก Gratuitous ARP, Proxy ARP และการโจมตี ARP spoofing

---

## 1. ปัญหาที่ ARP แก้

ตอนส่งข้อมูล เครื่องรู้ **IP ปลายทาง** (จาก DNS หรือผู้ใช้พิมพ์) แต่การส่งจริงในชั้น Ethernet ต้องใช้ **MAC ปลายทาง** ใส่ใน frame

**ARP = ตัวแปลง IP → MAC ภายในเครือข่ายเดียวกัน (broadcast domain เดียว)**

> 💡 **เปรียบเทียบ:** เข้าห้องประชุมแล้วตะโกนถามว่า "ใครชื่อสมชาย (IP) ยกมือหน่อย" คนชื่อสมชายยกมือแล้วบอกว่า "ผมนั่งเก้าอี้ตัวที่ 5 (MAC)" ครั้งต่อไปเราจดไว้แล้ว ไม่ต้องตะโกนถามอีก

---

## 2. ขั้นตอนการทำงาน

**สถานการณ์:** PC-A (192.168.1.10) ต้องการส่งถึง PC-B (192.168.1.20) ในวงเดียวกัน

```
 1) PC-A ตรวจ ARP cache ของตัวเอง → ยังไม่มี MAC ของ 192.168.1.20

 2) ARP Request (BROADCAST)
    Src MAC: AA:AA (PC-A)   Dst MAC: FF:FF:FF:FF:FF:FF
    "ใครคือ 192.168.1.20? บอก 192.168.1.10 ด้วย"
            │
     ┌──────┴──────── switch flood ไปทุกพอร์ตใน VLAN ───────┐
     ▼                    ▼                                  ▼
   PC-C (ไม่ใช่ ทิ้ง)    PC-B (ใช่!)                      PC-D (ไม่ใช่ ทิ้ง)

 3) ARP Reply (UNICAST) จาก PC-B → PC-A
    "192.168.1.20 อยู่ที่ MAC BB:BB"

 4) PC-A บันทึกลง ARP cache แล้วส่งข้อมูลจริงถึง BB:BB
    (PC-B ก็จด MAC ของ PC-A ไว้จาก Request ด้วย)
```

- **ARP Request** = broadcast (ไม่รู้ว่าใครเป็นเจ้าของ จึงต้องถามทุกคน)
- **ARP Reply** = unicast (ตอบกลับคนถามโดยตรง)
- ARP อยู่ระหว่าง L2 กับ L3 (EtherType `0x0806`)

---

## 3. ส่งไปนอกวง → ARP หา Default Gateway

**กฎสำคัญที่สุดของบทนี้:** ARP **ไม่ข้าม router** (เพราะเป็น broadcast)

**สถานการณ์:** PC-A (192.168.1.10/24, gateway 192.168.1.1) ส่งถึง 8.8.8.8

```
 1) PC-A ทำ AND: 8.8.8.8 ไม่อยู่ในวง 192.168.1.0/24 → ต้องส่งผ่าน gateway
 2) PC-A ARP หา MAC ของ "192.168.1.1" (gateway) ไม่ใช่ของ 8.8.8.8
 3) ได้ MAC ของ router แล้วส่ง frame:
       Dst MAC = MAC ของ router
       Dst IP  = 8.8.8.8          ← IP ปลายทางจริงไม่เปลี่ยน
 4) Router รับแล้วส่งต่อ โดย ARP หา hop ถัดไปของตัวเอง
```

> 🔑 **ถ้า ARP หา gateway ไม่ได้ = ออกนอกวงไม่ได้ทั้งหมด** (เช่น gateway ล่ม, VLAN ผิด, ตั้ง gateway ผิด)

---

## 4. ARP Cache (ARP Table)

เครื่องจะจำผล ARP ไว้ช่วงหนึ่งเพื่อไม่ต้องถามซ้ำทุกครั้ง

```bash
# Windows
arp -a
  Internet Address      Physical Address      Type
  192.168.1.1           00-11-22-33-44-55     dynamic
  192.168.1.255         ff-ff-ff-ff-ff-ff     static

# Linux
ip neigh show
  192.168.1.1 dev eth0 lladdr 00:11:22:33:44:55 REACHABLE

# Cisco
show ip arp
```

- **Dynamic:** ได้จาก ARP อัตโนมัติ หมดอายุตามเวลา (Windows/Linux ไม่กี่นาที, Cisco router ค่าเริ่มต้น 4 ชั่วโมง)
- **Static:** ตั้งเอง ไม่หมดอายุ

**ล้าง ARP cache** (เมื่อเปลี่ยนอุปกรณ์/IP แล้วยังจำ MAC เก่า):
```bash
arp -d *                 # Windows (admin)
sudo ip neigh flush all  # Linux
clear ip arp             # Cisco
```

---

## 5. ARP แบบพิเศษ

### Gratuitous ARP (GARP)
- เครื่อง **ประกาศ IP/MAC ของตัวเองเอง** โดยไม่มีใครถาม (ส่ง ARP ถามหา IP ของตัวเอง)
- **ใช้เพื่อ:**
  - ตรวจว่า **IP ซ้ำ** หรือไม่ตอนเพิ่งได้ IP (ถ้ามีคนตอบ = มีคนใช้ IP นี้อยู่แล้ว → Windows แจ้ง "IP address conflict")
  - บอกทุกเครื่องให้ **อัปเดต MAC ใหม่** หลัง failover ของ HSRP/VRRP, firewall cluster, VM ย้ายเครื่อง

### Proxy ARP
- Router **ตอบ ARP แทน** เครื่องที่อยู่อีกวง ทำให้เครื่องที่ตั้งค่าผิด (ไม่มี gateway หรือ mask กว้างเกิน) ยังส่งข้อมูลได้
- ช่วยแก้ปัญหาเฉพาะหน้าได้ แต่ทำให้ ARP table ใหญ่และซ่อนปัญหาการตั้งค่า หลายองค์กรจึงปิดไว้

### Reverse ARP / InARP
- RARP (MAC → IP) เป็นของเก่าที่ DHCP มาแทนแล้ว

### IPv6 ไม่มี ARP
- ใช้ **NDP (Neighbor Discovery Protocol)** ผ่าน ICMPv6 (Neighbor Solicitation/Advertisement) และใช้ multicast แทน broadcast (Level 19)

---

## 6. ความปลอดภัย: ARP Spoofing / ARP Poisoning

**ปัญหา:** ARP **ไม่มีการยืนยันตัวตน** ใครตอบมาก็เชื่อ และยอมรับ reply แม้ไม่ได้ถาม

```
 ผู้โจมตีส่ง ARP Reply ปลอมว่า:
   "192.168.1.1 (gateway) อยู่ที่ MAC ของฉัน"  → ส่งให้เหยื่อ
   "192.168.1.10 (เหยื่อ) อยู่ที่ MAC ของฉัน"  → ส่งให้ gateway

 ผล: traffic ของเหยื่อวิ่งผ่านเครื่องผู้โจมตีก่อน = Man-in-the-Middle (MITM)
     ดักดู/แก้ไขข้อมูลได้ หรือทิ้งข้อมูล (DoS)
```

**การป้องกัน**
- **Dynamic ARP Inspection (DAI)** บน switch: ตรวจ ARP กับตาราง DHCP snooping ปลอมไม่ได้ (Level 63)
- **DHCP snooping + IP Source Guard**
- แยก VLAN ให้เล็ก, ใช้ 802.1X
- ใช้การเข้ารหัส (HTTPS, SSH, VPN) ข้อมูลที่ถูกดักก็อ่านไม่ได้
- Static ARP สำหรับอุปกรณ์สำคัญ (จัดการยาก ใช้เฉพาะจุด)
- ตรวจจับ: แจ้งเตือนเมื่อ MAC ของ gateway เปลี่ยน (เช่น arpwatch)

> ⚠️ ทดลอง ARP spoofing ได้เฉพาะใน lab ของตัวเองเท่านั้น

---

## 7. ARP ในการแก้ปัญหา

| อาการ | ตรวจด้วย ARP |
|---|---|
| ping gateway ไม่ได้ | `arp -a` มี MAC ของ gateway ไหม ถ้าเป็น incomplete = L2 ไปไม่ถึง (VLAN/สาย) |
| เปลี่ยน router ใหม่ IP เดิม แต่บางเครื่องเข้าเน็ตไม่ได้ | เครื่องจำ MAC เก่า → ล้าง ARP cache หรือรอหมดอายุ (router ใหม่ควรส่ง GARP) |
| IP conflict | ARP เห็น MAC สองตัวสลับกันสำหรับ IP เดียว |
| เน็ตช้าผิดปกติทั้งวง สงสัยถูกดัก | MAC ของ gateway ในเครื่องไม่ตรงกับ MAC จริงของ router |

**ดูใน Wireshark:** filter `arp` เห็น Request "Who has 192.168.1.1? Tell 192.168.1.10" และ Reply "192.168.1.1 is at 00:11:22:33:44:55"

---

## 8. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| ARP หา MAC ของเว็บไซต์ปลายทาง | ARP หาเฉพาะในวงเดียวกัน ถ้าปลายทางอยู่นอกวงจะหา MAC ของ gateway |
| ARP Reply เป็น broadcast | Request เป็น broadcast, Reply เป็น unicast |
| ARP มีระบบป้องกันการปลอม | ไม่มีเลย ต้องพึ่ง DAI/การเข้ารหัส |
| IPv6 ใช้ ARP | ใช้ NDP แทน |

---

## 9. Cheat Sheet

```
ARP = IP → MAC ภายในวงเดียว · EtherType 0x0806
Request = broadcast (FF:FF...) · Reply = unicast
ปลายทางนอกวง → ARP หา MAC ของ GATEWAY · ARP ไม่ข้าม router
ดู: arp -a (Win) · ip neigh (Linux) · show ip arp (Cisco)
GARP = ประกาศตัวเอง (ตรวจ IP ซ้ำ / failover) · Proxy ARP = router ตอบแทน
ARP spoofing → MITM · ป้องกัน: DAI + DHCP snooping + การเข้ารหัส
IPv6 ใช้ NDP แทน ARP
```

---

## 10. แบบทดสอบ 10 ข้อ

1. ARP แปลงอะไรเป็นอะไร
2. ARP Request ส่งไปที่ MAC อะไร ARP Reply ล่ะ
3. PC (10.0.0.5/24, gateway 10.0.0.1) ส่งถึง 1.1.1.1 จะ ARP หา MAC ของใคร
4. ใน frame ที่ PC ส่งในข้อ 3 Dst MAC และ Dst IP คืออะไร
5. ทำไม ARP ไม่ข้าม router
6. Gratuitous ARP ใช้ทำอะไร 2 กรณี
7. คำสั่งดู ARP table บน Windows และ Linux
8. ARP spoofing คืออะไร ผลกระทบคืออะไร
9. Switch ป้องกัน ARP spoofing ด้วยฟีเจอร์อะไร
10. IPv6 ใช้อะไรแทน ARP

<details><summary><b>เฉลย</b></summary>

1. IP address → MAC address
2. Request: FF:FF:FF:FF:FF:FF (broadcast); Reply: MAC ของผู้ถาม (unicast)
3. Default gateway (10.0.0.1)
4. Dst MAC = MAC ของ gateway; Dst IP = 1.1.1.1
5. เป็น broadcast และ router ไม่ส่ง broadcast ข้ามเครือข่าย
6. ตรวจ IP ซ้ำ และแจ้ง MAC ใหม่หลัง failover/ย้าย VM
7. Windows `arp -a`; Linux `ip neigh show`
8. ส่ง ARP reply ปลอมเพื่ออ้างว่าเป็นเจ้าของ IP (เช่น gateway) → traffic ผ่านผู้โจมตี (MITM) หรือถูกทิ้ง (DoS)
9. Dynamic ARP Inspection (DAI) ร่วมกับ DHCP snooping
10. NDP (Neighbor Discovery Protocol) ผ่าน ICMPv6
</details>

---

➡️ ต่อไป: **Level 12 — ICMP, ping, traceroute**
