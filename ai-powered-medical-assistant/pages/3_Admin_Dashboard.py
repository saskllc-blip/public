"""Admin Dashboard — LLMOps: tool analytics, model evaluation, debug console."""
import json, os, sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.logger import (get_tool_logs, get_eval_logs, get_metrics_summary,
                           clear_tool_logs, clear_eval_logs, clear_agent_traces)
from evaluation.evaluator import run_evaluation, get_evaluation_summary

st.set_page_config(page_title="Admin Dashboard", page_icon="⚙️", layout="wide")
st.title("⚙️ Admin Dashboard — LLMOps & Metrics")
st.caption("System health · Tool performance · Model evaluation · Debug console")

if st.button("🔄 Refresh", type="secondary"): st.rerun()

# ── Overview metrics ──────────────────────────────────────────────────────────
m    = get_metrics_summary()
ev   = get_evaluation_summary()
cols = st.columns(6)
cols[0].metric("Total Tool Calls",   m["total_tool_calls"])
cols[1].metric("✅ Successful",      m["successful_tool_calls"])
cols[2].metric("❌ Failed",          m["failed_tool_calls"])
cols[3].metric("Success Rate",       f"{m['tool_success_rate']:.1f}%")
cols[4].metric("Agent Sessions",     m["total_agent_sessions"])
cols[5].metric("Avg Eval Score",     f"{ev['average_score']:.2f}")
st.divider()

tab1,tab2,tab3,tab4,tab5 = st.tabs([
    "📈 Tool Analytics","🧪 Model Evaluation",
    "🐛 Debug Console","📋 Appointment Stats","🔧 System Controls"])

# ─── Tab 1: Tool Analytics ────────────────────────────────────────────────────
with tab1:
    st.subheader("Tool Usage Analytics")
    counts = m.get("tool_call_counts",{})
    if counts:
        cc, ct = st.columns([2,1])
        with cc:
            fig = px.bar(x=list(counts.keys()), y=list(counts.values()),
                         labels={"x":"Tool","y":"Calls"},
                         title="Call Frequency by Tool",
                         color=list(counts.values()), color_continuous_scale="Blues")
            fig.update_layout(showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        with ct:
            st.dataframe(pd.DataFrame(list(counts.items()),columns=["Tool","Calls"])
                         .sort_values("Calls",ascending=False),
                         use_container_width=True, hide_index=True)
    else:
        st.info("No tool call data yet. Use the AI Assistant to generate data.")

    logs = get_tool_logs(50)
    if logs:
        st.subheader("Recent Tool Logs")
        df = pd.DataFrame(logs)[["timestamp","tool_name","success","duration_ms","error","patient_id"]]
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%m/%d %H:%M:%S")
        df["success"]   = df["success"].map({True:"✅",False:"❌"})

        def hl_row(row):
            return ["background-color:#fff3cd"]*len(row) if row["success"]=="❌" else [""]*len(row)

        st.dataframe(df.style.apply(hl_row,axis=1), use_container_width=True, hide_index=True)

        sc = pd.DataFrame(logs)["success"].value_counts().reset_index()
        sc.columns=["Status","Count"]
        sc["Status"]=sc["Status"].map({True:"Success",False:"Failed"})
        fig2=px.pie(sc,names="Status",values="Count",title="Success Rate",
                    color="Status",color_discrete_map={"Success":"#28a745","Failed":"#dc3545"})
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No tool logs yet.")

# ─── Tab 2: Model Evaluation ─────────────────────────────────────────────────
with tab2:
    st.subheader("🧪 QA Model Evaluation")
    ecol, rcol = st.columns([1,2])

    with ecol:
        st.markdown("#### Run Evaluation")
        emod   = st.selectbox("Module",["all","appointment","ehr","search","rag"])
        llmj   = st.checkbox("LLM-as-Judge (needs OpenAI key)", value=False)
        live   = st.checkbox("Use live agent for answers", value=False)
        if st.button("▶️ Run Evaluation", type="primary"):
            with st.spinner("Evaluating..."):
                agent_inst = None
                if live:
                    from agents.healthcare_agent import HealthcareAgent
                    agent_inst = HealthcareAgent()
                er = run_evaluation(emod, agent_inst, llmj)
            st.success(f"Done! Avg: **{er['average_score']:.3f}** Grade: **{er['grade']}**")
            st.session_state["last_eval"] = er

    with rcol:
        st.markdown("#### Historical Summary")
        c1,c2,c3 = st.columns(3)
        c1.metric("Total Evals",  ev["total_evals"])
        c2.metric("Avg Score",    f"{ev['average_score']:.3f}")
        c3.metric("Overall Grade",ev["grade"])
        if ev.get("module_averages"):
            fig_r=go.Figure(data=go.Scatterpolar(
                r=list(ev["module_averages"].values()),
                theta=list(ev["module_averages"].keys()),
                fill="toself", name="Module Scores", line_color="#1E88E5"))
            fig_r.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,1])),
                                 title="Module Performance", showlegend=False)
            st.plotly_chart(fig_r, use_container_width=True)

    if "last_eval" in st.session_state:
        st.divider()
        st.subheader("Latest Results")
        df_ev = pd.DataFrame(st.session_state["last_eval"]["results"])[
            ["module","question","score","grade","generated"]]
        df_ev.columns=["Module","Question","Score","Grade","Answer"]
        grade_colors={"A":"#d4edda","B":"#cce5ff","C":"#fff3cd","D":"#ffe8d6","F":"#f8d7da"}
        st.dataframe(df_ev.style.map(lambda v: f"background-color:{grade_colors.get(v,'')}",
                                           subset=["Grade"]),
                     use_container_width=True, hide_index=True)

    all_el = get_eval_logs(200)
    if len(all_el) > 1:
        dft = pd.DataFrame(all_el)[["timestamp","score","module"]]
        dft["timestamp"] = pd.to_datetime(dft["timestamp"])
        st.plotly_chart(px.line(dft,x="timestamp",y="score",color="module",
                                title="Eval Score Trend Over Time"),
                        use_container_width=True)

