# บทเรียน Level 80 — Service Mesh, eBPF & Cloud-Native Networking (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจปัญหาของ microservices ที่ service mesh แก้ · sidecar vs ambient/sidecarless · mTLS อัตโนมัติ, traffic management, observability · Istio/Linkerd/Cilium · eBPF คืออะไร ทำไมเปลี่ยนวงการ network · XDP · Cilium/Hubble · ข้อควรพิจารณาก่อนนำไปใช้

---

## 1. ปัญหาของ Microservices

แอปเดียวถูกแตกเป็นหลายสิบ–ร้อย service ที่เรียกกันผ่าน network
```
 [frontend] → [cart] → [pricing] → [inventory] → [db]
        ↘ [user] → [auth]       ↘ [recommend] → [ml-model]
```

| ปัญหา | ถ้าไม่มี mesh ต้อง… |
|---|---|
| **ความปลอดภัยระหว่าง service** (ใครเรียกใครได้, เข้ารหัส) | แต่ละทีมเขียน TLS/การยืนยันตัวตนเอง |
| **ความน่าเชื่อถือ** (retry, timeout, circuit breaker) | เขียนใน library ของแต่ละภาษา |
| **Traffic management** (canary, A/B) | ทำที่ LB ภายนอกเท่านั้น |
| **Observability** (service ไหนช้า, error ที่ไหน) | ใส่ instrumentation ทุก service |

**Service mesh** = ชั้น infrastructure ที่ย้ายเรื่องเหล่านี้ **ออกจากโค้ดของแอป** มาไว้ที่ network proxy ที่ควบคุมจากศูนย์กลาง

---

## 2. สถาปัตยกรรม Service Mesh

```
               ┌──────────── Control Plane (istiod / linkerd) ───────────┐
               │  นโยบาย, certificate (CA), service discovery, config     │
               └──────┬─────────────────────┬───────────────────┬────────┘
                      │ (xDS config)        │                   │
     ┌─── Pod A ──────▼──┐       ┌── Pod B ─▼──────────┐
     │ [app] ↔ [sidecar] │══mTLS═│ [sidecar] ↔ [app]   │   ← Data plane: proxy (Envoy / linkerd2-proxy)
     └───────────────────┘       └─────────────────────┘
```
- **Data plane:** proxy ดัก traffic เข้า-ออกของทุก service (ผ่าน iptables redirect หรือ eBPF)
- **Control plane:** แจก config/cert/นโยบายให้ proxy ทั้งหมด

### Sidecar vs Sidecarless

| แบบ | หลักการ | ข้อดี | ข้อเสีย |
|---|---|---|---|
| **Sidecar** (ดั้งเดิม) | proxy 1 ตัวต่อ pod | แยกเด็ดขาด ฟีเจอร์ครบ | ใช้ CPU/RAM มาก (หลายร้อย proxy), latency เพิ่ม, upgrade ต้อง restart pod |
| **Ambient mode (Istio)** | **ztunnel** ต่อ node (L4 mTLS) + **waypoint proxy** เฉพาะเมื่อต้องการ L7 | ทรัพยากรน้อยลงมาก, ไม่ต้อง inject sidecar | ใหม่กว่า |
| **Cilium Service Mesh** | **eBPF** ใน kernel ทำ L3/L4 + Envoy ต่อ node สำหรับ L7 | ประสิทธิภาพสูง | ผูกกับ Cilium CNI |

---

## 3. ความสามารถหลักของ Service Mesh

