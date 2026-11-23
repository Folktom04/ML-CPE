# Tier 8 — Data Center, Virtualization & Cloud Networking (Level 71–80)

> เป้าหมายของ Tier: ดูแลเครือข่ายของแอปสมัยใหม่ — load balancer, DC fabric, container, Kubernetes และ cloud

---

## Level 71 — Load Balancing

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L71-load-balancing.md](lessons/L71-load-balancing.md)

**สิ่งที่ต้องรู้**
- L4 (TCP/UDP) vs L7 (HTTP: path, header, cookie)
- Algorithm: round robin, least connections, weighted, IP hash, consistent hashing
- Health check (TCP/HTTP), session persistence (sticky), SSL offload/termination/re-encryption
- SNAT vs DSR (Direct Server Return), X-Forwarded-For / PROXY protocol
- เครื่องมือ: HAProxy, Nginx, Envoy, F5 BIG-IP, Citrix ADC, Cloud LB (ALB/NLB)
- GSLB (DNS-based) ข้าม data center

```
frontend web
  bind *:443 ssl crt /etc/haproxy/site.pem
  default_backend app
backend app
  balance leastconn
  option httpchk GET /health
  server a1 10.0.1.11:8080 check
  server a2 10.0.1.12:8080 check
```

**แบบทดสอบ**
1. L4 vs L7 LB เลือกใช้เมื่อไร
2. Backend เห็น IP ของ LB แทน client แก้อย่างไร
3. Sticky session มีข้อเสียอะไร
4. DSR ข้อดีคืออะไร
5. Health check ที่ดีควรตรวจอะไร

<details><summary>เฉลย</summary>

1. L4: เร็ว ไม่ใช่ HTTP (DB, game); L7: routing ตาม path/host, WAF, header
2. X-Forwarded-For (HTTP) หรือ PROXY protocol (L4)
3. โหลดไม่สมดุล, server ล่มแล้ว session หาย
4. traffic ขากลับไม่ผ่าน LB → รองรับ throughput สูง
5. endpoint ที่สะท้อนสุขภาพจริงของแอป (รวม dependency สำคัญ) ไม่ใช่แค่ port เปิด
</details>

**5 โปรเจค**
- ⭐ P1: HAProxy + 3 web container + health check
- ⭐⭐ P2: Nginx reverse proxy + TLS termination + rate limit
- ⭐⭐ P3: Benchmark algorithm ต่าง ๆ ด้วย wrk/k6 ทำกราฟ
- ⭐⭐ P4: Blue/green deployment ผ่าน LB (สลับ backend ไม่มี downtime)
- ⭐⭐⭐ P5: LB HA ด้วย keepalived (VRRP) + HAProxy 2 ตัว

---

## Level 72 — Proxy, Reverse Proxy, CDN & WAF

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L72-proxy-cdn-waf.md](lessons/L72-proxy-cdn-waf.md)

**สิ่งที่ต้องรู้**
- Forward proxy (Squid, explicit/transparent, PAC/WPAD) vs Reverse proxy
- Secure Web Gateway (URL filtering)
- CDN: edge cache, Anycast, cache-control headers, origin shielding
- WAF: OWASP Top 10, ModSecurity/Coraza, Cloudflare/AWS WAF
- Anycast routing

**แบบทดสอบ**
1. Forward vs Reverse proxy
2. PAC file คืออะไร
3. CDN ทำให้เว็บเร็วขึ้นอย่างไร
4. Anycast คืออะไร
5. WAF ป้องกันอะไรที่ firewall ทั่วไปป้องกันไม่ได้

<details><summary>เฉลย</summary>

1. Forward แทน client ออกไปข้างนอก; Reverse แทน server รับจากข้างนอก
2. JavaScript บอก browser ว่า URL ไหนใช้ proxy ไหน
3. cache ใกล้ผู้ใช้ ลด RTT, ลดโหลด origin
4. IP เดียวประกาศจากหลายที่ routing พาไปจุดที่ใกล้ที่สุด
5. การโจมตีระดับ HTTP เช่น SQL injection, XSS
</details>

**5 โปรเจค**
- ⭐ P1: Squid proxy + ACL block หมวดเว็บ
- ⭐⭐ P2: ใช้ Cloudflare (free) หน้าเว็บส่วนตัว + วัดก่อน/หลัง
- ⭐⭐ P3: ModSecurity + OWASP CRS หน้า DVWA (lab) ทดสอบการ block
- ⭐⭐ P4: Varnish/Nginx cache + วัด hit ratio
- ⭐⭐⭐ P5: Anycast lab: 2 node ประกาศ IP เดียวกันด้วย BGP (FRR) ดูการ failover

