"""
MediAssist — AI Powered Healthcare Assistant
Home screen: navigation cards, quick stats, architecture overview, setup guide.
"""
import json, os, sys
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
from utils.logger import get_metrics_summary

st.set_page_config(
    page_title="MediAssist — AI Healthcare Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/color/96/hospital.png", width=64)
    st.title("MediAssist")
    st.caption("AI Powered Healthcare Assistant")
    st.divider()
    st.markdown("""
**Navigate:**
- 👤 [Patient View](Patient_View)
- 🩺 [Doctor View](Doctor_View)
- ⚙️ [Admin Dashboard](Admin_Dashboard)
- 🧠 [Memory & Logs](Memory_Logs)
    """)
    st.divider()
    api_ok = (config.OPENAI_API_KEY and
              config.OPENAI_API_KEY != "your_openai_api_key_here")
    if api_ok:
        st.success("🟢 LLM Mode: OpenAI Active")
    else:
        st.warning("🟡 LLM Mode: Mock (No API Key)")
    st.caption(f"Model: `{config.LLM_MODEL}`")


# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:2rem 0 1rem">
  <h1 style="font-size:3rem;margin-bottom:.25rem">🏥 MediAssist</h1>
  <p style="font-size:1.25rem;color:#6c757d">
    AI-Powered Agentic Healthcare Assistant<br>
    <em>Appointment booking · EHR access · Medical search · LLMOps analytics</em>
  </p>
</div>
""", unsafe_allow_html=True)

st.divider()

# ── Quick Stats ───────────────────────────────────────────────────────────────
try:
    with open(config.PATIENTS_FILE) as f: n_patients = len(json.load(f))
except Exception: n_patients = 0
try:
    with open(config.DOCTORS_FILE) as f:  n_doctors  = len(json.load(f))
except Exception: n_doctors = 0
try:
    with open(config.APPOINTMENTS_FILE) as f: all_appts = json.load(f)
    n_appts     = len(all_appts)
    n_confirmed = sum(1 for a in all_appts if a.get("status") == "Confirmed")
except Exception: n_appts = n_confirmed = 0

m = get_metrics_summary()

st.subheader("📊 System Overview")
c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric("👤 Patients",      n_patients)
c2.metric("🩺 Doctors",       n_doctors)
c3.metric("📅 Appointments",  n_appts)
c4.metric("✅ Confirmed",     n_confirmed)
c5.metric("🔧 Tool Calls",    m.get("total_tool_calls",0))
c6.metric("📈 Success Rate",  f"{m.get('tool_success_rate',0):.0f}%")

st.divider()

# ── Navigation Cards ──────────────────────────────────────────────────────────
st.subheader("🧭 Quick Navigation")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
<div style="border:1px solid #dee2e6;border-radius:12px;padding:1.25rem;text-align:center;
            background:linear-gradient(135deg,#e8f5e9,#f1f8e9)">
  <div style="font-size:2.5rem">👤</div>
  <h3 style="margin:.5rem 0">Patient View</h3>
  <p style="color:#555;font-size:.9rem">View medical history, chat with AI assistant, book appointments, upload medical records with OCR</p>
</div>
""", unsafe_allow_html=True)
    st.page_link("pages/1_Patient_View.py", label="Open Patient View →", use_container_width=True)

with col2:
    st.markdown("""
<div style="border:1px solid #dee2e6;border-radius:12px;padding:1.25rem;text-align:center;
            background:linear-gradient(135deg,#e3f2fd,#e8eaf6)">
  <div style="font-size:2.5rem">🩺</div>
  <h3 style="margin:.5rem 0">Doctor View</h3>
  <p style="color:#555;font-size:.9rem">Manage schedule, look up patients, check slot availability and utilisation</p>
</div>
""", unsafe_allow_html=True)
    st.page_link("pages/2_Doctor_View.py", label="Open Doctor View →", use_container_width=True)

with col3:
    st.markdown("""
<div style="border:1px solid #dee2e6;border-radius:12px;padding:1.25rem;text-align:center;
            background:linear-gradient(135deg,#fff3e0,#fce4ec)">
  <div style="font-size:2.5rem">⚙️</div>
  <h3 style="margin:.5rem 0">Admin Dashboard</h3>
  <p style="color:#555;font-size:.9rem">Tool analytics, model evaluation, debug failures, system controls</p>
</div>
""", unsafe_allow_html=True)
    st.page_link("pages/3_Admin_Dashboard.py", label="Open Admin Dashboard →", use_container_width=True)

with col4:
    st.markdown("""
<div style="border:1px solid #dee2e6;border-radius:12px;padding:1.25rem;text-align:center;
            background:linear-gradient(135deg,#f3e5f5,#ede7f6)">
  <div style="font-size:2.5rem">🧠</div>
  <h3 style="margin:.5rem 0">Memory & Logs</h3>
  <p style="color:#555;font-size:.9rem">Agent traces, planning debugger, scenario tester, memory snapshots</p>
</div>
""", unsafe_allow_html=True)
    st.page_link("pages/4_Memory_Logs.py", label="Open Memory & Logs →", use_container_width=True)

