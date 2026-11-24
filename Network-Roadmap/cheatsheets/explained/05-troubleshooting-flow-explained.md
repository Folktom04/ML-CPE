# อธิบายละเอียด: ลำดับการไล่ปัญหา พร้อมกรณีศึกษาทีละขั้น

> คู่กับ cheat sheet [05-troubleshooting-flow.md](../05-troubleshooting-flow.md)
> อ่านจบแล้วจะ: มีวิธีคิดที่ใช้ได้กับทุกปัญหา · รู้ว่าต้องเริ่มจากตรงไหนและทำไม · เห็นการไล่ปัญหาจริงตั้งแต่รับแจ้งจนปิดงาน 6 กรณี · รู้วิธีบันทึกและสื่อสารผล

---

## 1. วิธีคิด: "แบ่งครึ่ง" ไม่ใช่ "เดา"

มือใหม่มักเดาสาเหตุที่คุ้นเคย ("น่าจะ firewall") แล้วไปแก้ตรงนั้นทันที ผู้มีประสบการณ์จะ **แบ่งเส้นทางเป็นช่วง ๆ แล้วพิสูจน์ทีละช่วงว่าผ่านหรือไม่**
```
 [ผู้ใช้] ── ① ── [Switch] ── ② ── [Gateway] ── ③ ── [Firewall] ── ④ ── [WAN/ISP] ── ⑤ ── [ปลายทาง]

 ping gateway ผ่าน?   ใช่ → ช่วง ①② ปกติ ตัดทิ้งได้   ไม่ → ปัญหาอยู่ในช่วง ①② (แคบลงมาก)
 ping 8.8.8.8 ผ่าน?   ใช่ → ช่วง ③④ ปกติ             ไม่ → ปัญหาอยู่ที่ ③④
 port ปลายทางผ่าน?    ...
```
ทุกการทดสอบควร **ตัดความเป็นไปได้ออกครึ่งหนึ่ง** — เร็วกว่าเดาสุ่มมาก

### 3 กฎที่ช่วยไม่ให้หลงทาง
1. **เปลี่ยนทีละอย่าง** แล้วทดสอบ — เปลี่ยนหลายอย่างพร้อมกันจะไม่รู้ว่าอะไรแก้ได้ (หรือทำให้แย่ลง)
2. **ทดสอบจากมุมของผู้ใช้** — ping จาก router อาจผ่าน แต่ผู้ใช้ไม่ผ่าน เพราะ IP ต้นทางต่างกัน
3. **จดทุกอย่างพร้อมเวลา** — คำสั่ง, ผลลัพธ์, สิ่งที่เปลี่ยน (ใช้ส่งต่อ, เปิด TAC, ทำ post-mortem)

---

## 2. ถามก่อนลงมือ — ทำไมแต่ละคำถามสำคัญ

| คำถาม | ถ้าคำตอบคือ… | ชี้ไปที่ |
|---|---|---|
| **ใครเป็นบ้าง** | คนเดียว | เครื่อง, สาย, พอร์ต, บัญชีผู้ใช้ |
| | ทั้งแผนก/ชั้น | switch ชั้นนั้น, VLAN, uplink, AP |
| | ทั้งสาขา | WAN/ISP/firewall สาขา/VPN |
| | ทุกคน | ระบบกลาง (DNS, firewall HQ, internet, แอป) |
| **อะไรใช้ไม่ได้** | ทุกอย่าง | network พื้นฐาน (IP, gateway) |
| | เฉพาะเว็บภายนอก | internet/DNS/proxy |
| | เฉพาะระบบเดียว | ระบบนั้น/route/policy ไปหาระบบนั้น |
| **ที่ไหน** | Wi-Fi เป็น แต่สาย LAN ไม่เป็น | ระบบ Wi-Fi (AP, controller, SSID, RADIUS) |
| | ที่บ้าน/VPN | VPN, route ของ VPN, MTU |
| **เมื่อไร** | เป็นตลอด | config/อุปกรณ์เสีย — ทำซ้ำได้ แก้ง่ายกว่า |
| | เป็นช่วงเวลาเดิมทุกวัน | งานตามตาราง (backup, update) ทำให้ลิงก์เต็ม |
| | สุ่ม เป็นพัก ๆ | Wi-Fi, สาย/SFP เสื่อม, loop, congestion — ต้องเก็บข้อมูลต่อเนื่อง |
| **มีอะไรเปลี่ยน** | เพิ่งมี change/ย้ายโต๊ะ/อัปเดต | **สาเหตุอันดับ 1** ของปัญหาส่วนใหญ่ — ดูก่อน |

