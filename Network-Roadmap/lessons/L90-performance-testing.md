# บทเรียน Level 90 — Performance Testing & Tuning (ฉบับละเอียด)

> อ่านจบแล้วจะ: แยกองค์ประกอบของ latency · คำนวณ BDP และเข้าใจข้อจำกัดของ TCP window · ใช้ iperf3 อย่างถูกวิธี · อ่านผลและหาคอขวด (ลิงก์ vs CPU vs ต่อ flow) · ทดสอบ UDP/jitter/loss · จำลองเงื่อนไขด้วย netem · tune Linux (buffer, BBR, fq, offload, RSS, MTU) · bufferbloat และ microburst · RFC 2544/Y.1564 · TRex · รายงานผลการทดสอบ

---

## 1. "เน็ตช้า" แปลว่าอะไร

| ตัวชี้วัด | ความหมาย | ผู้ใช้รู้สึก |
|---|---|---|
| **Bandwidth** | ความจุของลิงก์ (ตามสัญญา) | — |
| **Throughput** | ปริมาณข้อมูลที่ส่งได้จริง | ดาวน์โหลดช้า |
| **Latency (RTT)** | เวลาไป-กลับ | หน่วง, เว็บโหลดช้า (หลาย round trip) |
| **Jitter** | ความแปรปรวนของ latency | เสียง/วิดีโอกระตุก |
| **Packet loss** | packet หาย | TCP ช้าลงมาก, เสียงขาด |
(ทบทวน Level 1/13) — **ต้องวัดให้ถูกตัว** ก่อนสรุปว่า "ต้องซื้อ bandwidth เพิ่ม"

---

## 2. องค์ประกอบของ Latency

```
 Latency = Propagation + Serialization + Queuing + Processing
```
| ส่วน | สาเหตุ | ตัวอย่าง |
|---|---|---|
| **Propagation** | ระยะทาง — แสงในไฟเบอร์ ≈ 200,000 km/s → **≈ 5 µs/km** | กรุงเทพ–สิงคโปร์ ~1,500 km (ทางสาย) → 7.5 ms ทางเดียว → **RTT ≥ 15 ms** (จริงมักมากกว่าเพราะเส้นทางอ้อม) |
| **Serialization** | เวลา "ปล่อย" bit ลงสาย = ขนาด ÷ ความเร็ว | 1500 B บน 1 Mbps = 12 ms · บน 10 Gbps = 1.2 µs |
| **Queuing** | รอใน buffer เมื่อ congestion | **แปรผันมาก** — ต้นเหตุหลักของ jitter/bufferbloat |
| **Processing** | lookup, firewall inspection, encryption | firewall ที่ทำ SSL inspection เพิ่มหลาย ms |
💡 **ไม่มีอุปกรณ์ใดลด propagation ได้** — ถ้าต้องการ latency ต่ำต้องย้ายระบบให้ใกล้ผู้ใช้ (CDN, edge, region ใกล้)

---

## 3. TCP Throughput และ BDP

### Bandwidth-Delay Product (BDP)
```
 BDP = Bandwidth × RTT  = ปริมาณข้อมูลที่ "ลอยอยู่ในท่อ" ได้
 ตัวอย่าง: 1 Gbps × 50 ms = 1,000,000,000 × 0.05 / 8 = 6.25 MB
```
TCP ส่งได้ไม่เกิน **window** ก่อนต้องรอ ACK → **Throughput สูงสุดต่อ flow ≈ Window ÷ RTT**
```
 Window 64 KB (ไม่มี window scaling), RTT 50 ms → 65,535 × 8 / 0.05 ≈ 10.5 Mbps  (แม้ลิงก์ 1 Gbps!)
 ต้องการ 1 Gbps ที่ RTT 50 ms → window ≥ 6.25 MB
```
→ ลิงก์ระยะไกล (สาขาต่างประเทศ, DR site, cloud ข้ามภูมิภาค) **ช้าต่อ flow** แม้ bandwidth เหลือ — แก้ด้วย window scaling + buffer ใหญ่ขึ้น, หลาย stream, protocol ที่เหมาะ (Level 13)

