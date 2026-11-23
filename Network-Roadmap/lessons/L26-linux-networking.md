# บทเรียน Level 26 — Linux Networking Configuration (ฉบับละเอียด)

> อ่านจบแล้วจะ: ตั้ง IP/route/DNS แบบถาวรบน Linux ได้ (Netplan, NetworkManager) · ทำ VLAN, bonding, bridge · เปิด IP forwarding ให้ Linux เป็น router · ใช้ network namespace ทำ lab · policy-based routing

---

## 1. ทำไม Network Engineer ต้องรู้ Linux

- **Server, VM, container, cloud** ส่วนใหญ่เป็น Linux
- **อุปกรณ์เครือข่ายจำนวนมากใช้ Linux** อยู่ข้างใน (Arista EOS, Cumulus/SONiC, FortiOS พื้นฐาน, VyOS, pfSense ใช้ FreeBSD)
- เครื่องมือ automation/monitoring เกือบทั้งหมดรันบน Linux
- ใช้ทำ lab ได้ฟรี (router, firewall, DNS, DHCP)

---

## 2. แนวคิดสำคัญ: ชั่วคราว vs ถาวร

| | คำสั่ง `ip ...` | ไฟล์ config (Netplan/NetworkManager) |
|---|---|---|
| ผล | ทันที | ทันทีเมื่อ apply |
| หลัง reboot | **หายไป** | **คงอยู่** |
| ใช้เมื่อ | ทดสอบ แก้ปัญหาเฉพาะหน้า | ตั้งค่าจริง |

### ตั้งค่าชั่วคราวด้วยคำสั่ง ip
```bash
sudo ip addr add 192.168.50.10/24 dev eth1     # เพิ่ม IP
sudo ip addr del 192.168.50.10/24 dev eth1     # ลบ IP
sudo ip link set eth1 up                       # เปิด interface
sudo ip route add default via 192.168.50.1     # default gateway
sudo ip route add 10.20.0.0/16 via 192.168.50.254   # static route
sudo ip link set eth1 mtu 9000                 # MTU
```

---

## 3. ระบบจัดการเครือข่ายแต่ละ distro

| ระบบ | ใช้บน | ไฟล์/คำสั่ง |
|---|---|---|
| **Netplan** (เป็น front-end ที่สร้าง config ให้ networkd หรือ NetworkManager) | **Ubuntu** 18.04+ | `/etc/netplan/*.yaml` → `netplan try` / `netplan apply` |
| **NetworkManager** | RHEL/Rocky/Alma/Fedora, Ubuntu Desktop | `nmcli`, `nmtui` |
| **systemd-networkd** | distro minimal, container host | `/etc/systemd/network/*.network` |
| ifupdown | Debian (รุ่นเก่า/ทั่วไป) | `/etc/network/interfaces` |

---

## 4. Netplan (Ubuntu)

```yaml
# /etc/netplan/01-netcfg.yaml   (YAML: ใช้ space เท่านั้น ห้าม tab, ระวังการเยื้อง)
network:
  version: 2
  renderer: networkd
  ethernets:
    ens3:
      dhcp4: false
      addresses: [10.0.0.10/24]
      routes:
        - to: default
          via: 10.0.0.1
        - to: 172.16.0.0/12
          via: 10.0.0.254
      nameservers:
        addresses: [10.0.0.53, 1.1.1.1]
        search: [corp.local]
    ens4:
      dhcp4: true
```
```bash
sudo netplan try        # ทดสอบ: ถ้าไม่กด Enter ภายใน 120 วินาทีจะย้อนกลับเอง (ปลอดภัยเมื่อทำผ่าน SSH!)
sudo netplan apply
sudo chmod 600 /etc/netplan/*.yaml
```

## 5. NetworkManager (nmcli)

