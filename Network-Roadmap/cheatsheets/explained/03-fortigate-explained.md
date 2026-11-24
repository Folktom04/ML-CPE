# อธิบายละเอียด: คำสั่งตรวจเช็ค FortiGate

> คู่กับ cheat sheet [03-fortigate.md](../03-fortigate.md)
> อ่านจบแล้วจะ: เข้าใจโครงสร้างคำสั่งของ FortiOS · รู้ว่า FortiGate ประมวลผล packet ตามลำดับอย่างไร · อ่านผลของ routing table, session, debug flow, sniffer, VPN, SD-WAN, HA ได้ทีละบรรทัด · แก้ปัญหาที่พบบ่อยที่สุดได้เอง

---

## 1. โครงสร้างคำสั่ง FortiOS — 4 คำขึ้นต้น

| ขึ้นต้นด้วย | ใช้ทำอะไร | ความเสี่ยง | ตัวอย่าง |
|---|---|---|---|
| **`get`** | ดูสถานะ/ข้อมูลในรูปแบบที่อ่านง่าย | ไม่มี | `get system status` |
| **`show`** | ดู **config** (เฉพาะค่าที่ต่างจากค่าเริ่มต้น) | ไม่มี | `show firewall policy 15` |
| **`diagnose`** (`diag`) | ตรวจเชิงลึก, debug, ดู session, จับ packet | บางคำสั่ง **กระทบระบบ** (clear, debug โดยไม่กรอง) | `diag sys session list` |
| **`execute`** (`exe`) | สั่งให้ทำบางอย่าง | ขึ้นกับคำสั่ง (ping ปลอดภัย, reboot ไม่ปลอดภัย) | `exe ping 8.8.8.8` |
| `config` ... `end` | แก้ config | **เปลี่ยนระบบทันทีเมื่อ end** (ไม่มีขั้น commit) | `config system interface` |

> ⚠️ ต่างจาก Cisco: FortiGate **ใช้ config ทันทีและบันทึกอัตโนมัติ** เมื่อพิมพ์ `end` — ไม่มี "running vs startup" ให้ถอยกลับง่าย ๆ

### VDOM (Virtual Domain)
FortiGate หนึ่งเครื่องแบ่งเป็น "firewall เสมือน" หลายตัวได้ ถ้าเปิดใช้ VDOM:
```
FGT # config vdom
FGT (vdom) # edit root          ← เข้าไปใน VDOM ที่ต้องการก่อน แล้วค่อยใช้คำสั่ง routing/policy/session
FGT (root) # get router info routing-table all
FGT (root) # end
FGT # config global             ← คำสั่งระดับระบบ (HA, interface ฮาร์ดแวร์, admin)
```
ถ้าลืมเข้า VDOM จะเห็นผลว่างเปล่าหรือ error — เป็นเรื่องที่มือใหม่สับสนบ่อย

---

## 2. FortiGate ประมวลผล packet อย่างไร (เข้าใจตรงนี้ = อ่าน debug ออก)

```
 packet เข้า interface
   │
   ├─① ตรวจว่ามี session อยู่แล้วไหม ──── มี → ส่งต่อเลย (เร็ว, อาจทำใน NPU hardware)
   │                                     ไม่มี → เป็น packet แรกของ connection ใหม่:
   ├─② DNAT / VIP (แปลง IP ปลายทาง ถ้ามี virtual IP)
   ├─③ Routing lookup: ไปทางไหน ออก interface อะไร
   ├─④ Reverse path check: มี route กลับไปหา IP ต้นทางผ่าน interface ที่ packet เข้ามาไหม
   ├─⑤ Firewall policy: หา policy แรก (บนลงล่าง) ที่ตรงกับ incoming intf + outgoing intf + src + dst + service + schedule
   │      ไม่ตรงเลย → ทิ้ง (implicit deny / policy 0)
   ├─⑥ Security profiles (IPS, antivirus, web filter, app control...)
   ├─⑦ SNAT (แปลง IP ต้นทาง เช่น ออกอินเทอร์เน็ต)
   └─⑧ สร้าง session → ส่งออก interface
```
**ข้อสำคัญ:** ข้อ ③ เกิด **ก่อน** ข้อ ⑤ — FortiGate รู้ outgoing interface จาก routing ก่อน แล้วจึงหา policy ที่ตรงกับคู่ interface นั้น → **route ผิด = ไม่เจอ policy** แม้ policy จะเขียนไว้ถูก

---

## 3. `get system status` — ข้อมูลพื้นฐาน

