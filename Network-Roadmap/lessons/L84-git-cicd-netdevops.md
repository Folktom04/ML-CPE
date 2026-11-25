# บทเรียน Level 84 — Git, CI/CD & NetDevOps (ฉบับละเอียด)

> อ่านจบแล้วจะ: ใช้ Git ได้คล่อง (commit, branch, merge, pull request, revert) · เข้าใจแนวคิด config as code และ NetDevOps · ออกแบบ pipeline CI (lint → render → validate ด้วย Batfish → test ใน containerlab) และ CD (approval, canary, rollback) · ทำ pre/post check ด้วย pyATS/SuzieQ · เขียน GitHub Actions ตัวอย่าง · เข้าใจ GitOps

---

## 1. NetDevOps คืออะไร

**นำแนวปฏิบัติของ software engineering มาใช้กับเครือข่าย**

| แบบเดิม | NetDevOps |
|---|---|
| แก้ config ด้วยมือผ่าน SSH | config ถูก **generate จาก template + ข้อมูล** |
| ไม่มีประวัติว่าใครแก้อะไร ทำไม | ทุกการเปลี่ยนอยู่ใน **Git** (ใคร/เมื่อไร/ทำไม/diff) |
| review ด้วยการอ่าน change request ใน Word | **Pull request** + reviewer เห็น diff จริง |
| ทดสอบบน production | ทดสอบอัตโนมัติใน **CI** (lint, Batfish, lab เสมือน) |
| ย้อนกลับด้วยความจำ | **revert** commit แล้ว deploy ใหม่ |

เป้าหมาย: **เปลี่ยนแปลงได้เร็วขึ้น และปลอดภัยขึ้นพร้อมกัน**

---

## 2. Git พื้นฐานที่ต้องคล่อง

```bash
git config --global user.name "Your Name"
git config --global user.email "you@company.example"
git init netconfig && cd netconfig       # หรือ git clone <url>
git status                               # ดูสถานะ
git add templates/ inventory/            # เลือกไฟล์ที่จะ commit
git commit -m "Add VLAN 30 (CCTV) to BKK access switches"
git log --oneline --graph                # ประวัติ
git diff                                 # สิ่งที่ยังไม่ commit
git diff main..feature/vlan30            # เทียบ branch
git show <commit>                        # ดู commit หนึ่ง
git blame templates/acl.j2               # บรรทัดนี้ใครแก้เมื่อไร
```
### Branch และ Pull Request (PR / Merge Request)
```
 main ──●──────────●────────────●──  (สิ่งที่ deploy อยู่จริง/อนุมัติแล้ว)
         \                    /
 feature  ●──●──●  ── PR ──►  (review + CI ผ่าน → merge)
```
```bash
git switch -c feature/vlan30-cctv
# แก้ไฟล์ ...
git add -A && git commit -m "Add VLAN 30 CCTV"
git push -u origin feature/vlan30-cctv
# เปิด PR บน GitHub/GitLab/Bitbucket → CI รัน → reviewer approve → merge
```
### ย้อนกลับ
```bash
git revert <commit>          # สร้าง commit ใหม่ที่ย้อนผล (ปลอดภัย เหมาะกับ branch ที่แชร์)
git restore <file>           # ทิ้งการแก้ที่ยังไม่ commit
# git reset --hard — อันตราย ใช้เฉพาะ branch ส่วนตัว
```
### Commit message ที่ดี
```
Add VLAN 30 (CCTV) to BKK access switches

- VLAN 30 /24 10.10.30.0 per IPAM ticket NET-1234
- Trunk allowed list updated on uplinks
Change: CHG0012345
```

### ห้าม commit อะไรลง Git ⚠️
**รหัสผ่าน, private key, API token, SNMP community, PSK ของ VPN** → ใช้ `.gitignore`, vault, secret scanning (gitleaks, GitHub secret scanning) — ถ้าเผลอ commit ให้ถือว่ารั่วแล้ว **เปลี่ยน credential ทันที** (ลบจากประวัติอย่างเดียวไม่พอ)

---

## 3. Config as Code — โครงสร้างที่นิยม

```
netconfig/
├── data/                 # ข้อมูล (หรือดึงจาก NetBox — Level 89)
│   ├── sites/bkk.yml
│   └── devices/sw-acc-01.yml
├── templates/            # Jinja2
│   ├── ios_access.j2
│   └── ios_core.j2
├── rendered/             # config ที่ generate (intended config)
├── tests/
│   ├── batfish/test_policy.py
│   └── lab/topology.clab.yml
├── playbooks/ (หรือ nornir/)
└── .github/workflows/ci.yml
```
**หลักการ:** "ข้อมูล" แยกจาก "template" — เปลี่ยน VLAN แก้แค่ YAML, เปลี่ยนมาตรฐานแก้แค่ template

