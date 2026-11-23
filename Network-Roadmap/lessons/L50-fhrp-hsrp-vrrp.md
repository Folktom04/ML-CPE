# บทเรียน Level 50 — First Hop Redundancy (HSRP / VRRP / GLBP) (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจว่าทำไม default gateway ต้องมีสำรอง · การทำงานของ Virtual IP/Virtual MAC · ตั้ง HSRP และ VRRP พร้อม priority, preempt, tracking · GLBP · จับคู่กับ STP root · ทดสอบและแก้ปัญหา failover ได้

---

## 1. ปัญหา: Default Gateway เป็น Single Point of Failure

เครื่องผู้ใช้ตั้ง gateway ได้ **IP เดียว** (เช่น 10.0.10.1) ถ้ามี router/L3 switch 2 ตัว แต่ผู้ใช้ชี้ไปที่ตัวหนึ่ง เมื่อตัวนั้นล่ม **ผู้ใช้ทั้ง VLAN ออกนอกวงไม่ได้** แม้อีกตัวยังทำงานอยู่ (เปลี่ยน gateway ทุกเครื่องด้วยมือไม่ได้ และ DHCP ก็ไม่ได้อัปเดตทันที)

**FHRP (First Hop Redundancy Protocol)** แก้ด้วยการสร้าง **"gateway เสมือน"**:
- **Virtual IP (VIP)** — IP ที่ผู้ใช้ตั้งเป็น gateway
- **Virtual MAC** — MAC ที่ตอบ ARP ของ VIP
- router 2 ตัวขึ้นไปตกลงกันว่า **ใครเป็นตัวหลัก** ถือ VIP/vMAC อยู่ เมื่อตัวหลักล่ม **อีกตัวรับ VIP/vMAC ต่อทันที** — เครื่องผู้ใช้ไม่ต้องเปลี่ยนอะไร (ARP cache ยังใช้ MAC เดิมได้)

```
            ผู้ใช้ VLAN 10 · gateway = 10.0.10.1 (VIP)
                         │
          ┌──────────────┴──────────────┐
     [DIST-1] 10.0.10.2            [DIST-2] 10.0.10.3
     Active ✅ (ถือ VIP + vMAC)      Standby (รอ)
     priority 110                   priority 100
```

---

## 2. เปรียบเทียบ HSRP / VRRP / GLBP

| | **HSRP** | **VRRP** | **GLBP** |
|---|---|---|---|
| มาตรฐาน | Cisco | **เปิด (RFC 5798, v3)** — ทุกยี่ห้อ | Cisco |
| บทบาท | **Active / Standby** (+ Listen) | **Master / Backup** | AVG + AVF (สูงสุด 4) |
| Load balance ใน VLAN เดียว | ❌ (ทำต่อ VLAN ได้) | ❌ (ทำต่อ VLAN ได้) | ✅ |
| Virtual MAC | v1 `0000.0c07.acXX` · v2 `0000.0c9f.fXXX` | `0000.5e00.01XX` (XX = VRID) | `0007.b400.XXYY` |
| Multicast | v1 224.0.0.2 · v2 224.0.0.102 (UDP 1985) | 224.0.0.18 (IP protocol 112) | 224.0.0.102 (UDP 3222) |
| Hello / Hold | 3 / 10 วินาที | Advertisement 1 วินาที, master down ≈ 3 วินาที | 3 / 10 วินาที |
| Preempt (ค่าเริ่มต้น) | **ปิด** | **เปิด** | ปิด (สำหรับ AVG) |
| VIP = IP จริงของ router ได้ไหม | ไม่ได้ | **ได้** (router นั้นเป็น owner, priority 255) | ไม่ได้ |
| IPv6 | HSRPv2 | VRRPv3 | ✅ |

> **เลือกอย่างไร:** Cisco ล้วน → HSRP (คุ้นเคย) หรือ VRRP · หลายยี่ห้อ/firewall/Linux → **VRRP** · ต้องการ load balance ใน VLAN เดียว → GLBP (หรือออกแบบ active-active แบบอื่น)

---

## 3. HSRP — การตั้งค่าและกลไก

