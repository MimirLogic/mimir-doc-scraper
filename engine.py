"""
Cox Industries — Mill Cert Reconciliation Engine
Extracts data from 3 document types and merges by Heat Number.
"""

import os
import time
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel
import streamlit as st

load_dotenv()


def _get_api_key():
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            st.error("GEMINI_API_KEY not found.")
        return key


def _get_client():
    return genai.Client(api_key=_get_api_key())


_cached_model = None

def get_best_model() -> str:
    global _cached_model
    if _cached_model:
        return _cached_model
    preferred = [
        "gemini-2.5-flash-preview-05-20", "gemini-2.5-flash", "gemini-2.0-flash",
        "gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-2.0-flash-lite",
    ]
    try:
        client = _get_client()
        available_ids = {m.name.replace("models/", "") for m in client.models.list()}
        for model in preferred:
            if model in available_ids:
                _cached_model = model
                return model
        for mid in available_ids:
            if "gemini" in mid:
                _cached_model = mid
                return mid
    except Exception as e:
        print(f"⚠️ Model listing failed ({e})")
    _cached_model = "gemini-2.0-flash"
    return _cached_model


# ─── Schemas ───

class MillCertChemistry(BaseModel):
    c: str | None = None
    mn: str | None = None
    si: str | None = None
    p: str | None = None
    s: str | None = None
    cr: str | None = None
    ni: str | None = None
    mo: str | None = None
    cu: str | None = None
    v: str | None = None
    nb: str | None = None
    ti: str | None = None
    al: str | None = None
    b: str | None = None
    n: str | None = None
    sn: str | None = None
    ca: str | None = None

class MillCertData(BaseModel):
    doc_type: str | None = "mill_cert"
    heat_number: str | None = None
    grade: str | None = None
    mill_name: str | None = None
    country_of_melt: str | None = None
    diameter: str | None = None
    part_description: str | None = None
    ship_date: str | None = None
    chemistry: MillCertChemistry | None = None
    mill_tensile: str | None = None
    mill_reduction_of_area: str | None = None

class LabSample(BaseModel):
    sample_id: str | None = None
    size: str | None = None
    tensile_psi: str | None = None
    yield_psi: str | None = None
    elongation_pct: str | None = None
    reduction_of_area_pct: str | None = None

class LabReportData(BaseModel):
    doc_type: str | None = "lab_report"
    heat_number: str | None = None
    grade: str | None = None
    report_id: str | None = None
    report_date: str | None = None
    purchase_order: str | None = None
    samples: list[LabSample] | None = None

class InvoiceLineItem(BaseModel):
    part_number: str | None = None
    part_description: str | None = None
    quantity: str | None = None
    heat_number: str | None = None

class InvoiceData(BaseModel):
    doc_type: str | None = "invoice"
    customer_name: str | None = None
    customer_po: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    sales_order: str | None = None
    line_items: list[InvoiceLineItem] | None = None


# ─── Upload / Cleanup ───

def _upload_and_stabilize(file_path: str, max_wait: int = 30):
    client = _get_client()
    uploaded = client.files.upload(file=file_path)
    retries = 0
    while True:
        state = client.files.get(name=uploaded.name).state.name
        if state == "ACTIVE":
            return uploaded
        if retries >= max_wait:
            client.files.delete(name=uploaded.name)
            raise TimeoutError(f"Timed out after {max_wait}s")
        time.sleep(1)
        retries += 1

def _cleanup(f):
    try:
        if f: _get_client().files.delete(name=f.name)
    except Exception: pass


# ─── Classification ───

