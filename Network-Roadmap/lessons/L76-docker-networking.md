# บทเรียน Level 76 — Container Networking (Docker) (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจพื้นฐาน Linux ที่อยู่เบื้องหลัง container (network namespace, veth, bridge, iptables) · network driver ของ Docker (bridge, host, none, macvlan/ipvlan, overlay) · port publishing · DNS ระหว่าง container · Docker Compose network · ปัญหาที่พบบ่อยในองค์กร (ชน IP subnet, firewall bypass) · troubleshooting

---

## 1. Container ต่างจาก VM อย่างไร (ในมุม network)

| | VM | Container |
|---|---|---|
| แยกด้วย | hypervisor (OS แยกกัน) | **kernel เดียวกัน** แยกด้วย namespaces/cgroups |
| network | vNIC + vSwitch | **network namespace + veth pair + bridge** |
| เริ่มทำงาน | นาที | วินาที |
| IP | มักคงที่ | **เปลี่ยนทุกครั้งที่สร้างใหม่** → ต้องอ้างอิงด้วยชื่อ (DNS) |

---

## 2. พื้นฐาน Linux ที่ทำให้ Container มี Network

### Network Namespace
"สำเนาแยก" ของ network stack — interface, route table, iptables, port ของตัวเอง
```bash
sudo ip netns add red                      # สร้าง namespace
sudo ip netns exec red ip addr             # มีแค่ lo
```
### veth pair — "สายแลนเสมือน" สองปลาย
```bash
sudo ip link add veth-red type veth peer name veth-red-br
sudo ip link set veth-red netns red        # ปลายหนึ่งเข้า namespace
```
### Bridge — "switch เสมือน" ใน host
```bash
sudo ip link add br0 type bridge && sudo ip link set br0 up
sudo ip link set veth-red-br master br0 && sudo ip link set veth-red-br up
sudo ip netns exec red ip addr add 172.30.0.2/24 dev veth-red
sudo ip netns exec red ip link set veth-red up
sudo ip addr add 172.30.0.1/24 dev br0     # host เป็น gateway
sudo ip netns exec red ping 172.30.0.1
```
**นี่คือสิ่งที่ Docker ทำให้อัตโนมัติ** + iptables NAT/forwarding

```
 ┌──────────────── Docker host ─────────────────────────────┐
 │ [container A ns] eth0 172.17.0.2 ─veth─┐                  │
 │ [container B ns] eth0 172.17.0.3 ─veth─┤ docker0 (bridge) │
 │                                        │  172.17.0.1      │
 │                     iptables MASQUERADE│/DNAT             │
 │                                   eth0 (host) 10.0.5.20 ──┼──► LAN
 └───────────────────────────────────────────────────────────┘
```

---

## 3. Network Drivers ของ Docker

| Driver | การทำงาน | ใช้เมื่อ |
|---|---|---|
| **bridge (default `docker0`)** | container อยู่ใน subnet ภายใน (172.17.0.0/16) ออกนอกด้วย NAT | ทดสอบเร็ว ๆ (ไม่มี DNS ระหว่างชื่อ) |
| **bridge แบบ user-defined** ⭐ | สร้างเอง: **มี DNS ตามชื่อ container**, แยกกลุ่มกัน | **แนะนำสำหรับแอปทั่วไป** |
| **host** | ใช้ network stack ของ host ตรง ไม่มีการแยก/NAT | ต้องการประสิทธิภาพสูงสุด, monitoring agent |
| **none** | ไม่มี network (มีแค่ lo) | งาน batch ที่ไม่ต้องใช้ network |
| **macvlan** | container มี **MAC/IP บน LAN จริง** เหมือนเครื่องจริง | แอปต้องอยู่บน LAN (legacy, IoT) — host คุยกับ container ตรง ๆ ไม่ได้โดยค่าเริ่มต้น |
| **ipvlan** (L2/L3) | คล้าย macvlan แต่ใช้ MAC ของ host | switch จำกัดจำนวน MAC ต่อพอร์ต |
| **overlay** | VXLAN ข้ามหลาย host (Docker Swarm) | cluster หลาย host (ปัจจุบันนิยม Kubernetes) |

```bash
docker network ls
docker network create --driver bridge --subnet 172.30.10.0/24 app-net
docker run -d --name db  --network app-net postgres:16
docker run -d --name web --network app-net -p 8080:80 nginx
docker exec web getent hosts db             # → 172.30.10.2 (DNS ของ Docker ที่ 127.0.0.11)
docker network inspect app-net
```

---

## 4. Port Publishing (`-p`)

