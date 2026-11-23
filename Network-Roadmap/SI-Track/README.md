# 🏢 SI-Track: Level 1–100 สำหรับงาน System Integrator

หลักสูตรนี้เน้น **4 บริการหลัก** ของบริษัท System Integrator (SI) ที่ให้บริการโครงสร้างพื้นฐานไอทีแก่องค์กร

| บริการ | ขอบเขต | Level |
|---|---|---|
| 🗄️ **วางระบบศูนย์ข้อมูล (Data Center)** | ออกแบบโครงสร้างพื้นฐาน Server, Storage SAN, High-Availability Cluster | 21–40 |
| 🔒 **ความปลอดภัยไซเบอร์ (Cybersecurity)** | Next-Gen Firewall, Zero Trust Segmentation และระบบเฝ้าระวังภัยคุกคาม | 41–60 |
| ☁️ **คลาวด์และเวอร์ชวลไลเซชัน (Cloud & HCI)** | Hyper-Converged Infrastructure (HCI) และการทำ Cloud Migration แบบไร้รอยต่อ | 61–80 |
| 🎧 **บริการสนับสนุน 24x7 (Support & Maintenance)** | ดูแลระบบฉุกเฉินและบำรุงรักษาเชิงป้องกันตลอดเวลา | 81–100 |

แต่ละ Level มี **สิ่งที่ต้องรู้**, **แบบทดสอบ 5 ข้อ** (เฉลยซ่อนไว้ ต้องกดเปิดเอง) และ **5 โปรเจค** ไล่ความยาก ⭐ → ⭐⭐⭐
Level 20 ของแต่ละ Part (40, 60, 80, 100) เป็น **Capstone** จากโจทย์ลูกค้าจำลอง

---

## 📚 สารบัญ

| ไฟล์ | Level | เนื้อหา |
|---|---|---|
| [00-foundation.md](00-foundation.md) | 1–20 | พื้นฐาน Network ที่งาน SI ต้องใช้ (ลิงก์ไป Roadmap หลัก + SI Checkpoint + 5 โปรเจคปิด Part) |
| [01-datacenter-a.md](01-datacenter-a.md) | 21–30 | DC fundamentals, Server, Sizing, Storage, FC SAN, iSCSI/NVMe-oF, Storage arrays, vSphere, HA Cluster, App/DB HA |
| [02-datacenter-b.md](02-datacenter-b.md) | 31–40 | Backup, DR, DC network, VXLAN/ACI/NSX, DC security, Monitoring/DCIM, Pre-sales, Implementation, Handover, **Capstone DC** |
| [03-security-a.md](03-security-a.md) | 41–50 | Security for SI, NGFW concepts, FortiGate, Palo Alto, Firewall HA/migration, SSL inspection, VPN/ZTNA, Zero Trust, **Zero Trust Segmentation**, NAC |
| [04-security-b.md](04-security-b.md) | 51–60 | EDR/XDR, Email/Identity, SIEM, SOC, NDR, Vuln mgmt, Incident Response, Compliance, DC/Cloud security, **Capstone Security** |
| [05-cloud-hci-a.md](05-cloud-hci-a.md) | 61–70 | Hypervisors, HCI concepts, Nutanix, vSAN/VCF, Azure Local/Proxmox-Ceph, HCI sizing, HCI network, Lifecycle, Cloud fundamentals, AWS/Azure |
| [06-cloud-hci-b.md](06-cloud-hci-b.md) | 71–80 | Hybrid connectivity, Migration strategy (7Rs), **Seamless cutover tools**, DB/data migration, Cloud DR, Governance/FinOps, IaC, Kubernetes, Hybrid ops, **Capstone Cloud & HCI** |
| [07-support-a.md](07-support-a.md) | 81–90 | SLA/severity, ITIL, Ticketing, NOC 24x7, Triage, Network/Security incidents, Server/Storage incidents, Vendor TAC/RMA, Remote support security, Incident communication |
| [08-support-b.md](08-support-b.md) | 91–100 | **Preventive Maintenance**, Patch lifecycle, Backup/DR drill, Change mgmt, Knowledge base, Service reporting, On-call 24x7, Automation, Career in SI, **Final Capstone** |

---

## 🧭 วิธีใช้

1. **ทุกคนเริ่มที่ Level 1–20** (พื้นฐาน Network) ถ้าผ่านแบบทดสอบได้แล้วให้ข้ามไปทำ 5 โปรเจคปิด Part 0
2. **ทำ Part 1–4 ตามลำดับ** แนะนำให้ทำตามลำดับเพราะงานจริงไล่จาก DC → Security → Cloud/HCI → Support หรือข้ามไป Part ที่ตรงกับตำแหน่งงานก่อนก็ได้
   - ตำแหน่ง **Support/NOC Engineer** → Part 0 → Part 4 → ย้อนไปทำ Part ที่ดูแล
   - ตำแหน่ง **Security Engineer** → Part 0 → Part 2 → Part 4
   - ตำแหน่ง **System/Virtualization Engineer** → Part 0 → Part 1 → Part 3 → Part 4
   - ตำแหน่ง **Pre-sales/Solution Architect** → ทำครบทุก Part (เน้น L37, L66, L72 และ Capstone)
