# Tier 2 — Protocol หลัก (Level 11–20)

> เป้าหมายของ Tier: อธิบายได้ว่าเมื่อพิมพ์ URL แล้วเกิดอะไรขึ้นทุกขั้น (ARP → DHCP → DNS → TCP → TLS → HTTP)

---

## Level 11 — ARP

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L11-arp.md](lessons/L11-arp.md)

**สิ่งที่ต้องรู้**
- ARP แปลง IPv4 → MAC ภายใน broadcast domain เดียวกัน
- ARP Request (broadcast) / ARP Reply (unicast), ARP cache + timeout
- ถ้าปลายทางอยู่นอก subnet → ARP หา MAC ของ default gateway
- Gratuitous ARP (แจ้ง IP ซ้ำ, failover), Proxy ARP
- ARP spoofing/poisoning คืออะไร (ป้องกันด้วย DAI — Level 63)

```bash
ip neigh show          # Linux
arp -a                 # Windows/macOS
```

**แบบทดสอบ**
1. PC A (10.0.0.5/24) ส่งไป 8.8.8.8 จะ ARP หา MAC ของใคร
2. ARP request ส่งไปที่ MAC อะไร
3. Gratuitous ARP ใช้ในสถานการณ์ไหน
4. ทำไม ARP ไม่ข้าม router
5. IPv6 ใช้อะไรแทน ARP

<details><summary>เฉลย</summary>

1. MAC ของ default gateway
2. FF:FF:FF:FF:FF:FF
3. ตรวจ IP ซ้ำ, อัปเดต MAC หลัง failover (HSRP/VRRP, cluster)
4. เป็น broadcast L2 และ router ไม่ forward broadcast
5. NDP (Neighbor Solicitation/Advertisement, ICMPv6)
</details>

**5 โปรเจค**
- ⭐ P1: ล้าง ARP cache แล้ว ping จับด้วย Wireshark อธิบายลำดับ
- ⭐ P2: Packet Tracer simulation: ARP ภายใน subnet vs ข้าม subnet
- ⭐⭐ P3: Python + Scapy: ARP scanner หาเครื่องใน LAN ของตัวเอง (lab/บ้านตัวเองเท่านั้น)
- ⭐⭐ P4: สคริปต์ monitor ARP table แจ้งเตือนเมื่อ MAC ของ gateway เปลี่ยน (ตรวจ spoofing)
- ⭐⭐⭐ P5: Lab 3 VM: สาธิต ARP spoofing ด้วย arpspoof แล้วป้องกันด้วย static ARP / DAI — เขียนรายงาน

---

## Level 12 — ICMP, ping, traceroute

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L12-icmp-ping-traceroute.md](lessons/L12-icmp-ping-traceroute.md)

**สิ่งที่ต้องรู้**
- ICMP Type: 0 Echo Reply, 3 Destination Unreachable, 8 Echo Request, 11 Time Exceeded
- traceroute ใช้ TTL เพิ่มทีละ 1 (Linux ใช้ UDP, Windows tracert ใช้ ICMP)
- mtr = ping + traceroute ต่อเนื่อง
- Path MTU Discovery ใช้ ICMP Type 3 Code 4 (Fragmentation needed) — อย่า block ICMP ทั้งหมด!
- `* * *` ใน traceroute ไม่ได้แปลว่าเสียเสมอ (อาจแค่ rate-limit ICMP)

```bash
ping -c 5 8.8.8.8 ; traceroute 1.1.1.1 ; mtr -rwc 100 google.com
```

**แบบทดสอบ**
1. traceroute รู้ได้อย่างไรว่าแต่ละ hop คือใคร
2. "Request timed out" vs "Destination host unreachable" ต่างกันอย่างไร
3. ทำไมการ block ICMP ทั้งหมดที่ firewall เป็นเรื่องไม่ดี
4. hop กลางทางมี loss 50% แต่ปลายทาง 0% แปลว่าอะไร
5. ping ใช้ port อะไร

<details><summary>เฉลย</summary>

