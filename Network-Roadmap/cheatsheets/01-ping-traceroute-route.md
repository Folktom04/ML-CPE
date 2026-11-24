# คำสั่งตรวจเช็คพื้นฐาน: Ping, Traceroute, Route, DNS, Port (Windows / Linux / macOS)

> ใช้ตรวจจากเครื่องผู้ใช้หรือ server ก่อนไปดูอุปกรณ์เครือข่าย · ดูคำสั่งบนอุปกรณ์ได้ใน [Cisco](02-cisco.md) · [FortiGate](03-fortigate.md) · [Firewall อื่น ๆ](04-paloalto-checkpoint.md) · [ลำดับการไล่ปัญหา](05-troubleshooting-flow.md)

---

## 1. ดู IP / Gateway / DNS ของเครื่อง

| สิ่งที่ต้องการ | Windows | Linux | macOS |
|---|---|---|---|
| IP, mask, gateway, DNS, MAC | `ipconfig /all` | `ip a` · `ip r` · `resolvectl status` | `ifconfig` · `networksetup -getinfo Wi-Fi` |
| แบบสั้น (PowerShell) | `Get-NetIPConfiguration` | `ip -br a` | `ipconfig getifaddr en0` |
| ขอ IP ใหม่ (DHCP) | `ipconfig /release` → `ipconfig /renew` | `sudo dhclient -r && sudo dhclient` หรือ `nmcli con up <ชื่อ>` | `sudo ipconfig set en0 DHCP` |
| ล้าง DNS cache | `ipconfig /flushdns` | `resolvectl flush-caches` | `sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder` |
| ตาราง ARP (IP ↔ MAC) | `arp -a` | `ip neigh` | `arp -a` |
| ดู Wi-Fi (สัญญาณ, ช่อง, AP) | `netsh wlan show interfaces` | `iw dev wlan0 link` · `nmcli dev wifi` | กด Option + คลิกไอคอน Wi-Fi |

**อ่านผล:** IP ขึ้นต้น `169.254.x.x` (Windows) = **ไม่ได้ IP จาก DHCP** → ตรวจสาย/VLAN/DHCP server/DHCP relay

---

## 2. Ping

| ต้องการ | Windows | Linux / macOS |
|---|---|---|
| ping ปกติ | `ping 8.8.8.8` | `ping -c 4 8.8.8.8` |
| ping ไม่หยุด | `ping -t 8.8.8.8` (Ctrl+C หยุด) | `ping 8.8.8.8` |
| กำหนดจำนวน | `ping -n 100 10.0.0.1` | `ping -c 100 10.0.0.1` |
| กำหนดขนาด | `ping -l 1400 10.0.0.1` | `ping -s 1400 10.0.0.1` |
| **ทดสอบ MTU (ห้าม fragment)** | `ping -f -l 1472 10.0.0.1` | Linux `ping -M do -s 1472 10.0.0.1` · macOS `ping -D -s 1472 10.0.0.1` |
| เลือก interface/IP ต้นทาง | `ping -S 10.0.0.5 8.8.8.8` | `ping -I eth1 8.8.8.8` |
| IPv6 | `ping -6 2001:4860:4860::8888` | `ping -6 ...` หรือ `ping6 ...` |
| ping เร็ว ๆ (หา loss) | — | `sudo ping -i 0.2 -c 500 10.0.0.1` |

> 1472 + 28 (IP header 20 + ICMP 8) = 1500 · ถ้า 1472 ไม่ผ่านแต่ค่าเล็กกว่าผ่าน แสดงว่า MTU บนเส้นทางเล็กกว่า 1500 (มักเกิดกับ VPN/PPPoE)

### อ่านผล Ping
| ผลลัพธ์ | ความหมาย | ตรวจต่อ |
|---|---|---|
| `Reply from ... time=12ms TTL=118` | ปกติ | ดู time ว่าสูงหรือแกว่งไหม |
| `Request timed out` | ไม่มีคำตอบกลับ: ปลายทางปิด/firewall บล็อก ICMP/ไม่มีเส้นทางกลับ | traceroute, ดู route ขากลับ, firewall |
| `Destination host unreachable` (Reply from **IP ของ gateway หรือของตัวเอง**) | หา MAC ปลายทางไม่ได้ (ARP ล้มเหลว) หรือ router ไม่มี route | ARP, VLAN, routing |
| `Destination net unreachable` | router ไม่มี route ไปเครือข่ายนั้น | routing table ของ router ที่ตอบ |
| `TTL expired in transit` | **routing loop** | traceroute ดู hop ที่วนซ้ำ |
| `General failure` / `Transmit failed` | เครื่องตัวเองไม่มี route/interface down | `ipconfig`, `route print` |
| `Packet needs to be fragmented but DF set` | MTU เล็กกว่าขนาดที่ส่ง | ลดขนาด/ตั้ง MSS |
| `Ping request could not find host` | DNS resolve ไม่ได้ | `nslookup` |
| loss เป็นช่วง ๆ / time แกว่งมาก | congestion, Wi-Fi สัญญาณอ่อน, สายเสีย | `mtr`/`pathping`, counter errors |

