# บทเรียน Level 83 — APIs: REST, NETCONF, RESTCONF, YANG, gNMI (ฉบับละเอียด)

> อ่านจบแล้วจะ: เข้าใจว่าทำไม API ดีกว่า screen-scraping CLI · พื้นฐาน REST (method, status code, JSON, auth, pagination, rate limit) · YANG data model · NETCONF (datastores, edit-config, commit, rollback) · RESTCONF · gNMI และ streaming telemetry · OpenConfig · controller API (Meraki, Catalyst Center ฯลฯ) · ใช้ curl/Postman/Python ได้

---

## 1. ทำไมต้องใช้ API

| CLI + screen scraping | API |
|---|---|
| Output ออกแบบให้คนอ่าน — ต้อง parse เอง | **ข้อมูลมีโครงสร้าง** (JSON/XML) |
| รูปแบบเปลี่ยนตาม version → parser พัง | มี **schema (YANG)** ชัดเจน |
| ส่งทีละบรรทัด ผิดกลางทางค้างครึ่ง ๆ | **transaction**: validate ทั้งก้อน, commit พร้อมกัน, rollback |
| ไม่รู้ว่าสำเร็จไหมนอกจากอ่าน text | status/error ชัดเจน |

```
 วิวัฒนาการ: CLI → SNMP (อ่านได้ดี เขียนแย่) → REST API/NETCONF/RESTCONF (YANG) → gNMI streaming telemetry
```

---

## 2. พื้นฐาน REST API

### HTTP Methods ↔ CRUD

| Method | ความหมาย | ตัวอย่าง |
|---|---|---|
| **GET** | อ่าน | ดูรายการ interface |
| **POST** | สร้างใหม่ | สร้าง VLAN |
| **PUT** | แทนที่ทั้งก้อน | ตั้ง interface ใหม่ทั้งหมด |
| **PATCH** | แก้บางส่วน (merge) | แก้ description |
| **DELETE** | ลบ | ลบ loopback |

### Status Codes

| Code | ความหมาย |
|---|---|
| 200 OK / 201 Created / 204 No Content | สำเร็จ |
| 400 Bad Request | ข้อมูลที่ส่งผิดรูปแบบ |
| **401 Unauthorized** | ยังไม่ยืนยันตัวตน/token ผิด |
| **403 Forbidden** | ยืนยันแล้วแต่ไม่มีสิทธิ์ |
| 404 Not Found | URL/ทรัพยากรไม่มี |
| 409 Conflict | ขัดแย้ง (มีอยู่แล้ว) |
| **429 Too Many Requests** | เกิน rate limit — รอ (ดู header `Retry-After`) |
| 5xx | ฝั่ง server ผิดพลาด |

### JSON
```json
{
  "hostname": "SW-ACC-01",
  "interfaces": [
    {"name": "Gi1/0/1", "enabled": true, "vlan": 10},
    {"name": "Gi1/0/2", "enabled": false, "vlan": null}
  ]
}
```
### Authentication ที่พบบ่อย

| วิธี | หมายเหตุ |
|---|---|
| Basic auth (user:password base64) | ต้องใช้กับ HTTPS เท่านั้น |
| **API key / token** ใน header (`X-Cisco-Meraki-API-Key`, `Authorization: Bearer ...`) | นิยม · เก็บใน vault, กำหนดสิทธิ์/อายุ |
| Session token (login → ได้ token → ใช้ต่อ) | Catalyst Center, FortiGate (บางแบบ), Palo Alto |
| **OAuth 2.0** | cloud API (Microsoft Graph, Google) |

### Pagination & Rate limit
- API คืนข้อมูลทีละหน้า (`?page=`, `perPage`, header `Link`/`next`) → ต้องวน loop จนครบ
- **Rate limit** (เช่น Meraki ~10 requests/วินาทีต่อ org) → ใช้ retry with backoff

### เครื่องมือ
```bash
curl -s -H "Authorization: Bearer $TOKEN" https://api.example.com/v1/devices | jq '.[] | {name, serial}'
```
- **Postman/Bruno/Insomnia** — ทดลอง API แบบ GUI, เก็บ collection
- **Python `requests`/`httpx`**, SDK ของผู้ผลิต (meraki, dnacentersdk, pan-os-python, fortiosapi)
- เอกสาร API มักอยู่ในรูป **OpenAPI/Swagger**

---

## 3. YANG — ภาษาบรรยายโครงสร้างข้อมูล

**YANG (RFC 7950)** = "schema" บอกว่า config/state ของอุปกรณ์มีหน้าตาอย่างไร (ไม่ใช่ protocol — เป็น **data model**)
```yang
module example-interfaces {
  container interfaces {
    list interface {
      key "name";
      leaf name        { type string; }
      leaf description { type string; }
      leaf enabled     { type boolean; default true; }
      leaf mtu         { type uint16 { range "68..9216"; } }
    }
  }
}
```

