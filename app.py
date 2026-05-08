import re
import sys
import os
import base64
import csv
import io
import json
from datetime import datetime
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go


ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "tools"))

import streamlit as st
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

# On Streamlit Cloud there is no .env — pull secrets into os.environ so
# all tools that call os.getenv() work without any changes.
for _k in ["GROQ_API_KEY", "NEWS_API_KEY", "MY_EMAIL"]:
    if not os.getenv(_k):
        try:
            os.environ[_k] = st.secrets.get(_k, "")
        except Exception:
            pass

from get_real_contacts_free import find_real_people
from research_company import fetch_company_news, fetch_active_projects
from hiring_intent import check_hiring_intent

# ── Image Loader ───────────────────────────────────────────────────────────────
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""

LOGO_PATH = ROOT / "viactlogo.png"
logo_base64 = get_base64_of_bin_file(LOGO_PATH)

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="viAct Intelligence",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Jost:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Jost', sans-serif !important; }
#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}

.stApp { background-color: #080a0f; }
[data-testid="stSidebar"] { background-color: #0d1117 !important; border-right: 1px solid #1f2430; }

div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div {
    background-color: rgba(18,21,28,0.8) !important;
    border: 1px solid #2d303a !important;
    border-radius: 8px !important;
}
div[data-baseweb="input"] > div:focus-within {
    border-color: #ff6a3d !important;
    box-shadow: 0 0 12px rgba(255,106,61,0.4) !important;
}
button[kind="primary"] {
    background: linear-gradient(135deg,#ff6a3d 0%,#e54d1f 100%) !important;
    color: white !important; border: none !important;
    border-radius: 8px !important; font-weight: 600 !important;
    font-size: 1.1rem !important; transition: all 0.3s ease !important;
}
.glass-card {
    background: rgba(22,25,33,0.7); backdrop-filter: blur(15px);
    border: 1px solid rgba(255,106,61,0.15); border-radius: 12px;
    padding: 25px; position: relative; overflow: hidden;
    box-shadow: 0 8px 32px rgba(0,0,0,0.2); transition: all 0.3s ease;
}
.metric-title { color: #8b949e; font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px; }
.metric-value { color: #ff6a3d; font-size: 2.8rem; font-weight: 700; line-height: 1.1; margin-bottom: 8px; }

div[data-baseweb="tab-list"] { gap: 10px; margin-bottom: 20px; }
div[data-baseweb="tab"] {
    background-color: rgba(22,25,33,0.8); border-radius: 6px; padding: 10px 20px;
    border: 1px solid #2d303a; color: #8b949e; font-weight: 600; font-size: 1.05rem;
}
div[aria-selected="true"] {
    background-color: #ff6a3d !important; color: white !important;
    border-color: #ff6a3d !important; box-shadow: 0 4px 15px rgba(255,106,61,0.4);
}
.sim-badge { background: #ff4b4b; color: white; padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; display: inline-block; margin-bottom: 10px; }
.tier-badge { background: #7c4dff; color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; margin-left: 8px; }
.intent-high { background: #00c273; color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; }
.intent-mid  { background: #ffaa00; color: black; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; }
.intent-low  { background: #2d303a; color: #8b949e; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; }
.chat-user { background: #1e2330; border: 1px solid #2d303a; border-radius: 8px; padding: 12px; margin-bottom: 10px; }
.chat-prospect { background: #12151c; border: 2px solid #ff6a3d; border-radius: 8px; padding: 12px; margin-bottom: 10px; }

</style>
""", unsafe_allow_html=True)

# ── Session State ──────────────────────────────────────────────────────────────
for key, default in [
    ('ai_data', None), ('company_name', ""), ('roleplay_history', []),
    ('is_analyzing', False), ('live_contacts', []),
    ('enrichment_tier', 1), ('hiring_data', {}), ('projects_raw', ""),
    ('roleplay_persona', 'hse_director'), ('pitch_score', None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    if logo_base64:
        st.markdown(
            f"<div style='text-align:center;margin-bottom:20px;'>"
            f"<img src='data:image/png;base64,{logo_base64}' width='150'></div>",
            unsafe_allow_html=True,
        )
    st.markdown("<h3 style='color:white;margin-bottom:20px;'>Command Center</h3>", unsafe_allow_html=True)
    target_comp = st.text_input("🎯 Target Company", placeholder="e.g. L&T, Saudi Aramco", value=st.session_state.company_name)
    custom_instructions = st.text_area("✨ Strategy Focus", placeholder="e.g. Focus on PPE detection", height=100)
    run = st.button("🚀 Execute Analysis", type="primary", use_container_width=True)

# ── Personas ───────────────────────────────────────────────────────────────────
PERSONAS = {
    "hse_director": {
        "title": "HSE Director", "icon": "🦺", "color": "#ff6a3d",
        "concerns": "safety compliance, ISO 45001/OSHA regulations, incident rates, near-miss reporting, worker protection, justifying safety investments to management",
    },
    "it_head": {
        "title": "IT / Digital Head", "icon": "💻", "color": "#4da6ff",
        "concerns": "system integration complexity, data security and sovereignty, bandwidth requirements, API documentation, cloud vs on-premise, IT team bandwidth for implementation",
    },
    "cfo": {
        "title": "CFO", "icon": "💰", "color": "#00c273",
        "concerns": "ROI proof, total cost of ownership, payback period, capex vs opex model, competing budget priorities, cost per incident prevented",
    },
    "ceo": {
        "title": "CEO / Managing Director", "icon": "👔", "color": "#a855f7",
        "concerns": "regulatory fines and reputational risk, competitive advantage, scalability across sites, reference customers in the same industry, vendor lock-in",
    },
}

# ── LLM ────────────────────────────────────────────────────────────────────────
def _groq_client():
    from groq import Groq
    return Groq(api_key=os.getenv("GROQ_API_KEY", ""))


def roleplay_reply(company: str, user_pitch: str, company_context: str, persona_key: str) -> dict:
    persona = PERSONAS.get(persona_key, PERSONAS["hse_director"])
    client = _groq_client()
    prompt = f"""You are the {persona['title']} at {company}.
Your core concerns: {persona['concerns']}

Company context (use to make your objection specific, not generic):
{company_context}

A viAct.ai sales rep just said: "{user_pitch}"

Reply in JSON with exactly these two fields:
{{
  "objection": "Your tough, specific objection as the {persona['title']}. Must reference {company}'s actual situation. 2 sentences max. Be direct and skeptical.",
  "coaching_tip": "One sharp, actionable tip for the sales rep on exactly how to counter THIS objection. Start with 'Try:'. 1 sentence."
}}"""
    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.75,
    )
    data = json.loads(res.choices[0].message.content)
    return {
        "objection": data.get("objection", ""),
        "coaching_tip": data.get("coaching_tip", ""),
    }


def pitch_analysis(company: str, history: list, persona_key: str) -> dict:
    persona = PERSONAS.get(persona_key, PERSONAS["hse_director"])
    client = _groq_client()
    convo = "\n".join(
        f"{'Sales Rep' if m['role'] == 'user' else persona['title']}: {m['content']}"
        for m in history
    )
    prompt = f"""Analyze this B2B sales roleplay. The sales rep was pitching viAct.ai (AI safety platform) to the {persona['title']} at {company}.

CONVERSATION:
{convo}

Score the sales rep and return JSON:
{{
  "overall_score": <integer 1-10>,
  "opening_hook": <integer 1-10>,
  "objection_handling": <integer 1-10>,
  "product_knowledge": <integer 1-10>,
  "closing_attempt": <integer 1-10>,
  "best_moment": "The strongest thing the rep said",
  "biggest_gap": "The most critical missed opportunity",
  "next_time": "One specific thing to do differently next call"
}}"""
    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return json.loads(res.choices[0].message.content)


def call_llm_json(company: str, news: str, contacts_text: str, projects: str,
                  instructions: str, hiring_summary: str) -> dict:
    client = _groq_client()
    prompt = f"""You are viAct.ai's Lead BD Strategist. Analyze the TARGET company and return a JSON intelligence brief.

TARGET COMPANY: {company}
STRATEGY FOCUS: {instructions or "General safety AI opportunity"}

REAL NEWS DATA (use this — do not invent events):
{news}

REAL ACTIVE PROJECTS (use this — do not invent projects):
{projects}

CONFIRMED CONTACTS (these are real LinkedIn profiles — reference them in outreach):
{contacts_text}

HIRING SIGNALS: {hiring_summary}

RULES:
- Base sales_triggers ONLY on the real news provided above
- Base active_job_sites ONLY on the real projects provided above
- In outreach, address the first person from the CONFIRMED CONTACTS list by name
- Do NOT invent names, events, or projects not in the data above
- If data is thin, say so briefly rather than fabricating

Return ONLY valid JSON:
{{
  "company_overview": {{
    "snapshot": "2-sentence factual summary based on news",
    "risk_level": "Low|Medium|High"
  }},
  "lead_scoring": {{
    "total_score": 8,
    "justification": "specific reason referencing news/projects",
    "analytics_breakdown": {{"Safety": 9, "Tech": 7, "Finance": 8, "Urgency": 6}},
    "tech_stack_probability": {{"CCTV": 40, "Manual": 60}},
    "safety_tech_investment_5yr_trend": [20, 40, 60, 80, 90]
  }},
  "active_job_sites": [
    {{"project_name": "Real project from data above", "status": "Active", "viact_use_case": "Specific AI module"}}
  ],
  "commercial_strategy": {{
    "recommended_plan": "Enterprise|Pro|Starter",
    "competitor_angle": "specific differentiation point"
  }},
  "sales_triggers": [
    {{"trigger": "Real event from news above", "viact_solution": "Specific AI solution"}}
  ],
  "outreach": {{
    "target_person": "Full name from CONFIRMED CONTACTS — do not invent",
    "target_first_name": "First name only from CONFIRMED CONTACTS",
    "target_role": "Their role/title from CONFIRMED CONTACTS",
    "email_subject": "Compelling subject line (max 60 chars) referencing a specific real trigger — no generic phrases like 'Partnership Opportunity'",
    "email_body": "Write a complete professional B2B cold email (120-160 words). Use this exact structure:\n\nDear [First Name],\n\n[Hook paragraph — 1 sentence referencing a specific real news event or project about {company}. Show you did your homework.]\n\n[Problem paragraph — 1-2 sentences on the safety/efficiency challenge that news event represents for their operations.]\n\n[Solution paragraph — 2 sentences on how viAct.ai's AI safety platform addresses this specifically. Mention a concrete module: PPE detection, crane AI, confined space monitoring, etc. Include a realistic outcome metric.]\n\n[Social proof — 1 sentence mentioning viAct works with leading construction/O&G firms across Asia and the Middle East.]\n\nWould you be open to a 15-minute discovery call next week to see if there is a fit?\n\nBest regards,\nAditya Meshram\nBusiness Development, viAct.ai\n{os.getenv('MY_EMAIL', 'aditya.meshram@viact.ai')}",
    "linkedin_note": "Write a professional LinkedIn connection note (max 280 chars). Structure: 'Hi [First Name], [one specific hook about {company} from real news — show you know their work]. At viAct.ai we help [their industry] teams [specific safety/efficiency outcome using AI]. Would love to connect.' No filler phrases like 'I came across your profile'."
  }}
}}"""
    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return json.loads(res.choices[0].message.content)


# ── CRM Export ─────────────────────────────────────────────────────────────────
def build_crm_export(ai_data: dict, contacts: list, company: str, hiring_data: dict) -> dict:
    outreach = ai_data.get("outreach", {})
    triggers = " | ".join(t.get("trigger", "") for t in ai_data.get("sales_triggers", []))
    return {
        "company": company,
        "lead_score": ai_data["lead_scoring"]["total_score"],
        "risk_level": ai_data["company_overview"]["risk_level"],
        "snapshot": ai_data["company_overview"]["snapshot"],
        "recommended_plan": ai_data["commercial_strategy"]["recommended_plan"],
        "top_contact": outreach.get("target_person", ""),
        "email_subject": outreach.get("email_subject", ""),
        "email_body": outreach.get("email_body", ""),
        "linkedin_note": outreach.get("linkedin_note", ""),
        "sales_triggers": triggers,
        "hiring_intent_score": hiring_data.get("intent_score", 0),
        "contacts_found": len(contacts),
        "export_timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

# ── Main Execution ─────────────────────────────────────────────────────────────
if run:
    if not target_comp:
        st.sidebar.error("Enter a company name.")
        st.stop()

    st.session_state.company_name = target_comp
    st.session_state.roleplay_history = []
    st.session_state.is_analyzing = True

    with st.spinner(f"Running deep intelligence scan on {target_comp}..."):
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        with col_p1: news_status = st.empty()
        with col_p2: contacts_status = st.empty()
        with col_p3: projects_status = st.empty()
        with col_p4: hiring_status = st.empty()

        news_status.info("📰 Fetching news...")
        news_raw = fetch_company_news(target_comp)
        news_status.success("📰 News ready")

        contacts_status.info("👤 Finding contacts...")
        contacts_result = find_real_people(target_comp)
        contacts_list = contacts_result.get("contacts", [])
        tier = contacts_result.get("enrichment_tier", 1)
        contacts_status.success(f"👤 {len(contacts_list)} contacts (tier {tier})")

        projects_status.info("🏗️ Scanning projects...")
        projects_raw = fetch_active_projects(target_comp)
        projects_status.success("🏗️ Projects ready")

        hiring_status.info("💼 Checking hiring...")
        hiring_data = check_hiring_intent(target_comp)
        hiring_status.success(f"💼 Intent: {hiring_data.get('intent_score', 0)}/3")

        hiring_summary = (
            f"Safety roles found: {len(hiring_data.get('safety_roles', []))}. "
            f"Tech/digital roles found: {len(hiring_data.get('tech_roles', []))}. "
            f"Overall hiring intent score: {hiring_data.get('intent_score', 0)}/3."
        )

        contacts_for_llm = [
            {"name": c.get("Name", ""), "role": c.get("Name & Role", ""), "tier": c.get("tier", "manager")}
            for c in contacts_list
        ]

        ai_data = call_llm_json(
            target_comp, news_raw, json.dumps(contacts_for_llm, indent=2),
            projects_raw, custom_instructions, hiring_summary,
        )

        st.session_state.live_contacts = contacts_list
        st.session_state.enrichment_tier = tier
        st.session_state.hiring_data = hiring_data
        st.session_state.projects_raw = projects_raw
        st.session_state.ai_data = ai_data
        st.session_state.is_analyzing = False

# ── Dashboard ──────────────────────────────────────────────────────────────────
if st.session_state.ai_data:
    ai_data     = st.session_state.ai_data
    company     = st.session_state.company_name
    hiring_data = st.session_state.hiring_data
    tier        = st.session_state.enrichment_tier
    contacts    = st.session_state.live_contacts

    # Header metrics
    st.markdown(f"<h2 style='color:white;'>Executive Brief: {company}</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        st.markdown(
            f'<div class="glass-card"><div class="metric-title">🎯 ICP Fit</div>'
            f'<div class="metric-value">{ai_data["lead_scoring"]["total_score"]}</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="glass-card"><div class="metric-title">⚠️ Risk</div>'
            f'<div class="metric-value">{ai_data["company_overview"]["risk_level"]}</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="glass-card"><div class="metric-title">🏢 Company Snapshot</div>'
            f'<p style="color:#c9d1d9;margin-top:8px;">{ai_data["company_overview"]["snapshot"]}</p></div>',
            unsafe_allow_html=True,
        )

    t1, t2, t3 = st.tabs(["🚀 Strategy", "🤖 AI Coach", "✉️ Exec Outreach"])

    # ── Strategy Tab ────────────────────────────────────────────────────────────
    with t1:
        st.markdown("<br>", unsafe_allow_html=True)

        # Hiring intent banner
        intent_score = hiring_data.get("intent_score", 0)
        intent_map = {
            0: ("🔕 No Hiring Signals Detected", "intent-low"),
            1: ("🟡 Actively Hiring: Safety / HSE Roles", "intent-mid"),
            2: ("🔵 Actively Hiring: Tech / Digital Roles", "intent-mid"),
            3: ("🟢 High Intent — Hiring Both Safety & Tech", "intent-high"),
        }
        label_text, badge_cls = intent_map.get(intent_score, intent_map[0])
        st.markdown(
            f'<div style="margin-bottom:20px;">'
            f'<span class="{badge_cls}">HIRING SIGNALS</span>'
            f'<span style="color:white;margin-left:10px;">{label_text}</span></div>',
            unsafe_allow_html=True,
        )

        col_s1, col_s2, col_s3 = st.columns([1.2, 1.2, 1])
        with col_s1:
            st.markdown('<div class="glass-card"><div class="metric-title">🔥 Deal Triggers (from real news)</div>', unsafe_allow_html=True)
            triggers = ai_data.get('sales_triggers', [])
            if triggers:
                for t in triggers:
                    st.markdown(f"✅ **{t['trigger']}**")
                    st.markdown(f"<span style='color:#8b949e;font-size:0.85rem;'>↳ {t['viact_solution']}</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span style='color:#8b949e;'>No triggers extracted from available news.</span>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col_s2:
            st.markdown('<div class="glass-card"><div class="metric-title">🏗️ Active Projects (real web data)</div>', unsafe_allow_html=True)
            sites = ai_data.get('active_job_sites', [])
            if sites:
                for s in sites:
                    st.markdown(f"🏢 **{s['project_name']}**")
                    st.markdown(f"<span style='color:#8b949e;font-size:0.85rem;'>Status: {s.get('status','—')} · {s.get('viact_use_case','')}</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span style='color:#8b949e;'>No project data found for this company.</span>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col_s3:
            st.markdown('<div class="glass-card"><div class="metric-title">💼 Deal Recommendation</div>', unsafe_allow_html=True)
            strategy = ai_data.get('commercial_strategy', {})
            st.markdown(f"<div style='color:#ff6a3d;font-size:1.3rem;font-weight:700;'>{strategy.get('recommended_plan','—')}</div>", unsafe_allow_html=True)
            st.markdown(f"<p style='color:#8b949e;font-size:0.85rem;margin-top:8px;'>{strategy.get('competitor_angle','')}</p>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Raw project data source (expandable)
        with st.expander("🔎 Raw project search data (source verification)"):
            st.text(st.session_state.projects_raw)

        # Hiring roles detail
        if intent_score > 0:
            with st.expander("📋 Hiring Role Details"):
                hc1, hc2 = st.columns(2)
                with hc1:
                    st.markdown("**Safety / HSE Roles Found**")
                    for r in hiring_data.get("safety_roles", []):
                        st.markdown(f"- [{r['title']}]({r['url']})")
                with hc2:
                    st.markdown("**Tech / Digital Roles Found**")
                    for r in hiring_data.get("tech_roles", []):
                        st.markdown(f"- [{r['title']}]({r['url']})")

    # ── AI Coach Tab ─────────────────────────────────────────────────────────────
    with t2:
        st.markdown("<br>", unsafe_allow_html=True)

        # ── Persona selector ────────────────────────────────────────────────────
        st.markdown("<div style='color:#8b949e;font-size:0.8rem;font-weight:700;text-transform:uppercase;letter-spacing:1.2px;margin-bottom:12px;'>Choose Your Prospect</div>", unsafe_allow_html=True)
        persona_cols = st.columns(4)
        for idx, (pkey, pdata) in enumerate(PERSONAS.items()):
            with persona_cols[idx]:
                if st.button(f"{pdata['icon']} {pdata['title']}", key=f"persona_{pkey}", use_container_width=True):
                    if st.session_state.roleplay_persona != pkey:
                        st.session_state.roleplay_persona = pkey
                        st.session_state.roleplay_history = []
                        st.session_state.pitch_score = None
                        st.rerun()
                is_sel = st.session_state.roleplay_persona == pkey
                border = f"2px solid {pdata['color']}" if is_sel else "1px solid #2d303a"
                bg = f"{pdata['color']}18" if is_sel else "#12151c"
                st.markdown(f"""<div style="background:{bg};border:{border};border-radius:6px;padding:7px 10px;margin-top:-8px;font-size:0.73rem;color:#8b949e;min-height:42px;">{pdata['concerns'][:68]}…</div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Active persona + stage indicator
        persona = PERSONAS[st.session_state.roleplay_persona]
        n_exchanges = len([m for m in st.session_state.roleplay_history if m["role"] == "user"])
        stage_map = {0: ("Opening", "#8b949e"), 1: ("Discovery", "#4da6ff"), 2: ("Objection Handling", "#ffaa00"), 3: ("Objection Handling", "#ffaa00"), 4: ("Moving to Close", "#00c273")}
        stage_label, stage_color = stage_map.get(n_exchanges, ("Closing", "#00c273"))

        st.markdown(f"""
        <div style="display:flex;align-items:center;justify-content:space-between;background:#0d1117;border:1px solid #1f2430;border-radius:10px;padding:14px 20px;margin-bottom:22px;">
            <div style="display:flex;align-items:center;gap:12px;">
                <div style="width:42px;height:42px;border-radius:50%;background:{persona['color']}22;border:2px solid {persona['color']};display:flex;align-items:center;justify-content:center;font-size:1.3rem;">{persona['icon']}</div>
                <div>
                    <div style="color:white;font-weight:700;font-size:0.95rem;">{persona['title']} @ {company}</div>
                    <div style="color:#8b949e;font-size:0.78rem;">Focus: {persona['concerns'][:80]}…</div>
                </div>
            </div>
            <div style="text-align:right;">
                <div style="color:#8b949e;font-size:0.72rem;text-transform:uppercase;letter-spacing:1px;">Stage</div>
                <div style="color:{stage_color};font-weight:700;font-size:0.9rem;">{stage_label}</div>
                <div style="color:#8b949e;font-size:0.72rem;">{n_exchanges} exchange{'s' if n_exchanges != 1 else ''}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Build company context
        triggers_list = [t.get('trigger', '') for t in ai_data.get('sales_triggers', [])[:3]]
        company_context = (
            f"Overview: {ai_data['company_overview']['snapshot']}\n"
            f"Risk profile: {ai_data['company_overview']['risk_level']}\n"
            f"Recent news/events: {'; '.join(triggers_list) if triggers_list else 'N/A'}\n"
            f"Hiring intent: {hiring_data.get('intent_score', 0)}/3\n"
            f"Active projects: {', '.join(s.get('project_name','') for s in ai_data.get('active_job_sites',[])[:2]) or 'Not identified'}"
        )

        # ── Render chat history ──────────────────────────────────────────────────
        for msg in st.session_state.roleplay_history:
            if msg["role"] == "user":
                st.markdown(f"""
                <div style="display:flex;justify-content:flex-end;margin-bottom:12px;">
                    <div style="max-width:75%;background:#1e3a5f;border:1px solid #2d5a8e;border-radius:12px 12px 2px 12px;padding:12px 16px;">
                        <div style="color:#8bbfd4;font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">You — BD Rep</div>
                        <div style="color:white;font-size:0.92rem;line-height:1.5;">{msg["content"]}</div>
                    </div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:4px;">
                    <div style="width:36px;height:36px;min-width:36px;border-radius:50%;background:{persona['color']}22;border:2px solid {persona['color']};display:flex;align-items:center;justify-content:center;font-size:1rem;margin-top:2px;">{persona['icon']}</div>
                    <div style="max-width:75%;background:#12151c;border:1px solid {persona['color']}44;border-radius:2px 12px 12px 12px;padding:12px 16px;">
                        <div style="color:{persona['color']};font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">{persona['title']} @ {company}</div>
                        <div style="color:white;font-size:0.92rem;line-height:1.5;">{msg["content"]}</div>
                    </div>
                </div>""", unsafe_allow_html=True)
                if msg.get("coaching_tip"):
                    st.markdown(f"""
                    <div style="margin-left:46px;margin-bottom:16px;">
                        <div style="background:#0d1f17;border-left:3px solid #00c273;border-radius:6px;padding:8px 14px;display:inline-block;max-width:72%;">
                            <span style="color:#00c273;font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;">🎯 Coach Tip</span>
                            <div style="color:#c9d1d9;font-size:0.85rem;margin-top:4px;">{msg["coaching_tip"]}</div>
                        </div>
                    </div>""", unsafe_allow_html=True)

        # ── Input ────────────────────────────────────────────────────────────────
        user_pitch = st.chat_input(f"Pitch to the {persona['title']}...")
        if user_pitch:
            st.session_state.roleplay_history.append({"role": "user", "content": user_pitch})
            st.session_state.pitch_score = None
            with st.spinner(f"{persona['title']} is thinking..."):
                result = roleplay_reply(company, user_pitch, company_context, st.session_state.roleplay_persona)
            st.session_state.roleplay_history.append({
                "role": "assistant",
                "content": result["objection"],
                "coaching_tip": result["coaching_tip"],
            })
            st.rerun()

        # ── Bottom action bar ────────────────────────────────────────────────────
        if st.session_state.roleplay_history:
            bot_c1, bot_c2 = st.columns([1, 1])
            with bot_c1:
                if st.button("📊 Get Pitch Score", key="analyze_pitch", use_container_width=True):
                    with st.spinner("Analyzing your pitch..."):
                        st.session_state.pitch_score = pitch_analysis(
                            company, st.session_state.roleplay_history, st.session_state.roleplay_persona
                        )
                    st.rerun()
            with bot_c2:
                if st.button("🔄 Reset", key="reset_coach", use_container_width=True):
                    st.session_state.roleplay_history = []
                    st.session_state.pitch_score = None
                    st.rerun()

        # ── Pitch Score Card ─────────────────────────────────────────────────────
        if st.session_state.pitch_score:
            ps = st.session_state.pitch_score
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<div style='color:#8b949e;font-size:0.8rem;font-weight:700;text-transform:uppercase;letter-spacing:1.2px;margin-bottom:16px;'>📊 Pitch Analysis</div>", unsafe_allow_html=True)
            sc1, sc2, sc3, sc4, sc5 = st.columns(5)
            for col, label, key in [
                (sc1, "Overall", "overall_score"),
                (sc2, "Opening", "opening_hook"),
                (sc3, "Objections", "objection_handling"),
                (sc4, "Knowledge", "product_knowledge"),
                (sc5, "Closing", "closing_attempt"),
            ]:
                val = ps.get(key, 0)
                col_color = "#00c273" if val >= 7 else ("#ffaa00" if val >= 5 else "#ff4b4b")
                with col:
                    st.markdown(f"""
                    <div style="background:#12151c;border:1px solid #1f2430;border-radius:10px;padding:14px;text-align:center;">
                        <div style="color:#8b949e;font-size:0.72rem;text-transform:uppercase;letter-spacing:1px;">{label}</div>
                        <div style="color:{col_color};font-size:1.8rem;font-weight:700;margin:4px 0;">{val}</div>
                        <div style="color:#2d303a;font-size:0.7rem;">/10</div>
                    </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            fb1, fb2, fb3 = st.columns(3)
            with fb1:
                st.markdown(f"""<div style="background:#0d1f17;border-left:3px solid #00c273;border-radius:6px;padding:14px;">
                    <div style="color:#00c273;font-size:0.75rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">✅ Best Moment</div>
                    <div style="color:#c9d1d9;font-size:0.87rem;">{ps.get('best_moment','—')}</div>
                </div>""", unsafe_allow_html=True)
            with fb2:
                st.markdown(f"""<div style="background:#1f1507;border-left:3px solid #ffaa00;border-radius:6px;padding:14px;">
                    <div style="color:#ffaa00;font-size:0.75rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">⚠️ Biggest Gap</div>
                    <div style="color:#c9d1d9;font-size:0.87rem;">{ps.get('biggest_gap','—')}</div>
                </div>""", unsafe_allow_html=True)
            with fb3:
                st.markdown(f"""<div style="background:#0d1117;border-left:3px solid #4da6ff;border-radius:6px;padding:14px;">
                    <div style="color:#4da6ff;font-size:0.75rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">🎯 Next Time</div>
                    <div style="color:#c9d1d9;font-size:0.87rem;">{ps.get('next_time','—')}</div>
                </div>""", unsafe_allow_html=True)

    # ── Exec Outreach Tab ────────────────────────────────────────────────────────
    with t3:
        st.markdown("<br>", unsafe_allow_html=True)
        outreach = ai_data.get('outreach', {})
        best_contact   = outreach.get('target_person', 'Decision Maker')
        first_name     = outreach.get('target_first_name', best_contact.split()[0] if best_contact else 'there')
        target_role    = outreach.get('target_role', '')
        email_subject  = outreach.get('email_subject', '')
        email_body     = outreach.get('email_body', '')
        linkedin_note  = outreach.get('linkedin_note', '')
        tier_label     = f'<span class="tier-badge">Tier {tier} Enrichment</span>' if tier > 1 else ''

        # Target header
        st.markdown(f"""
            <div style="background:rgba(255,106,61,0.08);border:1px solid #ff6a3d;padding:16px 20px;border-radius:10px;margin-bottom:28px;display:flex;align-items:center;gap:16px;">
                <div>
                    <div style="color:#8b949e;font-size:0.75rem;text-transform:uppercase;letter-spacing:1px;">AI Optimal Target</div>
                    <div style="color:white;font-size:1.2rem;font-weight:700;margin-top:4px;">{best_contact}</div>
                    <div style="color:#8b949e;font-size:0.85rem;">{target_role}</div>
                </div>
                <div style="margin-left:auto;display:flex;gap:8px;align-items:center;">
                    <span style="background:#00c273;color:white;padding:4px 10px;border-radius:4px;font-size:0.75rem;font-weight:700;">HIGH CONVERSION</span>
                    {tier_label}
                </div>
            </div>
        """, unsafe_allow_html=True)

        col_out1, col_out2 = st.columns([3, 1])
        with col_out1:
            ot1, ot2 = st.tabs(["📧 Cold Email", "🔗 LinkedIn Note"])

            # ── Cold Email Preview ──────────────────────────────────────────
            with ot1:
                # Editable subject
                edited_subject = st.text_input(
                    "Subject",
                    value=email_subject,
                    key="email_subject_edit",
                )

                # Email metadata bar
                st.markdown(f"""
                <div style="background:#0d1117;border:1px solid #1f2430;border-radius:8px 8px 0 0;padding:14px 18px;margin-top:6px;">
                    <div style="display:flex;gap:8px;margin-bottom:6px;">
                        <span style="color:#8b949e;font-size:0.82rem;width:36px;">From:</span>
                        <span style="color:#c9d1d9;font-size:0.82rem;">Aditya Meshram &lt;{os.getenv("MY_EMAIL", "aditya.meshram@viact.ai")}&gt;</span>
                    </div>
                    <div style="display:flex;gap:8px;margin-bottom:6px;">
                        <span style="color:#8b949e;font-size:0.82rem;width:36px;">To:</span>
                        <span style="color:#c9d1d9;font-size:0.82rem;">{best_contact} — {target_role} @ {company}</span>
                    </div>
                    <div style="display:flex;gap:8px;">
                        <span style="color:#8b949e;font-size:0.82rem;width:36px;">Sub:</span>
                        <span style="color:#ff6a3d;font-size:0.82rem;font-weight:600;">{edited_subject}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Editable email body
                edited_body = st.text_area(
                    "Email body",
                    value=email_body,
                    height=320,
                    key="email_body_edit",
                    label_visibility="collapsed",
                )

                # Word count
                word_count = len(edited_body.split()) if edited_body else 0
                wc_color = "#00c273" if 100 <= word_count <= 180 else "#ffaa00"
                st.markdown(
                    f'<div style="text-align:right;color:{wc_color};font-size:0.78rem;margin-top:4px;">'
                    f'{word_count} words {"✓ Good length" if 100 <= word_count <= 180 else "(aim for 120–160 words)"}</div>',
                    unsafe_allow_html=True,
                )

                # Tips
                with st.expander("✏️ Writing tips"):
                    st.markdown("""
**Subject line**: Specific beats clever — reference the real trigger (e.g. "Re: [Company]'s [Project Name] — AI Safety")

**Hook**: Lead with something they care about (their recent news), not with who you are.

**Body**: One problem → one solution → one outcome metric → one ask.

**CTA**: Ask for 15 minutes, not a demo. Lower barrier = higher reply rate.

**Length**: 120–160 words. Anything longer gets skimmed or deleted.
                    """)

            # ── LinkedIn Note Preview ───────────────────────────────────────
            with ot2:
                char_count = len(linkedin_note)
                bar_pct = min(int(char_count / 300 * 100), 100)
                bar_color = "#00c273" if char_count <= 280 else "#ff4b4b"

                # Simulated LinkedIn message card
                st.markdown(f"""
                <div style="background:#0d1117;border:1px solid #1f2430;border-radius:10px;padding:18px;margin-bottom:12px;">
                    <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
                        <div style="width:44px;height:44px;border-radius:50%;background:#ff6a3d;display:flex;align-items:center;justify-content:center;font-weight:700;color:white;font-size:1.1rem;">{first_name[0].upper() if first_name else 'A'}</div>
                        <div>
                            <div style="color:white;font-weight:600;font-size:0.9rem;">Aditya Meshram</div>
                            <div style="color:#8b949e;font-size:0.78rem;">BD Manager · viAct.ai</div>
                        </div>
                        <div style="margin-left:auto;background:#0077b5;color:white;padding:5px 12px;border-radius:15px;font-size:0.78rem;font-weight:600;">Connect</div>
                    </div>
                    <div style="color:#8b949e;font-size:0.75rem;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Message to {first_name}:</div>
                </div>
                """, unsafe_allow_html=True)

                edited_linkedin = st.text_area(
                    "LinkedIn note",
                    value=linkedin_note,
                    height=160,
                    key="linkedin_note_edit",
                    label_visibility="collapsed",
                )

                actual_chars = len(edited_linkedin)
                bar_pct = min(int(actual_chars / 300 * 100), 100)
                bar_color = "#00c273" if actual_chars <= 270 else ("#ffaa00" if actual_chars <= 299 else "#ff4b4b")
                st.markdown(f"""
                <div style="margin-top:8px;">
                    <div style="background:#1f2430;border-radius:4px;height:4px;overflow:hidden;">
                        <div style="background:{bar_color};width:{bar_pct}%;height:100%;transition:width 0.3s;"></div>
                    </div>
                    <div style="display:flex;justify-content:space-between;margin-top:4px;">
                        <span style="color:#8b949e;font-size:0.75rem;">Character count</span>
                        <span style="color:{bar_color};font-size:0.75rem;font-weight:600;">{actual_chars} / 300</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                with st.expander("✏️ LinkedIn tips"):
                    st.markdown("""
**Rule**: Write like you're texting a senior professional, not like a press release.

**Hook**: Reference something real about their company in sentence 1.

**Keep it under 270 chars** so it's never truncated in the notification email.

**No fluff**: Delete "I hope this message finds you well", "I came across your profile", "I'd love to pick your brain".

**End with a soft CTA**: "Would love to connect" — never "Let me know if you're interested."
                    """)

        with col_out2:
            st.markdown('<div class="glass-card"><div class="metric-title">🔍 Contacts Found</div>', unsafe_allow_html=True)
            for i, c in enumerate(contacts):
                border_col = '#ff6a3d' if i == 0 else '#2d303a'
                star = '⭐ ' if i == 0 else ''
                st.markdown(f"""
                <div style="background:#12151c;padding:12px;border-radius:8px;margin-bottom:10px;border-left:2px solid {border_col};">
                    <div style="color:white;font-weight:600;font-size:0.88rem;">{star}{c['Name & Role']}</div>
                    <a href="{c['Link']}" target="_blank" style="color:#ff6a3d;font-size:0.78rem;text-decoration:none;">↗️ LinkedIn</a>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # ── CRM Export ───────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📤 Export to CRM (HubSpot-ready)"):
        # Use edited values from outreach tab if available
        ai_data_export = dict(ai_data)
        ai_data_export['outreach'] = dict(ai_data.get('outreach', {}))
        ai_data_export['outreach']['email_subject'] = st.session_state.get('email_subject_edit', ai_data.get('outreach', {}).get('email_subject', ''))
        ai_data_export['outreach']['email_body']    = st.session_state.get('email_body_edit',    ai_data.get('outreach', {}).get('email_body', ''))
        ai_data_export['outreach']['linkedin_note'] = st.session_state.get('linkedin_note_edit', ai_data.get('outreach', {}).get('linkedin_note', ''))
        crm_record = build_crm_export(ai_data_export, contacts, company, hiring_data)
        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            st.download_button(
                label="⬇️ Download Full JSON",
                data=json.dumps({"full_intelligence": ai_data, "crm_record": crm_record}, indent=2).encode(),
                file_name=f"viact_intel_{company.replace(' ', '_')}.json",
                mime="application/json",
                use_container_width=True,
            )
        with col_ex2:
            csv_buf = io.StringIO()
            csv.DictWriter(csv_buf, fieldnames=crm_record.keys()).writeheader()
            csv.DictWriter(csv_buf, fieldnames=crm_record.keys()).writerow(crm_record)
            st.download_button(
                label="⬇️ Download CSV (HubSpot)",
                data=csv_buf.getvalue().encode(),
                file_name=f"viact_intel_{company.replace(' ', '_')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        st.json(crm_record)

elif not st.session_state.get('is_analyzing', False):
    st.markdown(
        "<h1 style='text-align:center;color:#ff6a3d;margin-top:20vh;'>viAct AI Core</h1>"
        "<p style='text-align:center;color:#8b949e;'>Enter a target company in the sidebar to begin.</p>",
        unsafe_allow_html=True,
    )
