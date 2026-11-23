# Tier 1 — พื้นฐานเครือข่าย (Level 1–10)

> เป้าหมายของ Tier: เข้าใจว่าข้อมูลเดินทางอย่างไร อ่าน IP/Subnet ได้คล่อง และรู้จักอุปกรณ์/สายทุกชนิดที่จะเจอในที่ทำงาน

---

## Level 1 — Network คืออะไร & ประเภทเครือข่าย

**เป้าหมาย:** อธิบายได้ว่าเครือข่ายคืออะไร แยกประเภทและ Topology ได้

**สิ่งที่ต้องรู้**
- Network = อุปกรณ์ตั้งแต่ 2 ตัวขึ้นไปเชื่อมกันเพื่อแชร์ข้อมูล/ทรัพยากร
- ประเภทตามขนาด: PAN, LAN, MAN, WAN, (WLAN, SAN, Campus)
- Topology: Bus, Star, Ring, Mesh (Full/Partial), Hybrid, Spine-Leaf (DC สมัยใหม่)
- Physical topology ≠ Logical topology
- Client-Server vs Peer-to-Peer
- หน่วย: bit vs Byte, bps/Kbps/Mbps/Gbps, Bandwidth vs Throughput vs Latency vs Jitter

**แบบทดสอบ**
1. LAN กับ WAN ต่างกันอย่างไร (ยกตัวอย่างในบริษัท)
2. ลิงก์ 100 Mbps ดาวน์โหลดไฟล์ 1 GB ใช้เวลาอย่างน้อยกี่วินาที
3. Topology ไหนทนทานต่อลิงก์ขาดมากที่สุด และข้อเสียคืออะไร
4. Bandwidth กับ Throughput ต่างกันอย่างไร
5. Latency กับ Jitter ต่างกันอย่างไร และกระทบงานแบบไหน

<details><summary>เฉลย</summary>

1. LAN = พื้นที่จำกัด ความเร็วสูง องค์กรเป็นเจ้าของ (เช่น เครือข่ายในชั้นสำนักงาน); WAN = เชื่อมระยะไกล มักเช่าจาก ISP (เช่น เชื่อมสำนักงานใหญ่กับสาขา)
2. 1 GB = 8,000 Mb → 8000/100 = 80 วินาที (ยังไม่รวม overhead)
3. Full Mesh — ข้อเสียคือใช้สาย/พอร์ตมาก n(n-1)/2 ลิงก์ ต้นทุนสูง
4. Bandwidth = ความจุสูงสุดทางทฤษฎี; Throughput = ที่ได้จริง
5. Latency = เวลาหน่วง; Jitter = ความแปรปรวนของ latency — กระทบ VoIP/วิดีโอคอลมาก
</details>

**5 โปรเจค**
- ⭐ P1: วาดแผนผังเครือข่ายบ้าน/หอพักของตัวเอง (draw.io) ระบุอุปกรณ์ทั้งหมด
- ⭐ P2: ตารางเปรียบเทียบ Topology 6 แบบ: ข้อดี/ข้อเสีย/ต้นทุน/ตัวอย่างใช้งานจริง
- ⭐ P3: วัด Bandwidth/Latency/Jitter ด้วย speedtest + ping 100 ครั้ง ในเวลาต่าง ๆ แล้วทำกราฟ
- ⭐⭐ P4: สัมภาษณ์/ค้นคว้าเครือข่ายของมหาวิทยาลัย แล้วจำแนกส่วน LAN/WAN/Campus
- ⭐⭐ P5: เขียนสคริปต์ Python คำนวณเวลาโอนไฟล์จากขนาดไฟล์ + bandwidth + overhead %

---

## Level 2 — OSI Model 7 Layers

**เป้าหมาย:** จำและอธิบาย 7 ชั้นได้ พร้อมตัวอย่าง Protocol/อุปกรณ์ในแต่ละชั้น

