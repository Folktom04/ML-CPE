# คำสั่งตรวจเช็ค Firewall อื่น ๆ: Palo Alto, Check Point, Linux (nftables/iptables)

> 📘 คำอธิบายละเอียดพร้อมตัวอย่างผลลัพธ์: [explained/04-paloalto-checkpoint-explained.md](explained/04-paloalto-checkpoint-explained.md)

> หลักการเหมือน FortiGate: ดูสถานะ → route → policy ที่ match → session → debug/capture · ใช้ filter ทุกครั้งที่ debug และปิด debug เมื่อเสร็จ

---

## 1. Palo Alto Networks (PAN-OS CLI)

ตั้งค่า CLI ที่ช่วยให้อ่านง่าย: `set cli pager off` · `set cli config-output-format set` (แสดง config เป็นบรรทัด `set`)

### ภาพรวมระบบ
| ตรวจ | คำสั่ง |
|---|---|
| รุ่น, version, serial, uptime, content version | `show system info` |
| CPU/memory (management plane) | `show system resources` |
| CPU ของ dataplane | `show running resource-monitor minute last 5` |
| สถานะ HA | `show high-availability state` · `show high-availability all` |
| License | `request license info` |
| Log ระบบ | `show log system direction equal backward` |
| เวลา/NTP | `show clock` · `show ntp` |

### Interface และ Routing
| ตรวจ | คำสั่ง |
|---|---|
| interface ทั้งหมด (สถานะ, IP, zone) | `show interface all` |
| รายละเอียด/counters ของ interface | `show interface ethernet1/1` · `show counter interface ethernet1/1` |
| ARP | `show arp all` |
| **ตาราง route** | `show routing route` · `show routing route destination 10.20.1.5/32` |
| **route ที่ใช้ส่งจริงไป IP นี้** ⭐ | `test routing fib-lookup virtual-router default ip 10.20.1.5` |
| OSPF / BGP | `show routing protocol ospf neighbor` · `show routing protocol bgp summary` · `show routing protocol bgp peer` |
| (PAN-OS ที่ใช้ Advanced Routing Engine) | `show advanced-routing route` · `show advanced-routing bgp peer status` |

### Ping / Traceroute
```
ping source 10.0.20.1 host 10.40.1.5
ping source 10.0.20.1 count 100 size 1472 do-not-fragment yes host 10.40.1.5
traceroute source 10.0.20.1 host 8.8.8.8
```
(ไม่ระบุ source = ping จาก management interface ซึ่งมักใช้คนละเส้นทางกับ dataplane)

### Policy และ Session
| ตรวจ | คำสั่ง |
|---|---|
| **จำลองว่า traffic จะ match security rule ไหน** ⭐ | `test security-policy-match from trust to untrust source 10.0.20.55 destination 8.8.8.8 protocol 6 destination-port 443` |
| จำลอง NAT | `test nat-policy-match from trust to untrust source 10.0.20.55 destination 8.8.8.8 protocol 6 destination-port 443` |
| ดู session ตามเงื่อนไข | `show session all filter source 10.0.20.55 destination 10.40.1.5` |
| รายละเอียด session (rule, NAT, app, bytes ขาไป/กลับ) | `show session id <id>` |
| สถิติ session รวม | `show session info` |
| ลบ session (⚠️) | `clear session id <id>` |
| **เหตุผลที่ dataplane ทิ้ง packet** ⭐ | `show counter global filter delta yes severity drop` |
| ดู counter แบบกรองเฉพาะ flow | ตั้ง filter ก่อน (ข้อถัดไป) แล้ว `show counter global filter delta yes packet-filter yes` |

| Counter ที่พบบ่อย | ความหมาย |
|---|---|
| `flow_policy_deny` | ถูก security policy ปฏิเสธ |
| `flow_tcp_non_syn_drop` | packet TCP ที่ไม่ใช่ SYN แต่ไม่มี session → มักเป็น **asymmetric routing** |
| `flow_fwd_l3_noroute` | ไม่มี route |
| `flow_fwd_mtu_exceeded` | packet ใหญ่เกิน MTU |
| `flow_dos_*` | ติด DoS protection/zone protection |