### ① Security: mTLS อัตโนมัติ + Identity
- ทุก service ได้ **identity** (SPIFFE ID เช่น `spiffe://cluster.local/ns/shop/sa/cart`) และ **certificate อายุสั้น** ที่หมุนเวียนอัตโนมัติ
- **mTLS** ระหว่างทุก service — เข้ารหัส + ยืนยันตัวตนทั้งสองฝั่ง โดยแอปไม่ต้องแก้ (Level 65)
- **Authorization policy** ระดับ identity (ไม่ใช่ IP) — แนวคิด **zero trust ใน cluster** (Level 66)
```yaml
# Istio: บังคับ mTLS ทั้ง namespace และให้เฉพาะ frontend เรียก cart ได้ (GET/POST)
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata: { name: default, namespace: shop }
spec: { mtls: { mode: STRICT } }
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata: { name: cart-allow-frontend, namespace: shop }
spec:
  selector: { matchLabels: { app: cart } }
  action: ALLOW
  rules:
  - from: [ { source: { principals: ["cluster.local/ns/shop/sa/frontend"] } } ]
    to:   [ { operation: { methods: ["GET", "POST"] } } ]
```

### ② Traffic Management
- **Canary / traffic splitting:** 90% ไป v1, 10% ไป v2
- Routing ตาม header (ส่งผู้ทดสอบไป v2)
- **Retry, timeout, circuit breaking, outlier detection** (ถอด instance ที่ error บ่อย)
- **Fault injection** (จงใจหน่วง/ใส่ error เพื่อทดสอบความทนทาน — chaos engineering)
```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata: { name: pricing, namespace: shop }
spec:
  hosts: [pricing]
  http:
  - route:
    - { destination: { host: pricing, subset: v1 }, weight: 90 }
    - { destination: { host: pricing, subset: v2 }, weight: 10 }
    timeout: 2s
    retries: { attempts: 3, perTryTimeout: 500ms, retryOn: "5xx,connect-failure" }
```
(Gateway API — Level 77 — กำลังเป็นมาตรฐานร่วมสำหรับการตั้ง routing ของ mesh ด้วย — GAMMA initiative)

### ③ Observability
proxy เห็นทุก request → ได้ **metrics** (request rate, error rate, latency — "golden signals"/RED) แบบเดียวกันทุก service, **distributed tracing** (OpenTelemetry/Jaeger — แอปต้องส่งต่อ trace header), **service topology graph** (Kiali)

---

## 4. เลือก Service Mesh

| Mesh | จุดเด่น |
|---|---|
| **Istio** | ฟีเจอร์ครบที่สุด, Envoy, ambient mode, ใช้แพร่หลาย — ซับซ้อนกว่า |
| **Linkerd** | เบา เรียบง่าย proxy เขียนด้วย Rust, mTLS อัตโนมัติ — ฟีเจอร์น้อยกว่า |
| **Cilium Service Mesh** | eBPF, รวมกับ CNI/NetworkPolicy/Hubble |
| Consul (HashiCorp) | รองรับ VM + K8s, multi-platform |
| Cloud managed | AWS VPC Lattice, Google Cloud Service Mesh, Azure (Istio add-on) |

### ควรใช้ Service Mesh เมื่อ…
✅ microservices จำนวนมาก, ต้องการ mTLS/zero trust ภายใน (compliance), ต้องการ traffic management/observability แบบสม่ำเสมอหลายทีมหลายภาษา
❌ แอปไม่กี่ตัว/monolith, ทีมยังไม่พร้อมดูแล (เพิ่มความซับซ้อน, debugging ยากขึ้น, ใช้ทรัพยากร) — เริ่มจาก NetworkPolicy + Ingress + observability ปกติก่อน

---

## 5. eBPF — Programmable Kernel

**eBPF (extended Berkeley Packet Filter)** = ให้รัน **โปรแกรมเล็ก ๆ ที่ปลอดภัยภายใน Linux kernel** ณ จุดต่าง ๆ (hook) **โดยไม่ต้องแก้/คอมไพล์ kernel ใหม่หรือโหลด kernel module**
```
 User space:  [โปรแกรม/Cilium agent] ──โหลด eBPF program + อ่าน/เขียน eBPF maps──┐
 ─────────────────────────────────────────────────────────────────────────────── │
 Kernel:      [Verifier ตรวจว่าปลอดภัย (ไม่ loop ไม่สิ้นสุด, ไม่อ่าน memory มั่ว)] ◄─┘
              → JIT compile → ผูกกับ hook:
                 XDP (driver ของ NIC) · TC (traffic control) · socket · kprobe/tracepoint · cgroup
```
### Hook ที่สำคัญด้าน network