```bash
nmcli device status
nmcli connection show
# ตั้ง static
sudo nmcli con mod "System eth0" ipv4.method manual \
  ipv4.addresses 10.0.0.10/24 ipv4.gateway 10.0.0.1 \
  ipv4.dns "10.0.0.53 1.1.1.1" ipv4.dns-search corp.local
sudo nmcli con up "System eth0"
# กลับไปใช้ DHCP
sudo nmcli con mod "System eth0" ipv4.method auto
# เพิ่ม route
sudo nmcli con mod "System eth0" +ipv4.routes "172.16.0.0/12 10.0.0.254"
```
`nmtui` = เมนูแบบข้อความ ใช้ง่ายสำหรับมือใหม่

---

## 6. DNS บน Linux

- `/etc/resolv.conf` — ไฟล์ที่โปรแกรมใช้อ่าน DNS server **แต่บน distro สมัยใหม่ถูกสร้างอัตโนมัติ** (โดย systemd-resolved หรือ NetworkManager) แก้ด้วยมือแล้วจะหายเมื่อ reboot หรือ renew DHCP → ต้องตั้งผ่าน Netplan/nmcli
- **systemd-resolved:** `resolv.conf` มักชี้ไป `127.0.0.53` (stub resolver)
  ```bash
  resolvectl status           # DNS ที่ใช้จริงแต่ละ interface
  resolvectl query example.com
  ```
- `/etc/hosts` — กำหนดชื่อ→IP เองแบบ local (ถูกตรวจก่อน DNS ตาม `/etc/nsswitch.conf`)
- `hostnamectl set-hostname web01`

---

## 7. VLAN บน Linux (802.1Q)

ให้ server เดียวอยู่หลาย VLAN ผ่าน trunk port

```bash
# ชั่วคราว
sudo ip link add link eth0 name eth0.20 type vlan id 20
sudo ip addr add 10.20.0.10/24 dev eth0.20
sudo ip link set eth0.20 up
```
```yaml
# Netplan
  vlans:
    vlan20:
      id: 20
      link: ens3
      addresses: [10.20.0.10/24]
```
พอร์ต switch ฝั่งตรงข้ามต้องเป็น **trunk** ที่อนุญาต VLAN 20

---

## 8. Bonding (Link Aggregation / NIC Teaming)

รวมหลาย NIC เป็นหนึ่งเพื่อ **สำรอง (redundancy)** และ/หรือ **เพิ่ม bandwidth**

| Mode | ชื่อ | ต้องตั้ง switch? | ใช้เมื่อ |
|---|---|---|---|
| **1** | **active-backup** | ไม่ต้อง | ต้องการสำรองอย่างเดียว ใช้ได้กับ switch ทุกแบบ (ปลอดภัยที่สุด) |
| **4** | **802.3ad (LACP)** | **ต้องตั้ง LACP** (port-channel) | ต้องการทั้งสำรองและ bandwidth รวม |
| 0 | balance-rr | ต้อง (static) | ไม่ค่อยใช้ (packet อาจสลับลำดับ) |
| 6 | balance-alb | ไม่ต้อง | ทางเลือกเมื่อ switch ไม่รองรับ LACP |

```yaml
# Netplan: bond LACP
  ethernets:
    ens3: {}
    ens4: {}
  bonds:
    bond0:
      interfaces: [ens3, ens4]
      addresses: [10.0.0.10/24]
      routes: [{to: default, via: 10.0.0.1}]
      parameters:
        mode: 802.3ad
        lacp-rate: fast
        mii-monitor-interval: 100
        transmit-hash-policy: layer3+4
```
```bash
cat /proc/net/bonding/bond0       # ดูสถานะ: slave ไหน up, LACP partner
```

---

## 9. Bridge — สวิตช์เสมือนใน Linux

ใช้กับ **VM (KVM/Proxmox) และ container** ให้ VM เชื่อมเข้าเครือข่ายจริงเหมือนเสียบ switch

