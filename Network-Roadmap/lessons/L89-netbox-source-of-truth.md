# บทเรียน Level 89 — Source of Truth & IPAM (NetBox) (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจ Source of Truth (intended vs actual state) · ทำไม Excel ไม่พอ · โครงสร้างข้อมูลของ NetBox (DCIM, IPAM, circuits, virtualization) · ลำดับการใส่ข้อมูล · ใช้ REST/GraphQL API และ pynetbox · ใช้ NetBox เป็น inventory ของ Ansible/Nornir · generate config จาก NetBox · webhooks/event rules · reconciliation · data governance · Nautobot และทางเลือกอื่น

---

## 1. Source of Truth (SoT) คืออะไร

**SoT** = แหล่งข้อมูลที่ **ทุกคนและทุกระบบยอมรับว่าเป็นความจริงหนึ่งเดียว** ว่าเครือข่าย "**ควรเป็นอย่างไร**" (intended state)
| | **Intended state (SoT)** | **Actual/Operational state** |
|---|---|---|
| คำถาม | ควรมีอะไร | ตอนนี้เป็นอย่างไร |
| แหล่ง | NetBox/Nautobot, Git | อุปกรณ์จริง, monitoring, telemetry |
| ตัวอย่าง | "SW-ACC-01 port Gi1/0/5 ควรอยู่ VLAN 20" | "ตอนนี้ Gi1/0/5 อยู่ VLAN 1 และ down" |

**ความต่างระหว่างสองอย่าง = drift/ปัญหา** → ตรวจจับและแก้ (reconciliation)

### ปัญหาเมื่อไม่มี SoT
- IP plan อยู่ใน Excel หลายไฟล์ หลายเวอร์ชัน → **IP ชน**, ไม่รู้ว่า IP ไหนว่าง
- ไม่รู้ว่าสาย port 23 ของ patch panel ไปที่ไหน
- automation ไม่มีข้อมูลที่เชื่อถือได้ให้ใช้ → เขียนค่า hard-code ในสคริปต์
- ข้อมูลอยู่ในหัวคนคนเดียว — คนลาออก ความรู้หายไป

### ทำไม Excel ไม่พอ
| Excel | SoT แบบ NetBox |
|---|---|
| ไม่มี API | **REST/GraphQL API** สำหรับ automation |
| ไม่มี validation (พิมพ์ IP ผิดได้, ซ้ำได้) | ตรวจรูปแบบ, ตรวจ IP ซ้ำ, ความสัมพันธ์ |
| ข้อมูลไม่เชื่อมกัน | device ↔ interface ↔ IP ↔ VLAN ↔ cable ↔ circuit เชื่อมกัน |
| แก้พร้อมกันชนกัน, ไม่มีประวัติ | หลายคนพร้อมกัน, **change log** ทุกการแก้ |
| ไม่มีสิทธิ์ละเอียด | RBAC |

---

## 2. NetBox คืออะไร

**NetBox** = open source (Python/Django) สำหรับ **DCIM + IPAM** และ SoT ของเครือข่าย (เริ่มที่ DigitalOcean, ปัจจุบันดูแลโดย NetBox Labs) — มี UI, REST API, GraphQL, plugins, webhooks/event rules, custom fields
**Nautobot** = fork ของ NetBox ที่เน้น automation platform (Jobs, GraphQL, Git integration) — แนวคิดคล้ายกัน

### ติดตั้ง (lab) ด้วย Docker
```bash
git clone -b release https://github.com/netbox-community/netbox-docker.git
cd netbox-docker
tee docker-compose.override.yml <<'EOF'
services:
  netbox:
    ports: ["8000:8080"]
EOF
docker compose pull && docker compose up -d
docker compose exec netbox /opt/netbox/netbox/manage.py createsuperuser
# เปิด http://localhost:8000
```

---

## 3. โครงสร้างข้อมูลหลัก

