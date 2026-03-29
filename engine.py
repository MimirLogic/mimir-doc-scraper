import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

# 1. Load the secrets from your .env file
load_dotenv() 

# 2. Explicitly grab the key and check if it exists
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("CRITICAL ERROR: Python cannot find your API key in the .env file.")
    exit()

client = genai.Client(api_key=api_key)

# --- Define the Strict Data Structure for the Weld Cert ---

class ChemicalProperties(BaseModel):
    c: str | None
    mn: str | None
    si: str | None
    p: str | None
    s: str | None
    cr: str | None
    ni: str | None
    mo: str | None

class MechanicalProperties(BaseModel):
    grade: str | None
    tensile: str | None
    yield_strength: str | None 
    reduction: str | None
    elongation: str | None

class WeldCertData(BaseModel):
    customer: str | None
    purchase_order: str | None
    part_number: str | None
    part_description: str | None
    invoice_date: str | None
    invoice_number: str | None
    heat_number: str | None
    quantity: str | None
    chemical_properties: ChemicalProperties | None
    mechanical_properties: MechanicalProperties | None

# --- The Extraction Engine ---

def extract_weld_cert_data(pdf_path: str) -> str:
    """
    Reads a vendor invoice and extracts the exact fields needed 
    to populate a Cox Industries CD Weld Stud Certification.
    """
    print(f"[{pdf_path}] Uploading invoice to Gemini Vision...")
    
    try:
        # Upload the file to Google AI Studio
        uploaded_file = client.files.upload(file=pdf_path)
        
        # Construct the Prompt for this specific task
        prompt = (
            "You are a highly accurate manufacturing data extraction assistant for Cox Industries. "
            "Analyze the attached invoice carefully. "
            "Extract the data required to fill out a Material Test Report / Certification. "
            "Map the 'Bill To' name to the customer field. "
            "If a requested field or chemical/mechanical property is missing, return 'N/A'. "
            "Do not guess or invent numbers."
        )

        print(f"[{pdf_path}] Extracting structured form data...")
        
        # Call the Model and force it to use our WeldCertData structure
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[uploaded_file, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=WeldCertData,
                temperature=0.1, 
            ),
        )

        # Clean up the uploaded file to keep your storage clean
        client.files.delete(name=uploaded_file.name)

        # Return the clean, structured JSON response
        return response.text

    except Exception as e:
        print(f"Error during extraction: {e}")
        return None
