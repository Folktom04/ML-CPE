# บทเรียน Level 78 — Cloud Networking (AWS VPC) (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจโครงสร้าง Region/AZ · VPC, subnet, route table · Internet Gateway vs NAT Gateway · Security Group vs NACL · VPC endpoints · VPC peering vs Transit Gateway · ELB · Route 53 · Flow Logs · เทียบกับ Azure/GCP · ออกแบบ VPC 3-tier ด้วย Terraform · ระวังค่าใช้จ่าย data transfer

---

## 1. ทำไม Network Engineer ต้องรู้ Cloud

องค์กรเกือบทุกแห่งมีงานบน cloud (hybrid) — network ใน cloud **ใช้หลักการเดิม** (IP, subnet, routing, firewall, DNS, VPN, BGP) แต่ **ไม่มีอุปกรณ์ให้จับ**: ทุกอย่างเป็น API/console/code และมีข้อจำกัดเฉพาะ

### Region และ Availability Zone
```
 Region ap-southeast-1 (สิงคโปร์)   Region ap-southeast-7 (กรุงเทพฯ)
   ├── AZ a (data center แยกไฟ/เครือข่าย)
   ├── AZ b
   └── AZ c        ← เชื่อมกันด้วย latency ต่ำ (ms เดียว)
```
- **Region** = พื้นที่ทางภูมิศาสตร์ (เลือกตามผู้ใช้, latency, กฎหมาย/PDPA, ราคา)
- **AZ** = data center แยกกันใน region → **วางระบบอย่างน้อย 2 AZ** เพื่อ HA

---

## 2. VPC (Virtual Private Cloud)

**VPC** = เครือข่ายส่วนตัวเสมือนของเราใน region หนึ่ง (กำหนด CIDR เอง)
```
 VPC 10.20.0.0/16 (ap-southeast-1)
 ├── AZ-a
 │   ├── public-a   10.20.0.0/24   (ALB, NAT GW)
 │   ├── app-a      10.20.10.0/24  (EC2/EKS)
 │   └── db-a       10.20.20.0/24  (RDS)
 └── AZ-b
     ├── public-b   10.20.1.0/24
     ├── app-b      10.20.11.0/24
     └── db-b       10.20.21.0/24
```
- **Subnet อยู่ใน AZ เดียว** (ข้าม AZ ไม่ได้)
- AWS **สงวน 5 IP ต่อ subnet** (network, +1 VPC router, +2 DNS, +3 reserved, broadcast) → /24 ใช้ได้ 251
- **วางแผน CIDR ให้ไม่ชน** กับ on-prem และ VPC อื่น (เพราะจะต้องเชื่อมกันในอนาคต — Level 79) — ใช้ IPAM กลาง

### "Public" vs "Private" Subnet
ไม่ได้ตั้งเป็นค่า แต่ขึ้นกับ **route table**:
| Subnet | Route `0.0.0.0/0` ไปที่ |
|---|---|
| **Public** | **Internet Gateway (IGW)** — instance ต้องมี public/Elastic IP ด้วย |
| **Private** | **NAT Gateway** (ออกได้ เข้าไม่ได้) หรือไม่มีเลย |
| **Isolated** | ไม่มี default route (เช่น DB) |

### Route Table
```
 Route table: rt-private-a
   Destination        Target
   10.20.0.0/16       local            ← ภายใน VPC (ลบไม่ได้)
   0.0.0.0/0          nat-0abc (NAT GW ใน public-a)
   10.0.0.0/8         tgw-0123 (Transit Gateway ไป on-prem)
   pl-xxxx (S3)       vpce-...  (Gateway endpoint)
```
- longest prefix match เหมือนเดิม
- ใช้ **NAT GW แยกต่อ AZ** — ถ้าใช้ NAT GW ตัวเดียว AZ นั้นล่มทุก AZ ออกเน็ตไม่ได้ (และเสียค่า cross-AZ)

### IGW vs NAT Gateway
| | **Internet Gateway** | **NAT Gateway** |
|---|---|---|
| ทิศทาง | เข้า-ออก (instance มี public IP) | **ออกอย่างเดียว** (ขาเข้าเริ่มจากภายนอกไม่ได้) |
| ค่าใช้จ่าย | ไม่มีค่าตัว (มีค่า data transfer) | **ค่ารายชั่วโมง + ค่าต่อ GB ที่ประมวลผล** (มักแพงเกินคาด) |
| HA | ในตัว | ต่อ AZ (ต้องสร้างแต่ละ AZ) |

---

## 3. Security Group vs Network ACL

