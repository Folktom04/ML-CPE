# อธิบายละเอียด: Palo Alto, Check Point และ Linux Firewall

> คู่กับ cheat sheet [04-paloalto-checkpoint.md](../04-paloalto-checkpoint.md)
> อ่านจบแล้วจะ: เข้าใจว่า firewall ทุกยี่ห้อ "คิด" แบบเดียวกัน · ใช้คำสั่งของ Palo Alto และ Check Point ตอบคำถามเดียวกับที่ใช้ debug flow ของ FortiGate · อ่านผลสำคัญได้

---

## 1. Firewall ทุกยี่ห้อตอบ 5 คำถามเดียวกัน

| คำถาม | ทำไมสำคัญ | Palo Alto | Check Point | FortiGate (เทียบ) |
|---|---|---|---|---|
| ① packet **มาถึง** firewall ไหม | ถ้าไม่มาถึง ปัญหาอยู่ก่อนหน้า | packet-diag (receive) | `fw monitor` / `tcpdump` | sniffer |
| ② จะ **ออกทางไหน** | route ผิด = เจอ policy ผิดคู่ zone | `test routing fib-lookup` | `ip route get` | routing-table details |
| ③ ตรงกับ **policy ไหน** | อนุญาตหรือปฏิเสธ | `test security-policy-match` | SmartConsole / zdebug | Policy Lookup |
| ④ ถ้าถูกทิ้ง **ทิ้งเพราะอะไร** | ชี้จุดที่ต้องแก้ | `show counter global ... drop` | `fw ctl zdebug drop` | debug flow |
| ⑤ มี **session** ทั้งขาไปและกลับไหม | ไม่มีขากลับ = ปลายทาง/asymmetric | `show session` | `fw tab -t connections` | session list |

> จำโครงนี้ไว้ ใช้กับ firewall ยี่ห้อใดก็ได้ (Sophos, Check Point, Cisco FTD, Juniper SRX) — ต่างกันแค่ชื่อคำสั่ง

---

## 2. Palo Alto — แนวคิดที่ต้องรู้ก่อน

### Zone-based
Palo Alto ตัดสินใจจาก **zone** (เช่น trust, untrust, dmz) มากกว่า interface — ทุก interface ต้องอยู่ใน zone และ policy เขียนเป็น "จาก zone A ไป zone B"

### NAT กับ Security Policy — จุดที่สับสนบ่อยที่สุด ⭐
```
 Security policy ใช้ IP "ก่อน NAT" (pre-NAT IP) แต่ใช้ zone "หลัง NAT" (post-NAT zone)
```
ตัวอย่าง: คนจากอินเทอร์เน็ตเข้าเว็บ 203.0.113.50 ที่ถูก DNAT ไปยัง server 10.0.110.10 ใน DMZ
→ security rule ต้องเขียน: from **untrust** to **dmz** (zone ปลายทางหลัง NAT), destination **203.0.113.50** (IP ก่อน NAT)
ถ้าเขียน destination เป็น 10.0.110.10 จะไม่ match — ปัญหานี้เจอบ่อยมาก

### Management plane vs Data plane
- **Management plane (MP):** GUI, CLI, log, การตั้งค่า
- **Data plane (DP):** ประมวลผล traffic จริง
→ CPU ของ MP สูง (GUI ช้า) ไม่ได้แปลว่า traffic ช้า และกลับกัน · ping ที่ไม่ระบุ source จะออกจาก **management interface** ไม่ใช่ dataplane

---

## 3. Palo Alto — อ่านผลคำสั่งสำคัญ

### `show interface all`
```
name            id    speed/duplex/state        mac address
ethernet1/1     16    1000/full/up              00:1b:17:00:01:10       ← ปกติ
ethernet1/2     17    ukn/ukn/down(autoneg)     00:1b:17:00:01:11       ← ไม่มี link
...
name                id    vsys zone      forwarding         tag  address
ethernet1/1         16    1    untrust   vr:default         0    203.0.113.10/29
ethernet1/2         17    1    trust     vr:default         0    10.0.0.1/24
```
ส่วนแรกคือสถานะ link (เหมือน `show interfaces status` ของ Cisco) ส่วนที่สองคือ **zone** และ **virtual router** ของแต่ละ interface — ใช้ตรวจว่า interface อยู่ zone ที่ถูกต้อง

