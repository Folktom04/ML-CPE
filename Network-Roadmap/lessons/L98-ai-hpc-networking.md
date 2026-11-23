# บทเรียน Level 98 — Networking for AI / HPC Data Centers (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจว่าทำไม AI training ต้องการเครือข่ายพิเศษ · ลักษณะ traffic (collective ops, all-reduce, elephant flows, synchronization, tail latency) · front-end vs back-end (scale-out) vs scale-up network · RDMA, InfiniBand, RoCEv2, Ultra Ethernet · lossless Ethernet (PFC, ECN, DCQCN) และความเสี่ยง · ปัญหา ECMP กับ low-entropy flows และทางแก้ · rail-optimized topology · 400G/800G optics · ทดลอง Soft-RoCE และ simulation

---

## 1. ทำไม AI เปลี่ยนการออกแบบเครือข่าย DC

การเทรนโมเดลขนาดใหญ่กระจายงานไปยัง **GPU หลายพัน–หลายหมื่นตัว** ที่ต้องแลกข้อมูลกันตลอดเวลา
```
 รอบการเทรน (iteration):
   ① แต่ละ GPU คำนวณ (compute) กับข้อมูลส่วนของตัวเอง
   ② ทุก GPU แลก gradient กัน (communication: all-reduce) ← ใช้ network
   ③ ทุก GPU ต้อง "รอกัน" ให้ครบก่อนเริ่มรอบถัดไป (synchronization)
```
**ผลกระทบ:** **GPU ที่ช้าที่สุด (หรือ packet ที่ช้าที่สุด) กำหนดความเร็วของทั้ง cluster** → GPU ราคาหลายแสนบาทต่อตัวนั่งรอเครือข่าย = เสียเงินมหาศาล
| เครือข่าย enterprise DC | AI/HPC back-end network |
|---|---|
| flow จำนวนมาก ขนาดหลากหลาย | **flow น้อยแต่ใหญ่มาก (elephant)** ระหว่าง GPU |
| ดู average throughput | **tail latency / Job Completion Time (JCT)** สำคัญที่สุด |
| oversubscription 3:1 ได้ | **non-blocking 1:1** (หรือใกล้เคียง) |
| packet loss เล็กน้อยรับได้ (TCP retransmit) | loss ทำให้ RDMA ช้ามาก → ต้อง **lossless/ใกล้ lossless** |
| 10/25/100G ต่อ server | **400G/800G ต่อ GPU** (server 8 GPU = 3.2–6.4 Tbps) |

---

## 2. ลักษณะ Traffic: Collective Communication

library (NVIDIA **NCCL**, AMD RCCL) ทำ **collective operations**:
| Operation | ความหมาย |
|---|---|
| **All-Reduce** ⭐ | ทุก GPU รวมค่า (เช่น บวก gradient) แล้วทุกตัวได้ผลรวม — ใช้มากที่สุดใน data parallel training |
| All-Gather | ทุกตัวได้ข้อมูลของทุกตัว |
| Reduce-Scatter | รวมแล้วแบ่งผลลัพธ์ให้แต่ละตัว |
| All-to-All | ทุกตัวส่งข้อมูลต่างกันให้ทุกตัว — ใช้ใน **Mixture-of-Experts (MoE)** หนักมากต่อเครือข่าย |
| Broadcast | ส่งจากตัวหนึ่งไปทุกตัว |
**Ring/Tree all-reduce:** GPU ส่งต่อกันเป็นวง/ต้นไม้ — ทุกลิงก์ทำงานพร้อมกันเต็มความเร็ว, เป็นจังหวะ (bursty, synchronized)
- **Incast:** หลายตัวส่งไปหาตัวเดียวพร้อมกัน → buffer ล้น (Level 90 microburst)
- **Low entropy:** flow จำนวนน้อย (เช่น 8 flow ต่อ server) ที่ 5-tuple ใกล้เคียงกัน → ECMP hash กระจายได้ไม่ดี (ข้อ 6)

---

## 3. เครือข่าย 3 แบบใน AI Cluster

