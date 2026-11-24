# คำสั่งตรวจเช็ค FortiGate (FortiOS CLI)

> 📘 คำอธิบายละเอียดพร้อมตัวอย่างผลลัพธ์: [explained/03-fortigate-explained.md](explained/03-fortigate-explained.md)

> เข้า CLI ได้ทาง SSH, console หรือปุ่ม **CLI Console** มุมขวาบนของ GUI
> คำสั่ง `get` และ `show` อ่านอย่างเดียว · `diagnose debug` ใช้ CPU เพิ่ม: **ตั้ง filter ทุกครั้ง** และปิดเมื่อเสร็จด้วย `diagnose debug disable` และ `diagnose debug reset`
> คำสั่งบางตัวต่างกันตาม version ของ FortiOS (6.4 / 7.0 / 7.2 / 7.4 / 7.6) · ถ้าใช้ VDOM ต้องเข้า `config vdom` → `edit <ชื่อ>` ก่อน (หรือ `config global` สำหรับคำสั่งระดับระบบ)

---

## 0. เทคนิคการใช้ CLI

| เทคนิค | ตัวอย่าง |
|---|---|
| กรองผลลัพธ์ | `show firewall policy \| grep -f 10.0.20.55` (`-f` แสดงทั้งบล็อกที่เจอ) |
| ไม่สนตัวพิมพ์ | `get system interface \| grep -i port1` |
| ดู config ทั้งหมดรวมค่าเริ่มต้น | `show full-configuration system interface port1` |
| แสดงผลไม่หยุดทีละหน้า | `config system console` → `set output standard` → `end` |
| ย่อคำสั่ง | `diag` = `diagnose`, `exe` = `execute` |

---

## 1. ภาพรวมระบบ

| ตรวจ | คำสั่ง |
|---|---|
| **รุ่น, version, serial, HA mode, VDOM, เวลา** ⭐ | `get system status` |
| CPU, memory, session, uptime | `get system performance status` |
| process ที่กิน CPU/memory (กด q ออก) | `diagnose sys top 2 20` |
| memory ละเอียด / conserve mode | `diagnose hardware sysinfo conserve` · `diagnose hardware sysinfo memory` |
| ฮาร์ดแวร์ / อุณหภูมิ / พัดลม | `get hardware status` · `execute sensor list` |
| License และ FortiGuard | `get system fortiguard-service status` · `diagnose autoupdate versions` |
| ทดสอบติดต่อ FortiGuard | `diagnose debug rating` · `execute ping service.fortiguard.net` |
| เวลา / NTP | `execute date` · `execute time` · `diagnose sys ntp status` |
| ใครล็อกอินอยู่ | `get system admin list` |
| Disk / log disk | `diagnose sys logdisk usage` |

---

## 2. Interface

| ตรวจ | คำสั่ง |
|---|---|
| IP และสถานะ interface | `get system interface physical` · `diagnose ip address list` |
| config ของ interface | `show system interface port1` |
| **ความเร็ว, duplex, errors, drops ของพอร์ต** ⭐ | `diagnose hardware deviceinfo nic port1` |
| รายชื่อ NIC | `diagnose hardware deviceinfo nic` |
| SFP/transceiver | `get system interface transceiver` |
| สถิติ traffic ต่อ interface | `diagnose netlink interface list port1` |
| ARP | `get system arp` · `diagnose ip arp list` |
| ลบ ARP (ระวังกระทบชั่วคราว) | `execute clear system arp table` |
| LACP aggregate | `diagnose netlink aggregate name <agg-name>` |
| VLAN / switch interface | `show system interface \| grep -f vlanid` |

---

## 3. Routing

| ตรวจ | คำสั่ง |
|---|---|
| **ตาราง route ที่ใช้งาน** ⭐ | `get router info routing-table all` |
| route ไป IP นี้ใช้เส้นไหน | `get router info routing-table details 10.20.1.5` |
| route ทั้งหมดรวมที่ไม่ active | `get router info routing-table database` |
| ตาราง route ใน kernel (ที่ส่งจริง) | `diagnose ip route list` |
| static route config | `show router static` |
| policy route | `diagnose firewall proute list` |
| OSPF | `get router info ospf neighbor` · `get router info ospf interface` · `get router info ospf database brief` |
| BGP | `get router info bgp summary` · `get router info bgp neighbors 203.0.113.1 advertised-routes` · `... received-routes` · `get router info bgp network` |
| IPv6 | `get router info6 routing-table` · `diagnose ipv6 address list` |
| Link monitor (ตรวจ gateway) | `diagnose sys link-monitor status` |

