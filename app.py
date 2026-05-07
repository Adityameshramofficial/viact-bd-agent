import sys
import os
import base64
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "tools"))

import streamlit as st
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from get_real_contacts_free import find_real_people
from research_company import fetch_company_news

# ── Function to load local image as base64 ─────────────────────────────────────
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return ""

# Path to your local logo file
LOGO_PATH = ROOT / "viactlogo.png"
logo_base64 = get_base64_of_bin_file(LOGO_PATH)

# Fallback transparent icon if local image is missing
PAGE_ICON = "🏗️" 

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="viAct - BD Intelligence Agent",
    page_icon=PAGE_ICON,
    layout="centered",
)

# ── viAct Premium SaaS UI (Advanced CSS Injection) ─────────────────────────────
st.markdown("""
<style>
/* 1. Import Premium Fonts */
@import url('https://fonts.googleapis.com/css2?family=Jost:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Jost', sans-serif !important;
}

/* Hide Streamlit Default Branding (Header & Footer) */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* 2. Sleek Input Fields (Dark Glass Effect) */
div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > div {
    background-color: #12151c !important;
    border: 1px solid #2d303a !important;
    border-radius: 12px !important;
    padding: 2px !important;
    transition: all 0.3s ease-in-out !important;
}
div[data-baseweb="input"] > div:focus-within, div[data-baseweb="textarea"] > div:focus-within {
    border-color: #ff6a3d !important;
    box-shadow: 0 0 15px rgba(255, 106, 61, 0.25) !important;
    transform: scale(1.01);
}

/* 3. Gradient SaaS Button (3D Hover Effect) */
button[kind="primary"] {
    background: linear-gradient(135deg, #ff6a3d 0%, #e54d1f 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 1.1rem !important;
    letter-spacing: 0.5px !important;
    padding: 1rem !important;
    box-shadow: 0 4px 15px rgba(255, 106, 61, 0.3) !important;
    transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
}
button[kind="primary"]:hover {
    transform: translateY(-4px) !important;
    box-shadow: 0 10px 25px rgba(255, 106, 61, 0.5) !important;
}
button[kind="primary"]:active {
    transform: translateY(0px) !important;
}

/* 4. Beautiful Expanders (Results Cards) */
[data-testid="stExpander"] {
    background-color: #12151c !important;
    border: 1px solid #2d303a !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important;
}
[data-testid="stExpander"] summary {
    font-weight: 500 !important;
    color: #e2e8f0 !important;
}

/* 5. Custom Title Gradient & Logo alignment */
.saas-title {
    display: flex;
    align-items: center;
    font-size: 3rem;
    font-weight: 700;
    margin-bottom: 0px;
    padding-bottom: 0px;
    letter-spacing: -1px;
    line-height: 1.2;
}
.saas-logo {
    height: 55px; /* Adjusting for the horizontal logo */
    width: auto;
    margin-right: 15px;
    margin-bottom: 5px;
}
.saas-title-text span {
    background: -webkit-linear-gradient(45deg, #ff6a3d, #ffb088);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.saas-subtitle {
    color: #8b949e;
    font-size: 1.1rem;
    font-weight: 400;
    margin-top: 10px;
    margin-bottom: 30px;
}
</style>
""", unsafe_allow_html=True)

# ── Header (Custom Branded SaaS Style) ─────────────────────────────────────────
if logo_base64:
    logo_html = f"<img src='data:image/png;base64,{logo_base64}' class='saas-logo'>"
else:
    logo_html = "🏗️ viAct"

st.markdown(f"""
<div class='saas-title'>
    {logo_html}
    <span class='saas-title-text'><span>BD Intelligence Agent </span></span>
</div>
<div class='saas-subtitle'>Autonomous B2B Research & Personalized Outreach. Powered by Real-Time Web Data.</div>
""", unsafe_allow_html=True)

# ── Inputs ─────────────────────────────────────────────────────────────────────
company_name = st.text_input(
    "🎯 Target Company Name",
    placeholder="e.g. Larsen and Toubro, Tata Projects, ADNOC",
)

