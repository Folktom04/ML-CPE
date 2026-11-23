# Tier 3 — เครื่องมือ, OS Networking & Troubleshooting (Level 21–30)

> เป้าหมายของ Tier: ใช้เครื่องมือจริงที่ Network Engineer ใช้ทุกวัน และ troubleshoot อย่างเป็นระบบ

---

## Level 21 — คำสั่งเครือข่ายพื้นฐานบน OS

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L21-os-network-commands.md](lessons/L21-os-network-commands.md)

**สิ่งที่ต้องรู้**
| งาน | Linux | Windows | macOS |
|---|---|---|---|
| ดู IP | `ip a` | `ipconfig /all` | `ifconfig` |
| ดู route | `ip r` | `route print` | `netstat -rn` |
| ดู ARP | `ip neigh` | `arp -a` | `arp -a` |
| ดู socket | `ss -tulpn` | `netstat -ano` | `lsof -i` |
| DNS cache | `resolvectl flush-caches` | `ipconfig /flushdns` | `dscacheutil -flushcache` |
| ต่ออายุ DHCP | `dhclient -r && dhclient` | `ipconfig /release` `/renew` | — |

- `ethtool` ดู speed/duplex/error, `ip -s link` ดู counter

**แบบทดสอบ**
1. คำสั่งดูว่า process ไหน listen port 443 บน Linux
2. ดู default gateway บน Windows
3. ดู interface error counter บน Linux
4. ล้าง DNS cache บน Windows
5. ดู speed/duplex ของ eth0

<details><summary>เฉลย</summary>

1. `ss -tlpn | grep :443`
2. `ipconfig` หรือ `route print 0.0.0.0`
3. `ip -s link show eth0` / `ethtool -S eth0`
4. `ipconfig /flushdns`
5. `ethtool eth0`
</details>

**5 โปรเจค**
- ⭐ P1: Cheat sheet 3 OS (ตารางข้างบนขยายเป็น 40 คำสั่ง)
- ⭐ P2: Bash script "netinfo" สรุป IP, GW, DNS, public IP, port ที่เปิด
- ⭐⭐ P3: PowerShell version ของ P2
- ⭐⭐ P4: Python cross-platform ด้วย `psutil` รายงาน network ของเครื่อง เป็น JSON
- ⭐⭐ P5: สคริปต์ health-check ประจำวัน (ping GW, DNS resolve, HTTP check) ส่งผลแจ้งเตือน

---

## Level 22 — Wireshark

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L22-wireshark.md](lessons/L22-wireshark.md)

**สิ่งที่ต้องรู้**
- Capture filter (BPF) vs Display filter
- Display filter: `ip.addr==10.0.0.1`, `tcp.port==443`, `dns`, `tcp.flags.syn==1 && tcp.flags.ack==0`, `tcp.analysis.retransmission`, `http.response.code>=400`
- Follow TCP Stream, Statistics → Conversations / IO Graph / Expert Info
- Coloring rules, Profiles, Name resolution
- จับที่ไหน: SPAN/mirror port, TAP, บนเครื่องเอง

**แบบทดสอบ**
1. Filter หา TCP retransmission
2. Filter เฉพาะ DNS ที่ตอบ NXDOMAIN
3. Capture filter vs Display filter ต่างกันอย่างไร
4. ต้องการจับ traffic ของเครื่องอื่นบน switch ทำอย่างไร
5. ใช้เมนูไหนดูว่า IP คู่ไหนคุยกันมากที่สุด

<details><summary>เฉลย</summary>

1. `tcp.analysis.retransmission`
2. `dns.flags.rcode == 3`
3. Capture = กรองก่อนเก็บ (ประหยัดพื้นที่, syntax BPF); Display = กรองตอนแสดง
4. ตั้ง SPAN/port mirror หรือใช้ network TAP
5. Statistics → Conversations
</details>