### อ่าน `get router info routing-table all`
```
S*      0.0.0.0/0 [10/0] via 203.0.113.1, wan1, [1/0]
         └ default  └ distance/metric        └ ขาออก  └ priority/weight
C       10.0.20.0/24 is directly connected, internal
O       10.30.0.0/16 [110/20] via 10.0.0.2, port3, 00:15:02
B       10.40.0.0/16 [20/0] via 169.254.10.1 (recursive via ...), 00:20:11
```
ถ้าไม่มี route ไปปลายทาง (หรือ route ออกผิด interface) traffic จะถูกทิ้งด้วยเหตุผล "no route" หรือ **reverse path check** (ดูข้อ 6)

---

## 4. Ping, Traceroute, Telnet จาก FortiGate

```
execute ping 8.8.8.8
execute ping-options source 10.0.20.1          ! ใช้ IP ต้นทางของ interface ภายใน (ทดสอบผ่าน VPN/route ภายใน)
execute ping-options repeat-count 100
execute ping-options data-size 1472
execute ping-options df-bit yes                ! ทดสอบ MTU
execute ping-options reset                     ! คืนค่าเริ่มต้น
execute ping 10.40.1.5
execute traceroute 8.8.8.8
execute traceroute-options source 10.0.20.1
execute telnet 10.40.1.5 443                   ! ทดสอบ TCP port (Ctrl+C ออก)
execute ping6 2001:4860:4860::8888
```
⚠️ ping จาก FortiGate โดยไม่ตั้ง source จะใช้ IP ของ interface ขาออก → อาจไม่ตรงกับ policy/selector ของ VPN → **ตั้ง `ping-options source` ทุกครั้งที่ทดสอบ VPN**

---

## 5. Firewall Policy และ Session

| ตรวจ | คำสั่ง |
|---|---|
| ดู policy | `show firewall policy` · `show firewall policy 15` |
| หา policy ที่เกี่ยวกับ IP/address | `show firewall policy \| grep -f 10.0.20.55` · `show firewall address \| grep -f 10.0.20.55` |
| **จำลองว่า traffic จะ match policy ไหน** ⭐ | GUI: Policy & Objects → Firewall Policy → **Policy Lookup** · CLI (7.x): `diagnose firewall iprope lookup <src_ip> <src_port> <dst_ip> <dst_port> <protocol> <src_intf>` |
| จำนวน hit ของ policy | `diagnose firewall iprope show 100004 15` (หรือดู Hit Count ใน GUI) |
| สถิติ session รวม | `diagnose sys session stat` · `get system session status` |

### ดู Session (ตั้ง filter ก่อนเสมอ)
```
diagnose sys session filter clear
diagnose sys session filter src 10.0.20.55
diagnose sys session filter dst 10.40.1.5
diagnose sys session filter dport 443
diagnose sys session list                     ! ดู session ที่ตรง filter
diagnose sys session clear                    ! ⚠️ ลบเฉพาะ session ที่ตรง filter (ถ้าไม่มี filter = ลบทั้งหมด!)
```
ใน `session list` ดูได้ว่า: `policy_id=` (ผ่าน policy ไหน), `hook=pre/post` + `act=snat/dnat` (NAT เป็น IP อะไร), `state=` (เช่น `may_dirty`, `npu` = offload ไป hardware), `duration`, `expire`, จำนวน packet ขาไป/กลับ (`org` / `reply`) → ถ้า **reply = 0** แปลว่าไม่มีขากลับ (route ขากลับ/ปลายทางไม่ตอบ/asymmetric)

---

## 6. Debug Flow — ดูว่า FortiGate ทำอะไรกับ packet ⭐ (คำสั่งที่สำคัญที่สุด)