| Hook | ทำงานที่ | ใช้ทำ |
|---|---|---|
| **XDP (eXpress Data Path)** | **เร็วที่สุด** — ทันทีที่ packet มาถึง driver ก่อนสร้าง skb | **DDoS mitigation** (drop หลายสิบล้าน pps), L4 load balancer (Meta Katran, Cloudflare) |
| **TC (tc ingress/egress)** | หลังสร้าง skb | policy, NAT, load balancing ของ Cilium |
| **Socket/cgroup** | ระดับ socket | **socket-level load balancing** (แปล ClusterIP เป็น pod IP ตอน connect — ไม่ต้อง NAT ทุก packet) |
| kprobe/tracepoint | ฟังก์ชันใน kernel | observability, tracing, security monitoring |

### ทำไม eBPF เปลี่ยนวงการ

| แบบเดิม (iptables) | eBPF |
|---|---|
| rule เป็นรายการเชิงเส้น — **หลายพัน service = หลายหมื่น rule ช้าลงเรื่อย ๆ** | **hash map** lookup เวลาคงที่ |
| อัปเดต rule ทั้งชุด (ช้าใน cluster ใหญ่) | อัปเดตเฉพาะ entry |
| ผูกกับ IP | ผูกกับ **identity** (label ของ pod) ได้ |
| มองเห็นจำกัด | เห็นทุก packet/flow/syscall + บริบท (pod, process) |

---

## 6. Cilium และ Hubble

**Cilium** = CNI ที่ใช้ eBPF ทั้งหมด (CNCF graduated project)
- **แทน kube-proxy** (kube-proxy replacement) — service load balancing ด้วย eBPF
- **NetworkPolicy L3–L7** (เช่น อนุญาตเฉพาะ `GET /api/products`), **DNS/FQDN policy** (อนุญาตออก `*.github.com`)
- **Identity-based security**, **WireGuard/IPsec** เข้ารหัสระหว่าง node อย่างโปร่งใส
- **BGP** (ประกาศ Pod CIDR/LB IP ไป ToR), **Egress gateway**, **Cluster Mesh** (หลาย cluster)
- **Hubble** — observability: เห็นทุก flow พร้อมชื่อ pod, verdict (FORWARDED/DROPPED) และเหตุผล
```bash
cilium status
cilium connectivity test                          # ทดสอบ cluster ครบชุด
hubble observe --namespace shop --verdict DROPPED # ทำไม packet ถูกทิ้ง (policy ไหน)
hubble observe --pod shop/cart-7d9 --protocol http
```
```yaml
# CiliumNetworkPolicy: L7 + FQDN
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata: { name: api-policy, namespace: shop }
spec:
  endpointSelector: { matchLabels: { app: api } }
  ingress:
  - fromEndpoints: [ { matchLabels: { app: frontend } } ]
    toPorts:
    - ports: [ { port: "8080", protocol: TCP } ]
      rules: { http: [ { method: "GET", path: "/api/products.*" } ] }
  egress:
  - toFQDNs: [ { matchPattern: "*.stripe.com" } ]
    toPorts: [ { ports: [ { port: "443", protocol: TCP } ] } ]
  - toEndpoints: [ { matchLabels: { "k8s:io.kubernetes.pod.namespace": kube-system, k8s-app: kube-dns } } ]
    toPorts: [ { ports: [ { port: "53", protocol: ANY } ], rules: { dns: [ { matchPattern: "*" } ] } } ]
```

### เครื่องมือ eBPF อื่น ๆ

