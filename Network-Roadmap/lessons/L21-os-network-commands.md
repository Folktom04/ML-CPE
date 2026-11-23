# บทเรียน Level 21 — คำสั่งเครือข่ายพื้นฐานบน OS (ฉบับละเอียด)

> อ่านจบแล้วจะ: ใช้คำสั่งดู IP, route, ARP, DNS, socket, interface error บน Windows / Linux / macOS ได้คล่อง · อ่านผลลัพธ์และรู้ว่าแต่ละค่าบอกอะไร · มีชุดคำสั่ง "ตรวจสุขภาพเครือข่าย" ไว้ใช้ทันที

---

## 1. ทำไมต้องคล่องคำสั่ง

ในงานจริง วิศวกรต้องเข้าเครื่องผู้ใช้/เซิร์ฟเวอร์ผ่าน remote แล้วหาสาเหตุให้เร็ว GUI แต่ละเวอร์ชันต่างกันและช้า ส่วน **command line เหมือนกันทุกเครื่อง เร็ว คัดลอกผลส่งต่อได้ และเขียนเป็นสคริปต์อัตโนมัติได้**

---

## 2. ตารางเทียบคำสั่ง 3 OS

| งาน | Windows (CMD / PowerShell) | Linux | macOS |
|---|---|---|---|
| ดู IP/interface | `ipconfig /all` · `Get-NetIPConfiguration` | `ip addr` (`ip a`) | `ifconfig` · `ipconfig getifaddr en0` |
| ดู route | `route print` · `Get-NetRoute` | `ip route` (`ip r`) | `netstat -rn` |
| ดู default gateway | `ipconfig` | `ip route \| grep default` | `route -n get default` |
| ดู ARP/neighbor | `arp -a` · `Get-NetNeighbor` | `ip neigh` | `arp -a` |
| ดู DNS ที่ใช้ | `ipconfig /all` · `Get-DnsClientServerAddress` | `resolvectl status` · `cat /etc/resolv.conf` | `scutil --dns` |
| ล้าง DNS cache | `ipconfig /flushdns` | `resolvectl flush-caches` | `sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder` |
| ขอ IP ใหม่ (DHCP) | `ipconfig /release` + `/renew` | `sudo dhclient -r && sudo dhclient` หรือ `nmcli con up <ชื่อ>` | `sudo ipconfig set en0 DHCP` |
| ดู port ที่เปิด/การเชื่อมต่อ | `netstat -ano` · `Get-NetTCPConnection` | `ss -tulpn` · `ss -tan` | `lsof -i -P` · `netstat -an` |
| ทดสอบ port | `Test-NetConnection host -Port 443` | `nc -zv host 443` | `nc -zv host 443` |
| ping / trace | `ping` · `tracert` · `pathping` | `ping` · `traceroute` · `mtr` | `ping` · `traceroute` |
| DNS lookup | `nslookup` · `Resolve-DnsName` | `dig` · `host` · `nslookup` | `dig` · `nslookup` |
| speed/duplex/error ของ NIC | `Get-NetAdapter` · `Get-NetAdapterStatistics` | `ethtool eth0` · `ip -s link` | `networksetup -getMedia en0` |
| ชื่อเครื่อง | `hostname` | `hostname` · `hostnamectl` | `hostname` |
| Wi-Fi | `netsh wlan show interfaces` | `nmcli dev wifi` · `iw dev wlan0 link` | `wdutil info` (sudo) |

> 💡 `ifconfig`, `netstat`, `route`, `arp` บน Linux เป็นคำสั่งรุ่นเก่า (แพ็กเกจ net-tools) distro ใหม่อาจไม่มี ให้ใช้ชุด `ip` และ `ss` แทน

---

## 3. อ่านผล `ipconfig /all` (Windows)

```
Ethernet adapter Ethernet:
   Description . . . . . . . . . . . : Intel(R) Ethernet Connection
   Physical Address. . . . . . . . . : 00-1A-2B-3C-4D-5E        ← MAC
   DHCP Enabled. . . . . . . . . . . : Yes                       ← ได้ IP จาก DHCP
   IPv4 Address. . . . . . . . . . . : 192.168.10.55(Preferred)  ← "Duplicate" = IP ชน
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
   Lease Obtained. . . . . . . . . . : 23 November 2026 08:00
   Lease Expires . . . . . . . . . . : 24 November 2026 08:00
   Default Gateway . . . . . . . . . : 192.168.10.1
   DHCP Server . . . . . . . . . . . : 10.0.0.10                 ← server ที่แจก (ตรวจ rogue DHCP)
   DNS Servers . . . . . . . . . . . : 10.0.0.53
   Connection-specific DNS Suffix  . : corp.local
```
**สิ่งที่ต้องดูทุกครั้ง:** IP อยู่วงที่ถูกต้อง? (ไม่ใช่ 169.254.x.x) · mask ถูก? · gateway อยู่วงเดียวกัน? · DNS ถูก (เครื่องในโดเมนต้องเป็น DNS ของ AD)? · DHCP server เป็นของเราจริง?

