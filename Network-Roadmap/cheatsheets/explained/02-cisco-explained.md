# อธิบายละเอียด: คำสั่งตรวจเช็ค Cisco

> คู่กับ cheat sheet [02-cisco.md](../02-cisco.md)
> อ่านจบแล้วจะ: เข้าใจโหมดของ CLI · อ่าน output ของคำสั่งสำคัญได้ทีละบรรทัด · รู้ว่าค่าไหนปกติ ค่าไหนผิดปกติ · ไล่หาเครื่อง/ปัญหาในเครือข่าย Cisco ได้เอง

---

## 1. พื้นฐาน CLI ของ Cisco

### โหมดต่าง ๆ (ดูจากเครื่องหมายท้ายชื่อ)
```
SW01>                 ← User EXEC: ดูได้น้อย
SW01> enable
SW01#                 ← Privileged EXEC: ใช้ show/ping/traceroute ได้ทั้งหมด ⭐ (ส่วนใหญ่ทำงานที่นี่)
SW01# configure terminal
SW01(config)#         ← Global config: แก้การตั้งค่า (ระวัง!)
SW01(config)# interface Gi1/0/10
SW01(config-if)#      ← แก้เฉพาะ interface
SW01(config-if)# end  ← กลับไป # ทันที
```
**คำสั่ง `show` ไม่เปลี่ยนแปลงอะไร** — ปลอดภัยที่จะลองบนระบบจริง

### ช่วยเหลือในตัว
- พิมพ์ `?` เพื่อดูคำสั่งที่ใช้ได้: `show ip ?`
- กด **Tab** เติมคำสั่งให้ครบ, พิมพ์ย่อได้ถ้าไม่ซ้ำ: `sh ip int br` = `show ip interface brief`
- `terminal length 0` = แสดงผลทั้งหมดโดยไม่ต้องกด space ทีละหน้า (สะดวกเวลาคัดลอกผลเก็บ)

### กรองผลด้วย `|` (pipe) — ใช้บ่อยมาก
```
show running-config | include ntp          ← เฉพาะบรรทัดที่มีคำว่า ntp
show ip interface brief | exclude unassigned ← ตัดบรรทัดที่ไม่มี IP ออก
show running-config | section router ospf  ← แสดงทั้งบล็อกการตั้งค่า OSPF
show logging | include Gi1/0/10            ← log ที่เกี่ยวกับพอร์ตนี้
```
**ชื่อ interface:** `Fa` = FastEthernet 100M · `Gi` = Gigabit 1G · `Te` = TenGig 10G · `Twe` = 25G · `Hu` = 100G · `Vlan20` = SVI (IP ของ VLAN 20) · `Po1` = Port-channel · `Lo0` = Loopback
เลข `Gi1/0/10` = switch ตัวที่ 1 (ใน stack) / module 0 / พอร์ต 10

---

## 2. ภาพรวมอุปกรณ์: `show version`

```
SW01# show version
Cisco IOS XE Software, Version 17.09.04a                         ← (1) version ของ OS
...
SW01 uptime is 2 weeks, 3 days, 4 hours, 12 minutes              ← (2) เปิดมานานเท่าไร
Uptime for this control processor is 2 weeks, 3 days, 4 hours
System returned to ROM by Reload Command                         ← (3) reboot ครั้งล่าสุดเพราะอะไร
System image file is "flash:packages.conf"
...
Model Number                       : C9300-48P                   ← (4) รุ่น
System Serial Number               : FOC2412X0AB                 ← (5) serial (ใช้เปิด case กับ Cisco)
```
1. **Version** — ใช้เช็คว่ามีช่องโหว่/bug ที่ประกาศไว้ไหม และสอดคล้องกับมาตรฐานองค์กร
2. **Uptime** — ถ้าผู้ใช้แจ้งว่า "เน็ตหลุดเมื่อเช้า" แล้ว uptime = 3 ชั่วโมง → **switch reboot เอง** เมื่อเช้า!
3. **Returned to ROM by...** — `Reload Command` = มีคนสั่ง · `power-on` = ไฟดับ/ถอดปลั๊ก · ข้อความแนว `crash`/`error`/`watchdog` = **ระบบล่ม** → เก็บข้อมูลเปิด TAC
4–5. รุ่นและ serial สำหรับ inventory/support contract