---

## 3. ทำไมลำดับขั้นจึงเป็นแบบนี้

| ขั้น | คำสั่ง | ทำไมต้องทำก่อนขั้นถัดไป |
|---|---|---|
| 1. ดู IP ของเครื่อง | `ipconfig /all` | ไม่มี IP ที่ถูกต้อง → ทุกขั้นต่อไปล้มหมด เสียเวลาเปล่า |
| 2. ping gateway | `ping 10.0.20.1` | พิสูจน์ช่วงในวง (สาย/พอร์ต/VLAN/switch) ในคำสั่งเดียว |
| 3. ping IP ภายนอก | `ping 8.8.8.8` | พิสูจน์ routing + NAT + firewall + ISP โดย **ไม่เกี่ยวกับ DNS** |
| 4. ทดสอบ DNS | `nslookup` | แยกปัญหา "ชื่อ" ออกจาก "เส้นทาง" |
| 5. traceroute | `tracert -d` | ถ้าขั้น 3 ไม่ผ่าน → บอกว่าหายที่ hop ไหน |
| 6. ทดสอบ port | `Test-NetConnection -Port` | ping ผ่านไม่ได้แปลว่าแอปผ่าน (firewall/บริการ) |
| 7. ทดสอบ MTU | `ping -f -l 1472` | สำหรับอาการ "บางอย่างได้ บางอย่างค้าง" |
| 8. วัดคุณภาพ | `mtr`, `iperf3` | สำหรับอาการ "ช้า/กระตุก" |
| 9. ดูอุปกรณ์ใน path | interface → route → policy → session → debug | เมื่อรู้แล้วว่าติดช่วงไหน จึงไปดูอุปกรณ์ช่วงนั้น |

---

## 4. กรณีศึกษา A — พนักงานคนเดียวใช้เน็ตไม่ได้

**รับแจ้ง:** "คุณสมชาย ฝ่ายบัญชีชั้น 3 ใช้อะไรไม่ได้เลย เพื่อนข้าง ๆ ใช้ได้ปกติ เพิ่งย้ายโต๊ะมาเมื่อเช้า"
**วิเคราะห์จากคำถาม:** คนเดียว + ใช้อะไรไม่ได้ + **เพิ่งย้ายโต๊ะ** → สงสัยพอร์ต/สาย/VLAN

```
ขั้น 1  (เครื่องผู้ใช้) ipconfig /all
        IPv4 Address: 169.254.12.88     ← ไม่ได้ IP จาก DHCP
        → ปัญหาอยู่ระหว่างเครื่อง ↔ switch ↔ DHCP (ยังไม่ต้องดู firewall/internet)

ขั้น 2  หาพอร์ต: ดูหมายเลขที่หัวผนัง (เช่น 3F-045) → เทียบผังพอร์ต → SW-3F Gi1/0/22
        SW-3F# show interfaces status | include Gi1/0/22
        Gi1/0/22  Desk-3F-045   connected   99   a-full a-1000
                                            └ VLAN 99 = parking VLAN (พอร์ตที่ไม่ได้ใช้ถูกปิดไว้ใน VLAN นี้)

ขั้น 3  ยืนยัน: พอร์ตโต๊ะเดิมของคุณสมชายอยู่ VLAN 20 (บัญชี) แต่พอร์ตโต๊ะใหม่ยังเป็น VLAN 99

แก้     (ตาม standard change) ตั้ง Gi1/0/22 เป็น access VLAN 20 + description ใหม่
        SW-3F(config)# interface Gi1/0/22
        SW-3F(config-if)# switchport access vlan 20
        SW-3F(config-if)# description Desk-3F-045-Somchai-ACC

ยืนยัน  ipconfig /renew → ได้ 10.0.20.x ✅ · ping gateway ✅ · เปิด ERP ✅
ปิดงาน  บันทึกใน ticket + อัปเดตผังพอร์ต/NetBox
```
**บทเรียน:** IP `169.254.x.x` บอกได้ทันทีว่าไม่ต้องไปดูส่วนที่ไกลกว่า switch · "เพิ่งย้ายโต๊ะ" คือเบาะแสสำคัญ