1. router ที่ TTL หมดส่ง ICMP Time Exceeded กลับมา
2. Timeout = ไม่มีตอบกลับ; Unreachable = มีอุปกรณ์ตอบว่าไปไม่ถึง (เช่น ไม่มี route/ARP ไม่ได้)
3. PMTUD พัง → เว็บบางเว็บค้าง (MTU black hole), troubleshoot ยาก
4. router นั้นแค่ rate-limit การตอบ ICMP ไม่ใช่ปัญหาจริง
5. ไม่มี — ICMP ไม่ใช้ port
</details>

**5 โปรเจค**
- ⭐ P1: traceroute ไป 5 ประเทศ ทำแผนที่เส้นทาง + latency
- ⭐ P2: ทำ ping monitoring ด้วย bash/cron บันทึกลง CSV แล้ววาดกราฟ
- ⭐⭐ P3: เขียน ping แบบ ICMP raw socket ด้วย Python
- ⭐⭐ P4: เขียน traceroute เองด้วย Scapy
- ⭐⭐⭐ P5: สร้าง dashboard "ISP health" ด้วย smokeping หรือ Python + Grafana

---

## Level 13 — TCP

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L13-tcp.md](lessons/L13-tcp.md)

**สิ่งที่ต้องรู้**
- Connection-oriented, reliable, ordered
- 3-way handshake SYN → SYN/ACK → ACK; 4-way close FIN/ACK; RST
- Sequence/Acknowledgment number, Window size, Sliding window
- Flow control vs Congestion control (Slow start, CUBIC, BBR)
- Retransmission, Duplicate ACK, Fast retransmit
- TCP states: LISTEN, SYN_SENT, ESTABLISHED, TIME_WAIT, CLOSE_WAIT
- MSS, Window scaling, Bandwidth-Delay Product

**แบบทดสอบ**
1. เรียงลำดับ 3-way handshake
2. CLOSE_WAIT จำนวนมากบน server บอกอะไร
3. ได้ RST ทันทีหลังส่ง SYN หมายความว่าอะไร
4. ลิงก์ 1 Gbps RTT 100 ms ต้องการ window ประมาณเท่าไร
5. Flow control กับ Congestion control ต่างกันอย่างไร

<details><summary>เฉลย</summary>

1. SYN, SYN-ACK, ACK
2. แอปไม่ยอม close socket (bug ในแอป)
3. port ปิด (ไม่มีโปรแกรม listen) หรือ firewall ส่ง reject
4. BDP = 1e9 × 0.1 / 8 = 12.5 MB
5. Flow = ป้องกันผู้รับล้น (rwnd); Congestion = ป้องกันเครือข่ายล้น (cwnd)
</details>

**5 โปรเจค**
- ⭐ P1: Wireshark: จับ handshake+close ของ HTTP แล้วอธิบาย seq/ack
- ⭐⭐ P2: Python TCP chat server รองรับหลาย client (threading/asyncio)
- ⭐⭐ P3: ใช้ `tc netem` ใส่ delay/loss แล้ววัด throughput ด้วย iperf3 ทำกราฟ
- ⭐⭐ P4: เปรียบเทียบ congestion control CUBIC vs BBR บน Linux
- ⭐⭐⭐ P5: เขียน port scanner แบบ TCP connect + SYN scan (Scapy) ใช้ใน lab ตัวเอง

---

## Level 14 — UDP & Port Numbers

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L14-udp-ports.md](lessons/L14-udp-ports.md)

**สิ่งที่ต้องรู้**
- UDP: connectionless, header 8 byte, ไม่มี retransmit — เหมาะ DNS, VoIP, game, streaming, QUIC
- Port: Well-known 0–1023, Registered 1024–49151, Ephemeral 49152–65535
- Port ที่ต้องจำ: 20/21 FTP, 22 SSH, 23 Telnet, 25 SMTP, 53 DNS, 67/68 DHCP, 69 TFTP, 80 HTTP, 110 POP3, 123 NTP, 143 IMAP, 161/162 SNMP, 389 LDAP, 443 HTTPS, 445 SMB, 514 Syslog, 636 LDAPS, 993/995, 1812/1813 RADIUS, 3306 MySQL, 3389 RDP, 5060 SIP
- Socket = IP + Protocol + Port; 5-tuple

