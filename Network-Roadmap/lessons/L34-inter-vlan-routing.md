# บทเรียน Level 34 — Inter-VLAN Routing (ฉบับละเอียด)

> อ่านจบแล้วจะ: ทำให้เครื่องต่าง VLAN คุยกันได้ 3 วิธี (Legacy, Router-on-a-Stick, L3 Switch SVI) · เข้าใจ routed port · ตัดสินใจว่าจะวาง gateway ไว้ที่ L3 switch หรือ firewall · แก้ปัญหา inter-VLAN ได้

---

## 1. ทำไมต้องมี Inter-VLAN Routing

VLAN แยก broadcast domain → เครื่องต่าง VLAN อยู่คนละ subnet → **คุยกันต้องผ่านอุปกรณ์ Layer 3** ที่ทำหน้าที่เป็น **default gateway** ของแต่ละ VLAN

```
 PC-A VLAN 10 (10.0.10.50, GW 10.0.10.1) ──X── PC-B VLAN 20 (10.0.20.50, GW 10.0.20.1)
                      ↘                        ↗
                    [ อุปกรณ์ L3 มี IP 10.0.10.1 และ 10.0.20.1 ]
```

---

## 2. วิธีที่ 1: Legacy (พอร์ตละ VLAN)

```
           Router
       G0/0      G0/1
        │          │
   (access VLAN10)(access VLAN20)
        └──[ SWITCH ]──┘
```
- Router ใช้ 1 interface ต่อ 1 VLAN
- ❌ เปลืองพอร์ตทั้ง router และ switch · VLAN มากก็ทำไม่ได้ → **ไม่ใช้แล้ว** (รู้ไว้เป็นพื้นฐาน)

---

## 3. วิธีที่ 2: Router-on-a-Stick (ROAS)

```
            Router
              │ G0/0 (แบ่งเป็น subinterface)
              │   G0/0.10 → 10.0.10.1  (VLAN 10)
              │   G0/0.20 → 10.0.20.1  (VLAN 20)
          TRUNK (802.1Q)
              │
        [   SWITCH   ]
        /            \
   PC VLAN 10      PC VLAN 20
```
- สาย **trunk เส้นเดียว** ไป router และแบ่ง interface ของ router เป็น **subinterface** ต่อ VLAN
- Traffic จาก VLAN 10 ไป VLAN 20 วิ่ง **ขึ้น trunk ไป router แล้ววิ่งกลับลงมาบน trunk เดียวกัน**

### Config
```
! Router
interface GigabitEthernet0/0
 no shutdown                                ! physical ต้อง up ก่อน
interface GigabitEthernet0/0.10
 encapsulation dot1Q 10
 ip address 10.0.10.1 255.255.255.0
interface GigabitEthernet0/0.20
 encapsulation dot1Q 20
 ip address 10.0.20.1 255.255.255.0
interface GigabitEthernet0/0.99
 encapsulation dot1Q 99 native              ! ถ้าต้องการให้ subinterface นี้รับ untagged (native)
 ip address 10.0.99.1 255.255.255.0
! Switch
interface Gi1/0/48
 switchport mode trunk
 switchport trunk allowed vlan 10,20,99
```
### ข้อดี / ข้อเสีย
- ✅ ใช้พอร์ตเดียว ราคาถูก ใช้ router/firewall ที่มีอยู่ได้ (firewall หลายยี่ห้อทำแบบเดียวกันด้วย VLAN subinterface)
- ❌ **ลิงก์เดียวเป็นคอขวด** (traffic ข้าม VLAN วิ่งสองรอบบนสายเดียว) และเป็น **single point of failure**
- 📍 เหมาะกับ **สาขาเล็ก/สำนักงานเล็ก** หรือเมื่อต้องการให้ firewall ตรวจทุก traffic ข้าม VLAN

---

## 4. วิธีที่ 3: L3 Switch + SVI ⭐ (มาตรฐานองค์กร)

**SVI (Switch Virtual Interface)** = interface เสมือนของ VLAN บน L3 switch ทำหน้าที่เป็น gateway — routing ทำใน **ฮาร์ดแวร์ (ASIC)** จึงเร็วเท่า wire-speed

```
        [ L3 SWITCH ]
     interface vlan 10 → 10.0.10.1
     interface vlan 20 → 10.0.20.1
        /           \
   PC VLAN 10     PC VLAN 20     (routing เกิดภายใน switch ไม่ต้องออกไปที่อื่น)
```
### Config
```
ip routing                                   ! ⚠️ ลืมบ่อยที่สุด — ไม่เปิดจะไม่ route
!
vlan 10
 name USERS
vlan 20
 name SERVERS
!
interface vlan 10
 description GW-USERS
 ip address 10.0.10.1 255.255.255.0
 ip helper-address 10.0.20.10                ! DHCP relay (Level 15)
 no shutdown
interface vlan 20
 description GW-SERVERS
 ip address 10.0.20.1 255.255.255.0
 no shutdown
!
show ip interface brief | include Vlan
show ip route connected
```