### `test routing fib-lookup` — ไปทางไหน
```
> test routing fib-lookup virtual-router default ip 10.1.5.20
--------------------------------------------------------------------------------
runtime route lookup
--------------------------------------------------------------------------------
virtual-router:   default
destination:      10.1.5.20
result:
  interface tunnel.1, source 10.0.0.1, nexthop 0.0.0.0
```
→ ไป 10.1.5.20 ออกทาง **tunnel.1** (VPN) ✅ · ถ้าได้ ethernet1/1 (internet) แทน = ไม่มี route ไป VPN

### `test security-policy-match` — จำลองว่าจะผ่านไหม ⭐
```
> test security-policy-match from trust to untrust source 10.0.20.55 destination 8.8.8.8 protocol 6 destination-port 443

"Allow-Internet; index: 12" {
        from trust;
        source any;
        to untrust;
        destination any;
        application/service [ ssl/tcp/any/443 web-browsing/tcp/any/80 ];
        action allow;
        ...
}
```
→ จะ match rule ชื่อ **Allow-Internet** (ลำดับที่ 12) และ action = **allow**
- ถ้าไม่มีผลลัพธ์ หรือ match rule ที่ action deny → ต้องแก้ policy
- `protocol 6` = TCP, `17` = UDP, `1` = ICMP
- ระวัง: Palo Alto ตรวจ **application** ด้วย (App-ID) เช่น rule อนุญาตเฉพาะ `ssl` แต่ traffic จริงถูกระบุเป็นแอปอื่น → ถูกปฏิเสธ แม้ port จะตรง

### `show session all filter ...` → `show session id ...`
```
> show session all filter source 10.0.20.55 destination 10.0.100.25
ID      Application    State   Type Flag  Src[Sport]/Zone/Proto (translated IP[Port])
                                          Vsys                      Dst[Dport]/Zone (translated IP[Port])
-------------------------------------------------------------------------------------
84521   ssl            ACTIVE  FLOW       10.0.20.55[51544]/trust/6  (10.0.20.55[51544])
                                          vsys1                      10.0.100.25[443]/servers  (10.0.100.25[443])

> show session id 84521
        c2s flow:                                       ← client to server (ขาไป)
                source:      10.0.20.55 [trust]
                dst:         10.0.100.25
        s2c flow:                                       ← server to client (ขากลับ)
                source:      10.0.100.25 [servers]
        ...
        application                          : ssl
        rule                                 : Users-to-ERP          ← ผ่าน rule นี้
        session to be logged at end          : True
        layer7 processing                    : enabled
        c2s byte/packet count                : 1240 / 9
        s2c byte/packet count                : 0 / 0                ← ⚠️ ขากลับเป็น 0
```
**s2c = 0** → server ไม่ตอบ หรือขากลับไม่ผ่าน firewall นี้ — เหมือน `reply=0` ของ FortiGate

### `show counter global filter delta yes severity drop` — ทำไมถูกทิ้ง ⭐
```
> show counter global filter delta yes severity drop
name                          value     rate severity  category  aspect    description
------------------------------------------------------------------------------------------------
flow_policy_deny               152        5 drop      flow      session   Session setup: denied by policy
flow_tcp_non_syn_drop          48         1 drop      flow      parse     Packets dropped: non-SYN TCP without session match
flow_fwd_l3_noroute            3          0 drop      flow      forward   Packets dropped: no route
```
- `delta yes` = แสดงเฉพาะค่าที่ **เพิ่มขึ้นตั้งแต่รันครั้งก่อน** → รันครั้งหนึ่ง, ให้ผู้ใช้ทดสอบ, รันอีกครั้ง → เห็นเฉพาะสิ่งที่เกิดช่วงทดสอบ
- อ่าน `description` ได้เลย: policy ปฏิเสธ / TCP ที่ไม่ใช่ SYN แต่ไม่มี session (**asymmetric routing**) / ไม่มี route
- ใช้คู่กับ packet filter (ในข้อถัดไป) เพื่อให้เห็นเฉพาะ traffic ของผู้ใช้ที่สนใจ

