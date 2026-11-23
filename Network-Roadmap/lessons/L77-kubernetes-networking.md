# บทเรียน Level 77 — Kubernetes Networking (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจกฎพื้นฐาน network model ของ Kubernetes · Pod networking และ CNI (Calico, Cilium, Flannel) · Service (ClusterIP, NodePort, LoadBalancer) และ kube-proxy · CoreDNS · Ingress/Gateway API · NetworkPolicy · ทาง bare-metal (MetalLB, BGP) · วางแผน IP · troubleshooting

---

## 1. ส่วนประกอบที่ต้องรู้

| คำ | ความหมาย |
|---|---|
| **Cluster** | กลุ่มเครื่อง (node) ที่ Kubernetes จัดการ |
| **Node** | เครื่อง (VM/bare metal) ที่รัน workload — control plane node + worker node |
| **Pod** | หน่วยเล็กสุด: container 1 ตัวขึ้นไปที่ **ใช้ network namespace เดียวกัน (IP เดียวกัน)** |
| **Deployment** | ควบคุมจำนวน pod replica — pod ถูกสร้าง/ลบได้ตลอด **IP ของ pod จึงเปลี่ยนเสมอ** |
| **Service** | IP/ชื่อคงที่ที่กระจายโหลดไปยังกลุ่ม pod |
| **Namespace** (ของ K8s) | แบ่งกลุ่ม resource (dev, prod, team-a) — **ไม่ใช่** network namespace ของ Linux |

---

## 2. Kubernetes Network Model — กฎ 4 ข้อ

1. **ทุก Pod มี IP ของตัวเอง** (unique ทั้ง cluster)
2. **Pod คุยกับ Pod ใดก็ได้โดยไม่ต้อง NAT** (ข้าม node ก็ตาม)
3. Node คุยกับ Pod ทุกตัวได้โดยไม่ NAT
4. IP ที่ pod เห็นว่าเป็นของตัวเอง = IP ที่ผู้อื่นเห็น

→ **Kubernetes ไม่ได้ implement เอง** — ให้ **CNI plugin** เป็นผู้ทำ

### 4 ปัญหาการสื่อสาร
| ระดับ | แก้ด้วย |
|---|---|
| Container ↔ container ใน pod เดียวกัน | `localhost` (namespace เดียวกัน) |
| Pod ↔ Pod | **CNI** |
| Pod ↔ Service | **Service + kube-proxy/eBPF** |
| ภายนอก ↔ Service | **NodePort/LoadBalancer/Ingress/Gateway** |

---

## 3. CNI (Container Network Interface)

```
 Node 1 (10.0.5.11)                         Node 2 (10.0.5.12)
 ┌───────────────────────────┐              ┌───────────────────────────┐
 │ Pod A 10.244.1.5          │              │ Pod C 10.244.2.8          │
 │ Pod B 10.244.1.6          │              │                           │
 │   (Pod CIDR 10.244.1.0/24)│              │   (Pod CIDR 10.244.2.0/24)│
 └──────────────┬────────────┘              └──────────────┬────────────┘
                └────── Pod A → Pod C ข้าม node: 2 วิธี ────┘
```
| วิธีส่งข้าม node | หลักการ | ข้อดี/ข้อเสีย |
|---|---|---|
| **Overlay (VXLAN/Geneve/IP-in-IP)** | ห่อ packet ของ pod ใน IP ของ node | ✅ ไม่ต้องแก้ network จริง ❌ overhead, MTU ลด |
| **Native routing (BGP/direct route)** | ประกาศ Pod CIDR ของแต่ละ node ให้ network จริง (เช่น BGP กับ ToR) | ✅ ประสิทธิภาพดี, มองเห็น IP pod ได้ตรง ❌ ต้องร่วมมือกับทีม network |
| **Cloud native (VPC IP)** | pod ได้ IP จาก VPC ตรง (AWS VPC CNI, Azure CNI) | ✅ pod เป็น first-class ใน VPC ❌ ใช้ IP ใน subnet เยอะ |

### CNI ยอดนิยม
| CNI | จุดเด่น |
|---|---|
| **Calico** | BGP native routing หรือ VXLAN/IP-in-IP, NetworkPolicy แข็งแรง, มี eBPF dataplane |
| **Cilium** | **eBPF** (แทน iptables/kube-proxy), NetworkPolicy ระดับ L7, observability (**Hubble**), service mesh, BGP — ได้รับความนิยมสูง (Level 80) |
| **Flannel** | ง่าย (VXLAN) แต่ **ไม่รองรับ NetworkPolicy** ด้วยตัวเอง |
| AWS VPC CNI / Azure CNI / GKE Dataplane V2 | managed cloud |
| Multus | ให้ pod มีหลาย interface (telco/NFV) |