```python
# render.py — ข้อมูล + template = intended config
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
env = Environment(loader=FileSystemLoader("templates"), undefined=StrictUndefined,  # ตัวแปรหายให้ error
                  trim_blocks=True, lstrip_blocks=True)
dev = yaml.safe_load(open("data/devices/sw-acc-01.yml"))
cfg = env.get_template("ios_access.j2").render(**dev)
open("rendered/sw-acc-01.cfg", "w").write(cfg)
```

---

## 4. CI — Continuous Integration (ทดสอบทุก PR)

```
 PR เปิด ──► ① Lint ──► ② Render ──► ③ Static analysis ──► ④ Lab test ──► ⑤ แสดงผล/diff ใน PR
            yamllint    Jinja2       Batfish                containerlab
            ansible-lint             policy checks          ping mesh/BGP
```
### ① Lint
`yamllint`, `ansible-lint`, `ruff`/`black` (Python), ตรวจ schema ของข้อมูล (JSON Schema/pydantic: VLAN 2–4094, IP ถูกรูปแบบ, ไม่ซ้ำ)

### ② Render + Diff
generate intended config แล้วแสดง **diff เทียบ config ปัจจุบัน** ใน PR → reviewer เห็นผลกระทบจริง

### ③ Batfish — วิเคราะห์ config แบบ Offline ⭐
Batfish อ่านไฟล์ config ของทั้งเครือข่าย **สร้างแบบจำลอง** แล้วตอบคำถามได้โดยไม่ต้องมีอุปกรณ์จริง:
- ACL/firewall นี้อนุญาต flow X ไหม · มี rule ที่ไม่มีวันถูกใช้ (unreachable) ไหม
- ทุก subnet ไปถึง DNS ได้ไหม · Guest ห้ามถึง Server จริงไหม
- BGP session จะขึ้นไหม (ASN/IP ตรง), IP ซ้ำ, MTU ไม่ตรง, undefined reference
```python
from pybatfish.client.session import Session
from pybatfish.datamodel.flow import HeaderConstraints
bf = Session(host="localhost")
bf.init_snapshot("rendered/", name="candidate", overwrite=True)

def test_guest_cannot_reach_servers():
    ans = bf.q.reachability(
        pathConstraints={"startLocation": "@enter(fw-01[inside-guest])"},
        headers=HeaderConstraints(srcIps="10.50.0.0/24", dstIps="10.10.100.0/24"),
        actions="SUCCESS").answer().frame()
    assert ans.empty, f"Guest reaches servers!\n{ans}"

def test_no_undefined_references():
    assert bf.q.undefinedReferences().answer().frame().empty

def test_bgp_sessions_compatible():
    df = bf.q.bgpSessionCompatibility().answer().frame()
    assert (df["Configured_Status"] == "UNIQUE_MATCH").all()
```

### ④ Lab test ด้วย containerlab
สร้าง topology เสมือน (Arista cEOS, Nokia SR Linux, FRR, Cisco IOL/XRd บางรุ่น) → deploy config ที่ render → ทดสอบ → ทำลาย
```yaml
# tests/lab/topology.clab.yml
name: ci-lab
topology:
  nodes:
    spine1: { kind: arista_ceos, image: ceos:4.32.0F, startup-config: ../../rendered/spine1.cfg }
    leaf1:  { kind: arista_ceos, image: ceos:4.32.0F, startup-config: ../../rendered/leaf1.cfg }
    leaf2:  { kind: arista_ceos, image: ceos:4.32.0F, startup-config: ../../rendered/leaf2.cfg }
  links:
    - endpoints: ["spine1:eth1", "leaf1:eth1"]
    - endpoints: ["spine1:eth2", "leaf2:eth1"]
```
```bash
sudo containerlab deploy -t tests/lab/topology.clab.yml
# รอ BGP ขึ้น → pytest ตรวจ neighbor/route/ping
sudo containerlab destroy -t tests/lab/topology.clab.yml
```
(การใช้ image ของผู้ผลิตต้องเป็นไปตาม license — ใช้ image ที่ได้รับอนุญาต)

---

## 5. CD — Continuous Delivery/Deployment