### Packet diag — capture 4 จุด
```
 receive  : packet เข้ามาถึง dataplane
 firewall : ผ่านการประมวลผล (หลัง NAT/policy)
 transmit : ส่งออก interface
 drop     : ถูกทิ้ง ⭐
```
ถ้าเห็นใน receive แต่ไปโผล่ใน drop → ทิ้งที่ firewall (ดู counter ประกอบ) · เห็นใน transmit แต่ไม่มีขากลับใน receive → ปลายทางไม่ตอบ
⚠️ ตั้ง filter ทุกครั้ง และ `set capture off` + `set filter off` เมื่อเสร็จ

### VPN
```
> show vpn ike-sa
IKEv2 SAs
Gateway ID  Peer-Address     Gateway Name    Role SN   Algorithm         Established     Expiration   ...  State
----------  ------------     ------------    ---- --   ---------         -----------     ----------        -----
1           198.51.100.20    GW-CNX          Init 5    PSK/DH14/A256/SHA256 Nov.24 08:10:02 Nov.24 16:10:02  Established   ← phase 1 ✅

> show vpn ipsec-sa
Name        Gateway   TnID   Peer-Address/Port  Algorithm         SPI(in)   SPI(out)   life(Sec/KB)
TUN-CNX     GW-CNX    1      198.51.100.20/500  ESP/G256/          ...       ...         2810/0         ← phase 2 ✅
```
ไม่มีบรรทัด = phase นั้นไม่ขึ้น → ดู `less mp-log ikemgr.log` หาข้อความ เช่น `NO_PROPOSAL_CHOSEN`, `AUTHENTICATION_FAILED`, `TS_UNACCEPTABLE` (ความหมายเดียวกับ FortiGate)

---

## 4. Check Point — แนวคิดที่ต้องรู้ก่อน

### สถาปัตยกรรม 3 ส่วน
```
 SmartConsole (โปรแกรมบนเครื่องผู้ดูแล) → Management Server (เก็บ policy, log) → Security Gateway (ตัวกรอง traffic จริง)
```
- **policy แก้ที่ SmartConsole** แล้วต้อง **Install Policy** ไปที่ gateway ถึงจะมีผล (แก้แล้วลืม install = ยังไม่เปลี่ยน)
- คำสั่งตรวจเช็คส่วนใหญ่รันบน **gateway** ใน **expert mode** (Linux shell) — จาก clish พิมพ์ `expert`

### SecureXL (เร่งความเร็ว)
traffic ส่วนใหญ่หลังจาก packet แรกจะผ่าน **SecureXL** (เส้นทางเร็ว) ไม่ผ่าน firewall kernel เต็มรูปแบบ → เครื่องมือบางตัวอาจไม่เห็นครบ (`fw monitor` เวอร์ชันใหม่จัดการได้แล้ว)

---

## 5. Check Point — อ่านผลคำสั่งสำคัญ

### `cpview` — หน้าจอภาพรวม
หน้าจอแบบเมนู (ใช้ลูกศรเลื่อน) แสดง CPU ต่อ core, memory, throughput, จำนวน connection, drop — เหมาะเป็นคำสั่งแรกเมื่อ "firewall ช้า" (กด `q` ออก)

### `fw stat` — policy ที่ติดตั้งอยู่
```
[Expert@GW-HQ:0]# fw stat
HOST      POLICY     DATE
localhost Standard   24Nov2026 09:12:44 :  [>eth1] [<eth1] [>eth2] [<eth2]
```
บอกชื่อ policy ที่ติดตั้งและ **เวลาติดตั้งล่าสุด** — ถ้าเวลาเก่ากว่าที่แก้ใน SmartConsole = **ยังไม่ได้ install policy**

### `cphaprob state` — Cluster
```
Cluster Mode:   High Availability (Active Up) with IGMP Membership
ID         Unique Address  Assigned Load   State          Name
1 (local)  10.255.0.1      100%            ACTIVE         GW-HQ-1
2          10.255.0.2      0%              STANDBY        GW-HQ-2
```
ปกติ = ACTIVE หนึ่งเครื่อง STANDBY หนึ่งเครื่อง · ถ้าเห็น `DOWN`, `READY`, `ACTIVE(!)` → มีปัญหา → `cphaprob -a if` ดูว่า interface ไหนทำให้ cluster ไม่สมบูรณ์

