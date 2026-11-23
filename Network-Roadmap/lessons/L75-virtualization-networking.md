# บทเรียน Level 75 — Virtualization Networking (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจ virtual switch · VMware vSwitch/vDS, port group, VMkernel · NIC teaming · Hyper-V vSwitch/SET · Linux bridge, Open vSwitch, Proxmox · แยก traffic (mgmt/vMotion/storage/VM) · ออกแบบ uplink ไปยัง switch จริงอย่างถูกต้อง · SR-IOV · NSX/micro-segmentation · troubleshooting

---

## 1. Virtual Switch คืออะไร

host เครื่องเดียวมี VM หลายสิบตัว → ต้องมี **switch ในซอฟต์แวร์** เชื่อม vNIC ของ VM กับ NIC จริงของ host
```
 ┌──────────────────── ESXi / Hyper-V / KVM Host ─────────────────────┐
 │  [VM1 vNIC]  [VM2 vNIC]  [VM3 vNIC]   [vmk0 mgmt] [vmk1 vMotion]   │
 │      │           │           │            │            │           │
 │  ┌───┴───────────┴───────────┴────────────┴────────────┴───────┐   │
 │  │             Virtual Switch (port groups/VLANs)              │   │
 │  └──────────────────┬──────────────────────┬───────────────────┘   │
 │               uplink vmnic0           uplink vmnic1                │
 └──────────────────────┼──────────────────────┼──────────────────────┘
                        │ trunk                │ trunk
                   [ToR Leaf A]           [ToR Leaf B]
```
- VM ใน host เดียวกัน VLAN เดียวกัน → คุยกันในหน่วยความจำ **ไม่ออก NIC จริงเลย** (switch ภายนอกมองไม่เห็น traffic นี้)
- ลิงก์ host ↔ switch จริง เป็น **802.1Q trunk** ที่มีหลาย VLAN
- virtual switch **ไม่รัน STP** และไม่ส่ง frame จาก uplink หนึ่งไปอีก uplink → ไม่เกิด loop

---

## 2. VMware vSphere

### Standard vSwitch (vSS) vs Distributed vSwitch (vDS)
| | **vSS** | **vDS** ⭐ |
|---|---|---|
| ตั้งค่าที่ | ทีละ host | **vCenter ที่เดียว** ใช้กับทุก host |
| ความสม่ำเสมอ | config อาจต่างกันระหว่าง host → vMotion ล้ม | เหมือนกันทุก host |
| ฟีเจอร์ | พื้นฐาน | LACP, NetFlow/IPFIX, port mirroring, NIOC, LBT, private VLAN |
| License | ทุกระดับ | ระดับสูง |

### Port Group
"กลุ่มพอร์ต" ที่มีนโยบายเดียวกัน — สำคัญที่สุดคือ **VLAN ID**
| VLAN setting | ความหมาย |
|---|---|
| **VST (VLAN 10)** ⭐ | vSwitch ติด/ถอด tag ให้ VM (VM ไม่รู้เรื่อง VLAN) |
| EST (None/0) | switch จริงเป็น access port |
| VGT (4095 / trunk) | ส่ง tag เข้า VM (VM จัดการ VLAN เอง เช่น virtual firewall/router) |