def detect_document_type(file_path: str) -> str:
    # Filename hints first - fast path
    name = os.path.basename(file_path).lower()
    if any(x in name for x in ["titan", "lab", "26-0", "26-1", "test-report", "lab-services"]):
        return "lab_report"
    if any(x in name for x in ["beta", "charter", "mill", "rel-", "release", "bol", "147018", "21029340"]):
        return "mill_cert"
    if any(x in name for x in ["invoice", "inv-", "inv_", "so700", "214"]):
        return "invoice"

    model = get_best_model()
    uploaded = None
    try:
        uploaded = _upload_and_stabilize(file_path)
        prompt = """Look at this document and classify it. Respond with EXACTLY ONE of these words and nothing else: mill_cert, lab_report, invoice, or unknown.

Choose mill_cert if you see: chemistry data (Carbon, Manganese, Silicon, Phosphorus, Sulfur), heat numbers, steel mill names like Beta Steel or Charter Steel, Bill of Lading, Certification of Analysis, or material test report.

Choose lab_report if you see: tensile testing results, yield strength, elongation, reduction of area, lab services report, Titan Metallurgy, or ASTM E8 testing.

Choose invoice if you see: customer name, purchase order, invoice number, line items with quantities and prices, ship-to address, Cox Industries letterhead.

Choose unknown only if none of the above clearly apply.

Your response must be ONE WORD."""

        response = _get_client().models.generate_content(
            model=model, contents=[uploaded, prompt],
            config=types.GenerateContentConfig(temperature=0.0),
        )
        result = response.text.strip().lower().replace('"', '').replace("'", "").replace(".", "").replace(",", "")
        # Check substring match for safety
        for valid in ("mill_cert", "lab_report", "invoice"):
            if valid in result:
                return valid
        return "unknown"
    except Exception as e:
        print(f"Classification error: {e}")
        return "unknown"
    finally:
        _cleanup(uploaded)


# ─── Extraction ───