### DCIM (Data Center Infrastructure Management)
```
 Region (ภาค) → Site Group → Site (BKK-HQ, CNX-BR01) → Location (อาคาร/ชั้น/ห้อง) → Rack
   └── Device (SW-ACC-01)
         ├── Device Type (C9300-48P) ← Manufacturer (Cisco)   [template: interface/power port อัตโนมัติ]
         ├── Device Role (access-switch, core, firewall, AP)
         ├── Platform (cisco_ios / eos / junos)  ← ใช้บอก driver ของ automation
         ├── Status (planned / staged / active / offline / decommissioning)
         ├── Interfaces (Gi1/0/1 ... : type, mode access/tagged, VLAN, LAG, MTU, enabled)
         ├── Console/Power ports
         └── Serial, asset tag, primary IP, tenant, custom fields
   Cable: เชื่อม interface ↔ interface / front-rear port ของ patch panel → trace สายได้ end-to-end
```
### IPAM
```
 RIR (APNIC, RFC1918) → Aggregate (10.0.0.0/8)
 VRF (PROD, GUEST, MGMT) + Route Targets
 Prefix (10.10.0.0/16 container → 10.10.20.0/24 active, site=BKK, VLAN=20, role=users)
 IP Address (10.10.20.1/24 → ผูกกับ interface Vlan20 ของ CORE-01, status, DNS name, role=anycast/vip)
 IP Range (DHCP pool 10.10.20.100-200)
 VLAN Group (scope = site) → VLAN (20 USERS)
 ASN, Route target, Service (port/protocol บนอุปกรณ์)
```
- **"Get next available prefix/IP"** — จองอัตโนมัติผ่าน UI/API (กัน IP ชน)
- ตรวจ **utilization** ของ prefix

### อื่น ๆ
- **Circuits:** provider (ISP), circuit ID, bandwidth, termination ที่ site — ผูก contract
- **Virtualization:** cluster, VM, VM interfaces
- **Tenancy:** ลูกค้า/แผนก · **Contacts** · **Tags** · **Custom fields** (เช่น "maintenance contract end")
- **Config contexts:** ข้อมูล JSON ต่อ site/role/platform (เช่น NTP, syslog, DNS ของแต่ละ site) — ใช้ใน template
- **Config templates (Jinja2) + render config** ในตัว (NetBox 3.5+)

---

## 4. ลำดับการใส่ข้อมูล (สำคัญ — ทำตามลำดับเพื่อให้ความสัมพันธ์ถูก)

```
 1. Organization: Regions → Sites → Locations → Tenants
 2. DCIM พื้นฐาน: Manufacturers → Device Types (import จาก devicetype-library) → Device Roles → Platforms
 3. Racks
 4. IPAM: RIR/Aggregates → VRFs → Prefixes (container แล้วค่อยย่อย) → VLAN groups → VLANs
 5. Devices (+ interfaces มาจาก device type อัตโนมัติ)
 6. IP addresses ผูกกับ interfaces + กำหนด primary IP
 7. Cables (interface ↔ interface)
 8. Circuits / Providers
```
- **devicetype-library** (GitHub community) มี device type หลายพันรุ่นพร้อม interface — import ได้ไม่ต้องพิมพ์เอง
- ข้อมูลเริ่มต้นจำนวนมาก: **CSV/YAML bulk import** ใน UI หรือสคริปต์ API

### Naming convention ตัวอย่าง
```
 <site>-<role>-<เลข>   BKK-CORE-01, BKK-ACC-2F-03, CNX-FW-01
 Interface description: "<ปลายทาง>:<พอร์ตปลายทาง>"  เช่น "BKK-CORE-01:Te1/1/1"
```

---

## 5. ใช้ API — pynetbox