### CPU: `show processes cpu sorted`
```
CPU utilization for five seconds: 85%/62%; one minute: 80%; five minutes: 78%
                                  └─┬─┘└┬┘
                         CPU รวม 85%   └ ในจำนวนนี้ 62% เป็น "interrupt" (การประมวลผล packet ที่ถูกส่งขึ้น CPU)
 PID Runtime(ms)  Invoked  uSecs   5Sec   1Min   5Min TTY Process
 215   2938221   1234567   2380  18.31% 15.20% 14.90%   0 IP Input        ← process ที่กิน CPU มากสุด
```
- CPU รวมสูง แต่ **ตัวหลัง (interrupt) ต่ำ** → process ทำงานหนัก (เช่น routing protocol คำนวณ, SNMP ถูกถามถี่)
- **ตัวหลังสูง** → มี traffic จำนวนมากถูกส่งให้ CPU ประมวลผลแทน hardware (เช่น ARP จำนวนมาก, routing loop ทำให้ TTL หมด, ACL ที่มี `log`)
- ปกติ switch/router ควรต่ำกว่า ~50% ต่อเนื่อง · ใช้ `show processes cpu history` ดูกราฟย้อนหลัง 72 ชั่วโมง

---

## 3. Interface — คำสั่งที่ใช้บ่อยที่สุด

### `show ip interface brief` — สรุปทุก interface ในหน้าเดียว ⭐
```
SW01# show ip interface brief
Interface              IP-Address      OK? Method Status                Protocol
Vlan1                  unassigned      YES unset  administratively down down
Vlan20                 10.0.20.1       YES NVRAM  up                    up        ← ปกติ
Vlan30                 10.0.30.1       YES NVRAM  up                    down      ← ผิดปกติ
GigabitEthernet1/0/1   unassigned      YES unset  up                    up
GigabitEthernet1/0/2   unassigned      YES unset  down                  down      ← ไม่มีอะไรเสียบ/สายเสีย
GigabitEthernet1/0/3   unassigned      YES unset  administratively down down      ← ถูกปิดด้วยคำสั่ง shutdown
```
**อ่าน Status / Protocol (2 คอลัมน์สุดท้าย):**
| Status | Protocol | ความหมาย | แนวทาง |
|---|---|---|---|
| up | up | ✅ ปกติ | — |
| down | down | ไม่มีสัญญาณไฟฟ้า/แสง (Layer 1) | สาย, ฝั่งตรงข้ามปิด, SFP ผิดชนิด |
| administratively down | down | มีคนสั่ง `shutdown` | ตั้งใจหรือไม่? (`no shutdown` ถ้าต้องเปิด) |
| up | down | L1 ได้ แต่ L2 ไม่ขึ้น | ฝั่งตรงข้ามตั้งค่าไม่ตรง; **สำหรับ SVI (Vlan30)** = ไม่มีพอร์ตใดใน VLAN 30 ที่ up หรือ VLAN 30 ไม่มีอยู่ |

### `show interfaces status` (switch) — มองภาพพอร์ตทั้งหมด
```
Port      Name               Status       Vlan       Duplex  Speed Type
Gi1/0/1   Uplink-CORE01      connected    trunk        full    1000 10/100/1000BaseTX
Gi1/0/5   PC-ACC-2F-05       connected    20         a-full  a-1000 10/100/1000BaseTX
Gi1/0/6   PC-ACC-2F-06       notconnect   20           auto   auto 10/100/1000BaseTX
Gi1/0/7   Printer-2F         err-disabled 40           auto   auto 10/100/1000BaseTX
Gi1/0/8   PC-HR-2F-08        connected    20         a-half  a-100 10/100/1000BaseTX
```
| ดู | อธิบาย |
|---|---|
| `connected` / `notconnect` | มีอุปกรณ์เชื่อมต่อหรือไม่ |
| `err-disabled` | **switch ปิดพอร์ตเองอัตโนมัติ** เพราะตรวจพบสิ่งผิดปกติ (เช่น เสียบ switch เพิ่ม, MAC เกินจำนวนที่อนุญาต) |
| Vlan `20` / `trunk` | พอร์ตอยู่ VLAN ไหน (เครื่องได้ IP วงไหน) |
| `a-full a-1000` | `a-` = เจรจาความเร็วอัตโนมัติ (auto) ได้ full duplex 1 Gbps ✅ |
| `a-half a-100` (Gi1/0/8) | ⚠️ **ได้แค่ 100 Mbps half duplex** — สายเสีย (ใช้ได้แค่ 2 คู่), การ์ดแลนเก่า หรือมีปัญหา → เครื่องนี้จะช้ามาก |