---

## Level 73 — Data Center Design: Spine-Leaf

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L73-dc-spine-leaf.md](lessons/L73-dc-spine-leaf.md)

**สิ่งที่ต้องรู้**
- 3-tier เดิม vs Clos/Spine-Leaf (ทุก leaf ต่อทุก spine, east-west traffic)
- L3 fabric (BGP unnumbered, eBGP per leaf — RFC 7938), ECMP
- Oversubscription, port density, 25/100/400G
- ToR vs EoR, Border leaf, Service leaf
- Power/cooling, rack layout, cabling (MPO), OOB management

**แบบทดสอบ**
1. ทำไม spine-leaf เหมาะกับ DC สมัยใหม่
2. ใน spine-leaf hop ระหว่าง server 2 ตัวคนละ leaf กี่ hop
3. Leaf ต่อ server 48×25G uplink 6×100G oversubscription
4. ทำไมใช้ eBGP ใน DC fabric
5. Border leaf ทำหน้าที่อะไร

<details><summary>เฉลย</summary>

1. Latency คาดเดาได้, ECMP, scale ด้วยการเพิ่ม spine/leaf, ไม่มี STP
2. leaf → spine → leaf (เท่ากันทุกคู่)
3. 1200/600 = 2:1
4. Simple, scale, policy ยืดหยุ่น, failure domain เล็ก
5. เชื่อม fabric กับภายนอก (WAN/Internet/firewall)
</details>

**5 โปรเจค**
- ⭐⭐ P1: Containerlab 2 spine + 4 leaf ด้วย FRR BGP unnumbered
- ⭐⭐ P2: ทดสอบ ECMP + ตัด spine วัดผล
- ⭐⭐ P3: ออกแบบ DC 20 rack (port count, oversubscription, BOM)
- ⭐⭐⭐ P4: Generate config fabric อัตโนมัติจาก YAML (Jinja2)
- ⭐⭐⭐ P5: Arista cEOS spine-leaf + Ansible deploy + automated test (ping mesh)

---

## Level 74 — VXLAN & EVPN

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L74-vxlan-evpn.md](lessons/L74-vxlan-evpn.md)

**สิ่งที่ต้องรู้**
- VXLAN: L2 over L3 (UDP 4789), VNI 24 บิต (16 ล้าน), VTEP
- Flood-and-learn vs BGP EVPN control plane
- EVPN route types: 2 (MAC/IP), 3 (IMET), 5 (IP prefix)
- Symmetric vs Asymmetric IRB, Distributed Anycast Gateway
- MTU: ต้องเพิ่ม underlay MTU (+50 byte), ARP suppression, multihoming (ESI)

**แบบทดสอบ**
1. VXLAN overhead ประมาณกี่ byte
2. ทำไมต้องมี EVPN แทน flood-and-learn
3. Route type 2 บรรจุอะไร
4. Anycast gateway คืออะไร
5. VNI มีกี่บิต

<details><summary>เฉลย</summary>

1. 50 byte (IPv4 underlay)
2. เรียน MAC/IP ผ่าน control plane ลด flooding, scale ดีกว่า, รองรับ multihoming
3. MAC (และ IP) ของ host + VNI
4. ทุก leaf มี gateway IP/MAC เดียวกัน → VM ย้ายไป leaf ไหนก็ได้
5. 24 บิต
</details>

**5 โปรเจค**
- ⭐⭐ P1: VXLAN static (Linux `ip link add vxlan`) เชื่อม 2 host
- ⭐⭐⭐ P2: EVPN-VXLAN บน FRR หรือ cEOS (L2VNI)
- ⭐⭐⭐ P3: เพิ่ม L3VNI symmetric IRB + anycast gateway
- ⭐⭐⭐ P4: Wireshark ดู VXLAN encap + EVPN route type
- ⭐⭐⭐ P5: Multi-tenant fabric 2 VRF + border leaf ออก firewall

---

## Level 75 — Virtualization Networking

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L75-virtualization-networking.md](lessons/L75-virtualization-networking.md)