| เครื่องมือ | ใช้ทำ |
|---|---|
| **bpftrace / BCC** | tracing (`tcpconnect`, `tcpretrans`, `tcplife` — ดูว่า process ไหนเชื่อมต่ออะไร, retransmit ที่ไหน) |
| **Falco / Tetragon** | runtime security (ตรวจพฤติกรรมผิดปกติ เช่น shell ใน container, เชื่อมต่อ IP แปลก) |
| **Pixie, Grafana Beyla** | observability อัตโนมัติไม่ต้องแก้โค้ด |
| Katran, Cloudflare (XDP) | L4 LB/DDoS ระดับ hyperscale |

```bash
sudo bpftool prog show                   # eBPF programs ที่โหลดอยู่
sudo /usr/share/bcc/tools/tcpretrans      # ดู TCP retransmission แบบ real time
sudo bpftrace -e 'tracepoint:syscalls:sys_enter_connect { @[comm] = count(); }'
```

---

## 7. ภาพรวม Cloud-Native Networking Stack

```
 ภายนอก ──► [CDN/WAF] ──► [Cloud LB / MetalLB+BGP] ──► [Gateway API / Ingress]
       ──► [Service mesh: mTLS, routing, retries] ──► [Service (eBPF LB)] ──► [Pods]
 ข้างใต้: CNI (Cilium/Calico) · NetworkPolicy · underlay (VPC หรือ spine-leaf + BGP)
 ข้าง ๆ: Observability (Hubble, OpenTelemetry, Prometheus/Grafana) · GitOps (Argo CD/Flux)
```
**บทบาทของ network engineer ในโลกนี้:** ออกแบบ underlay + BGP peering กับ cluster, IP planning, ingress/egress/firewall ขององค์กร, เข้าใจ CNI/policy/mesh เพื่อร่วมแก้ปัญหากับทีม platform/DevOps, ทำ automation/GitOps (Tier 9)

---

## 8. Troubleshooting ใน Mesh

| อาการ | ตรวจ |
|---|---|
| Service คุยกันไม่ได้หลังเปิด STRICT mTLS | client อยู่นอก mesh (ไม่มี sidecar/ไม่อยู่ใน ambient) → PERMISSIVE ชั่วคราว ระหว่าง migrate |
| ได้ 403 RBAC: access denied | AuthorizationPolicy ไม่อนุญาต identity/method นั้น |
| 503 UF/UH (Envoy) | upstream ไม่มี endpoint healthy, circuit breaker ทำงาน |
| latency เพิ่ม | proxy hop เพิ่ม, retry ซ้อนหลายชั้น (retry storm) |
| packet drop ไม่รู้สาเหตุ | `hubble observe --verdict DROPPED` บอก policy ที่ทิ้ง |

```bash
istioctl analyze -n shop
istioctl proxy-status
istioctl proxy-config routes deploy/frontend -n shop
kubectl logs deploy/cart -c istio-proxy -n shop    # access log ของ sidecar
```

---

## 9. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| ใช้ Kubernetes ต้องมี service mesh | เป็นทางเลือก — ใช้เมื่อความซับซ้อนคุ้มกับประโยชน์ |
| Service mesh แทน NetworkPolicy | ทำงานร่วมกัน (L3/L4 policy + L7/identity) |
| eBPF คือ firewall ตัวหนึ่ง | เป็นเทคโนโลยีรันโปรแกรมใน kernel ใช้ทำได้ทั้ง network, security, observability |
| eBPF โหลดโค้ดอะไรก็ได้ในkernel | ต้องผ่าน verifier ตรวจความปลอดภัย (และต้องมีสิทธิ์สูง) |
| Retry ยิ่งมากยิ่งดี | retry หลายชั้นทำให้เกิด retry storm ซ้ำเติมระบบที่กำลังล่ม |

---

## 10. Cheat Sheet

