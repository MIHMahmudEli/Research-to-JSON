import streamlit as st
import os
import json
import base64
from dotenv import load_dotenv
from utils import setup_gemini, extract_text_from_pdf, extract_structured_data

# Load env variables
load_dotenv()

# Set Streamlit Page Config
st.set_page_config(
    page_title="Research to JSON",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Custom CSS
custom_css = """
<style>
    /* Global Styling */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
        font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    h1, h2, h3 {
        color: #58a6ff;
        font-weight: 700;
    }
    
    /* Upload Box overrides */
    .css-1n76uvr, .css-1q8dd3e {
        border-radius: 12px;
        background: rgba(33, 38, 45, 0.5) !important;
        border: 2px dashed #30363d !important;
        transition: border 0.3s ease;
    }
    
    .css-1n76uvr:hover, .css-1q8dd3e:hover {
        border-color: #58a6ff !important;
    }
    
    /* JSON Output Formatting */
    .stCodeBlock {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.5);
    }
    
    /* Custom Button */
    .stDownloadButton button {
        background-color: #238636;
        color: white;
        border: 1px solid rgba(240, 246, 252, 0.1);
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        transition: background-color 0.2s ease, border-color 0.2s ease;
    }
    
    .stDownloadButton button:hover {
        background-color: #2ea043;
        border-color: #8b949e;
        color: white;
    }
    
    /* Header Gradient Text */
    .gradient-text {
        background: linear-gradient(90deg, #58a6ff, #a371f7, #f778ba);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# Main App Header
st.markdown("<h1 class='gradient-text'>Research Paper to JSON AI Extractor</h1>", unsafe_allow_html=True)
st.markdown("Upload a PDF research paper, and AI will automatically analyze and extract its metadata, sections, and references into a structured JSON format.")

# API Key Validation (Sidebar)
with st.sidebar:
    st.header("⚙️ Configuration")
    st.markdown("Enter your Google Gemini API Key to enable the AI extraction.")
    
    api_key_env = os.getenv("GEMINI_API_KEY", "")
    user_api_key = st.text_input("Gemini API Key", value=api_key_env, type="password", placeholder="AIzaSy...")
    
    st.markdown("---")
    st.markdown("### How it works")
    st.markdown("1. Provide your Gemini API key.")
    st.markdown("2. Upload a valid PDF file.")
    st.markdown("3. Wait for the intelligent parsing.")
    st.markdown("4. Download the extracted data as JSON.")

if not user_api_key:
    st.warning("⚠️ Please provide a Google Gemini API Key in the sidebar to begin.")
    st.stop()

# Configure API
try:
    setup_gemini(user_api_key)
except Exception as e:
    st.error(f"Failed to configure Gemini API: {e}")
    st.stop()

st.markdown("---")

# Split view placeholder
col1, col2 = st.columns(2, gap="large")

# Right Column: The Extracted JSON and Upload logic
with col2:
    st.subheader("🛠️ Upload & Extraction")
    uploaded_file = st.file_uploader("Drag and Drop your PDF research paper here", type=["pdf"])
    
    extracted_data = None
    
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        
        with st.spinner("🤖 Analyzing the document and extracting structured data... This might take a minute."):
            try:
                # 1. Parse text from PDF
                pdf_text = extract_text_from_pdf(file_bytes)
                
                # 2. Extract structured data with Gemini
                extracted_data = extract_structured_data(pdf_text)
                
                st.success("✅ Extraction Complete!")
                
            except Exception as e:
                st.error(f"An error occurred: {e}")
        
    if extracted_data:
        st.subheader("📋 JSON Result")
        st.json(extracted_data)
        
        # Download button
        json_str = json.dumps(extracted_data, indent=4)
        st.download_button(
            label="⬇️ Download JSON File",
            data=json_str,
            file_name=f"{extracted_data.get('title', 'research_data')[:30].replace(' ', '_')}.json",
            mime="application/json"
        )
        
# Left Column: PDF Preview
with col1:
    st.subheader("📄 Document Preview")
    if uploaded_file is not None:
        try:
            # Base64 encode the PDF for iframe display
            base64_pdf = base64.b64encode(file_bytes).decode('utf-8')
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800px" type="application/pdf" style="border-radius: 8px; border: 1px solid #30363d;"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)
        except Exception as e:
            st.error("Failed to render PDF preview.")
    else:
        st.info("Upload a PDF to see the preview here.")
