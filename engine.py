import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import create_model

# 1. Load the secrets from your .env file into memory
load_dotenv() 

# 2. Initialize the Gemini Client 
# (It automatically finds GEMINI_API_KEY from the step above)
client = genai.Client()

def extract_document_data(pdf_path: str, fields_to_extract: list[str]) -> dict:
    """
    Takes a PDF and a list of requested fields, uses Gemini Vision to read it,
    and returns a clean dictionary of the extracted data.
    """
    print(f"[{pdf_path}] Uploading document to Gemini...")
    
    try:
        # Upload the file to Google AI Studio
        uploaded_file = client.files.upload(file=pdf_path)
        
        # Dynamically build the Pydantic Schema
        schema_fields = {field_name: (str, ...) for field_name in fields_to_extract}
        DynamicExtractionModel = create_model('DynamicExtractionModel', **schema_fields)

        # Construct the Prompt
        prompt = (
            "You are a precision manufacturing data extraction assistant. "
            "Analyze the attached document carefully. "
            f"Extract the following exact fields: {', '.join(fields_to_extract)}. "
            "If a requested field is entirely missing from the document, return 'NOT_FOUND'. "
            "Do not guess or invent numbers."
        )

        print(f"[{pdf_path}] Analyzing document layout and extracting requested fields...")
        
        # Call the Model
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                uploaded_file,
                prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=DynamicExtractionModel,
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

# --- Test the Engine ---
if __name__ == "__main__":
    # Point this to a real test PDF on your machine
    test_pdf = "sample_vendor_cert.pdf" 
    
    # What do you want to pull?
    customer_request = ["heat_number", "part_number"]
    
    if os.path.exists(test_pdf):
        print("Starting extraction engine...\n" + "-"*30)
        result = extract_document_data(test_pdf, customer_request)
        print("-" * 30)
        print("Final Output:")
        print(result)
    else:
        print(f"Setup Error: Please place a file named '{test_pdf}' in this folder to test.")