### `show interfaces Gi1/0/5` — รายละเอียดเชิงลึกของพอร์ตเดียว
```
GigabitEthernet1/0/5 is up, line protocol is up (connected)
  Hardware is Gigabit Ethernet, address is 7c0e.ce12.3405
  Description: PC-ACC-2F-05
  MTU 1500 bytes, BW 1000000 Kbit/sec, DLY 10 usec,
     reliability 255/255, txload 1/255, rxload 12/255           ← (1) ภาระ
  Full-duplex, 1000Mb/s, media type is 10/100/1000BaseTX         ← (2)
  Last clearing of "show interface" counters 3d02h               ← (3) counter นับมาตั้งแต่เมื่อไร
  Input queue: 0/2000/0/0 (size/max/drops/flushes); Total output drops: 1520   ← (4)
  5 minute input rate 47000000 bits/sec, 4100 packets/sec         ← (5) ใช้อยู่ 47 Mbps
  5 minute output rate 1200000 bits/sec, 300 packets/sec
     12503321 packets input, 9876543210 bytes
     0 runts, 0 giants, 0 throttles
     235 input errors, 235 CRC, 0 frame, 0 overrun, 0 ignored    ← (6) ⚠️ มี CRC error
     0 output errors, 0 collisions, 1 interface resets
     0 late collision, 0 deferred                                 ← (7)
```
1. **txload/rxload x/255** — ภาระการใช้งาน (255/255 = เต็มลิงก์) · **reliability 255/255** = ไม่มี error
2. **Full-duplex, 1000Mb/s** — ควรเป็น full เสมอ
3. **Last clearing** — counter สะสมมานานเท่าไร (ตัวเลข error ต้องเทียบกับระยะเวลา)
4. **output drops** — switch ต้องทิ้ง packet เพราะส่งออกไม่ทัน (**ลิงก์เต็มหรือมี burst**) — มีบ้างเล็กน้อยปกติ แต่ถ้าเพิ่มขึ้นเรื่อย ๆ ขณะผู้ใช้บ่นช้า = congestion
5. **5 minute rate** — ค่าเฉลี่ย 5 นาที (บอกการใช้งานคร่าว ๆ)
6. **CRC / input errors** — frame ที่ได้รับ **เสียหาย** → สายแลนเสีย/หัว RJ45 ไม่ดี/สายยาวเกิน 100 m/ผ่านจุดรบกวน, ไฟเบอร์สกปรก
7. **late collision** — แทบแน่นอนว่าเป็น **duplex mismatch** (ฝั่งหนึ่ง full อีกฝั่ง half)

**วิธีพิสูจน์ว่า error ยังเกิดอยู่:** `clear counters Gi1/0/5` → รอ 10–15 นาที → ดูใหม่ ถ้า CRC เพิ่มขึ้น = ยังมีปัญหาจริง (เปลี่ยนสาย/พอร์ต)

### SFP ไฟเบอร์: `show interfaces Te1/1/1 transceiver detail`
```
                                     High Alarm  High Warn  Low Warn   Low Alarm
           Optical     Optical       Threshold   Threshold  Threshold  Threshold
Port       Tx Power(dBm) Rx Power(dBm)  (dBm)       (dBm)      (dBm)      (dBm)
Te1/1/1    -2.3          -14.8          ...                  -11.0      -14.0     ← Rx ต่ำกว่า Low Alarm!
```
- **Tx Power** = แสงที่เราส่ง · **Rx Power** = แสงที่เรารับได้
- Rx ต่ำกว่า **Low Warning/Alarm** → แสงอ่อน: หัวไฟเบอร์สกปรก, สายงอ/หัก, ระยะไกลเกินชนิด SFP, SFP เสื่อม → ลิงก์จะมี CRC หรือขึ้นลง
- ค่า dBm ติดลบมากขึ้น = แสงอ่อนลง (-3 → -14 คืออ่อนลงมาก)

### err-disabled — พอร์ตถูกปิดอัตโนมัติ
```
SW01# show interfaces status err-disabled
Port      Name          Status       Reason               Err-disabled Vlans
Gi1/0/7   Printer-2F    err-disabled psecure-violation
```
| Reason | สาเหตุ | แก้ |
|---|---|---|
| `psecure-violation` | port-security: MAC เกินจำนวน/เปลี่ยนเครื่อง | ตรวจว่าเครื่องถูกต้อง → `shutdown` แล้ว `no shutdown` (หรือ clear port-security) |
| `bpduguard` | มีคนเสียบ **switch** ที่พอร์ตผู้ใช้ | เอา switch ออก แล้วเปิดพอร์ต |
| `loopback` / `link-flap` | สายวน/พอร์ตขึ้นลงถี่ | หาจุด loop/สายเสีย |

---

## 4. Switching: VLAN, Trunk, MAC, STP

