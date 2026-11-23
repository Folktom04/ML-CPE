# Tier 9 — Network Automation & Operations (Level 81–90)

> เป้าหมายของ Tier: ทำงานแบบ NetDevOps — เขียนโค้ดจัดการเครือข่าย, monitor, วัดผล และมี source of truth

---

## Level 81 — Python for Network Engineers

**สิ่งที่ต้องรู้**
- พื้นฐาน: data types, loops, functions, venv, pip, error handling
- Library: Netmiko (SSH multi-vendor), Paramiko, NAPALM (getters, config replace/merge), Scrapli, Nornir (concurrency)
- Parse output: TextFSM/ntc-templates, TTP, Genie
- จัดการ credential ปลอดภัย (env var, vault — ห้าม hard-code)
- concurrency: threading/asyncio สำหรับอุปกรณ์หลายร้อยตัว

```python
from netmiko import ConnectHandler
import os
dev = {"device_type": "cisco_ios", "host": "10.0.0.1",
       "username": os.environ["NET_USER"], "password": os.environ["NET_PASS"]}
with ConnectHandler(**dev) as c:
    rows = c.send_command("show ip interface brief", use_textfsm=True)
    for r in rows:
        print(r["interface"], r["status"])
```

**แบบทดสอบ**
1. `use_textfsm=True` ทำอะไร
2. NAPALM ต่างจาก Netmiko อย่างไร
3. ทำไมห้ามเก็บรหัสผ่านในโค้ด
4. Nornir เหมาะกับงานแบบไหน
5. เชื่อม 500 อุปกรณ์ทีละตัวใช้เวลานาน แก้อย่างไร

<details><summary>เฉลย</summary>

1. แปลง text output เป็น list of dict ด้วย ntc-templates
2. NAPALM ให้ API กลาง (get_facts, config diff/replace) ข้ามยี่ห้อ; Netmiko ส่งคำสั่ง CLI
3. รั่วผ่าน Git/แชร์ไฟล์ → ใช้ env/vault
4. Inventory + task ขนานจำนวนมาก (framework Python ล้วน)
5. ทำ concurrent ด้วย threading/Nornir/asyncio (Scrapli async)
</details>

**5 โปรเจค**
- ⭐ P1: สคริปต์ backup config ทุกอุปกรณ์ลงโฟลเดอร์ตามวันที่
- ⭐⭐ P2: Inventory report: hostname, model, serial, version → Excel
- ⭐⭐ P3: Compliance checker: ตรวจว่าทุกอุปกรณ์มี NTP/syslog/AAA ตาม standard
- ⭐⭐ P4: Bulk change VLAN บน 50 access switch พร้อม dry-run + rollback
- ⭐⭐⭐ P5: CLI tool (Typer/Click) "netctl" รวม backup/report/compliance + Nornir

---

## Level 82 — Ansible for Network

**สิ่งที่ต้องรู้**
- Agentless, inventory, playbook, role, variables (group_vars/host_vars), Jinja2 templates
- Collections: `cisco.ios`, `arista.eos`, `junipernetworks.junos`, `ansible.netcommon`
- Resource modules (`ios_vlans`, `ios_interfaces`) state: merged/replaced/overridden/deleted
- Idempotency, `--check --diff`, ansible-vault
- AWX/Ansible Automation Platform

```yaml
- hosts: access
  gather_facts: no
  tasks:
    - cisco.ios.ios_vlans:
        config:
          - {vlan_id: 10, name: USERS}
          - {vlan_id: 20, name: VOICE}
        state: merged
```

**แบบทดสอบ**
1. Idempotent หมายถึงอะไร
2. state `overridden` ต่างจาก `merged`
3. ทดสอบก่อน apply จริงใช้ flag อะไร
4. เก็บรหัสผ่านอย่างไร
5. connection plugin สำหรับ network CLI

<details><summary>เฉลย</summary>

1. รันกี่ครั้งผลเหมือนเดิม ไม่เปลี่ยนถ้าตรงอยู่แล้ว
2. overridden ลบสิ่งที่ไม่ได้ระบุทั้งหมด; merged เพิ่ม/แก้อย่างเดียว
3. `--check --diff`
4. ansible-vault
5. `ansible.netcommon.network_cli`
</details>

