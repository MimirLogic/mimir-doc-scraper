# ⚙️ Mill Cert Scraper
### AI-Powered Multi-Document Extraction & Reconciliation for Weld Stud Certifications

Built by [Mimir Logic](https://github.com/MimirLogic) — AI tools for the people who actually run the machines.

---

## What It Does

Manufacturing quality certifications require data from three separate documents — a mill cert from the steel supplier, a mechanical test report from an independent lab, and a customer invoice. Traditionally this means someone manually reading all three, cross-referencing heat numbers, and typing everything into a cert form by hand.

This app eliminates that process entirely.

Upload the documents. The AI extracts, classifies, and reconciles the data automatically. Review, edit if needed, and generate a completed Weld Stud Certification in seconds.

---

## Two-Mode Workflow

### 📥 Mode 1 — Intake: Build the Database
Upload mill certs and lab reports **as they arrive** — days or weeks before any order ships. The system extracts chemistry and mechanical data, links records by heat number, and saves everything to a Heat Master database. Heats can be saved with partial data and updated when remaining documents arrive.

### 📄 Mode 2 — Generate Cert: When Orders Ship
Select a heat from the database, add customer order details (scan an invoice or enter manually), and generate a completed certification. Every cert is logged automatically with an auto-generated cert number.

```
Steel Arrives        Lab Results Return       Customer Order Ships
     │                      │                         │
     ▼                      ▼                         ▼
┌──────────┐         ┌──────────┐              ┌─────────────┐
│Mill Cert │────────▶│Lab Report│─────────────▶│ Select Heat │
│Chemistry │  Intake │Mechanics │  Intake      │ + Invoice   │
└──────────┘  Mode   └──────────┘  Mode        │ = Cert      │
     │                      │                  └──────┬──────┘
     └──────────┬───────────┘                         │
                ▼                                     ▼
         ┌────────────┐                      ┌──────────────┐
         │Heat Master │◀────────────────────│  Cert Log    │
         │ (database) │                      │  (audit)     │
         └────────────┘                      └──────────────┘
```

---

## Key Features

- **AI Document Classification** — Drop any combination of documents, the system identifies each one automatically
- **Heat Number Reconciliation** — Chemistry, mechanicals, and order data merged by heat number across documents
- **Editable Review Step** — All extracted fields are editable before cert generation
- **Lab Sample Selector** — Choose which test specimen to use when multiple samples exist
- **ASTM Spec Checkboxes** — Toggle applicable specifications (A29, A108, A276, A320, A496, A1044, AASHTO M169)
- **Google Sheets Backend** — Persistent Heat Master database and cert log via Google Sheets
- **Multi-Format Export** — Download as Excel, JSON, or printable HTML (open in browser → Print → PDF)
- **Source Tracking** — Every field shows which document it came from

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| UI | Streamlit |
| AI Extraction | Google Gemini (auto-detects best available model) |
| Data Validation | Pydantic |
| Cert Rendering | Jinja2 |
| Database | Google Sheets via gspread |
| Export | pandas + openpyxl |

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/MimirLogic/mimir-doc-scraper.git
cd mimir-doc-scraper

# 2. Install
pip install -r requirements.txt

# 3. Configure
cp secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml with your Gemini API key and Google service account

# 4. Run
streamlit run app.py
```

See **[DEPLOY.md](DEPLOY.md)** for full Streamlit Cloud deployment instructions (~20 minutes).

---

## About Mimir Logic

Mimir Logic builds AI-powered tools for manufacturing — designed by people who have actually worked the floor.

[GitHub](https://github.com/MimirLogic)