### Loss กับ TCP (Mathis formula — ประมาณ)
```
 Throughput ≤ (MSS / RTT) × (1.22 / √loss)
 MSS 1460 B, RTT 50 ms, loss 0.1% → (1460×8/0.05) × (1.22/0.0316) ≈ 9 Mbps
```
→ **loss เพียงเล็กน้อยบนลิงก์ RTT สูงทำลาย throughput ได้มาก** (สำหรับ congestion control แบบ loss-based เช่น CUBIC — BBR ทนกว่า)

---

## 4. iperf3 — เครื่องมือหลัก

```bash
# ฝั่ง server
iperf3 -s                                   # ฟังที่ TCP 5201
# ฝั่ง client
iperf3 -c 10.0.0.10 -t 30                   # TCP 30 วินาที (client → server)
iperf3 -c 10.0.0.10 -t 30 -R                # ย้อนทิศ (server → client)
iperf3 -c 10.0.0.10 -t 30 --bidir           # สองทิศพร้อมกัน
iperf3 -c 10.0.0.10 -t 30 -P 8              # 8 stream ขนาน
iperf3 -c 10.0.0.10 -w 8M                   # กำหนด window/socket buffer
iperf3 -c 10.0.0.10 -u -b 50M -l 1200       # UDP 50 Mbps → ดู jitter และ loss
iperf3 -c 10.0.0.10 -J > result.json        # ผล JSON สำหรับรายงาน/automation
iperf3 -c 10.0.0.10 -C bbr                  # เลือก congestion control (Linux)
```
### อ่านผล
```
[ ID] Interval           Transfer     Bitrate         Retr
[  5]   0.00-30.00  sec  3.28 GBytes   939 Mbits/sec   12     sender
[  5]   0.00-30.00  sec  3.28 GBytes   938 Mbits/sec          receiver
```
- **939 Mbps บน 1G** = ปกติ (overhead ของ Ethernet/IP/TCP ~5–6%)
- **Retr** = retransmissions → loss/congestion ระหว่างทาง
- UDP: ดู **Jitter** และ **Lost/Total** (สำคัญสำหรับ VoIP/video)

### วิเคราะห์คอขวด
| ผล | หมายถึง |
|---|---|
| 1 stream ได้ 2 Gbps, `-P 8` ได้ 9.4 Gbps | ข้อจำกัด **ต่อ flow** (window/RTT, CPU 1 core, ECMP hash) — ไม่ใช่ลิงก์ |
| `-P 8` ก็ไม่เกิน 2 Gbps | คอขวดที่ลิงก์/อุปกรณ์กลางทาง/CPU รวม/NIC |
| ทิศหนึ่งเร็ว อีกทิศช้า | asymmetric (ISP), duplex mismatch, policer ทิศเดียว, QoS |
| Retr สูง | loss: สายเสีย (CRC), congestion, policer |
| CPU ของเครื่องทดสอบ 100% | เครื่องทดสอบเป็นคอขวดเอง — ใช้เครื่องที่แรงขึ้น/หลาย stream/`-A` affinity |

### หลักการทดสอบที่ถูกต้อง
- ทดสอบ **end-to-end ระหว่างจุดที่สนใจ** และทดสอบแยกส่วน (segment) เพื่อหาจุดคอขวด
- **ทดสอบนานพอ** (≥30 วินาที) ทำซ้ำหลายรอบ หลายช่วงเวลา
- บันทึกเงื่อนไข (MTU, NIC, OS, path) · อย่าทดสอบเต็มลิงก์ production ในเวลาทำงานโดยไม่ได้แจ้ง/อนุมัติ
- **speedtest บนเว็บ** วัดถึง server ของผู้ให้บริการ — ไม่เท่ากับประสิทธิภาพไปยังแอปของเรา

---

## 5. จำลองเงื่อนไขด้วย netem

ทดสอบแอปเมื่อ latency สูง/มี loss (เช่น จำลองสาขาต่างประเทศ) ใน lab:
```bash
sudo tc qdisc add dev eth1 root netem delay 100ms 10ms loss 0.5%   # หน่วง 100±10 ms + loss 0.5%
sudo tc qdisc change dev eth1 root netem delay 200ms               # เปลี่ยนค่า
sudo tc qdisc add dev eth1 root tbf rate 20mbit burst 32kbit latency 400ms   # จำกัด bandwidth
sudo tc qdisc del dev eth1 root                                    # ลบ
```
⚠️ ใช้บนเครื่อง lab/router ทดสอบเท่านั้น

