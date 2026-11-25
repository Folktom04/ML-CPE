# บทเรียน Level 88 — SDN Concepts & Intent-Based Networking (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจ control/data/management plane · แนวคิด SDN แยก control plane และ controller · northbound/southbound API · OpenFlow (flow table, match–action) · P4 programmable data plane · controllers (ONOS, OpenDaylight, Ryu) · SDN ในงานจริง (ACI, NSX, SD-Access, SD-WAN, cloud) · Intent-Based Networking (IBN) · ทดลองด้วย Mininet + Ryu

---

## 1. ทบทวน 3 Planes

| Plane | หน้าที่ | ตัวอย่าง |
|---|---|---|
| **Data (Forwarding) plane** | ส่ง packet ตามตาราง (เร็วมาก ใน ASIC) | lookup FIB, ACL, QoS, encapsulation |
| **Control plane** | **ตัดสินใจ** ว่าจะส่งอย่างไร → สร้างตาราง | OSPF, BGP, STP, ARP |
| **Management plane** | คนกับระบบจัดการอุปกรณ์ | SSH/CLI, SNMP, API, syslog |

### เครือข่ายแบบดั้งเดิม
ทุกอุปกรณ์มี **control plane ของตัวเอง** (distributed) — ตั้งค่าทีละเครื่อง, routing protocol คำนวณกันเอง
- ✅ ทนทาน (ไม่มีศูนย์กลาง), พิสูจน์แล้วหลายสิบปี
- ❌ เปลี่ยนนโยบายทั้งเครือข่ายต้องแก้หลายร้อยเครื่อง, ควบคุม path ละเอียดยาก, นวัตกรรมขึ้นกับผู้ผลิต

---

## 2. SDN — Software-Defined Networking

**แนวคิดหลัก:** แยก **control plane ออกจากอุปกรณ์** ไปไว้ที่ **controller ศูนย์กลาง** (ซอฟต์แวร์) ซึ่งเห็นภาพรวมทั้งเครือข่าย แล้วโปรแกรม data plane ของอุปกรณ์ผ่าน API
```
            ┌─────────────── Applications ───────────────┐
            │  Load balancer · Firewall · Traffic eng.   │
            └───────────────────┬────────────────────────┘
                     Northbound API (REST/gRPC/intent)
            ┌───────────────────▼────────────────────────┐
            │        SDN Controller (control plane)       │  ← เห็นทั้ง topology
            │   topology · path computation · policy      │
            └───────────────────┬────────────────────────┘
                     Southbound API (OpenFlow, NETCONF, gNMI, P4Runtime, BGP, OVSDB)
            ┌──────────┬────────┴──────┬────────────────┐
         [Switch]   [Switch]        [Switch]         [vSwitch]    ← data plane (ทำตามที่สั่ง)
```

| API | ระหว่าง | ตัวอย่าง |
|---|---|---|
| **Northbound** | แอป/คน/orchestrator ↔ controller | REST API, intent API |
| **Southbound** | controller ↔ อุปกรณ์ | **OpenFlow**, NETCONF/YANG, gNMI, P4Runtime, BGP (BGP-LS/PCEP/FlowSpec), OVSDB |
| East-West | controller ↔ controller (cluster/federation) | |

### ข้อดี/ข้อเสีย

| ✅ | ❌ |
|---|---|
| **มุมมองรวม** — คำนวณ path/นโยบายทั้งเครือข่ายได้ดีกว่า | **Controller เป็นจุดศูนย์กลาง** → ต้องทำ cluster/HA (single point of failure, ความปลอดภัยของ controller สำคัญมาก) |
| **Programmability** — automation ผ่าน API ที่เดียว | Scale ของ controller, latency ของ control |
| เปลี่ยนนโยบายเร็ว สม่ำเสมอ | ทักษะใหม่, ระบบนิเวศ/ผูกกับผู้ผลิต |
| ฮาร์ดแวร์อาจถูกลง (white box) | debugging ข้ามชั้นซับซ้อน |

---

## 3. OpenFlow

protocol southbound แรกที่ทำให้ SDN เป็นที่รู้จัก (ONF) — controller ติดตั้ง **flow entry** ลงใน **flow table** ของ switch

### Flow entry

| ส่วน | ตัวอย่าง |
|---|---|
| **Match fields** | in_port, eth_src/dst, eth_type, vlan, ip_src/dst, ip_proto, tcp/udp port |
| **Priority** | ตัวไหนชนะเมื่อ match หลายตัว |
| **Instructions/Actions** | output:port, drop, set-field (แก้ header), push/pop VLAN, goto-table, **send to controller** |
| **Counters** | packets/bytes ที่ match |
| **Timeouts** | idle/hard timeout |

