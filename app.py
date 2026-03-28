import streamlit as st
import os
import json
import re
import shutil
from engine import extract_document_data

# --- Helper Functions ---
def sanitize_filename(name):
    """Strips out illegal characters like slashes from part numbers so Windows doesn't crash."""
    return re.sub(r'[\\/*?:"<>|]', "-", str(name)).strip()

def create_output_dir():
    """Creates a folder to drop the finished files into if it doesn't exist."""
    output_dir = "Renamed_Certs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return output_dir

# --- App UI ---
st.set_page_config(page_title="Mimir Logic | Doc Scraper", layout="centered")

st.title("📄 AI Document Scraper")
st.markdown("Upload a vendor cert or blueprint. The AI will extract the data and rename the file for you.")

st.subheader("1. What do you want to extract?")
user_request = st.text_input(
    "Enter fields separated by commas (The AI will use these to name the file)", 
    value="heat_number, part_number"
)
fields_to_extract = [field.strip() for field in user_request.split(",")]

st.subheader("2. Upload Document")
uploaded_file = st.file_uploader("Drag and drop a PDF here", type=["pdf"])

if st.button("Extract & Rename File", type="primary"):
    if uploaded_file is not None and fields_to_extract:
        
        # Save file temporarily for the engine
        temp_pdf_path = f"temp_{uploaded_file.name}"
        with open(temp_pdf_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        with st.spinner("Analyzing document and renaming..."):
            result = extract_document_data(temp_pdf_path, fields_to_extract)
        
        if result:
            try:
                # Parse the JSON data the AI gave us
                parsed_json = json.loads(result)
                
                # Check if the AI actually found what we asked for
                # If it says "NOT_FOUND", we don't want to use that in the file name
                valid_parts = []
                for key, value in parsed_json.items():
                    if value != "NOT_FOUND":
                        valid_parts.append(sanitize_filename(value))
                
                if valid_parts:
                    # Glue the found parts together with an underscore (e.g., HT123_PN456.pdf)
                    new_filename = "_".join(valid_parts) + ".pdf"
                    output_folder = create_output_dir()
                    final_path = os.path.join(output_folder, new_filename)
                    
                    # Move and rename the file!
                    shutil.copy(temp_pdf_path, final_path)
                    
                    st.success(f"Success! File saved as: **{new_filename}**")
                    st.json(parsed_json)
                else:
                    st.warning("The AI could not find any of the requested fields to name the file.")
                    st.json(parsed_json)
                    
            except Exception as e:
                st.error(f"Error formatting the file name: {e}")
        else:
            st.error("Something went wrong during extraction.")
            
        # Always clean up the temp file
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
            
    else:
        st.warning("Please upload a PDF and specify at least one field to extract.")