---

## 6. Linux Network Tuning (สำหรับ server/เครื่องทดสอบ)

### Socket buffers (สำหรับ high-BDP)
```bash
# /etc/sysctl.d/90-net-tuning.conf
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 134217728     # min default max
net.ipv4.tcp_wmem = 4096 65536 134217728
net.ipv4.tcp_window_scaling = 1              # (เปิดเป็นค่าเริ่มต้น)
net.core.default_qdisc = fq                  # pacing ที่ BBR ต้องการ
net.ipv4.tcp_congestion_control = bbr        # ทน loss/RTT สูงได้ดีกว่า CUBIC ในหลายกรณี
net.ipv4.tcp_mtu_probing = 1                 # ช่วยเมื่อ PMTUD ถูกบล็อก
```
```bash
sudo sysctl --system
sysctl net.ipv4.tcp_congestion_control ; ss -tin dst 10.0.0.10     # ดู cwnd, rtt, retrans ของ connection จริง
```
### NIC และ CPU
| เรื่อง | คำสั่ง/แนวคิด |
|---|---|
| **Offloads** (TSO/GSO/GRO/LRO, checksum) | `ethtool -k eth0` — ลดภาระ CPU (ปิดบางตัวเมื่อ capture/debug หรือใช้กับ router/bridge) |
| **RSS / multiqueue** | กระจาย interrupt ไปหลาย core: `ethtool -l eth0`, `-L combined 8` |
| **Ring buffer** | `ethtool -g eth0`, `-G eth0 rx 4096` — ลด drop ตอน burst |
| **IRQ affinity / irqbalance** | ผูก interrupt กับ core ที่เหมาะ (NUMA) |
| **ดู drop** | `ethtool -S eth0 | grep -i -E "drop|miss|err"`, `ip -s link`, `nstat` |
| **MTU/jumbo** | `ip link set eth0 mtu 9000` — **ทุก hop ใน path ต้องรองรับ** (ทดสอบ `ping -M do -s 8972`) — ใช้กับ storage/DC, ไม่ใช้บนอินเทอร์เน็ต |
| txqueuelen | `ip link set eth0 txqueuelen 10000` (ระวัง bufferbloat) |
⚠️ **เปลี่ยนทีละอย่าง วัดก่อน/หลัง** — tuning ตาม blog โดยไม่วัดอาจทำให้แย่ลง

---

## 7. Bufferbloat

**Buffer ใหญ่เกินไป** ในอุปกรณ์ (มักเป็น home/branch router, modem) → เมื่อลิงก์เต็ม packet รอในคิวนานหลายร้อย ms → **latency พุ่ง** ระหว่างมีการดาวน์โหลด/อัปโหลด
```
 ปกติ: ping 15 ms · ระหว่างอัปโหลดไฟล์ใหญ่: ping 600 ms → VoIP/Teams พัง
```
- ทดสอบ: **flent RRUL** (โหลดเต็มทั้งสองทิศพร้อมวัด latency), Waveform bufferbloat test
- แก้: **AQM — fq_codel / CAKE** (SQM บน OpenWrt/Linux), ตั้ง shaper ต่ำกว่าความเร็วจริงเล็กน้อย (~90–95%) เพื่อให้คิวอยู่ที่อุปกรณ์ที่เราควบคุม, QoS ให้ priority กับ real-time (Level 54)
```bash
sudo tc qdisc replace dev eth0 root cake bandwidth 95mbit
flent rrul -p all_scaled -l 60 -H netperf-server.example -o rrul.png
```

---

## 8. Microbursts

traffic พุ่งเกินความเร็วพอร์ตในช่วง **ไม่กี่ microsecond–millisecond** → buffer ของ switch ล้น → **drop** — แม้ค่าเฉลี่ย 5 นาทีแสดงแค่ 20%
```
 เกิดบ่อยเมื่อ: หลาย server ส่งพร้อมกันไปเครื่องเดียว (incast: storage, backup, AI, Hadoop shuffle)
               ลิงก์ความเร็วสูงลงลิงก์ความเร็วต่ำ (100G → 10G, 10G → 1G)
```
- **ตรวจ:** output **discards** ที่เพิ่มขึ้นบนพอร์ต (Level 86) ทั้งที่ utilization ต่ำ, telemetry ความละเอียดสูง (gNMI ทุก 1 วินาทีหรือน้อยกว่า), buffer/queue monitoring ของ switch (เช่น Arista LANZ, Cisco Nexus buffer telemetry)
- **แก้:** switch ที่ buffer ใหญ่ขึ้น (deep buffer) ในจุดที่จำเป็น, ลด oversubscription, QoS/ECN, เพิ่มความเร็ว uplink, ออกแบบ traffic (pacing)