**สิ่งที่ต้องรู้**
- L7 Application (HTTP, DNS) · L6 Presentation (TLS, encoding) · L5 Session · L4 Transport (TCP/UDP) · L3 Network (IP, router) · L2 Data Link (Ethernet, MAC, switch) · L1 Physical (สาย, สัญญาณ, hub)
- PDU: Data → Segment/Datagram → Packet → Frame → Bits
- Encapsulation / De-encapsulation
- ใช้ OSI เป็น "ภาษากลาง" ในการ troubleshoot: "ปัญหาอยู่ที่ Layer ไหน"

**แบบทดสอบ**
1. Switch ทั่วไปทำงานที่ Layer ไหน Router ล่ะ
2. PDU ของ Layer 4 (TCP) เรียกว่าอะไร
3. ถ้า ping IP ได้ แต่เปิดเว็บด้วยชื่อไม่ได้ น่าจะเป็นปัญหาที่ layer/บริการอะไร
4. สายหลวม ไฟพอร์ตไม่ติด คือปัญหา Layer ไหน
5. อธิบาย Encapsulation ตอนส่ง HTTP request

<details><summary>เฉลย</summary>

1. Switch = L2, Router = L3
2. Segment (UDP = Datagram)
3. L7 — DNS
4. L1 Physical
5. HTTP data → ใส่ TCP header (port) → ใส่ IP header (src/dst IP) → ใส่ Ethernet header+trailer (MAC, FCS) → แปลงเป็นบิตส่งบนสาย
</details>

**5 โปรเจค**
- ⭐ P1: ทำ Infographic OSI 7 layers + protocol + อุปกรณ์ + PDU
- ⭐ P2: จับ packet การเปิดเว็บ 1 ครั้งใน Wireshark แล้วชี้ header ของแต่ละ layer
- ⭐⭐ P3: เขียน "Troubleshooting checklist ตาม OSI" (bottom-up) สำหรับ helpdesk
- ⭐⭐ P4: ทำ Flashcard/Quiz เว็บง่าย ๆ (HTML/JS) สุ่มถามว่า protocol อยู่ layer ไหน
- ⭐⭐ P5: เขียนบทความเปรียบเทียบ OSI กับการส่งพัสดุไปรษณีย์ (อธิบายให้คนไม่ใช่สาย IT เข้าใจ)

---

## Level 3 — TCP/IP Model

**เป้าหมาย:** เข้าใจโมเดลที่ใช้จริงบนอินเทอร์เน็ตและ map กับ OSI

**สิ่งที่ต้องรู้**
- 4 ชั้น: Application, Transport, Internet, Network Access (บางตำรา 5 ชั้น แยก Data Link/Physical)
- OSI L5–L7 → Application; L3 → Internet; L1–L2 → Network Access
- RFC คืออะไร, IETF/IEEE/IANA มีหน้าที่อะไร
- Protocol suite: IP, ICMP, ARP, TCP, UDP, DNS, DHCP, HTTP

**แบบทดสอบ**
1. TCP/IP model มีกี่ชั้น อะไรบ้าง
2. ICMP อยู่ชั้นไหนของ TCP/IP
3. องค์กรไหนดูแลมาตรฐาน Ethernet (802.3)
4. ใครแจก IP block และ port number ระดับโลก
5. ทำไมในงานจริงคนยังพูดว่า "L2/L3/L7" ตาม OSI

<details><summary>เฉลย</summary>

1. 4 ชั้น: Application, Transport, Internet, Network Access
2. Internet layer
3. IEEE
4. IANA (ผ่าน RIR เช่น APNIC)
5. OSI ละเอียดกว่า ใช้เป็นภาษาสื่อสาร/troubleshoot ได้ชัดเจน
</details>

**5 โปรเจค**
- ⭐ P1: แผนภาพเทียบ OSI vs TCP/IP พร้อม protocol
- ⭐ P2: อ่าน RFC 791 (IPv4) สรุป header ทุก field เป็นภาษาไทย
- ⭐⭐ P3: ใช้ Python `socket` เขียน client-server echo แล้วอธิบายว่าโค้ดแต่ละบรรทัดอยู่ชั้นไหน
- ⭐⭐ P4: สืบค้น ASN และ IP block ของมหาวิทยาลัย/ISP ผ่าน APNIC whois แล้วทำรายงาน
- ⭐⭐ P5: ใช้ Scapy สร้าง packet ทีละชั้น `Ether()/IP()/TCP()/Raw()` แล้ว `show()` อธิบายผล