```
FGT # get system status
Version: FortiGate-100F v7.2.8,build1639,240313 (GA.M)       ← (1) รุ่น + version FortiOS
Virus-DB: 92.03147(2026-11-23 18:24)                         ← (2) ฐานข้อมูล security อัปเดตล่าสุด
IPS-DB: 28.00812(2026-11-23 01:15)
Serial-Number: FG100FTK20012345                               ← (3)
License Status: Valid                                         ← (4)
VM Resources: ...
Log hard disk: Available
Hostname: FGT-HQ
Operation Mode: NAT                                           ← (5) NAT = ทำงานเป็น router/firewall (ปกติ)
Current virtual domain: root
Virtual domain configuration: disable                         ← (6) ไม่ได้ใช้ VDOM
Current HA mode: a-p, master                                  ← (7) HA แบบ active-passive และเครื่องนี้เป็นตัวหลัก
System time: Tue Nov 24 10:22:31 2026                         ← (8) เวลา — ต้องถูกต้อง!
```
1. **Version** — คำสั่งบางตัวต่างกันระหว่าง 6.x กับ 7.x, เช็คกับประกาศช่องโหว่ของ Fortinet (PSIRT)
2. **DB date** — ถ้าวันที่เก่ามาก = อัปเดตไม่ได้ (license หมด/ออกเน็ตไม่ได้/DNS เสีย) → การป้องกันไม่ทันภัยใหม่
4. **License** — Expired = security profile บางตัวหยุดทำงาน
5. **Operation Mode** — `Transparent` = ทำงานเหมือน bridge (ไม่มี routing ปกติ)
7. **HA mode** — standalone/a-p/a-a และบทบาท master(primary)/slave(secondary)
8. **System time** — เวลาผิดทำให้ log ผิด, VPN ที่ใช้ certificate ล้ม, การยืนยันตัวตนล้มเหลว

### `get system performance status`
```
CPU states: 12% user 8% system 0% nice 78% idle 0% iowait 2% irq 0% softirq   ← ใช้ CPU รวม ~22%
Memory: 3972164k total, 1688012k used (42.5%), ...                             ← memory 42.5%
Average network usage: 245678 / 238901 kbps in 1 minute, ...
Average sessions: 18432 sessions in 1 minute, ...                              ← จำนวน session
Average session setup rate: 210 sessions per second in last 1 minute, ...      ← session ใหม่ต่อวินาที
Uptime: 45 days, 3 hours, 12 minutes
```
- **Memory สูงเกิน ~80–88%** → FortiGate จะเข้า **conserve mode** (เพื่อปกป้องตัวเอง อาจหยุดตรวจ AV/proxy หรือไม่รับ session ใหม่ ตามการตั้งค่า) → ผู้ใช้เจอเว็บเข้าไม่ได้เป็นพัก ๆ · ดูด้วย `diagnose hardware sysinfo conserve`
- **session setup rate พุ่งผิดปกติ** → อาจมีเครื่องติดมัลแวร์สแกนเครือข่าย หรือถูกโจมตี
- **Uptime** สั้นผิดปกติ = เพิ่ง reboot (crash? ไฟดับ? HA failover?)

### `diagnose sys top`
แสดง process ที่ใช้ CPU/memory แบบ real-time (กด `q` ออก) — process ที่มักเห็นสูง: `ipsengine` (IPS), `wad` (proxy/SSL inspection), `scanunitd` (antivirus), `miglogd` (log), `httpsd` (GUI)

---

## 4. Interface — ดูความผิดปกติของพอร์ต

### `diagnose hardware deviceinfo nic port1` ⭐
```
Name:            port1
Driver:          ...
State:           up                         ← link ขึ้น
Link:            up
Speed:           1000                       ← 1 Gbps
Duplex:          full                       ← ต้องเป็น full
...
Rx_Packets:      1824301234
Tx_Packets:      1702299871
Rx_Errors:       0
Rx_CRC_Errors:   1834                       ← ⚠️ frame เสียหายเข้ามา
Rx_Dropped:      0
Tx_Errors:       0
Tx_Dropped:      0
```
- **Speed/Duplex** ไม่ตรงกับที่คาด (เช่น 100/half บนลิงก์ ISP 1G) → สาย/พอร์ต ISP/การ auto-negotiation
- **CRC errors เพิ่มขึ้น** → สาย, หัว, SFP, หรือพอร์ตฝั่งตรงข้าม
- **Dropped** เพิ่ม → รับไม่ทัน/ลิงก์เต็ม
(ชื่อ field ต่างกันเล็กน้อยตามรุ่นฮาร์ดแวร์)

### ARP: `get system arp`
```
Address           Age(min)   Hardware Addr      Interface
10.0.20.55        0          a4:bb:6d:11:22:33  internal
203.0.113.1       2          00:1b:21:aa:bb:cc  wan1        ← gateway ของ ISP ต้องมี MAC ถ้าเชื่อมต่อได้
```
ถ้า **gateway ของ ISP ไม่มีใน ARP** → FortiGate คุยกับ router ของ ISP ไม่ได้เลย (สาย, VLAN ของ ISP, IP/mask ผิด) — ยังไม่ต้องไปดู routing/policy

---

## 5. Routing Table