### `show vlan brief`
```
VLAN Name                             Status    Ports
---- -------------------------------- --------- -------------------------------
1    default                          active    Gi1/0/48
20   USERS                            active    Gi1/0/2, Gi1/0/5, Gi1/0/6, Gi1/0/8
30   VOICE                            active
40   IOT                              active    Gi1/0/7
```
- แสดงเฉพาะ **พอร์ต access** — พอร์ต trunk ไม่ปรากฏที่นี่ (ดูด้วย `show interfaces trunk`)
- ถ้า VLAN ที่ต้องใช้ **ไม่อยู่ในรายการ** = ยังไม่ได้สร้างบน switch นี้ → พอร์ตใน VLAN นั้นใช้งานไม่ได้

### `show interfaces trunk` — ตรวจว่า VLAN วิ่งผ่าน uplink ได้ไหม ⭐
```
Port        Mode         Encapsulation  Status        Native vlan
Gi1/0/1     on           802.1q         trunking      999

Port        Vlans allowed on trunk
Gi1/0/1     10,20,40                                  ← (A) VLAN ที่อนุญาต — ไม่มี 30!

Port        Vlans allowed and active in management domain
Gi1/0/1     10,20,40                                  ← (B) อนุญาต + มีอยู่บน switch นี้

Port        Vlans in spanning tree forwarding state and not pruned
Gi1/0/1     10,20,40                                  ← (C) ส่งได้จริง
```
**ตัวอย่างการวิเคราะห์:** โทรศัพท์ (VLAN 30) ทั้งชั้นใช้ไม่ได้ → (A) ไม่มี VLAN 30 → traffic ของ VLAN 30 ข้าม uplink ไม่ได้ → แก้: `switchport trunk allowed vlan add 30`
> ⚠️ ต้องใช้ **`add`** — ถ้าพิมพ์ `switchport trunk allowed vlan 30` จะ **แทนที่** ทั้งรายการ VLAN อื่นหายหมด (ความผิดพลาดคลาสสิกที่ทำให้ทั้งชั้นล่ม)

### หาเครื่องจาก IP → MAC → พอร์ต ⭐
```
CORE01# show ip arp 10.0.20.77
Protocol  Address          Age (min)  Hardware Addr   Type   Interface
Internet  10.0.20.77              3   a4bb.6d11.2233  ARPA   Vlan20       ← ได้ MAC

CORE01# show mac address-table address a4bb.6d11.2233
          Mac Address Table
Vlan    Mac Address       Type        Ports
----    -----------       --------    -----
  20    a4bb.6d11.2233    DYNAMIC     Gi1/0/24                           ← อยู่ที่พอร์ต 24 ของ core

CORE01# show cdp neighbors Gi1/0/24
Device ID   Local Intrfce   Holdtme  Capability  Platform   Port ID
SW-2F       Gig 1/0/24      150      S I         C9200-48P  Gig 1/0/1    ← พอร์ตนั้นต่อไปที่ switch ชั้น 2

(ssh ไป SW-2F แล้วทำซ้ำ)
SW-2F# show mac address-table address a4bb.6d11.2233
  20    a4bb.6d11.2233    DYNAMIC     Gi1/0/17                           ← เจอแล้ว! พอร์ต 17 ของ SW-2F
```
- ถ้าพอร์ตที่เจอเป็น uplink/port-channel → เครื่องอยู่ "ถัดไป" ให้ตามต่อ
- ถ้าเจอ **MAC หลายตัวบนพอร์ตเดียว** (ไม่ใช่ uplink) → มี switch/hub/AP เล็ก ๆ หรือ VM ต่ออยู่หลังพอร์ตนั้น
- ถ้า MAC เดียว **ย้ายไปมาระหว่างสองพอร์ต** (ดู log `%SW_MATM-4-MACFLAP_NOTIF`) → **loop** หรือ NIC teaming ตั้งค่าผิด

