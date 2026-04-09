import fitz  # PyMuPDF
import google.generativeai as genai
import json
import re
import os
from typing import Dict, Any, Optional

try:
    from groq import Groq
except ImportError:
    pass

try:
    from openai import OpenAI
except ImportError:
    pass

try:
    from anthropic import Anthropic
except ImportError:
    pass

# Global configuration state
global_ai_config = {
    "provider": "Google Gemini",
    "api_key": ""
}


class RateLimitError(Exception):
    """Raised when the Gemini API returns a 429 quota-exceeded response."""
    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after  # seconds to wait before retrying

def setup_ai(provider: str, api_key: str):
    """Configures the selected AI API."""
    global global_ai_config
    global_ai_config["provider"] = provider
    global_ai_config["api_key"] = api_key
    
    if provider == "Google Gemini":
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

def _clean_json_text(text: str) -> str:
    """Extracts JSON content from text that might contain markdown backticks or preamble."""
    text = text.strip()
    # Find the first occurrences of { or [ and the last } or ]
    start_idx = text.find('{')
    start_arr = text.find('[')
    
    if start_idx == -1 and start_arr == -1:
        return text # Hope for the best
        
    start = start_idx if (start_idx != -1 and (start_arr == -1 or start_idx < start_arr)) else start_arr
    
    end_idx = text.rfind('}')
    end_arr = text.rfind(']')
    end = end_idx if (end_idx != -1 and (end_arr == -1 or end_idx > end_arr)) else end_arr
    
    if start != -1 and end != -1 and end > start:
        return text[start:end+1]
    
    # Fallback to backtick removal if logic above fails
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def _handle_api_error(api_err):
    """Raises RateLimitError or re-raises other errors."""
    err_str = str(api_err)
    
    if "credit balance is too low" in err_str.lower() or "insufficient_quota" in err_str.lower():
        raise RateLimitError(
            "API balance is empty or too low. Please add credits to your provider account or switch to a free provider like Groq.",
            retry_after=0
        )
        
    if "429" in err_str or "quota" in err_str.lower() or "rate" in err_str.lower() or "too_many_requests" in err_str.lower():
        retry_seconds = 60
        match = re.search(r'retry_delay\s*\{\s*seconds:\s*(\d+)', err_str)
        if match:
            retry_seconds = int(match.group(1))
        raise RateLimitError(
            "API free-tier quota exceeded. Please wait and try again.",
            retry_after=retry_seconds
        )
    raise api_err

def extract_structured_data(pdf_text: str) -> Dict[str, Any]:
    """
    Sends the PDF text to the selected AI to extract structured JSON data.
    """
    provider = global_ai_config["provider"]
    api_key = global_ai_config["api_key"]

    # Prevent instant token limit errors by truncating long papers
    # ~40,000 chars is roughly 10,000 tokens, which avoids blowing up free limits.
    max_chars = 40000
    if len(pdf_text) > max_chars:
        pdf_text = pdf_text[:max_chars] + "\n\n...[REMAINDER TRUNCATED TO FIT FREE API LIMITS]"

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
        "summary": "(String) A concise 2-3 paragraph summary of the entire paper",
        "research_objective": "(String) The main goal or problem being solved",
        "detailed_methodology": "(String) Deep technical breakdown of algorithms, architecture, or strategies used",
        "experimental_setup": "(String) Hardware, software, hyperparameters, and environment details",
        "quantitative_results": ["(String) Exact numerical results, comparisons, metrics, and percentages 1", "(String) result 2"],
        "key_findings": ["(String) high-level key observation 1", "(String) high-level key observation 2"],
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
        response_text = ""
        if provider == "Google Gemini":
            model = _get_model()
            response = model.generate_content(prompt)
            response_text = response.text
        elif provider == "Groq (Free & Fast)":
            client = Groq(api_key=api_key)
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            response_text = response.choices[0].message.content
        elif provider == "OpenAI (ChatGPT)":
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            response_text = response.choices[0].message.content
        elif provider == "Anthropic (Claude)":
            client = Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            response_text = response.content[0].text
    except Exception as api_err:
        _handle_api_error(api_err)

    try:
        response_text_clean = _clean_json_text(response_text)
        parsed_data = json.loads(response_text_clean)
        return parsed_data
    except Exception as e:
        raise Exception(f"Failed to parse {provider}'s response into JSON. Raw response partially: {str(response_text)[:200]}...\nError: {e}")


def generate_related_work(papers: list, user_topic: str = "") -> dict:
    """
    Takes a list of extracted paper JSON objects and generates a
    Related Work section suitable for an academic paper.
    Returns a dict with 'related_work_text', 'themes', and 'citation_map'.
    """
    provider = global_ai_config["provider"]
    api_key = global_ai_config["api_key"]


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
        response_text = ""
        if provider == "Google Gemini":
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
            response = model.generate_content(prompt)
            response_text = response.text
        elif provider == "Groq (Free & Fast)":
            client = Groq(api_key=api_key)
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            response_text = response.choices[0].message.content
        elif provider == "OpenAI (ChatGPT)":
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            response_text = response.choices[0].message.content
        elif provider == "Anthropic (Claude)":
            client = Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            response_text = response.content[0].text
    except Exception as api_err:
        _handle_api_error(api_err)

    try:
        resp_text_clean = _clean_json_text(response_text)
        return json.loads(resp_text_clean)
    except Exception:
        # If it completely fails to be JSON, return the raw text as a fallback
        return {
            "related_work_text": str(response_text) if response_text else "Error: Could not retrieve text from response.",
            "themes": [],
            "citation_map": []
        }