```
 priority=200, ip, nw_src=10.0.50.0/24, nw_dst=10.0.10.0/24 → actions=drop          (Guest ห้ามเข้า server)
 priority=100, in_port=1, dl_dst=00:00:00:00:00:02 → actions=output:2
 priority=0   (table-miss) → actions=CONTROLLER                                       (ไม่รู้จัก ถาม controller)
```
### Reactive vs Proactive
- **Reactive:** packet แรกที่ไม่ match → ส่ง **Packet-In** ไป controller → controller ติดตั้ง flow → packet ถัดไปเร็ว (ภาระ controller สูง, latency packet แรก)
- **Proactive:** controller ติดตั้ง flow ล่วงหน้า (นิยมใน production)

### ข้อจำกัด
match ได้เฉพาะ field ที่ spec กำหนด, ฮาร์ดแวร์รองรับไม่เท่ากัน → ใน enterprise ปัจจุบันใช้ OpenFlow ไม่มาก แต่ยังพบใน **Open vSwitch** (OpenStack/OVN), งานวิจัย, บาง ISP/DC

---

## 4. P4 — Programmable Data Plane

**P4** = ภาษาเขียน "วิธีที่ switch ประมวลผล packet" เอง (parser → match-action tables → deparser)
- ไม่ถูกจำกัดด้วย protocol ที่ ASIC รู้จัก — สร้าง header/protocol ใหม่ได้
- รันบน switch ที่ programmable (Intel Tofino — หยุดพัฒนาแล้ว แต่แนวคิดยังอยู่ใน SmartNIC/DPU, FPGA), software switch (BMv2)
- ควบคุมด้วย **P4Runtime** (southbound)
- ใช้ทำ **in-band network telemetry (INT)** — ใส่ข้อมูล latency/queue ของทุก hop ลงใน packet

| OpenFlow | P4 |
|---|---|
| ควบคุม "ตาราง" ของ switch ที่มีโครงสร้างตายตัว | กำหนด "โครงสร้าง" ของ pipeline เอง |

---

## 5. Controllers แบบ Open Source

| Controller | หมายเหตุ |
|---|---|
| **ONOS** | สำหรับ carrier/SP, HA cluster, intent framework |
| **OpenDaylight (ODL)** | modular, รองรับหลาย southbound (NETCONF, BGP-LS, PCEP, OpenFlow) — ฐานของหลายผลิตภัณฑ์ |
| **Ryu** | Python เรียบง่าย เหมาะสำหรับเรียนรู้/ทดลอง |
| Faucet | OpenFlow controller สำหรับ production ขนาดเล็ก (config YAML) |
| OVN | control plane สำหรับ Open vSwitch (OpenStack, Kubernetes บางแบบ) |

---

## 6. SDN ในงานจริง (ที่คุณอาจใช้อยู่แล้ว)

ปัจจุบัน "SDN" มักหมายถึง **ระบบที่มี controller กลาง + API + automation** ไม่จำเป็นต้องเป็น OpenFlow

| ระบบ | แนวคิด |
|---|---|
| **Cisco ACI** | DC fabric: APIC controller, นโยบายแบบ **EPG/contract** (กลุ่มของ endpoint + กฎระหว่างกลุ่ม), VXLAN ภายใน |
| **VMware NSX** | overlay + distributed firewall ใน hypervisor (Level 75) |
| **Cisco SD-Access (Catalyst Center)** | campus fabric: LISP (control) + VXLAN (data) + **SGT** (Cisco TrustSec — นโยบายตามกลุ่มผู้ใช้) + ISE |
| **Juniper Apstra** | intent-based DC (multi-vendor) |
| **Arista CloudVision** | config/telemetry/change control ของ EOS |
| **SD-WAN** | controller/orchestrator กลาง, นโยบาย application-aware (Level 60) |
| **Cloud VPC** (AWS/Azure/GCP) | SDN ขนาดใหญ่ที่สุด — สร้าง subnet/route/firewall ผ่าน API ทั้งหมด (Level 78) |
| **Cloud-managed Wi-Fi/LAN** (Meraki, Mist) | dashboard/AI กลาง |
| Kubernetes CNI (Cilium/Calico) | controller (agent) โปรแกรม data plane (eBPF/iptables) ตาม policy (Level 77/80) |

**ผลลัพธ์ร่วม:** ผู้ดูแลกำหนด **นโยบายระดับกลุ่ม/แอป** แทน config ทีละพอร์ต/IP