---

## 5. กรณีศึกษา B — โทรศัพท์ IP ทั้งชั้น 2 ใช้ไม่ได้ แต่คอมพิวเตอร์ใช้ได้

**วิเคราะห์:** ทั้งชั้น + เฉพาะโทรศัพท์ (VLAN 30 VOICE) + คอมพิวเตอร์ (VLAN 20) ปกติ → ปัญหาเฉพาะ VLAN 30 บนเส้นทางของชั้น 2 · ถาม: มี change ล่าสุดไหม → "เมื่อคืนทีมเพิ่ม VLAN 40 กล้อง CCTV ที่ชั้น 2"

```
ขั้น 1  SW-2F# show interfaces trunk
        Port        Vlans allowed on trunk
        Gi1/0/48    40                          ← เหลือแค่ VLAN 40!

        (ควรเป็น 10,20,30,40)
        → เมื่อคืนมีคนพิมพ์  switchport trunk allowed vlan 40  (ไม่มีคำว่า add)
          แทนที่จะเป็น       switchport trunk allowed vlan add 40

ขั้น 2  แล้วทำไมคอมพิวเตอร์ยังใช้ได้? → ตรวจเพิ่ม:
        SW-2F# show interfaces trunk
        Port        Vlans allowed on trunk
        Gi1/0/47    10,20                       ← มี uplink อีกเส้นสำหรับ data ที่ไม่ได้ถูกแก้
        (ในเครือข่ายจริงอาจเป็น uplink เส้นเดียว ซึ่งจะทำให้ทุก VLAN ล่มยกเว้น 40)

แก้     SW-2F(config)# interface Gi1/0/48
        SW-2F(config-if)# switchport trunk allowed vlan 30,40     (ตรวจกับเอกสาร/NetBox ว่าควรมี VLAN อะไรบ้าง)
        (ทำฝั่ง core ให้ตรงกันด้วย)

ยืนยัน  show interfaces trunk → มี 30 แล้ว · โทรศัพท์ลงทะเบียนกลับมา · ทดสอบโทรออก
ป้องกัน  post-mortem: ใช้ template/automation สำหรับการแก้ trunk + ตรวจ diff ก่อน apply (Level 82/84)
```
**บทเรียน:** อาการ "เฉพาะ VLAN เดียว" ชี้ไปที่ trunk/VLAN · ถามเรื่อง change ช่วยประหยัดเวลามาก

---

## 6. กรณีศึกษา C — ทั้งบริษัทเข้าเว็บไม่ได้ แต่ระบบภายในใช้ได้

```
ขั้น 1  (เครื่องผู้ใช้) ping 8.8.8.8 → Request timed out
        nslookup google.com → ได้ IP กลับมา (DNS ภายในตอบจาก cache)
        → ไม่ใช่ปัญหา DNS แต่ "ออกนอก" ไม่ได้

ขั้น 2  tracert -d 8.8.8.8
          1  <1 ms  10.0.20.1        ← core
          2   1 ms  10.0.0.254       ← firewall
          3   *  *  *                ← หายหลัง firewall
        → ปัญหาที่ firewall หรือ ISP

ขั้น 3  (FortiGate) get system arp | grep wan1
        (ไม่มี gateway ของ ISP)                 ← firewall คุยกับ router ISP ไม่ได้เลย
        diagnose hardware deviceinfo nic wan1
        Link: down                              ← ❗ link ของ wan1 ล่ม

ขั้น 4  ทำไมไม่ failover ไป wan2?
        diagnose sys sdwan health-check status
        Seq(1 wan1): state(dead) ...
        Seq(2 wan2): state(dead) ...            ← wan2 ก็ dead?
        execute ping-options interface wan2 ... ping gateway ISP2 → ได้
        → health-check ของ wan2 ตั้ง target เป็น IP ที่ปิด ICMP ไปแล้ว ทำให้ระบบคิดว่า wan2 เสียด้วย

แก้      (เร่งด่วน) เปลี่ยน health-check target ของ wan2 เป็นปลายทางที่เชื่อถือได้ (ตาม emergency change)
         → ผู้ใช้ออกเน็ตทาง wan2 ได้ ✅
         แจ้ง ISP1 เรื่อง link down (เตรียม circuit ID) → ISP พบสายขาดหน้าอาคาร
ป้องกัน  health-check ใช้ target 2 แห่งขึ้นไป · alert เมื่อ member SD-WAN ใดตัวหนึ่ง dead · ทดสอบ failover ทุกไตรมาส (Level 93)
```
**บทเรียน:** redundancy ที่ไม่เคยทดสอบอาจใช้ไม่ได้จริง · ARP ของ gateway ISP บอกได้เร็วว่าปัญหาอยู่ที่ L1/L2 หรือไม่