| | **Security Group (SG)** ⭐ | **Network ACL (NACL)** |
|---|---|---|
| ระดับ | **ENI/instance** | **subnet** |
| Stateful? | **Stateful** (ตอบกลับอนุญาตอัตโนมัติ) | **Stateless** (ต้องเปิดขากลับ ephemeral 1024–65535 เอง) |
| Rule | **allow เท่านั้น** (ที่ไม่ระบุ = deny) | allow และ **deny**, เรียงตามหมายเลข |
| อ้างอิง | IP/CIDR หรือ **SG อื่น** (เช่น "อนุญาตจาก sg-app") | CIDR เท่านั้น |
| ใช้หลัก | ✅ ควบคุมหลัก | ชั้นเสริม (เช่น block CIDR อันตรายทั้ง subnet) |

```
 sg-alb : inbound 443 from 0.0.0.0/0
 sg-app : inbound 8080 from sg-alb          ← อ้างอิง SG แทน IP (auto-scale ได้)
 sg-db  : inbound 5432 from sg-app
```
⚠️ ความผิดพลาดที่พบบ่อยที่สุดใน cloud: **เปิด 22/3389/DB ให้ 0.0.0.0/0** → ใช้ **SSM Session Manager**/bastion แทน, ตรวจด้วย AWS Config/Security Hub

---

## 4. VPC Endpoints — เรียกบริการ AWS โดยไม่ออกอินเทอร์เน็ต

| ประเภท | สำหรับ | การทำงาน | ค่าใช้จ่าย |
|---|---|---|---|
| **Gateway endpoint** | **S3, DynamoDB** | ใส่ route ใน route table | ฟรี (ลดค่า NAT GW ได้มาก) |
| **Interface endpoint (PrivateLink)** | บริการ AWS อื่น ๆ (SSM, ECR, Secrets Manager...) และบริการของ partner/ของเราเอง | สร้าง ENI + private IP ใน subnet + private DNS | ค่ารายชั่วโมง + ต่อ GB |
- ✅ ความปลอดภัย (traffic ไม่ออกเน็ต) + ลดค่า NAT
- **PrivateLink** ยังใช้ "เปิดบริการ" ให้ VPC อื่น/ลูกค้าเข้าถึงได้โดยไม่ต้อง peering ทั้ง VPC (และ IP ชนกันได้)

---

## 5. เชื่อมหลาย VPC

### VPC Peering
- เชื่อม VPC 2 ตัว (ข้าม account/region ได้) — **ไม่ transitive** (A–B, B–C ไม่ทำให้ A–C คุยกัน)
- CIDR ห้ามซ้อนกัน · เมื่อมีหลาย VPC → full mesh จำนวนมาก (n(n-1)/2) → จัดการยาก

### Transit Gateway (TGW) ⭐
**router กลาง (hub)** ของ region: attach VPC, VPN, Direct Connect, peering ข้าม region
```
              [ Transit Gateway ]
         /     |       |       \        \
     VPC-Prod VPC-Dev VPC-Shared  VPN/DX → on-prem
```
- **TGW route table** หลายชุด → แยก domain (เช่น Prod กับ Dev ไม่คุยกัน แต่ทั้งคู่ไป Shared/on-prem ได้)
- รูปแบบนิยม: **inspection VPC** (AWS Network Firewall/firewall ของผู้ผลิต) ให้ traffic ระหว่าง VPC/ออกเน็ตผ่าน firewall กลาง
- มีค่าต่อ attachment + ต่อ GB
- (AWS Cloud WAN สำหรับ global network ที่ซับซ้อน)

---

## 6. Elastic Load Balancing (เชื่อมกับ Level 71)

| | **ALB** | **NLB** | GWLB |
|---|---|---|---|
| Layer | L7 (HTTP/HTTPS/gRPC) | L4 (TCP/UDP/TLS) | L3 (ส่งให้ appliance) |
| จุดเด่น | path/host routing, WAF, OIDC auth | latency ต่ำมาก, **static IP/EIP**, เก็บ IP ของ client | แทรก firewall ของผู้ผลิตแบบ transparent (GENEVE) |
- วาง LB ใน **public subnet อย่างน้อย 2 AZ**, target อยู่ใน private subnet
- Health check, cross-zone load balancing, ACM จัดการ certificate

---

## 7. DNS: Route 53

- **Public hosted zone** — DNS สาธารณะ · **Private hosted zone** — ใช้ภายใน VPC ที่ผูกไว้
- **Routing policy:** simple, weighted, latency-based, **failover (+ health check)**, geolocation → ใช้ทำ GSLB/DR (Level 71)
- **Alias record** ชี้ไป ALB/CloudFront ได้ที่ zone apex
- **Route 53 Resolver endpoints:** inbound (on-prem ถามชื่อใน VPC) / outbound + forwarding rule (VPC ถามชื่อ on-prem `corp.local`) — สำคัญมากใน hybrid (Level 79)
- AmazonProvidedDNS อยู่ที่ VPC base +2 (เช่น 10.20.0.2)