---

## 4. Service — IP คงที่สำหรับกลุ่ม Pod

Pod เกิดและตายตลอด → client ไม่ควรจำ IP ของ pod → **Service** เลือก pod ด้วย **label selector** และให้ IP/ชื่อคงที่
```yaml
apiVersion: v1
kind: Service
metadata: { name: web, namespace: shop }
spec:
  type: ClusterIP
  selector: { app: web }         # ส่งไป pod ที่มี label app=web
  ports:
  - port: 80                     # port ของ Service
    targetPort: 8080             # port ของ container
```
| ประเภท | เข้าถึงจาก | การทำงาน |
|---|---|---|
| **ClusterIP** (ค่าเริ่มต้น) | ภายใน cluster เท่านั้น | IP เสมือน (เช่น 10.96.x.x) |
| **NodePort** | ภายนอก: `<IP ของ node ใดก็ได้>:30000–32767` | เปิด port บนทุก node |
| **LoadBalancer** | ภายนอกผ่าน LB | cloud สร้าง LB ให้ (NLB/ALB/Azure LB) หรือ **MetalLB** บน bare metal |
| ExternalName | — | CNAME ไปชื่อภายนอก |
| Headless (`clusterIP: None`) | DNS คืน IP ของ pod ตรง | StatefulSet (DB cluster) |

### kube-proxy
ทำให้ ClusterIP ใช้งานได้บนทุก node: เขียน rule **iptables** (หรือ **IPVS**, หรือแทนด้วย **eBPF ของ Cilium**) ให้ DNAT จาก ClusterIP → IP ของ pod ปลายทาง
- **EndpointSlice** = รายการ IP ของ pod ที่ **Ready** (ผ่าน readinessProbe) — pod ไม่ ready ไม่ถูกส่ง traffic
- `externalTrafficPolicy: Local` — ส่งเฉพาะ pod บน node ที่รับ traffic (**เห็น IP จริงของ client**, ไม่ hop ข้าม node) แต่กระจายโหลดไม่สม่ำเสมอ

---

## 5. DNS ใน Cluster (CoreDNS)

```
 <service>.<namespace>.svc.cluster.local
 web.shop.svc.cluster.local → ClusterIP ของ service web
```
- pod ใน namespace เดียวกันเรียกแค่ `web` ได้, ข้าม namespace ใช้ `web.shop`
- `/etc/resolv.conf` ของ pod มี `search shop.svc.cluster.local svc.cluster.local cluster.local` และ **`ndots:5`** → ชื่อภายนอกเช่น `api.github.com` จะถูกลองต่อท้าย search domain ก่อน → DNS query เพิ่มหลายเท่า (แก้: ใช้ FQDN มีจุดท้าย `api.github.com.` หรือปรับ ndots, NodeLocal DNSCache)
- ปัญหา DNS เป็นสาเหตุอันดับต้นของ "แอปช้า/timeout" ใน K8s

---

## 6. Ingress และ Gateway API — HTTP(S) จากภายนอก

**Ingress** = กฎ L7 (host/path → service) ที่ **Ingress Controller** (NGINX Ingress, Traefik, HAProxy, cloud ALB) นำไปทำ
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: shop
  namespace: shop
spec:
  ingressClassName: nginx
  tls:
  - hosts: [shop.example.com]
    secretName: shop-tls               # cert (มักจัดการโดย cert-manager + ACME)
  rules:
  - host: shop.example.com
    http:
      paths:
      - { path: /api, pathType: Prefix, backend: { service: { name: api, port: { number: 80 } } } }
      - { path: /,    pathType: Prefix, backend: { service: { name: web, port: { number: 80 } } } }
```
**Gateway API** = ผู้สืบทอดของ Ingress (GatewayClass → Gateway → HTTPRoute/TCPRoute/GRPCRoute) — แยกบทบาทระหว่างทีม infra (Gateway) กับทีมแอป (Route) ชัดเจนกว่า รองรับ traffic splitting/header matching ในตัว — แนะนำสำหรับระบบใหม่

```
 ผู้ใช้ → DNS → LoadBalancer (VIP) → Ingress/Gateway controller pods → Service → Pods
```

---

## 7. NetworkPolicy — Firewall ระหว่าง Pod

**ค่าเริ่มต้น: ทุก pod คุยกับทุก pod ได้** (flat network) → ต้องกำหนด NetworkPolicy (CNI ต้องรองรับ)
```yaml
# 1) default deny ingress ทั้ง namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: default-deny, namespace: shop }
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
# 2) อนุญาต api → db port 5432 เท่านั้น
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: db-allow-api, namespace: shop }
spec:
  podSelector: { matchLabels: { app: db } }
  policyTypes: [Ingress]
  ingress:
  - from: [ { podSelector: { matchLabels: { app: api } } } ]
    ports: [ { protocol: TCP, port: 5432 } ]