### Packet Capture / Diagnostic (Packet Diag)
```
debug dataplane packet-diag clear all
debug dataplane packet-diag set filter match source 10.0.20.55 destination 10.40.1.5
debug dataplane packet-diag set filter on
debug dataplane packet-diag set capture stage receive  file rx.pcap
debug dataplane packet-diag set capture stage firewall file fw.pcap
debug dataplane packet-diag set capture stage transmit file tx.pcap
debug dataplane packet-diag set capture stage drop     file drop.pcap
debug dataplane packet-diag set capture on
! ... ทดสอบ ...
debug dataplane packet-diag set capture off
debug dataplane packet-diag set filter off
view-pcap filter-pcap rx.pcap
```
(GUI: Monitor → Packet Capture ทำได้เหมือนกัน) · เห็นใน **drop** stage = ถูกทิ้ง → ดู counter ประกอบ

### IPsec VPN
| ตรวจ | คำสั่ง |
|---|---|
| Phase 1 | `show vpn ike-sa` · `show vpn ike-sa gateway <gw>` |
| Phase 2 | `show vpn ipsec-sa` · `show vpn ipsec-sa tunnel <tunnel>` |
| สั่งเริ่ม | `test vpn ike-sa gateway <gw>` · `test vpn ipsec-sa tunnel <tunnel>` |
| Log ของ IKE | `less mp-log ikemgr.log` · `show log system subtype equal vpn` |
| GlobalProtect ผู้ใช้ที่เชื่อมต่อ | `show global-protect-gateway current-user` |

### อื่น ๆ
- ผู้ใช้กับ IP (User-ID): `show user ip-user-mapping ip 10.0.20.55`
- ทดสอบ URL category: `test url-info-cloud www.example.com`
- Config ที่ยังไม่ commit: `show config diff` (ใน configure mode) · commit และย้อนกลับผ่าน GUI: Config Audit / Load named configuration snapshot

---

## 2. Check Point (Gaia / expert mode)

> คำสั่งส่วนใหญ่รันใน **expert mode** (`expert` จาก clish) · `cpview` เป็นหน้าจอภาพรวมที่สะดวกที่สุด

### ภาพรวม
| ตรวจ | คำสั่ง |
|---|---|
| ภาพรวม CPU/memory/traffic/connection แบบ real-time ⭐ | `cpview` |
| version | `fw ver` · clish: `show version all` |
| สถานะ firewall และ policy ที่ติดตั้ง | `fw stat` · `cpstat fw` |
| **สถานะ ClusterXL (Active/Standby)** | `cphaprob state` · `cphaprob -a if` · `cphaprob list` |
| SecureXL / acceleration | `fwaccel stat` · `fwaccel stats -s` |
| CoreXL | `fw ctl multik stat` |
| จำนวน connection | `fw tab -t connections -s` |
| ข้อมูลสำหรับ TAC | `cpinfo` (ใช้เวลานาน) |

### Interface และ Routing
| ตรวจ | คำสั่ง |
|---|---|
| interface | clish `show interfaces all` · expert `ifconfig` / `ip a` |
| route | clish `show route` · expert `netstat -rn` / `ip route` |
| route ไป IP นี้ | expert `ip route get 10.20.1.5` |
| OSPF / BGP | clish `show ospf neighbors` · `show bgp peers` |
| ARP | `arp -an` |

### Ping / Traceroute / Capture
```
ping -I eth1 10.40.1.5
traceroute -n 8.8.8.8
tcpdump -nni eth1 host 10.0.20.55
fw monitor -F "10.0.20.55,0,10.40.1.5,443,6"      ! (R80.20+) src,sport,dst,dport,proto — 0 = ใดก็ได้
fw monitor -e "accept host(10.0.20.55);"           ! รูปแบบเดิม
```
`fw monitor` แสดงจุดตรวจ: `i` (ก่อนเข้า inbound) → `I` (หลังผ่าน inbound) → `o` (ก่อน outbound) → `O` (หลัง outbound) · เห็นแค่ `i` ไม่เห็น `I` = ถูกทิ้งที่ inbound