### VMkernel Adapter (vmk) — NIC ของ hypervisor เอง
| vmk | traffic |
|---|---|
| vmk0 | **Management** (vCenter คุยกับ host) |
| vmk1 | **vMotion** (ย้าย VM — memory เยอะ ต้องการ bandwidth สูง) |
| vmk2 | **Storage**: iSCSI/NFS/**vSAN** |
| อื่น ๆ | Fault Tolerance, replication, backup |

### Security Policy ของ Port Group
| ตัวเลือก | ค่าแนะนำ | หมายเหตุ |
|---|---|---|
| Promiscuous mode | Reject | เปิดเฉพาะ IDS/nested lab |
| MAC address changes | Reject | |
| Forged transmits | Reject | (บาง appliance/nested ต้อง Accept) |

---

## 3. NIC Teaming / Load Balancing ไปยัง Uplink

| วิธี (vSphere) | หลักการ | ฝั่ง switch จริง |
|---|---|---|
| **Route based on originating virtual port** ⭐ (ค่าเริ่มต้น) | VM แต่ละตัวผูกกับ uplink หนึ่ง | trunk ธรรมดา (**ไม่ทำ port-channel**) |
| Route based on source MAC hash | คล้ายข้างบน | trunk ธรรมดา |
| **Route based on physical NIC load (LBT)** (vDS) | ย้าย VM ไป uplink อื่นเมื่อ uplink ใช้ >75% | trunk ธรรมดา |
| **Route based on IP hash** | กระจายต่อ flow | **ต้องเป็น static EtherChannel** (mode on) |
| **LACP (vDS LAG)** | | port-channel **mode active** |

⚠️ **ความผิดพลาดคลาสสิก:** ตั้ง port-channel ที่ switch จริง แต่ vSwitch ใช้ "originating port" (หรือกลับกัน) → **MAC flapping, packet loss, host หลุด**
**Failover order:** active / standby / unused uplinks · **Beacon probing** ต้องมี ≥3 uplink · **Notify switches = Yes** (ส่ง RARP เมื่อ VM ย้ายเพื่อให้ switch อัปเดต MAC table)

### ฝั่ง Switch จริง (ToR) สำหรับ host
```
interface Ethernet1/10
  description ESXi-01 vmnic0
  switchport mode trunk
  switchport trunk allowed vlan 10,20,30,100-110   ! เฉพาะ VLAN ที่ต้องใช้
  spanning-tree port type edge trunk               ! PortFast สำหรับ trunk ไป host
  mtu 9216
  no shutdown
```

---

## 4. Microsoft Hyper-V

- **Hyper-V Virtual Switch** 3 แบบ: **External** (ผูกกับ NIC จริง), **Internal** (VM ↔ host), **Private** (VM ↔ VM เท่านั้น)
- **SET (Switch Embedded Teaming)** — teaming ในตัว vSwitch (แนะนำแทน LBFO แบบเก่า) — switch-independent (ไม่ต้องทำ port-channel)
- **Host vNIC** สำหรับ Management, Live Migration, Cluster, **SMB Direct (RDMA)** สำหรับ Storage Spaces Direct/Azure Local
```powershell
New-VMSwitch -Name "SETswitch" -NetAdapterName "NIC1","NIC2" -EnableEmbeddedTeaming $true -AllowManagementOS $false
Add-VMNetworkAdapter -ManagementOS -SwitchName "SETswitch" -Name "Mgmt"
Set-VMNetworkAdapterVlan -ManagementOS -VMNetworkAdapterName "Mgmt" -Access -VlanId 10
Set-VMNetworkAdapterVlan -VMName "Web01" -Access -VlanId 20
Get-VMSwitchTeam ; Get-VMNetworkAdapterVlan -ManagementOS
```

---

## 5. Linux/KVM, Proxmox

### Linux Bridge
```bash
# /etc/network/interfaces (Debian/Proxmox) — bridge ที่รู้จัก VLAN + bond
auto bond0
iface bond0 inet manual
    bond-slaves eno1 eno2
    bond-mode 802.3ad            # LACP (ต้องตั้ง port-channel active ที่ switch)
    bond-xmit-hash-policy layer3+4
    bond-miimon 100
auto vmbr0
iface vmbr0 inet manual
    bridge-ports bond0
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes
    bridge-vids 2-4094
auto vmbr0.10
iface vmbr0.10 inet static
    address 10.0.10.21/24        # management ของ host บน VLAN 10
    gateway 10.0.10.1
```
```bash
bridge vlan show ; bridge fdb show ; cat /proc/net/bonding/bond0 ; ip -d link show
```

### Open vSwitch (OVS)
virtual switch แบบ programmable: รองรับ **OpenFlow**, VXLAN/Geneve tunnel, ใช้ใน **OpenStack**, OVN, บาง Kubernetes CNI
```bash
ovs-vsctl add-br br0
ovs-vsctl add-port br0 eno1
ovs-vsctl add-port br0 vm1-tap tag=20       # access VLAN 20
ovs-vsctl show ; ovs-ofctl dump-flows br0
```
**Proxmox VE** มี **SDN** (zones: VLAN, QinQ, VXLAN, EVPN) ให้จัดการผ่าน GUI

---

## 6. แยก Traffic ประเภทต่าง ๆ

| Traffic | VLAN ตัวอย่าง | หมายเหตุ |
|---|---|---|
| Management | 10 | เข้าถึงจาก admin เท่านั้น (Level 92 hardening) |
| vMotion/Live Migration | 11 | bandwidth สูง, ไม่ route ออกนอก (มัก non-routable) |
| Storage (iSCSI/NFS/vSAN/Ceph) | 12, 13 | **jumbo MTU**, latency ต่ำ, iSCSI ใช้ **multipathing** (2 subnet/2 NIC) ไม่ใช่ teaming |
| VM networks | 100+ | ตาม segment ของแอป/tenant |
| Backup | 14 | อาจแยก NIC |
| OOB (iDRAC/iLO) | แยก switch | |

**NIOC/QoS:** กำหนด share/reservation ไม่ให้ vMotion กิน bandwidth ของ storage/VM
**ความเร็ว:** ปัจจุบัน host ใช้ 2 × 25G ขึ้นไป (HCI นิยม 25/100G)

---

## 7. ประสิทธิภาพสูง: SR-IOV, DPDK, SmartNIC

| เทคโนโลยี | หลักการ | แลกกับ |
|---|---|---|
| **SR-IOV** | NIC จริงแบ่งเป็น **Virtual Function (VF)** ส่งให้ VM ตรง ข้าม vSwitch → latency ต่ำ throughput สูง | vMotion/ฟีเจอร์ vSwitch ใช้ไม่ได้/จำกัด, firewall ของ vSwitch ไม่เห็น |
| **DPDK** | ประมวลผล packet ใน user space แบบ poll (OVS-DPDK, virtual router/firewall ของ telco — NFV) | ใช้ CPU core เฉพาะ |
| **SmartNIC/DPU** (NVIDIA BlueField, AMD Pensando) | ย้ายงาน vSwitch/firewall/encryption ไปบน NIC | ราคา/ระบบนิเวศ |
| **RDMA (RoCE/iWARP)** | storage/AI ส่งข้อมูลตรงระหว่าง memory | ต้องตั้ง lossless (PFC/ECN) — Level 98 |

---

## 8. Network Virtualization: VMware NSX (และทางเลือก)

**NSX** = overlay (**Geneve**) + distributed routing + **distributed firewall (DFW)** ใน hypervisor
- **Micro-segmentation:** firewall อยู่ที่ vNIC ของทุก VM → ควบคุม east-west ระหว่าง VM แม้อยู่ subnet เดียวกัน (Level 67)
- นโยบายผูกกับ **tag/กลุ่ม** (เช่น "Web-PROD") ไม่ใช่ IP → VM ย้าย/สร้างใหม่ได้นโยบายตาม
- Edge node ทำ north-south routing, NAT, LB, VPN
- ทางเลือก/คล้ายกัน: Cisco ACI, OpenStack Neutron/OVN, Nutanix Flow, Proxmox SDN + firewall, Kubernetes network policy (บทถัดไป)

---

## 9. Troubleshooting

| อาการ | สาเหตุที่พบบ่อย |
|---|---|
| VM ใหม่ไม่ได้ IP/ping gateway ไม่ได้ | port group VLAN ผิด, VLAN ไม่อยู่ใน allowed list ของ trunk ที่ switch, VLAN ไม่มีใน switch |
| Host หลุดเป็นระยะ/MAC flapping | teaming policy ไม่ตรงกับ port-channel ของ switch |
| vMotion ล้มเหลว | vmk vMotion คนละ subnet/VLAN, MTU ไม่ตรง, port group ชื่อไม่เหมือนกัน (vSS) |
| Storage ช้า/หลุด | MTU jumbo ไม่ครบทุก hop, ไม่มี multipathing, NIC shared กับ vMotion โดยไม่มี QoS |
| VM บน host เดียวกันคุยได้แต่ข้าม host ไม่ได้ | ปัญหาที่ uplink/switch จริง (VLAN/trunk) |
| Nested/virtual appliance ไม่ทำงาน | ต้องเปิด promiscuous/forged transmits (หรือ MAC learning) |

```
# ESXi
esxcli network nic list
esxcli network vswitch standard list
esxcli network vswitch dvs vmware list
esxcli network ip interface ipv4 get
vmkping -I vmk1 -d -s 8972 10.0.11.22      # ทดสอบ jumbo บน vmk (-d = DF)
# ดู CDP/LLDP ว่า vmnic ต่ออยู่กับ port ไหนของ switch (ใน vCenter หรือ esxcli)
```

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| ต้องทำ port-channel กับทุก host เพื่อใช้ 2 uplink | ค่าเริ่มต้น (originating port) ใช้ trunk ธรรมดา ไม่ต้อง port-channel — ต้องตั้งให้ตรงกันสองฝั่ง |
| VM ใน host เดียวกันคุยกันผ่าน switch จริง | คุยกันใน vSwitch ไม่ออก NIC |
| iSCSI ใช้ NIC teaming ได้ประสิทธิภาพดีสุด | ใช้ multipathing (port binding/MPIO) |
| SR-IOV ดีกว่าทุกกรณี | เสีย vMotion/ฟีเจอร์ vSwitch/การมองเห็น |
| vSwitch ต้องรัน STP | ไม่รัน — ไม่ forward ระหว่าง uplink จึงไม่เกิด loop |

---

## 11. Cheat Sheet

```
vSwitch เชื่อม vNIC ↔ NIC จริง · uplink = 802.1Q trunk · edge trunk + jumbo ที่ switch
VMware: vSS (ต่อ host) vs vDS (vCenter, LACP, NetFlow, LBT) · port group = VLAN (VST)
vmk: mgmt · vMotion · storage (iSCSI/NFS/vSAN)
Teaming: originating port/LBT → trunk ธรรมดา · IP hash → static EtherChannel · LACP → active
Hyper-V: External/Internal/Private · SET · host vNIC + VLAN
Linux: bridge vlan-aware + bond 802.3ad · OVS (OpenFlow, tunnel) · Proxmox SDN
แยก traffic ด้วย VLAN + NIOC · storage = jumbo + multipath
SR-IOV/DPDK/SmartNIC/RDMA เพื่อประสิทธิภาพ · NSX = overlay + DFW micro-segmentation
vmkping -d -s 8972 · esxcli network ...
```

---

## 12. แบบทดสอบ 10 ข้อ

1. VM 2 ตัวบน host เดียวกัน VLAN เดียวกัน traffic ออกไป switch จริงไหม
2. vSS กับ vDS ต่างกันอย่างไร
3. Port group VLAN 4095 ใน vSphere หมายถึงอะไร
4. ถ้าใช้ teaming "Route based on originating virtual port" ฝั่ง switch ควรตั้งอย่างไร
5. อาการเมื่อ teaming ของ vSwitch ไม่ตรงกับ port-channel ของ switch
6. VMkernel adapter ใช้ทำอะไร ยกตัวอย่าง 3 ประเภท
7. ทำไม iSCSI ควรใช้ multipathing แทน NIC teaming
8. คำสั่งทดสอบ jumbo frame บน vmk ของ ESXi
9. SR-IOV ให้ประโยชน์อะไร และเสียอะไร
10. Micro-segmentation ใน NSX ต่างจาก firewall แบบเดิมอย่างไร

<details><summary><b>เฉลย</b></summary>

1. ไม่ — คุยกันภายใน vSwitch ในหน่วยความจำ
2. vSS ตั้งค่าทีละ host; vDS จัดการจาก vCenter ใช้ร่วมทุก host และมีฟีเจอร์มากกว่า (LACP, NetFlow, LBT, mirroring)
3. ส่ง VLAN tag เข้า VM (VGT) ให้ VM จัดการ VLAN เอง
4. Trunk ธรรมดา (ไม่ทำ port-channel) ตั้ง edge trunk/PortFast และ allowed VLAN ให้ครบ
5. MAC flapping, packet loss, host/VM หลุดเป็นระยะ
6. Interface ของ hypervisor เอง เช่น management, vMotion, storage (iSCSI/NFS/vSAN), FT, replication
7. Multipathing ใช้ทุกเส้นทางพร้อมกันและ failover ที่ระดับ storage ได้ถูกต้อง teaming กระจายต่อ flow/VM ทำให้ไม่ได้ประโยชน์เต็มที่
8. `vmkping -I vmk1 -d -s 8972 <IP ปลายทาง>`
9. Latency ต่ำ/throughput สูงเพราะข้าม vSwitch — แต่เสีย vMotion, ฟีเจอร์และ visibility/firewall ของ vSwitch
10. Firewall อยู่ที่ vNIC ของทุก VM ควบคุม east-west ได้แม้ใน subnet เดียวกัน และนโยบายผูกกับ tag/กลุ่ม ไม่ใช่ IP
</details>

---

➡️ ต่อไป: **Level 76 — Container Networking (Docker)**