3. **เกณฑ์ผ่าน Level:** ทำแบบทดสอบได้ ≥ 4/5 ข้อ และทำโปรเจคอย่างน้อย 3 ชิ้น (ใน 3 ชิ้นนั้นต้องเป็น ⭐⭐ ขึ้นไป 1 ชิ้น)
4. **เก็บผลงานใน Git**: เอกสาร HLD/LLD, runbook, report และ script ทั้งหมดใช้เป็น portfolio ตอนสมัครงาน (L99)

---

## 🛠️ Lab ที่ต้องใช้ (ฟรีหรือ trial)

| ด้าน | เครื่องมือ |
|---|---|
| Data Center | VMware vSphere (eval / VMUG Advantage / Hands-on Labs), Proxmox VE, TrueNAS, Veeam Community Edition, DMTF Redfish mockup |
| Security | FortiGate VM (eval), Palo Alto VM / labs, Wazuh, Security Onion, Suricata, Nessus Essentials, Microsoft Sentinel/Defender trial |
| Cloud & HCI | Nutanix Community Edition, Proxmox + Ceph, Windows Server (S2D eval), AWS Free Tier, Azure free account, Terraform, Packer |
| Support | Zabbix, Grafana, GLPI / Jira Service Management (free), BookStack/Wiki.js, Vaultwarden, Apache Guacamole, Uptime Kuma |

> เครื่องที่แนะนำ: RAM 64 GB ขึ้นไป สำหรับ nested virtualization/HCI (ถ้ามีน้อยกว่านี้ ใช้ Hands-on Labs ของ vendor และ cloud แทน)
> ⚠️ **ลบทรัพยากรบน cloud หลังทำ lab ทุกครั้ง** และทำ lab ด้าน security เฉพาะในเครือข่ายของตัวเองเท่านั้น

---

## ✅ ตารางติดตามความคืบหน้า

<details><summary>Part 0–2 (Level 1–60)</summary>

- Part 0: [ ] 1–5 · [ ] 6–10 · [ ] 11–15 · [ ] 16–20 · [ ] โปรเจคปิด Part
- [ ] 21 DC basics · [ ] 22 Server HW · [ ] 23 Sizing · [ ] 24 Storage · [ ] 25 FC SAN
- [ ] 26 iSCSI/NVMe · [ ] 27 Arrays · [ ] 28 vSphere · [ ] 29 HA Cluster · [ ] 30 App/DB HA
- [ ] 31 Backup · [ ] 32 DR · [ ] 33 DC network · [ ] 34 Fabric/SDN · [ ] 35 DC security
- [ ] 36 Monitoring/DCIM · [ ] 37 Pre-sales · [ ] 38 Implementation · [ ] 39 Handover · [ ] 40 **Capstone DC**
- [ ] 41 Sec for SI · [ ] 42 NGFW · [ ] 43 FortiGate · [ ] 44 Palo Alto · [ ] 45 FW HA/Migration
- [ ] 46 SSL inspection · [ ] 47 VPN/ZTNA · [ ] 48 Zero Trust · [ ] 49 ZT Segmentation · [ ] 50 NAC
- [ ] 51 EDR/XDR · [ ] 52 Email/Identity · [ ] 53 SIEM · [ ] 54 SOC · [ ] 55 NDR
- [ ] 56 Vuln mgmt · [ ] 57 IR · [ ] 58 Compliance · [ ] 59 DC/Cloud sec · [ ] 60 **Capstone Security**
</details>

<details><summary>Part 3–4 (Level 61–100)</summary>

- [ ] 61 Hypervisors · [ ] 62 HCI concepts · [ ] 63 Nutanix · [ ] 64 vSAN/VCF · [ ] 65 Azure Local/Ceph
- [ ] 66 HCI sizing · [ ] 67 HCI network · [ ] 68 HCI lifecycle · [ ] 69 Cloud basics · [ ] 70 AWS/Azure
- [ ] 71 Hybrid connectivity · [ ] 72 Migration strategy · [ ] 73 Seamless cutover · [ ] 74 Data migration · [ ] 75 Cloud DR
- [ ] 76 Governance/FinOps · [ ] 77 IaC · [ ] 78 Kubernetes · [ ] 79 Hybrid ops · [ ] 80 **Capstone Cloud & HCI**
- [ ] 81 SLA · [ ] 82 ITIL · [ ] 83 Ticketing · [ ] 84 NOC · [ ] 85 Triage
- [ ] 86 Net/Sec incidents · [ ] 87 Server/Storage incidents · [ ] 88 Vendor/RMA · [ ] 89 Remote support · [ ] 90 Communication
- [ ] 91 PM · [ ] 92 Patch lifecycle · [ ] 93 Backup/DR drill · [ ] 94 Change · [ ] 95 Knowledge
- [ ] 96 Reporting · [ ] 97 On-call 24x7 · [ ] 98 Automation · [ ] 99 Career · [ ] 100 **Final Capstone**
</details>
