# บทเรียน Level 41 — Routing Table & Static Routing (ฉบับละเอียด)

> อ่านจบแล้วจะ: อ่าน routing table ได้ทุกบรรทัด · เข้าใจกฎ 3 ข้อที่ router ใช้เลือก route (Longest match → AD → Metric) · ตั้ง static route แบบต่าง ๆ · เข้าใจ recursive lookup และ summary/null route · แก้ปัญหา routing พื้นฐาน

---

## 1. Routing คืออะไร

**Routing** คือการที่ router ตัดสินใจว่า packet ที่มี **IP ปลายทาง** นี้ ควรส่งออก **interface ไหน** และส่งต่อให้ **ใคร (next hop)** โดยเปิดดู **routing table**

> 💡 **เปรียบเทียบ:** routing table คือ **ป้ายบอกทางที่ทางแยก** — router ไม่รู้เส้นทางทั้งหมดจนถึงปลายทาง รู้แค่ว่า "ไปที่นั่นให้เลี้ยวทางนี้แล้วส่งต่อให้คนถัดไป" (hop-by-hop)

### Router ได้ route มาจาก 3 แหล่ง
1. **Connected** — วงที่ interface ของตัวเองต่ออยู่ (ได้อัตโนมัติเมื่อ interface up และมี IP)
2. **Static** — ผู้ดูแลกำหนดเอง
3. **Dynamic** — เรียนรู้จาก routing protocol (OSPF, EIGRP, BGP, RIP)

---

## 2. อ่าน Routing Table (Cisco)

```
R1# show ip route
Codes: L - local, C - connected, S - static, R - RIP, O - OSPF, D - EIGRP,
       B - BGP, O IA - OSPF inter area, * - candidate default ...

Gateway of last resort is 203.0.113.1 to network 0.0.0.0

S*    0.0.0.0/0 [1/0] via 203.0.113.1
      10.0.0.0/8 is variably subnetted, 5 subnets, 3 masks
C        10.0.10.0/24 is directly connected, GigabitEthernet0/1
L        10.0.10.1/32 is directly connected, GigabitEthernet0/1
O        10.0.20.0/24 [110/2] via 10.255.0.2, 00:15:32, GigabitEthernet0/2
S        10.50.0.0/16 [1/0] via 10.255.0.6
D        172.16.0.0/16 [90/3072] via 10.255.0.2, 01:02:11, GigabitEthernet0/2
```
| ส่วน | ความหมาย |
|---|---|
| `O` | แหล่งที่มา (OSPF) |
| `10.0.20.0/24` | วงปลายทาง (prefix) |
| `[110/2]` | **[Administrative Distance / Metric]** |
| `via 10.255.0.2` | **next hop** (ส่งต่อให้ใคร) |
| `00:15:32` | เรียนรู้มานานเท่าไร |
| `GigabitEthernet0/2` | interface ขาออก |
| `L ... /32` | **Local** — IP ของ interface ตัวเอง |
| `S*` | static ที่เป็น **default route** (candidate default) |

---

## 3. Router เลือก Route อย่างไร — กฎ 3 ข้อ (สำคัญมาก)

### กฎที่ 1: Longest Prefix Match (ชนะเสมอ)
หา route ที่ **ตรงกับ IP ปลายทาง และ prefix ยาวที่สุด** (เจาะจงที่สุด)
```
 routing table: 10.0.0.0/8 via A · 10.1.0.0/16 via B · 10.1.1.0/24 via C · 0.0.0.0/0 via D
 ปลายทาง 10.1.1.5   → ตรงทั้ง /8, /16, /24, /0 → เลือก /24 → ส่งให้ C
 ปลายทาง 10.1.9.9   → ตรง /8, /16, /0          → เลือก /16 → ส่งให้ B
 ปลายทาง 10.200.0.1 → ตรง /8, /0               → เลือก /8  → ส่งให้ A
 ปลายทาง 8.8.8.8    → ตรงแค่ /0                 → default → ส่งให้ D
```

### กฎที่ 2: Administrative Distance (AD) — ใช้เมื่อ prefix **เท่ากันทุกตัว** แต่มาจากคนละแหล่ง
AD = "ความน่าเชื่อถือของแหล่งที่มา" **ต่ำกว่า = เชื่อมากกว่า**

| แหล่ง | AD |
|---|---|
| Connected | **0** |
| Static | **1** |
| eBGP | 20 |
| EIGRP (internal) | 90 |
| OSPF | **110** |
| IS-IS | 115 |
| RIP | 120 |
| EIGRP external | 170 |
| iBGP | 200 |
| ไม่น่าเชื่อถือ (ไม่ใช้) | 255 |