---

## 9. การทดสอบระดับมาตรฐาน: RFC 2544, Y.1564, TRex

### RFC 2544 (benchmark อุปกรณ์ในห้องแล็บ)
| Test | วัด |
|---|---|
| **Throughput** | อัตราสูงสุดที่ **ไม่มี loss** (ต่อขนาด frame: 64, 128, 256, 512, 1024, 1280, 1518) |
| **Latency** | ที่อัตรา throughput |
| **Frame loss rate** | % loss ที่โหลดต่าง ๆ |
| **Back-to-back** | burst ยาวสุดที่รับได้โดยไม่ loss (ความสามารถของ buffer) |
💡 **Frame 64 bytes = pps สูงสุด** → แสดงขีดจำกัดของ CPU/forwarding engine (10G line rate ที่ 64B ≈ 14.88 Mpps) — datasheet ที่บอก "10 Gbps" มักวัดที่ frame ใหญ่

### ITU-T Y.1564 (Ethernet service activation)
ทดสอบ **วงจรของผู้ให้บริการ** ตาม SLA: CIR/EIR, frame delay, delay variation, loss — หลาย service (VoIP/data) พร้อมกัน → ใช้ตอนรับมอบวงจร Metro Ethernet/MPLS (Level 57)

### TRex
traffic generator open source (DPDK) ของ Cisco — สร้าง traffic ระดับหลายสิบ Gbps/หลายล้าน pps, stateful (จำลอง HTTP/แอปจริง) หรือ stateless → ใช้ทดสอบ firewall/router/VM ว่ารองรับเท่าไร (ใช้ใน lab เท่านั้น)

### ทดสอบ firewall ให้สมจริง
datasheet แยกตัวเลข: firewall throughput (UDP ใหญ่) ≫ **threat prevention/IPS throughput** ≫ **SSL inspection throughput** · ดู **connections per second** และ **concurrent sessions** — ทดสอบด้วย traffic mix ที่ใกล้ของจริง (Level 62)

---

## 10. รายงานผลการทดสอบ (Template)

```
 Test: WAN BKK ↔ CNX หลังอัปเกรดเป็น 500 Mbps    วันที่/เวลา: ...    ผู้ทดสอบ: ...
 Setup: iperf3 3.16, Ubuntu 24.04, NIC 10G, MTU 1500, path: BKK-FW → MPLS → CNX-FW
 ผล:
   TCP 1 stream   : 180 Mbps (RTT 12 ms, Retr 0)
   TCP 8 streams  : 474 Mbps (Retr 35)
   UDP 400 Mbps   : jitter 0.8 ms, loss 0.02%
   ping ระหว่าง load: 12 → 45 ms
 วิเคราะห์: ลิงก์ส่งได้ตามสัญญา (~95% ด้วย overhead); single flow ถูกจำกัดด้วย window ของ host
 ข้อเสนอ: เปิด QoS ให้ VoIP เนื่องจาก latency เพิ่มระหว่าง load; ปรับ TCP buffer บน backup server
```

---

## 11. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| ลิงก์ 1 Gbps ทุก flow ต้องได้ 1 Gbps | single flow ถูกจำกัดด้วย window/RTT/loss/CPU |
| ซื้อ bandwidth เพิ่มแก้ latency ได้ | propagation ไม่ลด; queuing แก้ด้วย QoS/AQM |
| speedtest เว็บ = ประสิทธิภาพของแอป | วัดถึง server ของผู้ให้บริการ ไม่ใช่ path ไปยังแอป |
| Datasheet 10 Gbps = ได้ 10 Gbps เมื่อเปิดทุกฟีเจอร์ | IPS/SSL inspection/frame เล็ก ได้ต่ำกว่ามาก |
| buffer ยิ่งใหญ่ยิ่งดี | bufferbloat ทำให้ latency พุ่ง |

