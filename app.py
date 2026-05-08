import sys
import os
import base64
import csv
import io
import json
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go

# Safely import agraph for Power Maps
try:
    from streamlit_agraph import agraph, Node, Edge, Config
    AGRAPH_AVAILABLE = True
except ImportError:
    AGRAPH_AVAILABLE = False

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "tools"))

import streamlit as st
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from get_real_contacts_free import find_real_people
from research_company import fetch_company_news

# ── Image Loader ───────────────────────────────────────────────────────────────
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f: return base64.b64encode(f.read()).decode()
    except: return ""

LOGO_PATH = ROOT / "viactlogo.png"
logo_base64 = get_base64_of_bin_file(LOGO_PATH)

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="viAct Intelligence", page_icon="🏗️", layout="wide", initial_sidebar_state="expanded")

# ── Ultra Premium SaaS CSS (CEO Dashboard Edition) ─────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Jost:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Jost', sans-serif !important; }
#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}

/* Main Background */
.stApp { background-color: #080a0f; }
[data-testid="stSidebar"] { background-color: #0d1117 !important; border-right: 1px solid #1f2430; }

/* Inputs & Buttons */
div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > div { background-color: rgba(18, 21, 28, 0.8) !important; border: 1px solid #2d303a !important; border-radius: 8px !important; }
div[data-baseweb="input"] > div:focus-within { border-color: #ff6a3d !important; box-shadow: 0 0 12px rgba(255, 106, 61, 0.4) !important; }
button[kind="primary"] { background: linear-gradient(135deg, #ff6a3d 0%, #e54d1f 100%) !important; color: white !important; border: none !important; border-radius: 8px !important; font-weight: 600 !important; font-size: 1.1rem !important; transition: all 0.3s ease !important; }
button[kind="primary"]:hover { transform: translateY(-2px) !important; box-shadow: 0 8px 20px rgba(255, 106, 61, 0.5) !important; }

/* CEO Style Glass Cards */
.glass-card { background: rgba(22, 25, 33, 0.7); backdrop-filter: blur(15px); -webkit-backdrop-filter: blur(15px); border: 1px solid rgba(255, 106, 61, 0.15); border-radius: 12px; padding: 25px; height: 100%; position: relative; overflow: hidden; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2); transition: all 0.3s ease;}
.glass-card:hover { border-color: rgba(255, 106, 61, 0.6); box-shadow: 0 10px 30px rgba(255, 106, 61, 0.15); transform: translateY(-2px);}
.metric-title { color: #8b949e; font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px;}
.metric-value { color: #ff6a3d; font-size: 2.8rem; font-weight: 700; line-height: 1.1; margin-bottom: 8px;}
.metric-desc { color: #e2e8f0; font-size: 0.95rem; line-height: 1.5; }

/* Mission Cards (For Sites & Personas) */
.mission-card { background: #12151c; border-left: 3px solid #00c273; border-radius: 6px; padding: 15px; margin-bottom: 12px; }
.mission-card-title { font-weight: 600; color: #fff; font-size: 1.1rem; margin-bottom: 5px; }
.mission-card-tag { display: inline-block; background: rgba(0, 194, 115, 0.1); color: #00c273; padding: 3px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; margin-right: 10px;}

.target-card { background: #12151c; border-left: 3px solid #ff6a3d; border-radius: 6px; padding: 15px; margin-bottom: 12px; }
.target-role { color: #ff6a3d; font-size: 0.85rem; font-weight: 700; text-transform: uppercase; margin-bottom: 3px;}

/* Tabs */
div[data-baseweb="tab-list"] { gap: 10px; margin-bottom: 20px; }
div[data-baseweb="tab"] { background-color: rgba(22, 25, 33, 0.8); border-radius: 6px; padding: 10px 20px; border: 1px solid #2d303a; color: #8b949e; font-weight: 600; font-size: 1.05rem; }
div[data-baseweb="tab"]:hover { background-color: rgba(255, 106, 61, 0.1); color: white; border-color: #ff6a3d; }
div[aria-selected="true"] { background-color: #ff6a3d !important; color: white !important; border-color: #ff6a3d !important; box-shadow: 0 4px 15px rgba(255, 106, 61, 0.4); }

.saas-title { display: flex; align-items: center; font-size: 2.5rem; font-weight: 700; margin-bottom: 0px; line-height: 1.2; }
.saas-logo { height: 42px; margin-right: 15px; margin-bottom: 5px; }
.chart-container { background: rgba(22, 25, 33, 0.5); border: 1px solid #2d303a; border-radius: 12px; padding: 20px; }
.sim-badge { background: #ff4b4b; color: white; padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; display: inline-block; margin-bottom: 15px; animation: pulse 2s infinite; }
@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.6; } 100% { opacity: 1; } }
</style>
""", unsafe_allow_html=True)

# ── Session State ──────────────────────────────────────────────────────────────
if 'ai_data' not in st.session_state: st.session_state.ai_data = None
if 'company_name' not in st.session_state: st.session_state.company_name = ""
if 'roleplay_history' not in st.session_state: st.session_state.roleplay_history = []
if 'is_analyzing' not in st.session_state: st.session_state.is_analyzing = False

# ── Sidebar UI ─────────────────────────────────────────────────────────────────
with st.sidebar:
    if logo_base64: st.markdown(f"<div style='text-align:center; margin-bottom: 20px;'><img src='data:image/png;base64,{logo_base64}' width='150'></div>", unsafe_allow_html=True)
    st.markdown("<h3 style='color: white; margin-bottom: 20px;'>Command Center</h3>", unsafe_allow_html=True)
    target_comp = st.text_input("🎯 Target Company", placeholder="e.g. L&T, Saudi Aramco", value=st.session_state.company_name)
    custom_instructions = st.text_area("✨ Strategy Focus", placeholder="e.g. Focus on PPE detection", height=100)
    st.write("")
    run = st.button("🚀 Execute Analysis", type="primary", use_container_width=True)

# ── LLM Functions ──────────────────────────────────────────────────────────────
def roleplay_reply(company, user_pitch):
    api_key = os.getenv("GROQ_API_KEY", "")
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        prompt = f"Act as the strict HSE Director at {company}. A viAct salesperson pitched: '{user_pitch}'. Reply with a tough objection about budget or integration. 2 sentences max."
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0.8)
        return res.choices[0].message.content
    except Exception as e: return f"Error: {e}"

def call_llm_json(company, news, contacts_text, instructions):
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key: return {"error": "GROQ_API_KEY missing"}
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
    except: return {"error": "groq module missing"}

    prompt = f"""You are viAct.ai's Lead BD Strategist.
TARGET: {company}
NEWS: {news}
CONTACTS: {contacts_text}
INSTRUCTIONS: {instructions}

CRITICAL RULES: Respond ONLY in valid JSON. For "active_job_sites", ONLY list real sites from NEWS. 

JSON FORMAT:
{{
  "company_overview": {{ "snapshot": "2-sentence overview", "risk_level": "High/Medium/Low" }},
  "lead_scoring": {{
    "total_score": 8, "justification": "Why this score?",
    "analytics_breakdown": {{ "Safety_Risk": 9, "Tech_Readiness": 7, "Financial_Health": 8, "Expansion_Urgency": 6 }},
    "tech_stack_probability": {{ "Legacy_CCTV": 40, "Manual_Methods": 35, "Advanced_ERP": 25 }},
    "safety_tech_investment_5yr_trend": [20, 35, 45, 60, 85]
  }},
  "active_job_sites": [ {{"project_name": "Project Name", "status": "Ongoing", "viact_use_case": "Crane AI"}} ],
  "power_map_nodes": [
    {{"id": "CEO", "label": "CEO / Top Exec", "title": "Decision Maker"}},
    {{"id": "HSE", "label": "HSE Director", "title": "Champion", "reports_to": "CEO"}},
    {{"id": "SITE", "label": "Site Manager", "title": "End User", "reports_to": "HSE"}}
  ],
  "commercial_strategy": {{ "recommended_plan": "Enterprise", "competitor_angle": "How to beat Procore" }},
  "sales_triggers": [ {{"trigger": "News event 1", "viact_solution": "Solution 1"}} ],
  "outreach": {{ "email_subject": "Subject", "email_body": "3 lines", "linkedin_note": "300 chars" }}
}}"""
    try:
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0.7)
        return json.loads(res.choices[0].message.content.replace("```json", "").replace("```", "").strip())
    except Exception as e: return {"error": f"JSON Error: {str(e)}"}

# ── Chart Builders ─────────────────────────────────────────────────────────────
def create_radar_chart(breakdown):
    categories = [c.replace('_', ' ') for c in list(breakdown.keys())]
    values = list(breakdown.values())
    fig = go.Figure(data=go.Scatterpolar(r=values + [values[0]], theta=categories + [categories[0]], fill='toself', fillcolor='rgba(255, 106, 61, 0.4)', line=dict(color='#ff6a3d', width=2), marker=dict(color='white', size=6)))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10], color='#8b949e', gridcolor='#2d303a'), angularaxis=dict(color='white', gridcolor='#2d303a')), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=25, r=25, t=25, b=25), height=240)
    return fig
def create_donut_chart(tech_stack):
    labels = [l.replace('_', ' ') for l in list(tech_stack.keys())]
    values = list(tech_stack.values())
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.65, marker_colors=['#ff6a3d', '#ffa600', '#00c273', '#3d5afe'])])
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=10, b=10), height=240, showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5, font=dict(color="#c9d1d9", size=10)))
    return fig
def create_trend_chart(trend_data):
    years = ['Yr 1', 'Yr 2', 'Yr 3', 'Yr 4', 'Yr 5']
    fig = go.Figure(data=go.Scatter(x=years, y=trend_data, mode='lines+markers', line=dict(color='#00c273', width=3), marker=dict(size=8, color='white', line=dict(color='#00c273', width=2))))
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(color='#8b949e', gridcolor='#2d303a'), yaxis=dict(color='#8b949e', gridcolor='#2d303a', showgrid=True), margin=dict(l=25, r=20, t=20, b=25), height=240)
    return fig

# ── Main Execution ─────────────────────────────────────────────────────────────
if run:
    if not target_comp: st.sidebar.error("⚠️ Enter a company name."); st.stop()
    st.session_state.company_name = target_comp
    st.session_state.roleplay_history = [] 
    st.session_state.is_analyzing = True

if st.session_state.is_analyzing:
    with st.spinner(f"Scanning the web for {st.session_state.company_name}..."):
        news_raw = fetch_company_news(st.session_state.company_name)
        c_raw = find_real_people(st.session_state.company_name)
        c_text = "\n".join(f"- {c['Name & Role']}" for c in c_raw) if isinstance(c_raw, list) else "None"
        st.session_state.ai_data = call_llm_json(st.session_state.company_name, news_raw, c_text, custom_instructions)
        st.session_state.is_analyzing = False

# ── Dashboard UI Rendering ─────────────────────────────────────────────────────
if not st.session_state.ai_data and not st.session_state.is_analyzing:
    st.markdown("<div style='text-align: center; margin-top: 15vh;'><h1 style='color:#ff6a3d; font-size:4rem;'>viAct AI Core</h1><p style='color:#8b949e; font-size:1.2rem;'>Enter a target in the command center to generate an executive BD brief.</p></div>", unsafe_allow_html=True)
    
elif st.session_state.ai_data and "error" not in st.session_state.ai_data:
    ai_data = st.session_state.ai_data
    score = ai_data.get('lead_scoring', {}).get('total_score', 0)
    risk = ai_data.get('company_overview', {}).get('risk_level', 'Unknown')
    
    st.markdown(f"<h2>Executive Brief: <span style='color:#ffffff;'>{st.session_state.company_name}</span></h2>", unsafe_allow_html=True)
    st.write("")
    
    # Metrics Row
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1: st.markdown(f"""<div class="glass-card"><div class="metric-title">🎯 ICP Fitment</div><div class="metric-value">{score}<span style='font-size:1.4rem; color:#8b949e;'>/10</span></div><div class="metric-desc">{ai_data.get('lead_scoring', {}).get('justification', '')}</div></div>""", unsafe_allow_html=True)
    with c2: 
        r_col = "#ff4b4b" if "High" in risk else ("#ffa600" if "Medium" in risk else "#00c273")
        st.markdown(f"""<div class="glass-card"><div class="metric-title">⚠️ Operational Risk</div><div class="metric-value" style="color:{r_col};">{risk}</div><div class="metric-desc">Status: Ready for viAct</div></div>""", unsafe_allow_html=True)
    with c3: st.markdown(f"""<div class="glass-card"><div class="metric-title">🏢 Strategic Overview</div><div class="metric-desc" style="font-size:1.1rem;">{ai_data.get('company_overview', {}).get('snapshot', '')}</div></div>""", unsafe_allow_html=True)

    st.write("")
    
    # Graphs Row
    g1, g2, g3 = st.columns(3)
    with g1:
        st.markdown("<div class='chart-container'><div class='metric-title' style='text-align:center;'>Lead Readiness Radar</div>", unsafe_allow_html=True)
        st.plotly_chart(create_radar_chart(ai_data.get('lead_scoring', {}).get('analytics_breakdown', {})), use_container_width=True, config={'displayModeBar': False})
        st.markdown("</div>", unsafe_allow_html=True)
    with g2:
        st.markdown("<div class='chart-container'><div class='metric-title' style='text-align:center;'>Tech Stack Probability</div>", unsafe_allow_html=True)
        st.plotly_chart(create_donut_chart(ai_data.get('lead_scoring', {}).get('tech_stack_probability', {})), use_container_width=True, config={'displayModeBar': False})
        st.markdown("</div>", unsafe_allow_html=True)
    with g3:
        st.markdown("<div class='chart-container'><div class='metric-title' style='text-align:center;'>5-Year Investment Trend</div>", unsafe_allow_html=True)
        st.plotly_chart(create_trend_chart(ai_data.get('lead_scoring', {}).get('safety_tech_investment_5yr_trend', [])), use_container_width=True, config={'displayModeBar': False})
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border:1px solid #1f2430; margin:30px 0;'>", unsafe_allow_html=True)

    # 🚀 CEO LEVEL TABS
    t1, t2, t3, t4 = st.tabs(["🚀 Strategy & Targets", "🕸️ Power Map", "🤖 AI Sales Coach", "✉️ Exec Outreach"])

    with t1:
        # THE "ATTACK PLAN" TAB
        st.markdown("<br>", unsafe_allow_html=True)
        col_s1, col_s2, col_s3 = st.columns([1.2, 1.2, 1])
        
        with col_s1:
            st.markdown("""<div class="glass-card"><div class="metric-title">🔥 Deal Triggers (Why Now?)</div>""", unsafe_allow_html=True)
            for t in ai_data.get('sales_triggers', []):
                st.markdown(f"**Signal:** {t.get('trigger', '')} <br> <span style='color:#00c273;'>**Pitch:** 🎯 {t.get('viact_solution', '')}</span>", unsafe_allow_html=True)
                st.markdown("<hr style='border-top: 1px solid #2d303a;'>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_s2:
            st.markdown("""<div class="glass-card"><div class="metric-title">🌍 Active Deployment Sites</div>""", unsafe_allow_html=True)
            sites = ai_data.get('active_job_sites', [])
            if sites:
                for s in sites:
                    st.markdown(f"""
                    <div class="mission-card">
                        <div class="mission-card-title">🏢 {s.get('project_name', '')}</div>
                        <span class="mission-card-tag">🟢 {s.get('status', 'Active')}</span>
                        <span class="mission-card-tag" style="background:rgba(255,106,61,0.1); color:#ff6a3d;">🤖 viAct: {s.get('viact_use_case', '')}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else: st.caption("No specific active sites found in recent news.")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_s3:
            st.markdown("""<div class="glass-card" style="border-left: 3px solid #ff6a3d;"><div class="metric-title">💼 Deal Desk Strategy</div>""", unsafe_allow_html=True)
            com = ai_data.get('commercial_strategy', {})
            st.markdown(f"**📦 Recommended Tier:**<br><span style='font-size:1.2rem; color:#fff;'>{com.get('recommended_plan', '')}</span><br><br>", unsafe_allow_html=True)
            st.markdown(f"**⚔️ Competitor Takedown:**<br><span style='color:#ff4b4b;'>{com.get('competitor_angle', '')}</span>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    with t2:
        # THE "POWER MAP" TAB
        st.markdown("<br>", unsafe_allow_html=True)
        col_p1, col_p2 = st.columns([2.5, 1])
        
        with col_p1:
            st.markdown("""<div class="chart-container"><div class="metric-title">🕸️ Interactive Influence Graph</div>""", unsafe_allow_html=True)
            if AGRAPH_AVAILABLE:
                nodes, edges = [], []
                for p in ai_data.get('power_map_nodes', []):
                    color = "#00c273" if "Champion" in p['title'] else ("#ff6a3d" if "Decision" in p['title'] else "#3d5afe")
                    nodes.append(Node(id=p['id'], label=p['label'], title=p['title'], shape="dot", size=25, color=color))
                    if p.get('reports_to'): edges.append(Edge(source=p['reports_to'], target=p['id'], color="#8b949e"))
                config = Config(width="100%", height=400, directed=True, nodeHighlightBehavior=True, highlightColor="#fff", collapsible=False)
                agraph(nodes=nodes, edges=edges, config=config)
            else: st.error("⚠️ Please run `pip install streamlit-agraph`.")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_p2:
            st.markdown("""<div class="glass-card"><div class="metric-title">🎯 Who to Target</div>""", unsafe_allow_html=True)
            for p in ai_data.get('power_map_nodes', []):
                st.markdown(f"""
                <div class="target-card">
                    <div class="target-role">{p.get('title', '')}</div>
                    <div style="color:white; font-size:1.1rem; font-weight:600;">{p.get('label', '')}</div>
                    <div style="color:#8b949e; font-size:0.85rem;">Key persona for this deal.</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    with t3:
        # THE "AI SALES COACH" TAB
        st.markdown("<br>", unsafe_allow_html=True)
        c_sim1, c_sim2 = st.columns([2, 1])
        
        with c_sim1:
            st.markdown("""<div class="glass-card"><div class="sim-badge">🔴 SIMULATION ACTIVE</div><div class="metric-title">Meeting Roleplay Simulator</div>""", unsafe_allow_html=True)
            chat_container = st.container(height=300, border=False)
            with chat_container:
                for chat in st.session_state.roleplay_history:
                    with st.chat_message("user"): st.write(chat['user'])
                    with st.chat_message("assistant", avatar="👔"): st.write(chat['ai'])

            user_pitch = st.chat_input("Enter your pitch to the HSE Director...")
            if user_pitch:
                st.session_state.roleplay_history.append({"user": user_pitch, "ai": "..."})
                st.rerun() 
                
            if st.session_state.roleplay_history and st.session_state.roleplay_history[-1]["ai"] == "...":
                latest_user_msg = st.session_state.roleplay_history[-1]["user"]
                reply = roleplay_reply(st.session_state.company_name, latest_user_msg)
                st.session_state.roleplay_history[-1]["ai"] = reply
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            
        with c_sim2:
            st.markdown("""<div class="glass-card" style="border-left: 3px solid #00c273;"><div class="metric-title">📊 Coach Analysis</div>""", unsafe_allow_html=True)
            st.write("Pitching to **HSE Directors** requires:")
            st.markdown("- **High ROI focus:** Show cost savings.<br>- **Zero-friction:** Explain easy camera integration.<br>- **Compliance:** Mention safety rules.", unsafe_allow_html=True)
            st.progress(75, text="Pitch Readiness Score")
            st.markdown("</div>", unsafe_allow_html=True)

    with t4:
        st.markdown("<br>", unsafe_allow_html=True)
        outreach = ai_data.get('outreach', {})
        c_em, c_in = st.columns(2)
        with c_em:
            st.markdown("""<div class="glass-card"><div class="metric-title">📧 Executive Email Draft</div>""", unsafe_allow_html=True)
            st.text_area("Body", outreach.get('email_body', ''), height=150, label_visibility="collapsed")
            csv_b = io.StringIO(); writer = csv.writer(csv_b)
            writer.writerow(["Company", "Score", "Snapshot", "Email Body"])
            writer.writerow([st.session_state.company_name, score, ai_data.get('company_overview', {}).get('snapshot', ''), outreach.get('email_body', '')])
            st.download_button("📥 Push to CRM (CSV)", data=csv_b.getvalue(), file_name=f"{st.session_state.company_name}.csv", mime="text/csv", type="primary")
            st.markdown("</div>", unsafe_allow_html=True)

        with c_in:
            st.markdown("""<div class="glass-card"><div class="metric-title">🔗 LinkedIn Exec Draft</div>""", unsafe_allow_html=True)
            st.text_area("Note", outreach.get('linkedin_note', ''), height=150, label_visibility="collapsed")
            st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.ai_data and "error" in st.session_state.ai_data:
    st.error(st.session_state.ai_data["error"])