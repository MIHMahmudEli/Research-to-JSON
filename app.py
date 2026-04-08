import streamlit as st
import os
import json
import fitz  # PyMuPDF
from dotenv import load_dotenv
from utils import (
    setup_gemini, extract_text_from_pdf,
    extract_structured_data, generate_related_work, RateLimitError
)

load_dotenv()

st.set_page_config(
    page_title="Research to JSON — AI Paper Extractor",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={'About': "Research to JSON | Powered by Google Gemini AI"}
)

# ── CSS ───────────────────────────────────────────────────────────────────
CUSTOM_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #080c14; color: #cbd5e1; }

    /* Animated BG */
    .stApp::before {
        content: ''; position: fixed; top: -50%; left: -50%;
        width: 200%; height: 200%;
        background:
            radial-gradient(ellipse at 20% 30%, rgba(88,101,242,0.12) 0%, transparent 50%),
            radial-gradient(ellipse at 80% 70%, rgba(163,113,247,0.10) 0%, transparent 50%),
            radial-gradient(ellipse at 50% 10%, rgba(34,211,238,0.07) 0%, transparent 40%);
        pointer-events: none; z-index: 0;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: rgba(13,17,30,0.95) !important;
        border-right: 1px solid rgba(255,255,255,0.06) !important;
        backdrop-filter: blur(20px);
    }
    section[data-testid="stSidebar"] * { color: #94a3b8 !important; }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 { color: #e2e8f0 !important; }

    /* Hero */
    .hero-wrapper { text-align: left; padding: 1.5rem 0 1.2rem; }
    .hero-badge {
        display: inline-block; padding: 4px 14px;
        background: rgba(88,101,242,0.15); border: 1px solid rgba(88,101,242,0.35);
        border-radius: 100px; font-size: 0.72rem; font-weight: 600;
        letter-spacing: 0.12em; text-transform: uppercase; color: #818cf8; margin-bottom: 0.8rem;
    }
    .hero-title {
        font-size: clamp(1.8rem, 4vw, 3rem); font-weight: 900; line-height: 1.1;
        background: linear-gradient(135deg, #e0e7ff 0%, #818cf8 40%, #a855f7 70%, #ec4899 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text; margin: 0 0 0.6rem;
    }
    .hero-sub {
        font-size: 1rem; color: #64748b; max-width: 600px;
        margin: 0 0 1rem; line-height: 1.7; font-weight: 400;
    }

    /* Divider */
    .fancy-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(129,140,248,0.4), transparent);
        margin: 1.2rem 0; border: none;
    }

    /* Cards */
    .premium-card {
        background: rgba(15,20,40,0.45); border: 1px solid rgba(255,255,255,0.08);
        border-radius: 20px; padding: 1.75rem; backdrop-filter: blur(16px);
        box-shadow: 0 10px 40px rgba(0,0,0,0.3); margin-bottom: 1rem;
        position: relative; overflow: hidden; transition: all 0.3s ease;
    }
    .premium-card:hover { transform: translateY(-3px); box-shadow: 0 15px 50px rgba(99,102,241,0.15); border-color: rgba(99,102,241,0.3); }
    .premium-card::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0;
        height: 2px; background: linear-gradient(90deg, transparent, #6366f1, transparent); opacity: 0.5;
    }

    /* Related Work text card */
    .rw-card {
        background: rgba(10,14,26,0.7); border: 1px solid rgba(129,140,248,0.2);
        border-radius: 16px; padding: 2rem 2.5rem; margin-bottom: 1.5rem;
        line-height: 1.85; font-size: 1rem; color: #e2e8f0;
        white-space: pre-wrap; word-wrap: break-word;
        box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    }

    /* Citation list */
    .citation-item {
        display: flex; align-items: flex-start; gap: 14px;
        padding: 12px 18px; margin-bottom: 10px;
        background: rgba(99,102,241,0.05); border-radius: 12px;
        border-left: 3px solid rgba(99,102,241,0.4); transition: all 0.2s ease;
    }
    .citation-item:hover { background: rgba(99,102,241,0.1); border-left-color: #818cf8; }
    .citation-num {
        min-width: 28px; height: 28px; border-radius: 50%;
        background: linear-gradient(135deg, #4f46e5, #7c3aed);
        color: #fff; font-size: 0.78rem; font-weight: 700;
        display: flex; align-items: center; justify-content: center; flex-shrink: 0;
    }

    /* Theme chip */
    .theme-chip {
        display: inline-flex; align-items: center; gap: 5px;
        padding: 5px 15px; margin: 4px;
        background: rgba(168,85,247,0.1); border: 1px solid rgba(168,85,247,0.3);
        border-radius: 100px; font-size: 0.8rem; font-weight: 600; color: #c084fc;
    }

    /* Section labels */
    .section-label {
        display: flex; align-items: center; gap: 8px;
        font-size: 0.8rem; font-weight: 700; letter-spacing: 0.1em;
        text-transform: uppercase; color: #475569; margin-bottom: 0.75rem; margin-top: 1rem;
    }
    .section-label::after { content: ''; flex: 1; height: 1px; background: rgba(255,255,255,0.06); }

    /* File uploader */
    [data-testid="stFileUploader"] { border-radius: 14px; overflow: hidden; }
    [data-testid="stFileUploader"] > div {
        background: rgba(15,23,42,0.7) !important;
        border: 2px dashed rgba(99,102,241,0.35) !important;
        border-radius: 14px !important; padding: 2rem !important; transition: all 0.3s ease !important;
    }
    [data-testid="stFileUploader"] > div:hover {
        border-color: rgba(129,140,248,0.7) !important;
        background: rgba(99,102,241,0.06) !important;
        box-shadow: 0 0 30px rgba(99,102,241,0.12) !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; background: transparent !important; }
    .stTabs [data-baseweb="tab"] {
        height: 42px; border-radius: 10px 10px 0 0 !important;
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
        color: #94a3b8 !important; font-weight: 500 !important; transition: all 0.3s ease !important;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(99,102,241,0.12) !important; color: #818cf8 !important;
        border-color: rgba(99,102,241,0.4) !important; font-weight: 700 !important;
    }

    /* Buttons */
    .stDownloadButton button {
        background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
        color: #fff !important; border: none !important; border-radius: 12px !important;
        font-weight: 700 !important; box-shadow: 0 4px 15px rgba(79,70,229,0.4) !important;
        transition: all 0.25s ease !important; width: 100% !important; margin-top: 0.5rem !important;
    }
    .stDownloadButton button:hover { transform: translateY(-2px) !important; box-shadow: 0 8px 25px rgba(79,70,229,0.5) !important; }

    /* Stat pills */
    .stat-pill {
        display: inline-flex; align-items: center; gap: 5px;
        background: rgba(99,102,241,0.1); border: 1px solid rgba(99,102,241,0.2);
        border-radius: 100px; padding: 5px 14px;
        font-size: 0.75rem; font-weight: 700; color: #818cf8; margin: 3px;
    }

    /* Success */
    .success-banner {
        background: linear-gradient(135deg, rgba(16,185,129,0.1), rgba(5,150,105,0.08));
        border: 1px solid rgba(16,185,129,0.25); border-radius: 12px;
        padding: 0.75rem 1.25rem; color: #34d399; font-weight: 600;
        font-size: 0.9rem; display: flex; align-items: center; gap: 8px; margin-bottom: 1.5rem;
    }

    /* List items */
    .list-item {
        margin-bottom: 14px; padding: 12px 16px;
        background: rgba(255,255,255,0.02); border-radius: 12px;
        border-left: 3px solid rgba(99,102,241,0.4); transition: all 0.2s ease; color: #cbd5e1;
    }
    .list-item:hover { background: rgba(99,102,241,0.06); border-left-color: #818cf8; transform: translateX(4px); }

    /* Empty state */
    .empty-state {
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        min-height: 380px; border: 2px dashed rgba(255,255,255,0.06);
        border-radius: 14px; color: #334155; text-align: center; padding: 2rem; gap: 12px;
    }
    .empty-state .icon { font-size: 3rem; opacity: 0.4; }
    .empty-state p { font-size: 0.9rem; margin: 0; line-height: 1.6; }

    /* Sidebar steps */
    .step-item { display: flex; align-items: flex-start; gap: 12px; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.04); }
    .step-num {
        min-width: 24px; height: 24px; border-radius: 50%;
        background: linear-gradient(135deg, #4f46e5, #7c3aed);
        color: white; font-size: 0.72rem; font-weight: 700;
        display: flex; align-items: center; justify-content: center; flex-shrink: 0;
    }
    .step-text { font-size: 0.85rem; color: #94a3b8; line-height: 1.5; }

    /* Glass card */
    .glass-card {
        background: rgba(15,20,40,0.6); border: 1px solid rgba(255,255,255,0.07);
        border-radius: 16px; padding: 1.5rem; backdrop-filter: blur(12px);
        box-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05); margin-bottom: 1rem;
    }

    /* Insight text */
    .insight-text { font-size: 1rem; line-height: 1.75; color: #cbd5e1; }

    /* Animations */
    @keyframes fadeIn { from { opacity: 0; transform: translateY(15px); } to { opacity: 1; transform: translateY(0); } }
    .fade-in { animation: fadeIn 0.7s cubic-bezier(0.16,1,0.3,1) forwards; }

    /* Rate limit */
    .rate-limit-card {
        background: linear-gradient(135deg, rgba(245,158,11,0.08), rgba(239,68,68,0.06));
        border: 1px solid rgba(245,158,11,0.3); border-radius: 16px;
        padding: 1.5rem 1.75rem; margin-bottom: 1rem; position: relative; overflow: hidden;
    }
    .rate-limit-card::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, #f59e0b, #ef4444); border-radius: 16px 16px 0 0;
    }

    /* Page nav buttons */
    .nav-btn {
        display: inline-flex; align-items: center; gap: 8px;
        padding: 10px 22px; border-radius: 12px; border: 1px solid rgba(99,102,241,0.3);
        background: rgba(99,102,241,0.08); color: #818cf8; font-size: 0.9rem;
        font-weight: 600; text-decoration: none; cursor: pointer; transition: all 0.2s ease;
        font-family: 'Inter', sans-serif; margin: 0 6px;
    }
    .nav-btn.active {
        background: linear-gradient(135deg, #4f46e5, #7c3aed);
        border-color: transparent; color: #fff;
        box-shadow: 0 4px 15px rgba(79,70,229,0.4);
    }

    .block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; }
    header[data-testid="stHeader"] { display: none; }
    footer { display: none; }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div style='padding: 0.5rem 0 1rem;'>
            <div style='font-size:1.5rem; font-weight:800; background: linear-gradient(135deg,#818cf8,#a855f7); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;'>
                🔬 ResearchJSON
            </div>
            <div style='font-size:0.75rem; color:#475569; margin-top:4px; font-weight:500;'>
                AI-Powered Paper Extractor & Writer
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-label">⚙ Configuration</div>', unsafe_allow_html=True)
    api_key_env = os.getenv("GEMINI_API_KEY", "")
    user_api_key = st.text_input(
        "Gemini API Key", value=api_key_env, type="password",
        placeholder="AIzaSy...", help="Get your free key at aistudio.google.com"
    )
    if user_api_key:
        st.markdown('<div style="color:#34d399; font-size:0.8rem; font-weight:600; margin-top:-8px;">✓ API Key provided</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#f59e0b; font-size:0.8rem; font-weight:500; margin-top:-8px;">⚠ API Key required</div>', unsafe_allow_html=True)

    st.markdown('<hr class="fancy-divider" style="margin:1.2rem 0;"/>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">🧭 Navigation</div>', unsafe_allow_html=True)

    if "page" not in st.session_state:
        st.session_state.page = "extractor"

    if st.button("📄 Paper Extractor", use_container_width=True):
        st.session_state.page = "extractor"
    if st.button("✍️ Related Work Generator", use_container_width=True):
        st.session_state.page = "related_work"

    st.markdown('<hr class="fancy-divider" style="margin:1.2rem 0;"/>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.72rem; color:#334155; text-align:center;">Powered by Google Gemini AI · PyMuPDF</div>', unsafe_allow_html=True)

# ── API guard ─────────────────────────────────────────────────────────────
if not user_api_key:
    st.markdown("""
        <div class="hero-wrapper fade-in">
            <div class="hero-badge">AI-Powered Research Tool</div>
            <h1 class="hero-title">Turn Research Papers<br/>Into Structured Data</h1>
            <p class="hero-sub">Extract, analyze, and synthesize academic papers with Google Gemini AI.</p>
        </div>
    """, unsafe_allow_html=True)
    st.info("👈 Please enter your **Gemini API Key** in the sidebar to get started.")
    st.stop()

try:
    setup_gemini(user_api_key)
except Exception as e:
    st.error(f"⚠️ Failed to initialise Gemini API: {e}")
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════
# PAGE 1 — PAPER EXTRACTOR
# ═══════════════════════════════════════════════════════════════════════════
if st.session_state.page == "extractor":
    st.markdown("""
        <div class="hero-wrapper fade-in">
            <div class="hero-badge">✦ Step 1 of 2 — Extract Papers</div>
            <h1 class="hero-title">Research Paper<br/><span style="opacity:0.85;">→ Structured JSON</span></h1>
            <p class="hero-sub">Upload a PDF and Gemini extracts title, abstract, datasets, key findings, and more — ready to use in the Related Work Generator.</p>
        </div>
    """, unsafe_allow_html=True)

    # Session state
    for key in ["extracted_data", "last_filename", "file_bytes"]:
        if key not in st.session_state:
            st.session_state[key] = None

    col_pdf, col_extract = st.columns([1, 1], gap="large")

    with col_extract:
        st.markdown('<div class="section-label">📤 Upload Paper</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Drag & drop PDF", type=["pdf"], label_visibility="collapsed"
        )

        if uploaded_file is not None:
            if uploaded_file.name != st.session_state.last_filename:
                st.session_state.file_bytes = uploaded_file.read()
                st.session_state.extracted_data = None
                st.session_state.last_filename = uploaded_file.name

                with st.spinner("🤖 Gemini is reading your paper…"):
                    try:
                        pdf_text = extract_text_from_pdf(st.session_state.file_bytes)
                        st.session_state.extracted_data = extract_structured_data(pdf_text)
                    except RateLimitError as rle:
                        st.markdown(f"""
                            <div class="rate-limit-card">
                                <div style="font-size:1rem; font-weight:700; color:#fbbf24;">⚠️ API Quota Exceeded</div>
                                <div style="font-size:0.88rem; color:#94a3b8; margin:0.5rem 0;">
                                    Free-tier limit reached. Please wait <strong style="color:#fbbf24;">{rle.retry_after}s</strong> before retrying.
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Extraction Error: {e}")
        else:
            st.session_state.extracted_data = None
            st.session_state.last_filename = None
            st.session_state.file_bytes = None

        ed = st.session_state.extracted_data
        if ed:
            st.markdown('<div class="success-banner">✅ Extraction complete! Analysis dashboard ready below.</div>', unsafe_allow_html=True)

            stats_html = (
                f'<span class="stat-pill">👥 {len(ed.get("authors",[]))} Authors</span>'
                f'<span class="stat-pill">📊 {len(ed.get("datasets",[]))} Datasets</span>'
                f'<span class="stat-pill">📑 {len(ed.get("sections",[]))} Sections</span>'
                f'<span class="stat-pill">📚 {len(ed.get("references",[]))} References</span>'
            )
            st.markdown(f'<div style="margin-bottom:1.5rem;">{stats_html}</div>', unsafe_allow_html=True)

            t_summary, t_insights, t_datasets, t_raw = st.tabs([
                "📝 Summary", "💡 Insights", "📦 Datasets", "🔍 Raw JSON"
            ])

            with t_summary:
                st.markdown('<div style="margin-top:1rem;"></div>', unsafe_allow_html=True)
                if ed.get("summary"):
                    st.markdown(f'<div class="premium-card insight-text">{ed["summary"]}</div>', unsafe_allow_html=True)
                else:
                    st.info("No summary extracted.")

            with t_insights:
                st.markdown('<div style="margin-top:1rem;"></div>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    if ed.get("key_findings"):
                        st.markdown('<div class="section-label">💡 Key Findings</div>', unsafe_allow_html=True)
                        for f in ed["key_findings"]:
                            st.markdown(f'<div class="list-item">{f}</div>', unsafe_allow_html=True)
                with c2:
                    if ed.get("limitations"):
                        st.markdown('<div class="section-label">⚠️ Limitations</div>', unsafe_allow_html=True)
                        for l in ed["limitations"]:
                            st.markdown(f'<div class="list-item">{l}</div>', unsafe_allow_html=True)
                if ed.get("future_work"):
                    st.markdown('<div class="section-label">🚀 Future Work</div>', unsafe_allow_html=True)
                    for fw in ed["future_work"]:
                        st.markdown(f'<div class="list-item">{fw}</div>', unsafe_allow_html=True)

            with t_datasets:
                st.markdown('<div style="margin-top:1rem;"></div>', unsafe_allow_html=True)
                if ed.get("datasets"):
                    for d in ed["datasets"]:
                        name = d.get("name", "Unknown")
                        link = d.get("link", "Not found")
                        btn = ""
                        if link.lower() != "not found" and "http" in link.lower():
                            btn = f'<br/><a href="{link}" target="_blank" style="display:inline-block;margin-top:10px;padding:6px 14px;background:rgba(99,102,241,0.15);border:1px solid rgba(99,102,241,0.3);border-radius:8px;color:#818cf8;text-decoration:none;font-size:0.85rem;font-weight:600;">🔗 Open Dataset</a>'
                        st.markdown(f'<div class="premium-card"><strong style="color:#fff;">{name}</strong>{btn}</div>', unsafe_allow_html=True)
                else:
                    st.info("No datasets identified in this paper.")

            with t_raw:
                st.markdown('<div style="margin-top:1rem;"></div>', unsafe_allow_html=True)
                st.json(ed)

            json_str = json.dumps(ed, indent=4, ensure_ascii=False)
            safe_title = ed.get("title", "paper")[:30].strip().replace(" ", "_")
            st.download_button(
                label="⬇️ Download JSON",
                data=json_str,
                file_name=f"{safe_title}.json",
                mime="application/json",
            )
            st.markdown("""
                <div style="margin-top:1rem; padding:12px 16px; background:rgba(99,102,241,0.06); border:1px solid rgba(99,102,241,0.2); border-radius:12px; font-size:0.85rem; color:#818cf8;">
                    💡 <strong>Tip:</strong> Download this JSON file, then use the <strong>Related Work Generator</strong> (sidebar) to compile multiple papers into a written Related Work section.
                </div>
            """, unsafe_allow_html=True)
        elif uploaded_file is None:
            st.markdown("""
                <div class="empty-state">
                    <div class="icon">📎</div>
                    <p><strong style="color:#475569;">No file selected</strong><br/>
                    Upload a PDF research paper to start AI extraction.</p>
                </div>
            """, unsafe_allow_html=True)

    with col_pdf:
        st.markdown('<div class="section-label">📄 PDF Preview</div>', unsafe_allow_html=True)
        if st.session_state.file_bytes:
            try:
                doc = fitz.open(stream=st.session_state.file_bytes, filetype="pdf")
                total_pages = len(doc)
                pg = st.number_input("Page", min_value=1, max_value=total_pages, value=1, label_visibility="collapsed")
                page = doc.load_page(pg - 1)
                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
                st.image(pix.tobytes("png"), use_container_width=True)
                st.markdown(f"<div style='text-align:center;color:#475569;font-size:0.8rem;'>Page {pg} of {total_pages}</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Render Error: {e}")
        else:
            st.markdown("""
                <div class="empty-state">
                    <div class="icon">📄</div>
                    <p><strong style="color:#475569;">PDF Preview</strong><br/>Upload a paper to see it here.</p>
                </div>
            """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 2 — RELATED WORK GENERATOR
# ═══════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "related_work":
    st.markdown("""
        <div class="hero-wrapper fade-in">
            <div class="hero-badge">✦ Step 2 of 2 — Write Related Work</div>
            <h1 class="hero-title">Related Work<br/><span style="opacity:0.85;">Generator</span></h1>
            <p class="hero-sub">Upload up to <strong style="color:#818cf8;">30 JSON files</strong> exported from the Paper Extractor. Gemini will analyze all papers and write a full, thematic Related Work section ready for your paper.</p>
        </div>
    """, unsafe_allow_html=True)

    # Session state for this page
    for key in ["rw_result", "rw_papers_loaded"]:
        if key not in st.session_state:
            st.session_state[key] = None

    # ── Configuration row ──
    cfg_col1, cfg_col2 = st.columns([2, 1], gap="large")

    with cfg_col1:
        st.markdown('<div class="section-label">📁 Upload JSON Files (max 30)</div>', unsafe_allow_html=True)
        json_files = st.file_uploader(
            "Upload extracted paper JSON files",
            type=["json"],
            accept_multiple_files=True,
            label_visibility="collapsed",
            help="Upload JSON files exported from the Paper Extractor tab."
        )

    with cfg_col2:
        st.markdown('<div class="section-label">🎯 Your Research Topic (optional)</div>', unsafe_allow_html=True)
        user_topic = st.text_area(
            "Your research topic",
            placeholder="e.g., Deep learning for medical image segmentation using transformers...",
            height=120,
            label_visibility="collapsed",
            help="Describing your topic helps Gemini make the Related Work more relevant."
        )

    # Validate and load JSON files
    papers = []
    errors = []

    if json_files:
        if len(json_files) > 30:
            st.warning(f"⚠️ You uploaded {len(json_files)} files. Only the first 30 will be used.")
            json_files = json_files[:30]

        for f in json_files:
            try:
                data = json.load(f)
                if isinstance(data, dict):
                    papers.append(data)
                else:
                    errors.append(f"⚠️ `{f.name}` — Not a valid paper JSON object.")
            except Exception as e:
                errors.append(f"❌ `{f.name}` — Parse error: {e}")

        if errors:
            for err in errors:
                st.warning(err)

    # ── Papers Preview ──
    if papers:
        st.markdown('<hr class="fancy-divider"/>', unsafe_allow_html=True)
        st.markdown(f'<div class="section-label">📚 {len(papers)} Papers Loaded</div>', unsafe_allow_html=True)

        cols = st.columns(3)
        for idx, paper in enumerate(papers):
            with cols[idx % 3]:
                title = paper.get("title", "Untitled")[:60]
                authors = ", ".join(paper.get("authors", ["Unknown"])[:2])
                if len(paper.get("authors", [])) > 2:
                    authors += " et al."
                kw_count = len(paper.get("keywords", []))
                ds_count = len(paper.get("datasets", []))
                st.markdown(f"""
                    <div class="premium-card" style="padding:1.2rem;">
                        <div style="font-size:0.75rem; color:#818cf8; font-weight:600; margin-bottom:4px;">[{idx+1}]</div>
                        <div style="font-size:0.88rem; font-weight:700; color:#e2e8f0; line-height:1.4; margin-bottom:6px;">{title}</div>
                        <div style="font-size:0.75rem; color:#64748b;">{authors}</div>
                        <div style="margin-top:8px;">
                            <span class="stat-pill" style="font-size:0.68rem;">🏷 {kw_count} kw</span>
                            <span class="stat-pill" style="font-size:0.68rem;">📊 {ds_count} ds</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        st.markdown('<hr class="fancy-divider"/>', unsafe_allow_html=True)

        # ── Generate Button ──
        gen_col, _ = st.columns([1, 2])
        with gen_col:
            generate_btn = st.button(
                f"🤖 Generate Related Work ({len(papers)} papers)",
                use_container_width=True,
                type="primary"
            )

        if generate_btn:
            st.session_state.rw_result = None
            with st.spinner("✍️ Gemini is reading all papers and crafting your Related Work section… (this may take 20-60 seconds)"):
                try:
                    result = generate_related_work(papers, user_topic=user_topic)
                    st.session_state.rw_result = result
                except RateLimitError as rle:
                    st.markdown(f"""
                        <div class="rate-limit-card">
                            <div style="font-size:1rem;font-weight:700;color:#fbbf24;">⚠️ API Quota Exceeded</div>
                            <div style="font-size:0.88rem;color:#94a3b8;margin:0.5rem 0;">
                                Please wait <strong style="color:#fbbf24;">{rle.retry_after} seconds</strong> and try again.
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Generation Error: {e}")

    elif json_files is not None and len(json_files) == 0:
        st.markdown("""
            <div class="empty-state" style="min-height:300px;">
                <div class="icon">📂</div>
                <p><strong style="color:#475569;">No JSON files uploaded</strong><br/>
                Export JSON files from the Paper Extractor, then upload up to 30 here.</p>
            </div>
        """, unsafe_allow_html=True)

    # ── Results ──
    rw = st.session_state.rw_result
    if rw:
        rw_text       = rw.get("related_work_text", "")
        themes        = rw.get("themes", [])
        citation_map  = rw.get("citation_map", [])

        st.markdown('<div class="success-banner">✅ Related Work section generated! Review, copy, or download below.</div>', unsafe_allow_html=True)

        # Theme chips
        if themes:
            st.markdown('<div class="section-label">🗂 Identified Themes</div>', unsafe_allow_html=True)
            chips_html = "".join(f'<span class="theme-chip">📌 {t}</span>' for t in themes)
            st.markdown(f'<div style="margin-bottom:1.5rem;">{chips_html}</div>', unsafe_allow_html=True)

        rw_tab, cite_tab = st.tabs(["📝 Related Work Text", "📖 Reference List"])

        with rw_tab:
            st.markdown('<div style="margin-top:1rem;"></div>', unsafe_allow_html=True)

            # Render text with proper paragraphs
            paragraphs = rw_text.split("\n\n") if "\n\n" in rw_text else rw_text.split("\n")
            rendered = "".join(
                f'<p style="margin:0 0 1.2rem 0;">{p.strip()}</p>'
                for p in paragraphs if p.strip()
            )
            st.markdown(f'<div class="rw-card">{rendered}</div>', unsafe_allow_html=True)

            # Copy-friendly text area
            st.text_area(
                "📋 Copy-ready text",
                value=rw_text,
                height=200,
                label_visibility="collapsed",
                help="Select all & copy from here"
            )

            # Download as .txt
            st.download_button(
                label="⬇️ Download as .txt",
                data=rw_text,
                file_name="related_work.txt",
                mime="text/plain",
            )

            # Download full JSON result
            st.download_button(
                label="⬇️ Download Full Result (JSON)",
                data=json.dumps(rw, indent=2, ensure_ascii=False),
                file_name="related_work_result.json",
                mime="application/json",
            )

        with cite_tab:
            st.markdown('<div style="margin-top:1rem;"></div>', unsafe_allow_html=True)
            if citation_map:
                for cite in citation_map:
                    ref_num = cite.get("ref_num", "?")
                    title   = cite.get("title", "Unknown Title")
                    authors = cite.get("authors", "Unknown Authors")
                    st.markdown(f"""
                        <div class="citation-item">
                            <div class="citation-num">{ref_num}</div>
                            <div>
                                <div style="font-weight:600; color:#e2e8f0; font-size:0.9rem;">{title}</div>
                                <div style="color:#64748b; font-size:0.8rem; margin-top:3px;">{authors}</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                # Build from loaded papers as fallback
                for i, paper in enumerate(papers, 1):
                    title   = paper.get("title", "Unknown Title")
                    authors_list = paper.get("authors", [])
                    authors = ", ".join(authors_list[:3])
                    if len(authors_list) > 3:
                        authors += " et al."
                    st.markdown(f"""
                        <div class="citation-item">
                            <div class="citation-num">{i}</div>
                            <div>
                                <div style="font-weight:600; color:#e2e8f0; font-size:0.9rem;">{title}</div>
                                <div style="color:#64748b; font-size:0.8rem; margin-top:3px;">{authors}</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