### Spanning Tree: `show spanning-tree vlan 20`
```
VLAN0020
  Spanning tree enabled protocol rstp
  Root ID    Priority    4116
             Address     7c0e.ce00.0001
             Cost        4
             Port        1 (GigabitEthernet1/0/1)       ← ทางไป root ออกพอร์ตนี้
  Bridge ID  Priority    32788  (priority 32768 sys-id-ext 20)
             Address     7c0e.ce12.3400                  ← switch ตัวนี้ (ไม่ใช่ root)
Interface           Role Sts Cost      Prio.Nbr Type
------------------- ---- --- --------- -------- ------------------
Gi1/0/1             Root FWD 4         128.1    P2p          ← พอร์ตไปหา root, ส่งได้
Gi1/0/2             Altn BLK 4         128.2    P2p          ← พอร์ตสำรอง ถูก block (ปกติ! กัน loop)
Gi1/0/5             Desg FWD 4         128.5    P2p Edge     ← พอร์ตผู้ใช้ (Edge = PortFast)
```
**STP คืออะไรแบบสั้น:** เมื่อมีสายสำรองหลายเส้นจะเกิด "วน" (loop) ได้ STP จะ **ปิด (BLK) บางพอร์ตไว้** ให้เหลือเส้นทางเดียว และเปิดใช้เมื่อเส้นหลักเสีย
- **Root bridge ควรเป็น core switch** (ตั้ง priority ต่ำ) — ถ้า root เป็น access switch หรืออุปกรณ์แปลก ๆ = ออกแบบผิด/มีคนเสียบ switch ที่ priority ต่ำ
- `BLK` บนพอร์ตสำรองเป็นเรื่อง **ปกติ**
- ดูการเปลี่ยนแปลงบ่อย:
```
SW01# show spanning-tree detail | include ieee|occurr|from|is exec
 VLAN0020 is executing the rstp compatible Spanning Tree protocol
  Number of topology changes 1842 last change occurred 00:00:12 ago   ← เปลี่ยน 1,842 ครั้ง ล่าสุด 12 วินาทีก่อน!
          from GigabitEthernet1/0/9                                    ← เกิดจากพอร์ตนี้
```
→ topology change บ่อย = มีพอร์ตขึ้นลงบ่อย (เช่น เครื่องผู้ใช้ที่ไม่ได้ตั้ง PortFast, สายหลวม) ทำให้ทั้ง VLAN สะดุดเป็นช่วง ๆ → ไปดูพอร์ต Gi1/0/9

### EtherChannel: `show etherchannel summary`
```
Flags:  D - down        P - bundled in port-channel
        I - stand-alone s - suspended
        S - Layer2      U - in use
Group  Port-channel  Protocol    Ports
------+-------------+-----------+-----------------------------------
1      Po1(SU)         LACP      Te1/1/1(P)   Te1/1/2(P)       ← ✅ ปกติ: Po1 ใช้งาน, ทั้งสองพอร์ตรวมกลุ่ม
2      Po2(SU)         LACP      Te1/1/3(P)   Te1/1/4(s)       ← ⚠️ Te1/1/4 ถูก suspend (ตั้งค่าไม่ตรง)
```
- `(P)` = รวมอยู่ในกลุ่ม ✅ · `(s)` suspended / `(I)` stand-alone / `(D)` down = ปัญหา → ตรวจว่าทั้งสองฝั่งตั้ง speed/VLAN/mode (LACP active) ตรงกัน

---

## 5. Routing

### `show ip route` — ตารางเส้นทาง
```
CORE01# show ip route
Codes: L - local, C - connected, S - static, O - OSPF, B - BGP, D - EIGRP ...
Gateway of last resort is 10.0.0.254 to network 0.0.0.0      ← (1) default gateway ของ router

S*    0.0.0.0/0 [1/0] via 10.0.0.254                         ← (2)
      10.0.0.0/8 is variably subnetted, 12 subnets, 4 masks
C        10.0.20.0/24 is directly connected, Vlan20         ← (3)
L        10.0.20.1/32 is directly connected, Vlan20         ← (4)
O        10.1.0.0/16 [110/30] via 10.0.0.2, 01:12:44, GigabitEthernet1/0/48   ← (5)
B        10.16.0.0/12 [20/0] via 169.254.10.1, 3d04h        ← (6)
```
1. **Gateway of last resort** — ถ้าไม่มี route ที่ตรงเลย ส่งไปที่นี่ (ถ้าเขียนว่า `not set` = ไปอินเทอร์เน็ตไม่ได้)
2. **`S*`** = static route ที่เป็น default (`*` = ตัวเลือกสำหรับ default)
3. **`C` connected** — วงที่ router ต่ออยู่ตรง ๆ
4. **`L` local** — IP ของ router เอง (/32)
5. **`O` OSPF** — เรียนรู้จาก OSPF: `[110/30]` = **[Administrative Distance / Metric]**, `via 10.0.0.2` = ส่งให้ router นี้, `01:12:44` = route นี้เสถียรมา 1 ชั่วโมงกว่า (ถ้าเห็นเวลาสั้น ๆ เช่น `00:00:15` ซ้ำ ๆ = **route กระพือ/flap**)
6. **`B` BGP** — เรียนรู้จาก BGP (เช่น จาก AWS ผ่าน VPN)