**5 โปรเจค**
- ⭐ P1: ทำ cheat sheet display filter 30 ตัว
- ⭐⭐ P2: แก้โจทย์จาก Wireshark sample captures / Malware-Traffic-Analysis (ระดับเริ่มต้น)
- ⭐⭐ P3: วิเคราะห์ว่าทำไมเว็บโหลดช้าจาก pcap (หา RTT, retransmission, DNS delay)
- ⭐⭐ P4: เขียน Lua dissector ง่าย ๆ สำหรับ protocol ที่ตัวเองสร้าง
- ⭐⭐⭐ P5: ใช้ `pyshark`/`tshark` ทำรายงาน pcap อัตโนมัติ (top talkers, protocols, errors)

---

## Level 23 — tcpdump & CLI capture

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L23-tcpdump.md](lessons/L23-tcpdump.md)

**สิ่งที่ต้องรู้**
```bash
tcpdump -i eth0 -nn host 10.0.0.5 and port 53
tcpdump -i any -w cap.pcap -C 100 -W 5        # ring buffer
tcpdump -nn 'tcp[tcpflags] & tcp-syn != 0'
tshark -r cap.pcap -Y http -T fields -e ip.src -e http.host
```
- ใช้บน server/router ที่ไม่มี GUI, ส่งไฟล์ pcap มาเปิด Wireshark
- Packet capture บนอุปกรณ์: Cisco EPC, Fortinet `diagnose sniffer`, Palo Alto `debug dataplane packet-diag`

**แบบทดสอบ**
1. `-nn` ทำอะไร
2. จับเฉพาะ traffic ที่ไม่ใช่ SSH
3. จับเป็น ring buffer เพื่ออะไร
4. แสดงเนื้อหา packet เป็น ASCII ใช้ option ใด
5. ดึงเฉพาะ field ออกมาเป็น CSV ใช้เครื่องมือใด

<details><summary>เฉลย</summary>

1. ไม่ resolve ชื่อ host และ port
2. `tcpdump not port 22`
3. capture ยาวนานโดยไม่ทำ disk เต็ม
4. `-A` (หรือ `-X` hex+ascii)
5. `tshark -T fields -E separator=,`
</details>

**5 โปรเจค**
- ⭐ P1: จับ DHCP DORA บน Linux VM ด้วย tcpdump
- ⭐⭐ P2: สคริปต์ capture อัตโนมัติเมื่อ ping fail (trigger-based capture)
- ⭐⭐ P3: ตั้ง capture ring buffer 24 ชั่วโมงบน server แล้ววิเคราะห์ traffic peak
- ⭐⭐ P4: ทำ packet capture บนอุปกรณ์จริง/virtual (Cisco CSR EPC หรือ FortiGate VM)
- ⭐⭐⭐ P5: pipeline: tcpdump → tshark → CSV → pandas → กราฟ top talkers

---

## Level 24 — Nmap & Network Discovery

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L24-nmap-discovery.md](lessons/L24-nmap-discovery.md)

> ⚠️ สแกนเฉพาะเครือข่ายที่ตัวเองเป็นเจ้าของหรือได้รับอนุญาตเป็นลายลักษณ์อักษรเท่านั้น

**สิ่งที่ต้องรู้**
```bash
nmap -sn 192.168.1.0/24          # host discovery
nmap -sS -p- 10.0.0.5            # SYN scan ทุก port
nmap -sV -O 10.0.0.5             # version + OS
nmap -sU -p 53,161 10.0.0.5      # UDP
nmap --script ssl-enum-ciphers -p 443 host
```
- State: open / closed / filtered
- ใช้ทำ asset inventory, ตรวจ firewall rule, audit

**แบบทดสอบ**
1. `filtered` หมายถึงอะไร
2. ทำไม UDP scan ช้า
3. `-sS` ต้องการสิทธิ์อะไร
4. ใช้ nmap ตรวจว่า firewall rule ใหม่ทำงานถูกต้องอย่างไร
5. NSE คืออะไร

<details><summary>เฉลย</summary>

