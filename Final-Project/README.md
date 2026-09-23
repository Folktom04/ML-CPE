# UV Guard ☀️

ระบบ Machine Learning วิเคราะห์ความเข้มข้นรังสี UV (UVI, UVA, UVB) และระดับความเสี่ยงต่อผิวตามประเภทผิว พร้อมแอปมือถือแจ้งเตือน

> ค่าเวลาไหม้และผลต่อผิวเป็นค่าประมาณเพื่อการศึกษาและการเตือนภัยทั่วไป ไม่ใช่การวินิจฉัยทางการแพทย์

## Architecture
GPS / เวลา / Open-Meteo / lux / ภาพท้องฟ้า → Feature Engineering → Clear-sky physics (UVI, UVA, UVB) × CMF จาก ML (XGBoost + CNN, Stacking) → Quantile range → Risk Engine → FastAPI → Expo App + Notifications

## Structure
| Folder | Content |
|---|---|
| `source_code/src/` | data fetching, physics, features, training, risk engine |
| `source_code/notebooks/` | EDA and experiments |
| `source_code/api/` | FastAPI service + scheduler |
| `source_code/app/` | Expo (React Native) app |
| `dataset/field/` | ข้อมูลภาคสนามจากมือถือ (lux, ภาพท้องฟ้า) |

ระบบใช้ **สมาร์ทโฟนเครื่องเดียว** ไม่มีเซนเซอร์หรือโมดูลเสริม ค่าอ้างอิงมาจาก Open-Meteo (แบบจำลอง) ไม่ใช่เครื่องวัด UV จริง
| `docs/` | diagrams, figures, report |

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest -q
```

ดูแผนงานทั้งหมดใน [ROADMAP.md](ROADMAP.md)
