# 🚀 Deployment Guide — Streamlit Cloud + Google Sheets

Live URL anyone at Cox can open — no Python install needed. ~20 min setup.

---

## Step 1: Google Cloud Service Account (10 min)

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → Create project (e.g. `cox-cert-scraper`)
2. Enable **Google Sheets API** and **Google Drive API** (APIs & Services → Library)
3. Create service account (APIs & Services → Credentials → Create Credentials → Service Account)
4. Create JSON key (click service account → Keys tab → Add Key → JSON)
5. Copy the `client_email` from the JSON — you need it in Step 2

## Step 2: Create Google Sheet (2 min)

1. Create a new spreadsheet named **Cox Mill Cert Database**
2. Share it with the `client_email` from Step 1 (Editor access)
3. The app auto-creates "Heat Master" and "Cert Log" tabs on first run

## Step 3: Push to GitHub (3 min)

```bash
cd mimir-doc-scraper
git add .
git commit -m "v4: two-mode workflow, database-first intake"
git push
```

## Step 4: Deploy on Streamlit Cloud (5 min)

1. Go to [share.streamlit.io](https://share.streamlit.io) → Sign in with GitHub
2. New app → Select `MimirLogic/mimir-doc-scraper` → Branch: `main` → File: `app.py`
3. Click **Advanced settings** → paste your secrets (see `secrets.toml.example`)
4. Deploy!

## Step 5: Test (2 min)

1. Open the app URL → sidebar should say "☁️ Connected to Google Sheets"
2. **Intake mode**: Upload Beta Steel cert → save heat to database
3. **Intake mode**: Upload Titan lab report for same heat → save again (now "Complete")
4. **Generate Cert**: Select heat from database → upload or type invoice details → generate cert
5. Check Google Sheet — both tabs should have data

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "GEMINI_API_KEY not found" | Check Secrets in Streamlit Cloud |
| "⚠️ Offline Mode" | `gcp_service_account` secrets missing |
| "SpreadsheetNotFound" | Sheet name must match AND be shared with service account |
| Model errors | Auto-detect finds whatever works on your key |