---

## 7. Intent-Based Networking (IBN)

**IBN** = บอก "**อะไร**" (เจตนาทางธุรกิจ) ไม่ใช่ "**อย่างไร**" (คำสั่ง CLI) แล้วระบบ:
```
 ① Translation   : "ฝ่ายบัญชีเข้า ERP ได้ แต่ Guest เข้าไม่ได้ และ VoIP ได้ priority"
                    → แปลงเป็น VLAN/VRF/SGT/ACL/QoS
 ② Activation    : deploy ไปยังอุปกรณ์ทั้งหมดอัตโนมัติ
 ③ Assurance     : ตรวจสอบต่อเนื่อง (telemetry) ว่าเครือข่ายยังทำตาม intent จริงไหม
 ④ Remediation   : พบความต่าง → แจ้งเตือน/แนะนำ/แก้อัตโนมัติ (closed loop)
```

| แบบเดิม | IBN |
|---|---|
| "ตั้ง ACL 101 บน 40 router" | "Guest ห้ามเข้า server zone" |
| ตรวจว่าทำงานไหมด้วยมือ | ระบบตรวจต่อเนื่องและบอกเมื่อผิด |
| ตัวอย่าง | Cisco Catalyst Center, Juniper Apstra/Mist, Arista CloudVision, Forward Networks (verification), Batfish (ตรวจ intent ก่อน deploy — Level 84) |

**ความเชื่อมโยงกับ NetDevOps:** Source of Truth (intent ในรูปข้อมูล — Level 89) → generate config → deploy → verify (pre/post check, telemetry) = **closed-loop automation** ที่ทำได้ด้วยเครื่องมือ open source

---

## 8. Lab: Mininet + Ryu

```bash
# ติดตั้ง (Ubuntu VM สำหรับ lab)
sudo apt install mininet openvswitch-switch
python3 -m venv ryu-env && source ryu-env/bin/activate && pip install ryu   # (Ryu เก่าแล้ว อาจต้องใช้ Python รุ่นที่รองรับ หรือใช้ os-ken)
# terminal 1: รัน controller (L2 learning switch ตัวอย่าง)
ryu-manager ryu.app.simple_switch_13
# terminal 2: สร้าง topology 1 switch 3 host ชี้ไปที่ controller
sudo mn --topo single,3 --mac --switch ovsk,protocols=OpenFlow13 --controller remote
mininet> pingall
mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s1      # ดู flow ที่ controller ติดตั้ง
```
### โครงของ Ryu app (L2 learning ย่อ)
```python
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet

class L2Switch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw); self.mac_to_port = {}
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in(self, ev):
        msg, dp = ev.msg, ev.msg.datapath
        ofp, parser = dp.ofproto, dp.ofproto_parser
        in_port = msg.match["in_port"]
        eth = packet.Packet(msg.data).get_protocol(ethernet.ethernet)
        table = self.mac_to_port.setdefault(dp.id, {})
        table[eth.src] = in_port                                   # เรียนรู้ MAC
        out_port = table.get(eth.dst, ofp.OFPP_FLOOD)              # ไม่รู้ → flood
        actions = [parser.OFPActionOutput(out_port)]
        if out_port != ofp.OFPP_FLOOD:                             # ติดตั้ง flow ครั้งต่อไปไม่ต้องถาม controller
            match = parser.OFPMatch(in_port=in_port, eth_dst=eth.dst)
            inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
            dp.send_msg(parser.OFPFlowMod(datapath=dp, priority=1, match=match, instructions=inst, idle_timeout=60))
        dp.send_msg(parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id, in_port=in_port,
                                        actions=actions, data=None if msg.buffer_id != ofp.OFP_NO_BUFFER else msg.data))
```
(ต้องมี handler ติดตั้ง table-miss flow → CONTROLLER ตอน switch เชื่อมต่อ — ดูตัวอย่าง `simple_switch_13.py`)

---

## 9. บทบาทของ Network Engineer ในยุค SDN/IBN