```
! DIST-1 (ตั้งใจให้เป็น Active)
interface Vlan10
 ip address 10.0.10.2 255.255.255.0
 standby version 2                       ! รองรับ group 0-4095, IPv6, millisecond timer
 standby 10 ip 10.0.10.1                 ! VIP (group 10 — ตั้งให้ตรงกับ VLAN เพื่ออ่านง่าย)
 standby 10 priority 110                 ! ค่าเริ่มต้น 100 · สูงกว่าเป็น Active
 standby 10 preempt                      ! ⭐ ยึดคืนเมื่อกลับมาและ priority สูงกว่า
 standby 10 preempt delay minimum 60     ! รอให้ routing/STP พร้อมก่อนยึดคืน
 standby 10 timers msec 250 msec 750     ! (ทางเลือก) failover เร็วขึ้น
 standby 10 authentication md5 key-string S3cr3t!
 standby 10 track 1 decrement 20         ! ลด priority ถ้า uplink ตาย (ดูข้อ 5)
!
! DIST-2 (Standby)
interface Vlan10
 ip address 10.0.10.3 255.255.255.0
 standby version 2
 standby 10 ip 10.0.10.1
 standby 10 priority 100
 standby 10 preempt
 standby 10 authentication md5 key-string S3cr3t!
```

### การเลือก Active
1. **Priority สูงสุด** (0–255, ค่าเริ่มต้น 100)
2. ถ้าเท่ากัน → **IP จริงสูงสุด** ของ interface

### Preempt — สำคัญมาก
- **ไม่มี preempt:** DIST-1 ล่ม → DIST-2 เป็น Active · DIST-1 กลับมา **DIST-2 ยังเป็น Active ต่อ** (ไม่ยึดคืน)
- **มี preempt:** DIST-1 กลับมาแล้วยึดคืน (เพราะ priority สูงกว่า) → traffic กลับมาเดินตามที่ออกแบบไว้
- ใช้ **preempt delay** ป้องกันการยึดคืนก่อนที่ routing protocol/STP ของตัวที่เพิ่งบูตจะพร้อม (ถ้ายึดเร็วเกินจะเกิด blackhole ชั่วคราว)

### HSRP States
Initial → Learn → Listen → Speak → **Standby** / **Active**

---

## 4. VRRP — การตั้งค่า

```
! ทั้งสองตัว (Cisco IOS-XE รุ่นใหม่ใช้ VRRPv3)
fhrp version vrrp v3
interface Vlan10
 ip address 10.0.10.2 255.255.255.0
 vrrp 10 address-family ipv4
  address 10.0.10.1 primary
  priority 110
  preempt delay minimum 60            ! preempt เปิดเป็นค่าเริ่มต้น
  track 1 decrement 20
```
**Linux:** ใช้ **keepalived** (ใช้มากกับ load balancer/HAProxy, firewall ที่เป็น Linux)
```
vrrp_instance VI_10 {
  state BACKUP
  interface eth0
  virtual_router_id 10
  priority 110
  advert_int 1
  virtual_ipaddress { 10.0.10.1/24 }
}
```

---

## 5. Object Tracking — สำรองให้ฉลาด

**ปัญหา:** DIST-1 เป็น Active แต่ **uplink ไป core ขาด** — DIST-1 ยังทำงานอยู่ (LAN ฝั่งผู้ใช้ยัง up) จึงยังถือ VIP → ผู้ใช้ส่ง traffic มาที่ DIST-1 ซึ่งไม่มีทางออก (หรือต้องอ้อมผ่านลิงก์ระหว่าง DIST)

**ทางแก้:** **track** สถานะ uplink (หรือ route/IP SLA) → ถ้าเสีย **ลด priority** ลงจนต่ำกว่า standby → standby (ที่ตั้ง preempt) ขึ้นเป็น Active
```
track 1 interface TenGigabitEthernet1/1/1 line-protocol
track 2 ip route 0.0.0.0 0.0.0.0 reachability          ! หรือ track ว่ายังมี default route
interface Vlan10
 standby 10 track 1 decrement 20                        ! 110 - 20 = 90 < 100 → DIST-2 เป็น Active
```
> ⚠️ ต้องตั้ง **preempt บน standby** ด้วย ไม่เช่นนั้นจะไม่ยึด Active แม้ priority สูงกว่าแล้ว

---

## 6. Load Sharing — ใช้ทั้งสองตัว

HSRP/VRRP หนึ่ง group มี Active ตัวเดียว แต่ทำ **คนละ group ต่อ VLAN** ได้:
```
 VLAN 10, 30, 50 (กลุ่ม A): DIST-1 = Active (priority 110), DIST-2 = Standby
 VLAN 20, 40, 60 (กลุ่ม B): DIST-2 = Active, DIST-1 = Standby
```
→ ทั้งสองตัวทำงาน แต่ละตัวรับครึ่งหนึ่งของ VLAN