```bash
sudo ip link add br0 type bridge
sudo ip link set eth1 master br0
sudo ip link set br0 up
bridge link show
```
Proxmox ตั้ง `vmbr0` ให้อัตโนมัติ; bridge แบบ **VLAN-aware** ให้ VM แต่ละตัวอยู่คนละ VLAN ได้

---

## 10. Linux เป็น Router / NAT Gateway

```bash
# 1) เปิด IP forwarding (ถาวร)
echo 'net.ipv4.ip_forward=1' | sudo tee /etc/sysctl.d/99-forward.conf
sudo sysctl --system
# 2) NAT ขาออก (nftables) — ดู Level 17
sudo nft add table ip nat
sudo nft add chain ip nat postrouting '{ type nat hook postrouting priority 100; }'
sudo nft add rule ip nat postrouting oifname "eth0" masquerade
# 3) แจก IP ให้ LAN ด้วย dnsmasq (ดู Level 15)
```
> ⚠️ ค่าเริ่มต้นของ Linux **ไม่ forward packet** ระหว่าง interface — ลืมข้อ 1 คือสาเหตุอันดับหนึ่งที่ "ทำ Linux router แล้วไม่ทำงาน"

---

## 11. Network Namespace — สร้างหลายเครื่องจำลองบนเครื่องเดียว

แต่ละ namespace มี interface, routing table, firewall แยกกัน (เป็นพื้นฐานของ container)

```bash
sudo ip netns add red
sudo ip netns add blue
sudo ip link add veth-red type veth peer name veth-blue      # "สาย" เสมือน 2 ปลาย
sudo ip link set veth-red netns red
sudo ip link set veth-blue netns blue
sudo ip netns exec red  ip addr add 10.99.0.1/24 dev veth-red
sudo ip netns exec blue ip addr add 10.99.0.2/24 dev veth-blue
sudo ip netns exec red  ip link set veth-red up
sudo ip netns exec blue ip link set veth-blue up
sudo ip netns exec red  ping -c 2 10.99.0.2                  # ✅ สองเครื่องจำลองคุยกัน
```
ใช้ทำ lab routing (เพิ่ม namespace เป็น router + เปิด forwarding) ได้โดยไม่ต้องมี VM

---

## 12. Policy-Based Routing (เลือกเส้นทางตามต้นทาง)

ปกติ route เลือกจาก **ปลายทาง** เท่านั้น PBR ให้เลือกตาม **ต้นทาง** หรือเงื่อนไขอื่น เช่น server มี 2 ISP และต้องตอบกลับออก ISP เดียวกับที่ traffic เข้ามา

```bash
echo "100 isp2" | sudo tee -a /etc/iproute2/rt_tables
sudo ip route add default via 203.0.113.1 dev eth2 table isp2
sudo ip rule add from 203.0.113.10 table isp2       # traffic ที่ source เป็น IP ขา ISP2 ใช้ตาราง isp2
ip rule show ; ip route show table isp2
```

---

## 13. Firewall บน Linux (ภาพรวม)

- **nftables** (มาตรฐานปัจจุบัน) แทน iptables
- front-end: **ufw** (Ubuntu), **firewalld** (RHEL: `firewall-cmd --add-service=https --permanent`)
- ตรวจปัญหา "เข้า port ไม่ได้" อย่าลืมตรวจ firewall ในตัว server ด้วย: `sudo nft list ruleset`, `sudo ufw status`, `sudo firewall-cmd --list-all`

---

## 14. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| ตั้งด้วย `ip addr add` แล้วถาวร | หายเมื่อ reboot ต้องตั้งใน Netplan/NetworkManager |
| แก้ /etc/resolv.conf โดยตรงก็พอ | มักถูกเขียนทับ ตั้งผ่านตัวจัดการเครือข่าย |
| bond mode 4 ใช้ได้โดยไม่ต้องตั้ง switch | ต้องตั้ง LACP ที่ switch ด้วย |
| Linux forward packet เองเมื่อมี 2 interface | ต้องเปิด ip_forward |
| netplan apply ผ่าน SSH ปลอดภัย | ใช้ `netplan try` เพื่อให้ย้อนกลับได้ถ้าหลุด |