```
 ┌──────────── GPU Server (เช่น 8 GPU) ────────────┐
 │ GPU0 GPU1 ... GPU7   ←──── Scale-up: NVLink/NVSwitch (ภายใน server/rack, TB/s) │
 │  │    │        │                                  │
 │ NIC0 NIC1 ... NIC7   ←──── Back-end (scale-out): 1 NIC 400/800G ต่อ GPU        │
 │ NIC-FE (2×100/200G)  ←──── Front-end: storage, management, ผู้ใช้, inference API │
 │ BMC                  ←──── OOB management                                       │
 └─────────────────────────────────────────────────┘
```
| เครือข่าย | หน้าที่ | ลักษณะ |
|---|---|---|
| **Scale-up** | GPU ↔ GPU ใน server/rack | NVLink/NVSwitch (NVIDIA), UALink (มาตรฐานเปิดใหม่) — bandwidth สูงมาก latency ต่ำมาก |
| **Scale-out (back-end)** ⭐ | GPU ↔ GPU ข้าม server | **InfiniBand หรือ Ethernet (RoCEv2)** — non-blocking, lossless/congestion control |
| **Front-end** | storage (dataset/checkpoint), ผู้ใช้, orchestration (Kubernetes/Slurm), อินเทอร์เน็ต | Ethernet DC ปกติ (spine-leaf — Level 73) แต่ bandwidth สูง |
| Storage network | บางแบบแยก (NVMe-oF, parallel FS: Lustre, GPFS, WEKA, VAST) | throughput สูงตอนโหลดข้อมูล/บันทึก checkpoint |

---

## 4. RDMA — หัวใจของ AI Networking

**RDMA (Remote Direct Memory Access)** = ย้ายข้อมูลจาก memory ของเครื่องหนึ่งไปยัง memory ของอีกเครื่อง **โดยไม่ผ่าน CPU/OS kernel** (kernel bypass, zero-copy)
```
 TCP/IP ปกติ: App → copy → kernel → TCP stack → NIC ... → NIC → kernel → copy → App   (CPU ทำงานหนัก, latency สูง)
 RDMA      : App memory → NIC ─────────────────────────────→ NIC → App memory          (NIC ทำเอง, µs)
 GPUDirect RDMA: memory ของ GPU → NIC → NIC → memory ของ GPU (ไม่ผ่าน CPU memory เลย)
```
### ตัวเลือก Transport
| เทคโนโลยี | ลักษณะ |
|---|---|
| **InfiniBand (IB)** | สร้างมาเพื่อ HPC: lossless ด้วย **credit-based flow control**, subnet manager, adaptive routing, SHARP (คำนวณ reduce ใน switch) — ประสิทธิภาพยอดเยี่ยม แต่ระบบนิเวศเฉพาะ (ผู้ผลิตหลักรายเดียว) |
| **RoCEv2** (RDMA over Converged Ethernet v2) ⭐ | RDMA บน **UDP/IP (dst port 4791)** → route ได้บน Ethernet ปกติ — ต้องทำให้ Ethernet "เกือบ lossless" + congestion control |
| iWARP | RDMA บน TCP — ใช้น้อยใน AI |
| **Ultra Ethernet (UEC)** | มาตรฐานใหม่จาก Ultra Ethernet Consortium (spec 1.0 ออกปี 2025): transport ใหม่ที่ออกแบบสำหรับ AI/HPC — packet spraying, รับ packet ไม่เรียงลำดับได้, congestion control ใหม่, ลดการพึ่ง PFC |
แนวโน้ม: Ethernet ได้รับความนิยมเพิ่มขึ้นมากใน AI cluster ขนาดใหญ่ (ราคา, ระบบนิเวศหลายผู้ผลิต, ทักษะ) ขณะที่ InfiniBand ยังเป็นมาตรฐานในหลาย cluster

---

## 5. Lossless Ethernet: PFC, ECN, DCQCN

RoCE รับ packet loss ได้แย่มาก (go-back-N retransmission → throughput ตก) → ต้องป้องกันการทิ้ง packet จาก congestion