### เงื่อนไขที่ SVI จะ up/up
1. VLAN นั้น **ถูกสร้างแล้ว** (อยู่ใน `show vlan`)
2. มี **อย่างน้อย 1 พอร์ต** ใน VLAN นั้น (access หรือ trunk ที่ allow VLAN) **อยู่ในสถานะ up** และ forwarding
3. SVI ไม่ได้ `shutdown`
(ถ้า SVI ขึ้น `down/down` ให้ตรวจ 3 ข้อนี้)

### ข้อดี / ข้อเสีย
- ✅ เร็วมาก, ไม่มีคอขวดลิงก์เดียว, ขยายได้, ทำ HSRP/VRRP คู่ได้ (Level 50)
- ❌ traffic ข้าม VLAN **ไม่ผ่าน firewall** — ต้องควบคุมด้วย ACL บน switch (stateless) หรือออกแบบให้ VLAN ที่สำคัญไปผ่าน firewall

---

## 5. Routed Port (No Switchport)

แปลงพอร์ตของ L3 switch ให้เป็น **พอร์ต router จริง** (ไม่อยู่ใน VLAN ใด)
```
interface GigabitEthernet1/0/1
 description P2P-TO-CORE
 no switchport
 ip address 10.255.0.1 255.255.255.252
```
- ใช้กับ **ลิงก์ L3 point-to-point** ระหว่าง switch (เช่น access ↔ distribution แบบ routed access, หรือ switch ↔ firewall)
- ไม่มี STP บนลิงก์นี้, converge ด้วย routing protocol

| | SVI | Routed Port |
|---|---|---|
| ผูกกับ | VLAN (หลายพอร์ต) | พอร์ตเดียว |
| ใช้เป็น | gateway ของผู้ใช้ใน VLAN | ลิงก์ L3 ระหว่างอุปกรณ์ |
| STP | มี (ใน VLAN) | ไม่มี |

---

## 6. ควรวาง Gateway ไว้ที่ไหน? (การตัดสินใจออกแบบ)

| ตัวเลือก | ข้อดี | ข้อเสีย | เหมาะกับ |
|---|---|---|---|
| **L3 core/distribution switch** | เร็ว, ขยายได้, HA ง่าย | ข้าม VLAN ไม่ผ่าน firewall (ACL stateless) | VLAN ผู้ใช้ทั่วไปที่ระดับความเสี่ยงเท่ากัน |
| **Firewall (VLAN subinterface)** | ตรวจทุก traffic ข้าม zone, log, IPS | firewall ต้องแรงพอ, อาจเป็นคอขวด | Guest, IoT, CCTV, Server, DMZ, Management |
| **ผสม (นิยม)** | ได้ทั้งเร็วและปลอดภัย | ซับซ้อนขึ้น | องค์กรส่วนใหญ่ |

**รูปแบบผสมที่พบบ่อย**
```
 VLAN ผู้ใช้หลายแผนก → gateway ที่ core switch (routing เร็ว) อยู่ใน VRF/zone "USER"
 Guest / IoT / CCTV / Servers → gateway ที่ firewall (ตรวจ policy ระหว่าง zone)
 core switch ↔ firewall เชื่อมด้วย routed link หรือ transit VLAN + static/OSPF
```

### ACL บน SVI (ตัวอย่างเบื้องต้น — รายละเอียด Level 53)
```
ip access-list extended GUEST-IN
 permit udp any any eq 53
 deny   ip any 10.0.0.0 0.255.255.255          ! ห้ามเข้าเครือข่ายภายใน
 permit ip any any                             ! ออก internet ได้
interface vlan 50
 ip access-group GUEST-IN in
```

---

## 7. Packet ข้าม VLAN เดินทางอย่างไร (L3 switch)

```
 PC-A (VLAN10 10.0.10.50) ส่งถึง PC-B (VLAN20 10.0.20.50)
 1) PC-A: ปลายทางอยู่นอกวง → ARP หา MAC ของ gateway 10.0.10.1 (SVI VLAN10)
 2) ส่ง frame: Dst MAC = MAC ของ SVI, Dst IP = 10.0.20.50
 3) L3 switch: route จาก VLAN10 → VLAN20 (connected) → ARP หา MAC ของ 10.0.20.50 ใน VLAN20
 4) สร้าง frame ใหม่: Src MAC = MAC ของ SVI VLAN20, Dst MAC = PC-B → ส่งออกพอร์ตของ PC-B
 TTL ลดลง 1 · traceroute จาก PC-A เห็น hop แรกเป็น 10.0.10.1
```

---

## 8. แก้ปัญหา Inter-VLAN Routing