---

## 8. Observability และ Troubleshooting

- **VPC Flow Logs** — บันทึก metadata ของ flow (src/dst/port/ACCEPT/REJECT) ระดับ VPC/subnet/ENI → ส่ง CloudWatch/S3 → วิเคราะห์ (Athena) / SIEM
```
 2 123456789012 eni-0a1b 10.20.10.15 10.20.20.30 49152 5432 6 10 840 1700000000 1700000060 REJECT OK
   → app พยายามต่อ DB port 5432 แต่ถูก REJECT → ตรวจ SG/NACL ของ DB
```
- **Reachability Analyzer** — วิเคราะห์ว่า A ไป B ได้ไหมและติดที่ไหน (SG/NACL/route) **โดยไม่ต้องส่ง packet**
- **Network Access Analyzer**, **Traffic Mirroring** (ส่ง packet ให้ IDS), CloudWatch metrics
| อาการ | ตรวจตามลำดับ |
|---|---|
| Instance ออกเน็ตไม่ได้ | route table ของ subnet (IGW/NAT), public IP (ถ้าอยู่ public subnet), SG outbound, NACL ทั้งสองทาง, NAT GW อยู่ใน public subnet ไหม |
| เข้าจากเน็ตไม่ได้ | ALB SG, target health, SG ของ instance อนุญาตจาก SG ของ ALB |
| Peering คุยกันไม่ได้ | route ทั้งสองฝั่ง, SG, CIDR ซ้อน |
| ชื่อภายในไม่ resolve | private hosted zone ผูก VPC ไหม, enableDnsHostnames/enableDnsSupport |

---

## 9. ค่าใช้จ่ายด้าน Network (เรื่องที่ทีมมักพลาด)

| รายการ | หมายเหตุ |
|---|---|
| **Data transfer ออกอินเทอร์เน็ต** | คิดต่อ GB |
| **Cross-AZ** | คิดทั้งสองทิศ — ระวังแอปคุย DB ข้าม AZ ตลอด |
| **NAT Gateway** | ค่าชั่วโมง + ต่อ GB → ใช้ gateway endpoint สำหรับ S3/DynamoDB |
| TGW / PrivateLink / VPN / Direct Connect | ต่อชั่วโมง/attachment + ต่อ GB |
| Public IPv4 | คิดค่าต่อ IP (ตั้งแต่ปี 2024) → พิจารณา IPv6/ลด public IP |
→ ออกแบบให้ traffic อยู่ใน AZ เดียวกันเท่าที่ทำได้, ใช้ CDN, ตรวจ Cost Explorer แยกตาม usage type

---

## 10. Infrastructure as Code (Terraform)

```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"
  name = "prod"
  cidr = "10.20.0.0/16"
  azs              = ["ap-southeast-1a", "ap-southeast-1b"]
  public_subnets   = ["10.20.0.0/24",  "10.20.1.0/24"]
  private_subnets  = ["10.20.10.0/24", "10.20.11.0/24"]
  database_subnets = ["10.20.20.0/24", "10.20.21.0/24"]
  enable_nat_gateway     = true
  one_nat_gateway_per_az = true
  enable_flow_log        = true
  flow_log_destination_type = "s3"
  flow_log_destination_arn  = "arn:aws:s3:::example-flowlogs-bucket"
}
resource "aws_security_group" "db" {
  name   = "sg-db"
  vpc_id = module.vpc.vpc_id
  ingress {
    from_port = 5432
    to_port   = 5432
    protocol  = "tcp"
    security_groups = [aws_security_group.app.id]
  }
}
```
`terraform plan` → review ใน pull request → `terraform apply` (Level 87)

---

## 11. เทียบ AWS / Azure / GCP

| แนวคิด | AWS | Azure | GCP |
|---|---|---|---|
| เครือข่ายส่วนตัว | VPC (ต่อ region) | VNet (ต่อ region) | VPC (**global**, subnet ต่อ region) |
| Firewall ระดับ instance | Security Group | NSG (ผูก subnet/NIC, stateful) | VPC Firewall rules (+ network tags) |
| Hub | Transit Gateway | **Virtual WAN** / hub VNet + peering | NCC / Shared VPC |
| NAT ขาออก | NAT Gateway | NAT Gateway | Cloud NAT |
| Private access บริการ | VPC Endpoint/PrivateLink | Private Endpoint / Service Endpoint | Private Service Connect |
| Dedicated link | Direct Connect | ExpressRoute | Cloud Interconnect |
| Flow log | VPC Flow Logs | NSG/VNet Flow Logs | VPC Flow Logs |

---