```bash
pip install pynetbox
export NETBOX_URL=http://localhost:8000 NETBOX_TOKEN=xxxxxxxx     # สร้าง token ใน UI (สิทธิ์เท่าที่ต้องการ)
```
```python
import os, pynetbox
nb = pynetbox.api(os.environ["NETBOX_URL"], token=os.environ["NETBOX_TOKEN"])

# อ่าน
for d in nb.dcim.devices.filter(site="bkk-hq", role="access-switch", status="active"):
    print(d.name, d.device_type.model, d.serial, d.primary_ip4)

# จอง prefix /24 ถัดไปจาก container แล้วจอง IP แรกเป็น gateway
container = nb.ipam.prefixes.get(prefix="10.10.0.0/16")
new = container.available_prefixes.create({"prefix_length": 24, "status": "active",
                                           "description": "CCTV BKK", "site": nb.dcim.sites.get(slug="bkk-hq").id})
gw = new.available_ips.create({"description": "gateway"})
print(new.prefix, gw.address)

# สร้าง VLAN
nb.ipam.vlans.create(vid=30, name="CCTV", site=nb.dcim.sites.get(slug="bkk-hq").id, status="active")
```
### REST ตรง ๆ และ GraphQL
```bash
curl -s -H "Authorization: Token $NETBOX_TOKEN" -H "Accept: application/json" \
  "$NETBOX_URL/api/ipam/prefixes/?site=bkk-hq&status=active" | jq '.results[].prefix'
```
```graphql
# ดึงเฉพาะข้อมูลที่ต้องการครั้งเดียว (เร็วกว่าเรียก REST หลายรอบ)
{ device_list(filters: {site: "bkk-hq"}) { name platform { slug } primary_ip4 { address }
    interfaces { name mode untagged_vlan { vid } } } }
```

---

## 6. NetBox เป็น Inventory ของ Automation

### Ansible dynamic inventory
```yaml
# netbox_inventory.yml
plugin: netbox.netbox.nb_inventory
api_endpoint: http://netbox.example.local
token: "{{ lookup('env', 'NETBOX_TOKEN') }}"
validate_certs: true
config_context: true
group_by: [sites, device_roles, platforms]
query_filters:
  - status: active
  - has_primary_ip: true
compose:
  ansible_network_os: platform.slug        # platform slug ตั้งเป็น cisco.ios.ios ฯลฯ ให้ตรง
```
```bash
ansible-inventory -i netbox_inventory.yml --graph
ansible-playbook -i netbox_inventory.yml site.yml --limit sites_bkk_hq
```
### Nornir
`nornir_netbox` plugin ใช้ NetBox เป็น inventory (filter ตาม site/role/tag)

**ผลลัพธ์:** เพิ่ม switch ใหม่ใน NetBox → automation รู้จักทันที — ไม่ต้องแก้ไฟล์ hosts

---

## 7. Generate Config จาก NetBox (Closed Loop)

```
 [NetBox: intended] ──API──► [Jinja2 render] ──► [Git/PR + CI (Level 84)] ──► [Deploy: Ansible/Nornir]
        ▲                                                                            │
        └──────────────── [Reconciliation: เทียบของจริงกับ NetBox] ◄──[Collect actual]┘
```
```jinja
{# templates/access.j2 — ข้อมูลจาก NetBox device + interfaces + config_context #}
hostname {{ device.name }}
{% for s in config_context.ntp_servers %}
ntp server {{ s }}
{% endfor %}
{% for vlan in vlans %}
vlan {{ vlan.vid }}
 name {{ vlan.name }}
{% endfor %}
{% for intf in interfaces if intf.mode and intf.mode.value == "access" %}
interface {{ intf.name }}
 description {{ intf.description or "user-port" }}
 switchport mode access
 switchport access vlan {{ intf.untagged_vlan.vid }}
 {{ "shutdown" if not intf.enabled else "no shutdown" }}
{% endfor %}
```

### Webhooks / Event Rules
เมื่อข้อมูลใน NetBox เปลี่ยน → ส่ง HTTP POST ไปยังระบบอื่น
- สร้าง VLAN ใหม่ใน NetBox → trigger pipeline (GitHub Actions/AWX) → generate config → PR → deploy
- เพิ่ม IP ใน NetBox → อัปเดต DNS (Infoblox/PowerDNS)
- อุปกรณ์ status = decommissioning → ลบจาก monitoring

---

## 8. Reconciliation — ทำให้ข้อมูลตรงกับความจริง