ตัวอย่าง: 10.0.20.0/24 เรียนจากทั้ง OSPF (110) และ EIGRP (90) → **EIGRP ลง routing table**

### กฎที่ 3: Metric — ใช้เมื่อมาจาก **protocol เดียวกัน prefix เท่ากัน**
เลือก metric ต่ำสุด (OSPF = cost, EIGRP = composite metric, RIP = hop) ถ้าเท่ากันทุกอย่าง → **ECMP** ใช้หลายเส้นพร้อมกัน

> 🔑 **ลำดับ:** Longest match **ก่อน** AD เสมอ — route /24 จาก RIP (AD 120) ชนะ route /16 จาก static (AD 1) สำหรับปลายทางที่อยู่ใน /24 นั้น

---

## 4. Static Route

```
ip route <ปลายทาง> <mask> <next-hop | exit-interface> [AD] [name ...]
```

### 3 รูปแบบ
```
! 1) Next-hop IP (นิยมที่สุด)
ip route 10.50.0.0 255.255.0.0 10.255.0.6

! 2) Exit interface (เหมาะกับลิงก์ point-to-point เช่น serial/tunnel)
ip route 10.50.0.0 255.255.0.0 Tunnel1

! 3) Fully specified (interface + next-hop) — แนะนำบน Ethernet
ip route 10.50.0.0 255.255.0.0 GigabitEthernet0/2 10.255.0.6
```
> ⚠️ **ห้ามใช้ exit-interface อย่างเดียวบน Ethernet (multi-access)** — router จะถือว่าทุกปลายทางอยู่ติดกัน ต้อง ARP หาทุก IP ปลายทาง พึ่ง proxy ARP ของ router อีกฝั่ง ทำให้ ARP table ใหญ่และทำงานผิดพลาดได้

### Default Route
```
ip route 0.0.0.0 0.0.0.0 203.0.113.1          ! ทุกปลายทางที่ไม่มี route เจาะจง → ISP
```
**IPv6:** `ipv6 route ::/0 2001:db8:ffff::1`

### Recursive Lookup
Static route ที่ชี้ next-hop ซึ่ง **ไม่ได้ต่อตรง** → router ต้องหา route ไปยัง next-hop นั้นอีกรอบ
```
 ip route 10.50.0.0/16 via 172.16.1.1  (172.16.1.1 ไม่ใช่ connected)
 → lookup 172.16.1.1 → พบ 172.16.0.0/16 via 10.255.0.2 (connected) → ส่งออกทางนั้น
```

### Host Route และ Summary/Null Route
```
ip route 10.9.9.9 255.255.255.255 10.255.0.6            ! /32 host route
ip route 10.11.0.0 255.255.0.0 Null0                    ! ทิ้ง traffic ที่ไปวงในสรุปซึ่งไม่มีจริง
```
**Null0** ใช้คู่กับ summary route เพื่อป้องกัน routing loop (Level 10) และใช้ "ทิ้ง" traffic ที่ไม่ต้องการ

---

## 5. ข้อดี / ข้อเสีย ของ Static Route

| ✅ ข้อดี | ❌ ข้อเสีย |
|---|---|
| ง่าย คาดเดาได้ | ไม่ปรับเองเมื่อเส้นทางเสีย (ต้องใช้ IP SLA/track — Level 42) |
| ไม่กิน CPU/bandwidth | ดูแลยากเมื่อเครือข่ายใหญ่ (ต้องแก้ทุก router) |
| ปลอดภัย (ไม่มีการแลก route) | ตั้งผิดง่าย (routing loop, blackhole) |

**ใช้เมื่อ:** stub network (สาขาที่มีทางออกทางเดียว), default route ไป ISP, route ไปยัง VPN/partner, เครือข่ายเล็ก, route สำรอง (floating static)

---

## 6. อย่าลืม "ทางกลับ"

```
 PC-A 10.0.10.5 ── R1 ── R2 ── R3 ── Server 10.0.30.5
 R1 มี route ไป 10.0.30.0/24 ✅ → packet ไปถึง server
 แต่ R3 ไม่มี route กลับไป 10.0.10.0/24 ❌ → reply หาย
 อาการ: ping ไม่ผ่าน ทั้งที่ "route ฝั่งไปถูกแล้ว"
```
> 🔑 Routing ต้องถูกต้อง **ทั้งสองทิศทาง** ทุก router บนเส้นทางต้องรู้ทั้งทางไปและทางกลับ