1. ไม่ได้รับตอบหรือได้ ICMP unreachable — มี firewall กรอง
2. port ปิดตอบ ICMP ซึ่งถูก rate-limit, port เปิดมักไม่ตอบ ต้องรอ timeout
3. root/admin (raw socket)
4. สแกนจากฝั่ง source ที่ควรถูกอนุญาต/ปฏิเสธ แล้วเทียบกับ policy ที่คาดหวัง
5. Nmap Scripting Engine — สคริปต์ Lua สำหรับ detect/enum
</details>

**5 โปรเจค**
- ⭐ P1: Inventory เครือข่ายบ้าน: host, OS, service
- ⭐⭐ P2: สคริปต์ nmap รายสัปดาห์ + diff แจ้งเมื่อมี port ใหม่เปิด (`ndiff`)
- ⭐⭐ P3: แปลง nmap XML → รายงาน HTML/Excel ด้วย Python
- ⭐⭐ P4: Lab ตรวจ firewall policy: เขียน test matrix แล้ววัดจริงด้วย nmap
- ⭐⭐⭐ P5: สร้าง asset discovery dashboard (nmap + SNMP + DB + เว็บ)

---

## Level 25 — dig, curl, openssl, nc, iperf

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L25-dig-curl-openssl-nc-iperf.md](lessons/L25-dig-curl-openssl-nc-iperf.md)

**สิ่งที่ต้องรู้**
- `dig @8.8.8.8 example.com +short`, `dig +trace`, `dig -x`
- `curl -v`, `curl -w "%{time_connect} %{time_starttransfer}\n"`, `--resolve`
- `openssl s_client -showcerts`, `openssl x509 -noout -dates`
- `nc -zv host 443` ทดสอบ port, `nc -l 9000`
- `iperf3 -s` / `iperf3 -c server -P 4 -R`

**แบบทดสอบ**
1. ทดสอบเว็บก่อนย้าย DNS (บังคับให้ชื่อชี้ IP ใหม่) ด้วย curl
2. วัดว่าเวลาส่วนไหนช้า (DNS/connect/TLS/TTFB)
3. ทดสอบว่า port 5432 ปลายทางเปิดจากเครื่องนี้ไหม (ไม่มี telnet)
4. ดูวันหมดอายุ cert
5. iperf3 `-R` ทำอะไร

<details><summary>เฉลย</summary>

1. `curl --resolve www.example.com:443:203.0.113.9 https://www.example.com`
2. `curl -w "%{time_namelookup} %{time_connect} %{time_appconnect} %{time_starttransfer}\n" -o /dev/null -s URL`
3. `nc -zv host 5432` หรือ PowerShell `Test-NetConnection host -Port 5432`
4. `openssl s_client -connect h:443 </dev/null | openssl x509 -noout -dates`
5. Reverse — server ส่งหา client (วัดฝั่ง download)
</details>

**5 โปรเจค**
- ⭐ P1: ทำ toolkit cheat sheet "One-liner ช่วยชีวิต" 30 ข้อ
- ⭐⭐ P2: สคริปต์วัด web timing 10 เว็บทุก 5 นาที เก็บลง SQLite
- ⭐⭐ P3: วัด bandwidth ระหว่าง 2 VM / 2 เครื่องในบ้านด้วย iperf3 ทั้ง TCP/UDP ทำรายงาน
- ⭐⭐ P4: ทำ "connectivity test matrix" (CSV ของ src→dst:port) ทดสอบอัตโนมัติด้วย Python
- ⭐⭐⭐ P5: ทำเว็บ Looking Glass ส่วนตัว (ping/traceroute/dig จาก server ของเรา) ใส่ rate limit

---

## Level 26 — Linux Networking Configuration

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L26-linux-networking.md](lessons/L26-linux-networking.md)

**สิ่งที่ต้องรู้**
- Netplan (Ubuntu), NetworkManager (`nmcli`), systemd-networkd, `/etc/network/interfaces`
- `/etc/resolv.conf`, systemd-resolved, `/etc/hosts`
- Static route, policy routing (`ip rule`), bonding/teaming, VLAN subinterface, bridge
- `sysctl net.ipv4.ip_forward=1`
- Network namespace (`ip netns`) — ทำ lab บนเครื่องเดียว