## 12. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| Subnet เป็น public เพราะตั้งชื่อว่า public | ขึ้นกับ route table (มี default route ไป IGW) |
| NACL ก็ stateful เหมือน SG | NACL stateless ต้องเปิดขากลับเอง |
| Peering ต่อกันเป็นทอด ๆ ได้ | ไม่ transitive — ใช้ TGW |
| Network ใน cloud ฟรี | data transfer/NAT/cross-AZ/TGW มีค่าใช้จ่ายมาก |
| Subnet ขยายข้าม AZ ได้ | subnet อยู่ใน AZ เดียว |

---

## 13. Cheat Sheet

```
Region > AZ (≥2 AZ เพื่อ HA) · VPC CIDR ไม่ชน on-prem · subnet อยู่ AZ เดียว · AWS สงวน 5 IP
Public = route 0/0 → IGW (+public IP) · Private = 0/0 → NAT GW (ต่อ AZ) · Isolated = ไม่มี
SG: instance, stateful, allow-only, อ้าง SG ได้ · NACL: subnet, stateless, allow/deny ตามลำดับ
Endpoints: Gateway (S3/DynamoDB ฟรี) · Interface/PrivateLink
Peering (ไม่ transitive, CIDR ห้ามซ้อน) vs Transit Gateway (hub, route tables, inspection VPC)
ELB: ALB L7 · NLB L4 static IP · GWLB appliance
Route 53: public/private zone, failover/latency/weighted, Resolver endpoints (hybrid DNS)
Flow Logs · Reachability Analyzer · Traffic Mirroring
ค่าใช้จ่าย: egress, cross-AZ, NAT, TGW, public IPv4
IaC: Terraform plan → PR review → apply
```

---

## 14. แบบทดสอบ 10 ข้อ

1. Region และ AZ ต่างกันอย่างไร ทำไมต้องวางระบบอย่างน้อย 2 AZ
2. อะไรทำให้ subnet เป็น public subnet
3. NAT Gateway ต่างจาก Internet Gateway อย่างไร
4. Security Group กับ NACL ต่างกันอย่างไร (3 ข้อ)
5. ทำไมควรอ้างอิง SG ใน rule แทน IP
6. Gateway endpoint ของ S3 มีประโยชน์อะไร
7. มี 10 VPC ที่ต้องคุยกันและกับ on-prem ควรใช้อะไร ทำไม
8. ALB กับ NLB เลือกอย่างไร
9. Instance ใน private subnet ออกอินเทอร์เน็ตไม่ได้ ตรวจอะไรบ้าง
10. ค่าใช้จ่าย network ใดที่มักถูกมองข้าม (3 อย่าง)

<details><summary><b>เฉลย</b></summary>

1. Region = พื้นที่ทางภูมิศาสตร์, AZ = data center แยกกันภายใน region — 2 AZ ขึ้นไปเพื่อให้ระบบทนต่อ AZ ล่ม
2. Route table ของ subnet มี default route ไปยัง Internet Gateway (และ instance มี public IP)
3. IGW ให้เข้า-ออกอินเทอร์เน็ตสำหรับ instance ที่มี public IP; NAT GW ให้ instance ใน private subnet ออกได้อย่างเดียว ภายนอกเริ่ม connection เข้ามาไม่ได้ และมีค่าใช้จ่ายต่อชั่วโมง/GB
4. SG ระดับ instance/ENI vs NACL ระดับ subnet; SG stateful vs NACL stateless; SG allow-only vs NACL allow/deny ตามลำดับ
5. Instance เพิ่ม/ลด (auto scaling) และ IP เปลี่ยนได้ rule ยังถูกต้องโดยไม่ต้องแก้
6. เข้าถึง S3 โดยไม่ผ่านอินเทอร์เน็ต/NAT GW — ปลอดภัยกว่าและไม่มีค่า NAT
7. Transit Gateway — เป็น hub กลาง ลดจำนวน peering แบบ full mesh, รองรับ VPN/Direct Connect และแยก route table ตาม domain
8. ALB สำหรับ HTTP/HTTPS ที่ต้องการ L7 routing/WAF; NLB สำหรับ TCP/UDP ที่ต้องการ latency ต่ำ, static IP, หรือเก็บ IP ของ client
9. Route table มี 0/0 ไป NAT GW, NAT GW อยู่ใน public subnet ที่มี route ไป IGW, SG outbound, NACL ทั้งขาไปและขากลับ (ephemeral ports)
10. Cross-AZ data transfer, NAT Gateway (ชั่วโมง+GB), egress ออกอินเทอร์เน็ต, TGW/PrivateLink, public IPv4
</details>

---

➡️ ต่อไป: **Level 79 — Hybrid & Multi-Cloud Connectivity**