### `get router info routing-table all`
```
FGT # get router info routing-table all
Codes: K - kernel, C - connected, S - static, R - RIP, B - BGP, O - OSPF, ...
       * - candidate default

Routing table for VRF=0
S*      0.0.0.0/0 [10/0] via 203.0.113.1, wan1, [1/0]                ← (1)
                  [10/0] via 198.51.100.1, wan2, [1/0]                ← (2)
C       10.0.0.0/24 is directly connected, port3                     ← (3)
C       10.0.20.0/24 is directly connected, internal
S       10.1.0.0/16 [10/0] via VPN-CNX tunnel 198.51.100.20, [1/0]   ← (4)
O       10.30.0.0/16 [110/20] via 10.0.0.2, port3, 00:45:12          ← (5)
B       10.16.0.0/12 [20/100] via 169.254.10.1 (recursive via VPN-AWS tunnel 52.x.x.1), 1d02h   ← (6)
```
1. **Default route ผ่าน wan1** — `[10/0]` = [distance/metric], `[1/0]` ท้าย = [priority/weight]
2. Default route อีกเส้นผ่าน wan2 ที่ distance **เท่ากัน** → ใช้ทั้งสองเส้นพร้อมกัน (ECMP) — ถ้าต้องการให้ wan2 เป็นสำรอง ต้องตั้ง distance สูงกว่า หรือใช้ SD-WAN
3. **Connected** — วงที่ต่ออยู่ตรง
4. **Static route ผ่าน VPN tunnel** — ไปสาขาเชียงใหม่ผ่าน VPN (สำคัญมาก: **ถ้าไม่มีบรรทัดนี้ traffic ไปสาขาจะออก default route ไปอินเทอร์เน็ตแทน** และไม่เจอ policy VPN)
5. **OSPF** — `00:45:12` = อายุ route
6. **BGP ผ่าน VPN** — เช่น route จาก AWS

**ข้อควรรู้:** route ที่ interface **down** (เช่น VPN ล่ม, link monitor ตรวจว่า gateway ตาย) จะ **หายไปจากตารางนี้** และ route ที่ distance สูงกว่า (สำรอง) จะขึ้นมาแทน — ถ้าอยากเห็น route ทั้งหมดรวมที่ไม่ได้ใช้ ใช้ `get router info routing-table database` (บรรทัดที่มี `>` = ถูกเลือกใช้)

### ถามเจาะจง
```
FGT # get router info routing-table details 10.1.5.20
Routing table for VRF=0
Routing entry for 10.1.0.0/16
  Known via "static", distance 10, metric 0, best
  * vrf 0 via VPN-CNX tunnel 198.51.100.20
```
บอกตรง ๆ ว่า packet ไป 10.1.5.20 จะออกทาง VPN-CNX — ถ้าออกทาง wan1 แทน = **ลืมใส่ route ไป VPN**

---

## 6. Ping จาก FortiGate — ทำไมต้องตั้ง source

```
FGT # execute ping 10.1.5.20
PING 10.1.5.20 (10.1.5.20): 56 data bytes
--- 10.1.5.20 ping statistics ---
5 packets transmitted, 0 packets received, 100% packet loss     ← ไม่ผ่าน?!
```
ไม่ได้แปลว่า VPN เสียเสมอ! เพราะ FortiGate ใช้ IP ของ **interface ขาออก** (อาจเป็น IP ของ tunnel หรือ wan) เป็นต้นทาง ซึ่ง:
- ไม่อยู่ใน phase 2 selector ของ VPN (อีกฝั่งไม่ยอมรับ)
- ฝั่งตรงข้ามไม่มี route กลับไปหา IP นั้น
```
FGT # execute ping-options source 10.0.20.1      ← ใช้ IP ของวงภายใน (internal) เป็นต้นทาง
FGT # execute ping 10.1.5.20
64 bytes from 10.1.5.20: icmp_seq=0 ttl=63 time=8.4 ms        ← ผ่าน ✅ = VPN ใช้งานได้จริง
FGT # execute ping-options reset                ← คืนค่าเมื่อเสร็จ
```
**ทดสอบ port จาก FortiGate:** `execute telnet 10.1.5.20 443` → ถ้าขึ้น `Connected to 10.1.5.20` = port เปิด (กด Ctrl+C ออก)

---

## 7. Session — "สมุดบันทึก" การเชื่อมต่อทั้งหมด

ทุกการเชื่อมต่อที่ผ่าน FortiGate จะมี **session** บันทึกว่าใครคุยกับใคร ผ่าน policy ไหน NAT เป็นอะไร