### ดูว่าทำไม packet ถูกทิ้ง ⭐
```
fw ctl zdebug + drop | grep 10.0.20.55
```
| ข้อความ | ความหมาย |
|---|---|
| `Rulebase drop - rule X` / `Rule: Cleanup` | ไม่มี rule อนุญาต |
| `Anti-spoofing` / `address spoofing` | topology ของ interface ไม่รวม subnet นี้ หรือ route ผิด/asymmetric |
| `first packet isn't SYN` | ไม่มี connection เดิม (asymmetric/timeout) |
| `Instance is currently fully utilized` | CPU/CoreXL เต็ม |
(ใช้ชั่วคราวเท่านั้น แล้ว Ctrl+C หยุด)

### VPN
| ตรวจ | คำสั่ง |
|---|---|
| เมนูจัดการ tunnel (ดู/ลบ SA) | `vpn tu` |
| สถานะ | `vpn tu tlist` (R80.x ขึ้นไป) · `cpstat vpn` |
| debug | `vpn debug trunc` → ทดสอบ → `vpn debug off` → ดู `$FWDIR/log/ike.elg` และ `vpnd.elg` |

---

## 3. Linux Firewall (nftables / iptables / firewalld / ufw)

| ตรวจ | คำสั่ง |
|---|---|
| rule ทั้งหมดพร้อมตัวนับ (nftables) | `sudo nft list ruleset` |
| rule พร้อมจำนวน packet ที่ match (iptables) | `sudo iptables -L -n -v --line-numbers` · NAT: `sudo iptables -t nat -L -n -v` |
| firewalld | `sudo firewall-cmd --list-all` · `sudo firewall-cmd --get-active-zones` |
| ufw | `sudo ufw status verbose` |
| connection tracking | `sudo conntrack -L -s 10.0.20.55` · `sudo conntrack -S` |
| ตามรอย packet ผ่าน rule (nftables) | เพิ่ม `meta nftrace set 1` ในกฎที่ต้องการ แล้ว `sudo nft monitor trace` |
| IP forwarding เปิดไหม | `sysctl net.ipv4.ip_forward` |
| reverse path filter (ทิ้ง asymmetric) | `sysctl net.ipv4.conf.all.rp_filter` |
| ป้องกันตัดตัวเองก่อนแก้ | `echo "nft -f /etc/nftables.conf.bak" \| at now + 5 minutes` |

---

## 4. เทียบคำสั่งที่ใช้บ่อยระหว่างยี่ห้อ

| งาน | Cisco | FortiGate | Palo Alto | Check Point |
|---|---|---|---|---|
| สถานะระบบ | `show version` | `get system status` | `show system info` | `cpview` / `fw stat` |
| interface | `show ip int brief` | `get system interface physical` | `show interface all` | `show interfaces all` |
| route | `show ip route` | `get router info routing-table all` | `show routing route` | `show route` |
| route ไป IP | `show ip route <ip>` | `get router info routing-table details <ip>` | `test routing fib-lookup ...` | `ip route get <ip>` |
| ping จาก source | `ping <ip> source <intf>` | `exe ping-options source` + `exe ping` | `ping source <ip> host <ip>` | `ping -I <intf> <ip>` |
| policy ที่ match | `show access-lists` (hit count) | Policy Lookup / `diag firewall iprope lookup` | `test security-policy-match` | SmartConsole / `fw ctl zdebug drop` |
| session | — | `diag sys session list` | `show session all filter ...` | `fw tab -t connections` |
| เหตุผลที่ drop | ACL log | `diag debug flow` | `show counter global ... drop` | `fw ctl zdebug drop` |
| capture | `monitor capture` | `diag sniffer packet` | `debug dataplane packet-diag` | `fw monitor` / `tcpdump` |
| VPN | `show crypto ipsec sa` | `get vpn ipsec tunnel summary` | `show vpn ipsec-sa` | `vpn tu` |
| HA | `show standby brief` | `get system ha status` | `show high-availability state` | `cphaprob state` |