---

## Level 4 — สาย สื่อนำสัญญาณ และ Physical Layer

**เป้าหมาย:** เลือกสาย/หัว/ไฟเบอร์ได้ถูกงาน เข้าหัวสาย LAN เองได้

**สิ่งที่ต้องรู้**
- UTP/STP, Cat5e (1G), Cat6 (1G/10G ≤55m), Cat6A (10G 100m), Cat8 (25/40G 30m)
- มาตรฐานสี T568A / T568B, สายตรง vs สายไขว้, Auto-MDIX
- Fiber: Single-mode (ไกล, 9µm, laser) vs Multi-mode (OM3/OM4, ใกล้)
- หัวต่อ: RJ45, LC, SC; โมดูล SFP, SFP+, QSFP28
- ระยะ 100 m ของ copper Ethernet, PoE/PoE+/PoE++ (802.3af/at/bt)
- Wireless เป็นสื่อแบบไม่ใช้สาย, ปัญหา EMI/crosstalk

**แบบทดสอบ**
1. สาย Cat6 วิ่ง 10Gbps ได้ไกลสุดประมาณเท่าไร
2. ลิงก์ระหว่างตึกห่าง 5 km ใช้สายอะไร
3. เรียงสี T568B
4. PoE+ (802.3at) จ่ายไฟได้ประมาณกี่วัตต์ต่อพอร์ต
5. Auto-MDIX ช่วยอะไร

<details><summary>เฉลย</summary>

1. ~55 m
2. Single-mode fiber + SFP แบบ LR
3. ขาวส้ม, ส้ม, ขาวเขียว, น้ำเงิน, ขาวน้ำเงิน, เขียว, ขาวน้ำตาล, น้ำตาล
4. ~30 W (ที่ PSE), af ~15.4 W, bt สูงสุด ~90 W
5. ปรับคู่สายส่ง/รับอัตโนมัติ ใช้สายตรงหรือไขว้ก็ได้
</details>

**5 โปรเจค**
- ⭐ P1: เข้าหัว RJ45 T568B 5 เส้น ทดสอบด้วย cable tester บันทึกผล
- ⭐ P2: ทำ BOM (Bill of Materials) เดินสายสำนักงาน 30 จุด พร้อมราคา
- ⭐⭐ P3: ออกแบบ Structured Cabling (patch panel, rack, labeling) ของชั้นสำนักงาน
- ⭐⭐ P4: ตารางเลือก SFP (SR/LR/ER, MM/SM, ระยะ, ราคา) สำหรับ 3 สถานการณ์
- ⭐⭐ P5: คำนวณ PoE Budget ของสวิตช์ 24 พอร์ต ที่ต่อ AP 8 ตัว + IP Camera 12 ตัว

---

## Level 5 — อุปกรณ์เครือข่าย

**เป้าหมาย:** รู้หน้าที่และตำแหน่งการวางอุปกรณ์แต่ละชนิด

**สิ่งที่ต้องรู้**
- Hub (L1, broadcast ทุกพอร์ต), Bridge, Switch (L2), L3 Switch, Router (L3)
- Access Point, Wireless LAN Controller
- Firewall / NGFW, IDS/IPS, Load Balancer, Proxy
- Modem/ONT, Media converter
- Collision domain vs Broadcast domain
- Hierarchical design: Core – Distribution – Access

**แบบทดสอบ**
1. Switch 24 พอร์ต (VLAN เดียว) มีกี่ collision domain และกี่ broadcast domain
2. Router 3 interface มีกี่ broadcast domain
3. ทำไมไม่ใช้ Hub แล้ว
4. ONT คืออะไร พบในบ้านแบบไหน
5. Firewall ควรวางอยู่ตรงไหนของเครือข่ายองค์กร