```bash
docker run -d -p 8080:80 nginx              # host:8080 → container:80 บนทุก IP ของ host
docker run -d -p 127.0.0.1:8080:80 nginx    # เฉพาะ localhost (ปลอดภัยกว่า)
docker run -d -p 10.0.5.20:443:443 app      # เฉพาะ IP นี้
```
- Docker สร้าง **DNAT rule ใน iptables** (chain `DOCKER`) ให้อัตโนมัติ
- ⚠️ **กับดักด้าน security:** rule ของ Docker ถูกประมวลผล **ก่อน** rule ของ UFW/firewalld ทั่วไป → port ที่ publish **เปิดสู่ภายนอกแม้ UFW จะ deny**
  - แก้: bind กับ `127.0.0.1` หรือ IP ภายใน, ใส่ rule ใน chain **`DOCKER-USER`**, ใช้ reverse proxy หน้า container, firewall ภายนอก host
```bash
# อนุญาตเฉพาะ LAN ภายในเข้า port ที่ publish
sudo iptables -I DOCKER-USER -i eth0 ! -s 10.0.0.0/8 -j DROP
sudo iptables -L DOCKER-USER -n -v ; sudo iptables -t nat -L DOCKER -n
```

---

## 5. Docker Compose Network

Compose สร้าง **user-defined network ให้ทุก project อัตโนมัติ** — service เรียกกันด้วย **ชื่อ service**
```yaml
# compose.yaml — แยก frontend/backend
services:
  proxy:
    image: nginx:1.27
    ports: ["443:443"]
    networks: [frontend]
  app:
    image: myapp:1.4
    environment:
      DB_HOST: db                    # อ้างอิงด้วยชื่อ ไม่ใช่ IP
    networks: [frontend, backend]
  db:
    image: postgres:16
    networks: [backend]              # proxy เข้า db ไม่ได้
    volumes: [dbdata:/var/lib/postgresql/data]
networks:
  frontend:
  backend:
    internal: true                   # ไม่มีทางออกอินเทอร์เน็ต
volumes:
  dbdata:
```
หลักการ: **แบ่ง network ตาม tier** (เหมือน DMZ/app/db ในบทที่ 67), publish เฉพาะ port ของ proxy

---

## 6. ปัญหาที่พบบ่อยในองค์กร

### ① Subnet ของ Docker ชนกับเครือข่ายองค์กร
Docker ใช้ **172.17.0.0/16** และ 172.18–31.x สำหรับ network ใหม่ → ถ้าองค์กร/VPN ใช้ 172.16.0.0/12 → **host เข้าถึงเครือข่ายนั้นไม่ได้** (route ไปที่ bridge ของ Docker แทน)
```json
// /etc/docker/daemon.json
{
  "bip": "10.200.0.1/24",
  "default-address-pools": [ { "base": "10.201.0.0/16", "size": 24 } ]
}
```
→ ตกลง **IP plan สำหรับ container** กับทีม network ก่อน (Level 9/10)

### ② MTU
host อยู่หลัง VPN/overlay ที่ MTU < 1500 แต่ docker0 = 1500 → pull image/HTTPS ค้าง → ตั้ง `"mtu": 1400` ใน daemon.json (หรือต่อ network)

### ③ Proxy ขององค์กร
Docker daemon pull image ผ่าน proxy ต้องตั้งใน systemd (`HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`) และ SSL inspection ต้องติดตั้ง CA ขององค์กร

### ④ DNS
container ใช้ DNS ของ host (หรือ 127.0.0.11 ใน user-defined network) → ถ้า host ใช้ `127.0.0.53` (systemd-resolved) Docker จะใช้ fallback → ตั้ง `"dns": ["10.0.0.53"]` ให้ชี้ DNS ภายในองค์กร

### ⑤ IP ของ client ที่แอปเห็น
ผ่าน port publish (userland proxy) แอปอาจเห็น IP ของ gateway แทน → ใช้ reverse proxy + X-Forwarded-For

---

## 7. Troubleshooting

```bash
docker network inspect app-net                       # subnet, container ที่อยู่ใน network
docker inspect -f '{{json .NetworkSettings.Networks}}' web
docker exec -it web sh -c "ip addr; ip route; cat /etc/resolv.conf"
# image ไม่มีเครื่องมือ → ใช้ container debug ที่แชร์ namespace
docker run --rm -it --network container:web nicolaka/netshoot
#   ภายใน: ping db, dig db, curl -v http://db:5432, tcpdump -i eth0, ss -tlnp
sudo iptables -t nat -L -n -v | grep -i docker
ip link show type bridge ; bridge link
sudo nsenter -t $(docker inspect -f '{{.State.Pid}}' web) -n ss -tlnp   # ดู port ใน namespace
```