```
 1) PC: IP/mask/gateway ถูกต้อง? gateway เป็น IP ของ SVI/subinterface ของ VLAN นั้น?
 2) ping gateway ของตัวเองได้ไหม?
      ไม่ได้ → ปัญหา L2: พอร์ตผิด VLAN, VLAN ไม่อยู่บน trunk, SVI down
 3) ping gateway ของอีก VLAN ได้ไหม?
 4) L3 switch: show ip route → มี connected route ของทั้งสองวง? "ip routing" เปิดหรือยัง?
 5) SVI up/up? (show ip interface brief)
 6) ACL บน SVI/firewall บล็อกหรือไม่?
 7) ปลายทางมี gateway ถูกต้องไหม (ขากลับ!) และ firewall ในเครื่องปลายทางบล็อกหรือไม่?
```
> 🔑 ปัญหาที่พบบ่อย: **เครื่องปลายทางไม่มี default gateway หรือ gateway ผิด** — ข้อมูลไปถึงแต่ตอบกลับไม่ได้

---

## 9. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| L3 switch route ได้ทันทีที่สร้าง SVI | ต้อง `ip routing` |
| SVI up เสมอเมื่อ no shutdown | ต้องมี VLAN และพอร์ตใน VLAN ที่ up |
| Router-on-a-stick ใช้ในองค์กรใหญ่ได้ดี | ลิงก์เดียวเป็นคอขวดและจุดเสีย |
| Routing ข้าม VLAN บน L3 switch ผ่าน firewall | ไม่ผ่าน ต้องควบคุมด้วย ACL หรือออกแบบให้ไปที่ firewall |

---

## 10. Cheat Sheet

```
ต่าง VLAN = ต่าง subnet = ต้องผ่าน L3 (gateway)
Legacy: พอร์ตละ VLAN (เลิกใช้)
ROAS: trunk + subinterface (encapsulation dot1Q N) · คอขวด/SPOF · สาขาเล็ก
L3 switch: ip routing + interface vlan N + ip address · เร็ว (ASIC) · มาตรฐานองค์กร
SVI up เมื่อ: VLAN มีอยู่ + มีพอร์ตใน VLAN up + no shutdown
Routed port: no switchport + ip address (ลิงก์ L3 P2P)
Gateway ที่ switch (เร็ว) vs firewall (ตรวจ policy) → นิยมผสม
ปัญหาบ่อย: ลืม ip routing · SVI down · ACL · ปลายทางไม่มี gateway
```

---

## 11. แบบทดสอบ 10 ข้อ

1. ทำไมเครื่องต่าง VLAN จึงต้องผ่านอุปกรณ์ L3
2. Router-on-a-stick ใช้อะไรบน router และอะไรบน switch
3. คำสั่ง subinterface สำหรับ VLAN 30 IP 10.0.30.1/24
4. ข้อเสียหลักของ router-on-a-stick
5. คำสั่งที่มักลืมบน L3 switch ทำให้ route ไม่ได้
6. SVI แสดง down/down ตรวจอะไรบ้าง
7. Routed port ต่างจาก SVI อย่างไร ใช้เมื่อไร
8. ทำไมหลายองค์กรวาง gateway ของ Guest/IoT ไว้ที่ firewall
9. PC VLAN10 ping gateway ตัวเองได้ แต่ ping server VLAN20 ไม่ได้ ทั้งที่ L3 switch มี route ครบ ควรตรวจอะไร
10. เมื่อ packet ถูก route ข้าม VLAN บน L3 switch MAC และ TTL เปลี่ยนอย่างไร

<details><summary><b>เฉลย</b></summary>

1. ต่าง VLAN คือคนละ broadcast domain/subnet ต้องใช้ routing ผ่าน gateway
2. Router ใช้ subinterface ต่อ VLAN (encapsulation dot1Q); switch ใช้พอร์ต trunk
3. `interface G0/0.30` → `encapsulation dot1Q 30` → `ip address 10.0.30.1 255.255.255.0`
4. ลิงก์เดียวเป็นคอขวด (traffic ข้าม VLAN วิ่งสองรอบ) และเป็น single point of failure
5. `ip routing`
6. VLAN ถูกสร้างหรือยัง, มีพอร์ตใน VLAN ที่ up (access/trunk ที่ allow), SVI ถูก shutdown หรือไม่
7. Routed port คือพอร์ตเดียวที่เป็น L3 (no switchport) ใช้กับลิงก์ P2P ระหว่างอุปกรณ์; SVI คือ interface ของ VLAN ใช้เป็น gateway ของผู้ใช้หลายพอร์ต
8. ให้ทุก traffic ข้าม zone ผ่าน stateful firewall ตรวจ/บันทึก/IPS ได้ ซึ่ง ACL บน switch ทำได้จำกัด
9. ACL บน SVI, gateway/route ของ server (ขากลับ), firewall ในเครื่อง server, server ทำงานอยู่ไหม
10. MAC ต้นทาง/ปลายทางถูกสร้างใหม่ (MAC ของ SVI ฝั่ง VLAN20 → MAC ของปลายทาง) และ TTL ลดลง 1; IP คงเดิม
</details>

---

➡️ ต่อไป: **Level 35 — Spanning Tree Protocol (STP)**