### ⭐ ต้องจับคู่กับ STP Root
```
 VLAN 10: HSRP Active = DIST-1  → STP root VLAN 10 = DIST-1 ด้วย
 VLAN 20: HSRP Active = DIST-2  → STP root VLAN 20 = DIST-2 ด้วย
```
**ถ้าไม่ตรงกัน:** frame จากผู้ใช้วิ่งตาม STP ไปทาง DIST-2 ก่อน แล้วต้องข้าม inter-switch link ไป DIST-1 (Active) → เส้นทางอ้อม เพิ่ม latency และใช้ลิงก์ระหว่าง DIST โดยไม่จำเป็น

---

## 7. GLBP — Load Balance ใน VLAN เดียว (Cisco)

- **AVG (Active Virtual Gateway)** — เลือก 1 ตัว ทำหน้าที่ **ตอบ ARP** ของ VIP
- **AVF (Active Virtual Forwarder)** — สูงสุด 4 ตัว แต่ละตัวมี **virtual MAC ของตัวเอง**
- AVG ตอบ ARP ด้วย vMAC ที่ **ต่างกันในแต่ละเครื่อง** (round-robin/weighted/host-dependent) → ผู้ใช้แต่ละคนใช้ router ต่างกัน ทั้งที่ gateway IP เดียวกัน
```
interface Vlan10
 glbp 10 ip 10.0.10.1
 glbp 10 priority 110
 glbp 10 preempt
 glbp 10 load-balancing round-robin
```

---

## 8. Anycast Gateway (Data Center สมัยใหม่)

ใน DC แบบ spine-leaf/EVPN-VXLAN ทุก leaf มี **gateway IP + MAC เดียวกัน** พร้อมกัน (active-active ทั้งหมด) — VM ย้ายไป leaf ไหนก็ใช้ gateway ที่ leaf นั้นได้ทันทีโดยไม่ต้องใช้ FHRP (Level 74) · MLAG/vPC ก็มีกลไกให้ gateway ทั้งสองตัวรับ traffic ได้ (เช่น peer-gateway, VARP ของ Arista)

---

## 9. ตรวจสอบและทดสอบ

```
show standby brief
                     P indicates configured to preempt.
Interface   Grp  Pri P State   Active          Standby         Virtual IP
Vl10        10   110 P Active  local           10.0.10.3       10.0.10.1
Vl20        20   100 P Standby 10.0.20.3       local           10.0.20.1

show standby vlan 10                 ! รายละเอียด: vMAC, timer, track, จำนวนครั้งที่เปลี่ยนสถานะ
show vrrp brief
show glbp brief
show track
```
**ทดสอบ failover (ตอนส่งมอบงาน)**
```
 1) จากเครื่องผู้ใช้: ping -t <IP ภายนอก VLAN> (หรือ ping ทุก 100 ms ด้วยเครื่องมือ)
 2) ปิด Active (shutdown SVI/reload/ดึง uplink เพื่อทดสอบ track)
 3) นับ packet ที่หาย → เวลา failover (ค่าเริ่มต้น HSRP ~10 วินาที; ปรับ timer msec เหลือ < 1 วินาที)
 4) เปิดกลับ → ตรวจ preempt (และ delay) ทำงานถูก
 5) ตรวจว่า STP root ตรงกับ Active หลังทดสอบ
```

---

## 10. แก้ปัญหา FHRP

| อาการ | สาเหตุ |
|---|---|
| **ทั้งสองตัวเป็น Active (split-brain)** | ไม่เห็น hello กัน — VLAN ไม่อยู่บน trunk ระหว่าง DIST, ACL บล็อก multicast, group/version/authentication ไม่ตรงกัน |
| ไม่ยึดคืนเมื่อตัวหลักกลับมา | ไม่ได้ตั้ง preempt |
| Uplink ขาดแต่ไม่ failover | ไม่ได้ตั้ง track หรือ decrement ไม่พอ หรือ standby ไม่มี preempt |
| Traffic เดินอ้อม | HSRP Active ไม่ตรงกับ STP root |
| Log "duplicate address" | VIP ซ้ำกับ IP จริงของเครื่องใด |
| ผู้ใช้ยังใช้ MAC เก่าหลัง failover | ปกติ Active ใหม่จะส่ง gratuitous ARP — ตรวจว่าไม่ถูก DAI/security บล็อก |