st.divider()

# ── Architecture Overview ─────────────────────────────────────────────────────
st.subheader("🏗️ System Architecture")
arch_col, feat_col = st.columns([3, 2])

with arch_col:
    st.markdown("""
```
  ┌─────────────────────────────────────────────────────┐
  │               Streamlit Multi-Page UI                │
  │  Patient View │ Doctor View │ Admin │ Memory & Logs  │
  └────────────────────────┬────────────────────────────┘
                           │
  ┌────────────────────────▼────────────────────────────┐
  │              HealthcareAgent (Orchestrator)          │
  │   Planner → Dispatcher → Memory Manager → Synthesis │
  └──┬──────────┬──────────┬──────────┬─────────────────┘
     │          │          │          │
  ┌──▼──┐  ┌───▼──┐  ┌────▼──┐  ┌───▼──────────┐
  │ EHR │  │ Appt │  │Search │  │  RAG (FAISS) │
  │Tool │  │ Tool │  │ Tool  │  │  Retrieval   │
  └──┬──┘  └───┬──┘  └────┬──┘  └──────────────┘
     │          │          │
  ┌──▼──────────▼──────────▼───────────────────────┐
  │           Data Layer                            │
  │  patients.json │ doctors.json │ appointments.json│
  └─────────────────────────────────────────────────┘
                           │
  ┌────────────────────────▼────────────────────────┐
  │           LLMOps / Logging Layer                 │
  │  tool_logs.json │ eval_logs.json │ agent_traces  │
  └─────────────────────────────────────────────────┘
```
""")

with feat_col:
    st.markdown("#### ✨ Key Features")
    features = [
        ("🤖", "Agentic AI", "Multi-step planning with tool chaining"),
        ("🧠", "Dual Memory", "Short-term buffer + long-term FAISS context"),
        ("🔍", "RAG Pipeline", "HuggingFace embeddings + similarity search"),
        ("📅", "Appointment AI", "Natural language booking & cancellation"),
        ("💊", "EHR Access", "Structured medical history retrieval"),
        ("🗄️", "Medical Vault", "Upload lab results, imaging, discharge summaries with OCR"),
        ("🌐", "Medical Search", "Wikipedia + DuckDuckGo (WHO/NIH sources)"),
        ("📊", "LLMOps", "Tool metrics, eval scoring, error analysis"),
        ("🔧", "Mock Mode", "Works without OpenAI key for demo use"),
    ]
    for icon, title, desc in features:
        st.markdown(f"**{icon} {title}** — {desc}")

st.divider()

# ── Setup Guide ───────────────────────────────────────────────────────────────
with st.expander("🚀 Setup Guide — First Time?", expanded=not api_ok):
    st.markdown("""
### Quick Setup

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Configure API key (optional — app runs in Mock Mode without it)**
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

**3. Run the app**
```bash
streamlit run app.py
```

---

### Running Modes

| Mode | Requirement | Behaviour |
|------|------------|-----------|
| **Mock Mode** | No API key needed | Rule-based responses, full UI works |
| **OpenAI Mode** | `OPENAI_API_KEY` in `.env` | GPT-4o-mini responses via LangChain |

---

### Directory Structure
```
AI Powered Medical Assistant/
├── app.py                    ← You are here (home)
├── config.py                 ← Central configuration
├── requirements.txt
├── .env.example
├── pages/
│   ├── 1_Patient_View.py
│   ├── 2_Doctor_View.py
│   ├── 3_Admin_Dashboard.py
│   └── 4_Memory_Logs.py
├── agents/
│   ├── healthcare_agent.py   ← Main orchestrator
│   ├── planner.py            ← Intent classifier
│   └── memory_manager.py     ← Two-tier memory
├── tools/
│   ├── appointment_tool.py
│   ├── ehr_tool.py
│   ├── medical_search_tool.py
│   └── rag_tool.py           ← FAISS RAG
├── evaluation/
│   └── evaluator.py          ← QA evaluation + LLM judge
├── utils/
│   └── logger.py             ← LLMOps logging
├── data/
│   ├── patients.json
│   ├── doctors.json
│   └── appointments.json
└── logs/                     ← Auto-created at runtime
    ├── tool_logs.json
    ├── eval_logs.json
    └── agent_traces.json
```
    """)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<div style='text-align:center;color:#aaa;font-size:.85rem'>"
    "MediAssist · AI Powered Healthcare Assistant · "
    "Built with LangChain, FAISS, Streamlit · "
    "Capstone Project — Applied Generative AI Specialisation"
    "</div>",
    unsafe_allow_html=True)
