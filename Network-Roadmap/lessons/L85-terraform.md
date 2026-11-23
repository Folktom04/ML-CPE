# บทเรียน Level 85 — Infrastructure as Code: Terraform (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจ IaC และแนวคิด declarative · องค์ประกอบของ Terraform (provider, resource, data, variable, output, locals, module) · workflow init/plan/apply/destroy · state file, remote backend, locking · drift และ import · ใช้ Terraform กับ cloud network, DNS, firewall, NetBox · เขียน module ที่ใช้ซ้ำได้ · pipeline plan-in-PR · OpenTofu · ข้อควรระวังด้านความปลอดภัย

---

## 1. Infrastructure as Code (IaC)

**IaC** = บรรยายโครงสร้างพื้นฐาน (VPC, subnet, firewall rule, DNS record, LB) **เป็นโค้ด** เก็บใน Git แล้วให้เครื่องมือสร้าง/ปรับให้ตรง
| Imperative (สั่งทีละขั้น) | **Declarative** (บอกผลลัพธ์ที่ต้องการ) ⭐ |
|---|---|
| "สร้าง subnet A, แล้วเพิ่ม route, แล้ว…" | "ต้องมี VPC นี้ ที่มี subnet 4 ตัว และ route แบบนี้" |
| ต้องรู้สถานะปัจจุบันเอง | เครื่องมือคำนวณความต่างและทำให้ตรงเอง |
| ตัวอย่าง: สคริปต์ Python/CLI | Terraform, CloudFormation, Bicep, Pulumi (โค้ดแต่ declarative) |

**ข้อดี:** ทำซ้ำได้ (dev/test/prod เหมือนกัน), review ได้ใน PR, มีประวัติ, ลดการคลิกผิดใน console, สร้าง environment ใหม่/DR ได้เร็ว

---

## 2. องค์ประกอบของ Terraform

```hcl
terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }     # ล็อก version
  }
}
provider "aws" {
  region = var.region
  default_tags { tags = { Owner = "network-team", ManagedBy = "terraform" } }
}

variable "region" {
  type    = string
  default = "ap-southeast-1"
}
variable "vpc_cidr" {
  type = string
  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "vpc_cidr ต้องเป็น CIDR ที่ถูกต้อง"
  }
}
locals {
  azs = ["${var.region}a", "${var.region}b"]
}

data "aws_availability_zones" "available" { state = "available" }   # อ่านข้อมูลที่มีอยู่

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  tags = { Name = "prod-vpc" }
}
resource "aws_subnet" "private" {
  count             = length(local.azs)
  vpc_id            = aws_vpc.main.id                         # อ้างอิง → Terraform รู้ลำดับการสร้าง
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, 10 + count.index)   # 10.20.10.0/24, 10.20.11.0/24
  availability_zone = local.azs[count.index]
  tags = { Name = "private-${local.azs[count.index]}" }
}
output "private_subnet_ids" { value = aws_subnet.private[*].id }
```
| องค์ประกอบ | หน้าที่ |
|---|---|
| **provider** | plugin ที่คุยกับ API ของแต่ละระบบ |
| **resource** | สิ่งที่ Terraform สร้าง/จัดการ |
| **data** | อ่านข้อมูลที่มีอยู่แล้ว (ไม่ได้จัดการ) |
| **variable** | input (+ type, validation, default) |
| **locals** | ค่าคำนวณภายใน |
| **output** | ค่าที่ส่งออก (ให้ module อื่น/คนดู) |
| **module** | กลุ่ม resource ที่ใช้ซ้ำได้ |
**ฟังก์ชันที่ network engineer ใช้บ่อย:** `cidrsubnet()`, `cidrhost()`, `cidrnetmask()`, `for_each`, `count`, `lookup()`, `yamldecode(file())`

---

## 3. Workflow

```bash
terraform init          # ดาวน์โหลด provider/module, ตั้ง backend
terraform fmt -recursive && terraform validate
terraform plan -out=tfplan      # ⭐ แสดงสิ่งที่จะเกิด: + สร้าง, ~ แก้, - ลบ, -/+ ลบแล้วสร้างใหม่
terraform apply tfplan          # ทำตาม plan ที่ review แล้ว
terraform destroy               # ลบทั้งหมด (ระวัง!)
terraform state list ; terraform state show aws_vpc.main
terraform output
```
### อ่าน plan ให้เป็น — ทักษะสำคัญที่สุด
```
  # aws_subnet.private[0] must be replaced
-/+ resource "aws_subnet" "private" {
      ~ cidr_block = "10.20.10.0/24" -> "10.20.12.0/24" # forces replacement
```
⚠️ **"must be replaced"** บนทรัพยากร network = **ลบแล้วสร้างใหม่** → ทุกอย่างใน subnet นั้นอาจหลุด/ถูกลบ → หยุดและทบทวนก่อน apply เสมอ
- ป้องกันด้วย `lifecycle { prevent_destroy = true }` บนทรัพยากรสำคัญ, `create_before_destroy`