---

## 11. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| HSRP preempt เปิดเป็นค่าเริ่มต้น | ปิด (VRRP เปิด) |
| มี HSRP แล้ว uplink ขาดก็ failover เอง | ต้อง track uplink และ standby ต้องมี preempt |
| HSRP กระจาย traffic ใน VLAN เดียวได้ | Active ตัวเดียวต่อ group — ใช้หลาย group/VLAN หรือ GLBP |
| VIP ต้องเป็น IP ใหม่เสมอ | VRRP ใช้ IP จริงของ router เป็น VIP ได้ (owner) |

---

## 12. Cheat Sheet

```
FHRP = Virtual IP + Virtual MAC ที่ย้ายไปตัวสำรองได้ (gateway ไม่มี SPOF)
HSRP (Cisco): Active/Standby · priority 100 · preempt ปิด (ต้องเปิดเอง) · vMAC 0000.0c07.acXX / v2 0000.0c9f.fXXX
VRRP (มาตรฐาน): Master/Backup · preempt เปิด · vMAC 0000.5e00.01XX · VIP เป็น IP จริงได้
GLBP (Cisco): AVG ตอบ ARP + AVF สูงสุด 4 → load balance ใน VLAN เดียว
เลือก Active: priority สูงสุด → IP สูงสุด
track uplink + decrement + preempt (ทั้งสองตัว) + preempt delay
Load share: คนละ group ต่อ VLAN · Active ต้องตรงกับ STP root
show standby brief / vrrp brief / glbp brief / track · ทดสอบ failover ด้วย ping ต่อเนื่อง
```

---

## 13. แบบทดสอบ 10 ข้อ

1. FHRP แก้ปัญหาอะไร
2. HSRP กับ VRRP ต่างกันอย่างไร (4 ข้อ)
3. HSRP เลือก Active อย่างไร
4. ถ้าไม่ตั้ง preempt เมื่อ router หลักกลับมาจะเกิดอะไร
5. ทำไมต้องตั้ง preempt delay
6. Interface tracking ช่วยในสถานการณ์ใด และต้องตั้งอะไรคู่กันที่ standby
7. ทำ load sharing ด้วย HSRP อย่างไร
8. ทำไม HSRP Active ควรเป็น STP root ของ VLAN เดียวกัน
9. GLBP กระจาย traffic ใน VLAN เดียวได้อย่างไร
10. show standby แสดงทั้งสองตัวเป็น Active สาเหตุที่เป็นไปได้คืออะไร

<details><summary><b>เฉลย</b></summary>

1. Default gateway เป็น single point of failure — สร้าง VIP/vMAC ที่ย้ายไป router สำรองได้อัตโนมัติ
2. HSRP เป็นของ Cisco / VRRP เป็นมาตรฐาน; HSRP Active/Standby / VRRP Master/Backup; HSRP preempt ปิด / VRRP เปิด; VRRP ใช้ IP จริงของ router เป็น VIP ได้; vMAC และ multicast ต่างกัน
3. Priority สูงสุด ถ้าเท่ากัน IP จริงสูงสุด
4. Router หลักไม่ยึด Active คืน ตัวสำรองยังเป็น Active ต่อ
5. ให้ routing protocol/STP ของ router ที่เพิ่งกลับมาพร้อมก่อนยึด Active ป้องกัน blackhole ชั่วคราว
6. Uplink ของ Active ขาดแต่ LAN ยัง up — track แล้วลด priority ให้ต่ำกว่า standby; standby ต้องตั้ง preempt
7. ใช้คนละ HSRP group ต่อ VLAN ให้ Active ของแต่ละ VLAN อยู่คนละ router
8. ให้เส้นทาง L2 (ตาม STP) และ L3 (gateway) ไปทางเดียวกัน ไม่อ้อมผ่านลิงก์ระหว่าง switch
9. AVG ตอบ ARP ของ VIP ด้วย virtual MAC ของ AVF ที่ต่างกันในแต่ละเครื่อง ผู้ใช้จึงส่ง traffic ไป router ต่างกัน
10. ไม่เห็น hello กัน — VLAN ไม่ได้อยู่บน trunk ระหว่างสอง router, ACL บล็อก, group/version/authentication ไม่ตรงกัน
</details>

---

🎉 **จบ Tier 5** · ➡️ ต่อไป: **Level 51 — Wireless 802.11 พื้นฐาน** · กลับไปทำโปรเจคใน [05-routing.md](../05-routing.md)