- ไม่ได้หายไป แต่เปลี่ยนจาก "พิมพ์ CLI" → **ออกแบบนโยบาย/สถาปัตยกรรม, เข้าใจสิ่งที่ controller ทำเบื้องหลัง, automation, troubleshooting ข้ามชั้น (overlay/underlay/controller)**
- ยังต้องรู้พื้นฐาน (routing, VXLAN, BGP) — เมื่อ controller ทำงานผิดพลาด คนที่เข้าใจพื้นฐานเท่านั้นที่แก้ได้

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| SDN = OpenFlow | OpenFlow เป็น southbound หนึ่ง — SDN คือแนวคิด controller + programmability |
| SDN ทำให้ไม่ต้องรู้ networking | ต้องรู้มากขึ้นเพื่อแก้ปัญหาข้ามชั้น |
| Controller ล่ม = เครือข่ายหยุดทันทีเสมอ | ระบบส่วนใหญ่ data plane ยังทำงานต่อด้วยสถานะเดิม (แต่เปลี่ยนแปลงไม่ได้) — ขึ้นกับการออกแบบ |
| IBN คือ automation แบบ push config | IBN รวม assurance — ตรวจสอบต่อเนื่องว่าตรงกับ intent |
| SDN มีแค่ใน data center | cloud, SD-WAN, campus fabric, Wi-Fi cloud-managed ล้วนเป็น SDN |

---

## 11. Cheat Sheet

```
Data plane (ส่ง) · Control plane (ตัดสินใจ) · Management plane (จัดการ)
SDN: แยก control → controller กลาง · Northbound (แอป↔controller) · Southbound (controller↔อุปกรณ์)
Southbound: OpenFlow · NETCONF/YANG · gNMI · P4Runtime · BGP-LS/PCEP/FlowSpec · OVSDB
OpenFlow entry: match · priority · actions · counters · timeouts · table-miss → controller
Reactive (packet-in) vs Proactive
P4: เขียน pipeline ของ data plane เอง · INT
Controllers: ONOS · OpenDaylight · Ryu · Faucet · OVN
จริง: ACI (EPG/contract) · NSX · SD-Access (LISP/VXLAN/SGT) · Apstra · SD-WAN · Cloud VPC
IBN: translate → activate → assure → remediate (closed loop)
Lab: mininet --controller remote + ryu-manager · ovs-ofctl dump-flows
```

---

## 12. แบบทดสอบ 10 ข้อ

1. Data plane, control plane, management plane ต่างกันอย่างไร
2. แนวคิดหลักของ SDN คืออะไร
3. Northbound กับ southbound API ต่างกันอย่างไร ยกตัวอย่าง
4. Flow entry ของ OpenFlow ประกอบด้วยอะไร
5. Reactive กับ proactive flow installation ต่างกันอย่างไร
6. P4 ต่างจาก OpenFlow อย่างไร
7. ข้อเสียหลักของ controller ศูนย์กลางและแนวทางแก้
8. ยกตัวอย่าง SDN ที่พบในงานจริง 3 อย่าง
9. Intent-based networking มีขั้นตอนอะไรบ้าง
10. ทำไม network engineer ยังต้องรู้พื้นฐานแม้ใช้ SDN

<details><summary><b>เฉลย</b></summary>

1. Data plane ส่ง packet ตามตาราง; control plane ตัดสินใจและสร้างตาราง (routing protocol); management plane ใช้จัดการอุปกรณ์ (SSH/SNMP/API)
2. แยก control plane ออกจากอุปกรณ์ไปไว้ที่ controller ศูนย์กลางที่เห็นภาพรวม และโปรแกรม data plane ผ่าน API
3. Northbound = แอป/orchestrator ↔ controller (REST/intent API); southbound = controller ↔ อุปกรณ์ (OpenFlow, NETCONF, gNMI, P4Runtime)
4. Match fields, priority, instructions/actions, counters, timeouts
5. Reactive ติดตั้ง flow เมื่อ packet แรกถูกส่งถาม controller (packet-in); proactive ติดตั้งล่วงหน้า
6. OpenFlow ควบคุมตารางของ pipeline ที่ตายตัว; P4 กำหนดโครงสร้าง pipeline/การ parse header เอง
7. เป็นจุดศูนย์กลางของความล้มเหลว/การโจมตีและ scale — ทำ cluster/HA, ปกป้อง controller, ออกแบบให้ data plane ทำงานต่อได้
8. Cloud VPC, SD-WAN, Cisco ACI/SD-Access, VMware NSX, Meraki/Mist cloud-managed, Kubernetes CNI
9. Translation (แปลงเจตนาเป็นนโยบาย/config) → activation (deploy) → assurance (ตรวจต่อเนื่อง) → remediation (แก้/แจ้งเตือน)
10. เพราะ SDN ยังสร้างบนพื้นฐาน (routing, VXLAN, BGP) เมื่อระบบผิดพลาดต้องเข้าใจสิ่งที่เกิดเบื้องหลังเพื่อแก้ปัญหาข้ามชั้น
</details>

---

➡️ ต่อไป: **Level 89 — Source of Truth & IPAM (NetBox)**