def extract_mill_cert(file_path: str) -> dict | None:
    uploaded = None
    try:
        uploaded = _upload_and_stabilize(file_path)
        prompt = """Extract data from this steel mill certification / Certification of Analysis.
Find: heat number, chemical composition (C, Mn, Si, P, S, Cr, Ni, Mo, Cu, V, Nb, Ti, Al, B, N, Sn, Ca),
mill grade, mill name, country of melt, diameter, description, mill-reported mechanicals if present.
Extract ALL values exactly as printed. Include decimals. Check ALL pages. Return null for missing values."""

        response = _get_client().models.generate_content(
            model=get_best_model(), contents=[uploaded, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json", response_schema=MillCertData, temperature=0.1),
        )
        _cleanup(uploaded)
        return json.loads(response.text)
    except Exception as e:
        import traceback
        st.error(f"Mill cert extraction failed: {type(e).__name__}: {e}")
        st.code(traceback.format_exc())
        _cleanup(uploaded)
        return None


def extract_lab_report(file_path: str) -> dict | None:
    uploaded = None
    try:
        uploaded = _upload_and_stabilize(file_path)
        prompt = """Extract data from this metallurgical lab report (likely Titan Metallurgy).
Find: heat number, grade, report ID, report date, purchase order.
For EACH sample: sample ID, size, Ultimate Tensile (psi), Yield (psi), Elongation %, Reduction of Area %.
Use PSI values not MPa. Extract ALL samples. Return exact values."""

        response = _get_client().models.generate_content(
            model=get_best_model(), contents=[uploaded, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json", response_schema=LabReportData, temperature=0.1),
        )
        _cleanup(uploaded)
        return json.loads(response.text)
    except Exception as e:
        import traceback
        st.error(f"Lab report extraction failed: {type(e).__name__}: {e}")
        st.code(traceback.format_exc())
        _cleanup(uploaded)
        return None


def extract_invoice(file_path: str) -> dict | None:
    uploaded = None
    try:
        uploaded = _upload_and_stabilize(file_path)
        prompt = """Extract data from this Cox Industries sales invoice.
Find: customer name (Bill To/Ship To company), customer PO, invoice number, invoice date, sales order.
For each line item: part number, part description, ship quantity, heat number. Return exact values."""

        response = _get_client().models.generate_content(
            model=get_best_model(), contents=[uploaded, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json", response_schema=InvoiceData, temperature=0.1),
        )
        _cleanup(uploaded)
        return json.loads(response.text)
    except Exception as e:
        import traceback
        st.error(f"Invoice extraction failed: {type(e).__name__}: {e}")
        st.code(traceback.format_exc())
        _cleanup(uploaded)
        return None


def extract_document(file_path: str) -> tuple[str, dict | None]:
    doc_type = detect_document_type(file_path)
    extractors = {"mill_cert": extract_mill_cert, "lab_report": extract_lab_report, "invoice": extract_invoice}
    data = extractors.get(doc_type, lambda x: None)(file_path)
    return doc_type, data


# ─── Reconciliation ───

def reconcile_heat_record(mill_data=None, lab_data=None, invoice_data=None, selected_sample_idx=0) -> dict:
    cert = {
        "customer": "", "date": "", "purchase_order": "", "invoice_number": "",
        "part_number": "", "heat_number": "", "quantity": "", "part_description": "",
        "c": "", "mn": "", "si": "", "p": "", "s": "", "cr": "", "ni": "", "mo": "",
        "grade": "", "tensile": "", "yield_strength": "", "elongation": "", "reduction": "",
        "astm_a29": False, "astm_a108": False, "astm_a276": False, "astm_a320": False,
        "astm_a496": False, "astm_a1044": False, "aashto_m169": False, "additional_spec": "",
        "sources": {"chemistry": "Not loaded", "mechanicals": "Not loaded", "order_details": "Not loaded"},
    }
    if mill_data:
        cert["heat_number"] = mill_data.get("heat_number", "")
        cert["grade"] = mill_data.get("grade", "")
        chem = mill_data.get("chemistry") or {}
        for k in ["c","mn","si","p","s","cr","ni","mo"]:
            cert[k] = chem.get(k, "") or ""
        cert["sources"]["chemistry"] = f"Mill Cert — {mill_data.get('mill_name', '?')}"

    if lab_data:
        if not cert["heat_number"]: cert["heat_number"] = lab_data.get("heat_number", "")
        if not cert["grade"]: cert["grade"] = lab_data.get("grade", "")
        samples = lab_data.get("samples") or []
        if samples and selected_sample_idx < len(samples):
            s = samples[selected_sample_idx]
            cert["tensile"] = s.get("tensile_psi", "") or ""
            cert["yield_strength"] = s.get("yield_psi", "") or ""
            cert["elongation"] = s.get("elongation_pct", "") or ""
            cert["reduction"] = s.get("reduction_of_area_pct", "") or ""
        cert["sources"]["mechanicals"] = f"Titan Lab #{lab_data.get('report_id', '?')}"

    if invoice_data:
        cert["customer"] = invoice_data.get("customer_name", "") or ""
        cert["purchase_order"] = invoice_data.get("customer_po", "") or ""
        cert["invoice_number"] = invoice_data.get("invoice_number", "") or ""
        cert["date"] = invoice_data.get("invoice_date", "") or ""
        items = invoice_data.get("line_items") or []
        if items:
            target = cert["heat_number"]
            matched = next((i for i in items if i.get("heat_number") == target), items[0])
            cert["part_number"] = matched.get("part_number", "") or ""
            cert["part_description"] = matched.get("part_description", "") or ""
            cert["quantity"] = matched.get("quantity", "") or ""
            if not cert["heat_number"]: cert["heat_number"] = matched.get("heat_number", "") or ""
        cert["sources"]["order_details"] = f"Invoice #{cert['invoice_number']}"

    return cert


def build_cert_from_sheets_row(row: dict) -> dict:
    """Build a cert record from a Heat Master row for cert generation."""
    return {
        "customer": "", "date": "", "purchase_order": "", "invoice_number": "",
        "part_number": "", "heat_number": str(row.get("Heat Number", "")),
        "quantity": "", "part_description": "",
        "c": str(row.get("C", "")), "mn": str(row.get("Mn", "")),
        "si": str(row.get("Si", "")), "p": str(row.get("P", "")),
        "s": str(row.get("S", "")), "cr": str(row.get("Cr", "")),
        "ni": str(row.get("Ni", "")), "mo": str(row.get("Mo", "")),
        "grade": str(row.get("Grade", "")),
        "tensile": str(row.get("Tensile (psi)", "")),
        "yield_strength": str(row.get("Yield (psi)", "")),
        "elongation": str(row.get("Elongation %", "")),
        "reduction": str(row.get("Reduction %", "")),
        "astm_a29": False, "astm_a108": False, "astm_a276": False,
        "astm_a320": False, "astm_a496": False, "astm_a1044": False,
        "aashto_m169": False, "additional_spec": "",
        "sources": {"chemistry": "Heat Master", "mechanicals": "Heat Master", "order_details": "Enter below"},
    }