```yaml
# /etc/netplan/01.yaml
network:
  version: 2
  ethernets:
    ens3:
      addresses: [10.0.0.10/24]
      routes: [{to: default, via: 10.0.0.1}]
      nameservers: {addresses: [1.1.1.1]}
  vlans:
    vlan20: {id: 20, link: ens3, addresses: [10.20.0.10/24]}
```

**แบบทดสอบ**
1. เปิด IP forwarding ถาวร
2. สร้าง VLAN 30 บน eth0 ด้วยคำสั่ง ip
3. bonding mode 4 คืออะไร
4. ทำไมแก้ /etc/resolv.conf แล้วหายหลัง reboot
5. `ip netns` ใช้ทำอะไร

<details><summary>เฉลย</summary>

1. `net.ipv4.ip_forward=1` ใน /etc/sysctl.d/*.conf แล้ว `sysctl --system`
2. `ip link add link eth0 name eth0.30 type vlan id 30`
3. 802.3ad LACP
4. ถูก systemd-resolved/NetworkManager สร้างทับ
5. แยก network stack — จำลองหลายเครื่อง/router บน host เดียว
</details>

**5 โปรเจค**
- ⭐ P1: ตั้ง static IP + DNS บน Ubuntu ด้วย netplan
- ⭐⭐ P2: Linux เป็น router 2 ขา + NAT + DHCP (dnsmasq)
- ⭐⭐ P3: สร้าง topology 3 router ด้วย `ip netns` + veth ด้วย bash script
- ⭐⭐ P4: ตั้ง bonding active-backup แล้วทดสอบดึงสาย/ปิด interface
- ⭐⭐⭐ P5: Policy-based routing: traffic จาก subnet A ออก ISP1, B ออก ISP2

---

## Level 27 — Windows Networking & PowerShell

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L27-windows-networking.md](lessons/L27-windows-networking.md)

**สิ่งที่ต้องรู้**
```powershell
Get-NetIPConfiguration
Test-NetConnection 10.0.0.5 -Port 445 -InformationLevel Detailed
Resolve-DnsName example.com -Type MX
Get-NetTCPConnection -State Listen
New-NetFirewallRule -DisplayName "Allow 8080" -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow
pktmon start --capture ; pktmon stop
```
- Network profile (Domain/Private/Public), Windows Defender Firewall
- AD-integrated DNS, DHCP Server role, NIC Teaming / SET
- `netsh` (legacy), `netsh wlan show wlanreport`

**แบบทดสอบ**
1. คำสั่ง PowerShell แทน telnet ทดสอบ port
2. Windows มี packet capture built-in ชื่ออะไร
3. ทำไม file sharing ใช้ไม่ได้เมื่อ profile เป็น Public
4. ดูรายงานปัญหา Wi-Fi ย้อนหลัง
5. Resolve-DnsName ต่างจาก nslookup อย่างไร

<details><summary>เฉลย</summary>

1. `Test-NetConnection -Port`
2. `pktmon` (หรือ `netsh trace`)
3. firewall profile Public block inbound SMB/discovery
4. `netsh wlan show wlanreport`
5. ใช้ resolver ของ Windows (เหมือนแอปจริง) ส่วน nslookup ถาม DNS server ตรง
</details>

**5 โปรเจค**
- ⭐ P1: สคริปต์ PowerShell รวบรวมข้อมูล network สำหรับ helpdesk เป็นไฟล์ zip
- ⭐⭐ P2: ติดตั้ง Windows Server lab: AD DS + DNS + DHCP
- ⭐⭐ P3: ทำ GPO ตั้ง firewall rule ให้ทุกเครื่องในโดเมน
- ⭐⭐ P4: pktmon capture → แปลง pcapng → วิเคราะห์ใน Wireshark
- ⭐⭐⭐ P5: สคริปต์ตรวจ network ของเครื่องลูกข่าย 50 เครื่องผ่าน WinRM สรุปเป็นรายงาน

---

## Level 28 — ตั้ง Lab: Packet Tracer, GNS3, EVE-NG, Containerlab

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L28-network-labs.md](lessons/L28-network-labs.md)

**สิ่งที่ต้องรู้**
- Cisco Packet Tracer: ฟรี เรียน CCNA ง่ายสุด แต่ฟีเจอร์จำกัด
- GNS3 / EVE-NG: รัน image จริง (IOSv, CSR1000v, vEOS, FortiGate, Palo Alto, Linux)
- Containerlab: lab ด้วย container (Arista cEOS, Nokia SR Linux, FRR) เหมาะกับ automation
- FRRouting (FRR) บน Linux = router open-source (OSPF/BGP)
- ทำ lab แบบ "Infrastructure as code": topology เป็นไฟล์ YAML เก็บใน Git

```yaml
# containerlab: lab.clab.yml
name: ospf3
topology:
  nodes:
    r1: {kind: linux, image: frrouting/frr:latest}
    r2: {kind: linux, image: frrouting/frr:latest}
  links:
    - endpoints: ["r1:eth1", "r2:eth1"]
```

**แบบทดสอบ**
1. ข้อดีของ Containerlab เทียบ GNS3
2. FRR คืออะไร
3. ทำไมควรเก็บ topology lab ใน Git
4. EVE-NG Community vs Pro ต่างกันหลัก ๆ อย่างไร
5. ทรัพยากรเครื่องสำคัญอะไรที่สุดสำหรับ lab VM จำนวนมาก

<details><summary>เฉลย</summary>

1. เบา เร็ว topology เป็นโค้ด เหมาะ CI/automation
2. Routing suite open-source (BGP, OSPF, IS-IS ฯลฯ) บน Linux
3. ทำซ้ำได้ แชร์ทีมได้ track การเปลี่ยนแปลง
4. Pro มีฟีเจอร์ เช่น hot-add link, Wireshark integration ดีกว่า, multi-user
5. RAM (และ CPU ที่รองรับ virtualization)
</details>

**5 โปรเจค**
- ⭐ P1: ติดตั้ง Packet Tracer + ทำ lab แรก 2 router
- ⭐⭐ P2: ติดตั้ง GNS3/EVE-NG + import IOSv/vIOS-L2
- ⭐⭐ P3: Containerlab 3 FRR router OSPF (เก็บไว้ใช้ต่อใน Tier 5)
- ⭐⭐ P4: เขียน README วิธีตั้ง lab ของตัวเองแบบให้เพื่อนทำตามได้ใน 30 นาที
- ⭐⭐⭐ P5: สร้าง repo "network-labs" รวม topology ทุก lab + script start/stop + CI ตรวจ YAML

---

## Level 29 — Cisco IOS พื้นฐาน (CLI ที่พบมากที่สุดในงาน)

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L29-cisco-ios-basics.md](lessons/L29-cisco-ios-basics.md)

**สิ่งที่ต้องรู้**
- Mode: User EXEC `>` → Privileged `#` → Global config `(config)#` → Interface `(config-if)#`
- ตั้งค่าเริ่มต้น: hostname, enable secret, console/vty password, `service password-encryption`, banner
- SSH: `ip domain-name`, `crypto key generate rsa modulus 2048`, `transport input ssh`, `login local`
- running-config vs startup-config, `copy run start` / `wr`
- `show ip interface brief`, `show run`, `show version`, `show interfaces`, `do` command
- `?`, Tab, `terminal length 0`, `| include` / `| section`

**แบบทดสอบ**
1. คำสั่งบันทึก config
2. ดูสถานะ interface ทุกตัวแบบย่อ
3. `enable password` vs `enable secret`
4. ขั้นตอนเปิด SSH v2 บน router
5. interface status "administratively down" แก้อย่างไร

<details><summary>เฉลย</summary>

1. `copy running-config startup-config` หรือ `write memory`
2. `show ip interface brief`
3. secret ถูก hash (แข็งแรงกว่า), password เป็น plain/type7
4. hostname, ip domain-name, crypto key generate rsa modulus 2048, ip ssh version 2, username X secret Y, line vty 0 4 → login local + transport input ssh
5. `no shutdown` ใน interface
</details>

**5 โปรเจค**
- ⭐ P1: Hardening template พื้นฐานของ router/switch (เก็บเป็นไฟล์)
- ⭐ P2: Lab ตั้ง SSH + user local + ปิด telnet แล้วทดสอบ
- ⭐⭐ P3: ทำ password recovery บน router (lab)
- ⭐⭐ P4: Backup/restore config ผ่าน TFTP/SCP
- ⭐⭐ P5: เปรียบเทียบ CLI Cisco vs Juniper Junos vs Arista EOS vs MikroTik (ตารางคำสั่งเทียบ 20 คำสั่ง)

---

## Level 30 — วิธีการ Troubleshoot อย่างเป็นระบบ

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L30-troubleshooting-methodology.md](lessons/L30-troubleshooting-methodology.md)

**สิ่งที่ต้องรู้**
- Approaches: Bottom-up, Top-down, Divide-and-conquer (เริ่มที่ L3 ping), Follow-the-path, Compare-config, Swap
- ขั้นตอน: เก็บข้อมูล → กำหนดขอบเขต (ใคร/อะไร/เมื่อไร/ที่ไหน/เปลี่ยนอะไรล่าสุด) → สมมติฐาน → ทดสอบ → แก้ → ยืนยัน → บันทึก
- "อะไรเปลี่ยนล่าสุด?" คือคำถามที่สำคัญที่สุด
- Baseline: รู้ว่า "ปกติ" เป็นอย่างไร
- เขียน RCA (Root Cause Analysis) แบบ blameless, 5 Whys

**แบบทดสอบ**
1. ผู้ใช้ 1 คนเข้าเว็บไม่ได้ แต่คนอื่นได้ — เริ่มตรงไหน
2. ทั้งชั้นเข้าเน็ตไม่ได้ — สงสัยอะไรก่อน
3. Divide-and-conquer เริ่มที่ layer ไหน เพราะอะไร
4. องค์ประกอบของ RCA ที่ดี
5. เข้าได้ด้วย IP แต่ไม่ได้ด้วยชื่อ — ขั้นตอนถัดไป

<details><summary>เฉลย</summary>

1. ที่ฝั่งผู้ใช้: IP/GW/DNS ของเครื่อง, สาย/Wi-Fi, proxy/browser
2. อุปกรณ์ที่ใช้ร่วมกัน: access/distribution switch, uplink, DHCP, VLAN, gateway
3. L3 (ping) — ผลบอกได้ว่าควรขึ้นหรือลง
4. Timeline, ผลกระทบ, root cause, การแก้ชั่วคราว/ถาวร, action items ป้องกันซ้ำ
5. ตรวจ DNS server ที่เครื่องใช้, nslookup/dig, hosts file, DNS suffix
</details>

**5 โปรเจค**
- ⭐ P1: Flowchart troubleshooting "เข้าเน็ตไม่ได้" สำหรับ helpdesk
- ⭐⭐ P2: ทำ "Break/Fix lab" 10 โจทย์ ใน Packet Tracer ให้เพื่อนแก้ (มีเฉลย)
- ⭐⭐ P3: เขียน RCA จากเหตุการณ์จริงที่เคยเจอ (หรือ outage สาธารณะ เช่น Facebook 2021 BGP)
- ⭐⭐ P4: ทำ Runbook template + ตัวอย่าง 5 อาการยอดฮิต
- ⭐⭐⭐ P5: สร้างเครื่องมือ "auto-diagnose" Python: ตรวจ NIC → IP → GW → DNS → HTTP แล้วบอกจุดที่เสีย