```
diagnose debug reset
diagnose debug flow filter clear
diagnose debug flow filter addr 10.0.20.55          ! หรือ saddr / daddr
diagnose debug flow filter port 443
diagnose debug flow show function-name enable
diagnose debug console timestamp enable
diagnose debug flow trace start 20                  ! เก็บ 20 packet
diagnose debug enable
! ... ทดสอบจากเครื่องผู้ใช้ ...
diagnose debug disable
diagnose debug reset
```
### ข้อความที่พบบ่อยและความหมาย
| ข้อความใน debug flow | ความหมาย | แก้ที่ |
|---|---|---|
| `Allowed by Policy-15` | ผ่าน policy 15 | — |
| `Denied by forward policy check (policy 0)` | **ไม่มี policy ที่ match** (ตก implicit deny) | สร้าง/แก้ policy: interface, address, service, schedule |
| `reverse path check fail, drop` | **ไม่มี route กลับไปหา IP ต้นทาง** ผ่าน interface ที่ packet เข้ามา (RPF) | route ขากลับ, asymmetric routing |
| `find a route: flag=... gw-x via portX` | route ที่เลือก | ตรวจว่าออกถูก interface |
| `SNAT 10.0.20.55->203.0.113.10:xxxxx` / `DNAT ...` | การแปลง NAT | ตรวจ VIP/IP pool |
| `enter IPSec interface-xxx` / `encrypted, and send to ...` | เข้า VPN tunnel | — |
| `no session matched` | packet กลางทาง (เช่น ACK) ไม่มี session | asymmetric routing, session timeout |
| `iprope_in_check() check failed on policy 0, drop` | ไปหา IP ของ FortiGate เอง แต่ไม่อนุญาต (admin access/local-in) | Administrative access บน interface / local-in policy |
| `Denied by quota check` / `shaper` | ติด quota/traffic shaping | |
| `dropped by ... UTM/IPS` | ถูก security profile บล็อก | log ของ profile นั้น |

---

## 7. Sniffer (จับ Packet)

```
diagnose sniffer packet <interface> '<filter>' <verbose> <count> <timestamp>
diagnose sniffer packet any 'host 10.0.20.55' 4 0 l
diagnose sniffer packet any 'host 10.0.20.55 and port 443' 4 50 a
diagnose sniffer packet wan1 'icmp' 4 20 l
diagnose sniffer packet any 'host 10.40.1.5 and not port 22' 6 100 l   ! verbose 6 = ดู payload (เอาไปแปลงเป็น pcap ได้)
```
| verbose | แสดง |
|---|---|
| 1 | header ของ packet |
| 4 | **header + ชื่อ interface** (ใช้บ่อยที่สุด) |
| 6 | header + data + ชื่อ interface (แปลงเป็น pcap ได้ด้วยเครื่องมือของ Fortinet หรือดาวน์โหลดจาก GUI: Network → Diagnostics/Packet Capture) |
- `count` = 0 ไม่จำกัด (กด Ctrl+C หยุด) · timestamp `l` = เวลาท้องถิ่น, `a` = เวลาจริง
- เห็น packet **เข้า** interface หนึ่งแต่ **ไม่ออก** interface อื่น → ใช้ debug flow หาเหตุผล
- traffic ที่ถูก **offload ไป NPU** อาจไม่ปรากฏใน sniffer → ปิด offload ชั่วคราวใน policy (`set auto-asic-offload disable`) เฉพาะเวลาที่ debug แล้วเปิดคืน

---

## 8. IPsec VPN

| ตรวจ | คำสั่ง |
|---|---|
| **สรุปสถานะ tunnel** ⭐ | `get vpn ipsec tunnel summary` |
| Phase 1 (IKE SA) | `diagnose vpn ike gateway list` · `diagnose vpn ike gateway list name <phase1>` |
| Phase 2 (IPsec SA, selector, จำนวน packet enc/dec) | `diagnose vpn tunnel list name <phase1>` |
| สั่งให้ tunnel ขึ้น | `diagnose vpn tunnel up <phase2> <phase1>` |
| รีเซ็ต tunnel (⚠️ ตัด traffic ชั่วคราว) | `diagnose vpn ike gateway clear name <phase1>` |
| SSL VPN ผู้ใช้ที่เชื่อมต่อ | `get vpn ssl monitor` |

### Debug IKE (tunnel ไม่ขึ้น)
```
diagnose debug reset
diagnose vpn ike log filter clear
diagnose vpn ike log filter rem-addr4 198.51.100.20     ! (FortiOS เก่า: diagnose vpn ike log-filter dst-addr4 ...)
diagnose debug application ike -1
diagnose debug console timestamp enable
diagnose debug enable
! ... รอ/สั่ง tunnel up ...
diagnose debug disable
diagnose debug reset
```
| อาการใน IKE debug | สาเหตุ |
|---|---|
| `no SA proposal chosen` | encryption/hash/DH ไม่ตรงกันสองฝั่ง |
| `authentication failed` / `probable pre-shared secret mismatch` | PSK ไม่ตรง (หรือ peer ID) |
| ไม่มีข้อความอะไรเลย | packet ไม่ถึง: UDP 500/4500 ถูกบล็อก, IP ปลายทางผิด, route |
| phase 1 ขึ้น แต่ phase 2 ไม่ขึ้น (`TS unacceptable`) | **subnet (selector) ไม่ตรงกัน** สองฝั่ง |
| tunnel ขึ้นแต่ traffic ไม่ผ่าน | ไม่มี policy ระหว่าง internal ↔ tunnel, ไม่มี static route ไป subnet ปลายทางผ่าน tunnel, NAT ผิด, enc เพิ่มแต่ dec = 0 (ฝั่งตรงข้ามไม่ตอบ) |