**สิ่งที่ต้องรู้**
- vSwitch: VMware vSS/vDS, Hyper-V vSwitch, Linux bridge, Open vSwitch (OVS)
- Port group, VLAN tagging (VST/EST/VGT), NIC teaming policy
- veth pair, tap, macvlan/ipvlan, SR-IOV, DPDK
- Network namespace = พื้นฐานของ container
- vMotion network, storage network (iSCSI/NFS) แยก

**แบบทดสอบ**
1. veth pair คืออะไร
2. OVS ต่างจาก Linux bridge
3. SR-IOV ช่วยอะไร
4. ทำไมแยก vMotion/storage network
5. macvlan ใช้เมื่อไร

<details><summary>เฉลย</summary>

1. สาย virtual 2 ปลาย ส่งเข้าปลายหนึ่งออกอีกปลาย
2. OVS รองรับ OpenFlow, VXLAN/GRE, programmable, ฟีเจอร์ SDN
3. VM ใช้ NIC ตรง (virtual function) bypass vSwitch → performance สูง
4. traffic หนัก/latency sensitive ไม่รบกวน production
5. container/VM ต้องการ MAC/IP ของตัวเองบน LAN จริง
</details>

**5 โปรเจค**
- ⭐ P1: Linux bridge + 2 KVM VM คนละ VLAN
- ⭐⭐ P2: Open vSwitch + VXLAN ระหว่าง 2 host
- ⭐⭐ P3: สร้าง "container ด้วยมือ" ด้วย netns + veth + bridge + NAT
- ⭐⭐ P4: Proxmox cluster lab + SDN zones
- ⭐⭐⭐ P5: OVS + OpenFlow rule ด้วย `ovs-ofctl` ทำ ACL/L2 forwarding เอง

---

## Level 76 — Container Networking (Docker)

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L76-docker-networking.md](lessons/L76-docker-networking.md)

**สิ่งที่ต้องรู้**
- Network drivers: bridge (docker0), host, none, overlay, macvlan, ipvlan
- Port publishing (`-p 8080:80`) = DNAT ใน iptables/nftables
- User-defined bridge มี DNS ภายใน (ชื่อ container)
- Docker Compose networks, Swarm overlay (VXLAN)
- ปัญหาบ่อย: subnet docker ชน subnet องค์กร (172.17/16) → ตั้ง `default-address-pools`

```bash
docker network create --subnet 10.200.0.0/24 appnet
docker run -d --name db --network appnet postgres
docker run -d --name web --network appnet -p 8080:80 nginx
```

**แบบทดสอบ**
1. ทำไม container ใน default bridge เรียกกันด้วยชื่อไม่ได้
2. `-p 8080:80` ทำงานอย่างไรเบื้องหลัง
3. ทำไมติดตั้ง Docker แล้วเข้าระบบองค์กรบาง subnet ไม่ได้
4. host network mode ข้อดีข้อเสีย
5. Swarm overlay ใช้เทคโนโลยีอะไร

<details><summary>เฉลย</summary>

1. Default bridge ไม่มี embedded DNS (ต้องใช้ user-defined network)
2. Docker สร้าง DNAT rule (iptables/nftables) + docker-proxy
3. docker0/บริดจ์ใช้ 172.17+ ชนกับ subnet องค์กร → route ผิด
4. เร็ว ไม่มี NAT แต่ไม่แยก network, port ชนกันได้
5. VXLAN
</details>

**5 โปรเจค**
- ⭐ P1: Compose 3-tier (nginx, app, db) แยก frontend/backend network
- ⭐⭐ P2: ดู iptables/nft rule ที่ Docker สร้าง อธิบายทุก chain
- ⭐⭐ P3: macvlan ให้ container มี IP บน LAN จริง
- ⭐⭐ P4: Swarm 3 node + overlay + ดู VXLAN ใน Wireshark
- ⭐⭐⭐ P5: Containerlab + Docker รวม router + app → ทำ "mini enterprise" ในเครื่องเดียว

---

## Level 77 — Kubernetes Networking

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L77-kubernetes-networking.md](lessons/L77-kubernetes-networking.md)