### `fw ctl zdebug + drop` — ทำไมถูกทิ้ง ⭐
```
[Expert@GW-HQ:0]# fw ctl zdebug + drop | grep 10.0.50.12
;[cpu_2];[fw4_1];fw_log_drop_ex: Packet proto=6 10.0.50.12:50122 -> 10.0.100.25:3389 dropped by fw_handle_first_packet Reason: Rulebase drop - rule 45;
```
อ่าน: TCP จาก 10.0.50.12 ไป 10.0.100.25:3389 **ถูกทิ้งเพราะ rule 45** (มักเป็น cleanup rule = ปฏิเสธทุกอย่างที่เหลือ) → ไม่มี rule อนุญาตที่อยู่ก่อนหน้า
| Reason | ความหมาย |
|---|---|
| `Rulebase drop - rule X` | policy ปฏิเสธ (rule X) |
| `Anti-Spoofing` / `address spoofing` | IP ต้นทางไม่อยู่ใน topology ที่กำหนดของ interface ที่เข้ามา → แก้ topology หรือ routing (คล้าย reverse path check) |
| `first packet isn't SYN` | ไม่มี connection เดิม → asymmetric routing / timeout |
| `TCP segment out of maximum allowed sequence` | ปัญหา TCP state |
⚠️ ใช้ชั่วคราว (ใส่ `grep` กรองเสมอ) แล้วกด **Ctrl+C** หยุด — รันทิ้งไว้ทำให้ CPU สูง

### `fw monitor` — เห็น packet ผ่าน 4 จุด
```
[Expert@GW-HQ:0]# fw monitor -F "10.0.20.55,0,10.0.100.25,443,6"
[vs_0][fw_1] eth1:i[60]: 10.0.20.55 -> 10.0.100.25 (TCP) len=60 id=1234     ← i  = ก่อนผ่าน inbound
[vs_0][fw_1] eth1:I[60]: 10.0.20.55 -> 10.0.100.25 (TCP) len=60 id=1234     ← I  = ผ่าน inbound แล้ว
[vs_0][fw_1] eth3:o[60]: 10.0.20.55 -> 10.0.100.25 (TCP) len=60 id=1234     ← o  = ก่อนออก
[vs_0][fw_1] eth3:O[60]: 10.0.20.55 -> 10.0.100.25 (TCP) len=60 id=1234     ← O  = ออกไปแล้ว ✅
```
- เห็นครบ i → I → o → O = ผ่าน firewall ไปแล้ว
- เห็นแค่ `i` = **ถูกทิ้งที่ inbound** (ใช้ zdebug ดูเหตุผล)
- หลัง NAT จะเห็น IP เปลี่ยนระหว่างจุดต่าง ๆ — ช่วยยืนยันว่า NAT ทำงานถูก
- รูปแบบ `-F "src,sport,dst,dport,proto"` ใช้ 0 แทน "อะไรก็ได้"

### VPN: `vpn tu`
เปิดเมนูให้เลือก: ดู IKE SA / IPsec SA, ลบ SA ของ peer เฉพาะราย (ใช้แทนการรีเซ็ต tunnel) — ⚠️ การลบ SA ทำให้ tunnel นั้นหยุดชั่วคราว

---

## 6. Linux Firewall — อ่านผล

### iptables พร้อมตัวนับ
```
$ sudo iptables -L INPUT -n -v --line-numbers
Chain INPUT (policy DROP 1523 packets, 98K bytes)          ← ค่าเริ่มต้น DROP — ทิ้งไปแล้ว 1,523 packet
num   pkts bytes target  prot opt in   out  source        destination
1     8823  612K ACCEPT  all  --  lo   *    0.0.0.0/0     0.0.0.0/0
2      12M   15G ACCEPT  all  --  *    *    0.0.0.0/0     0.0.0.0/0     ctstate RELATED,ESTABLISHED   ← ขากลับของ connection เดิม
3      420 25200 ACCEPT  tcp  --  *    *    10.0.10.0/24  0.0.0.0/0     tcp dpt:22                    ← SSH จากวงจัดการ
4        0     0 ACCEPT  tcp  --  *    *    0.0.0.0/0     0.0.0.0/0     tcp dpt:443                   ← ยังไม่มีใครใช้
```
- **pkts** ของ rule = จำนวนที่ตรง → ทดสอบแล้วดูว่าตัวเลขของ rule ไหนเพิ่ม = traffic ถูกตัดสินที่ rule นั้น
- **policy DROP** ที่หัว chain = สิ่งที่ไม่ตรง rule ใดจะถูกทิ้ง
- Rule ถูกตรวจ **จากบนลงล่าง** หยุดที่ rule แรกที่ตรง