---

## 9. SD-WAN

| ตรวจ | คำสั่ง (FortiOS 7.x) |
|---|---|
| สมาชิก SD-WAN | `diagnose sys sdwan member` |
| **Health check (latency, jitter, loss, สถานะ)** | `diagnose sys sdwan health-check status` (บางรุ่นเก่า: `diagnose sys sdwan health-check`) |
| กฎ SD-WAN (service/rule) ว่าเลือกลิงก์ไหน | `diagnose sys sdwan service4` |
| SLA log | `diagnose sys sdwan sla-log <health-check-name> <member-id>` |
| FortiOS 6.x ใช้ชื่อเดิม | `diagnose sys virtual-wan-link ...` |

---

## 10. HA (High Availability)

| ตรวจ | คำสั่ง |
|---|---|
| **สถานะ HA, ใครเป็น primary, เหตุผล** ⭐ | `get system ha status` |
| config sync ตรงกันไหม (checksum ต้องเท่ากันทุกตัว) | `diagnose sys ha checksum cluster` |
| เข้า CLI ของเครื่องสำรอง | `execute ha manage <index> <admin-user>` |
| ประวัติการสลับ | `diagnose sys ha history read` |
| สั่ง failover (⚠️ ทำใน maintenance window) | `diagnose sys ha reset-uptime` (บนเครื่อง primary ใน mode override disable) |

---

## 11. User, Authentication, Security Profile

| ตรวจ | คำสั่ง |
|---|---|
| ผู้ใช้ที่ login (firewall auth / FSSO) | `diagnose firewall auth list` · `diagnose debug authd fsso list` |
| ทดสอบ LDAP/RADIUS | `diagnose test authserver ldap <server> <user> <password>` · `diagnose test authserver radius <server> pap <user> <password>` |
| ทดสอบ DNS ของ FortiGate | `execute nslookup name example.com` (หรือ `diagnose test application dnsproxy 2`) |
| Web filter category ของ URL | GUI: Security Profiles → Web Filter → **URL lookup** |
| สถิติ IPS | `diagnose ips anomaly list` · `diagnose test application ipsmonitor 1` |
| DHCP lease ที่แจกจาก FortiGate | `execute dhcp lease-list` |

---

## 12. Log

```
execute log filter reset
execute log filter category 0            ! 0 = traffic, 1 = event, 2 = utm-virus, 4 = attack ฯลฯ (ดูตัวเลือกด้วย ?)
execute log filter field srcip 10.0.20.55
execute log filter view-lines 50
execute log display
```
GUI: **Log & Report → Forward Traffic** (กรอง srcip/dstip, ดู Policy ID, Action) และ **System Events** — มักเร็วกว่า CLI สำหรับงานประจำ

---

## 13. Config / Backup

| งาน | คำสั่ง |
|---|---|
| backup config ไป TFTP/FTP/SCP | `execute backup config tftp fgt-backup.conf 10.0.0.50` |
| ดู config ที่เปลี่ยนจากค่าเริ่มต้น | `show` (ทั้งหมด) · `show system interface` |
| ป้องกันตัดตัวเองเมื่อแก้ remote | `config system global` → `set cfg-save revert` → `set cfg-revert-timeout 600` → `end` → แก้ → ยืนยันด้วย `execute cfg save` (คืนค่าเป็น `automatic` หลังเสร็จ) |
| reboot (⚠️) | `execute reboot` |

---

## 14. Cheat Sheet ย่อ

```
get system status · get system performance status · diagnose sys top
get system interface physical · diagnose hardware deviceinfo nic port1 · get system arp
get router info routing-table all · get router info routing-table details <ip>
get router info ospf neighbor · get router info bgp summary
execute ping-options source <ip> → execute ping <ip> · execute traceroute <ip> · execute telnet <ip> <port>
diagnose sys session filter src <ip> → diagnose sys session list
diagnose debug flow filter addr <ip> → trace start 20 → debug enable → (ทดสอบ) → debug disable / reset
diagnose sniffer packet any 'host <ip>' 4 0 l
get vpn ipsec tunnel summary · diagnose vpn ike gateway list · diagnose vpn tunnel list
diagnose sys sdwan health-check status · get system ha status · diagnose sys ha checksum cluster
```
