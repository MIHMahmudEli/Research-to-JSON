import fitz  # PyMuPDF
import google.generativeai as genai
import json
import re
import os
from typing import Dict, Any, Optional


class RateLimitError(Exception):
    """Raised when the Gemini API returns a 429 quota-exceeded response."""
    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after  # seconds to wait before retrying

def setup_gemini(api_key: str):
    """Configures the Gemini API."""
    genai.configure(api_key=api_key)

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extracts text from a given PDF byte array.
    Raises exceptions for encrypted or completely unreadable PDFs.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        if doc.is_encrypted:
            raise ValueError("The uploaded PDF is encrypted and cannot be parsed.")
        
        text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text()
            
        if not text.strip():
            raise ValueError("The PDF appears to be empty or contains scannable images instead of readable text.")
            
        return text
    except Exception as e:
        raise Exception(f"Failed to read PDF: {str(e)}")

def extract_structured_data(pdf_text: str) -> Dict[str, Any]:
    """
    Sends the PDF text to Gemini to extract structured JSON data.
    """
    available_models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            available_models.append(m.name)
            
    if not available_models:
        raise Exception("No text generation models are available on your API key. Please check your Google AI Studio project.")
        
    chosen_model_name = available_models[0]
    # Prefer faster/standard models if they exist in the list
    for pref in ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro', 'models/gemini-1.0-pro']:
        if pref in available_models:
            chosen_model_name = pref
            break
            
    model = genai.GenerativeModel(chosen_model_name.replace('models/', ''))
    
    prompt = f"""
    You are an expert academic research assistant. Your task is to analyze the following research paper text 
    and extract the structured data according to the exact JSON schema provided below. 
    
    CRITICAL INSTRUCTIONS:
    - Return ONLY valid JSON.
    - Do NOT include markdown code blocks like ```json or ``` at the start or end. 
    - Output the raw JSON directly so it can be parsed programmatically.
    
    REQUIRED JSON SCHEMA:
    {{
        "title": "(String) The title of the paper",
        "authors": ["(String)", "(String) list of authors"],
        "abstract": "(String) The abstract of the paper",
        "keywords": ["(String)", "(String) list of keywords"],
        "sections": [
            {{
                "heading": "(String) The heading of the section (e.g., Introduction, Methodology)",
                "body": "(String) A concise summary or the text of the section"
            }}
        ],
        "references": ["(String) extracted reference", "(String) another reference"]
    }}
    
    PAPER TEXT TO ANALYZE:
    =======================
    {pdf_text}
    =======================
    """
    
    try:
        response = model.generate_content(prompt)
    except Exception as api_err:
        err_str = str(api_err)
        # Detect quota / rate-limit errors (HTTP 429)
        if "429" in err_str or "quota" in err_str.lower() or "rate" in err_str.lower():
            # Try to parse the retry_delay seconds from the error message
            retry_seconds = 60  # safe default
            match = re.search(r'retry_delay\s*\{\s*seconds:\s*(\d+)', err_str)
            if match:
                retry_seconds = int(match.group(1))
            raise RateLimitError(
                "Gemini API free-tier quota exceeded. Please wait and try again.",
                retry_after=retry_seconds
            )
        raise  # re-raise any other API errors as-is

    try:
        # Parse the response; strip any accidental markdown fences
        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        response_text = response_text.strip()
        parsed_data = json.loads(response_text)
        return parsed_data
    except Exception as e:
        raise Exception(f"Failed to parse Gemini's response into JSON. Raw response: {response.text}\nError: {e}")
