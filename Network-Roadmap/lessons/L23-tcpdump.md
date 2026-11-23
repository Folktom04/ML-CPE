# บทเรียน Level 23 — tcpdump & CLI Capture (ฉบับละเอียด)

> อ่านจบแล้วจะ: จับ packet บน server ที่ไม่มี GUI ได้ · เขียน BPF filter · เก็บเป็นไฟล์/ring buffer แล้วนำไปเปิดใน Wireshark · ใช้ tshark ดึงข้อมูลเป็นตาราง · จับ packet บน firewall/router

---

## 1. tcpdump คืออะไร ใช้เมื่อไร

**tcpdump** คือเครื่องมือจับ packet แบบ command line มีใน Linux/macOS เกือบทุกเครื่อง (และบนอุปกรณ์หลายยี่ห้อที่ใช้ Linux อยู่ข้างใน)

**ใช้เมื่อ:** server/VM/container ไม่มีหน้าจอ, ต้องจับระยะยาว, ต้องการเบาและเร็ว แล้วค่อย **ส่งไฟล์ .pcap กลับมาเปิดใน Wireshark** บนเครื่องเรา

> ต้องใช้สิทธิ์ root (`sudo`) เพราะเข้าถึง interface โดยตรง

---

## 2. คำสั่งพื้นฐาน

```bash
sudo tcpdump -D                         # แสดงรายชื่อ interface
sudo tcpdump -i eth0                    # จับบน eth0 แสดงบนจอ
sudo tcpdump -i any                     # ทุก interface
sudo tcpdump -i eth0 -nn                # ไม่แปลง IP/port เป็นชื่อ (แนะนำเสมอ)
sudo tcpdump -i eth0 -c 100             # จับ 100 packet แล้วหยุด
sudo tcpdump -i eth0 -w cap.pcap        # บันทึกเป็นไฟล์ (ไม่แสดงบนจอ)
tcpdump -r cap.pcap -nn                 # อ่านไฟล์
sudo tcpdump -i eth0 -s 128             # เก็บแค่ 128 ไบต์แรกของแต่ละ packet (header) ไฟล์เล็ก
```

### Option ที่ใช้บ่อย
| Option | ความหมาย |
|---|---|
| `-i` | interface |
| `-n` / `-nn` | ไม่แปลง IP / ไม่แปลงทั้ง IP และ port |
| `-c N` | จับ N packet |
| `-w file` / `-r file` | เขียน / อ่าน pcap |
| `-s N` | snaplen (ขนาดที่เก็บต่อ packet; 0 = ทั้งหมด) |
| `-v` `-vv` | รายละเอียดมากขึ้น |
| `-e` | แสดง MAC (header L2) |
| `-A` | แสดงเนื้อหาเป็น ASCII (ดู HTTP ที่ไม่เข้ารหัส) |
| `-X` | แสดง hex + ASCII |
| `-tttt` | แสดงวันเวลาเต็ม |
| `-C size -W count` | ring buffer (ไฟล์ละ size MB หมุนเวียน count ไฟล์) |
| `-G sec` | สร้างไฟล์ใหม่ทุก N วินาที (ใช้ร่วมกับชื่อไฟล์แบบมีเวลา) |

---

## 3. BPF Filter (Berkeley Packet Filter)

ใส่ไว้ **ท้ายคำสั่ง** (แนะนำให้ครอบด้วย `'...'`)

| ประเภท | ตัวอย่าง |
|---|---|
| Host | `host 10.0.0.5` · `src host 10.0.0.5` · `dst host 8.8.8.8` |
| Network | `net 192.168.1.0/24` |
| Port | `port 53` · `dst port 443` · `portrange 8000-8100` |
| Protocol | `tcp` · `udp` · `icmp` · `arp` · `ip6` · `icmp6` |
| VLAN | `vlan 10` |
| รวม | `and` / `&&` · `or` / `\|\|` · `not` / `!` · วงเล็บ `( )` |

```bash
sudo tcpdump -i eth0 -nn 'host 10.0.0.5 and port 443'
sudo tcpdump -i eth0 -nn 'port 53'                          # DNS
sudo tcpdump -i eth0 -nn 'port 67 or port 68'               # DHCP
sudo tcpdump -i eth0 -nn 'icmp or arp'
sudo tcpdump -i eth0 -nn 'not port 22'                      # ตัด SSH ที่ตัวเองใช้อยู่ออก (สำคัญ!)
sudo tcpdump -i eth0 -nn 'tcp[tcpflags] & (tcp-syn|tcp-rst) != 0'   # เฉพาะ SYN/RST
sudo tcpdump -i eth0 -nn 'host 10.0.0.5 and (port 80 or port 443)'
```