---

## 4. State — หัวใจของ Terraform

**State file (`terraform.tfstate`)** = แผนที่เชื่อม "resource ในโค้ด" ↔ "ทรัพยากรจริง (ID)" → ใช้คำนวณ diff
| ปัญหา | ทางแก้ |
|---|---|
| เก็บไว้บนเครื่องคนเดียว → ทีมใช้ร่วมกันไม่ได้, เครื่องหาย = state หาย | **Remote backend**: S3, Azure Storage, GCS, Terraform Cloud/HCP, GitLab |
| สองคน apply พร้อมกัน → state พัง | **State locking** (S3 lockfile/DynamoDB, ในตัว backend อื่น) |
| State มี **ข้อมูลลับ** (password, key ที่ resource สร้าง) | เข้ารหัส backend, จำกัดสิทธิ์อ่าน, **ไม่ commit state ลง Git** |
```hcl
terraform {
  backend "s3" {
    bucket       = "example-tfstate-network"
    key          = "prod/vpc/terraform.tfstate"
    region       = "ap-southeast-1"
    encrypt      = true
    use_lockfile = true          # S3 native locking (Terraform 1.10+); รุ่นเก่าใช้ dynamodb_table
  }
}
```
- **แยก state ตาม environment/ส่วน** (prod-network, prod-app, dev) — ลด blast radius ของความผิดพลาด
- คำสั่งที่ต้องระวัง: `terraform state rm`, `state mv`/`moved {}` block (ย้าย resource ในโค้ดโดยไม่สร้างใหม่)

---

## 5. Drift และ Import

### Drift
มีคนแก้ใน console (เช่น เพิ่ม rule ใน security group ด้วยมือ) → ของจริงต่างจากโค้ด
```bash
terraform plan -refresh-only      # แสดงสิ่งที่เปลี่ยนนอก Terraform
terraform plan -detailed-exitcode # exit 2 = มีความต่าง → ใช้ใน job ตรวจ drift รายวัน
```
ทางแก้: นำการเปลี่ยนนั้นเข้าโค้ด (ถ้าถูกต้อง) หรือ apply ทับกลับ — และสร้างวินัย "แก้ผ่านโค้ดเท่านั้น"

### Import ทรัพยากรที่มีอยู่แล้ว (brownfield)
```hcl
import {
  to = aws_vpc.legacy
  id = "vpc-0a1b2c3d"
}
```
```bash
terraform plan -generate-config-out=generated.tf   # ให้ Terraform เขียนโค้ดเริ่มต้นให้ แล้วปรับให้สะอาด
```

---

## 6. Module — ใช้ซ้ำและสร้างมาตรฐาน

```
modules/vpc/
├── main.tf  variables.tf  outputs.tf  README.md
envs/
├── dev/main.tf     → module "vpc" { source = "../../modules/vpc" cidr = "10.30.0.0/16" }
└── prod/main.tf    → module "vpc" { source = "../../modules/vpc" cidr = "10.20.0.0/16" }
```
- ใช้ module สาธารณะที่ผ่านการใช้งานแพร่หลาย (เช่น `terraform-aws-modules/vpc/aws`) หรือสร้าง module มาตรฐานขององค์กร (naming, tagging, flow logs บังคับ)
- **ล็อก version** ของ module/provider (`version = "~> 5.0"`) + `.terraform.lock.hcl` commit ลง Git