<details><summary>เฉลย</summary>

1. 24 collision domain, 1 broadcast domain
2. 3
3. Half-duplex, collision มาก, ความปลอดภัยต่ำ (ทุกคนเห็นทุก frame)
4. Optical Network Terminal แปลงไฟเบอร์ FTTH เป็น Ethernet
5. ขอบเครือข่ายระหว่าง Internet/WAN กับ LAN และระหว่าง zone (เช่น DMZ)
</details>

**5 โปรเจค**
- ⭐ P1: สำรวจห้อง server/rack ในที่จริง (หรือรูปจากเน็ต) ระบุอุปกรณ์ทุกชิ้น
- ⭐ P2: Packet Tracer: เทียบ Hub vs Switch ด้วย simulation mode
- ⭐⭐ P3: นับ collision/broadcast domain จากแผนผัง 5 แบบ (ทำโจทย์ + เฉลย)
- ⭐⭐ P4: ออกแบบเครือข่าย 3-tier สำหรับบริษัท 200 คน พร้อมเลือกรุ่นอุปกรณ์
- ⭐⭐ P5: เปรียบเทียบอุปกรณ์ 3 ยี่ห้อ (Cisco/Aruba/MikroTik/Ubiquiti) ด้านฟีเจอร์และราคา

---

## Level 6 — เลขฐาน 2 / 16 สำหรับงานเน็ตเวิร์ก

**เป้าหมาย:** แปลงเลขฐานในหัวได้เร็ว (พื้นฐานของ subnetting และ IPv6/MAC)

**สิ่งที่ต้องรู้**
- ค่าบิตใน 1 octet: 128 64 32 16 8 4 2 1
- Decimal ↔ Binary ↔ Hex, 1 hex digit = 4 bit (nibble)
- AND operation (หา network address)
- ค่าที่ต้องจำ: 0,128,192,224,240,248,252,254,255

**แบบทดสอบ**
1. 172 เป็นฐาน 2
2. 11110000 เป็นฐาน 10
3. 0xAC เป็นฐาน 10
4. 192.168.10.77 AND 255.255.255.224 = ?
5. 255.255.255.248 มีบิต 1 กี่บิต

<details><summary>เฉลย</summary>

1. 10101100
2. 240
3. 172
4. 77 = 01001101, AND 11100000 = 01000000 = 64 → 192.168.10.64
5. 29 บิต (/29)
</details>

**5 โปรเจค**
- ⭐ P1: ฝึกแปลงเลข 50 ข้อจับเวลา ให้ได้ < 10 วินาทีต่อข้อ
- ⭐ P2: เขียน Python แปลง dec/bin/hex แบบ CLI
- ⭐⭐ P3: ทำเกม quiz binary บนเว็บ (HTML/JS) พร้อมคะแนน
- ⭐⭐ P4: เขียนฟังก์ชัน AND IP กับ mask เอง (ห้ามใช้ `ipaddress`) + unit test
- ⭐⭐ P5: ทำ cheat sheet สำหรับพิมพ์ติดโต๊ะ (ตาราง power of 2, ค่าของ mask)

---

## Level 7 — MAC Address & Ethernet Frame

**เป้าหมาย:** อ่าน Ethernet frame ได้ และเข้าใจ MAC

**สิ่งที่ต้องรู้**
- MAC 48 bit = OUI (24 bit ผู้ผลิต) + NIC specific
- Unicast / Multicast (bit แรกของ byte แรก = 1) / Broadcast FF:FF:FF:FF:FF:FF
- Ethernet II frame: Preamble, Dst MAC, Src MAC, EtherType (0x0800 IPv4, 0x86DD IPv6, 0x0806 ARP, 0x8100 VLAN), Payload 46–1500, FCS
- MTU 1500, Jumbo frame 9000
- Duplex (half/full), speed negotiation, duplex mismatch
- MAC randomization ในมือถือ

