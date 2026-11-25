# บทเรียน Level 42 — Default Route, Floating Static & IP SLA (ฉบับละเอียด)

> อ่านจบแล้วจะ: ตั้ง default route และกระจายให้ router ภายในได้ · ทำ dual-ISP failover ด้วย floating static · รู้ว่าทำไมต้องใช้ IP SLA + track · ทำ policy-based routing แบ่ง traffic ตาม ISP · เข้าใจผลกระทบของ failover ต่อ NAT/session

---

## 1. Default Route

**Default route (0.0.0.0/0)** = "ปลายทางใดก็ตามที่ไม่มี route เจาะจง ให้ส่งไปที่นี่" — เป็น **gateway of last resort**

```
ip route 0.0.0.0 0.0.0.0 203.0.113.1         ! IPv4
ipv6 route ::/0 2001:db8:ffff::1             ! IPv6
```
- ใช้ที่ **router ขอบ (edge)** ชี้ไป ISP และที่ **สาขา/stub network** ชี้ไปสำนักงานใหญ่
- เพราะเป็น /0 (prefix สั้นที่สุด) จึงถูกเลือก **เป็นอันดับสุดท้าย** ตามกฎ longest match

### กระจาย Default Route ให้ router ภายใน (ผ่าน routing protocol)
```
router ospf 1
 default-information originate              ! ประกาศ default เมื่อ router นี้มี default ใน table
 default-information originate always       ! ประกาศแม้ไม่มี default (ระวัง: อาจดึง traffic มาทิ้ง)
```
router ภายในจะเห็น `O*E2 0.0.0.0/0` แล้วส่ง traffic อินเทอร์เน็ตมาที่ edge router

---

## 2. Dual ISP — ทำไมต้องมีสอง

ธุรกิจสมัยใหม่ใช้ cloud/SaaS อินเทอร์เน็ตล่ม = งานหยุด → นิยมมี **ISP 2 ราย** (ต่างผู้ให้บริการ ต่างเส้นทางกายภาพ)

รูปแบบ

| รูปแบบ | ลักษณะ |
|---|---|
| **Active/Standby** | ใช้ ISP1 เป็นหลัก ISP2 สำรองเมื่อ ISP1 ล่ม |
| **Active/Active (load sharing)** | ใช้ทั้งสอง แบ่งตาม traffic/ผู้ใช้/แอป (PBR หรือ SD-WAN) |
| **BGP multihoming** | มี public IP/ASN ของตัวเอง ประกาศผ่านทั้งสอง ISP (Level 48–49) |

---

## 3. Floating Static Route

Static route ที่ตั้ง **AD สูงกว่า** route หลัก เพื่อ **"ซ่อน" ไว้** ไม่ลง routing table จนกว่า route หลักจะหายไป

```
ip route 0.0.0.0 0.0.0.0 203.0.113.1            ! ISP1 หลัก (AD 1)
ip route 0.0.0.0 0.0.0.0 198.51.100.1 250       ! ISP2 สำรอง (AD 250 — "floating")
```
- ปกติ: ISP1 (AD 1) อยู่ใน table, ISP2 ไม่อยู่
- ถ้า **interface ไป ISP1 down** → route ISP1 หาย → ISP2 ลง table แทน
- ใช้สำรอง routing protocol ได้ด้วย เช่น สาขามี OSPF ผ่าน MPLS (AD 110) + floating static ผ่าน VPN (AD 200)

**ค่า AD ของ floating** ต้อง **สูงกว่า** route หลักและ routing protocol ที่ใช้อยู่ (เช่น 200–250)

---

## 4. ปัญหาของ Floating Static อย่างเดียว

Static route จะหายจาก table ก็ต่อเมื่อ **interface ขาออก down** หรือ next-hop ไม่มี route เท่านั้น

```
 [R1]──Gi0/0──[ONT/Router ISP1]──X──อินเทอร์เน็ต
         ↑ link ยัง up (ต่อกับกล่องของ ISP)
         แต่ภายใน ISP ขาด / ISP มีปัญหา routing
 → route ISP1 ยังอยู่ใน table → traffic ยังไป ISP1 → อินเทอร์เน็ตล่ม แต่ไม่ failover!
```
กรณีนี้พบบ่อยมาก เพราะ router มักต่อกับ ONT/modem/switch ของ ISP ไม่ใช่ต่อตรงกับ router ของ ISP

---

## 5. IP SLA + Object Tracking — ตรวจการเชื่อมต่อ "จริง"