### PFC — Priority Flow Control (802.1Qbb)
switch ส่ง **pause frame เฉพาะ priority (class)** ไปยัง upstream เมื่อ buffer ของ queue นั้นใกล้เต็ม → upstream หยุดส่ง class นั้นชั่วคราว (class อื่นยังวิ่ง)
```
 RoCE traffic → priority 3 (lossless queue) · traffic อื่น → priority 0 (lossy ปกติ)
 Buffer ของ queue 3 ถึง Xoff threshold → ส่ง PFC pause ไปยังพอร์ตต้นทาง → ถึง Xon → resume
```
**ความเสี่ยงของ PFC** ⚠️
| ปัญหา | อธิบาย |
|---|---|
| **Head-of-line blocking** | pause ทั้ง priority บนพอร์ต → flow ที่ไม่ได้เป็นต้นเหตุถูกหยุดไปด้วย |
| **Congestion spreading** | pause แพร่ย้อนกลับเป็นทอด ๆ (tree saturation) ทั่ว fabric |
| **PFC deadlock** | pause วนเป็นวง (cyclic buffer dependency) → ทุกอย่างค้าง |
| **PFC storm** | NIC/host เสียส่ง pause ไม่หยุด → ทำให้ส่วนใหญ่ของ fabric ค้าง → ต้องเปิด **PFC watchdog** |
→ **PFC เป็นตาข่ายนิรภัยสุดท้าย** ไม่ใช่กลไกหลัก

### ECN + DCQCN — Congestion Control (กลไกหลัก)
```
 1. Switch: queue เริ่มยาว (เกิน threshold Kmin) → mark ECN (CE bit) ใน IP header แบบ probabilistic (WRED/ECN)
 2. Receiver NIC เห็น CE → ส่ง CNP (Congestion Notification Packet) กลับไปหาผู้ส่ง
 3. Sender NIC ลดอัตราการส่ง (DCQCN algorithm) แล้วค่อย ๆ เพิ่มกลับ
 → ลดความเร็ว "ก่อน" buffer เต็ม จึงแทบไม่ต้องใช้ PFC
```
### การตั้งค่าที่ต้องตรงกัน end-to-end
- **DSCP/priority mapping** ของ RoCE (เช่น DSCP 26 → priority 3) และ CNP (เช่น DSCP 48) **ตรงกันทุก switch และ NIC**
- PFC เปิดเฉพาะ priority ของ RoCE, ECN threshold, buffer allocation (headroom ตามความยาวสาย/ความเร็ว)
- MTU (มัก 4096+ สำหรับ RoCE payload / jumbo 9000 ที่ Ethernet)
- ผู้ผลิตมี "AI/RoCE QoS profile" สำเร็จรูป (เช่น Arista, Cisco Nexus, NVIDIA Spectrum, Juniper) — ใช้เป็นจุดเริ่มต้นแล้วปรับตามการทดสอบ
```
! ตัวอย่างแนวคิด (syntax ต่างตามผู้ผลิต)
qos map dscp 26 to traffic-class 3
priority-flow-control mode on
priority-flow-control priority 3 no-drop
priority-flow-control watchdog
random-detect ecn  (บน queue 3: minimum-threshold 150 KB, maximum-threshold 1500 KB)
```

---

## 6. Load Balancing: ปัญหา ECMP กับ AI Traffic