**Administrative Distance (AD) คืออะไร:** ถ้ารู้เส้นทางไปวงเดียวกันจากหลายแหล่ง router เชื่อแหล่งที่ AD ต่ำกว่า: connected 0 → static 1 → eBGP 20 → EIGRP 90 → OSPF 110 → iBGP 200
**Metric คืออะไร:** ถ้ามาจากแหล่งเดียวกัน (เช่น OSPF ทั้งคู่) เลือกเส้นที่ metric (ต้นทุน) ต่ำกว่า

### ถามเจาะจง: ไป IP นี้ใช้เส้นไหน
```
CORE01# show ip route 10.1.5.20
Routing entry for 10.1.0.0/16
  Known via "ospf 1", distance 110, metric 30, type intra area
  Last update from 10.0.0.2 on GigabitEthernet1/0/48, 01:12:50 ago
  Routing Descriptor Blocks:
  * 10.0.0.2, from 10.255.0.2, 01:12:50 ago, via GigabitEthernet1/0/48
```
ถ้าตอบว่า `% Network not in table` และไม่มี default route → router **ไม่รู้ทาง** → packet ถูกทิ้ง

### OSPF Neighbor
```
CORE01# show ip ospf neighbor
Neighbor ID     Pri   State           Dead Time   Address         Interface
10.255.0.2        1   FULL/DR         00:00:35    10.0.0.2        Gi1/0/48     ← ✅
10.255.0.3        1   EXSTART/DROTHER 00:00:33    10.0.0.3        Gi1/0/47     ← ⚠️ ค้าง
```
**OSPF คืออะไรแบบสั้น:** router คุยกันเพื่อแลกแผนที่เครือข่ายอัตโนมัติ ต้องเป็น "เพื่อนบ้าน" (neighbor) ที่สถานะ **FULL** ก่อนจึงจะแลก route กันครบ
| State | ความหมาย | ถ้าค้างที่นี่ |
|---|---|---|
| (ไม่เห็นเลย) | ไม่ได้ยินกันเลย | ลิงก์/IP คนละวง, area ไม่ตรง, hello/dead timer ไม่ตรง, รหัสผ่าน OSPF ไม่ตรง, ACL บล็อก |
| INIT | ได้ยินอีกฝั่ง แต่อีกฝั่งไม่ได้ยินเรา | ปัญหาทิศทางเดียว/ACL |
| 2WAY | คุยกันได้ (บน LAN ระหว่าง router ที่ไม่ใช่ DR/BDR = **ปกติ**) | — |
| **EXSTART/EXCHANGE** | กำลังแลกข้อมูลแต่ไม่สำเร็จ | **MTU สองฝั่งไม่เท่ากัน** (สาเหตุอันดับ 1) |
| **FULL** | ✅ แลกข้อมูลครบ | — |
- **Dead Time** นับถอยหลัง ถ้าถึง 0 โดยไม่ได้ยิน hello → neighbor หลุด (ปกติจะรีเซ็ตกลับไป ~30–40 วินาทีเรื่อย ๆ)

### BGP Summary
```
CORE01# show ip bgp summary
Neighbor        V     AS  MsgRcvd MsgSent   TblVer InQ OutQ Up/Down  State/PfxRcd
169.254.10.1    4  64512    20553   20561      152   0    0 3d04h           12    ← ✅ รับมา 12 route
203.0.113.1     4  65001        0       0        1   0    0 never    Active       ← ⚠️ ยังไม่เชื่อมต่อ
```
**BGP คืออะไรแบบสั้น:** protocol แลก route ระหว่างองค์กร (เรา ↔ ISP, เรา ↔ cloud) ใช้ TCP port 179
- คอลัมน์สุดท้ายเป็น **ตัวเลข** = เชื่อมต่อแล้ว (จำนวน route ที่ได้รับ) ✅
- เป็น **คำ** (`Idle`, `Active`, `Connect`) = **ยังเชื่อมต่อไม่สำเร็จ** — ชื่อ `Active` ฟังเหมือนดีแต่จริง ๆ แปลว่า "กำลังพยายามเชื่อมต่ออยู่" ❗
  - สาเหตุ: IP ของ neighbor ผิด, AS ผิด, ping ไปหา neighbor ไม่ได้, firewall บล็อก TCP 179, รหัสผ่าน BGP ไม่ตรง
- `Up/Down` = เชื่อมต่อมานานเท่าไร (ถ้าเพิ่งไม่กี่นาทีทั้งที่ควรเสถียร = เพิ่ง flap)
- PfxRcd = 0 ทั้งที่ควรได้ → อีกฝั่งไม่ได้ประกาศ หรือเราตั้ง filter ไว้