**IP SLA** ส่ง probe (ICMP/TCP/HTTP/DNS) ไปยังเป้าหมายเป็นระยะ → **Track** ติดตามผล → static route **ผูกกับ track** (ถ้า track down → route ถูกถอนออก)

```
! 1) สร้าง probe: ping 8.8.8.8 ผ่าน ISP1 ทุก 5 วินาที
ip sla 1
 icmp-echo 8.8.8.8 source-interface GigabitEthernet0/0
 frequency 5
 threshold 1000
 timeout 1000
ip sla schedule 1 life forever start-time now
!
! 2) track ผล (ทางเลือก: delay กันการสลับไปมาเร็วเกิน)
track 1 ip sla 1 reachability
 delay down 10 up 30
!
! 3) ผูก route หลักกับ track + route สำรองแบบ floating
ip route 0.0.0.0 0.0.0.0 203.0.113.1 track 1
ip route 0.0.0.0 0.0.0.0 198.51.100.1 250
!
! 4) ให้ probe วิ่งผ่าน ISP1 เสมอ (ไม่งั้นเมื่อ failover แล้ว probe จะวิ่งผ่าน ISP2 และกลับมา success)
ip route 8.8.8.8 255.255.255.255 203.0.113.1
!
show ip sla statistics
show track 1
```

### เลือกเป้าหมาย probe ให้ดี
- ✅ **IP บนอินเทอร์เน็ตที่เสถียร** (เช่น public DNS) หรือ **หลายเป้าหมาย** (track list แบบ boolean OR/threshold) ป้องกันเป้าหมายเดียวล่มแล้ว failover โดยไม่จำเป็น
- ❌ IP ของ gateway ISP ฝั่งเรา (ตรวจได้แค่ลิงก์ ไม่รู้ว่าข้างใน ISP ขาด)
- ต้องบังคับให้ probe ออกทาง ISP ที่ต้องการตรวจ (source-interface + host route)
- ใช้ **delay up** ป้องกันการสลับไปมา (flapping) เมื่อลิงก์ไม่เสถียร

---

## 6. ผลกระทบเมื่อ Failover

| ประเด็น | ผลกระทบ / การจัดการ |
|---|---|
| **NAT** | public IP เปลี่ยนจาก ISP1 → ISP2 → **session เดิมหลุดทั้งหมด** ผู้ใช้ต้องเชื่อมต่อใหม่ (ปกติ) · ต้องมี NAT rule สำหรับทั้งสอง ISP (route-map ตาม interface ขาออก) และอาจต้อง `clear ip nat translation` |
| **Inbound (server ที่ให้บริการภายนอก)** | DNS ชี้ public IP ของ ISP1 → ISP1 ล่มคนนอกเข้าไม่ได้ → ใช้ DNS failover/TTL สั้น, หรือ BGP multihoming |
| **VPN site-to-site** | peer IP เปลี่ยน → ต้องตั้ง tunnel สำรองผ่าน ISP2 |
| **Failback** | เมื่อ ISP1 กลับมา route หลักกลับเข้ามา → session ผ่าน ISP2 หลุดอีกรอบ (ใช้ delay up ให้แน่ใจว่าเสถียรก่อน) |

---

## 7. Policy-Based Routing (PBR) — แบ่ง traffic ตามเงื่อนไข

Routing ปกติดูแค่ **ปลายทาง** PBR เลือกเส้นทางตาม **ต้นทาง, port, แอป** ได้

```
 แผนกบัญชี (10.0.10.0/24) → ISP1 · Guest Wi-Fi (10.0.50.0/23) → ISP2
```
```
ip access-list extended GUEST-NET
 permit ip 10.0.50.0 0.0.1.255 any
route-map PBR-ISP permit 10
 match ip address GUEST-NET
 set ip next-hop verify-availability 198.51.100.1 1 track 2   ! ใช้ ISP2 ถ้า track 2 ยังดี
interface vlan 50
 ip policy route-map PBR-ISP                                   ! ใส่ที่ interface ขาเข้าของ traffic
show route-map
show ip policy
```
> 💡 ปัจจุบันงานแบ่ง traffic ตามแอปและคุณภาพลิงก์มักทำด้วย **SD-WAN** บน firewall/router รุ่นใหม่ (Level 60 และ ISC Level 16) ซึ่งจัดการง่ายกว่า PBR มาก

---

## 8. Linux / Firewall