# ─── Tab 3: Debug Console ────────────────────────────────────────────────────
with tab3:
    st.subheader("🐛 Failure Analysis & Debug Console")
    tl    = get_tool_logs(200)
    fails = [t for t in tl if not t["success"]]

    if fails:
        st.error(f"⚠️ {len(fails)} failed tool calls")
        df_f = pd.DataFrame(fails)[["timestamp","tool_name","input","error","duration_ms"]]
        df_f.columns = ["Timestamp","Tool","Input","Error","Duration(ms)"]
        st.dataframe(df_f, use_container_width=True, hide_index=True)

        ec = (pd.DataFrame(fails)["error"].fillna("Unknown")
              .str[:50].value_counts().reset_index())
        ec.columns=["Error","Count"]
        st.plotly_chart(px.bar(ec,x="Count",y="Error",orientation="h",
                               title="Error Frequency",color="Count",
                               color_continuous_scale="Reds"),
                        use_container_width=True)

        st.subheader("💡 Suggested Fixes")
        for err in list({t.get("error","") for t in fails if t.get("error")})[:5]:
            with st.expander(f"Error: {err[:80]}"):
                if "not found" in err.lower():
                    st.markdown("**Fix:** Verify patient/doctor ID exists in data files.")
                elif "api" in err.lower() or "key" in err.lower():
                    st.markdown("**Fix:** Check OPENAI_API_KEY in `.env`.")
                elif "slot" in err.lower():
                    st.markdown("**Fix:** Slot already booked — refresh available slots.")
                elif "import" in err.lower() or "module" in err.lower():
                    st.markdown("**Fix:** Run `pip install -r requirements.txt`")
                else:
                    st.code(err)
    else:
        st.success("✅ No failures in recent tool calls!")

    st.divider()
    st.subheader("🔬 Live Tool Test")
    tt = st.selectbox("Tool",["get_available_slots","get_medical_history",
                               "search_medical_info","get_all_patients"])
    ti = st.text_input("Input", value="P001")
    if st.button("▶️ Run Test"):
        import time
        t0 = time.time()
        try:
            if tt=="get_available_slots":
                from tools.appointment_tool import get_available_slots as fn
                r=fn(ti)
            elif tt=="get_medical_history":
                from tools.ehr_tool import get_medical_history as fn
                r=fn(ti)
            elif tt=="search_medical_info":
                from tools.medical_search_tool import search_medical_info as fn
                r=fn(ti)
            else:
                from tools.ehr_tool import get_all_patients as fn
                r=fn()
        except Exception as e:
            r={"success":False,"error":str(e)}
        elapsed=(time.time()-t0)*1000
        st.json(r)
        st.metric("Execution Time",f"{elapsed:.0f}ms")
        (st.success if r.get("success") else st.error)(
            "✅ Tool OK" if r.get("success") else f"❌ {r.get('error')}")