**แบบทดสอบ**
1. EtherType 0x0806 คืออะไร
2. MAC 01:00:5E:xx:xx:xx เป็น unicast หรือ multicast
3. FCS ใช้ทำอะไร
4. อาการของ duplex mismatch
5. ทำไม Wi-Fi องค์กรอาจมีปัญหากับ MAC randomization

<details><summary>เฉลย</summary>

1. ARP
2. Multicast (IPv4 multicast mapping)
3. ตรวจ error ด้วย CRC
4. ช้ามาก, late collision, CRC error เพิ่มขึ้น
5. ระบบที่ผูก policy/ลงทะเบียนตาม MAC จะจำอุปกรณ์ไม่ได้
</details>

**5 โปรเจค**
- ⭐ P1: ดู MAC ของทุกอุปกรณ์ในบ้าน แล้ว lookup ผู้ผลิตจาก OUI
- ⭐ P2: Wireshark จับ frame 10 ตัว อธิบายทุก field
- ⭐⭐ P3: Python script lookup OUI จากไฟล์ IEEE (oui.txt)
- ⭐⭐ P4: ทดลองเปลี่ยน MTU บน Linux และ ping ด้วย DF bit (`ping -M do -s 1472`)
- ⭐⭐⭐ P5: Scapy สร้าง Ethernet frame เอง ส่งใน lab แล้วจับดูผล

---

## Level 8 — IPv4 Addressing

**เป้าหมาย:** แยกประเภท IP และใช้ IP ได้ถูกต้อง

**สิ่งที่ต้องรู้**
- 32 bit, network portion + host portion, subnet mask/prefix
- Classful (A/B/C/D/E) — รู้ไว้เป็นประวัติ
- Private (RFC1918): 10/8, 172.16/12, 192.168/16
- Special: 127/8 loopback, 169.254/16 APIPA, 100.64/10 CGNAT, 0.0.0.0, 255.255.255.255
- Network address, Broadcast address, Usable host, Default gateway
- Unicast / Broadcast / Multicast (224/4)

**แบบทดสอบ**
1. 172.31.5.5 เป็น private หรือไม่
2. เครื่องได้ IP 169.254.x.x หมายถึงอะไร
3. 192.168.1.0/24 มี host ใช้ได้กี่ตัว
4. 100.64.0.0/10 ใช้ทำอะไร
5. ทำไมเครื่องต้องมี default gateway

<details><summary>เฉลย</summary>

1. ใช่ (อยู่ใน 172.16.0.0–172.31.255.255)
2. ติดต่อ DHCP ไม่ได้ จึงตั้ง APIPA เอง
3. 254
4. Carrier-grade NAT (ISP)
5. เพื่อส่ง packet ไปยังเครือข่ายอื่นนอก subnet ตัวเอง
</details>

**5 โปรเจค**
- ⭐ P1: ทำ IP plan ของบ้าน (static สำหรับ printer/NAS, DHCP สำหรับที่เหลือ)
- ⭐ P2: Packet Tracer: 2 PC + switch ตั้ง IP ให้ ping กันได้ แล้วลองตั้งผิด subnet
- ⭐⭐ P3: Python ใช้ `ipaddress` ตรวจว่า IP เป็น private/loopback/multicast/reserved
- ⭐⭐ P4: เขียนรายงาน "ทำไม IPv4 หมด" + NAT/CGNAT ช่วยอย่างไร
- ⭐⭐ P5: สร้าง spreadsheet IPAM ง่าย ๆ (subnet, VLAN, gateway, ผู้ใช้, สถานะ)

---

## Level 9 — Subnetting

**เป้าหมาย:** Subnet ในหัวได้ภายใน 30 วินาที (ทักษะสัมภาษณ์งานอันดับ 1)

**สิ่งที่ต้องรู้**
- จำนวน subnet = 2^(บิตที่ยืม), host ต่อ subnet = 2^(บิต host) − 2
- Block size (magic number) = 256 − ค่า mask ใน octet ที่สนใจ
- หา Network / First / Last / Broadcast
- /31 สำหรับ point-to-point (RFC 3021), /32 host route
- ตาราง: /24=256, /25=128, /26=64, /27=32, /28=16, /29=8, /30=4