**สิ่งที่ต้องรู้**
- Model: ทุก Pod มี IP, Pod คุยกันได้ไม่ผ่าน NAT
- CNI: Calico (BGP), Cilium (eBPF), Flannel (VXLAN), AWS VPC CNI
- Service: ClusterIP, NodePort, LoadBalancer, Headless; kube-proxy (iptables/IPVS) หรือ eBPF
- Ingress / Gateway API, CoreDNS (`svc.namespace.svc.cluster.local`)
- NetworkPolicy (default allow → ควรทำ default deny), MetalLB สำหรับ on-prem

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: {name: db-allow-app, namespace: prod}
spec:
  podSelector: {matchLabels: {app: db}}
  policyTypes: [Ingress]
  ingress:
  - from: [{podSelector: {matchLabels: {app: api}}}]
    ports: [{port: 5432, protocol: TCP}]
```

**แบบทดสอบ**
1. Service ClusterIP ทำงานอย่างไร
2. NetworkPolicy ต้องการอะไรถึงจะมีผล
3. Ingress vs Service LoadBalancer
4. Pod เรียก service ด้วยชื่ออะไรได้บ้าง
5. ทำไม Cilium/eBPF ได้รับความนิยม

<details><summary>เฉลย</summary>

1. Virtual IP; kube-proxy/eBPF แปลงไปยัง Pod endpoint
2. CNI ที่รองรับ NetworkPolicy (Calico/Cilium)
3. Ingress = L7 routing หลาย service ผ่าน entry เดียว; LB = L4 ต่อ service
4. `svc`, `svc.ns`, `svc.ns.svc.cluster.local`
5. Performance, observability (Hubble), policy L3–L7, แทน kube-proxy
</details>

**5 โปรเจค**
- ⭐⭐ P1: kind/k3d cluster + deploy app + Service + Ingress
- ⭐⭐ P2: NetworkPolicy default deny + allow เฉพาะที่จำเป็น + ทดสอบ
- ⭐⭐ P3: ติดตั้ง Cilium + Hubble ดู flow
- ⭐⭐⭐ P4: k3s on-prem + MetalLB BGP mode peer กับ FRR router
- ⭐⭐⭐ P5: Debug toolkit: netshoot pod + runbook "Pod คุยกันไม่ได้" 10 สาเหตุ

---

## Level 78 — Cloud Networking (AWS VPC เป็นหลัก)

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L78-cloud-aws-vpc.md](lessons/L78-cloud-aws-vpc.md)

**สิ่งที่ต้องรู้**
- VPC, Subnet (public/private, ต่อ AZ), Route table, Internet Gateway, NAT Gateway
- Security Group (stateful, ระดับ ENI) vs NACL (stateless, ระดับ subnet)
- VPC Peering (non-transitive), Transit Gateway, PrivateLink/VPC Endpoint
- Route 53, ELB (ALB/NLB/GWLB), CloudFront
- VPC Flow Logs, Reachability Analyzer
- Azure: VNet, NSG, VNet peering, Virtual WAN; GCP: VPC แบบ global, firewall rules
- ระวังค่าใช้จ่าย: NAT Gateway, data transfer ข้าม AZ/ออกอินเทอร์เน็ต

**แบบทดสอบ**
1. subnet "public" ต่างจาก "private" ที่อะไร
2. SG กับ NACL ต่างกัน
3. VPC A peer B, B peer C → A คุยกับ C ได้ไหม
4. ทำไม private subnet ต้องมี NAT Gateway
5. เข้าถึง S3 จาก private subnet โดยไม่ผ่าน NAT ทำอย่างไร

<details><summary>เฉลย</summary>

1. route table มี 0.0.0.0/0 → Internet Gateway
2. SG stateful, allow only, ผูก instance; NACL stateless, allow/deny, ผูก subnet, มีลำดับ
3. ไม่ได้ (non-transitive) → ใช้ Transit Gateway
4. ให้ instance ออกอินเทอร์เน็ต (update) โดยไม่มี public IP
5. Gateway VPC Endpoint สำหรับ S3
</details>

**5 โปรเจค**
- ⭐⭐ P1: VPC 2 AZ (public/private) + bastion + NAT ด้วย Console (แล้วลบทิ้ง)
- ⭐⭐ P2: ทำแบบเดียวกันด้วย Terraform (เตรียม Level 85)
- ⭐⭐ P3: เปิด VPC Flow Logs → Athena query หา top talkers/rejected
- ⭐⭐⭐ P4: Hub-and-spoke ด้วย Transit Gateway 3 VPC + inspection VPC
- ⭐⭐⭐ P5: เปรียบเทียบ AWS/Azure/GCP networking (ตาราง concept mapping + ราคา)

---

## Level 79 — Hybrid & Multi-Cloud Connectivity

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L79-hybrid-multicloud.md](lessons/L79-hybrid-multicloud.md)

**สิ่งที่ต้องรู้**
- Site-to-site VPN ไป cloud (BGP over IPsec), Direct Connect / ExpressRoute / Cloud Interconnect
- Redundancy: 2 tunnel/2 device/2 location, BGP failover
- DNS hybrid: Route 53 Resolver endpoints, conditional forwarders
- IP plan ต้องไม่ชนกันทั้ง on-prem + ทุก cloud
- Multi-cloud networking: Aviatrix, Alkira, cloud-native transit

**แบบทดสอบ**
1. VPN vs Direct Connect เลือกอย่างไร
2. ทำไมต้องวาง IP plan ก่อนสร้าง VPC แรก
3. On-prem resolve ชื่อ private ใน cloud ได้อย่างไร
4. ใช้อะไรควบคุมว่า traffic เลือก DX หรือ VPN
5. ความเสี่ยงของ single Direct Connect

<details><summary>เฉลย</summary>

1. VPN: เร็ว ถูก ผ่าน internet; DX: bandwidth/latency คงที่ ปลอดภัยกว่า ราคาสูง ใช้เวลาติดตั้ง
2. CIDR ชนกันแก้ยากมากภายหลัง (peering/VPN ใช้ไม่ได้)
3. Conditional forwarder → Inbound resolver endpoint
4. BGP attributes (AS-path prepend, local pref, longest prefix)
5. Single point of failure — ควรมี DX 2 location หรือ VPN สำรอง
</details>

**5 โปรเจค**
- ⭐⭐ P1: VPN BGP ระหว่าง lab (VyOS/FRR) กับ AWS VGW/TGW
- ⭐⭐ P2: Hybrid DNS: on-prem BIND ↔ Route 53 Resolver
- ⭐⭐ P3: IP plan ขององค์กร multi-cloud (on-prem + AWS + Azure) 5 ปี
- ⭐⭐⭐ P4: Failover test DX(จำลอง) ↔ VPN ด้วย BGP prepend
- ⭐⭐⭐ P5: AWS ↔ Azure VPN (BGP) + เอกสารต้นทุน

---

## Level 80 — Service Mesh, eBPF & Cloud-Native Networking

> 📖 **อ่านบทเรียนฉบับละเอียด:** [lessons/L80-service-mesh-ebpf.md](lessons/L80-service-mesh-ebpf.md)

**สิ่งที่ต้องรู้**
- Service mesh: sidecar (Envoy) หรือ ambient/sidecarless; Istio, Linkerd, Cilium Service Mesh
- mTLS ระหว่าง service, traffic shifting (canary), retries/timeouts, circuit breaking
- Observability: tracing (OpenTelemetry), metrics, golden signals
- eBPF: XDP (packet processing ก่อน stack), tc, โปรแกรมใน kernel อย่างปลอดภัย
- North-south vs East-west traffic

**แบบทดสอบ**
1. Service mesh แก้ปัญหาอะไร
2. mTLS ต่างจาก TLS อย่างไร
3. XDP ใช้ทำอะไรได้
4. Canary deployment ด้วย mesh ทำอย่างไร
5. ข้อเสียของ sidecar

<details><summary>เฉลย</summary>

1. Security (mTLS), traffic management, observability ระหว่าง microservices โดยไม่แก้โค้ด
2. ทั้งสองฝั่งยืนยันตัวตนด้วย cert
3. DDoS drop, load balancing (Katran), firewall ความเร็วสูง
4. VirtualService กำหนด weight เช่น 90/10 ระหว่าง version
5. ใช้ CPU/RAM เพิ่ม, latency เพิ่ม, ซับซ้อน
</details>

**5 โปรเจค**
- ⭐⭐ P1: Istio + Bookinfo app + canary 90/10
- ⭐⭐ P2: เปิด strict mTLS แล้วตรวจด้วย Kiali
- ⭐⭐⭐ P3: เขียน XDP program (C/libbpf หรือ bpftrace) นับ/drop packet ตาม port
- ⭐⭐⭐ P4: Cilium L7 policy (อนุญาตเฉพาะ GET /api)
- ⭐⭐⭐ P5: Capstone Tier 8: แอป microservices บน k8s + LB + mesh + NetworkPolicy + hybrid VPN ไป cloud + observability