**แบบทดสอบ**
1. ทำไม DNS ใช้ UDP เป็นหลัก แต่ก็ใช้ TCP ด้วย
2. RDP ใช้ port อะไร
3. 5-tuple ประกอบด้วยอะไร
4. QUIC/HTTP3 วิ่งบน TCP หรือ UDP
5. SNMP trap ใช้ port อะไร

<details><summary>เฉลย</summary>

1. UDP เร็ว overhead ต่ำ; TCP ใช้เมื่อ response ใหญ่ / zone transfer
2. 3389
3. Src IP, Dst IP, Src Port, Dst Port, Protocol
4. UDP (443)
5. 162
</details>

**5 โปรเจค**
- ⭐ P1: Flashcard port number 40 ตัว ทำจนได้ 100%
- ⭐ P2: `ss -tulpn` / `netstat -ano` ทำรายการ service ที่เปิดบนเครื่องตัวเอง + อธิบาย
- ⭐⭐ P3: Python UDP client/server ส่งไฟล์ พร้อมเพิ่ม seq + ack เอง (reliable UDP)
- ⭐⭐ P4: ทำ UDP syslog receiver ด้วย Python บันทึกลงไฟล์
- ⭐⭐⭐ P5: เปรียบเทียบ latency TCP vs UDP vs QUIC (aioquic) ภายใต้ packet loss

---

## Level 15 — DHCP

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L15-dhcp.md](lessons/L15-dhcp.md)

**สิ่งที่ต้องรู้**
- DORA: Discover → Offer → Request → Acknowledge (UDP 67/68)
- Lease, renewal (T1 50%, T2 87.5%), Reservation, Exclusion
- Options: 3 router, 6 DNS, 15 domain, 66/67 PXE, 43 AP controller
- DHCP Relay (`ip helper-address`) เมื่อ server อยู่คนละ subnet
- DHCP snooping (Level 63), Rogue DHCP
- DHCP failover/HA

```
ip dhcp excluded-address 192.168.10.1 192.168.10.10
ip dhcp pool LAN10
 network 192.168.10.0 255.255.255.0
 default-router 192.168.10.1
 dns-server 1.1.1.1
interface g0/1
 ip helper-address 10.0.0.10
```

**แบบทดสอบ**
1. DORA ข้อใดเป็น broadcast
2. ทำไมต้องมี DHCP relay
3. Option 43 ใช้ทำอะไร
4. ผู้ใช้ได้ IP วงแปลก ๆ 192.168.0.x ทั้งที่องค์กรใช้ 10.x สาเหตุที่เป็นไปได้
5. Reservation ต่างจาก static IP อย่างไร

<details><summary>เฉลย</summary>

1. Discover และ (โดยทั่วไป) Request; Offer/Ack อาจ broadcast หรือ unicast ตาม flag
2. Broadcast ข้าม router ไม่ได้ → relay แปลงเป็น unicast ไป server
3. บอก AP ว่า Wireless Controller อยู่ที่ไหน
4. Rogue DHCP (เช่น มีคนเสียบ router บ้าน)
5. Reservation ยังจัดการจากศูนย์กลาง ได้ option อื่นด้วย; static ตั้งที่เครื่อง
</details>

**5 โปรเจค**
- ⭐ P1: Packet Tracer: router เป็น DHCP server 2 VLAN
- ⭐⭐ P2: ติดตั้ง ISC Kea หรือ dnsmasq บน Linux แจก IP ให้ VM
- ⭐⭐ P3: Lab DHCP relay: server อยู่ subnet ต่างกัน
- ⭐⭐ P4: Python+Scapy: rogue DHCP detector (ส่ง Discover แล้วดูว่ามี offer จากกี่ server)
- ⭐⭐⭐ P5: Windows Server DHCP failover (load-balance mode) + เอกสาร runbook