| องค์ประกอบ | ความหมาย |
|---|---|
| **module** | ไฟล์ model หนึ่ง |
| **container** | กลุ่มข้อมูล (เหมือน folder) |
| **list** (มี key) | รายการหลายรายการ (เช่น interface หลายตัว) |
| **leaf** | ค่าเดี่ยว (มี type) |
| leaf-list | รายการค่าเดี่ยว |
| config true/false | ค่าตั้ง vs สถานะ (operational state เช่น counters) |

### แหล่ง YANG model

| ประเภท | ตัวอย่าง |
|---|---|
| **IETF** (มาตรฐาน) | `ietf-interfaces`, `ietf-ip`, `ietf-routing` |
| **OpenConfig** (กลุ่มผู้ให้บริการขนาดใหญ่) ⭐ | `openconfig-interfaces`, `openconfig-bgp` — **ข้ามยี่ห้อ** |
| **Native/Vendor** | `Cisco-IOS-XE-native`, Junos models — ครบฟีเจอร์ที่สุดแต่ผูกยี่ห้อ |

เครื่องมือ: `pyang` (แสดง tree), YANG Suite (Cisco), GitHub `YangModels/yang`
```bash
pyang -f tree ietf-interfaces.yang
```

---

## 4. NETCONF (RFC 6241)

**Protocol** สำหรับจัดการ config ด้วย XML ผ่าน **SSH port 830**
```
 Client (ncclient) ──SSH 830──► Device
   <hello> แลก capabilities (รองรับ model/ฟีเจอร์อะไร)
   <rpc> get-config / edit-config / commit / lock ...
   <rpc-reply> ok / data / rpc-error
```
### Datastores

| Datastore | ความหมาย |
|---|---|
| **running** | config ที่ใช้งานอยู่ |
| **candidate** | พื้นที่ร่าง — แก้หลายอย่างแล้ว **validate + commit ทีเดียว** (atomic) |
| startup | config ตอนบูต |

### Operations สำคัญ
`get` (config + state) · `get-config` · `edit-config` (operation: merge/replace/create/delete/remove) · `lock`/`unlock` (กันคนอื่นแก้พร้อมกัน) · `validate` · `commit` (+ **confirmed commit**: ถ้าไม่ยืนยันภายในเวลาที่กำหนด → rollback อัตโนมัติ ⭐ กันตัดตัวเอง) · `discard-changes`

### เปิดใช้ (IOS-XE)
```
netconf-yang
! (ต้องมี AAA และ user privilege 15)
```
### Python ncclient
```python
from ncclient import manager
cfg = """
<config>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>Loopback100</name>
      <description>Created by NETCONF</description>
      <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:softwareLoopback</type>
      <enabled>true</enabled>
    </interface>
  </interfaces>
</config>"""
with manager.connect(host="10.0.0.1", port=830, username=user, password=pw,
                     hostkey_verify=True) as m:
    print([c for c in m.server_capabilities if "ietf-interfaces" in c])
    flt = '<filter><interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces"/></filter>'
    print(m.get_config(source="running", filter=flt).xml)
    m.edit_config(target="running", config=cfg)    # ถ้ารองรับ candidate: target="candidate" แล้ว m.commit()
```

---

## 5. RESTCONF (RFC 8040)

**REST-style API บน HTTPS** ที่ใช้ **YANG model เดียวกับ NETCONF** (JSON หรือ XML)
```
 URL:  https://<device>/restconf/data/<module>:<container>/<list>=<key>
 ตัวอย่าง: /restconf/data/ietf-interfaces:interfaces/interface=GigabitEthernet1
 Headers: Accept / Content-Type: application/yang-data+json
```
```bash
curl -s -u "$U:$P" --cacert ca.pem \
  -H "Accept: application/yang-data+json" \
  https://10.0.0.1/restconf/data/ietf-interfaces:interfaces/interface=GigabitEthernet1
```
```python
import requests
url = "https://10.0.0.1/restconf/data/ietf-interfaces:interfaces/interface=Loopback101"
hdr = {"Accept": "application/yang-data+json", "Content-Type": "application/yang-data+json"}
body = {"ietf-interfaces:interface": {
          "name": "Loopback101", "description": "via RESTCONF",
          "type": "iana-if-type:softwareLoopback", "enabled": True}}
r = requests.put(url, json=body, auth=(user, pw), headers=hdr, verify="ca.pem", timeout=15)
print(r.status_code)          # 201 Created หรือ 204 No Content
```

| NETCONF | RESTCONF |
|---|---|
| SSH 830, XML | HTTPS 443, JSON/XML |
| candidate datastore, lock, confirmed commit | ไม่มี candidate/transaction หลายขั้น (แต่ละ request = 1 การเปลี่ยน) |
| เหมาะกับ automation ที่ต้องการ transaction | เหมาะกับการเรียกง่าย ๆ/เว็บ |

