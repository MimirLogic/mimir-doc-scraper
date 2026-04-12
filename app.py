"""
Cox Industries — Mill Cert Scraper
Two-mode workflow:
  MODE 1 — INTAKE: Upload mill certs + lab reports → build Heat Master database
  MODE 2 — GENERATE: Select heat from database + add invoice details → produce customer cert
"""

import streamlit as st
import os, json, io
import pandas as pd
import streamlit.components.v1 as components
from jinja2 import Template
from engine import (
    extract_document, reconcile_heat_record, build_cert_from_sheets_row, get_best_model,
)

SHEETS_ENABLED = False
try:
    if "gcp_service_account" in st.secrets:
        from sheets import save_heat_master, save_cert_log, get_all_heats, get_heat_master, get_cert_log
        SHEETS_ENABLED = True
except Exception:
    pass

st.set_page_config(page_title="Cox Industries | Mill Cert Scraper", page_icon="🛡️", layout="wide",
                    initial_sidebar_state="expanded" if SHEETS_ENABLED else "collapsed")

# ─── Styling ───
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');
    .main { background-color: #f5f5f0; }
    .block-container { max-width: 1200px; padding-top: 1.5rem; }

    .cox-header {
        background: linear-gradient(135deg, #8B0000 0%, #B71C1C 40%, #D2232A 100%);
        color: white; padding: 1.2rem 2rem; border-radius: 0 0 10px 10px;
        margin: -2rem -1rem 1.2rem -1rem;
        box-shadow: 0 4px 20px rgba(139, 0, 0, 0.35);
        font-family: 'IBM Plex Sans', sans-serif;
        display: flex; justify-content: space-between; align-items: center;
    }
    .cox-header h1 { color: white !important; font-size: 1.5rem; font-weight: 700; margin: 0; }
    .cox-header p { color: rgba(255,255,255,0.8); font-size: 0.82rem; margin: 0.2rem 0 0 0; }
    .cox-header .badge {
        background: rgba(255,255,255,0.15); padding: 0.25rem 0.7rem;
        border-radius: 20px; font-size: 0.72rem; font-family: 'IBM Plex Mono', monospace;
        margin-left: 6px;
    }

    .mode-card {
        background: white; border-radius: 10px; padding: 1.5rem;
        border: 2px solid #e0e0e0; text-align: center;
        font-family: 'IBM Plex Sans', sans-serif;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        transition: all 0.2s;
    }
    .mode-card:hover { border-color: #D2232A; box-shadow: 0 4px 16px rgba(178,28,28,0.15); }
    .mode-card h3 { margin: 0.5rem 0 0.3rem 0; color: #222; }
    .mode-card p { font-size: 0.85rem; color: #666; margin: 0; }

    .source-card {
        background: white; border-left: 4px solid #ccc; border-radius: 0 6px 6px 0;
        padding: 0.7rem 1rem; margin-bottom: 0.5rem; font-family: 'IBM Plex Sans', sans-serif;
        font-size: 0.82rem; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .source-card.mill { border-left-color: #1565C0; }
    .source-card.lab { border-left-color: #F57F17; }
    .source-card.invoice { border-left-color: #2E7D32; }
    .source-card .doc-type { font-weight: 700; text-transform: uppercase; font-size: 0.68rem; letter-spacing: 1px; margin-bottom: 0.2rem; }
    .source-card.mill .doc-type { color: #1565C0; }
    .source-card.lab .doc-type { color: #F57F17; }
    .source-card.invoice .doc-type { color: #2E7D32; }

    .stButton > button {
        background: linear-gradient(135deg, #B71C1C, #D2232A) !important;
        color: white !important; border: none !important; border-radius: 8px !important;
        font-family: 'IBM Plex Sans', sans-serif !important; font-weight: 600 !important;
        font-size: 0.9rem !important; padding: 0.6rem 1.2rem !important; width: 100% !important;
        box-shadow: 0 2px 8px rgba(178,28,28,0.25) !important;
    }
    .stDownloadButton > button {
        background: linear-gradient(135deg, #1B5E20, #2E7D32) !important;
        color: white !important; border: none !important; border-radius: 8px !important;
        font-family: 'IBM Plex Sans', sans-serif !important; font-weight: 600 !important; width: 100% !important;
    }
    h2, h3, h4 { font-family: 'IBM Plex Sans', sans-serif !important; color: #333 !important; font-weight: 600 !important; }
    .cox-footer {
        text-align: center; font-family: 'IBM Plex Mono', monospace;
        font-size: 0.68rem; color: #bbb; margin-top: 2rem; padding: 0.8rem; border-top: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)


# ─── Session State ───
for k, v in {"mode": None, "intake_docs": [], "intake_mill": None, "intake_lab": None,
             "cert_record": None, "cert_step": 1, "invoice_data": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─── SIDEBAR ───
if SHEETS_ENABLED:
    with st.sidebar:
        st.markdown("### 📊 Heat Master Database")
        heats = get_all_heats()
        if heats:
            st.caption(f"**{len(heats)}** heats in database")
            for h in reversed(heats[-15:]):
                status = h.get("Status", "")
                icon = "✅" if status == "Complete" else "🔶" if "Awaiting" in status else "🔵"
                st.caption(f"{icon} **{h.get('Heat Number')}** — {h.get('Grade','')} — {status}")
        else:
            st.caption("No heats yet. Use Intake mode to add them.")

        st.markdown("---")
        certs = get_cert_log()
        if certs:
            st.markdown(f"### 📄 Cert Log ({len(certs)})")
            for c in reversed(certs[-10:]):
                st.caption(f"**{c.get('Cert #')}** — {c.get('Customer','')} — Heat {c.get('Heat Number','')}")
        st.markdown("---")
        st.caption("☁️ Connected to Google Sheets")
else:
    with st.sidebar:
        st.markdown("### ⚠️ Offline Mode")
        st.caption("Google Sheets not configured. See DEPLOY.md.")


# ─── HEADER ───
model_name = get_best_model()
sheets_badge = "☁️ Sheets" if SHEETS_ENABLED else "💻 Local"
st.markdown(f"""
<div class="cox-header">
    <div>
        <h1>🛡️ Cox Industries — Mill Cert Scraper</h1>
        <p>Build the heat database first, generate customer certs when orders ship</p>
    </div>
    <div><span class="badge">⚡ {model_name}</span><span class="badge">{sheets_badge}</span></div>
</div>
""", unsafe_allow_html=True)


# ================================================================
# MODE SELECT
# ================================================================
if st.session_state.mode is None:
    st.write("")
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("""
        <div class="mode-card">
            <div style="font-size: 2.5rem;">📥</div>
            <h3>Intake — Build Database</h3>
            <p>Upload mill certs and lab reports as they arrive.<br>
            Saves chemistry & mechanicals to the Heat Master.</p>
        </div>
        """, unsafe_allow_html=True)
        st.write("")
        if st.button("📥 Start Intake", key="btn_intake"):
            st.session_state.mode = "intake"
            st.rerun()

    with col2:
        st.markdown("""
        <div class="mode-card">
            <div style="font-size: 2.5rem;">📄</div>
            <h3>Generate Cert — Customer Order</h3>
            <p>Select a heat from the database, add invoice details,<br>
            and generate a completed Weld Stud Certification.</p>
        </div>
        """, unsafe_allow_html=True)
        st.write("")
        if st.button("📄 Generate Cert", key="btn_cert"):
            st.session_state.mode = "cert"
            st.session_state.cert_step = 1
            st.rerun()

    # Quick stats
    if SHEETS_ENABLED:
        st.write("")
        heats = get_all_heats()
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Heats in Database", len(heats))
        with c2:
            complete = sum(1 for h in heats if h.get("Status") == "Complete")
            st.metric("Complete (Chem + Lab)", complete)
        with c3:
            certs = get_cert_log()
            st.metric("Certs Generated", len(certs))


# ================================================================
# MODE 1: INTAKE — Build the Heat Master
# ================================================================
elif st.session_state.mode == "intake":
    st.subheader("📥 Intake — Build Heat Master Database")
    st.caption("Upload mill certs and/or lab reports as they come in. No invoice needed yet.")

    if st.button("← Back to Menu", key="intake_back"):
        st.session_state.mode = None
        st.session_state.intake_docs = []
        st.session_state.intake_mill = None
        st.session_state.intake_lab = None
        st.rerun()

    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="source-card mill"><div class="doc-type">🔵 Mill Cert</div>Beta / Charter Steel — Chemistry & Heat Number</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="source-card lab"><div class="doc-type">🟡 Lab Report</div>Titan Metallurgy — Tensile Test Results</div>', unsafe_allow_html=True)

    st.write("")
    files = st.file_uploader("Drop mill certs and/or lab reports here",
                              type=["pdf","png","jpg","jpeg"], accept_multiple_files=True, key="intake_upload")

    if files and st.button("🚀 Extract & Save to Database"):
        import traceback
        st.session_state.intake_mill = None
        st.session_state.intake_lab = None
        st.session_state.intake_docs = []

        progress = st.progress(0, "Starting...")
        for i, f in enumerate(files):
            progress.progress(i/len(files), f"Processing {f.name}...")
            tmp = f"temp_{f.name}"
            try:
                with open(tmp, "wb") as fh:
                    fh.write(f.getbuffer())
                st.info(f"Saved temp file: {tmp}")
                try:
                    doc_type, data = extract_document(tmp)
                    st.info(f"Detected as: {doc_type}")
                    if data:
                        st.success(f"Got data from {f.name}")
                        st.json(data)
                        st.session_state.intake_docs.append({"filename": f.name, "doc_type": doc_type, "data": data})
                        if doc_type == "mill_cert":
                            st.session_state.intake_mill = data
                        elif doc_type == "lab_report":
                            st.session_state.intake_lab = data
                    else:
                        st.error(f"No data returned for {f.name} (doc_type was: {doc_type})")
                except Exception as e:
                    st.error(f"Extraction crashed: {type(e).__name__}: {e}")
                    st.code(traceback.format_exc())
            except Exception as outer_e:
                st.error(f"Outer error: {outer_e}")
                st.code(traceback.format_exc())
            finally:
                if os.path.exists(tmp):
                    os.remove(tmp)
        progress.progress(1.0, "Done!")
        st.write("---")
        st.write(f"Total documents extracted: {len(st.session_state.intake_docs)}")

    # Show results & save
    if st.session_state.intake_docs:
        st.write("")
        for doc in st.session_state.intake_docs:
            dtype = doc["doc_type"]
            css = {"mill_cert":"mill","lab_report":"lab","invoice":"invoice"}.get(dtype,"")
            label = {"mill_cert":"MILL CERT","lab_report":"LAB REPORT","invoice":"INVOICE"}.get(dtype,"UNKNOWN")
            st.markdown(f'<div class="source-card {css}"><div class="doc-type">{label}</div><strong>{doc["filename"]}</strong></div>', unsafe_allow_html=True)
            with st.expander(f"Raw data — {doc['filename']}"):
                st.json(doc["data"])

        # Build a preview record
        cert = reconcile_heat_record(st.session_state.intake_mill, st.session_state.intake_lab, None)
        heat = cert.get("heat_number", "?")

        st.write("")
        st.markdown(f"#### Heat #{heat} — Data Preview")

        # Determine status
        has_chem = st.session_state.intake_mill is not None
        has_lab = st.session_state.intake_lab is not None
        if has_chem and has_lab:
            status = "Complete"
            st.success("✅ Chemistry + Mechanicals — Ready for customer certs")
        elif has_chem:
            status = "Awaiting Lab"
            st.warning("🔶 Chemistry loaded — Awaiting Titan lab results")
        elif has_lab:
            status = "Chemistry Missing"
            st.warning("🔶 Lab results loaded — Mill cert still needed")
        else:
            status = "Empty"

        # Editable preview
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("**Chemistry**")
            cc = st.columns(4)
            for i, k in enumerate(["c","mn","si","p","s","cr","ni","mo"]):
                with cc[i%4]:
                    cert[k] = st.text_input(k.upper(), value=str(cert.get(k,"") or ""), key=f"in_{k}_{cert.get('heat_number','x')}")
        with col_r:
            st.markdown("**Mechanicals**")
            cert["grade"] = st.text_input("Grade", value=str(cert.get("grade","") or ""), key=f"in_grade_{cert.get('heat_number','x')}")

            # Lab sample selector
            lab = st.session_state.intake_lab
            if lab and lab.get("samples") and len(lab["samples"]) > 1:
                samples = lab["samples"]
                opts = [f"Sample {i+1}: {s.get('sample_id','?')} — Ø{s.get('size','?')}\"" for i,s in enumerate(samples)]
                sel = st.radio("Test specimen:", opts, key="in_sample")
                idx = opts.index(sel)
                cert = reconcile_heat_record(st.session_state.intake_mill, lab, None, idx)

            mc = st.columns(2)
            with mc[0]:
                cert["tensile"] = st.text_input("Tensile (psi)", value=str(cert.get("tensile","") or ""), key=f"in_t_{cert.get('heat_number','x')}")
                cert["yield_strength"] = st.text_input("Yield (psi)", value=str(cert.get("yield_strength","") or ""), key=f"in_y_{cert.get('heat_number','x')}")
            with mc[1]:
                cert["elongation"] = st.text_input("Elongation %", value=str(cert.get("elongation","") or ""), key=f"in_e_{cert.get('heat_number','x')}")
                cert["reduction"] = st.text_input("Reduction %", value=str(cert.get("reduction","") or ""), key=f"in_r_{cert.get('heat_number','x')}")

        # CRITICAL: Persist the FULLY reconciled cert (including lab sample mechanicals) to session state
        # This must come AFTER the sample selector and mechanical text inputs so we capture the latest values
        st.session_state["preview_cert"] = dict(cert)

        if SHEETS_ENABLED:
            st.write("")
            if st.button(f"💾 Save Heat #{heat} to Database"):
                # Rebuild cert FRESH from session state mill+lab data right at save time
                # This guarantees we get the latest lab sample selection
                sample_idx = 0
                if st.session_state.intake_lab and st.session_state.intake_lab.get("samples"):
                    samples = st.session_state.intake_lab["samples"]
                    if len(samples) > 1:
                        # Try to read the radio button selection from session state
                        sel_key = f"in_sample"
                        if sel_key in st.session_state:
                            sel_val = st.session_state[sel_key]
                            for i, s in enumerate(samples):
                                if s.get("sample_id","") in sel_val:
                                    sample_idx = i
                                    break
                cert_to_save = reconcile_heat_record(
                    st.session_state.intake_mill,
                    st.session_state.intake_lab,
                    None,
                    selected_sample_idx=sample_idx,
                )
                st.write("DEBUG - About to save:")
                st.json({k: cert_to_save.get(k, "MISSING") for k in ["heat_number","grade","c","mn","si","p","s","cr","ni","mo","tensile","yield_strength","elongation","reduction"]})
                ok = save_heat_master(cert_to_save, status=status)
                if ok:
                    st.success(f"✅ Heat #{heat} saved to Heat Master! Status: **{status}**")
                    st.balloons()
        else:
            st.info("Google Sheets not configured — data won't persist. See DEPLOY.md.")


# ================================================================
# MODE 2: GENERATE CERT — From database + invoice
# ================================================================
elif st.session_state.mode == "cert":
    cert_step = st.session_state.cert_step

    if st.button("← Back to Menu", key="cert_back_menu"):
        st.session_state.mode = None
        st.session_state.cert_record = None
        st.session_state.cert_step = 1
        st.session_state.invoice_data = None
        st.rerun()

    # ── Step 1: Select heat ──
    if cert_step == 1:
        st.subheader("📄 Generate Cert — Step 1: Select Heat")

        tab_db, tab_upload = st.tabs(["🔍 From Database", "📁 Upload All Documents"])

        with tab_db:
            if SHEETS_ENABLED:
                heats = get_all_heats()
                complete_heats = [h for h in heats if h.get("Status") == "Complete"]

                if complete_heats:
                    heat_options = [f"{h['Heat Number']} — {h.get('Grade','')} — saved {h.get('Date Added','')}" for h in complete_heats]
                    selected = st.selectbox("Select a heat from the database:", heat_options)
                    idx = heat_options.index(selected)
                    chosen = complete_heats[idx]

                    with st.expander("Preview heat data"):
                        st.json(chosen)

                    if st.button("Use this heat →"):
                        cert = build_cert_from_sheets_row(chosen)
                        st.session_state.cert_record = cert
                        st.session_state.cert_step = 2
                        st.rerun()
                else:
                    st.warning("No complete heats in the database yet. Use Intake mode to add mill certs and lab reports first, or use the 'Upload All Documents' tab.")
            else:
                st.info("Google Sheets not configured. Use the 'Upload All Documents' tab instead.")

        with tab_upload:
            st.caption("Upload mill cert + lab report + invoice all at once (original workflow).")
            files = st.file_uploader("Drop all documents", type=["pdf","png","jpg","jpeg"],
                                      accept_multiple_files=True, key="cert_upload")
            if files and st.button("🚀 Extract All"):
                mill = lab = inv = None
                progress = st.progress(0)
                for i, f in enumerate(files):
                    progress.progress(i/len(files), f"Processing {f.name}...")
                    tmp = f"temp_{f.name}"
                    with open(tmp,"wb") as fh: fh.write(f.getbuffer())
                    dt, data = extract_document(tmp)
                    if os.path.exists(tmp): os.remove(tmp)
                    if data:
                        if dt == "mill_cert": mill = data
                        elif dt == "lab_report": lab = data
                        elif dt == "invoice": inv = data
                progress.progress(1.0, "✅ Done!")
                cert = reconcile_heat_record(mill, lab, inv)
                st.session_state.cert_record = cert
                st.session_state.cert_step = 3  # Skip to review
                st.rerun()

    # ── Step 2: Add invoice details ──
    elif cert_step == 2:
        st.subheader("📄 Generate Cert — Step 2: Add Invoice Details")
        cert = st.session_state.cert_record

        st.info(f"Heat **#{cert.get('heat_number')}** loaded from database. Now add the customer order details.")

        tab_scan, tab_manual = st.tabs(["📁 Upload Invoice", "✏️ Enter Manually"])

        with tab_scan:
            inv_file = st.file_uploader("Drop the Cox invoice here", type=["pdf","png","jpg","jpeg"], key="inv_upload")
            if inv_file and st.button("🚀 Extract Invoice"):
                tmp = f"temp_{inv_file.name}"
                with open(tmp,"wb") as fh: fh.write(inv_file.getbuffer())
                with st.spinner("Reading invoice..."):
                    dt, data = extract_document(tmp)
                if os.path.exists(tmp): os.remove(tmp)
                if data and dt == "invoice":
                    # Merge invoice into cert
                    cert["customer"] = data.get("customer_name","") or ""
                    cert["purchase_order"] = data.get("customer_po","") or ""
                    cert["invoice_number"] = data.get("invoice_number","") or ""
                    cert["date"] = data.get("invoice_date","") or ""
                    items = data.get("line_items") or []
                    if items:
                        target = cert["heat_number"]
                        matched = next((i for i in items if i.get("heat_number")==target), items[0])
                        cert["part_number"] = matched.get("part_number","") or ""
                        cert["part_description"] = matched.get("part_description","") or ""
                        cert["quantity"] = matched.get("quantity","") or ""
                    cert["sources"]["order_details"] = f"Invoice #{cert['invoice_number']}"
                    st.session_state.cert_record = cert
                    st.success("✅ Invoice data merged!")
                    st.session_state.cert_step = 3
                    st.rerun()
                else:
                    st.error("Could not extract invoice data.")

        with tab_manual:
            st.caption("Type the order details directly:")
            cert["customer"] = st.text_input("Customer Name", cert.get("customer",""), key="m_cust")
            c1, c2 = st.columns(2)
            with c1:
                cert["purchase_order"] = st.text_input("PO #", cert.get("purchase_order",""), key="m_po")
                cert["invoice_number"] = st.text_input("Invoice #", cert.get("invoice_number",""), key="m_inv")
                cert["date"] = st.text_input("Invoice Date", cert.get("date",""), key="m_date")
            with c2:
                cert["part_number"] = st.text_input("Part #", cert.get("part_number",""), key="m_pn")
                cert["quantity"] = st.text_input("Quantity", cert.get("quantity",""), key="m_qty")
                cert["part_description"] = st.text_input("Part Description", cert.get("part_description",""), key="m_desc")

            cert["sources"]["order_details"] = "Manual entry"
            st.session_state.cert_record = cert

            if st.button("Review Cert →"):
                st.session_state.cert_step = 3
                st.rerun()

    # ── Step 3: Review & Edit ──
    elif cert_step == 3:
        st.subheader("📄 Generate Cert — Step 3: Review & Edit")
        cert = st.session_state.cert_record

        left, right = st.columns(2)
        with left:
            st.markdown("#### Order Details")
            cert["customer"] = st.text_input("Customer", cert.get("customer",""), key="r_cust")
            cert["date"] = st.text_input("Date", cert.get("date",""), key="r_date")
            cert["purchase_order"] = st.text_input("PO", cert.get("purchase_order",""), key="r_po")
            cert["invoice_number"] = st.text_input("Invoice #", cert.get("invoice_number",""), key="r_inv")
            cert["part_number"] = st.text_input("Part #", cert.get("part_number",""), key="r_pn")
            cert["heat_number"] = st.text_input("Heat #", cert.get("heat_number",""), key="r_heat")
            cert["quantity"] = st.text_input("Quantity", cert.get("quantity",""), key="r_qty")
            cert["part_description"] = st.text_input("Part Description", cert.get("part_description",""), key="r_desc")

        with right:
            st.markdown("#### Chemistry")
            cc = st.columns(4)
            for i, k in enumerate(["c","mn","si","p","s","cr","ni","mo"]):
                with cc[i%4]:
                    cert[k] = st.text_input(k.upper(), cert.get(k,""), key=f"r_{k}")
            st.markdown("#### Mechanicals")
            cert["grade"] = st.text_input("AISI Grade", cert.get("grade",""), key="r_grade")
            mc = st.columns(2)
            with mc[0]:
                cert["tensile"] = st.text_input("Tensile", cert.get("tensile",""), key="r_t")
                cert["yield_strength"] = st.text_input("Yield", cert.get("yield_strength",""), key="r_y")
            with mc[1]:
                cert["elongation"] = st.text_input("Elongation %", cert.get("elongation",""), key="r_e")
                cert["reduction"] = st.text_input("Reduction %", cert.get("reduction",""), key="r_r")

        st.markdown("#### 📋 Specifications")
        sc = st.columns(4)
        for i, (k,l) in enumerate([("astm_a29","ASTM A29"),("astm_a108","ASTM A108"),("astm_a276","ASTM A276"),
                                    ("astm_a320","ASTM A320"),("astm_a496","ASTM A496"),("astm_a1044","ASTM A1044"),
                                    ("aashto_m169","AASHTO M169")]):
            with sc[i%4]:
                cert[k] = st.checkbox(l, cert.get(k, False), key=f"r_sp_{k}")
        cert["additional_spec"] = st.text_input("Additional", cert.get("additional_spec",""), key="r_addspec")

        st.session_state.cert_record = cert

        with st.expander("📎 Data Sources"):
            for k, v in cert.get("sources",{}).items():
                st.write(f"**{k.replace('_',' ').title()}:** {v}")

        st.write("")
        nav = st.columns([1,1,2])
        with nav[0]:
            if st.button("← Back"):
                st.session_state.cert_step = 2 if st.session_state.cert_step == 3 else 1
                st.rerun()
        with nav[1]:
            if st.button("Generate Cert →"):
                st.session_state.cert_step = 4
                st.rerun()

    # ── Step 4: Generated Cert ──
    elif cert_step == 4:
        st.subheader("📄 Generated Certificate")
        cert = st.session_state.cert_record

        try:
            with open("template.html","r") as f: tpl = f.read()
            html = Template(tpl).render(**cert)
            components.html(html, height=1050, scrolling=True)
        except Exception as e:
            st.error(f"Template error: {e}")

        if SHEETS_ENABLED:
            st.write("")
            if st.button("💾 Save to Cert Log & Database"):
                cert_num = save_cert_log(cert)
                save_heat_master(cert, status="Complete")
                if cert_num:
                    st.success(f"✅ Saved as **{cert_num}**!")
                    st.balloons()

        st.write("")
        st.markdown("#### 📥 Export")
        dc = st.columns(3)
        with dc[0]:
            flat = {
                "Customer": cert.get("customer"), "Date": cert.get("date"),
                "PO": cert.get("purchase_order"), "Invoice #": cert.get("invoice_number"),
                "Part #": cert.get("part_number"), "Heat #": cert.get("heat_number"),
                "Qty": cert.get("quantity"), "Description": cert.get("part_description"),
                "Grade": cert.get("grade"),
                "C": cert.get("c"), "Mn": cert.get("mn"), "Si": cert.get("si"),
                "P": cert.get("p"), "S": cert.get("s"), "Cr": cert.get("cr"),
                "Ni": cert.get("ni"), "Mo": cert.get("mo"),
                "Tensile": cert.get("tensile"), "Yield": cert.get("yield_strength"),
                "Elongation %": cert.get("elongation"), "Reduction %": cert.get("reduction"),
            }
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                pd.DataFrame([flat]).to_excel(w, index=False, sheet_name="Cert_Data")
            st.download_button("📥 Excel", buf.getvalue(),
                file_name=f"Cox_Cert_{cert.get('heat_number','x')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with dc[1]:
            st.download_button("📥 JSON",
                json.dumps({k:v for k,v in cert.items() if k!="sources"}, indent=2),
                file_name=f"Cox_Cert_{cert.get('heat_number','x')}.json", mime="application/json")
        with dc[2]:
            try:
                with open("template.html","r") as f: h = Template(f.read()).render(**cert)
                st.download_button("📥 HTML (Print to PDF)", h,
                    file_name=f"Cox_Cert_{cert.get('heat_number','x')}.html", mime="text/html")
            except: pass

        st.info("💡 Open the HTML download in your browser → Print → Save as PDF")

        st.write("")
        nav = st.columns([1,1,2])
        with nav[0]:
            if st.button("← Edit"): st.session_state.cert_step = 3; st.rerun()
        with nav[1]:
            if st.button("🔄 New Cert"):
                st.session_state.cert_record = None
                st.session_state.cert_step = 1
                st.session_state.invoice_data = None
                st.rerun()


st.markdown('<div class="cox-footer">Cox Industries · 24700 Wood CT, Macomb MI 48042 · Powered by Mimir Logic</div>', unsafe_allow_html=True)