### ขับเคลื่อนด้วยข้อมูล (YAML → for_each)
```yaml
# rules.yaml
app_ingress:
  - { port: 443, cidr: "10.0.0.0/8",  desc: "HTTPS from corp" }
  - { port: 22,  cidr: "10.0.99.0/24", desc: "SSH from jump hosts" }
```
```hcl
locals { rules = yamldecode(file("${path.module}/rules.yaml")).app_ingress }
resource "aws_vpc_security_group_ingress_rule" "app" {
  for_each          = { for r in local.rules : "${r.port}-${r.cidr}" => r }   # key คงที่ → แก้รายการไม่กระทบตัวอื่น
  security_group_id = aws_security_group.app.id
  ip_protocol       = "tcp"
  from_port         = each.value.port
  to_port           = each.value.port
  cidr_ipv4         = each.value.cidr
  description       = each.value.desc
}
```
💡 ใช้ **`for_each` (key คงที่)** แทน `count` สำหรับรายการที่เปลี่ยน — ลบรายการกลาง list ด้วย `count` จะทำให้ resource ถัดไปถูกสร้างใหม่ทั้งหมด

---

## 7. Provider ที่เกี่ยวกับงาน Network

| Provider | ใช้ทำ |
|---|---|
| **AWS / AzureRM / Google** | VPC/VNet, subnet, route, SG/NSG, TGW/vWAN, VPN, LB, DNS |
| **Cloudflare** | DNS record, WAF rule, Zero Trust policy |
| **Palo Alto (panos), FortiOS, Check Point** | address/service object, security policy |
| **NetBox** | สร้าง prefix/IP/VLAN ใน IPAM (หรือใช้ data source ดึง IP ว่าง) |
| Arista CloudVision, Cisco ACI/Catalyst Center/Meraki, Juniper Apstra | DC fabric, campus |
| F5 BIG-IP, Infoblox | LB, DNS/DHCP/IPAM |
| DNS (RFC 2136), Akamai, NS1 | DNS |

```hcl
resource "cloudflare_dns_record" "www" {
  zone_id = var.zone_id
  name    = "www"
  type    = "CNAME"
  content = "app-lb-123.ap-southeast-1.elb.amazonaws.com"
  proxied = true
  ttl     = 1
}
```

---

## 8. Terraform vs Ansible vs อื่น ๆ

| | **Terraform** | **Ansible** |
|---|---|---|
| เด่นที่ | **Provisioning** (สร้าง/ลบทรัพยากรผ่าน API) | **Configuration** (ตั้งค่าในอุปกรณ์/OS, ขั้นตอน) |
| State | มี state file | ไม่มี (ตรวจสถานะตอนรัน) |
| ลบสิ่งที่ไม่อยู่ในโค้ด | ✅ (ลบ resource ที่ถูกเอาออก) | ต้องเขียนเอง |
| ตัวอย่าง | VPC, TGW, SG, Cloudflare DNS, firewall object | baseline switch, VLAN, OS hardening |
- **OpenTofu** = fork open source ของ Terraform (หลังเปลี่ยน license เป็น BSL ในปี 2023) — syntax ใกล้เคียงกัน
- ทางเลือก: Pulumi (เขียนด้วย Python/TypeScript), CloudFormation/CDK (AWS), Bicep (Azure), Crossplane (Kubernetes-native)

---

## 9. Pipeline: Plan in PR, Apply after Approve

```
 PR เปิด → fmt/validate → tflint → security scan (checkov/trivy config: SG เปิด 0.0.0.0/0?)
        → terraform plan → โพสต์ plan เป็น comment ใน PR → reviewer อ่าน plan
 merge  → (approval) → terraform apply plan เดียวกับที่ review
 รายวัน → plan -detailed-exitcode → แจ้งเตือนเมื่อมี drift
```
- Credential ของ cloud ใน CI ใช้ **OIDC (short-lived)** แทน access key ถาวร
- เครื่องมือ: Atlantis, Terraform Cloud/HCP, Spacelift, env0, GitHub Actions/GitLab CI
- **Policy as code:** OPA/Conftest, Sentinel — เช่น "ห้าม SG เปิด 22 ให้ 0.0.0.0/0", "ทุก VPC ต้องเปิด flow logs"

---

## 10. ข้อควรระวัง

- **อย่าใส่ secret ในโค้ด/ตัวแปร default** — ใช้ secret manager/ตัวแปรสภาพแวดล้อม (`TF_VAR_...`) และ `sensitive = true`
- State มีข้อมูลลับ → เข้ารหัส จำกัดสิทธิ์
- **อ่าน plan ทุกครั้ง** โดยเฉพาะ destroy/replace
- ทรัพยากรที่ทีมอื่นจัดการด้วยมือ/เครื่องมืออื่น → อย่าให้ Terraform จัดการซ้อน (แย่งกันแก้)
- `terraform apply -auto-approve` ใช้เฉพาะ pipeline ที่ approve แล้วเท่านั้น
- เริ่มกับ dev environment ก่อน