**TTL บอกอะไรได้:** TTL ที่ได้ใกล้ 64 = Linux/อุปกรณ์เครือข่ายหลายรุ่น · ใกล้ 128 = Windows · ใกล้ 255 = Cisco/อุปกรณ์เครือข่าย (ค่าเริ่มต้นลบจำนวน hop)

> ⚠️ ping ไม่ผ่าน **ไม่ได้แปลว่าเครื่องปลายทางดับเสมอ** (หลายระบบบล็อก ICMP) → ทดสอบ port ด้วย (ข้อ 5)

---

## 3. Traceroute — ดูเส้นทางและ hop ที่มีปัญหา

| ต้องการ | Windows | Linux | macOS |
|---|---|---|---|
| ปกติ (ไม่แปลงชื่อ = เร็วกว่า) | `tracert -d 8.8.8.8` | `traceroute -n 8.8.8.8` | `traceroute -n 8.8.8.8` |
| ทดสอบด้วย TCP port (ผ่าน firewall ที่บล็อก ICMP/UDP) | `Test-NetConnection 8.8.8.8 -TraceRoute` | `sudo traceroute -n -T -p 443 example.com` · `tcptraceroute` | `sudo traceroute -n -P tcp -p 443 example.com` |
| ดู loss/latency ทุก hop ต่อเนื่อง | `pathping -n 8.8.8.8` (ใช้เวลา ~5 นาที) | `mtr -rwbzc 100 8.8.8.8` ⭐ | `brew install mtr` แล้วใช้เหมือน Linux |
| ดู MTU ตามเส้นทาง | — | `tracepath -n 8.8.8.8` | — |

### อ่านผล Traceroute / mtr
| เห็น | ความหมาย |
|---|---|
| `* * *` ที่ hop กลาง แต่ hop ถัดไปตอบปกติ | router ตัวนั้นไม่ตอบ ICMP (ปกติ ไม่ใช่ปัญหา) |
| `* * *` ตั้งแต่ hop หนึ่งไปจนจบ | traffic ถูกบล็อก/หายตั้งแต่จุดนั้น หรือปลายทางไม่ตอบ |
| IP ซ้ำวนไปมา (A → B → A → B) | **routing loop** |
| latency กระโดดที่ hop หนึ่งและ **ทุก hop ถัดไปสูงตาม** | ปัญหาจริงที่ลิงก์ช่วงนั้น |
| latency สูงเฉพาะ hop เดียว hop ถัดไปปกติ | router ตอบ ICMP ช้า (ไม่ใช่ปัญหา) |
| mtr loss เฉพาะ hop กลาง แต่ปลายทาง 0% | rate-limit ICMP ของ router นั้น (ไม่ใช่ปัญหา) |
| mtr loss ที่ปลายทาง และเริ่มตั้งแต่ hop X | ปัญหาเริ่มที่ hop X |
| hop แรกไม่ใช่ gateway ที่คาดไว้ | เครื่องใช้ gateway/route ผิด, VPN ดึง route |

---

## 4. Routing Table ของเครื่อง

| ต้องการ | Windows | Linux | macOS |
|---|---|---|---|
| ดูตาราง route | `route print` · `Get-NetRoute` | `ip r` (IPv6: `ip -6 r`) | `netstat -rn` |
| **ดูว่าไป IP นี้ใช้ route/interface ไหน** ⭐ | `Find-NetRoute -RemoteIPAddress 10.20.1.5` | `ip route get 10.20.1.5` | `route -n get 10.20.1.5` |
| เพิ่ม route ชั่วคราว | `route add 10.20.0.0 mask 255.255.0.0 10.0.0.254` | `sudo ip route add 10.20.0.0/16 via 10.0.0.254` | `sudo route -n add -net 10.20.0.0/16 10.0.0.254` |
| เพิ่ม route ถาวร | `route -p add ...` | ใส่ใน netplan/NetworkManager | — |
| ลบ route | `route delete 10.20.0.0` | `sudo ip route del 10.20.0.0/16` | `sudo route -n delete -net 10.20.0.0/16` |

**อ่านผล:** มี default route (`0.0.0.0/0` หรือ `default`) มากกว่า 1 อัน หรือ route ของ VPN ทับ subnet ภายใน → traffic ไปผิดทาง · route ที่ prefix ยาวกว่า (เจาะจงกว่า) ชนะเสมอ (longest prefix match)

---

## 5. ทดสอบ Port / บริการ (สำคัญกว่า ping)