หลัง merge เข้า main:
```
 merge → ⑥ Approval (CAB/manager ใน pipeline) → ⑦ Pre-check → ⑧ Deploy canary (1 device/site)
       → ⑨ Post-check (เทียบกับ pre) → ⑩ ขยายทีละกลุ่ม → ⑪ แจ้งผล (Teams/Slack/ITSM)
       ล้มเหลวที่ขั้นใด → หยุด + rollback อัตโนมัติ (config เดิม/revert commit)
```
- เครือข่ายส่วนใหญ่ใช้ **Continuous Delivery** (มีคนกดอนุมัติ/อยู่ใน maintenance window) มากกว่า deploy อัตโนมัติ 100%
- ผูกกับ **change management** (Level 95): PR ลิงก์กับ change ticket

---

## 6. Pre/Post Check — พิสูจน์ว่าไม่มีอะไรพัง

เก็บ "ภาพถ่ายสถานะ" ก่อนและหลัง change แล้วเทียบ

| เครื่องมือ | จุดเด่น |
|---|---|
| **pyATS/Genie** (Cisco, ใช้ฟรี) | `learn` feature (ospf, bgp, interface) → `diff` อัตโนมัติ |
| **SuzieQ** | เก็บสถานะเครือข่ายหลายยี่ห้อเป็นตาราง query/assert ได้ ดูย้อนหลังได้ |
| NAPALM getters / Nornir + assert | เขียนเอง |

```bash
pyats learn ospf bgp interface routing --testbed-file testbed.yml --output pre/
# ... ทำ change ...
pyats learn ospf bgp interface routing --testbed-file testbed.yml --output post/
pyats diff pre/ post/          # แสดงเฉพาะสิ่งที่เปลี่ยน เช่น neighbor หาย, route หาย
```
**ตรวจอะไร:** interface up/down, error counters, OSPF/BGP neighbor + จำนวน prefix, routing table ขนาด, ARP/MAC count, reachability (ping จุดสำคัญ), CPU

---

## 7. ตัวอย่าง GitHub Actions

```yaml
# .github/workflows/ci.yml
name: network-ci
on:
  pull_request:
    paths: ["data/**", "templates/**", "tests/**"]
jobs:
  validate:
    runs-on: ubuntu-latest
    services:
      batfish:
        image: batfish/allinone:latest
        ports: ["9996:9996", "9997:9997"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt
      - name: Lint
        run: |
          yamllint data/
          python scripts/validate_schema.py data/
      - name: Render configs
        run: python render.py --all
      - name: Batfish policy tests
        run: pytest tests/batfish -v
      - name: Upload rendered configs
        uses: actions/upload-artifact@v4
        with: { name: rendered, path: rendered/ }
```
- Deploy ไปยังอุปกรณ์จริงมักใช้ **self-hosted runner ภายในเครือข่าย** (cloud runner เข้าถึง management network ไม่ได้และไม่ควรได้)
- เก็บ credential ใน **secrets ของ CI/vault** ไม่ใช่ใน repo · จำกัดสิทธิ์ของ runner
- **Branch protection:** ห้าม push ตรงเข้า main, ต้องมี review + CI ผ่าน

---

## 8. GitOps และ Drift

**GitOps:** Git = สถานะที่ต้องการ (desired state) → ระบบ reconcile ให้ของจริงตรงกับ Git อัตโนมัติ (ชัดเจนในโลก Kubernetes — Argo CD/Flux)
**Drift:** มีคนแก้อุปกรณ์ด้วยมือจนต่างจาก Git → ตรวจจับด้วยงานประจำ (backup config → diff กับ intended) → แจ้งเตือน/สร้าง PR/แก้กลับ
- วัฒนธรรมสำคัญกว่าเครื่องมือ: **ตกลงกันว่าแก้ผ่าน pipeline เท่านั้น** (ยกเว้น emergency ที่ต้องบันทึกย้อนหลังใน Git)

---

## 9. เริ่มต้นอย่างไรในทีมจริง (ทีละขั้น)

1. **Backup config อัตโนมัติลง Git** (เห็น diff รายวัน — ได้ประโยชน์ทันที เสี่ยงต่ำ)
2. เขียน **template + data** สำหรับมาตรฐาน (baseline) แล้ว **ตรวจ compliance** (ยังไม่ deploy)
3. เพิ่ม **CI**: lint + render + Batfish ใน PR
4. Deploy อัตโนมัติสำหรับ **งานความเสี่ยงต่ำ** (description, VLAN บน access) พร้อม pre/post check
5. ขยายไปงานที่ซับซ้อนขึ้น + lab test + GitOps

---

## 10. เรื่องที่คนมักเข้าใจผิด