## 4. อ่านผล `ip a` และ `ip r` (Linux)

```
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP
    link/ether 52:54:00:12:34:56 brd ff:ff:ff:ff:ff:ff
    inet 10.0.0.15/24 brd 10.0.0.255 scope global dynamic eth0
    inet6 fe80::5054:ff:fe12:3456/64 scope link
```
- **UP** = เปิดใช้งาน (admin), **LOWER_UP** = มีสัญญาณ (สายเสียบ/link ขึ้น) ถ้ามี UP แต่ไม่มี LOWER_UP = สาย/อีกฝั่งมีปัญหา
- **mtu**, **state UP/DOWN**, **dynamic** = ได้จาก DHCP

```
$ ip r
default via 10.0.0.1 dev eth0 proto dhcp metric 100     ← default gateway
10.0.0.0/24 dev eth0 proto kernel scope link src 10.0.0.15
$ ip route get 8.8.8.8                                   ← ดูว่าจะออกทางไหนจริง
8.8.8.8 via 10.0.0.1 dev eth0 src 10.0.0.15
```

## 5. ดูการเชื่อมต่อและ port

```bash
ss -tulpn                    # port ที่ listen + process (ต้อง sudo เพื่อเห็นชื่อ process)
ss -tan state established    # การเชื่อมต่อที่เปิดอยู่
ss -s                        # สรุปจำนวนแต่ละ state
```
```powershell
netstat -ano | findstr :443                         # หาว่า PID ไหนใช้ port 443
tasklist /FI "PID eq 4321"                          # PID นั้นคือโปรแกรมอะไร
Get-NetTCPConnection -State Listen | Select LocalAddress,LocalPort,OwningProcess | Sort LocalPort
```
**ใช้แก้ปัญหา:** "เปิดบริการไม่ขึ้นเพราะ port ถูกใช้อยู่แล้ว", "server เปิดบริการแล้วจริงไหม", "listen ที่ 127.0.0.1 จึงเข้าจากเครื่องอื่นไม่ได้"

## 6. ดู error ของ interface — หาปัญหาชั้นกายภาพ

```bash
ip -s link show eth0          # RX/TX: packets, errors, dropped
ethtool eth0                  # Speed: 1000Mb/s, Duplex: Full, Link detected: yes
ethtool -S eth0 | grep -i err # ตัวนับ error ละเอียด
```
```powershell
Get-NetAdapter | Select Name,Status,LinkSpeed,FullDuplex
Get-NetAdapterStatistics -Name Ethernet
```
- **errors/CRC เพิ่มขึ้นเรื่อย ๆ** → สาย/หัว/พอร์ตเสีย, สัญญาณรบกวน, duplex mismatch
- **dropped** → buffer เต็ม/รับไม่ทัน
- **Speed 100Mb/s บนพอร์ต 1G** → สายมีคู่เสีย

## 7. Test-NetConnection — มีดพกของ Windows

```powershell
Test-NetConnection 10.0.0.5                       # ping + ข้อมูล route
Test-NetConnection 10.0.0.5 -Port 3389            # TcpTestSucceeded : True/False
Test-NetConnection google.com -TraceRoute
Test-NetConnection -ComputerName sql01 -Port 1433 -InformationLevel Detailed
```
`TcpTestSucceeded : False` + `PingSucceeded : True` → เครื่องปลายทางอยู่ แต่ port ปิด/ถูก firewall บล็อก

---

## 8. ชุดคำสั่ง "Health Check" 1 นาที