---

## 7. กรณีศึกษา D — ผู้ใช้เข้า server ภายใน (ข้าม firewall) ไม่ได้

**รับแจ้ง:** "ทีม HR เข้าระบบ HRIS (10.0.100.40:443) ไม่ได้ ตั้งแต่เปิดระบบใหม่เมื่อวาน ฝ่ายอื่นเข้าได้"
```
ขั้น 1  (เครื่อง HR) Test-NetConnection 10.0.100.40 -Port 443
        TcpTestSucceeded : False  (timed out)   ← timeout = ถูก drop ระหว่างทาง (ไม่ใช่ refused)

ขั้น 2  (FortiGate) debug flow filter addr 10.0.100.40
        msg="received a packet(proto=6, 10.0.25.31:51001->10.0.100.40:443) from internal-hr. flag [S]"
        msg="find a route: ... via servers"
        msg="Denied by forward policy check (policy 0)"
        → ไม่มี policy อนุญาต internal-hr → servers ไปที่ HRIS

ขั้น 3  ตรวจ policy: มี policy "Users-to-HRIS" แต่ source address เป็น group "Office-Users"
        ซึ่งไม่ได้รวม subnet ของ HR (10.0.25.0/24) — HR อยู่ VLAN แยกเพราะข้อมูลอ่อนไหว

แก้      เพิ่ม 10.0.25.0/24 เข้า address group ที่เหมาะสม (หรือสร้าง policy สำหรับ HR) ตาม change process

ยืนยัน  Test-NetConnection → True · debug flow แสดง "Allowed by Policy-xx" · ผู้ใช้ login ได้
```
**ถ้า debug flow เห็น "Allowed" แต่ยังใช้ไม่ได้:** ดู session (`reply=0`?) → ปัญหาที่ server (Windows Firewall, บริการไม่ทำงาน, server ไม่มี route กลับไป 10.0.25.0/24)
**บทเรียน:** timeout ชี้ไปที่ firewall/route · debug flow ให้คำตอบตรงที่สุด

---

## 8. กรณีศึกษา E — VPN สาขาขึ้นแล้ว แต่บางเว็บ/บางงานค้าง

**รับแจ้ง:** "สาขาหาดใหญ่ เปิดหน้าแรก ERP ได้ แต่ดูรายงานแล้วค้าง ส่งไฟล์แนบไม่ได้ · ping ไป HQ ได้ปกติ"
**วิเคราะห์:** "ข้อมูลเล็กได้ ข้อมูลใหญ่ค้าง + ping ได้" = สัญญาณคลาสสิกของ **ปัญหา MTU**
```
ขั้น 1  (เครื่องผู้ใช้สาขา) ping -f -l 1472 10.0.100.25
        Packet needs to be fragmented but DF set.
        ping -f -l 1400 10.0.100.25 → ไม่มีคำตอบ (timeout)
        ping -f -l 1350 10.0.100.25 → Reply ✅
        → เส้นทางรับ packet ได้ราว 1350+28 = ~1378 bytes (เพราะ ISP สาขาใช้ PPPoE + IPsec overhead)

ขั้น 2  ทำไม 1400 ได้ "timeout" แทนข้อความ fragment? → อุปกรณ์กลางทางทิ้งเงียบ ๆ
        และ ICMP "fragmentation needed" ถูกบล็อก → เครื่องไม่รู้ว่าต้องลดขนาด (PMTUD black hole)

แก้      ตั้ง TCP MSS บน policy/interface ของ VPN ที่ FortiGate ทั้งสองฝั่ง เช่น tcp-mss-sender/receiver 1300
         (หรือ ip tcp adjust-mss บน Cisco)
ยืนยัน  ดูรายงาน/ส่งไฟล์แนบได้ ✅
ป้องกัน  ใส่การทดสอบ MTU ใน checklist ส่งมอบสาขาใหม่ + ใส่ MSS ใน template config
```
**บทเรียน:** "ping ได้" ไม่ได้แปลว่า network ปกติ — ทดสอบด้วย packet ขนาดใหญ่ด้วย