**5 โปรเจค**
- ⭐⭐ P1: Playbook ตั้ง baseline (hostname, NTP, syslog, banner) ทุกอุปกรณ์
- ⭐⭐ P2: Role สร้าง VLAN/trunk จาก host_vars
- ⭐⭐ P3: Playbook backup config + commit ลง Git อัตโนมัติ
- ⭐⭐⭐ P4: Deploy OSPF/BGP ทั้ง lab จาก YAML แล้ว verify ด้วย assertion
- ⭐⭐⭐ P5: AWX + survey form ให้ helpdesk เปลี่ยน VLAN พอร์ตได้เอง

---

## Level 83 — APIs: REST, NETCONF, RESTCONF, YANG, gNMI

**สิ่งที่ต้องรู้**
- REST: methods, JSON, authentication (token, basic, OAuth), status codes, pagination, rate limit
- YANG = data model; NETCONF (SSH 830, XML, candidate/running, commit/rollback); RESTCONF (HTTPS, JSON/XML)
- gNMI/gRPC + streaming telemetry, OpenConfig models
- Controller APIs: Meraki Dashboard, Cisco Catalyst Center, Arista CloudVision, Fortinet, Palo Alto
- Postman, `curl`, Python `requests`, `ncclient`

```python
import requests
r = requests.get("https://10.0.0.1/restconf/data/ietf-interfaces:interfaces",
                 auth=(u, p), headers={"Accept": "application/yang-data+json"}, verify="ca.pem")
print(r.json())
```

**แบบทดสอบ**
1. NETCONF ใช้ port อะไร
2. YANG คืออะไร
3. ข้อดีของ candidate datastore
4. streaming telemetry ดีกว่า SNMP polling อย่างไร
5. HTTP 429 หมายถึงอะไร

<details><summary>เฉลย</summary>

1. TCP 830 (SSH)
2. ภาษาสร้าง data model สำหรับ config/state ของอุปกรณ์
3. แก้หลายอย่างแล้ว validate/commit พร้อมกัน (atomic) + rollback
4. push แบบ real-time, ความละเอียดสูง, structured data, ไม่ต้อง poll
5. Too Many Requests (rate limit)
</details>

**5 โปรเจค**
- ⭐⭐ P1: Postman collection สำหรับ RESTCONF ของ CSR1000v (DevNet Sandbox)
- ⭐⭐ P2: ncclient: get-config + edit-config เพิ่ม loopback
- ⭐⭐ P3: Meraki/Catalyst Center API ดึงรายการ client → CSV (DevNet sandbox)
- ⭐⭐⭐ P4: gNMIc subscribe interface counters → Prometheus
- ⭐⭐⭐ P5: FastAPI service ภายใน "network API" ห่อการทำงาน (เพิ่ม VLAN, query MAC) พร้อม auth + audit log

---

## Level 84 — Git, CI/CD & NetDevOps

**สิ่งที่ต้องรู้**
- Git: commit, branch, merge, pull request, review, revert
- Config as code: เก็บ template/variables/intended config ใน Git
- CI pipeline: lint (yamllint, ansible-lint), render config, test ใน lab virtual (containerlab), Batfish analysis
- CD: deploy ด้วย approval, canary (ทีละ site), auto-rollback
- Pre/post checks (pyATS/Genie, Batfish, SuzieQ)

**แบบทดสอบ**
1. ทำไมต้องใช้ pull request กับ network change
2. Batfish ทำอะไร
3. pre/post check ใช้ทำอะไร
4. canary deployment ในเครือข่ายหมายถึง
5. ข้อมูลอะไรไม่ควร commit ลง Git

<details><summary>เฉลย</summary>

1. Peer review, ประวัติ, ทดสอบอัตโนมัติก่อน merge
2. วิเคราะห์ config แบบ offline (reachability, ACL, routing) โดยไม่ต้องรันอุปกรณ์จริง
3. เก็บ state ก่อน/หลัง change แล้ว diff ยืนยันว่าไม่มีอะไรพัง
4. deploy ไปกลุ่มเล็กก่อน ตรวจผลแล้วค่อยขยาย
5. รหัสผ่าน, key, secret, community string
</details>

**5 โปรเจค**
- ⭐⭐ P1: repo config lab + GitHub Actions lint YAML/Ansible
- ⭐⭐ P2: Pipeline render Jinja2 → diff กับ config ปัจจุบัน แสดงใน PR
- ⭐⭐⭐ P3: Batfish test: "Guest ห้ามถึง Server" รันทุก PR
- ⭐⭐⭐ P4: Pipeline สร้าง containerlab → deploy → test ping mesh → ทำลาย
- ⭐⭐⭐ P5: pyATS pre/post check + รายงาน diff อัตโนมัติหลัง change