```
Service mesh = proxy data plane + control plane · mTLS อัตโนมัติ · identity (SPIFFE) · authz
Traffic: canary/split, retry, timeout, circuit breaker, fault injection · Observability: RED metrics, tracing
Sidecar (Envoy ต่อ pod) vs Ambient (ztunnel ต่อ node + waypoint) vs Cilium (eBPF)
Istio (ครบ) · Linkerd (เบา) · Cilium mesh · Consul
eBPF: โปรแกรมใน kernel ผ่าน verifier · hooks: XDP (เร็วสุด, DDoS/LB) · TC · socket · kprobe
eBPF > iptables: hash map, อัปเดตเฉพาะ entry, identity, visibility
Cilium: kube-proxy replacement, L7/FQDN policy, WireGuard, BGP, Cluster Mesh · Hubble observe
bpftool · bpftrace · BCC tcpretrans · Falco/Tetragon
```

---

## 11. แบบทดสอบ 10 ข้อ

1. Service mesh แก้ปัญหาอะไรของ microservices (4 ด้าน)
2. Data plane กับ control plane ใน mesh ต่างกันอย่างไร
3. Sidecar กับ ambient mode ต่างกันอย่างไร
4. mTLS ใน mesh ทำให้เกิด zero trust ใน cluster ได้อย่างไร
5. ยกตัวอย่างการใช้ traffic management 3 แบบ
6. เมื่อไรไม่ควรนำ service mesh มาใช้
7. eBPF คืออะไร ปลอดภัยได้อย่างไร
8. XDP เหมาะกับงานอะไร เพราะอะไร
9. ทำไม eBPF จึง scale ดีกว่า iptables ใน cluster ใหญ่
10. Pod ถูกปฏิเสธการเชื่อมต่อใน cluster ที่ใช้ Cilium จะหาสาเหตุได้อย่างไร

<details><summary><b>เฉลย</b></summary>

1. Security (mTLS, identity, authorization), reliability (retry/timeout/circuit breaker), traffic management (canary/split), observability (metrics/tracing) — โดยไม่ต้องแก้โค้ดของแอป
2. Data plane = proxy ที่ดักและส่ง traffic จริง; control plane = แจก config, certificate, นโยบายให้ proxy
3. Sidecar มี proxy ทุก pod (ใช้ทรัพยากรมาก ต้อง inject/restart); ambient ใช้ ztunnel ต่อ node สำหรับ L4/mTLS และ waypoint เฉพาะเมื่อต้องการ L7
4. ทุก service มี identity/certificate และทุกการเชื่อมต่อถูกเข้ารหัสและยืนยันทั้งสองฝั่ง จากนั้น authorization policy อนุญาตตาม identity แทนการเชื่อ network
5. Canary แบ่ง traffic 90/10, routing ตาม header ไปเวอร์ชันทดสอบ, retry/timeout/circuit breaker, fault injection
6. แอปมีไม่กี่ service/monolith หรือทีมยังไม่พร้อมดูแลความซับซ้อนและทรัพยากรที่เพิ่มขึ้น
7. เทคโนโลยีรันโปรแกรมขนาดเล็กใน Linux kernel ที่ hook ต่าง ๆ — ผ่าน verifier ตรวจว่าโปรแกรมจบได้และเข้าถึงหน่วยความจำอย่างปลอดภัย แล้ว JIT compile
8. DDoS mitigation และ L4 load balancing — ทำงานที่ driver ของ NIC ก่อน kernel สร้าง skb จึงประมวลผล/ทิ้ง packet ได้เร็วมาก
9. ใช้ hash map lookup เวลาคงที่และอัปเดตเฉพาะ entry แทน rule เชิงเส้นจำนวนมหาศาลที่ต้องเขียนใหม่ทั้งชุด
10. `hubble observe --verdict DROPPED` (ระบุ pod/namespace) เพื่อดู flow ที่ถูกทิ้งและ policy ที่เกี่ยวข้อง ร่วมกับ `cilium status`/policy ที่บังคับใช้
</details>

---

🎉 **จบ Tier 8** · ➡️ ต่อไป: **Level 81 — Python for Network Engineers** · กลับไปทำโปรเจคใน [08-datacenter-cloud.md](../08-datacenter-cloud.md)