> ⚠️ ถ้า SSH เข้า server แล้วจับโดยไม่ตัด port 22 จะเห็น packet ของ SSH ตัวเองท่วมจอ (และยิ่งแสดงยิ่งเกิด packet เพิ่ม)

---

## 4. อ่านผล tcpdump

```
08:15:01.123456 IP 10.0.0.15.51544 > 93.184.216.34.443: Flags [S], seq 12345, win 64240, options [mss 1460,...], length 0
08:15:01.140001 IP 93.184.216.34.443 > 10.0.0.15.51544: Flags [S.], seq 98765, ack 12346, win 65535, length 0
08:15:01.140100 IP 10.0.0.15.51544 > 93.184.216.34.443: Flags [.], ack 1, win 502, length 0
```
| ส่วน | ความหมาย |
|---|---|
| `08:15:01.123456` | เวลา |
| `10.0.0.15.51544 > 93.184.216.34.443` | ต้นทาง.port > ปลายทาง.port |
| **Flags** | `[S]` SYN · `[S.]` SYN-ACK · `[.]` ACK · `[P.]` PUSH+ACK (มีข้อมูล) · `[F.]` FIN · `[R]` RST |
| `length` | ขนาดข้อมูล (payload) |

จากตัวอย่าง: เวลาระหว่าง SYN กับ SYN-ACK ≈ 17 ms = RTT ไปยัง server

---

## 5. จับระยะยาวด้วย Ring Buffer

ปัญหาที่เกิดไม่บ่อย (เช่น วันละครั้ง) ต้องจับทิ้งไว้นาน แต่ไม่ให้ดิสก์เต็ม

```bash
# เก็บไฟล์ละ 100 MB หมุนเวียน 10 ไฟล์ (สูงสุด ~1 GB) เก็บเฉพาะ header
sudo tcpdump -i eth0 -nn -s 128 -C 100 -W 10 -w /var/tmp/cap.pcap 'host 10.0.0.5'

# สร้างไฟล์ใหม่ทุกชั่วโมง ตั้งชื่อตามเวลา
sudo tcpdump -i eth0 -nn -G 3600 -w '/var/tmp/cap-%Y%m%d-%H%M.pcap' 'port 443'

# รันเบื้องหลังแม้ออกจาก SSH
sudo nohup tcpdump -i eth0 -nn -C 100 -W 10 -w /var/tmp/cap.pcap 'port 5060' >/dev/null 2>&1 &
```
เมื่อปัญหาเกิด จดเวลาไว้ แล้วหยิบไฟล์ช่วงนั้นมาวิเคราะห์

**ส่งไฟล์กลับมาเปิด:** `scp user@server:/var/tmp/cap.pcap .` แล้วเปิดด้วย Wireshark

---

## 6. tshark — Wireshark แบบ CLI

ใช้ display filter ของ Wireshark ได้ และดึงเฉพาะ field ออกมาเป็นตาราง/CSV

```bash
tshark -r cap.pcap -Y 'dns' -T fields -e frame.time -e ip.src -e dns.qry.name
tshark -r cap.pcap -Y 'http.request' -T fields -e ip.src -e http.host -e http.request.uri
tshark -r cap.pcap -Y 'tls.handshake.type==1' -T fields -e ip.src -e tls.handshake.extensions_server_name
tshark -r cap.pcap -q -z conv,ip                  # สรุป conversation
tshark -r cap.pcap -q -z io,stat,60               # ปริมาณต่อนาที
tshark -r cap.pcap -T fields -E separator=, -E header=y -e ip.src -e ip.dst -e tcp.dstport > out.csv
```
**ไฟล์ทำงานอื่น:** `editcap` (ตัดช่วงเวลา/แบ่งไฟล์), `mergecap` (รวมไฟล์จากหลายจุด), `capinfos` (สรุปข้อมูลไฟล์)

---

## 7. จับ packet บนอุปกรณ์เครือข่าย

| อุปกรณ์ | คำสั่งตัวอย่าง |
|---|---|
| **FortiGate** | `diagnose sniffer packet any 'host 10.0.0.5 and port 443' 4 0 l` (verbose 4 = แสดง interface, ส่งออก pcap ได้จาก GUI) |
| **Palo Alto** | GUI Monitor → Packet Capture หรือ `debug dataplane packet-diag set capture ...` (ตั้ง filter ก่อนเสมอ) |
| **Cisco IOS-XE (EPC)** | `monitor capture CAP interface Gi1/0/1 both match ipv4 host 10.0.0.5 any` → `monitor capture CAP start` → `show monitor capture CAP buffer brief` |
| **Cisco ASA** | `capture CAP interface inside match ip host 10.0.0.5 any` → `show capture CAP` |
| **Linux router/firewall, VM, container** | `tcpdump` ตามปกติ (`docker exec`/`nsenter` เข้า network namespace) |

