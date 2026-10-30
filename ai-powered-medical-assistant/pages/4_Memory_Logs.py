"""Memory & Logs — agent traces, planning debugger, scenario tester, memory snapshot."""
import json, os, sys, time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.logger import get_agent_traces, get_tool_logs, clear_agent_traces
from agents.healthcare_agent import HealthcareAgent

st.set_page_config(page_title="Memory & Logs", page_icon="🧠", layout="wide")
st.title("🧠 Memory & Agent Logs")
st.caption("Agent traces · Planning debugger · Scenario tester · Memory snapshots")

if st.button("🔄 Refresh", type="secondary"): st.rerun()

tab1, tab2, tab3, tab4 = st.tabs([
    "📜 Agent Traces", "🗺️ Planning Debugger",
    "🧪 Scenario Tester", "💾 Memory Snapshot"])

# ─── Tab 1: Agent Traces ──────────────────────────────────────────────────────
with tab1:
    st.subheader("📜 Agent Execution Traces")
    traces = get_agent_traces(50)

    if not traces:
        st.info("No agent traces yet. Use the AI Assistant in Patient View to generate activity.")
    else:
        # Summary metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Sessions",   len(traces))
        c2.metric("Unique Patients",  len({t.get("patient_id","?") for t in traces if t.get("patient_id")}))
        c3.metric("Total Plan Steps", sum(len(t.get("plan",[])) for t in traces))
        avg_steps = sum(len(t.get("steps",[])) for t in traces) / len(traces)
        c4.metric("Avg Steps/Session", f"{avg_steps:.1f}")
        st.divider()

        for i, trace in enumerate(reversed(traces)):
            ts  = trace.get("timestamp","")[:19].replace("T"," ")
            sid = trace.get("session_id","?")
            inp = trace.get("user_input","")[:60]
            pid = trace.get("patient_id","N/A")
            steps = trace.get("steps",[])
            plan  = trace.get("plan",[])

            with st.expander(f"🔷 Session `{sid}` | {ts} | Patient: `{pid}`  —  *{inp}…*"):
                col_l, col_r = st.columns([1, 2])

                with col_l:
                    st.markdown("**🗒️ Plan**")
                    for p in plan:
                        st.markdown(f"- `{p}`")

                with col_r:
                    st.markdown("**⚙️ Execution Steps**")
                    for step in steps:
                        icon = {"success":"✅","error":"❌","info":"ℹ️"}.get(step.get("status",""),"🔹")
                        st.markdown(
                            f"{icon} `{step.get('tool','?')}` — "
                            f"{step.get('detail','')[:80]}  "
                            f"<small style='color:grey'>{step.get('timestamp','')[-8:]}</small>",
                            unsafe_allow_html=True)

                st.markdown("**💬 Response Preview**")
                resp = trace.get("final_response","")
                st.markdown(resp[:600] + ("…" if len(resp) > 600 else ""))

        # Timeline chart
        if len(traces) > 1:
            st.divider()
            df_t = pd.DataFrame([{
                "timestamp": t.get("timestamp",""),
                "steps": len(t.get("steps",[])),
                "session": t.get("session_id","?")[:6],
                "patient": t.get("patient_id","?")
            } for t in traces])
            df_t["timestamp"] = pd.to_datetime(df_t["timestamp"])
            fig = px.scatter(df_t, x="timestamp", y="steps",
                             color="patient", size="steps", hover_data=["session"],
                             title="Steps per Agent Session Over Time")
            st.plotly_chart(fig, use_container_width=True)

    if traces and st.button("🗑️ Clear Agent Traces", type="secondary"):
        clear_agent_traces()
        st.success("Agent traces cleared.")
        st.rerun()