### ดูเฉพาะที่สนใจ (ต้องตั้ง filter เสมอ — อาจมีหลายแสน session)
```
FGT # diagnose sys session filter clear
FGT # diagnose sys session filter src 10.0.20.55
FGT # diagnose sys session filter dport 443
FGT # diagnose sys session list
```
### ตัวอย่างผลลัพธ์ (ย่อเฉพาะส่วนสำคัญ)
```
session info: proto=6 proto_state=01 duration=35 expire=3564 timeout=3600 ...    ← (1)
...
statistic(bytes/packets/allow_err): org=18432/120/1 reply=245112/180/1 tuples=2   ← (2)
...
orgin->sink: org pre->post, reply pre->post dev=5->7/7->5 gwy=203.0.113.1/10.0.20.55
hook=post dir=org act=snat 10.0.20.55:51544->142.250.1.1:443(203.0.113.10:40011)  ← (3)
hook=pre dir=reply act=dnat 142.250.1.1:443->203.0.113.10:40011(10.0.20.55:51544)
...
misc=0 policy_id=15 ...                                                            ← (4)
npu_state=0x000c00 ...                                                             ← (5)
```
1. **proto=6** = TCP (17 = UDP, 1 = ICMP) · **proto_state=01** สำหรับ TCP = established (เชื่อมต่อสมบูรณ์) · `duration` เปิดมานานเท่าไร · `expire` เหลือเวลาก่อนหมดอายุถ้าไม่มี traffic
2. **org** = ขาไป (จากผู้เริ่มเชื่อมต่อ) · **reply** = ขากลับ
   - ⭐ **reply = 0/0** → **ไม่มีอะไรตอบกลับมาเลย** → ปลายทางไม่ตอบ, ถูกบล็อกหลังจาก FortiGate, หรือขากลับไปทางอื่น (asymmetric)
3. **act=snat** — แปลง IP ต้นทาง 10.0.20.55 เป็น **203.0.113.10** (IP สาธารณะ) เพื่อออกเน็ต
4. **policy_id=15** — ⭐ ผ่าน **policy หมายเลข 15** (ใช้ตรวจว่าตรง policy ที่ตั้งใจไหม)
5. **npu_state** — มีค่า = session ถูกส่งให้ **hardware (NPU) เร่งความเร็ว** → packet ถัดไปจะไม่ผ่าน CPU (ทำให้ sniffer/debug มองไม่เห็นบางส่วน)

### ล้าง session (ใช้เมื่อเปลี่ยน policy/route แล้ว session เก่ายังค้าง)
```
diagnose sys session filter src 10.0.20.55     ← ⚠️ ต้องตั้ง filter ก่อนเสมอ
diagnose sys session clear                     ← ลบเฉพาะที่ตรง filter
```
> 🚨 ถ้ารัน `clear` **โดยไม่มี filter** = **ตัดการเชื่อมต่อของผู้ใช้ทุกคนทันที** (รวมถึง SSH ที่คุณใช้อยู่)
> ตรวจ filter ปัจจุบันได้ด้วย `diagnose sys session filter` (ไม่ต้องใส่อะไรต่อ)

---

## 8. Debug Flow — เครื่องมือที่สำคัญที่สุด ⭐

ดูว่า FortiGate **ตัดสินใจอะไร** กับ packet ทีละขั้น (ตามลำดับในข้อ 2) — ตอบคำถาม "ทำไมผ่าน/ไม่ผ่าน" ได้แทบทุกกรณี

### ขั้นตอน
```
diagnose debug reset                               ← ล้าง debug เก่า
diagnose debug flow filter clear
diagnose debug flow filter addr 10.0.20.55         ← เฉพาะ IP นี้ (สำคัญ: ไม่กรอง = log ล้นจอ CPU สูง)
diagnose debug flow filter port 443                ← (ถ้าต้องการ) เฉพาะ port
diagnose debug flow show function-name enable      ← แสดงชื่อขั้นตอน
diagnose debug console timestamp enable            ← แสดงเวลา
diagnose debug flow trace start 20                 ← เก็บแค่ 20 packet
diagnose debug enable                              ← เริ่ม!
   (ให้ผู้ใช้ลองเชื่อมต่อ หรือ ping จากเครื่องผู้ใช้)
diagnose debug disable                             ← หยุด
diagnose debug reset
```

### ตัวอย่าง ① — ผ่านปกติ
```
id=65308 trace_id=1 func=print_pkt_detail line=5895 msg="vd-root:0 received a packet(proto=6, 10.0.20.55:51544->10.0.100.25:443) tun_id=0.0.0.0 from internal. flag [S], seq 1000, ..."
id=65308 trace_id=1 func=init_ip_session_common line=6076 msg="allocate a new session-0012abcd"
id=65308 trace_id=1 func=vf_ip_route_input_common line=2605 msg="find a route: flag=04000000 gw-10.0.0.2 via port3"
id=65308 trace_id=1 func=fw_forward_handler line=930 msg="Allowed by Policy-22:"
```
อ่านทีละบรรทัด:
1. **received a packet** — ได้รับ packet: TCP (proto=6) จาก 10.0.20.55 port 51544 ไป 10.0.100.25 port 443, เข้ามาทาง interface `internal`, `flag [S]` = SYN (packet แรกของการเชื่อมต่อ)
2. **allocate a new session** — สร้าง session ใหม่ (เป็น connection ใหม่)
3. **find a route** — routing บอกว่าออกทาง **port3** ไปหา gateway 10.0.0.2
4. **Allowed by Policy-22** ✅ — ผ่าน policy 22