### ทำไม ECMP ปกติไม่เหมาะ
- ECMP hash **ต่อ flow** (5-tuple) → flow ช้าง (หลาย GB) ไม่กี่ตัว + entropy ต่ำ → **หลาย flow ชนกันลงลิงก์เดียว** ขณะลิงก์อื่นว่าง
```
 8 flow ขนาดเท่ากัน · 8 uplink · ถ้ากระจายสมบูรณ์ ลิงก์ละ 1 flow
 ความน่าจะเป็นที่ hash ไม่ชนกันเลย = 8!/8^8 ≈ 0.24%  → แทบทุกครั้งมีลิงก์ที่ได้ 2+ flow (ความเร็วลดครึ่ง)
 → เพราะ synchronization ทั้งงานช้าตาม flow ที่ช้าที่สุด
```
### ทางแก้
| วิธี | หลักการ |
|---|---|
| **Flowlet switching** | แบ่ง flow ตามช่องว่างเวลา (gap) → ช่วงใหม่ย้ายลิงก์ได้โดยไม่สลับลำดับ |
| **Adaptive/Dynamic load balancing** | switch เลือกลิงก์ตาม **โหลดจริง** ของ queue/ลิงก์ (ไม่ใช่ hash อย่างเดียว) |
| **Packet spraying** | กระจาย **ทุก packet** ไปทุกลิงก์ → ใช้ได้เต็มที่ แต่ packet มาไม่เรียง → NIC ต้องรองรับ (เช่น SuperNIC, Ultra Ethernet) |
| **เพิ่ม entropy** | ใช้หลาย Queue Pair (QP) ต่อการเชื่อมต่อ, ปรับ UDP source port |
| **Scheduled/controlled fabric** | ระบบที่ fabric จัดตารางเอง (เช่น VOQ-based, DDC) |
| **Rail-optimized + ทำให้ traffic ส่วนใหญ่ไม่ข้าม spine** | ข้อ 7 |

---

## 7. Topology: Rail-Optimized

```
 Server 1: GPU0..GPU7 ─ NIC0..NIC7
 Server 2: GPU0..GPU7 ─ NIC0..NIC7
 ...
 Rail 0 leaf ← NIC0 ของทุก server · Rail 1 leaf ← NIC1 ของทุก server · ... · Rail 7 leaf
                 \_____________________ spine ______________________/
```
- GPU ลำดับเดียวกัน (เช่น GPU0) ของทุก server ต่อกับ **leaf เดียวกัน (rail)** → การสื่อสารระหว่าง GPU ลำดับเดียวกัน (ซึ่ง NCCL จัดให้บ่อยที่สุด) **อยู่ใน leaf เดียว 1 hop** ไม่ต้องผ่าน spine
- traffic ข้าม rail ใช้ NVLink ภายใน server ก่อน (scale-up) แล้วค่อยออก rail
- รวมกับ **non-blocking spine-leaf** (หรือ 3 ชั้นสำหรับหลายหมื่น GPU) — uplink = downlink (1:1)

### ตัวอย่างการคำนวณย่อ: 256 GPU (32 server × 8 GPU), 400G ต่อ GPU
```
 Rail 8 rails · แต่ละ rail มี 32 พอร์ต downlink 400G (1 ต่อ server)
 Leaf 64×400G: 32 down + 32 up (1:1) → 1 leaf ต่อ rail = 8 leaf
 Spine: uplink รวม 8 × 32 = 256 × 400G → spine 64×400G จำนวน 4 ตัว (แต่ละ leaf ต่อ spine ละ 8 พอร์ต)
 Optics: 256 (GPU↔leaf) + 256 (leaf↔spine) ลิงก์ × 2 ปลาย → ใช้ DAC/AEC/AOC ระยะสั้นได้ที่ไหนเพื่อลดต้นทุน/ไฟ
```
(ตัวเลขประกอบการเรียนรู้ — การออกแบบจริงใช้ reference architecture ของผู้ผลิตและคำนวณ power/cooling ด้วย)

### ความเร็วและ Optics
- 400G (QSFP-DD/OSFP), **800G** (OSFP, 2×400G breakout), 1.6T กำลังมา
- ทางเลือกสาย: DAC (ทองแดงสั้น ~2–3 m, ถูก, ไม่กินไฟ), AEC (active copper ~5–7 m), AOC/transceiver + fiber (ยาว)
- **Power และ cooling** ของ optics มีนัยสำคัญมาก → แนวโน้ม LPO (Linear Pluggable Optics), **CPO (Co-Packaged Optics)**
- rack AI กินไฟหลายสิบถึง 100+ kW ต่อ rack → liquid cooling — วางแผนร่วมกับทีม facility