**Windows (PowerShell)**
```powershell
Get-NetIPConfiguration                     # IP, gateway, DNS
Test-NetConnection (Get-NetRoute -DestinationPrefix 0.0.0.0/0).NextHop   # ping gateway
Test-NetConnection 8.8.8.8                 # ออกอินเทอร์เน็ต
Resolve-DnsName google.com                 # DNS
Test-NetConnection google.com -Port 443    # HTTPS
```
**Linux**
```bash
ip -br a; ip r
ping -c 3 $(ip route | awk '/default/ {print $3; exit}')
ping -c 3 8.8.8.8
dig +short google.com
curl -sI https://google.com | head -1
```
ผลแต่ละบรรทัดบอกได้ทันทีว่าปัญหาอยู่ที่ชั้นไหน (IP → gateway → อินเทอร์เน็ต → DNS → แอป)

---

## 9. เคล็ดลับ

- ใส่ `-n` (Linux) หรือ `-d` (tracert) เพื่อ **ไม่ resolve ชื่อ** ทำให้คำสั่งเร็วขึ้นมาก
- ส่งผลให้คนอื่น: `ipconfig /all > C:\temp\net.txt` · `ip a > net.txt`
- เปิด PowerShell/CMD แบบ **Run as administrator** สำหรับคำสั่งที่แก้ไขค่า (flushdns, release/renew, arp -d)
- ใช้ `watch -n1 'ip -s link show eth0'` (Linux) ดูตัวนับเปลี่ยนแบบ real-time

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| `ipconfig` ไม่มี DNS แสดง | ต้องใช้ `ipconfig /all` |
| interface UP แปลว่าสายเสียบอยู่ | Linux ดูที่ LOWER_UP / `ethtool` "Link detected" |
| ping ได้ = บริการใช้ได้ | ต้องทดสอบ port ของบริการด้วย (Test-NetConnection/nc) |
| `ifconfig` คือคำสั่งมาตรฐานของ Linux | Linux ใหม่ใช้ `ip`/`ss` |

---

## 11. Cheat Sheet

```
Windows: ipconfig /all · route print · arp -a · netstat -ano · nslookup · tracert
         Get-NetIPConfiguration · Test-NetConnection host -Port N · Resolve-DnsName
Linux:   ip a · ip r · ip route get X · ip neigh · ss -tulpn · dig · ethtool · ip -s link
macOS:   ifconfig · netstat -rn · arp -a · lsof -i -P · scutil --dns
ลำดับ health check: IP/mask/GW/DNS → ping GW → ping 8.8.8.8 → DNS → port 443
```

---

## 12. แบบทดสอบ 10 ข้อ

1. คำสั่ง Windows ที่แสดง DNS server และ DHCP server ของเครื่อง
2. คำสั่ง Linux ดู default gateway
3. ต้องการรู้ว่า packet ไป 8.8.8.8 จะออก interface ไหนบน Linux ใช้คำสั่งอะไร
4. คำสั่งดูว่าโปรแกรมไหนใช้ port 8080 บน Linux และบน Windows
5. ผล `ip a` แสดง `<UP>` แต่ไม่มี `LOWER_UP` หมายความว่าอะไร
6. คำสั่ง PowerShell ทดสอบว่าเข้าพอร์ต 1433 ของ sql01 ได้หรือไม่
7. `PingSucceeded : True` แต่ `TcpTestSucceeded : False` หมายความว่าอะไร
8. คำสั่งดู speed/duplex ของการ์ดเครือข่ายบน Linux
9. RX errors เพิ่มขึ้นตลอดเวลา สงสัยอะไร
10. เรียงลำดับการตรวจสุขภาพเครือข่ายแบบเร็ว 5 ขั้น

<details><summary><b>เฉลย</b></summary>

1. `ipconfig /all`
2. `ip route` (ดูบรรทัด default)
3. `ip route get 8.8.8.8`
4. Linux `ss -tulpn | grep 8080` (sudo); Windows `netstat -ano | findstr :8080` แล้ว `tasklist /FI "PID eq <pid>"`
5. interface เปิดใช้งานแต่ไม่มีสัญญาณ link (สายหลุด/อีกฝั่งปิด)
6. `Test-NetConnection sql01 -Port 1433`
7. เครื่องปลายทางออนไลน์ แต่ port นั้นปิดหรือถูก firewall บล็อก
8. `ethtool eth0`
9. สาย/หัวต่อ/พอร์ตเสีย สัญญาณรบกวน หรือ duplex mismatch
10. ตรวจ IP/mask/gateway/DNS → ping gateway → ping 8.8.8.8 → ทดสอบ DNS → ทดสอบ port/HTTP ของบริการ
</details>

---

➡️ ต่อไป: **Level 22 — Wireshark**