---

## 12. Cheat Sheet

```
Latency = propagation (≈5 µs/km) + serialization (size/rate) + queuing + processing
BDP = BW × RTT · max TCP/flow ≈ window/RTT · Mathis: ∝ MSS/(RTT·√loss)
iperf3 -s / -c host -t 30 [-R | --bidir | -P 8 | -u -b 50M | -w 8M | -J | -C bbr]
1 stream ช้า, -P 8 เร็ว = ข้อจำกัดต่อ flow · Retr = loss · CPU เต็ม = เครื่องทดสอบคอขวด
netem: tc qdisc add dev X root netem delay 100ms loss 0.5%
Linux: rmem/wmem max · tcp_rmem/wmem · fq + bbr · ethtool -k/-l/-g/-S · MTU ทุก hop
Bufferbloat: flent rrul · fq_codel/CAKE · shaper ~95%
Microburst: output discards ที่ util ต่ำ · telemetry ละเอียด · deep buffer/ECN
RFC 2544 (throughput/latency/loss/back-to-back · 64B = pps สูงสุด) · Y.1564 (SLA วงจร) · TRex
```

---

## 13. แบบทดสอบ 10 ข้อ

1. องค์ประกอบของ latency มีอะไรบ้าง ส่วนใดแปรผันมากที่สุด
2. กรุงเทพ–สิงคโปร์ระยะทางสาย 1,500 km RTT ขั้นต่ำประมาณเท่าไร
3. ลิงก์ 1 Gbps RTT 80 ms BDP เท่าไร
4. Window 64 KB RTT 50 ms throughput ต่อ flow สูงสุดประมาณเท่าไร
5. iperf3 1 stream ได้ 1.5 Gbps แต่ -P 8 ได้ 9.4 Gbps บนลิงก์ 10G หมายความว่าอะไร
6. ใช้ iperf3 วัด jitter และ loss อย่างไร
7. Bufferbloat คืออะไร แก้อย่างไร
8. Microburst คืออะไร ทำไม monitoring 5 นาทีมองไม่เห็น
9. ทำไม RFC 2544 ทดสอบด้วย frame 64 bytes
10. Datasheet firewall บอก 10 Gbps แต่ใช้จริงได้ 2 Gbps สาเหตุที่เป็นไปได้คืออะไร

<details><summary><b>เฉลย</b></summary>

1. Propagation, serialization, queuing, processing — queuing แปรผันมากที่สุด (ต้นเหตุ jitter)
2. 1,500 × 5 µs = 7.5 ms ทางเดียว → RTT ≈ 15 ms (จริงมากกว่า)
3. 1,000,000,000 × 0.08 / 8 = 10 MB
4. 65,535 × 8 / 0.05 ≈ 10.5 Mbps
5. ลิงก์รองรับได้ — ข้อจำกัดอยู่ที่ต่อ flow (window/RTT, CPU core เดียว, hash ของ ECMP/LAG)
6. `iperf3 -c <server> -u -b <อัตรา>` แล้วดู Jitter และ Lost/Total ในผลลัพธ์
7. Buffer ใหญ่เกินทำให้ packet รอคิวนานเมื่อลิงก์เต็ม latency พุ่ง — แก้ด้วย AQM (fq_codel/CAKE), shaper ต่ำกว่าความเร็วจริงเล็กน้อย, QoS
8. Traffic พุ่งเกินความเร็วพอร์ตในระดับ µs–ms ทำให้ buffer ล้นและ drop — ค่าเฉลี่ย 5 นาทีเกลี่ย spike จนมองไม่เห็น (ดู output discards/telemetry ละเอียด)
9. Frame เล็กสุดให้ pps สูงสุด แสดงขีดจำกัดของการประมวลผล/forwarding engine
10. เปิด IPS/threat prevention หรือ SSL inspection, traffic เป็น packet เล็ก, connections per second/concurrent sessions สูง, ไม่ได้ใช้ hardware offload
</details>

---

🎉 **จบ Tier 9** · ➡️ ต่อไป: **Level 91 — Advanced Troubleshooting ระดับองค์กร** · กลับไปทำโปรเจคใน [09-automation-operations.md](../09-automation-operations.md)