### ตัวอย่าง ② — ไม่มี policy (ปัญหาที่พบบ่อยที่สุด)
```
msg="received a packet(proto=6, 10.0.50.12:50122->10.0.100.25:3389) from guest. flag [S] ..."
msg="allocate a new session-0012ac01"
msg="find a route: flag=04000000 gw-10.0.0.2 via port3"
msg="Denied by forward policy check (policy 0)"
```
**อธิบาย:** route หาเจอ (ออก port3) แต่ **ไม่มี policy ใดที่อนุญาต** guest → port3 ไป RDP (3389) จึงตกไปที่ "policy 0" = **implicit deny** (กฎท้ายสุดที่ปฏิเสธทุกอย่าง)
**ทำอะไรต่อ:** ถ้าควรอนุญาต → ตรวจ policy: incoming interface ถูกไหม (guest), outgoing (port3), address ครอบคลุม IP ไหม, service มี RDP ไหม, schedule, และลำดับ policy · ถ้าไม่ควรอนุญาต → ระบบทำงานถูกแล้ว ✅

### ตัวอย่าง ③ — Reverse path check fail
```
msg="received a packet(proto=1, 172.16.5.10:1->10.0.20.55:2048) from port3. type=8, code=0, id=1, seq=1."
msg="allocate a new session-0012ac55"
msg="reverse path check fail, drop"
```
**อธิบาย:** packet จาก 172.16.5.10 เข้ามาทาง port3 แต่ FortiGate ดู routing table แล้ว **ไม่มี route กลับไปหา 172.16.5.10 ผ่าน port3** (ไม่มี route เลย หรือ route ชี้ไปทาง interface อื่น) → FortiGate คิดว่าอาจเป็น IP ปลอม (anti-spoofing) จึงทิ้ง
**ทำอะไรต่อ:** เพิ่ม route ไป 172.16.0.0/x ผ่าน port3 (ถ้าเป็นเครือข่ายจริงที่อยู่หลัง port3) · ตรวจ asymmetric routing (ขาไปออกทางหนึ่ง ขากลับเข้ามาอีกทาง)

### ตัวอย่าง ④ — ไม่มี session (asymmetric routing)
```
msg="received a packet(proto=6, 10.0.100.25:443->10.0.20.55:51544) from port3. flag [S.], seq 5000, ack 1001 ..."
msg="no session matched"
```
**อธิบาย:** FortiGate ได้รับ **SYN-ACK** (`[S.]` = ขาตอบกลับ) แต่ไม่มี session — เพราะ **ขาไป (SYN) ไม่ได้ผ่านเครื่องนี้** (ไปทางอื่น เช่น ผ่าน router อีกตัวหรือ firewall อีกเครื่อง) → stateful firewall ทิ้ง
**ทำอะไรต่อ:** ปรับ routing ให้ขาไปและขากลับผ่าน FortiGate เดียวกัน

### ตัวอย่าง ⑤ — ไปเข้า VPN
```
msg="find a route: flag=04000000 gw-198.51.100.20 via VPN-CNX"
msg="Allowed by Policy-30:"
msg="enter IPSec interface-VPN-CNX"
msg="encrypted, and send to 198.51.100.20 with source 203.0.113.10"
```
ผ่าน policy และถูกเข้ารหัสส่งไปสาขาเรียบร้อย ✅ → ถ้าผู้ใช้ยังใช้ไม่ได้ ปัญหาอยู่ที่ **อีกฝั่ง** (policy/route ขากลับของสาขา)

### ตัวอย่าง ⑥ — SNAT
```
msg="Allowed by Policy-15: SNAT"
msg="SNAT 10.0.20.55->203.0.113.10:40011"
```
ออกอินเทอร์เน็ตด้วย IP 203.0.113.10 — ถ้าปลายทาง (เช่น ระบบของพาร์ทเนอร์) อนุญาตเฉพาะ IP อื่น ต้องใช้ IP pool ที่ถูกต้อง

### สรุปข้อความที่ต้องจำ
| ข้อความ | ปัญหาอยู่ที่ |
|---|---|
| `Denied by forward policy check (policy 0)` | **Policy** (ไม่มี/ไม่ตรง) |
| `reverse path check fail` | **Route กลับ** ไปหาต้นทาง |
| `no session matched` | **Asymmetric routing** / session หมดอายุ |
| `find a route ... via <interface ผิด>` | **Routing table** |
| `iprope_in_check() check failed on policy 0` | ไปหา IP ของ FortiGate เอง แต่ไม่อนุญาต (เช่น ping/HTTPS ไปที่ interface ที่ไม่ได้เปิด administrative access) |
| ไม่มีข้อความอะไรเลย | **packet ไม่มาถึง FortiGate** → ปัญหาอยู่ก่อนหน้า (เครื่อง/switch/route ของเครื่องผู้ใช้) หรือ filter ผิด |