---

## Level 85 — Infrastructure as Code: Terraform

**สิ่งที่ต้องรู้**
- Declarative, provider, resource, data source, variable, output, module
- State file (remote backend + locking), `plan` / `apply` / `destroy`, drift
- Providers: AWS/Azure/GCP, Cloudflare, Palo Alto, FortiOS, NetBox, Arista CVaaS
- Terraform vs Ansible (provisioning vs configuration), OpenTofu
- อย่าใส่ secret ใน state/โค้ด, ใช้ tag/naming convention

```hcl
resource "aws_vpc" "main" {
  cidr_block = "10.10.0.0/16"
  tags = { Name = "lab-vpc" }
}
resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.10.1.0/24"
  availability_zone = "ap-southeast-1a"
}
```

**แบบทดสอบ**
1. state file มีไว้ทำไม
2. ทำไมต้อง remote backend + lock
3. drift คืออะไร
4. Terraform vs Ansible ใช้อะไรตอนไหน
5. module มีประโยชน์อย่างไร

<details><summary>เฉลย</summary>

1. map ระหว่างโค้ดกับทรัพยากรจริง เพื่อคำนวณ diff
2. ทีมใช้ร่วมกัน ป้องกันรันพร้อมกันจน state พัง
3. ทรัพยากรจริงต่างจากโค้ด (มีคนแก้ด้วยมือ)
4. Terraform สร้าง infra (VPC, LB, firewall object); Ansible ตั้งค่าในอุปกรณ์/OS
5. reuse, มาตรฐานเดียวกัน, ลดโค้ดซ้ำ
</details>

**5 โปรเจค**
- ⭐⭐ P1: Terraform VPC module (public/private/NAT) ใช้ซ้ำได้หลาย environment
- ⭐⭐ P2: Cloudflare DNS records ด้วย Terraform
- ⭐⭐ P3: จัดการ security group rules จากไฟล์ YAML
- ⭐⭐⭐ P4: Pipeline `terraform plan` ใน PR + `apply` หลัง approve
- ⭐⭐⭐ P5: Drift detection รายวัน + แจ้งเตือน

---

## Level 86 — Monitoring & Observability

**สิ่งที่ต้องรู้**
- Metrics (Prometheus, InfluxDB), Logs (Loki/ELK), Traces; Dashboard (Grafana)
- NMS: Zabbix, LibreNMS, PRTG, Observium, SolarWinds
- สิ่งที่ต้อง monitor: up/down, bandwidth (95th percentile), errors/discards, CPU/mem, temp, BGP/OSPF neighbor, cert expiry, latency/loss (synthetic)
- Alerting: threshold, hysteresis, deduplication, on-call (PagerDuty/Opsgenie), ลด alert fatigue
- SLO/SLI, MTTD/MTTR

**แบบทดสอบ**
1. ทำไมใช้ 95th percentile ในการคิด bandwidth
2. discards กับ errors ต่างกัน
3. Synthetic monitoring คืออะไร
4. วิธีลด alert fatigue
5. MTTR คืออะไร

<details><summary>เฉลย</summary>

1. ตัด spike สั้น ๆ ออก สะท้อนการใช้งานจริง (และใช้คิดเงินกับ ISP บางแบบ)
2. Discards = ทิ้งเพราะ buffer เต็ม/policy (congestion); Errors = frame เสีย (L1/L2)
3. จำลองการใช้งานจริง (ping/HTTP/DNS) จากหลายจุดอย่างสม่ำเสมอ
4. alert เฉพาะสิ่งที่ต้อง action, group/dedupe, ตั้ง severity, มี runbook
5. Mean Time To Recover/Repair
</details>

**5 โปรเจค**
- ⭐⭐ P1: LibreNMS/Zabbix monitor อุปกรณ์ทั้ง lab ผ่าน SNMPv3
- ⭐⭐ P2: Prometheus + snmp_exporter + Grafana dashboard
- ⭐⭐ P3: blackbox_exporter ตรวจ HTTP/DNS/ICMP + alert ไป LINE/Discord
- ⭐⭐⭐ P4: Monitor BGP/OSPF neighbor state + alert เมื่อ flap
- ⭐⭐⭐ P5: กำหนด SLO ของ "internet ขององค์กร" + dashboard error budget