---

## Level 16 — DNS

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L16-dns.md](lessons/L16-dns.md)

**สิ่งที่ต้องรู้**
- ลำดับ resolution: cache → hosts → resolver → root → TLD → authoritative
- Recursive vs Iterative, TTL, negative caching
- Records: A, AAAA, CNAME, MX, NS, TXT (SPF/DKIM/DMARC), PTR, SOA, SRV, CAA
- Forward/Reverse zone, Split-horizon DNS, Zone transfer (AXFR/IXFR)
- DoH/DoT, DNSSEC, Anycast DNS
- "It's always DNS" — สาเหตุยอดฮิตของ outage

```bash
dig example.com A +short ; dig +trace example.com ; dig -x 8.8.8.8 ; nslookup -type=mx gmail.com
```

**แบบทดสอบ**
1. CNAME ใส่ที่ zone apex (example.com) ได้หรือไม่ เพราะอะไร
2. PTR record ใช้ทำอะไร
3. ย้ายเว็บไป server ใหม่ ควรทำอะไรกับ TTL ก่อนวันย้าย
4. Split-horizon DNS คืออะไร
5. Record อะไรใช้ป้องกัน email spoofing

<details><summary>เฉลย</summary>

1. ไม่ได้ตามมาตรฐาน เพราะ apex ต้องมี SOA/NS (บางผู้ให้บริการมี ALIAS/ANAME แทน)
2. Reverse lookup IP → ชื่อ (สำคัญสำหรับ mail server)
3. ลด TTL ล่วงหน้า (เช่น 300 วินาที) อย่างน้อยเท่า TTL เดิม
4. ตอบคำตอบต่างกันตามผู้ถาม (ภายใน vs ภายนอก)
5. TXT: SPF, DKIM, DMARC
</details>

**5 โปรเจค**
- ⭐ P1: `dig +trace` 5 โดเมน อธิบายทุก step
- ⭐⭐ P2: ติดตั้ง BIND9 หรือ CoreDNS ทำ zone ภายใน `lab.local` + reverse zone
- ⭐⭐ P3: ตั้ง Pi-hole/AdGuard Home ในบ้าน วัดว่า block query ได้กี่ %
- ⭐⭐ P4: Python script ตรวจ SPF/DKIM/DMARC ของรายชื่อโดเมน ทำรายงาน
- ⭐⭐⭐ P5: ตั้ง DNS แบบ primary/secondary + DNSSEC signing + monitoring

---

## Level 17 — NAT / PAT

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L17-nat-pat.md](lessons/L17-nat-pat.md)

**สิ่งที่ต้องรู้**
- Static NAT (1:1), Dynamic NAT (pool), PAT/NAT Overload (many:1 ด้วย port)
- Inside local / Inside global / Outside local / Outside global
- Port forwarding (DNAT), Hairpin NAT/NAT reflection
- ปัญหา NAT กับ SIP, IPsec (NAT-T UDP 4500), P2P; CGNAT
- NAT ไม่ใช่ security (แต่ทำหน้าที่คล้าย stateful filter)

```
interface g0/0
 ip nat outside
interface g0/1
 ip nat inside
access-list 1 permit 192.168.0.0 0.0.255.255
ip nat inside source list 1 interface g0/0 overload
ip nat inside source static tcp 192.168.1.10 80 203.0.113.5 80
```

**แบบทดสอบ**
1. PAT แยก session ของแต่ละเครื่องได้อย่างไร
2. Inside global คืออะไร
3. Hairpin NAT แก้ปัญหาอะไร
4. ทำไม IPsec ต้องใช้ NAT-T
5. ผู้ใช้ CGNAT เปิด port forwarding ที่ router บ้านแล้วยังเข้าจากนอกไม่ได้ เพราะอะไร

<details><summary>เฉลย</summary>

