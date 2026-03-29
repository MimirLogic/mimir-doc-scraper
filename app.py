import streamlit as st
import os
import json
import streamlit.components.v1 as components
from jinja2 import Template
from engine import extract_weld_cert_data

# --- App UI ---
st.set_page_config(page_title="Mimir Logic | Form Autofiller", layout="wide")

st.title("⚡ Mimir Logic: Auto-Form Filler")
st.markdown("Upload a vendor invoice. The AI will extract the data and perfectly populate a Cox Industries Cert.")

# File Uploader - Now supports images!
uploaded_file = st.file_uploader("Upload Vendor Invoice (PDF or Picture)", type=["pdf", "png", "jpg", "jpeg"])

if st.button("Extract Data & Generate Cert", type="primary"):
    if uploaded_file is not None:
        
        # Save file temporarily for the engine
        temp_file_path = f"temp_{uploaded_file.name}"
        with open(temp_file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        with st.spinner("🤖 AI is reading the invoice and mapping data to the form..."):
            # 1. Get the JSON string from our AI engine
            json_result = extract_weld_cert_data(temp_file_path)
            
            if json_result:
                try:
                    # 2. Convert the JSON string into a Python Dictionary
                    data_dict = json.loads(json_result)
                    
                    # 3. Read our blank HTML template
                    with open("template.html", "r") as file:
                        template_string = file.read()
                        
                    # 4. Merge the data into the template using Jinja2
                    jinja_template = Template(template_string)
                    completed_html = jinja_template.render(**data_dict)
                    
                    st.success("✅ Form successfully populated!")
                    
                    # 5. Display the completed form right on the screen
                    st.markdown("### Your Completed Certificate:")
                    st.info("💡 Tip: To save this as a PDF, right-click the form below and select 'Print' -> 'Save as PDF'.")
                    
                    # Render the HTML in Streamlit
                    components.html(completed_html, height=850, scrolling=True)
                    
                    # Show the raw data on the side for proof
                    with st.expander("🔍 View Raw Extracted Data (For the Boss)"):
                        st.json(data_dict)
                        
                except Exception as e:
                    st.error(f"Error formatting the form: {e}")
            else:
                st.error("The AI failed to extract data from this document.")
                
        # Clean up temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
    else:
        st.warning("Please upload an invoice or picture first.")