**แบบทดสอบ**
1. 10.1.1.130/26 → network, broadcast, ช่วง host
2. ต้องการ 6 subnet จาก 192.168.5.0/24 ใช้ prefix อะไร มี host ได้ subnet ละเท่าไร
3. ต้องการ 500 host ต่อ subnet ใช้ prefix อะไร
4. 172.16.45.200/20 อยู่ network ไหน
5. 192.168.1.64/27 กับ 192.168.1.90 อยู่ subnet เดียวกันไหม

<details><summary>เฉลย</summary>

1. Block 64 → network 10.1.1.128, broadcast .191, host .129–.190
2. ยืม 3 บิต → /27 (8 subnet), 30 host
3. /23 (510 host)
4. Block 16 ใน octet ที่ 3 → 172.16.32.0/20 (32–47)
5. ใช่ (.64–.95)
</details>

**5 โปรเจค**
- ⭐ P1: ทำโจทย์ subnetting 100 ข้อ (subnettingpractice.com) บันทึกเวลา/ความแม่น
- ⭐⭐ P2: เขียน Subnet Calculator CLI ด้วย Python (ไม่ใช้ lib) + test
- ⭐⭐ P3: ทำ Subnet Calculator เป็นเว็บ (HTML/JS) แสดงผลแบบ binary
- ⭐⭐ P4: Packet Tracer: แบ่ง /24 เป็น 4 subnet ให้ 4 แผนก มี router เชื่อม ping ข้ามได้
- ⭐⭐⭐ P5: สร้างเครื่องสุ่มโจทย์ subnetting + ตรวจคำตอบอัตโนมัติ

---

## Level 10 — VLSM, CIDR & Route Summarization

**เป้าหมาย:** วางแผน IP ให้ประหยัด และสรุป route ได้

**สิ่งที่ต้องรู้**
- VLSM: เรียงความต้องการจากมากไปน้อย แล้วจัดสรรทีละก้อน
- CIDR notation, Supernetting / Summarization: หา common bits
- ข้อดีของ summarization: routing table เล็ก, ลด flap propagation
- ระวัง summarization ครอบ subnet ที่ไม่มีอยู่จริง (blackhole)

**แบบทดสอบ**
1. จาก 192.168.10.0/24 ต้องการ subnet 100, 50, 20, 2, 2 host จัด VLSM อย่างไร
2. Summarize 10.1.0.0/24 – 10.1.3.0/24
3. Summarize 172.16.8.0/24 ถึง 172.16.15.0/24
4. ลิงก์ point-to-point ใช้ /30 หรือ /31 ดี ต่างกันอย่างไร
5. ข้อเสียของ summary route ที่กว้างเกินไป

<details><summary>เฉลย</summary>

1. 100→.0/25, 50→.128/26, 20→.192/27, 2→.224/30, 2→.228/30
2. 10.1.0.0/22
3. 172.16.8.0/21
4. /31 ประหยัด IP (2 ตัวใช้ได้ทั้งคู่) ต้องรองรับ RFC 3021; /30 เสีย 2 ตัว แต่รองรับทุกที่
5. ดึง traffic ไปหา subnet ที่ไม่มีจริง → blackhole/routing loop ถ้าไม่มี null route
</details>

**5 โปรเจค**
- ⭐⭐ P1: ทำ IP plan VLSM สำหรับบริษัท 5 แผนก + 3 WAN link (เอกสาร + ตาราง)
- ⭐⭐ P2: Packet Tracer: implement IP plan จาก P1 ด้วย static route
- ⭐⭐ P3: Python: ใส่รายการความต้องการ host → พิมพ์แผน VLSM อัตโนมัติ
- ⭐⭐⭐ P4: Python: รับรายการ prefix → สรุป route ให้น้อยที่สุด (`collapse_addresses`) และอธิบาย
- ⭐⭐⭐ P5: ออกแบบ IP plan องค์กร 3 สาขา (HQ /16) ที่ summarization ได้ทุกสาขา