---

## 8. Operations และ Observability

- **Telemetry ละเอียดสูง:** queue depth, PFC pause counters (ส่ง/รับต่อพอร์ต), ECN mark count, CNP, drops — ระดับวินาทีหรือต่ำกว่า (gNMI — Level 83)
- **ดูที่ฝั่ง job:** JCT, bus bandwidth จาก **nccl-tests** (`all_reduce_perf`) → เทียบกับค่าที่ควรได้
- **Link flap/BER:** ลิงก์ 400/800G ที่ error เพียงเส้นเดียวทำให้ทั้ง job ช้า/ล้ม → ตรวจ FEC corrected/uncorrected counters, optic DOM
- **Burn-in/validation** ก่อนส่งมอบ cluster: ทดสอบทุกลิงก์, all-reduce ทุก rail
- Scheduler (Slurm/Kubernetes) ที่รู้ topology → วางงานให้ใช้ GPU ที่อยู่ใกล้กัน

---

## 9. Lab ที่ทำได้โดยไม่มี GPU

### Soft-RoCE (rdma_rxe) บน Linux VM 2 เครื่อง
```bash
sudo apt install rdma-core ibverbs-utils perftest
sudo modprobe rdma_rxe
sudo rdma link add rxe0 type rxe netdev eth1      # สร้าง RDMA device บน interface Ethernet
rdma link show ; ibv_devices ; ibv_devinfo
# VM-A (server)
ib_write_bw -d rxe0
# VM-B (client)
ib_write_bw -d rxe0 10.10.10.1                     # วัด bandwidth ของ RDMA write
ib_write_lat -d rxe0 10.10.10.1                    # latency
sudo tcpdump -i eth1 udp port 4791 -w roce.pcap    # ดู RoCEv2 ใน Wireshark (เปิด dissector RoCE)
```
(Soft-RoCE ทำงานในซอฟต์แวร์ — ใช้เรียนรู้แนวคิด ไม่ได้แสดงประสิทธิภาพจริง)

### Simulation ECMP collision (Python)
```python
import random, statistics
def worst_link_load(flows=8, links=8, trials=100_000):
    worst = []
    for _ in range(trials):
        load = [0]*links
        for _ in range(flows):
            load[random.randrange(links)] += 1        # hash แบบสุ่ม ≈ ECMP ต่อ flow
        worst.append(max(load))
    return statistics.mean(worst)
print("ECMP: ลิงก์ที่หนักสุดมี flow เฉลี่ย", round(worst_link_load(), 2))   # ≈ 2.6 (ลิงก์ที่หนักสุดช้าลง ~2.6 เท่า)
print("Packet spraying (ideal): 1.0")
```

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| AI network = DC network ปกติแค่เร็วขึ้น | traffic synchronized, elephant, low entropy, tail latency สำคัญ — ออกแบบต่างกัน |
| เปิด PFC แล้วจบ | PFC เป็นตาข่ายสุดท้าย — ต้องมี ECN/DCQCN, watchdog, mapping ตรงกันทั้งหมด |
| ECMP กระจายโหลดได้ดีเสมอ | flow น้อยและใหญ่ทำให้ hash ชนกันบ่อย |
| ใช้ oversubscription 3:1 ได้เพื่อประหยัด | back-end ควร non-blocking — GPU ราคาแพงกว่าพอร์ตมาก |
| Throughput เฉลี่ยดี = งานเร็ว | job ช้าตาม flow/ลิงก์ที่ช้าที่สุด (tail) |

---

## 11. Cheat Sheet