SoT มีค่าก็ต่อเมื่อ **ข้อมูลถูกต้อง** — ข้อมูลผิด = automation ทำผิดในขนาดใหญ่
| วิธี | รายละเอียด |
|---|---|
| **Discovery/import ครั้งแรก** | ดึงจากอุปกรณ์จริง (NAPALM getters, LLDP, ARP) → สร้างข้อมูลเริ่มต้น (ระวังนำความผิดเดิมเข้ามา — ตรวจทาน) |
| **Reconciliation report** ประจำ | เทียบ NetBox vs จริง: interface/VLAN/IP/serial/version ไม่ตรง → รายงาน |
| **Diode / ORB (NetBox Labs), Nautobot SSoT** | เครื่องมือ sync ข้อมูลจากแหล่งอื่น |
| **Sync จากระบบอื่น** | vCenter (VM), cloud (VPC/subnet), DHCP leases |
```python
# ตัวอย่าง reconciliation: serial ใน NetBox ตรงกับของจริงไหม
for d in nb.dcim.devices.filter(status="active", platform="cisco_ios"):
    actual = get_facts_via_napalm(d.primary_ip4.address.split("/")[0])
    if actual["serial_number"] != d.serial:
        print(f"MISMATCH {d.name}: netbox={d.serial} actual={actual['serial_number']}")
```
**ทิศทาง:** ข้อมูลส่วนใหญ่ควรไหล **จาก NetBox → อุปกรณ์** (NetBox คือ intent) ส่วนข้อมูล "ข้อเท็จจริง" เช่น serial/version อาจไหล **จากอุปกรณ์ → NetBox**

---

## 9. Data Governance

- **ใครแก้อะไรได้** (RBAC: helpdesk อ่าน, network team แก้ IPAM, automation account เฉพาะ API)
- **กระบวนการ:** การเปลี่ยนเครือข่ายเริ่มที่ NetBox ก่อน (planned → active) ไม่ใช่แก้อุปกรณ์แล้วค่อยมาอัปเดต
- **มาตรฐาน:** naming, tag, custom fields ที่บังคับ, **custom validators** (เช่น device ต้องมี tenant)
- **Change log/journal** เก็บประวัติ, ส่ง log ไป SIEM
- สำรองข้อมูล DB (PostgreSQL) และ media ประจำ, ทดสอบ restore
- เริ่มจาก **ขอบเขตเล็กแต่ถูกต้อง** (IPAM + devices ของ 1 site) ดีกว่าใส่ทุกอย่างแต่ผิดครึ่งหนึ่ง

---

## 10. ทางเลือกอื่น

| เครื่องมือ | หมายเหตุ |
|---|---|
| **Nautobot** | fork ของ NetBox เน้น automation (Jobs, SSoT, Golden Config app) |
| **Infoblox / BlueCat / EfficientIP (DDI)** | IPAM + DNS + DHCP เชิงพาณิชย์ (องค์กรใหญ่) — มักใช้คู่กับ NetBox |
| phpIPAM | IPAM open source เรียบง่าย |
| Cloud IPAM (AWS VPC IPAM, Azure IPAM) | เฉพาะ cloud |
| Device42, Device360 | DCIM/CMDB เชิงพาณิชย์ |
| CMDB ของ ITSM (ServiceNow) | ระดับองค์กร — sync กับ NetBox |

---

## 11. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| NetBox คือ monitoring tool | NetBox เก็บ intended state — ไม่ poll อุปกรณ์ (monitoring คือ actual) |
| ใส่ข้อมูลครั้งเดียวจบ | ต้องมีกระบวนการและ reconciliation ต่อเนื่อง |
| Import ข้อมูลจากอุปกรณ์จริงทั้งหมดได้ข้อมูลถูกต้อง | นำความผิดพลาดเดิมเข้ามาด้วย — ต้องตรวจทาน |
| Excel ก็เป็น SoT ได้ | ไม่มี API/validation/ความสัมพันธ์/ประวัติ |
| ต้องใส่ข้อมูลครบทุกอย่างก่อนใช้ | เริ่มจากส่วนเล็กที่ถูกต้องแล้วขยาย |

---