---

## Level 87 — Flow Analysis: NetFlow, sFlow, IPFIX

**สิ่งที่ต้องรู้**
- Flow = 5-tuple + bytes/packets/timestamp; NetFlow v5/v9, IPFIX, sFlow (sampling), J-Flow
- Exporter → Collector → Analyzer (ntopng, ElastiFlow, Akvorado, pmacct, nfdump/nfsen)
- Use case: top talkers, capacity planning, DDoS detection, security forensic, billing
- Sampling rate และความแม่นยำ, Flexible NetFlow

**แบบทดสอบ**
1. Flow ต่างจาก packet capture อย่างไร
2. sFlow ต่างจาก NetFlow
3. ใช้ flow ตรวจ DDoS อย่างไร
4. sampling 1:1000 มีผลอย่างไร
5. IPFIX คืออะไร

<details><summary>เฉลย</summary>

1. Flow เก็บ metadata สรุป (เล็ก เก็บนานได้) ไม่มี payload
2. sFlow สุ่ม packet + counter (stateless); NetFlow สร้าง flow cache บนอุปกรณ์
3. ตรวจปริมาณ pps/bps ผิดปกติไป IP เป้าหมาย, src จำนวนมาก
4. ลดโหลด แต่ flow เล็กอาจไม่เห็น ตัวเลขเป็นค่าประมาณ
5. มาตรฐาน IETF ที่พัฒนาจาก NetFlow v9
</details>

**5 โปรเจค**
- ⭐⭐ P1: softflowd/pmacct บน Linux router ส่ง NetFlow → nfdump
- ⭐⭐ P2: ntopng/Akvorado dashboard top talkers/apps
- ⭐⭐ P3: Python parse nfdump → รายงานรายวัน
- ⭐⭐⭐ P4: Flow-based DDoS detection (threshold + แจ้งเตือน)
- ⭐⭐⭐ P5: Capacity planning report 3 เดือนจาก flow + forecast (pandas/Prophet)

---

## Level 88 — SDN Concepts & Intent-Based Networking

**สิ่งที่ต้องรู้**
- SDN: แยก control plane ออกจาก data plane, controller ศูนย์กลาง, northbound/southbound API
- OpenFlow (match → action, flow table), P4 (programmable data plane)
- Controllers: ONOS, OpenDaylight, Ryu, Faucet
- ในงานจริง: Cisco ACI, VMware NSX, Catalyst Center (SD-Access), Juniper Apstra, cloud network = SDN
- Intent-based networking: กำหนด "เจตนา" → ระบบแปลงเป็น config + ตรวจสอบต่อเนื่อง

**แบบทดสอบ**
1. Northbound vs Southbound API
2. OpenFlow flow entry ประกอบด้วยอะไร
3. ข้อเสียของ controller ศูนย์กลาง
4. P4 ต่างจาก OpenFlow อย่างไร
5. ยกตัวอย่าง SDN ที่ใช้ทุกวันโดยไม่รู้ตัว

<details><summary>เฉลย</summary>

1. Northbound = แอป ↔ controller; Southbound = controller ↔ อุปกรณ์
2. Match fields, priority, counters, instructions/actions, timeouts
3. Single point of failure/scale — ต้องทำ cluster
4. P4 กำหนดวิธี parse/process packet เอง ไม่จำกัดตาม field ที่ OpenFlow รองรับ
5. Cloud VPC (AWS/Azure), Wi-Fi cloud-managed
</details>

**5 โปรเจค**
- ⭐⭐ P1: Mininet + Ryu: L2 learning switch
- ⭐⭐ P2: Ryu firewall app (block ตาม rule ใน JSON)
- ⭐⭐⭐ P3: Load balancer แบบ OpenFlow
- ⭐⭐⭐ P4: P4 tutorial (basic forwarding + ECN) บน BMv2
- ⭐⭐ P5: บทความเปรียบเทียบ ACI vs NSX vs SD-Access

---

## Level 89 — Source of Truth & IPAM (NetBox)