---

## 7. คำสั่งที่ใช้แก้ปัญหา

```
show ip route                         ! ทั้งหมด
show ip route 10.0.30.5               ! router จะใช้ route ไหนกับ IP นี้ (เลือกตาม longest match)
show ip route static / connected / ospf
show ip route summary
show ip cef 10.0.30.5                 ! ตาราง forwarding จริง (FIB)
traceroute 10.0.30.5
ping 10.0.30.5 source 10.0.10.1       ! ทดสอบจาก IP ต้นทางที่ระบุ (ทดสอบทางกลับ)
```
**Linux:** `ip route`, `ip route get 10.0.30.5` · **Windows:** `route print`, `Find-NetRoute -RemoteIPAddress 10.0.30.5`

---

## 8. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| AD ต่ำกว่าชนะเสมอ | **Longest prefix ชนะก่อน**; AD ใช้เมื่อ prefix เท่ากัน |
| Static route ตั้งฝั่งเดียวพอ | ต้องมี route ทางกลับด้วย |
| Exit interface บน Ethernet ใช้ได้ดี | ควรใช้ next-hop หรือ fully specified |
| Router รู้เส้นทางทั้งหมดถึงปลายทาง | รู้แค่ hop ถัดไป (hop-by-hop) |

---

## 9. Cheat Sheet

```
แหล่ง route: Connected (C/L) · Static (S) · Dynamic (O/D/B/R)
[AD/metric] · via next-hop · S* = default (gateway of last resort)
เลือก: 1) Longest prefix match → 2) AD ต่ำสุด → 3) Metric ต่ำสุด (เท่ากัน = ECMP)
AD: Connected 0 · Static 1 · eBGP 20 · EIGRP 90 · OSPF 110 · IS-IS 115 · RIP 120 · iBGP 200
ip route NET MASK NEXTHOP · ip route 0.0.0.0 0.0.0.0 GW · ip route SUMMARY Null0
บน Ethernet ใช้ next-hop/fully specified · ทางกลับต้องมี route
show ip route X · ping X source Y · traceroute
```

---

## 10. แบบทดสอบ 10 ข้อ

1. Router ได้ route จาก 3 แหล่งใดบ้าง
2. `[110/20]` ใน routing table หมายถึงอะไร
3. มี route 10.0.0.0/8 (static) และ 10.1.0.0/16 (OSPF) ปลายทาง 10.1.5.5 ใช้ route ใด เพราะอะไร
4. 172.16.1.0/24 เรียนได้จากทั้ง OSPF และ EIGRP ตัวใดลง table
5. AD ของ static และ OSPF คือเท่าไร
6. คำสั่ง static route ไป 192.168.50.0/24 ผ่าน next-hop 10.0.0.2
7. ทำไมไม่ควรใช้ static route ที่ระบุแค่ exit interface บน Ethernet
8. Recursive lookup คืออะไร
9. ping จาก PC ไป server ไม่ผ่าน ทั้งที่ router ฝั่ง PC มี route ไป server ครบ ควรตรวจอะไร
10. Null0 route ใช้ทำอะไร

<details><summary><b>เฉลย</b></summary>

1. Connected, Static, Dynamic (routing protocol)
2. AD = 110 (OSPF), metric (cost) = 20
3. 10.1.0.0/16 — longest prefix match ชนะก่อนพิจารณา AD
4. EIGRP (AD 90 < OSPF 110)
5. Static = 1, OSPF = 110
6. `ip route 192.168.50.0 255.255.255.0 10.0.0.2`
7. Router จะ ARP หาทุกปลายทางเหมือนอยู่ติดกัน พึ่ง proxy ARP ทำให้ ARP table ใหญ่และอาจทำงานผิด
8. การ lookup routing table ซ้ำเพื่อหาเส้นทางไปยัง next-hop ที่ไม่ได้ต่อตรง
9. Route ทางกลับ (router ฝั่ง server ต้องรู้ทางกลับไปวงของ PC) และ gateway ของ server, ACL/firewall
10. ทิ้ง traffic ที่ไปยังวงในช่วง summary ที่ไม่มีอยู่จริง ป้องกัน routing loop/ทิ้ง traffic ที่ไม่ต้องการ
</details>

---

➡️ ต่อไป: **Level 42 — Default Route, Floating Static & IP SLA**