---
# 3) อย่าลืม egress DNS เมื่อ default deny egress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: allow-dns, namespace: shop }
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
  - to: [ { namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: kube-system } } } ]
    ports: [ { protocol: UDP, port: 53 }, { protocol: TCP, port: 53 } ]
```
- นโยบายเป็น **allowlist แบบรวมกัน (additive)** — ไม่มี rule "deny" ใน API มาตรฐาน (Calico/Cilium มี policy ขยาย เช่น deny, L7, FQDN)
- **Zero trust ใน cluster:** default deny + อนุญาตเฉพาะ flow ที่ต้องใช้ (Level 66/67)

---

## 8. Kubernetes บน Bare Metal/On-premises

ไม่มี cloud LB → ต้องมีทาง:
- **MetalLB** หรือ **Cilium LB IPAM/BGP**: แจก IP จาก pool ให้ Service type LoadBalancer และประกาศด้วย
  - **L2 mode:** ตอบ ARP แทน VIP (node เดียวรับ — failover ด้วยการย้าย)
  - **BGP mode** ⭐: ประกาศ VIP ไปยัง ToR/router → ECMP กระจายหลาย node
- **Calico/Cilium BGP กับ ToR:** ประกาศ Pod CIDR/Service IP ให้ network จริง
```
 ToR (AS 65101) ◄── eBGP ── node1, node2, node3 (AS 64512)  ประกาศ 10.50.0.0/24 (LB pool)
 → ทีม network ต้องรับ route, ตั้ง prefix-list จำกัดสิ่งที่ยอมรับ, maximum-prefix