---

## 11. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| State file เป็นแค่ cache ลบได้ | ลบแล้ว Terraform ไม่รู้ว่าจัดการอะไรอยู่ (อาจสร้างซ้ำ) — สำคัญมาก |
| Commit state ลง Git สะดวก | มีข้อมูลลับและเกิด conflict — ใช้ remote backend |
| เปลี่ยน CIDR ใน Terraform = แก้ค่าเฉย ๆ | หลายค่า "forces replacement" — ลบสร้างใหม่ |
| Terraform แทน Ansible ได้ทั้งหมด | Terraform เด่น provisioning, Ansible เด่น configuration |
| count กับ for_each เหมือนกัน | for_each ใช้ key คงที่ ลดการสร้างใหม่โดยไม่ตั้งใจ |

---

## 12. Cheat Sheet

```
IaC declarative: บอกผลลัพธ์ → tool คำนวณ diff
provider · resource · data · variable(validation) · locals · output · module
init → fmt/validate → plan -out → (review) → apply tfplan · destroy ระวัง
อ่าน plan: + create · ~ update · - destroy · -/+ replace (forces replacement!)
State: remote backend + lock + encrypt · ห้าม commit · แยกตาม env
Drift: plan -refresh-only / -detailed-exitcode · import {} + -generate-config-out
for_each > count สำหรับ list ที่เปลี่ยน · cidrsubnet() · yamldecode(file())
lifecycle prevent_destroy · version pinning + .terraform.lock.hcl
Pipeline: plan ใน PR → approve → apply · OIDC · checkov/tflint · policy as code
Terraform = provisioning · Ansible = configuration · OpenTofu
```

---

## 13. แบบทดสอบ 10 ข้อ

1. Declarative ต่างจาก imperative อย่างไร
2. resource กับ data source ต่างกันอย่างไร
3. State file มีไว้ทำไม และควรเก็บอย่างไร
4. ทำไมต้องมี state locking
5. เห็นคำว่า "forces replacement" ใน plan ควรทำอย่างไร
6. Drift คืออะไร ตรวจอย่างไร
7. ทำไมควรใช้ for_each แทน count สำหรับรายการ firewall rule
8. ใช้ `cidrsubnet("10.20.0.0/16", 8, 5)` ได้ผลอะไร
9. Terraform กับ Ansible ควรใช้ทำอะไรต่างกัน
10. อธิบาย pipeline ที่ปลอดภัยสำหรับ Terraform ในทีม

<details><summary><b>เฉลย</b></summary>

1. Imperative สั่งขั้นตอนทีละขั้น; declarative บอกสถานะที่ต้องการแล้วเครื่องมือคำนวณและทำให้ตรงเอง
2. Resource = สิ่งที่ Terraform สร้าง/จัดการ; data source = อ่านข้อมูลของสิ่งที่มีอยู่โดยไม่จัดการ
3. เชื่อม resource ในโค้ดกับทรัพยากรจริงเพื่อคำนวณ diff — เก็บใน remote backend ที่เข้ารหัส มี lock และจำกัดสิทธิ์ ไม่ commit ลง Git
4. ป้องกันคนหรือ pipeline สองตัว apply พร้อมกันจน state เสียหาย
5. หยุดทบทวน — ทรัพยากรจะถูกลบแล้วสร้างใหม่ อาจกระทบบริการ พิจารณาทางเลือก (create_before_destroy, เปลี่ยนแนวทาง, maintenance window)
6. ทรัพยากรจริงถูกแก้นอก Terraform จนต่างจากโค้ด — ตรวจด้วย `terraform plan -refresh-only` หรือ `-detailed-exitcode` ตามรอบ
7. for_each ใช้ key คงที่ การเพิ่ม/ลบรายการไม่ทำให้ resource อื่นถูกสร้างใหม่ ต่างจาก count ที่อิง index
8. 10.20.5.0/24
9. Terraform สำหรับ provisioning ทรัพยากรผ่าน API (VPC, SG, DNS, firewall object); Ansible สำหรับ configuration ในอุปกรณ์/OS
10. PR → fmt/validate/lint/security scan → plan โพสต์ให้ review → approval → apply plan เดียวกัน ใช้ OIDC credential อายุสั้น remote state + lock และตรวจ drift รายวัน
</details>

---

➡️ ต่อไป: **Level 86 — Monitoring & Observability**