---

## 15. Cheat Sheet

```
ชั่วคราว: ip addr add/del · ip link set up/down · ip route add · ip link set mtu
ถาวร Ubuntu: /etc/netplan/*.yaml → netplan try → netplan apply
ถาวร RHEL: nmcli con mod ... ipv4.method manual ipv4.addresses ... → nmcli con up
DNS: resolvectl status · อย่าแก้ resolv.conf ตรง · /etc/hosts
VLAN: ip link add link eth0 name eth0.20 type vlan id 20
Bond: mode 1 active-backup (ไม่ต้องตั้ง switch) · mode 4 LACP (ต้องตั้ง) · /proc/net/bonding/bond0
Bridge: ip link add br0 type bridge · ip link set eth1 master br0
Router: net.ipv4.ip_forward=1 + nft masquerade
Lab: ip netns add · veth pair · ip netns exec
PBR: ip rule add from X table T
```

---

## 16. แบบทดสอบ 10 ข้อ

1. ทำไมค่าที่ตั้งด้วยคำสั่ง `ip` หายหลัง reboot และแก้อย่างไร
2. `netplan try` ต่างจาก `netplan apply` อย่างไร ทำไมควรใช้เมื่อทำผ่าน SSH
3. คำสั่ง nmcli ตั้ง IP 10.0.0.20/24 gateway 10.0.0.1 ให้ connection ชื่อ eth0
4. ทำไมแก้ /etc/resolv.conf แล้วค่าหายไป
5. คำสั่งสร้าง VLAN 30 บน eth0 แบบชั่วคราว
6. bond mode 1 กับ mode 4 ต่างกันอย่างไร
7. ทำ Linux เป็น router แล้ว client ping ข้ามวงไม่ได้ สิ่งแรกที่ควรตรวจคืออะไร
8. Network namespace ใช้ทำอะไร
9. veth pair คืออะไร
10. ยกตัวอย่างสถานการณ์ที่ต้องใช้ policy-based routing

<details><summary><b>เฉลย</b></summary>

1. คำสั่ง `ip` แก้เฉพาะ kernel ขณะนั้น — ต้องตั้งในไฟล์ config ของ Netplan/NetworkManager/networkd
2. `try` ใช้ค่าใหม่ชั่วคราวและย้อนกลับเองถ้าไม่ยืนยันภายในเวลา; ป้องกันการตัดตัวเองออกจาก SSH
3. `sudo nmcli con mod eth0 ipv4.method manual ipv4.addresses 10.0.0.20/24 ipv4.gateway 10.0.0.1` แล้ว `sudo nmcli con up eth0`
4. ไฟล์ถูกสร้างอัตโนมัติโดย systemd-resolved/NetworkManager
5. `sudo ip link add link eth0 name eth0.30 type vlan id 30`
6. Mode 1 = สำรองอย่างเดียว ไม่ต้องตั้ง switch; Mode 4 = LACP ได้ทั้งสำรองและ bandwidth รวม ต้องตั้ง LACP ที่ switch
7. `net.ipv4.ip_forward` เปิดหรือยัง (และ route/firewall/NAT)
8. แยก network stack ทำให้จำลองหลายเครื่อง/router บนเครื่องเดียว และเป็นพื้นฐานของ container
9. คู่ interface เสมือนที่เชื่อมกันเหมือนสาย ส่งเข้าปลายหนึ่งออกอีกปลาย
10. Server มี 2 ISP ต้องตอบกลับออก ISP เดียวกับที่ traffic เข้ามา หรือให้แต่ละ subnet ออก ISP ต่างกัน
</details>

---

➡️ ต่อไป: **Level 27 — Windows Networking & PowerShell**