1. แปลง source port ให้ไม่ซ้ำ เก็บใน translation table
2. IP สาธารณะที่แทนเครื่องภายในเมื่อมองจากข้างนอก
3. ผู้ใช้ภายในเข้าถึง server ภายในผ่าน public IP ได้
4. ESP ไม่มี port และ NAT แก้ header ทำให้ integrity พัง → ห่อ ESP ใน UDP 4500
5. ถูก NAT อีกชั้นที่ ISP; ไม่มี public IP จริง
</details>

**5 โปรเจค**
- ⭐ P1: Packet Tracer: PAT + static NAT สำหรับ web server
- ⭐⭐ P2: Linux เป็น NAT router ด้วย nftables masquerade ให้ VM ออกเน็ต
- ⭐⭐ P3: ตั้ง port forwarding ใน router บ้านเปิดเว็บส่วนตัว (หรืออธิบายทางเลือกเมื่อติด CGNAT: Cloudflare Tunnel/Tailscale)
- ⭐⭐ P4: Wireshark จับ packet ทั้งฝั่ง inside/outside ของ NAT เปรียบเทียบ header
- ⭐⭐⭐ P5: วัด PAT table capacity/timeout และเขียนบทความเรื่อง NAT exhaustion

---

## Level 18 — IPv6 พื้นฐาน

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L18-ipv6-basics.md](lessons/L18-ipv6-basics.md)

**สิ่งที่ต้องรู้**
- 128 bit, เขียนเป็น hex 8 กลุ่ม, การย่อ (ตัด 0 นำหน้า, `::` ได้ครั้งเดียว)
- ไม่มี broadcast; ใช้ multicast (ff02::1 all-nodes, ff02::2 all-routers)
- Header แบบ fixed 40 byte, extension headers, ไม่มี fragmentation ที่ router
- ประเภท: Global Unicast 2000::/3, Link-local fe80::/10, ULA fc00::/7, Loopback ::1, Multicast ff00::/8
- Dual-stack, Tunneling (6in4), Translation (NAT64/DNS64)

**แบบทดสอบ**
1. ย่อ 2001:0db8:0000:0000:0000:ff00:0042:8329
2. fe80::1 คือ address ประเภทใด
3. IPv6 ใช้อะไรแทน broadcast
4. ใน IPv6 ใครทำ fragmentation
5. NAT64 ใช้เมื่อไร

<details><summary>เฉลย</summary>

1. 2001:db8::ff00:42:8329
2. Link-local
3. Multicast
4. ต้นทางเท่านั้น (ผ่าน PMTUD)
5. เครือข่าย IPv6-only ต้องการเข้าถึงเว็บ IPv4
</details>

**5 โปรเจค**
- ⭐ P1: ตรวจว่า ISP บ้านให้ IPv6 หรือไม่ (test-ipv6.com) + ดู address บนเครื่อง
- ⭐ P2: ฝึกย่อ/ขยาย IPv6 50 ข้อ
- ⭐⭐ P3: Packet Tracer: IPv6 static routing 3 router
- ⭐⭐ P4: Python: ฟังก์ชันย่อ/ขยาย IPv6 เอง + test เทียบกับ `ipaddress`
- ⭐⭐⭐ P5: Lab dual-stack + NAT64/DNS64 ด้วย Jool/Tayga บน Linux

---

## Level 19 — IPv6 Addressing: SLAAC, DHCPv6, NDP

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L19-ipv6-slaac-ndp.md](lessons/L19-ipv6-slaac-ndp.md)

**สิ่งที่ต้องรู้**
- NDP: RS/RA/NS/NA/Redirect (ICMPv6 133–137)
- SLAAC: prefix จาก RA + interface ID (EUI-64 หรือ random/privacy)
- Stateless DHCPv6 (ให้ DNS) vs Stateful DHCPv6; flag M/O ใน RA
- DAD (Duplicate Address Detection)
- Subnet มาตรฐาน /64, site ได้ /48 หรือ /56, prefix delegation (DHCPv6-PD)
- Solicited-node multicast ff02::1:ffXX:XXXX