```
AI training: compute → all-reduce (communication) → sync · ช้าสุดกำหนดทั้งหมด · JCT/tail latency
Collectives (NCCL): all-reduce · all-gather · reduce-scatter · all-to-all (MoE) · incast · low entropy
Scale-up (NVLink/UALink) · Scale-out back-end (IB/RoCE, 400/800G ต่อ GPU, 1:1) · Front-end · Storage
RDMA: kernel bypass, zero-copy · GPUDirect · IB (credit-based, SHARP) · RoCEv2 UDP 4791 · Ultra Ethernet
Lossless: PFC (pause ต่อ priority — HOL, spreading, deadlock, storm → watchdog) + ECN/DCQCN (CNP) หลัก
Mapping DSCP/priority/CNP ตรงกันทุก switch+NIC · buffer headroom · MTU
ECMP ชน → flowlet · adaptive LB · packet spraying · เพิ่ม QP/entropy · rail-optimized
Telemetry: queue, PFC, ECN, FEC/BER · nccl-tests all_reduce_perf · burn-in
Lab: Soft-RoCE rdma_rxe + ib_write_bw · simulate ECMP
```

---

## 12. แบบทดสอบ 10 ข้อ

1. ทำไม AI training cluster ต้องการ fabric non-blocking
2. All-reduce คืออะไร
3. Scale-up กับ scale-out network ต่างกันอย่างไร
4. RDMA ทำให้ latency ต่ำได้อย่างไร
5. RoCEv2 ใช้ protocol/port อะไร และต่างจาก InfiniBand อย่างไร
6. PFC ทำงานอย่างไร และมีความเสี่ยงอะไรบ้าง
7. ECN/DCQCN ช่วย RoCE อย่างไร
8. ทำไม ECMP ปกติไม่เหมาะกับ AI traffic และมีทางแก้อะไร
9. Rail-optimized topology คืออะไร มีประโยชน์อย่างไร
10. ต้อง monitor ตัวชี้วัดอะไรบ้างใน AI fabric

<details><summary><b>เฉลย</b></summary>

1. GPU ทุกตัวสื่อสารพร้อมกันและต้องรอกัน — ถ้ามีคอขวด ตัวที่ช้าที่สุดทำให้ทั้ง job ช้า และ GPU ราคาแพงกว่าพอร์ตเครือข่ายมาก
2. Collective operation ที่ทุก GPU รวมค่า (เช่น gradient) แล้วทุกตัวได้ผลรวมเดียวกัน
3. Scale-up เชื่อม GPU ภายใน server/rack (NVLink/NVSwitch, bandwidth สูงมาก); scale-out เชื่อม GPU ข้าม server ผ่าน NIC (InfiniBand/RoCE)
4. ย้ายข้อมูลระหว่าง memory โดยตรงผ่าน NIC ไม่ผ่าน CPU/kernel และไม่ copy หลายรอบ (GPUDirect ถึง memory ของ GPU)
5. UDP dst port 4791 บน IP/Ethernet (route ได้) — IB เป็นเครือข่ายเฉพาะ lossless ด้วย credit-based flow control ส่วน RoCE ต้องอาศัย PFC/ECN บน Ethernet
6. ส่ง pause frame ต่อ priority เมื่อ buffer ใกล้เต็มให้ upstream หยุดส่ง — เสี่ยง head-of-line blocking, congestion spreading, deadlock, PFC storm (ต้องมี watchdog)
7. Switch mark ECN เมื่อ queue เริ่มยาว receiver ส่ง CNP ให้ sender ลดอัตรา — ลด congestion ก่อน buffer เต็มจึงแทบไม่ต้องพึ่ง PFC
8. Flow น้อยแต่ใหญ่ entropy ต่ำ ทำให้ hash ชนกันลงลิงก์เดียว — ใช้ flowlet, adaptive load balancing, packet spraying (NIC รองรับ out-of-order), เพิ่ม QP/entropy, rail-optimized
9. NIC ลำดับเดียวกันของทุก server ต่อกับ leaf เดียวกัน ทำให้การสื่อสารระหว่าง GPU ลำดับเดียวกันอยู่ใน leaf เดียว ลด hop และการพึ่ง spine
10. Queue depth, PFC pause ส่ง/รับ, ECN marks/CNP, drops, FEC/BER และ optic DOM, link flaps, JCT/bus bandwidth จาก nccl-tests
</details>

---

➡️ ต่อไป: **Level 99 — Career Path, Certifications & Interview**
