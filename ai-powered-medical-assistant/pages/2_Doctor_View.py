"""Doctor View — schedule, patient lookup, and slot availability."""
import json, os, sys
import streamlit as st
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from tools.appointment_tool import get_appointments_by_doctor
from tools.ehr_tool import get_medical_history, get_all_patients
from tools.visit_history_tool import get_doctor_visits

st.set_page_config(page_title="Doctor View", page_icon="🩺", layout="wide")
st.title("🩺 Doctor View")
st.caption("Doctor schedule · Patient lookup · Real-time appointment tracking")

with open(config.DOCTORS_FILE) as f:
    all_docs = json.load(f)

doc_options = {f"{d['name']} — {d['specialization']}": d for d in all_docs}
dlabel = st.selectbox("Select Doctor", list(doc_options.keys()))
doc    = doc_options[dlabel]
did    = doc["doctor_id"]

c1,c2,c3,c4 = st.columns(4)
c1.metric("Specialization", doc["specialization"])
c2.metric("Experience",     f"{doc['experience_years']} yrs")
c3.metric("Rating",         f"⭐ {doc['rating']}")
c4.metric("Fee",            f"₹{doc['consultation_fee']}")
st.markdown(f"🏥 **{doc['hospital']}**  |  ✉️ {doc['email']}")
st.divider()

tab1, tab2, tab3 = st.tabs(["📅 Schedule", "👥 Patient Lookup", "🗓️ Availability"])

with tab1:
    st.subheader("Appointments")
    ar = get_appointments_by_doctor(did)
    if ar.get("success") and ar.get("appointments"):
        appts = ar["appointments"]
        df = pd.DataFrame(appts)[["appointment_id","patient_name","date","time","status","reason"]]
        df.columns = ["ID","Patient","Date","Time","Status","Reason"]

        def hl(val):
            if val=="Confirmed": return "background-color:#d4edda;color:#155724"
            if val=="Cancelled": return "background-color:#f8d7da;color:#721c24"
            return ""

        st.dataframe(df.sort_values(["Date","Time"]).style.map(hl,subset=["Status"]),
                     use_container_width=True, hide_index=True)
        c1,c2,c3 = st.columns(3)
        c1.metric("Total",     len(appts))
        c2.metric("Confirmed", sum(1 for a in appts if a["status"]=="Confirmed"))
        c3.metric("Cancelled", sum(1 for a in appts if a["status"]=="Cancelled"))
    else:
        st.info("No appointments scheduled.")

    st.divider()
    st.subheader("Visit History")
    vr = get_doctor_visits(did)
    if vr.get("success") and vr.get("visits"):
        c1,c2,c3 = st.columns(3)
        c1.metric("Past Visits",        len(vr["visits"]))
        c2.metric("Patients Seen",      vr["unique_patients"])
        c3.metric("Referrals Received", vr["referrals_received"])
        st.dataframe(pd.DataFrame([{
            "Date": v["date"], "Patient": v["patient_name"], "Type": v["visit_type"],
            "Diagnosis": v["diagnosis"], "Status": v["control_status"],
            "Complaint": v["chief_complaint"],
        } for v in vr["visits"]]), use_container_width=True, hide_index=True)
    else:
        st.info("No past visits recorded.")

with tab2:
    st.subheader("Quick Patient Lookup")
    pr = get_all_patients()
    if pr.get("success"):
        popts = {f"{p['name']} ({p['patient_id']})": p for p in pr["patients"]}
        plabel = st.selectbox("Patient", list(popts.keys()))
        sp = popts[plabel]
        st.markdown(f"**Conditions:** {', '.join(sp.get('conditions',[]))}")
        st.markdown(f"**Last Visit:** {sp.get('last_visit','N/A')}")
        if st.button("📋 Load Full History"):
            h = get_medical_history(sp["patient_id"])
            if h.get("success"):
                st.code(h["history_text"], language=None)
            else:
                st.error(h.get("error"))
        ua = sp.get("upcoming_appointment")
        if ua:
            st.info(f"📅 Upcoming with **{ua['doctor']}** on {ua['date']} at {ua['time']}")
    else:
        st.error("Could not load patients.")

with tab3:
    st.subheader("Slot Availability")
    from datetime import date
    today  = date.today().isoformat()
    future = [s for s in doc.get("available_slots",[]) if s["date"] >= today]
    if not future:
        st.info("No future slots configured.")
    else:
        df_s = pd.DataFrame(future)
        df_s["Status"] = df_s["booked"].map({True:"🔴 Booked", False:"🟢 Available"})
        df_s = df_s.rename(columns={"date":"Date","time":"Time"})[["Date","Time","Status"]].sort_values(["Date","Time"])

        free = df_s[df_s["Status"]=="🟢 Available"]
        busy = df_s[df_s["Status"]=="🔴 Booked"]
        ca, cb = st.columns(2)
        with ca:
            st.markdown("##### 🟢 Available")
            st.dataframe(free, use_container_width=True, hide_index=True)
        with cb:
            st.markdown("##### 🔴 Booked")
            st.dataframe(busy, use_container_width=True, hide_index=True)

        booked = sum(1 for s in future if s["booked"])
        total  = len(future)
        st.progress(booked/total if total else 0,
                    text=f"Utilisation: {booked}/{total} slots booked")