| อาการ | ตรวจ |
|---|---|
| container เรียกกันด้วยชื่อไม่ได้ | อยู่ใน default bridge (ไม่มี DNS) → ใช้ user-defined network; อยู่คนละ network |
| เข้าจากภายนอกไม่ได้ | ไม่ได้ `-p`, แอปฟังที่ `127.0.0.1` ในตัว container (ต้องฟัง `0.0.0.0`), firewall ภายนอก |
| port เปิดสู่ภายนอกทั้งที่ไม่ต้องการ | bind 127.0.0.1/DOCKER-USER |
| host เข้า LAN/VPN บางส่วนไม่ได้หลังติดตั้ง Docker | subnet ชน |
| pull image/HTTPS ค้าง | MTU, proxy, CA |

---

## 8. Container Security (มุม network)

- ใช้ **user-defined network แยกตาม tier**, `internal: true` สำหรับ backend
- **อย่า publish port ฐานข้อมูล/admin** สู่ภายนอก
- จำกัด egress (allowlist ออกอินเทอร์เน็ตผ่าน proxy)
- หลีกเลี่ยง `--network host` และ `--privileged` เว้นแต่จำเป็น
- ใช้ image ที่เชื่อถือได้และสแกนช่องโหว่ (Trivy/Grype)

---

## 9. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| ควรอ้างอิง container ด้วย IP | IP เปลี่ยนเสมอ — ใช้ชื่อ (DNS ใน user-defined network) |
| UFW deny แล้ว port ของ Docker ปิด | Docker NAT rule มาก่อน — ใช้ DOCKER-USER/bind IP |
| default bridge มี DNS ตามชื่อ | เฉพาะ user-defined network |
| macvlan: host คุยกับ container ได้ปกติ | โดยค่าเริ่มต้น host ↔ macvlan container คุยกันตรงไม่ได้ |
| Docker subnet ไม่กระทบเครือข่ายองค์กร | 172.17+ อาจชนกับ VPN/LAN ทำให้เข้าไม่ได้ |

---

## 10. Cheat Sheet

```
Container net = network namespace + veth pair + bridge (docker0) + iptables NAT
Drivers: bridge (default/user-defined ⭐ มี DNS) · host · none · macvlan/ipvlan · overlay
docker network create/ls/inspect · --network · -p [IP:]host:container
Compose: network ต่อ project, ชื่อ service = DNS, แยก frontend/backend, internal: true
กับดัก: publish ข้าม UFW → DOCKER-USER / bind 127.0.0.1
daemon.json: bip, default-address-pools (กันชน 172.16/12), mtu, dns
Debug: netshoot --network container:<name> · nsenter · iptables -t nat -L
```

---

## 11. แบบทดสอบ 10 ข้อ

1. Network namespace คืออะไร
2. veth pair ทำหน้าที่อะไรใน container networking
3. ทำไมควรใช้ user-defined bridge แทน default bridge
4. `-p 127.0.0.1:8080:80` ต่างจาก `-p 8080:80` อย่างไร
5. ทำไม port ที่ publish ด้วย Docker ยังเข้าได้แม้ UFW deny และแก้อย่างไร
6. macvlan เหมาะกับงานแบบใด มีข้อจำกัดอะไร
7. หลังติดตั้ง Docker host เข้า VPN 172.18.0.0/16 ไม่ได้ เพราะอะไร แก้อย่างไร
8. ใน Compose ทำไม app เรียก database ด้วย `db` ได้
9. `internal: true` ใน Compose network ทำอะไร
10. Image ไม่มี ping/curl จะ debug network ของ container ได้อย่างไร

<details><summary><b>เฉลย</b></summary>

1. Network stack แยก (interface, route, iptables, port) สำหรับแต่ละ container
2. เป็นสายเสมือนสองปลาย — ปลายหนึ่งอยู่ใน container อีกปลายต่อกับ bridge บน host
3. มี DNS ตามชื่อ container และแยกกลุ่ม container ได้
4. แบบแรก bind เฉพาะ localhost (เข้าจากภายนอกไม่ได้); แบบหลังเปิดทุก IP ของ host
5. Docker ใส่ DNAT/forward rule ที่ประมวลผลก่อน UFW — แก้ด้วย DOCKER-USER chain, bind IP เฉพาะ, firewall ภายนอก/reverse proxy
6. Container ต้องมี IP บน LAN จริง (legacy/IoT) — host คุยกับ container ตรงไม่ได้โดยค่าเริ่มต้น, switch ต้องรับหลาย MAC
7. Docker สร้าง bridge ใน 172.18.0.0/16 ทำให้ route ชน — เปลี่ยน bip/default-address-pools ใน daemon.json
8. Compose สร้าง user-defined network และ DNS ภายในของ Docker แปลชื่อ service เป็น IP
9. Network นั้นไม่มีทางออกภายนอก (container ในนั้นคุยกันเองได้เท่านั้น)
10. รัน container debug (เช่น netshoot) ด้วย `--network container:<name>` หรือใช้ nsenter เข้า namespace
</details>

---

➡️ ต่อไป: **Level 77 — Kubernetes Networking**