- **Linux:** ใช้ metric (`ip route add default via A metric 100`, `... via B metric 200`) + สคริปต์ตรวจ หรือ keepalived/`ip rule` (Level 26)
- **FortiGate:** SD-WAN + Performance SLA (ทำงานแบบ IP SLA ในตัว)
- **Palo Alto:** Path monitoring บน static route

---

## 9. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| Floating static เพียงพอสำหรับ dual ISP | ถ้าลิงก์ยัง up แต่ ISP ข้างในล่ม จะไม่ failover — ต้องใช้ IP SLA + track |
| ping gateway ของ ISP เพียงพอสำหรับตรวจ | ตรวจได้แค่ลิงก์ ไม่รู้ว่าออกอินเทอร์เน็ตได้หรือไม่ |
| Failover แล้วผู้ใช้ไม่รู้สึกอะไร | session ผ่าน NAT หลุด ต้องเชื่อมต่อใหม่ |
| `default-information originate always` ปลอดภัยเสมอ | อาจดึง traffic มาที่ router ที่ไม่มีทางออกจริง |

---

## 10. Cheat Sheet

```
Default: ip route 0.0.0.0 0.0.0.0 GW · OSPF: default-information originate
Floating static: route สำรอง AD สูงกว่า (เช่น 250) ซ่อนจนกว่าหลักหาย
ปัญหา: link up แต่ ISP ข้างในขาด → ใช้ IP SLA + track
ip sla 1 / icmp-echo X source-interface ISP1 · track 1 ip sla 1 reachability · ip route ... track 1
probe: เป้าหมายบนอินเทอร์เน็ต หลายตัว · บังคับออก ISP ที่ตรวจ · delay up กัน flap
Failover: NAT session หลุด · inbound ต้อง DNS/BGP · VPN ต้องมี tunnel สำรอง
PBR: route-map match ต้นทาง → set next-hop · ใส่ที่ interface ขาเข้า · ปัจจุบันนิยม SD-WAN
```

---

## 11. แบบทดสอบ 10 ข้อ

1. Default route คืออะไร ทำไมถูกเลือกเป็นอันดับสุดท้าย
2. คำสั่งกระจาย default route ใน OSPF
3. Floating static route ทำงานอย่างไร
4. ควรตั้ง AD ของ floating static เท่าใดเมื่อใช้ร่วมกับ OSPF
5. ทำไม floating static อย่างเดียวอาจไม่ failover เมื่อ ISP1 ล่ม
6. องค์ประกอบ 3 ส่วนของ IP SLA failover บน Cisco
7. ทำไมไม่ควรใช้ IP ของ gateway ISP เป็นเป้าหมาย probe
8. ทำไมต้องมี host route บังคับให้ probe ออกทาง ISP1
9. ผลกระทบของ failover ต่อผู้ใช้ที่เชื่อมต่อผ่าน NAT
10. ต้องการให้ Guest Wi-Fi ใช้ ISP2 ส่วนพนักงานใช้ ISP1 ใช้เทคนิคใด

<details><summary><b>เฉลย</b></summary>

1. Route 0.0.0.0/0 สำหรับปลายทางที่ไม่มี route เจาะจง — prefix สั้นที่สุด จึงแพ้ทุก route ที่เจาะจงกว่าตาม longest match
2. `default-information originate` (ใต้ `router ospf`)
3. Static route สำรองที่ AD สูงกว่าหลัก จะลง routing table เมื่อ route หลักหายไปเท่านั้น
4. สูงกว่า 110 เช่น 200–250
5. Static route หายเมื่อ interface down เท่านั้น ถ้าลิงก์ไปอุปกรณ์ ISP ยัง up แต่ข้างใน ISP ขาด route หลักยังอยู่
6. IP SLA (probe), track (ติดตามผล), static route ที่ผูก track (+ floating route สำรอง)
7. ตรวจได้แค่ลิงก์ช่วงแรก ไม่รู้ว่าเครือข่าย ISP ภายในหรือการออกอินเทอร์เน็ตใช้ได้จริง
8. หลัง failover ถ้า probe วิ่งออกทาง ISP2 จะ success และทำให้ระบบคิดว่า ISP1 กลับมาแล้ว (สลับไปมา)
9. Public IP เปลี่ยน session เดิมหลุดทั้งหมด ต้องเชื่อมต่อใหม่
10. Policy-based routing (หรือ SD-WAN rule) แยกตามต้นทาง
</details>

---

➡️ ต่อไป: **Level 43 — แนวคิด Dynamic Routing**