**แบบทดสอบ**
1. ทำ EUI-64 จาก MAC 00:1A:2B:3C:4D:5E
2. RA flag M=1 หมายความว่าอะไร
3. ทำไม LAN IPv6 ควรเป็น /64
4. องค์กรได้ /48 แบ่ง /64 ได้กี่ subnet
5. Android รองรับ stateful DHCPv6 หรือไม่ มีผลต่อการออกแบบอย่างไร

<details><summary>เฉลย</summary>

1. 021A:2BFF:FE3C:4D5E (กลับบิต U/L, แทรก FFFE)
2. ให้ใช้ stateful DHCPv6 รับ address
3. SLAAC ต้องการ interface ID 64 บิต
4. 2^16 = 65,536
5. ไม่รองรับ → ต้องเปิด SLAAC ใน LAN ที่มีมือถือ Android
</details>

**5 โปรเจค**
- ⭐⭐ P1: Packet Tracer/GNS3: SLAAC + stateless DHCPv6
- ⭐⭐ P2: Linux radvd แจก RA ให้ VM, จับ RS/RA ด้วย Wireshark
- ⭐⭐ P3: ทำ IPv6 address plan ขององค์กร /48 (ตามตึก/ชั้น/VLAN) แบบอ่านง่าย
- ⭐⭐ P4: Python EUI-64 generator + solicited-node multicast calculator
- ⭐⭐⭐ P5: ทดสอบ RA Guard: ปล่อย rogue RA ใน lab แล้วป้องกัน

---

## Level 20 — HTTP, HTTPS & TLS พื้นฐาน

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L20-http-https-tls.md](lessons/L20-http-https-tls.md)

**สิ่งที่ต้องรู้**
- HTTP method (GET/POST/PUT/DELETE), status code (2xx/3xx/4xx/5xx), headers, cookies
- HTTP/1.1 keep-alive, HTTP/2 multiplexing, HTTP/3 บน QUIC
- TLS 1.2 vs 1.3 handshake, SNI, cipher suite, certificate chain
- "พิมพ์ URL แล้วเกิดอะไรขึ้น" — คำถามสัมภาษณ์คลาสสิก
- Browser DevTools Network tab

```bash
curl -v https://example.com ; curl -I -L http://example.com
openssl s_client -connect example.com:443 -servername example.com
```

**แบบทดสอบ**
1. 502 vs 504 ต่างกันอย่างไร
2. SNI ใช้ทำอะไร
3. TLS 1.3 handshake กี่ RTT
4. 301 vs 302
5. อธิบายสิ่งที่เกิดเมื่อพิมพ์ https://www.example.com จนเห็นหน้าเว็บ (สั้น ๆ)

<details><summary>เฉลย</summary>

1. 502 Bad Gateway = upstream ตอบผิด/ปฏิเสธ; 504 = upstream ตอบไม่ทัน (timeout)
2. บอกชื่อโดเมนตอน TLS handshake ให้ server เลือก cert ถูก (หลายเว็บบน IP เดียว)
3. 1-RTT (0-RTT เมื่อ resume)
4. 301 ถาวร, 302 ชั่วคราว
5. DNS resolve → ARP gateway → TCP handshake → TLS handshake (SNI, cert verify) → HTTP GET → response → render + โหลด resource อื่น
</details>

**5 โปรเจค**
- ⭐ P1: เขียนเอกสาร "พิมพ์ URL แล้วเกิดอะไรขึ้น" พร้อมภาพ packet capture ทุกขั้น
- ⭐⭐ P2: เขียน HTTP server ด้วย socket ดิบ (ไม่ใช้ framework)
- ⭐⭐ P3: ใช้ SSLKEYLOGFILE ถอดรหัส TLS ใน Wireshark แล้วดู HTTP/2 frame
- ⭐⭐ P4: สคริปต์ตรวจวันหมดอายุ cert ของรายชื่อโดเมน แจ้งเตือนผ่าน LINE/Discord
- ⭐⭐⭐ P5: ทำ benchmark HTTP/1.1 vs HTTP/2 vs HTTP/3 บนเว็บที่มี asset 100 ไฟล์