> ⚠️ การจับบนอุปกรณ์ production ใช้ CPU ได้ **ตั้ง filter ให้แคบที่สุด** และจำกัดจำนวน packet เสมอ

---

## 8. Workflow แบบมืออาชีพ

```
 1) กำหนดคำถาม: "packet ไปถึง server ไหม?" "ใครส่ง RST?"
 2) เลือกจุดจับ (client / server / ก่อนและหลัง firewall)
 3) ตั้ง filter แคบที่สุด + -nn + จำกัดขนาด/จำนวน
 4) เริ่มจับ → ทำให้ปัญหาเกิด → หยุด
 5) เปิดใน Wireshark/tshark วิเคราะห์
 6) สรุปหลักฐาน (screenshot/บรรทัด packet) แนบใน ticket
```

---

## 9. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| tcpdump ไม่ต้องใช้สิทธิ์พิเศษ | ต้องใช้ root/sudo |
| ไม่ใส่ `-nn` ก็ได้ | การ resolve ชื่อทำให้ช้าและสร้าง DNS traffic เพิ่ม |
| `-w` แล้วจะแสดงบนจอด้วย | `-w` เขียนไฟล์อย่างเดียว |
| จับบน firewall ได้ไม่จำกัด | กิน CPU ต้องจำกัด filter และจำนวน |

---

## 10. Cheat Sheet

```
sudo tcpdump -i eth0 -nn 'host X and port 443'      จับดูบนจอ
sudo tcpdump -i eth0 -nn -w cap.pcap 'filter'       บันทึกไฟล์
sudo tcpdump -i eth0 -C 100 -W 10 -w cap.pcap       ring buffer
tcpdump -r cap.pcap -nn                              อ่านไฟล์
Flags: [S] SYN · [S.] SYN-ACK · [.] ACK · [P.] data · [F.] FIN · [R] RST
BPF: host/net/port/src/dst · tcp/udp/icmp/arp · and/or/not · ตัด 'not port 22'
tshark -r f -Y 'filter' -T fields -e field  → ตาราง/CSV
FortiGate: diagnose sniffer packet · ASA: capture · IOS-XE: monitor capture
```

---

## 11. แบบทดสอบ 10 ข้อ

1. option `-nn` ทำอะไร และทำไมควรใช้
2. คำสั่งจับ DNS บน eth0 แล้วบันทึกเป็น dns.pcap
3. ทำไมต้องใส่ `not port 22` เมื่อจับบน server ผ่าน SSH
4. Flags `[S.]` และ `[R]` หมายถึงอะไร
5. ต้องการจับต่อเนื่องหลายวันโดยไม่ให้ดิสก์เต็ม ใช้ option อะไร
6. คำสั่งจับเฉพาะ traffic ระหว่างเครื่องเรากับ 10.0.0.5 ที่ port 80 หรือ 443
7. tshark ต่างจาก tcpdump อย่างไร
8. คำสั่ง FortiGate สำหรับจับ packet
9. หลังจับบน server เสร็จ จะนำไฟล์มาวิเคราะห์บนเครื่องตัวเองอย่างไร
10. ข้อควรระวังเมื่อจับ packet บน firewall ที่ใช้งานจริง

<details><summary><b>เฉลย</b></summary>

1. ไม่แปลง IP และ port เป็นชื่อ — เร็วขึ้นและไม่สร้าง DNS query เพิ่ม
2. `sudo tcpdump -i eth0 -nn -w dns.pcap 'port 53'`
3. ไม่ให้ packet ของ SSH session ตัวเองท่วมผลลัพธ์
4. `[S.]` = SYN-ACK, `[R]` = RST
5. `-C <MB> -W <จำนวนไฟล์>` (ring buffer) หรือ `-G` + จำนวนไฟล์จำกัด
6. `sudo tcpdump -i eth0 -nn 'host 10.0.0.5 and (port 80 or port 443)'`
7. tshark เป็น Wireshark แบบ CLI ใช้ display filter ได้และถอด field/สถิติได้ละเอียดกว่า
8. `diagnose sniffer packet <interface> '<filter>' <verbose> <count> <timestamp>`
9. ใช้ scp/sftp คัดลอกไฟล์ .pcap แล้วเปิดใน Wireshark
10. ใช้ CPU ได้มาก — ตั้ง filter แคบที่สุด จำกัดจำนวน packet และระวังข้อมูลอ่อนไหว
</details>

---

➡️ ต่อไป: **Level 24 — Nmap & Network Discovery**