| ❌ | ✅ |
|---|---|
| NetDevOps = ซื้อเครื่องมือ | เป็นกระบวนการ + วัฒนธรรม (review, test, ทำผ่าน pipeline) |
| CI/CD หมายถึง deploy production อัตโนมัติทันที | เครือข่ายมัก CD แบบมี approval + canary |
| ลบ secret ออกจาก commit ล่าสุดก็ปลอดภัย | ยังอยู่ในประวัติ — เปลี่ยน credential ทันที |
| Batfish ต้องมีอุปกรณ์จริง | วิเคราะห์จากไฟล์ config ล้วน |
| Pre/post check ไม่จำเป็นถ้า config ถูก | config ถูกแต่ผลกระทบอาจไม่คาดคิด — ต้องพิสูจน์ด้วยสถานะจริง |

---

## 11. Cheat Sheet

```
Git: add · commit · log · diff · switch -c · push · PR · merge · revert (ไม่ใช่ reset --hard)
ห้าม commit secret → .gitignore, vault, gitleaks · รั่วแล้วต้อง rotate
Config as code: data (YAML/NetBox) + template (Jinja2, StrictUndefined) = intended config
CI: lint (yamllint/schema) → render → diff ใน PR → Batfish (reachability, undefined refs, BGP) → containerlab test
CD: approval → pre-check → canary → post-check (pyATS diff/SuzieQ) → ขยาย → rollback อัตโนมัติ
Runner ภายใน + secrets ของ CI · branch protection
GitOps = Git คือ desired state + reconcile · drift detection
เริ่ม: backup→Git → compliance → CI → deploy งานเสี่ยงต่ำ
```

---

## 12. แบบทดสอบ 10 ข้อ

1. NetDevOps ต่างจากการจัดการเครือข่ายแบบเดิมอย่างไร (3 ข้อ)
2. ทำไมใช้ pull request กับการเปลี่ยน config
3. `git revert` ต่างจาก `git reset --hard` อย่างไร
4. ถ้าเผลอ commit รหัสผ่านขึ้น repo ต้องทำอะไร
5. ทำไมแยก "data" กับ "template"
6. Batfish ทำอะไรได้บ้าง ยกตัวอย่าง 3 อย่าง
7. containerlab ใช้ทำอะไรใน pipeline
8. Pre/post check ตรวจอะไรบ้าง
9. ทำไม deploy ไปอุปกรณ์จริงมักใช้ self-hosted runner
10. ทีมที่ยังไม่เคยทำ automation ควรเริ่ม NetDevOps อย่างไร

<details><summary><b>เฉลย</b></summary>

1. Config generate จาก template+data, ทุกการเปลี่ยนอยู่ใน Git มีประวัติ, review ผ่าน PR, ทดสอบอัตโนมัติก่อน deploy, rollback ด้วย revert
2. มี peer review เห็น diff จริง, CI ทดสอบอัตโนมัติก่อน merge, มีประวัติและลิงก์กับ change ticket
3. Revert สร้าง commit ใหม่ที่ย้อนผล (ประวัติยังอยู่ ปลอดภัยกับ branch ที่แชร์); reset --hard ลบประวัติ/การแก้ใน local (อันตราย)
4. ถือว่ารั่วแล้ว — เปลี่ยน credential ทันที แล้วจึงลบออกจากประวัติ และตั้ง secret scanning/vault
5. เปลี่ยนค่า (VLAN/IP) แก้แค่ข้อมูล; เปลี่ยนมาตรฐานแก้แค่ template — ลดความผิดพลาดและทำซ้ำได้
6. ตรวจ reachability/ACL (Guest ห้ามถึง Server), undefined references, BGP session compatibility, IP ซ้ำ, unreachable ACL lines
7. สร้าง lab เสมือนจาก config ที่ render แล้วทดสอบการทำงานจริง (neighbor, route, ping) ก่อน deploy แล้วทำลายทิ้ง
8. Interface status/errors, OSPF/BGP neighbors และจำนวน prefix, routing table, ARP/MAC, reachability ของจุดสำคัญ, CPU
9. Runner ต้องเข้าถึง management network ภายในได้ ซึ่ง cloud runner ไม่ควรเข้าถึง และเพื่อควบคุม credential/ความปลอดภัย
10. เริ่มจาก backup config ลง Git อัตโนมัติ → compliance check ด้วย template → เพิ่ม CI (lint/render/Batfish) → deploy อัตโนมัติสำหรับงานเสี่ยงต่ำพร้อม pre/post check → ขยาย
</details>

---

➡️ ต่อไป: **Level 85 — Infrastructure as Code: Terraform**