## 12. Cheat Sheet

```
SoT = intended state · Monitoring = actual · ต่างกัน = drift → reconcile
NetBox: DCIM (site/location/rack/device/type/role/platform/interface/cable) + IPAM (RIR/aggregate/VRF/prefix/IP/range/VLAN)
+ circuits · virtualization · tenancy · tags · custom fields · config contexts · config templates
ลำดับ: site → manufacturer/device type/role/platform → rack → IPAM → devices → IPs → cables → circuits
API: REST (Token) · GraphQL · pynetbox (available_prefixes/available_ips.create)
Ansible: netbox.netbox.nb_inventory · Nornir: nornir_netbox
Closed loop: NetBox → render → Git/CI → deploy → reconcile
Webhooks/event rules → pipeline/DNS/monitoring
Governance: RBAC · process (NetBox first) · naming · validators · backup
```

---

## 13. แบบทดสอบ 10 ข้อ

1. Source of Truth ต่างจาก monitoring อย่างไร
2. ทำไม Excel ไม่เหมาะเป็น IPAM ระยะยาว (4 ข้อ)
3. Device Type และ Platform ใน NetBox ใช้ทำอะไร
4. ลำดับการใส่ข้อมูลใน NetBox ที่เหมาะสม
5. จะจอง /24 ถัดไปที่ว่างจาก 10.10.0.0/16 ด้วย pynetbox อย่างไร
6. NetBox ช่วย Ansible ได้อย่างไร
7. Config context ใช้ทำอะไร
8. Webhook ของ NetBox ใช้ทำ automation อะไรได้บ้าง (2 ตัวอย่าง)
9. Reconciliation คืออะไร ยกตัวอย่าง
10. ถ้าทีม helpdesk แก้อุปกรณ์โดยตรงแล้วไม่อัปเดต NetBox จะเกิดอะไร และแก้อย่างไร

<details><summary><b>เฉลย</b></summary>

1. SoT เก็บสถานะที่ตั้งใจ (ควรเป็น); monitoring แสดงสถานะจริงปัจจุบัน
2. ไม่มี API, ไม่มี validation (IP ซ้ำ/ผิดรูปแบบ), ข้อมูลไม่สัมพันธ์กัน, แก้พร้อมกันชน/ไม่มีประวัติ, ไม่มี RBAC
3. Device Type เป็นแม่แบบรุ่น (สร้าง interface/power port อัตโนมัติ); Platform บอก OS/driver สำหรับ automation (เช่น cisco_ios)
4. Sites/locations/tenants → manufacturers/device types/roles/platforms → racks → IPAM (aggregates/VRF/prefixes/VLANs) → devices → IP ผูก interface → cables → circuits
5. `nb.ipam.prefixes.get(prefix="10.10.0.0/16").available_prefixes.create({"prefix_length": 24, ...})`
6. เป็น dynamic inventory (nb_inventory) จัดกลุ่มตาม site/role/platform พร้อมตัวแปรและ config context — เพิ่มอุปกรณ์ใน NetBox แล้ว automation รู้จักทันที
7. เก็บข้อมูล JSON ตาม site/role/platform (เช่น NTP/syslog/DNS) ให้อุปกรณ์รับค่าตามบริบท ใช้ใน template
8. เพิ่ม VLAN แล้ว trigger pipeline generate/deploy config, เพิ่ม IP แล้วอัปเดต DNS, เปลี่ยน status แล้วอัปเดต monitoring
9. การเทียบข้อมูลใน NetBox กับของจริงแล้วแก้ส่วนต่าง เช่น serial/VLAN/IP ของอุปกรณ์ไม่ตรงกับที่บันทึกไว้
10. เกิด drift — ข้อมูลใน NetBox ผิด automation อาจเขียนทับหรือทำผิดพลาด — แก้ด้วยกระบวนการ (เปลี่ยนที่ NetBox ก่อน/ผ่าน pipeline หรือ self-service), RBAC, และ reconciliation report ประจำ
</details>

---

➡️ ต่อไป: **Level 90 — Performance Testing & Tuning**