# ─── Tab 4: Appointment Stats ─────────────────────────────────────────────────
with tab4:
    st.subheader("📋 Appointment Analytics")
    with open(config.APPOINTMENTS_FILE) as f:
        all_a = json.load(f)
    if not all_a:
        st.info("No appointments yet.")
    else:
        df_a = pd.DataFrame(all_a)
        c1,c2,c3 = st.columns(3)
        c1.metric("Total",     len(df_a))
        c2.metric("Confirmed", len(df_a[df_a["status"]=="Confirmed"]))
        c3.metric("Cancelled", len(df_a[df_a["status"]=="Cancelled"]))

        r1,r2 = st.columns(2)
        with r1:
            st.plotly_chart(px.pie(df_a,names="specialization",
                                   title="By Specialization",
                                   color_discrete_sequence=px.colors.qualitative.Set2),
                            use_container_width=True)
        with r2:
            dc=df_a["doctor_name"].value_counts().reset_index()
            dc.columns=["Doctor","Appointments"]
            st.plotly_chart(px.bar(dc,x="Doctor",y="Appointments",
                                   title="Per Doctor",color="Appointments",
                                   color_continuous_scale="Blues"),
                            use_container_width=True)

        st.subheader("All Appointments")
        st.dataframe(df_a[["appointment_id","patient_name","doctor_name",
                            "date","time","status","reason"]],
                     use_container_width=True, hide_index=True)

# ─── Tab 5: System Controls ───────────────────────────────────────────────────
with tab5:
    st.subheader("🔧 System Controls")
    st.warning("⚠️ These actions are irreversible.")
    c1,c2,c3 = st.columns(3)
    with c1:
        if st.button("🗑️ Clear Tool Logs"):
            clear_tool_logs(); st.success("Tool logs cleared.")
    with c2:
        if st.button("🧹 Clear Eval Logs"):
            clear_eval_logs(); st.success("Eval logs cleared.")
    with c3:
        if st.button("🔄 Rebuild FAISS Index"):
            with st.spinner("Rebuilding..."):
                from tools.rag_tool import rebuild_vectorstore
                r = rebuild_vectorstore()
            (st.success if r.get("success") else st.error)(
                r.get("message") or r.get("error"))

    st.divider()
    st.markdown("#### ⚙️ Configuration")
    st.json({"LLM_MODEL": config.LLM_MODEL,
             "EMBEDDING_MODEL": config.EMBEDDING_MODEL,
             "CHUNK_SIZE": config.CHUNK_SIZE,
             "TOP_K_RESULTS": config.TOP_K_RESULTS,
             "MEMORY_WINDOW": config.MEMORY_WINDOW,
             "OPENAI_API_KEY": "✅ Set" if config.OPENAI_API_KEY and
             config.OPENAI_API_KEY != "your_openai_api_key_here" else "❌ Not set (Mock Mode)"})

    st.markdown("#### 📦 Package Status")
    pkgs = ["streamlit","langchain","langchain_openai","langchain_community",
            "faiss","sentence_transformers","openai","wikipedia",
            "duckduckgo_search","pandas","plotly"]
    rows = []
    for pkg in pkgs:
        try:
            __import__(pkg if pkg!="faiss" else "faiss")
            rows.append({"Package":pkg,"Status":"✅ Installed"})
        except ImportError:
            rows.append({"Package":pkg,"Status":"❌ Missing"})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