---

## 9. กรณีศึกษา F — เน็ตช้าเฉพาะช่วงบ่าย ทั้งสาขา

```
ขั้น 1  ถาม: ช้าตั้งแต่ประมาณ 13:00–16:00 ทุกวัน, ทุกแอป, ทั้งสาขาเชียงใหม่
        → อาการตามเวลา = สงสัย congestion (มีอะไรใช้แบนด์วิดท์ช่วงนั้น)

ขั้น 2  ดูกราฟ monitoring ของ wan1 สาขา: 13:00–16:00 upload เต็ม 100% (ลิงก์ 100 Mbps)

ขั้น 3  ใครใช้? ดู flow/FortiView (Top Sources/Applications) ช่วงเวลานั้น
        10.1.40.20 (NVR กล้อง CCTV) → อัปโหลดไป cloud storage 85 Mbps
        → ระบบกล้องใหม่ตั้งค่าให้ sync วิดีโอขึ้น cloud ช่วงบ่าย

ขั้น 4  mtr ไป HQ ช่วงบ่าย: latency 20 ms → 250 ms, loss 3%  (ยืนยันว่าลิงก์เต็มทำให้ทุกอย่างช้า)

แก้      ระยะสั้น: traffic shaping จำกัด NVR ไม่เกิน 20 Mbps + ตั้ง QoS ให้ ERP/voice ก่อน (Level 54)
         ระยะยาว: ย้ายเวลา sync เป็นกลางคืน / เพิ่ม bandwidth ถ้าธุรกิจต้องการ (Level 94)
ยืนยัน  กราฟ upload ไม่เต็ม · mtr ช่วงบ่าย latency กลับมาปกติ · ผู้ใช้ยืนยัน
```
**บทเรียน:** "ช้า" ต้องดู **ข้อมูลย้อนหลัง** (กราฟ, flow) ไม่ใช่ทดสอบตอนที่ไม่ช้า · ซื้อ bandwidth เพิ่มไม่ใช่คำตอบแรกเสมอไป

---

## 10. หาเครื่องจาก IP — ทำไมต้องไล่ ARP → MAC → พอร์ต

```
 IP (Layer 3) → รู้แค่ "ใคร" ไม่รู้ "อยู่ตรงไหน"
 router/L3 switch รู้ว่า IP นี้คือ MAC อะไร (ตาราง ARP)
 switch รู้ว่า MAC นี้อยู่พอร์ตไหน (ตาราง MAC) — แต่พอร์ตนั้นอาจเป็นสายที่ต่อไป switch อื่น
 → ตามสาย (CDP/LLDP) ไปเรื่อย ๆ จนเจอพอร์ตที่มี MAC นั้นตัวเดียว = ตำแหน่งจริงของเครื่อง
```
ใช้บ่อยเมื่อ: เครื่องติดมัลแวร์ต้องตัดออก, IP ชนกัน, หาเจ้าของอุปกรณ์แปลกปลอม (รายละเอียดคำสั่งใน [อธิบาย Cisco ข้อ 4](02-cisco-explained.md))

---

## 11. Checklist ก่อนบอกว่า "Network ไม่ผิด" — อธิบายแต่ละข้อ

