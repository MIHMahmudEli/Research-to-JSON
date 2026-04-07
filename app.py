import streamlit as st
import os
import json
import base64
from dotenv import load_dotenv
from utils import setup_gemini, extract_text_from_pdf, extract_structured_data

load_dotenv()

st.set_page_config(
    page_title="Research to JSON — AI Paper Extractor",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Research to JSON | Powered by Google Gemini AI"
    }
)

# ── Premium CSS ────────────────────────────────────────────────────────────
CUSTOM_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
    /* ── Base ── */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .stApp {
        background: #080c14;
        color: #cbd5e1;
    }

    /* ── Animated background ── */
    .stApp::before {
        content: '';
        position: fixed;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background:
            radial-gradient(ellipse at 20% 30%, rgba(88, 101, 242, 0.12) 0%, transparent 50%),
            radial-gradient(ellipse at 80% 70%, rgba(163, 113, 247, 0.10) 0%, transparent 50%),
            radial-gradient(ellipse at 50% 10%, rgba(34, 211, 238, 0.07) 0%, transparent 40%);
        pointer-events: none;
        z-index: 0;
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background: rgba(13, 17, 30, 0.95) !important;
        border-right: 1px solid rgba(255,255,255,0.06) !important;
        backdrop-filter: blur(20px);
    }
    section[data-testid="stSidebar"] * {
        color: #94a3b8 !important;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #e2e8f0 !important;
    }

    /* ── Hero header ── */
    .hero-wrapper {
        text-align: center;
        padding: 2.5rem 1rem 1.5rem;
        position: relative;
    }
    .hero-badge {
        display: inline-block;
        padding: 4px 14px;
        background: rgba(88, 101, 242, 0.15);
        border: 1px solid rgba(88, 101, 242, 0.35);
        border-radius: 100px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #818cf8;
        margin-bottom: 1rem;
    }
    .hero-title {
        font-size: clamp(2rem, 5vw, 3.4rem);
        font-weight: 900;
        line-height: 1.1;
        background: linear-gradient(135deg, #e0e7ff 0%, #818cf8 40%, #a855f7 70%, #ec4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0 0 0.75rem;
    }
    .hero-sub {
        font-size: 1.05rem;
        color: #64748b;
        max-width: 560px;
        margin: 0 auto 1.5rem;
        line-height: 1.7;
        font-weight: 400;
    }

    /* ── Divider ── */
    .fancy-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(129,140,248,0.4), transparent);
        margin: 1.5rem 0;
        border: none;
    }

    /* ── Glass card ── */
    .glass-card {
        background: rgba(15, 20, 40, 0.6);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 16px;
        padding: 1.5rem;
        backdrop-filter: blur(12px);
        box-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05);
        margin-bottom: 1rem;
    }

    /* ── Section headers ── */
    .section-label {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #475569;
        margin-bottom: 0.75rem;
    }
    .section-label::after {
        content: '';
        flex: 1;
        height: 1px;
        background: rgba(255,255,255,0.06);
    }

    /* ── File uploader ── */
    [data-testid="stFileUploader"] {
        border-radius: 14px;
        overflow: hidden;
    }
    [data-testid="stFileUploader"] > div {
        background: rgba(15, 23, 42, 0.7) !important;
        border: 2px dashed rgba(99, 102, 241, 0.35) !important;
        border-radius: 14px !important;
        padding: 2rem !important;
        transition: all 0.3s ease !important;
    }
    [data-testid="stFileUploader"] > div:hover {
        border-color: rgba(129, 140, 248, 0.7) !important;
        background: rgba(99, 102, 241, 0.06) !important;
        box-shadow: 0 0 30px rgba(99, 102, 241, 0.12) !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] p {
        color: #64748b !important;
        font-size: 0.9rem !important;
    }

    /* ── Buttons ── */
    .stDownloadButton button {
        background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.6rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        letter-spacing: 0.02em !important;
        box-shadow: 0 4px 15px rgba(79,70,229,0.4) !important;
        transition: all 0.25s ease !important;
        width: 100% !important;
    }
    .stDownloadButton button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(79,70,229,0.5) !important;
        background: linear-gradient(135deg, #4338ca, #6d28d9) !important;
    }
    .stButton button {
        background: rgba(99,102,241,0.12) !important;
        color: #818cf8 !important;
        border: 1px solid rgba(99,102,241,0.3) !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        transition: all 0.25s ease !important;
    }
    .stButton button:hover {
        background: rgba(99,102,241,0.2) !important;
        border-color: #818cf8 !important;
        color: #e0e7ff !important;
    }

    /* ── Alerts ── */
    .stAlert {
        border-radius: 12px !important;
        border-left-width: 3px !important;
    }
    [data-baseweb="notification"] {
        border-radius: 12px !important;
    }

    /* ── Text input ── */
    .stTextInput input {
        background: rgba(15,20,40,0.8) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        color: #e2e8f0 !important;
        border-radius: 10px !important;
        font-size: 0.88rem !important;
        transition: border-color 0.2s ease !important;
    }
    .stTextInput input:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 3px rgba(99,102,241,0.15) !important;
    }

    /* ── Spinner ── */
    .stSpinner > div {
        border-top-color: #818cf8 !important;
    }

    /* ── PDF iframe ── */
    .pdf-frame-wrapper iframe {
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 12px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.5);
    }

    /* ── Empty state ── */
    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 420px;
        border: 2px dashed rgba(255,255,255,0.06);
        border-radius: 14px;
        color: #334155;
        text-align: center;
        padding: 2rem;
        gap: 12px;
    }
    .empty-state .icon {
        font-size: 3rem;
        opacity: 0.5;
    }
    .empty-state p {
        font-size: 0.9rem;
        margin: 0;
        line-height: 1.6;
    }

    /* ── JSON block ── */
    .stJson {
        border-radius: 12px !important;
        background: rgba(10,14,26,0.8) !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
    }

    /* ── Success banner ── */
    .success-banner {
        background: linear-gradient(135deg, rgba(16,185,129,0.1), rgba(5,150,105,0.08));
        border: 1px solid rgba(16,185,129,0.25);
        border-radius: 12px;
        padding: 0.75rem 1.25rem;
        color: #34d399;
        font-weight: 600;
        font-size: 0.9rem;
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 1rem;
    }

    /* ── Stats row ── */
    .stat-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(99,102,241,0.1);
        border: 1px solid rgba(99,102,241,0.2);
        border-radius: 100px;
        padding: 4px 12px;
        font-size: 0.78rem;
        font-weight: 600;
        color: #818cf8;
        margin: 2px;
    }

    /* ── Sidebar steps ── */
    .step-item {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 10px 0;
        border-bottom: 1px solid rgba(255,255,255,0.04);
    }
    .step-num {
        min-width: 24px;
        height: 24px;
        border-radius: 50%;
        background: linear-gradient(135deg, #4f46e5, #7c3aed);
        color: white;
        font-size: 0.72rem;
        font-weight: 700;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }
    .step-text {
        font-size: 0.85rem;
        color: #94a3b8;
        line-height: 1.5;
    }

    /* remove default streamlit header padding */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
    }
    header[data-testid="stHeader"] { display: none; }
    #MainMenu { display: none; }
    footer { display: none; }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div style='padding: 0.5rem 0 1rem;'>
            <div style='font-size:1.4rem; font-weight:800; background: linear-gradient(135deg,#818cf8,#a855f7); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;'>
                🔬 ResearchJSON
            </div>
            <div style='font-size:0.75rem; color:#475569; margin-top:4px; font-weight:500;'>
                AI-Powered Paper Extractor
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-label">⚙ Configuration</div>', unsafe_allow_html=True)

    api_key_env = os.getenv("GEMINI_API_KEY", "")
    user_api_key = st.text_input(
        "Gemini API Key",
        value=api_key_env,
        type="password",
        placeholder="AIzaSy...",
        help="Get your free key at aistudio.google.com"
    )

    if user_api_key:
        st.markdown('<div style="color:#34d399; font-size:0.8rem; font-weight:600; margin-top:-8px;">✓ API Key provided</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#f59e0b; font-size:0.8rem; font-weight:500; margin-top:-8px;">⚠ API Key required</div>', unsafe_allow_html=True)

    st.markdown('<hr class="fancy-divider" style="margin:1.2rem 0;"/>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">📋 How It Works</div>', unsafe_allow_html=True)

    steps = [
        ("🔑", "Add your Gemini API key in the field above"),
        ("📤", "Drag & drop or browse for a PDF research paper"),
        ("🤖", "AI reads and intelligently extracts all key sections"),
        ("⬇️", "Download the clean structured JSON file"),
    ]
    for i, (icon, text) in enumerate(steps, 1):
        st.markdown(f"""
            <div class="step-item">
                <div class="step-num">{i}</div>
                <div class="step-text">{icon} {text}</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr class="fancy-divider" style="margin:1.2rem 0;"/>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">📊 Schema Output</div>', unsafe_allow_html=True)

    fields = ["title", "authors", "abstract", "keywords", "sections", "references"]
    pills_html = "".join(f'<span class="stat-pill">• {f}</span>' for f in fields)
    st.markdown(f'<div style="line-height:2;">{pills_html}</div>', unsafe_allow_html=True)

    st.markdown('<hr class="fancy-divider" style="margin:1.2rem 0;"/>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.72rem; color:#334155; text-align:center;">Powered by Google Gemini AI · PyMuPDF</div>', unsafe_allow_html=True)

# ── Guard ─────────────────────────────────────────────────────────────────
if not user_api_key:
    st.markdown("""
        <div class="hero-wrapper">
            <div class="hero-badge">AI-Powered Research Tool</div>
            <h1 class="hero-title">Turn Any Research Paper<br/>Into Structured JSON</h1>
            <p class="hero-sub">Upload a PDF academic paper and let Gemini AI automatically extract the title, authors, abstract, keywords, sections, and references — ready for any pipeline.</p>
        </div>
    """, unsafe_allow_html=True)
    st.info("👈 Please enter your **Gemini API Key** in the sidebar to get started.")
    st.stop()

try:
    setup_gemini(user_api_key)
except Exception as e:
    st.error(f"⚠️ Failed to initialise Gemini API: {e}")
    st.stop()

# ── Hero ──────────────────────────────────────────────────────────────────
st.markdown("""
    <div class="hero-wrapper">
        <div class="hero-badge">✦ Powered by Google Gemini AI</div>
        <h1 class="hero-title">Research Paper<br/>→ Structured JSON</h1>
        <p class="hero-sub">Drop your PDF below. Gemini will read and intelligently extract every key field in seconds.</p>
    </div>
    <hr class="fancy-divider"/>
""", unsafe_allow_html=True)

# ── Main split layout ─────────────────────────────────────────────────────
col_pdf, col_extract = st.columns([1, 1], gap="large")

extracted_data = None
file_bytes = None

# ── Right: Upload + Extraction ─────────────────────────────────────────────
with col_extract:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">📤 Upload Paper</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Drag & drop PDF here, or click to browse",
        type=["pdf"],
        label_visibility="collapsed"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    if uploaded_file is not None:
        file_bytes = uploaded_file.read()

        with st.spinner("🤖 Gemini is reading your paper — extracting structure, sections & references…"):
            try:
                pdf_text = extract_text_from_pdf(file_bytes)
                extracted_data = extract_structured_data(pdf_text)
            except Exception as e:
                st.error(f"**Extraction Error:** {e}")

    if extracted_data:
        st.markdown('<div class="success-banner">✅ Extraction complete! Your JSON is ready below.</div>', unsafe_allow_html=True)

        # Quick stats
        num_sections  = len(extracted_data.get("sections", []))
        num_refs      = len(extracted_data.get("references", []))
        num_authors   = len(extracted_data.get("authors", []))
        num_keywords  = len(extracted_data.get("keywords", []))
        stats_html = (
            f'<span class="stat-pill">👥 {num_authors} Authors</span>'
            f'<span class="stat-pill">📑 {num_sections} Sections</span>'
            f'<span class="stat-pill">📚 {num_refs} References</span>'
            f'<span class="stat-pill">🏷 {num_keywords} Keywords</span>'
        )
        st.markdown(f'<div style="margin-bottom:1rem;">{stats_html}</div>', unsafe_allow_html=True)

        with st.expander("📋 View Extracted JSON", expanded=True):
            st.json(extracted_data)

        json_str = json.dumps(extracted_data, indent=4, ensure_ascii=False)
        safe_title = extracted_data.get("title", "research_data")[:40].strip().replace(" ", "_")
        st.download_button(
            label="⬇️  Download JSON File",
            data=json_str,
            file_name=f"{safe_title}.json",
            mime="application/json",
        )
    elif uploaded_file is None:
        st.markdown("""
            <div class="empty-state">
                <div class="icon">📎</div>
                <p><strong style="color:#475569;">No file selected yet</strong><br/>
                Upload a PDF research paper above to begin AI extraction.</p>
            </div>
        """, unsafe_allow_html=True)

# ── Left: PDF Preview ──────────────────────────────────────────────────────
with col_pdf:
    st.markdown('<div class="section-label">📄 Document Preview</div>', unsafe_allow_html=True)
    if file_bytes is not None:
        try:
            b64 = base64.b64encode(file_bytes).decode("utf-8")
            st.markdown(
                f'<div class="pdf-frame-wrapper">'
                f'<iframe src="data:application/pdf;base64,{b64}" '
                f'width="100%" height="820" type="application/pdf" '
                f'style="border:1px solid rgba(255,255,255,0.07); border-radius:14px; box-shadow:0 8px 32px rgba(0,0,0,0.5);">'
                f'</iframe></div>',
                unsafe_allow_html=True
            )
        except Exception:
            st.error("Could not render PDF preview.")
    else:
        st.markdown("""
            <div class="empty-state">
                <div class="icon">📄</div>
                <p><strong style="color:#475569;">PDF preview appears here</strong><br/>
                Upload your paper on the right to see it rendered inline.</p>
            </div>
        """, unsafe_allow_html=True)