custom_instructions = st.text_area(
    "✨ Custom Instructions (Optional)",
    placeholder="e.g. 'Focus on UAE operations', 'Make the email casual', 'Emphasise ISO compliance'",
    height=90,
)

st.write("") # Extra space
run = st.button("🚀 Generate Intelligence Brief", type="primary", use_container_width=True)

# ── LLM helper ─────────────────────────────────────────────────────────────────
def call_llm(company: str, news: str, contacts_text: str, instructions: str) -> str:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return "_⚠️ GROQ_API_KEY not set in .env — add your free key from console.groq.com_"

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
    except ImportError:
        return "_⚠️ `groq` package not installed. Run: `pip install groq`_"

    prompt = f"""You are a Business Development analyst at viact.ai — an AI-powered construction site safety and productivity monitoring company.

TARGET COMPANY: {company}

LIVE NEWS ABOUT THE COMPANY:
{news if news.strip() else "No recent news found."}

REAL EMPLOYEE CONTACTS FOUND ON LINKEDIN:
{contacts_text if contacts_text.strip() else "No contacts found via search."}

CUSTOM INSTRUCTIONS FROM THE BD TEAM: {instructions if instructions.strip() else "None."}

YOUR TASK — produce two sections in clean Markdown:

## 📋 Strategic Research Brief

Write a concise BD brief with:
- **Company Snapshot** (1–2 sentences on size, industry, key projects)
- **3 Safety / Productivity Triggers** — specific reasons viact.ai is relevant RIGHT NOW, tied directly to the news above. Each trigger should name the pain point and the viact.ai feature that solves it.
- **Target Contacts** — a Markdown table of the real people found. Columns: Name | Role | Target Reason

## ✉️ Ready-to-Send Outreach

Write a cold outreach email:
- **From:** aditya.meshram@viact.ai
- **To:** [use the most relevant contact from the list, or "HSE/Digital Leader" if none found]
- **Subject:** (tie it to the strongest news trigger)
- **Body:** 3 sentences max — open with the news trigger, connect to viact.ai's capability, close with a clear CTA (20-min call).
- Sign off as: Aditya Meshram | viAct.ai

Keep the tone professional and specific. No filler sentences."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1500,
    )
    return response.choices[0].message.content


# ── Main logic ─────────────────────────────────────────────────────────────────
if run:
    if not company_name.strip():
        st.error("⚠️ Please enter a target company name to begin.")
        st.stop()

    with st.spinner("🔄 Step 1/3 — Extracting live market signals..."):
        news_raw = fetch_company_news(company_name)

    with st.spinner("👥 Step 2/3 — Identifying key decision-makers on LinkedIn..."):
        contacts_raw = find_real_people(company_name)

    # Format contacts for the LLM prompt
    if isinstance(contacts_raw, list) and contacts_raw:
        contacts_text = "\n".join(
            f"- {c['Name & Role']}  →  {c['Link']}" for c in contacts_raw
        )
    elif isinstance(contacts_raw, str):
        contacts_text = contacts_raw
    else:
        contacts_text = "No contacts returned."

    with st.spinner("🧠 Step 3/3 — AI synthesizing strategy & drafting email..."):
        result_md = call_llm(company_name, news_raw, contacts_text, custom_instructions)

    st.markdown("<br><hr style='border: 1px solid #2d303a;'>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='color: #ff6a3d;'>📊 Actionable Insights: {company_name}</h3>", unsafe_allow_html=True)

    # Raw data expanders 
    with st.expander("📡 View Raw Market Signals"):
        st.text(news_raw)

    with st.expander("👔 View Extracted Contacts"):
        st.text(contacts_text)

    st.write("")

    # Main output
    st.markdown(result_md)

    st.write("")
    # Download button
    st.download_button(
        label="📥 Export Brief (Markdown)",
        data=result_md,
        file_name=f"viact_strategy_{company_name.replace(' ', '_')}.md",
        mime="text/markdown",
        type="primary"
    )