| ต้องการ | Windows (PowerShell) | Linux / macOS |
|---|---|---|
| port TCP เปิดไหม | `Test-NetConnection 10.0.0.10 -Port 443` → ดู `TcpTestSucceeded : True` | `nc -zv 10.0.0.10 443` |
| ทดสอบหลาย port | `443,3389,445 \| % { Test-NetConnection 10.0.0.10 -Port $_ }` | `nc -zv 10.0.0.10 22 80 443` |
| ทดสอบ HTTP/HTTPS ละเอียด | `curl.exe -v https://site` · `Invoke-WebRequest https://site` | `curl -v https://site` · `curl -I https://site` |
| ดูเวลาแต่ละช่วง (DNS/connect/TLS) | `curl.exe -w ...` เหมือน Linux | `curl -o /dev/null -s -w "dns:%{time_namelookup} connect:%{time_connect} tls:%{time_appconnect} total:%{time_total}\n" https://site` |
| ดู certificate | — | `openssl s_client -connect site:443 -servername site </dev/null \| openssl x509 -noout -subject -issuer -dates` |
| port ที่เครื่องตัวเองเปิดฟัง | `netstat -ano \| findstr LISTENING` · `Get-NetTCPConnection -State Listen` | `sudo ss -tulpn` |
| connection ที่เชื่อมอยู่ | `netstat -ano` | `ss -tnp` |

### อ่านผล Port
| ผล | ความหมาย |
|---|---|
| เชื่อมต่อได้ (`succeeded` / `open`) | network + firewall ผ่าน และมีบริการฟังอยู่ |
| `Connection refused` | ถึงเครื่องแล้ว แต่ **ไม่มีบริการฟัง port นั้น** (หรือ firewall ตอบ RST) |
| `timed out` | packet ถูก **firewall drop** ระหว่างทาง หรือไม่มี route |

---

## 6. DNS

| ต้องการ | Windows | Linux / macOS |
|---|---|---|
| ถาม DNS ปกติ | `nslookup example.com` · `Resolve-DnsName example.com` | `dig example.com` · `dig +short example.com` |
| ถาม DNS server ที่ระบุ | `nslookup example.com 8.8.8.8` | `dig @8.8.8.8 example.com` |
| ชนิด record | `Resolve-DnsName example.com -Type MX` | `dig example.com MX` · `dig -x 8.8.8.8` (reverse) |
| ไล่ตั้งแต่ root | — | `dig +trace example.com` |
| ดู DNS ที่เครื่องใช้ | `Get-DnsClientServerAddress` | `resolvectl status` · `cat /etc/resolv.conf` |

**อ่านผล:** `NXDOMAIN` = ไม่มีชื่อนี้ · `SERVFAIL` = DNS server มีปัญหา/DNSSEC ผิด · `timed out` = ติดต่อ DNS server ไม่ได้ (UDP/TCP 53 ถูกบล็อก?) · ผลจาก DNS ภายในกับ 8.8.8.8 ต่างกัน = split DNS หรือ record ไม่ตรงกัน

---

## 7. ความเร็วและคุณภาพ

```bash
iperf3 -s                         # ฝั่ง server
iperf3 -c 10.0.0.10 -t 30         # TCP 30 วินาที
iperf3 -c 10.0.0.10 -R            # ทิศกลับ
iperf3 -c 10.0.0.10 -P 8          # 8 stream
iperf3 -c 10.0.0.10 -u -b 50M     # UDP ดู jitter/loss
```
รายละเอียดดู [Level 90](../lessons/L90-performance-testing.md)

---

## 8. จับ Packet บนเครื่อง

```bash
sudo tcpdump -ni eth0 host 10.0.0.10                 # ทุก packet กับ host นี้
sudo tcpdump -ni eth0 host 10.0.0.10 and port 443    # เฉพาะ port
sudo tcpdump -ni any icmp                            # ดู ping
sudo tcpdump -ni eth0 -w cap.pcap host 10.0.0.10     # บันทึกไปเปิดใน Wireshark
```
Windows: Wireshark หรือ `pktmon start --capture` → `pktmon stop` → `pktmon etl2pcap PktMon.etl`

---

## 9. Cheat Sheet ย่อ (ไล่จากใกล้ไปไกล)

```
1. ipconfig /all | ip a          → มี IP/gateway/DNS ถูกต้องไหม (169.254 = DHCP ไม่ได้)
2. ping <gateway>                → ถึง gateway ไหม
3. ping 8.8.8.8                  → ออกเน็ตได้ไหม (ไม่ผ่าน DNS)
4. nslookup google.com | dig     → DNS ใช้ได้ไหม
5. tracert -d / mtr <ปลายทาง>     → ติดที่ hop ไหน
6. Test-NetConnection -Port / nc -zv → port/บริการเปิดไหม
7. ping -f -l 1472 / ping -M do -s 1472 → ปัญหา MTU ไหม
8. route print / ip route get    → ไปผิดเส้นทาง/VPN ทับ route ไหม
```
