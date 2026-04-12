# 🛡️ Cox Industries — Mill Cert Scraper

**AI-powered multi-document reconciliation for Weld Stud Certifications**

Built by [Mimir Logic](https://github.com/MimirLogic) for Cox Industries quality operations.

---

## Two-Mode Workflow

### 📥 Mode 1: Intake — Build the Database
Upload mill certs and lab reports **as they arrive** — days or weeks before any customer order ships. The system extracts chemistry and mechanical data, links it by heat number, and saves it to the Heat Master database. Heats can be saved with partial data (chemistry only) and updated when lab results come back.

### 📄 Mode 2: Generate Cert — When Orders Ship
Select a heat from the database, add customer order details (from an invoice scan or manual entry), and generate a completed Cox Industries Weld Stud Certification. Every cert is logged with an auto-generated cert number.

```
Steel Arrives          Lab Results Return        Customer Order Ships
     │                       │                          │
     ▼                       ▼                          ▼
┌──────────┐          ┌──────────┐               ┌──────────────┐
│Mill Cert │─────────▶│Lab Report│──────────────▶│ Select Heat  │
│Chemistry │  Intake  │Mechanicals│   Intake     │ + Invoice    │
└──────────┘  Mode    └──────────┘   Mode        │ = Cert       │
     │                       │                   └──────┬───────┘
     └───────────┬───────────┘                          │
                 ▼                                      ▼
          ┌─────────────┐                      ┌──────────────┐
          │ Heat Master │◀─────────────────────│  Cert Log    │
          │ (database)  │                      │  (audit)     │
          └─────────────┘                      └──────────────┘
```

## Quick Start

```bash
git clone https://github.com/MimirLogic/mimir-doc-scraper.git
cd mimir-doc-scraper
pip install -r requirements.txt
cp secrets.toml.example .streamlit/secrets.toml  # edit with your keys
streamlit run app.py
```

See **[DEPLOY.md](DEPLOY.md)** for Streamlit Cloud deployment (~20 min).

## Tech Stack

Streamlit · Google Gemini AI · Pydantic · Jinja2 · gspread · Google Sheets

---

*Cox Industries · 24700 Wood CT, Macomb MI 48042 · Powered by Mimir Logic*