---

## 9. Sniffer — เห็น packet เข้า/ออกจริง

```
FGT # diagnose sniffer packet any 'host 10.0.20.55 and port 443' 4 20 l
interfaces=[any]
filters=[host 10.0.20.55 and port 443]
2026-11-24 10:30:01.120 internal in 10.0.20.55.51544 -> 10.0.100.25.443: syn 1000        ← เข้ามาทาง internal
2026-11-24 10:30:01.120 port3 out 10.0.20.55.51544 -> 10.0.100.25.443: syn 1000          ← ออกไปทาง port3 ✅
2026-11-24 10:30:02.121 internal in 10.0.20.55.51544 -> 10.0.100.25.443: syn 1000        ← ส่งซ้ำ
2026-11-24 10:30:02.121 port3 out 10.0.20.55.51544 -> 10.0.100.25.443: syn 1000
```
### อ่านผล
- **ระดับ verbose 4** = แสดง **ชื่อ interface + ทิศทาง** (`in` / `out`) — สำคัญที่สุด
- packet เข้า `internal` → ออก `port3` = FortiGate **ส่งต่อแล้ว** ✅
- แต่ **ไม่มี syn-ack กลับมาทาง port3** → server (หรืออุปกรณ์หลัง port3) **ไม่ตอบ** → ปัญหาไม่ได้อยู่ที่ FortiGate แล้ว → ไปตรวจ server/firewall ของ server/route กลับของ server
| เห็น | สรุป |
|---|---|
| `in` แต่ไม่มี `out` | FortiGate **ทิ้ง** → ใช้ debug flow หาเหตุผล |
| `in` + `out` ไม่มีขากลับ | ปลายทาง/ทางกลับมีปัญหา |
| ไม่เห็นอะไรเลย | packet **ไม่มาถึง** FortiGate (หรือถูก offload ไป NPU หลังจาก packet แรก) |
| `in` + `out` + ขากลับ `in` + `out` | network ปกติ → ปัญหาที่แอป |

พารามิเตอร์: `'<filter>'` ใช้รูปแบบเดียวกับ tcpdump (`host`, `net 10.0.0.0/8`, `port`, `icmp`, `and`, `or`, `not`) · `4` = verbose · `20` = จำนวน packet (0 = ไม่จำกัด, Ctrl+C หยุด) · `l` = แสดงเวลาท้องถิ่น

---

## 10. IPsec VPN — อ่านสถานะ

### `get vpn ipsec tunnel summary`
```
'VPN-CNX' 198.51.100.20:0  selectors(total,up): 1/1  rx(pkt,err): 15233/0  tx(pkt,err): 15240/0
'VPN-KKC' 198.51.100.30:0  selectors(total,up): 1/0  rx(pkt,err): 0/0      tx(pkt,err): 0/0
```
- **VPN-CNX**: selectors **1/1** = phase 2 ขึ้นครบ ✅, rx/tx มีตัวเลข = มี traffic ทั้งสองทาง
- **VPN-KKC**: selectors **1/0** = มี phase 2 1 ชุด แต่ **ขึ้น 0 ชุด** ❌ → tunnel ไม่ทำงาน

### 2 Phase ของ IPsec (เข้าใจก่อน debug)
```
 Phase 1 (IKE): สองฝั่ง "ยืนยันตัวตน + ตกลงวิธีเข้ารหัส" สร้างช่องทางคุยที่ปลอดภัย
                ต้องตรงกัน: IP ของ peer, Pre-shared key/certificate, encryption, hash, DH group, IKE version
 Phase 2 (IPsec): ตกลงว่า "subnet ไหนคุยกับ subnet ไหน" (selector) และเข้ารหัส traffic จริง
                ต้องตรงกัน: local/remote subnet (สลับกันสองฝั่ง), encryption, PFS
```
### `diagnose vpn tunnel list name VPN-CNX` (ส่วนสำคัญ)
```
name=VPN-CNX ver=2 serial=1 203.0.113.10:4500->198.51.100.20:4500 ...
...
proxyid_num=1 child_num=0 refcnt=8 ilast=1 olast=1 ...
proxyid=VPN-CNX-P2 proto=0 sa=1 ref=2 serial=1
  src: 0:10.0.0.0/255.255.0.0:0                       ← subnet ฝั่งเรา
  dst: 0:10.1.0.0/255.255.0.0:0                       ← subnet ฝั่งสาขา
  SA:  ref=3 options=... life: type=01 bytes=0/0 timeout=42897/43200
  dec: spi=8a2b3c4d esp=aes key=32 ... pkts=15233     ← ถอดรหัส (รับเข้า) 15,233 packet
  enc: spi=c4d5e6f7 esp=aes key=32 ... pkts=15240     ← เข้ารหัส (ส่งออก) 15,240 packet
```
| เห็น | ความหมาย |
|---|---|
| `sa=1` | phase 2 ขึ้น ✅ · `sa=0` = ไม่ขึ้น |
| enc เพิ่ม, dec เพิ่ม | ส่งและรับได้ ✅ |
| **enc เพิ่ม แต่ dec = 0** | เราส่งไปแล้ว **อีกฝั่งไม่ส่งกลับ** → ตรวจฝั่งสาขา: policy, route กลับ, ไม่ควรมี NAT |
| enc = 0 | traffic จากฝั่งเรา **ไม่ได้ถูกส่งเข้า tunnel** → ตรวจ route ไป 10.1.0.0/16 ผ่าน VPN-CNX และ policy |