### conntrack — session ของ Linux
```
$ sudo conntrack -L -s 10.0.20.55
tcp 6 431999 ESTABLISHED src=10.0.20.55 dst=10.0.100.25 sport=51544 dport=443 src=10.0.100.25 dst=10.0.20.55 sport=443 dport=51544 [ASSURED] mark=0 use=1
```
- ส่วนแรก = ขาไป, ส่วนที่สอง = ขากลับที่คาดไว้ · `[ASSURED]` = เห็นทั้งสองทางแล้ว ✅ · `[UNREPLIED]` = **ยังไม่มีขากลับ**

---

## 7. ตารางเทียบ: ใช้คำสั่งไหนเมื่อไร

| สถานการณ์ | Palo Alto | Check Point | FortiGate |
|---|---|---|---|
| "จะผ่านไหม" (ก่อนผู้ใช้ทดสอบ) | `test security-policy-match` | Policy ใน SmartConsole + `fw ctl zdebug drop` ระหว่างทดสอบ | Policy Lookup |
| "ทำไมไม่ผ่าน" | `show counter global ... drop` + packet-diag | `fw ctl zdebug + drop` | `diag debug flow` |
| "ผ่านแล้วแต่ไม่มีขากลับ" | `show session id` (s2c = 0) | `fw monitor` (ไม่มีขากลับ) | session `reply=0` |
| "ไปผิดทาง" | `test routing fib-lookup` | `ip route get` | `routing-table details` |
| "เครื่องช้า" | `show running resource-monitor` | `cpview` | `get sys perf status` / `diag sys top` |
| "HA ปกติไหม" | `show high-availability state` | `cphaprob state` | `get system ha status` |

---

## 8. แบบฝึกหัด

1. อธิบายด้วยคำของตัวเองว่าทำไม security rule ของ Palo Alto สำหรับ DNAT ต้องใช้ IP ก่อน NAT แต่ zone หลัง NAT
2. ผลของ `show session id` มี c2s = 10 packet, s2c = 0 — ปัญหาน่าจะอยู่ที่ไหน ตรวจอะไรต่อ
3. `fw monitor` เห็นแค่ `i` ไม่เห็น `I` — ใช้คำสั่งอะไรหาเหตุผล
4. Check Point แก้ rule ใน SmartConsole แล้วแต่ยังถูกบล็อก ตรวจอะไรก่อน
5. counter `flow_tcp_non_syn_drop` เพิ่มขึ้นเรื่อย ๆ หมายถึงอะไร

<details><summary><b>เฉลย</b></summary>

1. Firewall ประเมิน security policy หลังรู้ zone ปลายทางจริง (ต้อง lookup route ด้วย IP หลัง NAT จึงได้ zone หลัง NAT) แต่ address ในกฎยังอ้างตาม header เดิมของ packet (IP สาธารณะก่อน NAT)
2. Server ไม่ตอบ หรือขากลับไม่ผ่าน firewall นี้ — ตรวจ server (บริการ/firewall บนเครื่อง), route กลับของ server, ความเป็น asymmetric
3. `fw ctl zdebug + drop | grep <IP>`
4. ยังไม่ได้ Install Policy — ดูเวลาใน `fw stat`
5. มี TCP packet ที่ไม่ใช่ SYN มาถึงโดยไม่มี session → มักเป็น asymmetric routing หรือ session หมดอายุ
</details>

⬅️ [FortiGate](03-fortigate-explained.md) · ➡️ ต่อไป: [กรณีศึกษาการไล่ปัญหา](05-troubleshooting-flow-explained.md)