| ข้อ | ทำไมต้องตรวจ |
|---|---|
| ทดสอบจาก **ต้นทางจริง** | เครื่องของเราอาจอยู่คนละ VLAN/policy กับผู้ใช้ ผลจึงต่างกัน |
| traceroute **ทั้งสองทิศ** | ขาไปอาจปกติแต่ขากลับไปทางอื่น (asymmetric) |
| firewall: policy, session มี reply, ไม่มี drop | ยืนยันว่า firewall ไม่ได้บล็อกและมีขากลับ |
| interface ไม่มี error/drop เพิ่ม, ไม่เต็ม | ตัดปัญหาสายเสียและ congestion |
| DNS ได้ IP ถูก | ชื่อเดียวกันอาจได้ IP ผิด (cache เก่า/split DNS) |
| MTU ผ่านด้วย packet เต็มขนาด | ตัดปัญหา "เล็กได้ ใหญ่ค้าง" |
| เวลาของอุปกรณ์ตรงกัน | เวลาไม่ตรง → cert/VPN/802.1X ล้ม และ log เทียบกันไม่ได้ |
| บันทึกหลักฐาน | เมื่อส่งต่อทีมแอป/server/ISP จะมีข้อมูลยืนยัน ไม่ต้องเถียงกัน |

### ตัวอย่างการสื่อสารผลกับทีมอื่น (ดีกว่าบอกว่า "network ปกติ")
> "ทดสอบจากเครื่องผู้ใช้ 10.0.25.31 ไป 10.0.100.40:443 เวลา 10:42 — TCP เชื่อมต่อสำเร็จ, firewall อนุญาตด้วย policy 31, session มีข้อมูลขากลับ 245 KB, ไม่มี packet loss (mtr 100 รอบ) · แต่หน้าเว็บตอบ HTTP 500 หลัง login (ดูจาก curl -v) จึงน่าจะเป็นปัญหาที่แอปพลิเคชัน รบกวนทีมแอปตรวจ log ของ HRIS ช่วง 10:42 ครับ"

---

## 12. แบบฝึกหัด: ลองวิเคราะห์เอง

1. ผู้ใช้ได้ IP ถูกต้อง ping gateway ได้ ping 8.8.8.8 ได้ แต่เข้าเว็บด้วยชื่อไม่ได้ — ปัญหาน่าจะเป็นอะไร ทดสอบอะไรต่อ
2. ทุกคนในชั้น 4 หลุดเป็นช่วง ๆ ทุก 2–3 นาที `show spanning-tree detail` แสดง topology change หลายพันครั้ง — สงสัยอะไร
3. Test-NetConnection ไป server ได้ผล "refused" — ปัญหาน่าจะอยู่ฝั่งไหน
4. VPN ขึ้น, FortiGate HQ เห็น enc เพิ่มแต่ dec = 0 — ตรวจอะไรที่ไหน
5. ผู้ใช้บอกว่า "ช้า" แต่ตอนคุณไปตรวจทุกอย่างปกติ — ทำอย่างไร

<details><summary><b>เฉลย</b></summary>

1. DNS — `nslookup` ดูว่า DNS server ที่เครื่องใช้ตอบไหม/ตอบถูกไหม, ลองถาม DNS อีกตัว, ตรวจ firewall port 53
2. Loop หรือพอร์ตที่ขึ้นลงถี่ (อุปกรณ์ที่ไม่ได้ตั้ง PortFast, สายหลวม, มีคนเสียบ switch/hub) — ดูพอร์ตที่บรรทัด "from" ชี้ แล้วตรวจ log MAC flapping
3. ถึงเครื่องปลายทางแล้วแต่บริการไม่ได้ฟัง port นั้น (บริการหยุด/port ผิด) หรือ firewall ของเครื่องปฏิเสธ — ฝั่ง server
4. อีกฝั่ง (สาขา): tunnel/selector ตรงไหม, policy ขาเข้าจาก VPN, route กลับไป HQ ผ่าน VPN, ไม่มีการ NAT traffic VPN — ใช้ debug flow ที่สาขา
5. เก็บข้อมูลต่อเนื่อง: กราฟ utilization ย้อนหลัง, mtr/smokeping ที่รันทิ้งไว้, ให้ผู้ใช้จดเวลาที่ช้า แล้วเทียบกับข้อมูลช่วงนั้น
</details>

---

⬅️ [Palo Alto / Check Point](04-paloalto-checkpoint-explained.md) · 🏠 [กลับหน้ารวม Cheat Sheets](../README.md)
