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

def _get_model():
    """Returns the best available Gemini GenerativeModel."""
    available_models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            available_models.append(m.name)
    if not available_models:
        raise Exception("No text generation models are available on your API key.")
    chosen = available_models[0]
    for pref in ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro', 'models/gemini-1.0-pro']:
        if pref in available_models:
            chosen = pref
            break
    return genai.GenerativeModel(chosen.replace('models/', ''))

def _handle_api_error(api_err):
    """Raises RateLimitError or re-raises other errors."""
    err_str = str(api_err)
    if "429" in err_str or "quota" in err_str.lower() or "rate" in err_str.lower():
        retry_seconds = 60
        match = re.search(r'retry_delay\s*\{\s*seconds:\s*(\d+)', err_str)
        if match:
            retry_seconds = int(match.group(1))
        raise RateLimitError(
            "Gemini API free-tier quota exceeded. Please wait and try again.",
            retry_after=retry_seconds
        )
    raise api_err

def extract_structured_data(pdf_text: str) -> Dict[str, Any]:
    """
    Sends the PDF text to Gemini to extract structured JSON data.
    """
    model = _get_model()

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
        "summary": "(String) A concise 2-3 paragraph summary of the entire paper for a researcher",
        "key_findings": ["(String) key result 1", "(String) key result 2"],
        "datasets": [
           {{
             "name": "(String) Name of the dataset used",
             "link": "(String) URL link to the dataset, if available in text or reference. Use 'Not found' if unavailable."
           }}
        ],
        "limitations": ["(String) limitation 1", "(String) limitation 2"],
        "future_work": ["(String) suggested future research 1"],
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
        _handle_api_error(api_err)

    try:
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


def generate_related_work(papers: list, user_topic: str = "") -> dict:
    """
    Takes a list of extracted paper JSON objects and generates a
    Related Work section suitable for an academic paper.
    Returns a dict with 'related_work_text', 'themes', and 'citation_map'.
    """
    # Use pro model for better writing quality if available
    available_models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            available_models.append(m.name)
    if not available_models:
        raise Exception("No text generation models available.")
    chosen = available_models[0]
    for pref in ['models/gemini-1.5-pro', 'models/gemini-1.5-flash', 'models/gemini-pro', 'models/gemini-1.0-pro']:
        if pref in available_models:
            chosen = pref
            break
    model = genai.GenerativeModel(chosen.replace('models/', ''))

    # Build compact summaries for each paper
    papers_summary = ""
    for i, paper in enumerate(papers, 1):
        title    = paper.get("title", "Unknown Title")
        authors  = ", ".join(paper.get("authors", [])[:3])
        if len(paper.get("authors", [])) > 3:
            authors += " et al."
        abstract = paper.get("abstract", "")[:400]
        summary  = paper.get("summary", "")[:500]
        findings = "; ".join(paper.get("key_findings", [])[:4])
        keywords = ", ".join(paper.get("keywords", [])[:6])
        datasets = ", ".join([d.get("name", "") for d in paper.get("datasets", [])[:3]])

        papers_summary += f"""
--- Paper [{i}] ---
Title: {title}
Authors: {authors}
Keywords: {keywords}
Datasets Used: {datasets if datasets else 'Not specified'}
Abstract: {abstract}
Key Findings: {findings}
Summary: {summary}
"""

    topic_hint = f"The user's own research topic is: {user_topic}\n" if user_topic.strip() else ""

    prompt = f"""
You are an expert academic researcher and scientific writer. Write a comprehensive, well-structured 
"Related Work" section for an academic paper, based on the {len(papers)} papers below.

{topic_hint}

WRITING INSTRUCTIONS:
1. Use formal academic language (journal/conference quality).
2. Group papers THEMATICALLY into 3-5 research themes. Do NOT go paper-by-paper.
3. Use citation format [1], [2], etc. (matching each paper's number below).
4. Highlight agreements, contradictions, gaps, and evolution of ideas.
5. End with a paragraph explaining how gaps in prior work motivate current research.
6. Target length: 600-1000 words.

OUTPUT FORMAT — return ONLY this JSON (no markdown fences):
{{
  "related_work_text": "(String) Full Related Work text. Use newline characters for paragraph breaks.",
  "themes": ["Theme Name 1", "Theme Name 2", "Theme Name 3"],
  "citation_map": [
    {{"ref_num": 1, "title": "Paper title here", "authors": "Author names here"}}
  ]
}}

PAPERS:
{papers_summary}
"""

    try:
        response = model.generate_content(prompt)
    except Exception as api_err:
        _handle_api_error(api_err)

    try:
        resp_text = response.text.strip()
        if resp_text.startswith("```json"):
            resp_text = resp_text[7:]
        if resp_text.startswith("```"):
            resp_text = resp_text[3:]
        if resp_text.endswith("```"):
            resp_text = resp_text[:-3]
        resp_text = resp_text.strip()
        return json.loads(resp_text)
    except Exception:
        return {
            "related_work_text": response.text,
            "themes": [],
            "citation_map": []
        }