⚠️ อย่าใช้ `verify=False` ใน production — ใช้ cert ที่ถูกต้อง (Level 65)

---

## 6. gNMI และ Streaming Telemetry

**gNMI (gRPC Network Management Interface)** = protocol บน **gRPC (HTTP/2 + Protocol Buffers)** ใช้ได้ทั้ง get/set config และ **subscribe** (telemetry)

### SNMP Polling vs Streaming Telemetry

| | SNMP polling | Streaming telemetry (gNMI) |
|---|---|---|
| รูปแบบ | NMS ถามทุก 1–5 นาที (pull) | อุปกรณ์ **push** ข้อมูลเอง |
| ความละเอียด | หยาบ (เห็นค่าเฉลี่ย) | **ทุก 1–10 วินาที** หรือเมื่อเปลี่ยน (on-change) — เห็น microburst ได้ดีขึ้น |
| ข้อมูล | MIB/OID | YANG path (OpenConfig) — structured |
| ประสิทธิภาพ | โหลด CPU จากการถาม | encoding ไบนารีมีประสิทธิภาพ |
| ความปลอดภัย | SNMPv3 | TLS (mTLS) |

### Subscription modes
- **SAMPLE** — ส่งทุก N วินาที (counters)
- **ON_CHANGE** — ส่งเมื่อค่าเปลี่ยน (สถานะ interface/BGP)
- ONCE / POLL

### ตัวอย่าง gnmic
```bash
gnmic -a 10.0.20.11:6030 -u admin -p "$P" --tls-ca ca.pem \
  subscribe --path "/interfaces/interface[name=Ethernet1]/state/counters" \
  --mode stream --stream-mode sample --sample-interval 10s
gnmic -a 10.0.20.11:6030 ... get --path /system/state/hostname
gnmic ... set --update-path /interfaces/interface[name=Ethernet2]/config/description --update-value "uplink"
```
### Pipeline ที่นิยม
```
 Devices ──gNMI──► gnmic / Telegraf ──► Prometheus / InfluxDB ──► Grafana (dashboard + alert)
                                   └─► Kafka (สำหรับองค์กรใหญ่)
```
(Model-driven telemetry ของ Cisco บาง platform ใช้ dial-out gRPC — แนวคิดเดียวกัน)

---

## 7. Controller / Cloud APIs

ในองค์กรจริงมักคุยกับ **controller** มากกว่าอุปกรณ์ตรง ๆ

| ระบบ | ใช้ทำอะไรได้ |
|---|---|
| **Cisco Meraki Dashboard API** | inventory, client, SSID, VLAN, firmware ของหลายร้อย site |
| **Cisco Catalyst Center (DNA Center)** | inventory, template deploy, assurance, path trace |
| **Arista CloudVision** | config, telemetry, change control |
| **Fortinet FortiGate/FortiManager** | policy, object, VPN |
| **Palo Alto PAN-OS/Panorama** | security policy, object (XML API/REST) |
| Juniper Mist / Apstra | Wi-Fi/wired AI-ops, DC intent |
| Cloud provider API/SDK | VPC, SG, LB (มักใช้ผ่าน Terraform — Level 85) |

```python
import meraki, os
dash = meraki.DashboardAPI(os.environ["MERAKI_API_KEY"], suppress_logging=True)  # SDK จัดการ rate limit/pagination
orgs = dash.organizations.getOrganizations()
devices = dash.organizations.getOrganizationDevices(orgs[0]["id"], total_pages="all")
for d in devices:
    print(d["name"], d["model"], d["serial"], d.get("firmware"))
```

---

## 8. Webhooks — API แบบกลับทิศ

แทนที่เราจะถามซ้ำ ๆ → **ระบบส่ง HTTP POST มาหาเราเมื่อเกิดเหตุการณ์** (alert, การเปลี่ยนแปลงใน NetBox, device offline)
- ใช้ต่อกับ automation (ChatOps แจ้ง Teams, trigger pipeline — Level 89)
- ต้องตรวจ **signature/secret** ของ webhook ว่ามาจากแหล่งจริง

---

## 9. สร้าง API ภายในทีม