### HSRP / VRRP — Gateway สำรอง
```
CORE01# show standby brief
Interface   Grp  Pri P State   Active          Standby         Virtual IP
Vl20        20   110 P Active  local           10.0.20.3       10.0.20.1     ← core01 เป็นตัวหลักของ VLAN 20
```
**HSRP คืออะไรแบบสั้น:** core 2 ตัวใช้ **IP gateway เสมือน** (10.0.20.1) ร่วมกัน ตัวหนึ่งทำงาน (Active) อีกตัวรอ (Standby) ถ้าตัวหลักเสียอีกตัวรับแทนทันที ผู้ใช้ไม่ต้องเปลี่ยน gateway
- ถ้าเห็น **Active ทั้งสองตัว** = สองตัวไม่ได้ยินกัน (ลิงก์ระหว่างกันเสีย/VLAN ไม่ผ่าน) → เกิดปัญหา
- `P` = preempt (ตัวที่ priority สูงกว่าจะยึดคืนเมื่อกลับมา)

---

## 6. Ping และ Traceroute บน Cisco — อ่านสัญลักษณ์

```
CORE01# ping 10.1.5.20 source Vlan20
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to 10.1.5.20, timeout is 2 seconds:
Packet sent with a source address of 10.0.20.1
.!!!!                                          ← packet แรก timeout เพราะรอ ARP (ปกติ)
Success rate is 80 percent (4/5), round-trip min/avg/max = 2/3/5 ms
```
| สัญลักษณ์ | ความหมาย |
|---|---|
| `!` | ได้คำตอบ ✅ |
| `.` | หมดเวลา ไม่มีคำตอบ |
| `U` | มีคนตอบว่าไปไม่ถึง (unreachable) |
| `M` | packet ใหญ่เกินแต่ห้าม fragment (ปัญหา MTU) |

### ทำไมต้องระบุ `source`
ถ้าไม่ระบุ router จะใช้ IP ของ interface ขาออก (เช่น IP ลิงก์ WAN 10.0.0.1) ซึ่งปลายทางอาจไม่มี route กลับ → timeout ทั้งที่ผู้ใช้ใช้งานได้ปกติ
การ `ping ... source Vlan20` = **ทดสอบแบบเดียวกับที่ผู้ใช้ใน VLAN 20 จะเจอ** (ทั้งขาไปและขากลับ)

### ทดสอบ MTU
```
ping 10.40.1.5 size 1500 df-bit
MMMMM            ← ใหญ่เกิน → ลดขนาดลงจนได้ ! เพื่อรู้ MTU จริง
```

---

## 7. ACL, NAT, VPN — อ่านผลอย่างไร

### ACL hit count
```
CORE01# show access-lists GUEST-IN
Extended IP access list GUEST-IN
    10 permit udp any any eq domain (1532 matches)
    20 deny ip any 10.0.0.0 0.255.255.255 log (88 matches)     ← guest พยายามเข้า network ภายใน 88 ครั้ง (ถูกบล็อก)
    30 permit ip any any (502331 matches)
```
- `matches` = จำนวน packet ที่ตรงกับบรรทัดนั้น — ใช้ยืนยันว่า traffic **ผ่าน/โดนบล็อกที่บรรทัดไหน**
- ACL อ่าน **จากบนลงล่าง หยุดที่บรรทัดแรกที่ตรง** และท้ายสุดมี **deny ที่มองไม่เห็น** (implicit deny)

### NAT translations
```
EDGE01# show ip nat translations
Pro Inside global        Inside local          Outside local      Outside global
tcp 203.0.113.10:40011   10.0.20.55:51544      142.250.1.1:443    142.250.1.1:443
```
- **Inside local** = IP จริงของเครื่องภายใน · **Inside global** = IP สาธารณะที่ถูกแปลงเป็น
- ถ้าผู้ใช้ออกเน็ตไม่ได้แล้วไม่เห็น translation ของเขาเลย → traffic ไม่ถึง router นี้ หรือไม่ตรงกับ ACL ของ NAT

### IPsec VPN
```
EDGE01# show crypto ipsec sa | include peer|pkts
   current_peer 198.51.100.20 port 4500
    #pkts encaps: 15233, #pkts encrypt: 15233        ← ส่งเข้าอุโมงค์ไปแล้ว 15,233
    #pkts decaps: 0, #pkts decrypt: 0                ← ได้กลับมา 0!
```
**encaps เพิ่มแต่ decaps = 0** → ฝั่งเราส่งไปแล้ว แต่ **อีกฝั่งไม่ส่งกลับ** → ตรวจฝั่งตรงข้าม: route กลับ, firewall policy, NAT exemption, subnet (selector) ไม่ตรง