```

---

## 9. วางแผน IP สำหรับ Cluster

| ช่วง | ตัวอย่าง | หมายเหตุ |
|---|---|---|
| Node subnet | 10.0.5.0/24 | VLAN/subnet ของ node จริง |
| **Pod CIDR** | 10.244.0.0/16 | แบ่ง /24 ต่อ node (ค่าเริ่มต้น ~110 pod ต่อ node) |
| **Service CIDR** | 10.96.0.0/12 | IP เสมือน (ไม่ route ออกนอก) |
| LoadBalancer pool | 10.0.50.0/24 | ต้องประกาศ/route ได้จากผู้ใช้ |
⚠️ **ห้ามชน** กับ IP ขององค์กร, VPN, cluster อื่น (ถ้าต้องเชื่อมกัน) — เปลี่ยนภายหลังยากมาก
**Egress:** pod ออกนอก cluster มักถูก SNAT เป็น IP ของ node → firewall ภายนอกแยกไม่ออกว่า pod ไหน → ใช้ **egress gateway** (Cilium/Calico/Istio) ให้ IP ออกคงที่ต่อ namespace/แอป

---

## 10. Troubleshooting

```bash
kubectl get pods -o wide -n shop                  # IP และ node ของ pod
kubectl get svc,endpointslices -n shop            # service มี endpoint ไหม (ไม่มี = selector ผิด/pod ไม่ ready)
kubectl describe svc web -n shop
kubectl get ingress -n shop ; kubectl describe ingress shop -n shop
kubectl get networkpolicy -A
kubectl run tmp --rm -it --image=nicolaka/netshoot -n shop -- bash
#   ภายใน: nslookup web ; curl -v http://web ; curl -v http://10.244.2.8:8080
kubectl debug -it pod/web-xxx --image=nicolaka/netshoot --target=web   # ephemeral container
kubectl logs -n kube-system -l k8s-app=kube-dns
cilium status ; hubble observe --namespace shop --verdict DROPPED       # ถ้าใช้ Cilium
```
| อาการ | ตรวจ |
|---|---|
| Service ไม่ตอบ | EndpointSlice ว่าง → **selector/label ไม่ตรง** หรือ pod ไม่ Ready, targetPort ผิด |
| ชื่อ service resolve ไม่ได้ | CoreDNS, namespace ผิด, NetworkPolicy บล็อก DNS egress |
| Pod ข้าม node คุยไม่ได้ | CNI, MTU overlay, firewall ระหว่าง node บล็อก VXLAN (UDP 4789/8472) หรือ BGP |
| ภายนอกเข้าไม่ได้ | LB ไม่ได้ IP (MetalLB pool), Ingress class ผิด, cert, DNS |
| เข้าได้บางครั้ง | readiness probe, pod บางตัวเสีย |
| ทุกอย่างพังหลังใส่ policy | ลืมอนุญาต DNS/egress |

---

## 11. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| ควรเรียกแอปด้วย IP ของ pod | ใช้ Service/DNS — IP ของ pod เปลี่ยนตลอด |
| Pod แยกกันโดยอัตโนมัติ | ค่าเริ่มต้นคุยกันได้หมด ต้องใช้ NetworkPolicy |
| ทุก CNI รองรับ NetworkPolicy | Flannel ไม่รองรับด้วยตัวเอง |
| ClusterIP ping ได้ | เป็น IP เสมือน (iptables/IPVS/eBPF) — ping มักไม่ได้ ทดสอบด้วย curl/port |
| K8s namespace = network namespace | คนละเรื่อง — K8s namespace เป็นการจัดกลุ่ม resource |

---

## 12. Cheat Sheet

```
Model: ทุก pod มี IP · pod↔pod ไม่ NAT · implement โดย CNI
CNI: overlay (VXLAN) / native BGP / cloud VPC · Calico · Cilium (eBPF, Hubble) · Flannel (ไม่มี policy)
Service: ClusterIP · NodePort (30000-32767) · LoadBalancer · Headless · selector → EndpointSlice (Ready)
kube-proxy: iptables / IPVS / eBPF · externalTrafficPolicy: Local = เห็น client IP
DNS: svc.ns.svc.cluster.local · ndots:5
Ingress (host/path) → Gateway API (ใหม่) · cert-manager
NetworkPolicy: default deny + allow + อย่าลืม DNS
Bare metal: MetalLB/Cilium (L2 หรือ BGP กับ ToR)
IP plan: node / pod CIDR / service CIDR / LB pool — ห้ามชน · egress gateway
Debug: get svc,endpointslices · netshoot · kubectl debug · hubble observe
```

---

## 13. แบบทดสอบ 10 ข้อ

1. กฎพื้นฐานของ Kubernetes network model มีอะไรบ้าง
2. CNI แบบ overlay กับ native routing (BGP) ต่างกันอย่างไร
3. ทำไมต้องมี Service
4. ClusterIP, NodePort, LoadBalancer ต่างกันอย่างไร
5. Service มีแต่ไม่มี endpoint สาเหตุที่พบบ่อยคืออะไร
6. ชื่อ DNS เต็มของ service `api` ใน namespace `shop` คืออะไร
7. Ingress ต่างจาก Service type LoadBalancer อย่างไร
8. เขียนแนวทาง NetworkPolicy แบบ zero trust และสิ่งที่มักลืม
9. บน bare metal จะให้ Service type LoadBalancer ได้ IP ภายนอกอย่างไร
10. ต้องวางแผน IP range อะไรบ้างก่อนสร้าง cluster และทำไมต้องระวัง

<details><summary><b>เฉลย</b></summary>

1. ทุก pod มี IP ของตัวเอง, pod คุยกับ pod ได้โดยไม่ NAT, node คุยกับ pod ได้โดยไม่ NAT, IP ที่ pod เห็นของตนตรงกับที่ผู้อื่นเห็น
2. Overlay ห่อ packet ใน IP ของ node (ไม่ต้องแก้ network จริง แต่มี overhead/MTU); native routing ประกาศ Pod CIDR ให้ network จริง (ประสิทธิภาพดี แต่ต้องตั้งค่ากับ router/ToR)
3. Pod ถูกสร้าง/ลบตลอด IP เปลี่ยน — Service ให้ IP/ชื่อคงที่และกระจายโหลดไปยัง pod ที่ ready
4. ClusterIP ใช้ภายใน cluster; NodePort เปิด port บนทุก node; LoadBalancer ได้ IP ภายนอกผ่าน LB
5. Label selector ไม่ตรงกับ label ของ pod หรือ pod ไม่ผ่าน readiness probe
6. `api.shop.svc.cluster.local`
7. Ingress เป็นกฎ L7 (host/path, TLS) ที่ใช้ LB/IP เดียวกระจายหลาย service; LoadBalancer ให้ IP แยกต่อ service ระดับ L4
8. Default deny ingress/egress ทั้ง namespace แล้วอนุญาตเฉพาะ flow ที่ต้องใช้ — มักลืมอนุญาต DNS (UDP/TCP 53 ไป kube-system)
9. ใช้ MetalLB หรือ Cilium LB IPAM แจก IP จาก pool และประกาศด้วย L2 (ARP) หรือ BGP กับ ToR
10. Node subnet, Pod CIDR, Service CIDR, LoadBalancer pool — ต้องไม่ชนกับเครือข่ายองค์กร/VPN/cluster อื่น เพราะเปลี่ยนภายหลังยากมาก
</details>

---

➡️ ต่อไป: **Level 78 — Cloud Networking (AWS VPC)**