# ─── Tab 2: Planning Debugger ─────────────────────────────────────────────────
with tab2:
    st.subheader("🗺️ Query Planning Debugger")
    st.caption("See exactly how the agent decomposes your query into a plan, without executing tools.")

    debug_input = st.text_area(
        "Enter a query to decompose",
        value="Book an appointment with a cardiologist for patient Rajesh Kumar",
        height=80)

    if st.button("🔍 Decompose Query", type="primary"):
        from agents.planner import decompose_query, build_plan_text, classify_intents
        intents = classify_intents(debug_input)
        plan    = decompose_query(debug_input)

        st.divider()
        c_intent, c_plan = st.columns(2)
        with c_intent:
            st.markdown("#### 🎯 Detected Intents")
            if intents:
                for intent in intents:
                    colors = {
                        "book_appointment":  "#d4edda",
                        "get_medical_history": "#cce5ff",
                        "search_medical_info": "#fff3cd",
                        "add_medical_record":  "#ffe8d6",
                        "get_patient_info":    "#e2d9f3",
                    }
                    bg = colors.get(intent, "#f8f9fa")
                    st.markdown(
                        f"<span style='background:{bg};padding:4px 10px;border-radius:6px;"
                        f"font-family:monospace;font-size:0.9em'>{intent}</span>",
                        unsafe_allow_html=True)
            else:
                st.warning("No intents detected — query may be too vague.")

        with c_plan:
            st.markdown("#### 📋 Execution Plan")
            for order, (intent, desc) in enumerate(plan, 1):
                st.markdown(f"**Step {order}:** `{intent}`  \n_{desc}_")

        st.divider()
        st.markdown("#### 🔬 Raw Plan Text")
        st.code(build_plan_text(plan), language=None)

    st.divider()
    st.markdown("#### 📚 Intent Reference")
    intent_ref = {
        "book_appointment":    "Triggered by: 'book', 'appointment', 'doctor', 'schedule', specialist names",
        "get_medical_history": "Triggered by: 'history', 'medical record', 'diagnosis', 'condition', 'patient'",
        "search_medical_info": "Triggered by: 'what is', 'symptoms', 'treatment', 'medication', 'disease'",
        "add_medical_record":  "Triggered by: 'add record', 'update', 'new diagnosis', 'prescribed'",
        "get_patient_info":    "Triggered by: patient names or 'patient information'",
    }
    for intent, desc in intent_ref.items():
        st.markdown(f"- **`{intent}`** — {desc}")


# ─── Tab 3: Scenario Tester ───────────────────────────────────────────────────
with tab3:
    st.subheader("🧪 Interactive Scenario Tester")
    st.caption("Run complete end-to-end agent scenarios and inspect all steps.")

    if "scenario_agent" not in st.session_state:
        st.session_state.scenario_agent = HealthcareAgent()
    if "scenario_result" not in st.session_state:
        st.session_state.scenario_result = None

    preset_scenarios = {
        "-- Custom --": "",
        "📋 Summarise patient history":
            "Summarize the complete medical history for patient P001",
        "🩺 Book cardiology appointment":
            "I need to see a cardiologist as soon as possible",
        "🔍 Search CKD treatment":
            "What are the latest treatment options for chronic kidney disease?",
        "💊 Check medications":
            "What medications is Rajesh Kumar currently taking?",
        "🤒 Arthritis information":
            "Tell me about rheumatoid arthritis symptoms and treatment",
    }

    # A keyed text_area ignores later changes to value=, so the preset is
    # pushed into its session-state slot when the selection changes.
    def _apply_preset():
        st.session_state.scenario_query_input = preset_scenarios[st.session_state.scenario_preset]

    st.selectbox("Quick Scenario", list(preset_scenarios.keys()),
                 key="scenario_preset", on_change=_apply_preset)
    scenario_query = st.text_area(
        "Query",
        height=80,
        key="scenario_query_input")

    import config as _cfg
    from tools.ehr_tool import get_all_patients
    pr = get_all_patients()
    patient_opts = {f"{p['name']} ({p['patient_id']})": p
                    for p in (pr.get("patients") or [])}
    sel_p_label = st.selectbox("Patient Context", ["None"] + list(patient_opts.keys()))
    sel_patient = patient_opts.get(sel_p_label) if sel_p_label != "None" else None

    if st.button("▶️ Run Scenario", type="primary"):
        if not scenario_query.strip():
            st.warning("Enter a query first.")
        else:
            with st.spinner("Running agent pipeline..."):
                pid  = sel_patient["patient_id"]  if sel_patient else None
                pname= sel_patient["name"]         if sel_patient else None
                result = st.session_state.scenario_agent.run(
                    scenario_query, patient_id=pid, patient_name=pname)
            st.session_state.scenario_result = result
            st.rerun()

    if st.session_state.scenario_result:
        res = st.session_state.scenario_result
        st.divider()

        # Top metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Duration",    f"{res.get('duration_ms',0):.0f} ms")
        c2.metric("Plan Steps",  len(res.get("plan",[])))
        c3.metric("Tool Steps",  len(res.get("steps",[])))
        c4.metric("Session ID",  res.get("session_id","?"))

        # Plan + Steps side by side
        sc_l, sc_r = st.columns(2)
        with sc_l:
            st.markdown("#### 🗒️ Execution Plan")
            for intent, desc in res.get("plan",[]):
                st.markdown(f"- `{intent}`: _{desc}_")

        with sc_r:
            st.markdown("#### ⚙️ Steps Executed")
            for step in res.get("steps",[]):
                icon = {"success":"✅","error":"❌","info":"ℹ️"}.get(step.get("status",""),"🔹")
                st.markdown(f"{icon} **`{step.get('tool','?')}`** — {step.get('detail','')[:70]}")

        # Tool results
        st.markdown("#### 🔧 Tool Results")
        for tr in res.get("tool_results",[]):
            success = tr["data"].get("success", False)
            icon = "✅" if success else "❌"
            with st.expander(f"{icon} `{tr['intent']}` — {tr['desc'][:50]}"):
                st.json(tr["data"])

        # Agent response
        st.markdown("#### 💬 Agent Response")
        st.markdown(res.get("response",""))

        # Memory snapshot
        snap = res.get("memory_snapshot",{})
        if snap:
            st.markdown("#### 🧠 Memory State After Run")
            ms_l, ms_r = st.columns(2)
            with ms_l:
                st.markdown("**Short-term turns:**")
                for turn in snap.get("short_term_history",[]):
                    role = "👤" if turn["role"]=="user" else "🤖"
                    st.markdown(f"{role} {turn['content'][:80]}")
            with ms_r:
                st.markdown("**Session facts:**")
                for fact in snap.get("session_facts",[]):
                    st.markdown(f"- {fact}")

    if st.button("🔄 Reset Scenario Agent"):
        st.session_state.scenario_agent = HealthcareAgent()
        st.session_state.scenario_result = None
        st.success("Agent reset.")
        st.rerun()