**สิ่งที่ต้องรู้**
- Source of Truth (SoT) = ข้อมูลที่ "ควรเป็น" (intended state)
- NetBox/Nautobot: DCIM (site, rack, device, cable), IPAM (prefix, IP, VLAN, VRF), circuits, custom fields
- API + webhooks + plugins; ใช้เป็น inventory ของ Ansible/Nornir
- Config generation จาก SoT → deploy → verify (closed loop)
- Data quality: ใครแก้ได้, validation, reconciliation กับของจริง

**แบบทดสอบ**
1. Source of Truth ต่างจาก monitoring อย่างไร
2. ทำไม Excel ไม่เหมาะเป็น IPAM ระยะยาว
3. NetBox ใช้เป็น Ansible inventory ได้อย่างไร
4. Reconciliation คืออะไร
5. ข้อมูลที่ควรมีใน NetBox อย่างน้อย

<details><summary>เฉลย</summary>

1. SoT = สิ่งที่ตั้งใจ; Monitoring = สิ่งที่เป็นจริงตอนนี้
2. ไม่มี API, validation, ความสัมพันธ์ข้อมูล, แก้ชนกัน, ไม่มีประวัติ
3. dynamic inventory plugin `netbox.netbox.nb_inventory`
4. เทียบ intended (SoT) กับ actual แล้วแก้ส่วนต่าง
5. Sites, racks, devices, interfaces, cables, prefixes, IPs, VLANs, circuits
</details>

**5 โปรเจค**
- ⭐⭐ P1: ติดตั้ง NetBox (docker) ใส่ข้อมูล lab ทั้งหมด
- ⭐⭐ P2: Import จาก discovery (Level 39) ผ่าน API (pynetbox)
- ⭐⭐⭐ P3: Generate config จาก NetBox + Jinja2 → deploy ด้วย Nornir
- ⭐⭐⭐ P4: Reconciliation report: IP/VLAN จริงไม่ตรง NetBox
- ⭐⭐⭐ P5: Webhook: เพิ่ม VLAN ใน NetBox → trigger pipeline deploy อัตโนมัติ

---

## Level 90 — Performance Testing & Tuning

**สิ่งที่ต้องรู้**
- iperf3 (TCP/UDP, parallel streams), flent, TRex (traffic generator), RFC 2544/Y.1564
- ปัจจัย: BDP/TCP window, MTU/jumbo, NIC offload (TSO/GRO/LRO), interrupt/RSS, CPU
- Linux tuning: `net.core.rmem_max`, `net.ipv4.tcp_rmem`, BBR, txqueuelen, fq qdisc
- Latency: propagation (≈5 µs/km ในไฟเบอร์), serialization, queuing, processing
- Bufferbloat, microbursts

**แบบทดสอบ**
1. กรุงเทพ–สิงคโปร์ ~1,500 km ไฟเบอร์ RTT ขั้นต่ำประมาณเท่าไร
2. iperf3 single stream ไม่ถึง 10G แต่ -P 8 ถึง แปลว่าอะไร
3. Microburst คืออะไร ทำไม monitor 5 นาทีมองไม่เห็น
4. Jumbo frame ต้องตั้งที่ไหนบ้าง
5. RFC 2544 วัดอะไร

<details><summary>เฉลย</summary>

1. 1500×5µs = 7.5 ms ทางเดียว → RTT ≈ 15 ms (จริงมากกว่าเพราะเส้นทางอ้อม)
2. ข้อจำกัดต่อ flow (CPU core/window/latency) ไม่ใช่ลิงก์
3. traffic พุ่งระดับ ms ทำ buffer ล้น → drop; ค่าเฉลี่ย 5 นาทีเกลี่ยจนไม่เห็น
4. ทุก hop ใน path (host, switch, router) ต้องรองรับเท่ากัน
5. Throughput, latency, frame loss, back-to-back
</details>

**5 โปรเจค**
- ⭐⭐ P1: Benchmark ลิงก์ใน lab ด้วย iperf3 หลายรูปแบบ + รายงาน
- ⭐⭐ P2: Tune Linux TCP สำหรับลิงก์ latency สูง (netem 200ms) วัดก่อน/หลัง
- ⭐⭐ P3: flent RRUL test ตรวจ bufferbloat
- ⭐⭐⭐ P4: TRex สร้าง traffic ทดสอบ firewall/router VM หา max pps
- ⭐⭐⭐ P5: Capstone Tier 9: NetDevOps platform — NetBox + Git + CI (Batfish/containerlab) + Ansible/Nornir + Prometheus/Grafana ครบ loop