---

## 8. จับ Packet บน Switch (EPC)

ใช้เมื่อต้องการพิสูจน์ว่า "packet มาถึงพอร์ตนี้จริงไหม"
```
monitor capture CAP interface Gi1/0/17 both            ← จับทั้งขาเข้าและขาออกของพอร์ต
monitor capture CAP match ipv4 host 10.0.20.77 any     ← เฉพาะเครื่องนี้
monitor capture CAP start
(ให้ผู้ใช้ลองใช้งาน)
monitor capture CAP stop
show monitor capture CAP buffer brief
  1  0.000000  10.0.20.77 -> 10.0.104.11  DNS 74 Standard query A intranet.corp.local
  2  0.001523  10.0.104.11 -> 10.0.20.77  DNS 90 Standard query response A 10.0.100.25
  3  0.002100  10.0.20.77 -> 10.0.100.25  TCP 66 51544 → 443 [SYN]
  4  1.004000  10.0.20.77 -> 10.0.100.25  TCP 66 [TCP Retransmission] 51544 → 443 [SYN]   ← ไม่มี SYN-ACK กลับ
monitor capture CAP export flash:cap.pcap              ← เอาไปเปิดใน Wireshark
no monitor capture CAP                                  ← ลบทิ้งเมื่อเสร็จ
```
อ่าน: DNS ทำงานปกติ แต่ TCP ไป 443 ไม่มีคำตอบ → ปัญหาอยู่หลัง switch นี้ (firewall/server)

---

## 9. แก้ config อย่างปลอดภัย

```
SW01# reload in 10                      ← ตั้งเวลา reboot ใน 10 นาที (ตาข่ายนิรภัย)
SW01# configure terminal
SW01(config)# ... แก้ไข ...
SW01(config)# end
(ทดสอบ: ยังเข้าถึงได้ไหม ระบบปกติไหม)
SW01# reload cancel                     ← ✅ ยกเลิก reboot
SW01# copy running-config startup-config  ← บันทึก
```
**ทำไมได้ผล:** การแก้ไขยังไม่ถูกบันทึก ถ้าพลาดจนตัดการเชื่อมต่อตัวเอง (เช่น แก้ ACL ผิด) เมื่อครบ 10 นาที switch จะ reboot และกลับไปใช้ config เดิมที่บันทึกไว้

- **running-config** = config ที่ใช้งานอยู่ใน RAM (หายเมื่อ reboot ถ้าไม่ save)
- **startup-config** = config ที่บันทึกไว้ ใช้ตอนเปิดเครื่อง

---

## 10. แบบฝึกหัด (ใช้ Packet Tracer/CML/EVE-NG)

1. สร้าง 2 switch + 1 router, VLAN 10/20 → รัน `show ip interface brief` และ `show vlan brief` อธิบายทุกบรรทัด
2. ถอด VLAN 20 ออกจาก allowed list ของ trunk (`switchport trunk allowed vlan remove 20`) → ดูผลใน `show interfaces trunk` และอาการที่ผู้ใช้เจอ แล้วแก้กลับ
3. ตั้ง duplex ไม่ตรงกันสองฝั่ง → ดู counters ใน `show interfaces` (late collision/CRC)
4. หาพอร์ตของ PC จาก IP โดยใช้ `show ip arp` → `show mac address-table` → `show cdp neighbors`
5. ตั้ง OSPF แล้วเปลี่ยน MTU ฝั่งหนึ่ง → ดู state ค้างที่ EXSTART
6. ตั้ง BGP ด้วย AS ผิด → ดู `show ip bgp summary` ค้างที่ Active/Idle และ log

<details><summary><b>แนวคำตอบข้อ 2, 5, 6</b></summary>

2. VLAN 20 หายจาก allowed list → ผู้ใช้ VLAN 20 บน switch ปลายทางไม่ได้ IP/ping gateway ไม่ได้ · แก้ `switchport trunk allowed vlan add 20`
5. Neighbor ค้าง EXSTART/EXCHANGE · แก้ให้ MTU เท่ากัน (หรือ `ip ospf mtu-ignore` ชั่วคราว ซึ่งไม่แนะนำในระยะยาว)
6. State เป็น Idle/Active ไม่เป็นตัวเลข และ log แสดงข้อความ bad remote AS/notification
</details>

⬅️ [Ping/Route](01-ping-traceroute-route-explained.md) · ➡️ ต่อไป: [อธิบายคำสั่ง FortiGate](03-fortigate-explained.md)