### อาการ IKE debug ที่พบบ่อย (เมื่อ tunnel ไม่ขึ้น)
| เห็นใน `diagnose debug application ike -1` | แปลว่า |
|---|---|
| `no SA proposal chosen` | ตั้ง encryption/hash/DH ไม่ตรงกัน → ให้ทั้งสองฝั่งเทียบค่า phase 1/phase 2 |
| `probable pre-shared secret mismatch` / `authentication failed` | **รหัส PSK ไม่ตรง** (หรือ peer ID) |
| `TS_UNACCEPTABLE` / `no matching phase2 found` | **subnet (selector) ไม่ตรงกัน** — ฝั่งเราเขียน local 10.0.0.0/16 remote 10.1.0.0/16 อีกฝั่งต้องเขียนกลับกัน |
| ส่ง ไม่มีคำตอบกลับ (`negotiation timeout`) | packet ไม่ถึงอีกฝั่ง: UDP 500/4500 ถูก ISP/firewall บล็อก, IP peer ผิด |

---

## 11. SD-WAN — ดูคุณภาพของแต่ละลิงก์

### `diagnose sys sdwan health-check status`
```
Health Check(Ping-Google):
Seq(1 wan1): state(alive), packet-loss(0.000%) latency(12.512), jitter(0.845), mos(4.395), bandwidth-up(...), sla_map=0x1
Seq(2 wan2): state(alive), packet-loss(6.000%) latency(85.204), jitter(25.112), mos(3.210), bandwidth-up(...), sla_map=0x0
```
- **SD-WAN คืออะไรแบบสั้น:** มีหลายลิงก์อินเทอร์เน็ต FortiGate วัดคุณภาพแต่ละลิงก์ตลอด แล้วเลือกลิงก์ที่ดีที่สุดให้แต่ละแอป (เช่น Teams ไปลิงก์ที่ latency ต่ำ)
- **state(alive/dead)** — ลิงก์ใช้งานได้ไหม (dead = probe ไม่ผ่านเลย)
- **packet-loss / latency / jitter** — คุณภาพปัจจุบัน
- **sla_map=0x1** = ผ่านเกณฑ์ SLA ที่ตั้งไว้ · **0x0** = ไม่ผ่าน → ระบบจะย้ายแอปที่ต้องการคุณภาพไปลิงก์อื่น
- ในตัวอย่าง: wan2 มี loss 6%, jitter 25 ms → ไม่เหมาะกับเสียง/วิดีโอ → ติดต่อ ISP ของ wan2

### `diagnose sys sdwan service4`
แสดงว่าแต่ละกฎ SD-WAN (เช่น "Teams" หรือ "ERP") **กำลังใช้ลิงก์ไหน** — ใช้ตอบคำถาม "ทำไม Teams ไปออก wan2"

---

## 12. HA — สองเครื่องทำงานเป็นคู่

### `get system ha status`
```
HA Health Status: OK                                    ← (1)
Model: FortiGate-100F
Mode: HA A-P                                            ← active-passive
Group: 0
Debug: 0
Cluster Uptime: 45 days 3:12:20
Cluster state change time: 2026-10-10 02:15:33         ← (2) เปลี่ยนบทบาทครั้งล่าสุดเมื่อไร
Primary selected using:                                 ← (3) เหตุผลที่เลือกเครื่องนี้เป็นตัวหลัก
    <2026/10/10 02:15:33> FG100FTK20012345 is selected as the primary because it has the largest value of uptime.
ses_pickup: enable                                      ← session ถูก sync ไปเครื่องสำรอง (failover แล้ว connection ไม่หลุด)
Configuration Status:
    FG100FTK20012345(updated 3 seconds ago): in-sync    ← (4) config ตรงกัน ✅
    FG100FTK20067890(updated 1 seconds ago): in-sync
Primary     : FGT-HQ-1 , FG100FTK20012345, HA cluster index = 0
Secondary   : FGT-HQ-2 , FG100FTK20067890, HA cluster index = 1
```
1. **HA Health Status** — ถ้าไม่ OK จะบอกปัญหา (เช่น heartbeat ขาด, monitored interface down)
2. **state change time** — ถ้าเพิ่งเปลี่ยนเมื่อไม่กี่นาที = **เพิ่ง failover** → หาสาเหตุ (เครื่องหลัก reboot? พอร์ตที่ monitor down?)
3. เหตุผลของการเลือก primary (priority, uptime, จำนวนพอร์ตที่ monitor และยัง up)
4. **in-sync / out-of-sync** — out-of-sync = config สองเครื่องไม่ตรงกัน → ถ้า failover เครื่องสำรองอาจทำงานไม่เหมือนเดิม! ตรวจละเอียดด้วย `diagnose sys ha checksum cluster` (checksum ต้องเท่ากันทุกตัว)