# ─── Tab 4: Memory Snapshot ───────────────────────────────────────────────────
with tab4:
    st.subheader("💾 Live Memory Snapshot")
    st.caption("Current in-memory state of all active agent sessions in this app instance.")

    # Show recent tool calls as a proxy for system memory state
    tl = get_tool_logs(100)
    if tl:
        st.markdown("#### 🔧 Recent Tool Call Memory (last 100)")
        df_tl = pd.DataFrame(tl)
        df_tl["timestamp"] = pd.to_datetime(df_tl["timestamp"]).dt.strftime("%m/%d %H:%M:%S")
        df_tl["success"] = df_tl["success"].map({True: "✅", False: "❌"})
        cols_show = ["timestamp","tool_name","success","duration_ms","patient_id"]
        cols_show = [c for c in cols_show if c in df_tl.columns]
        st.dataframe(df_tl[cols_show], use_container_width=True, hide_index=True)

        # Tool call distribution
        tool_counts = df_tl["tool_name"].value_counts()
        fig_m = go.Figure(data=[go.Bar(
            x=tool_counts.index.tolist(),
            y=tool_counts.values.tolist(),
            marker_color="#1E88E5")])
        fig_m.update_layout(title="Tool Call Distribution", xaxis_title="Tool", yaxis_title="Count")
        st.plotly_chart(fig_m, use_container_width=True)

        # Patient activity heatmap proxy
        if "patient_id" in df_tl.columns:
            pt_counts = df_tl["patient_id"].value_counts().reset_index()
            pt_counts.columns = ["Patient","Calls"]
            fig_p = px.pie(pt_counts, names="Patient", values="Calls",
                           title="Tool Calls by Patient",
                           color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_p, use_container_width=True)
    else:
        st.info("No tool logs yet. Use the AI Assistant to generate activity.")

    st.divider()
    st.markdown("#### 📂 Log Files on Disk")
    log_files = {
        "Tool Logs":    config.TOOL_LOGS_FILE,
        "Eval Logs":    config.EVAL_LOGS_FILE,
        "Agent Traces": config.AGENT_TRACES_FILE,
    }
    for name, path in log_files.items():
        if os.path.exists(path):
            size_kb = os.path.getsize(path) / 1024
            try:
                with open(path) as f:
                    count = len(json.load(f))
            except Exception:
                count = "?"
            st.markdown(f"- **{name}** — `{os.path.basename(path)}` | {size_kb:.1f} KB | {count} entries")
        else:
            st.markdown(f"- **{name}** — _{os.path.basename(path)} not found yet_")