ห่อ automation เป็น API ให้ระบบอื่น/ทีมอื่นเรียก (เช่น ITSM เปิด ticket แล้วเรียก API เปลี่ยน VLAN)
```python
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
app = FastAPI(title="Network API")
class VlanChange(BaseModel):
    switch: str
    port: str = Field(pattern=r"^Gi\d/0/\d{1,2}$")
    vlan: int = Field(ge=2, le=4094)
@app.post("/v1/port-vlan")
def set_port_vlan(req: VlanChange, user=Depends(verify_token)):   # auth + audit log
    if req.vlan not in ALLOWED_VLANS:
        raise HTTPException(403, "VLAN not allowed")
    ...  # เรียก Nornir/Netmiko ตั้งค่า + บันทึก audit
    return {"status": "ok"}
```
หลักการ: **validate input เข้มงวด**, auth + RBAC, audit log, จำกัดสิ่งที่ทำได้ (allowlist)

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| YANG คือ protocol | YANG คือ data model — NETCONF/RESTCONF/gNMI คือ protocol ที่ใช้ model |
| 401 กับ 403 เหมือนกัน | 401 ยังไม่ยืนยันตัวตน, 403 ยืนยันแล้วแต่ไม่มีสิทธิ์ |
| RESTCONF ทำ transaction หลายขั้นได้เหมือน NETCONF | NETCONF มี candidate/lock/confirmed commit |
| Telemetry แค่ SNMP ที่ถี่ขึ้น | push-based, structured (YANG), on-change, encoding มีประสิทธิภาพ |
| `verify=False` ใช้ได้ไม่เป็นไร | เปิดช่อง MITM — ใช้ CA ที่ถูกต้อง |

---

## 11. Cheat Sheet

```
REST: GET/POST/PUT/PATCH/DELETE · 200/201/204 · 400 · 401 vs 403 · 404 · 409 · 429 (Retry-After) · 5xx
Auth: API key/Bearer token/session/OAuth · pagination · rate limit + backoff · OpenAPI
YANG: module/container/list(key)/leaf · IETF · OpenConfig (ข้ามยี่ห้อ) · native · pyang -f tree
NETCONF: SSH 830 · XML · running/candidate/startup · edit-config · lock · validate · commit · confirmed commit
RESTCONF: HTTPS · /restconf/data/<module>:<path> · application/yang-data+json
gNMI: gRPC · get/set/subscribe · SAMPLE / ON_CHANGE · gnmic → Prometheus/Influx → Grafana
Controllers: Meraki, Catalyst Center, CloudVision, FortiManager, Panorama · webhooks (ตรวจ signature)
```

---

## 12. แบบทดสอบ 10 ข้อ

1. ข้อดีของ API เมื่อเทียบกับ screen-scraping CLI (3 ข้อ)
2. PUT กับ PATCH ต่างกันอย่างไร
3. ได้ HTTP 429 ควรทำอย่างไร
4. YANG คืออะไร และ OpenConfig มีประโยชน์อย่างไร
5. NETCONF ใช้ transport และ port อะไร
6. Candidate datastore และ confirmed commit มีประโยชน์อย่างไร
7. RESTCONF URL สำหรับ interface GigabitEthernet1 ใน ietf-interfaces เขียนอย่างไร
8. Streaming telemetry ดีกว่า SNMP polling อย่างไร
9. SAMPLE กับ ON_CHANGE ควรใช้กับข้อมูลแบบใด
10. หากสร้าง API ภายในให้ helpdesk เปลี่ยน VLAN ต้องคำนึงถึงอะไรบ้าง

<details><summary><b>เฉลย</b></summary>

1. ข้อมูลมีโครงสร้าง (ไม่ต้อง parse), มี schema ไม่พังเมื่อ output เปลี่ยน, transaction/validate/rollback, error ชัดเจน
2. PUT แทนที่ทรัพยากรทั้งก้อน; PATCH แก้เฉพาะบางส่วน (merge)
3. หยุดรอตาม Retry-After/backoff แล้วลองใหม่ และลดอัตราการเรียก
4. ภาษากำหนด data model ของ config/state; OpenConfig เป็น model กลางที่ใช้ได้ข้ามยี่ห้อ
5. SSH port 830 (ข้อมูลเป็น XML)
6. แก้หลายอย่างในพื้นที่ร่างแล้ว validate/commit พร้อมกัน (atomic); confirmed commit ย้อนกลับอัตโนมัติถ้าไม่ยืนยันภายในเวลา ป้องกันตัดการเชื่อมต่อตัวเอง
7. `https://<device>/restconf/data/ietf-interfaces:interfaces/interface=GigabitEthernet1`
8. อุปกรณ์ push ข้อมูลเอง ความละเอียดสูง (วินาที/on-change), ข้อมูลมีโครงสร้างตาม YANG, encoding มีประสิทธิภาพ, ใช้ TLS
9. SAMPLE สำหรับค่าที่เปลี่ยนตลอด (counters/utilization); ON_CHANGE สำหรับสถานะ (interface up/down, BGP state)
10. Validate input เข้ม (allowlist VLAN/พอร์ต), authentication + RBAC, audit log, จำกัดสิ่งที่ทำได้, ใช้ HTTPS, เก็บ credential อุปกรณ์อย่างปลอดภัย
</details>

---

➡️ ต่อไป: **Level 84 — Git, CI/CD & NetDevOps**