---

## 13. กรณีศึกษา: "สาขาขอนแก่นเข้าระบบ ERP ที่ HQ ไม่ได้"

ข้อมูล: ผู้ใช้สาขาอยู่วง 10.2.20.0/24 · ERP อยู่ที่ HQ IP 10.0.100.25 port 443 · ทำงานที่ FortiGate ของสาขา
```
ขั้น 1  get vpn ipsec tunnel summary
        'VPN-HQ' 203.0.113.10:0  selectors(total,up): 1/1  rx(pkt,err): 0/0  tx(pkt,err): 0/0
        → tunnel ขึ้นแล้ว (1/1) แต่ไม่มี traffic เข้า tunnel เลย (tx = 0)

ขั้น 2  diagnose debug flow filter addr 10.0.100.25 → trace start 10 → debug enable (ให้ผู้ใช้เปิด ERP)
        msg="received a packet(proto=6, 10.2.20.55:50100->10.0.100.25:443) from internal. flag [S]"
        msg="find a route: flag=04000000 gw-198.51.100.1 via wan1"         ← ❗ ออกทาง wan1 (อินเทอร์เน็ต) ไม่ใช่ VPN
        msg="Allowed by Policy-5: SNAT"                                     ← ผ่าน policy ออกเน็ต แล้วหายไปในอินเทอร์เน็ต

ขั้น 3  get router info routing-table details 10.0.100.25
        Routing entry for 0.0.0.0/0 ... via 198.51.100.1, wan1               ← ใช้ default route เพราะไม่มี route ไป 10.0.0.0/16

สาเหตุ   ไม่มี static route ไป 10.0.0.0/16 ผ่าน VPN-HQ (เช่น ถูกลบตอนแก้ config หรือลืมใส่ตอนติดตั้ง)
แก้      เพิ่ม static route 10.0.0.0/16 → device VPN-HQ (และตรวจว่ามี policy internal → VPN-HQ)
ยืนยัน   ทดสอบใหม่ → debug flow ต้องเห็น "via VPN-HQ" + "enter IPSec interface" และ tunnel summary tx/rx เพิ่มขึ้น
```
**บทเรียน:**
- สถานะ tunnel "ขึ้น" ไม่ได้แปลว่าใช้งานได้ — ต้องดูว่ามี traffic เข้า/ออก tunnel (tx/rx, enc/dec)
- debug flow บอกครบทั้ง "ไปทางไหน" และ "ผ่าน policy อะไร" ในคำสั่งเดียว
- ถ้า tx เพิ่มแต่ rx = 0 → ไปตรวจ **อีกฝั่ง** ด้วยวิธีเดียวกัน (policy/route ขากลับของ HQ)

---

## 14. ข้อควรระวังทุกครั้ง

1. **debug ต้องมี filter** และ **ปิดเมื่อเสร็จ** (`diagnose debug disable` + `diagnose debug reset`) — ลืมปิดทำให้ CPU สูงต่อเนื่อง
2. **`diagnose sys session clear` ต้องตั้ง filter ก่อน** — ไม่งั้นตัดทุกคน
3. `config ... end` มีผลทันที — แก้บนระบบจริงตาม change process และ backup ก่อน (`execute backup config ...`)
4. ระวังข้อมูลส่วนบุคคลใน sniffer/log เวลาส่งให้คนอื่น
5. คำสั่งบางตัวต่างตาม version — ใช้ `?` ช่วย หรือดู CLI Reference ของ version นั้น

---

## 15. แบบฝึกหัด (ใช้ FortiGate VM trial ใน lab)

1. รัน `get system status` และ `get system performance status` อธิบายทุกค่า
2. สร้าง policy ให้ LAN ออกเน็ต แล้ว ping จาก PC — ดู session ด้วย filter และหา policy_id, SNAT IP
3. ลบ policy ชั่วคราว ทดสอบใหม่ แล้วจับ debug flow — ต้องเห็น `policy 0`
4. ส่ง ping จากเครือข่ายที่ไม่มี route กลับ — ดู `reverse path check fail`
5. สร้าง VPN สองเครื่องแล้วตั้ง PSK ผิด — ดู IKE debug · แก้ PSK แล้วตั้ง subnet ไม่ตรง — ดูอาการ phase 2
6. ใช้ sniffer ยืนยันว่า packet `in` และ `out` ผ่าน FortiGate

⬅️ [Cisco](02-cisco-explained.md) · ➡️ ต่อไป: [อธิบาย Palo Alto / Check Point](04-paloalto-checkpoint-explained.md)
