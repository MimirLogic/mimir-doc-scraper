"""
Cox Industries — Google Sheets Integration
Two-sheet architecture:
  1. Heat Master  → One row per heat (chemistry + mechanicals)
  2. Cert Log     → One row per customer cert generated
"""

import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
from datetime import datetime

HEAT_MASTER_HEADERS = [
    "Heat Number", "Grade", "Mill Name", "Country",
    "C", "Mn", "Si", "P", "S", "Cr", "Ni", "Mo",
    "Tensile (psi)", "Yield (psi)", "Elongation %", "Reduction %",
    "Lab Report ID", "Lab Sample Used", "Date Added", "Status",
]

CERT_LOG_HEADERS = [
    "Cert #", "Date Generated", "Heat Number",
    "Customer", "PO #", "Invoice #", "Invoice Date",
    "Part #", "Part Description", "Quantity", "Grade",
    "C", "Mn", "Si", "P", "S", "Cr", "Ni", "Mo",
    "Tensile (psi)", "Yield (psi)", "Elongation %", "Reduction %",
    "ASTM Specs", "Additional Specs",
]


def _get_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=scopes)
    return gspread.authorize(creds)


def _get_spreadsheet():
    client = _get_client()
    name = st.secrets.get("sheets", {}).get("spreadsheet_name", "Cox Mill Cert Database")
    try:
        return client.open(name)
    except gspread.SpreadsheetNotFound:
        ss = client.create(name)
        email = st.secrets.get("sheets", {}).get("share_with_email", "")
        if email:
            ss.share(email, perm_type="user", role="writer")
        return ss


def _ensure_sheet(ss, title, headers):
    try:
        ws = ss.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=title, rows=500, cols=len(headers))
        ws.update("A1", [headers])
        ws.format("A1:Z1", {"textFormat": {"bold": True}})
    return ws


# ─── Heat Master ───

def save_heat_master(cert, status="Complete"):
    """Save/update heat. Status can be 'Chemistry Only', 'Awaiting Lab', or 'Complete'."""
    try:
        ss = _get_spreadsheet()
        ws = _ensure_sheet(ss, "Heat Master", HEAT_MASTER_HEADERS)
        heat = cert.get("heat_number", "")
        if not heat: return False

        existing = ws.col_values(1)
        row_idx = None
        for i, val in enumerate(existing):
            if val == heat: row_idx = i + 1; break

        sources = cert.get("sources", {})
        row = [
            heat, cert.get("grade", ""),
            sources.get("chemistry", "").replace("Mill Cert — ", ""),
            "",  # Country
            cert.get("c",""), cert.get("mn",""), cert.get("si",""), cert.get("p",""),
            cert.get("s",""), cert.get("cr",""), cert.get("ni",""), cert.get("mo",""),
            cert.get("tensile",""), cert.get("yield_strength",""),
            cert.get("elongation",""), cert.get("reduction",""),
            sources.get("mechanicals", "").replace("Titan Lab #", ""),
            "",  # Lab sample
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            status,
        ]
        if row_idx:
            ws.update(f"A{row_idx}", [row])
        else:
            ws.append_row(row, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.error(f"Sheets error: {e}")
        return False


def get_heat_master(heat_number):
    try:
        ss = _get_spreadsheet()
        ws = _ensure_sheet(ss, "Heat Master", HEAT_MASTER_HEADERS)
        for r in ws.get_all_records():
            if str(r.get("Heat Number", "")) == str(heat_number): return r
        return None
    except Exception as e:
        st.error(f"Lookup error: {e}")
        return None


def get_all_heats():
    try:
        ss = _get_spreadsheet()
        ws = _ensure_sheet(ss, "Heat Master", HEAT_MASTER_HEADERS)
        return ws.get_all_records()
    except Exception:
        return []


# ─── Cert Log ───

def save_cert_log(cert):
    try:
        ss = _get_spreadsheet()
        ws = _ensure_sheet(ss, "Cert Log", CERT_LOG_HEADERS)
        today = datetime.now().strftime("%Y%m%d")
        existing = ws.col_values(1)
        n = sum(1 for c in existing if c.startswith(f"COX-{today}"))
        cert_num = f"COX-{today}-{n+1:03d}"

        specs = []
        for k, l in [("astm_a29","A29"),("astm_a108","A108"),("astm_a276","A276"),
                      ("astm_a320","A320"),("astm_a496","A496"),("astm_a1044","A1044"),
                      ("aashto_m169","AASHTO M169")]:
            if cert.get(k): specs.append(l)

        row = [
            cert_num, datetime.now().strftime("%Y-%m-%d %H:%M"), cert.get("heat_number",""),
            cert.get("customer",""), cert.get("purchase_order",""), cert.get("invoice_number",""),
            cert.get("date",""), cert.get("part_number",""), cert.get("part_description",""),
            cert.get("quantity",""), cert.get("grade",""),
            cert.get("c",""), cert.get("mn",""), cert.get("si",""), cert.get("p",""),
            cert.get("s",""), cert.get("cr",""), cert.get("ni",""), cert.get("mo",""),
            cert.get("tensile",""), cert.get("yield_strength",""),
            cert.get("elongation",""), cert.get("reduction",""),
            ", ".join(specs), cert.get("additional_spec",""),
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")
        return cert_num
    except Exception as e:
        st.error(f"Cert log error: {e}")
        return None


def get_cert_log():
    try:
        ss = _get_spreadsheet()
        ws = _ensure_sheet(ss, "Cert Log", CERT_LOG_HEADERS)
        return ws.get_all_records()
    except Exception:
        return []
