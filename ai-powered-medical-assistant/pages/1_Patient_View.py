"""Patient View — medical history, AI chat, appointments, and record management."""
import json
import os
import sys
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.ehr_tool import get_all_patients, get_medical_history, add_medical_record
from tools.appointment_tool import (get_available_slots, book_appointment,
                                     get_appointments_by_patient, cancel_appointment)
from tools.rag_tool import rebuild_vectorstore
from tools.medical_vault_tool import (upload_medical_record, get_patient_records,
                                       delete_record, search_records, get_vault_statistics)
from agents.healthcare_agent import HealthcareAgent
import config

st.set_page_config(page_title="Patient View", page_icon="👤", layout="wide")

# ── Session state ─────────────────────────────────────────────────────────────
if "agent"          not in st.session_state: st.session_state.agent = HealthcareAgent()
if "chat_history"   not in st.session_state: st.session_state.chat_history = []
if "search_results" not in st.session_state: st.session_state.search_results = []

def add_msg(role, content): st.session_state.chat_history.append({"role": role, "content": content})

# ── Patient selector ──────────────────────────────────────────────────────────
st.title("👤 Patient View")
st.caption("Medical history · AI assistant · Appointments · Record management")

res = get_all_patients()
if not res.get("success"):
    st.error("Could not load patients."); st.stop()

options = {f"{p['name']} (ID: {p['patient_id']})": p for p in res["patients"]}
label   = st.selectbox("Select Patient", list(options.keys()))
patient = options[label]
pid     = patient["patient_id"]
st.session_state.agent.memory.set_active_patient(pid)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Medical History", "🤖 AI Assistant",
                                         "📅 Appointments", "✏️ Add Record",
                                         "🗄️ Medical Vault"])

# ─── Tab 1: Medical History ───────────────────────────────────────────────────
with tab1:
    st.subheader(f"Medical History — {patient['name']}")
    hist = get_medical_history(pid)
    if hist.get("success"):
        c1, c2, c3 = st.columns(3)
        c1.metric("Age", patient["age"])
        c2.metric("Blood Group", patient["blood_group"])
        c3.metric("Last Visit", patient.get("last_visit","N/A"))
        st.divider()

        with open(config.PATIENTS_FILE) as f:
            full = next(p for p in json.load(f) if p["patient_id"]==pid)

        cl, cr = st.columns(2)
        with cl:
            st.markdown("#### 💊 Current Medications")
            for m in full.get("current_medications",[]): st.markdown(f"- {m}")
        with cr:
            st.markdown("#### ⚠️ Allergies")
            allergies = full.get("allergies",[])
            if allergies:
                for a in allergies: st.error(f"❌ {a}")
            else:
                st.success("No known allergies")

        st.divider()
        st.markdown("#### 🗂️ History Entries")
        for entry in reversed(full.get("medical_history",[])):
            with st.expander(f"📌 {entry['date']} — {entry['diagnosis']}"):
                st.markdown(f"**Doctor:** {entry['doctor']}")
                st.markdown(f"**Treatment:** {entry['treatment']}")
                st.markdown(f"**Notes:** {entry['notes']}")

        ua = patient.get("upcoming_appointment")
        if ua:
            st.info(f"📅 **Upcoming:** {ua['doctor']} on {ua['date']} at {ua['time']}")
    else:
        st.error(hist.get("error"))

# ─── Tab 2: AI Assistant ──────────────────────────────────────────────────────
with tab2:
    st.subheader("🤖 MediAssist — AI Healthcare Assistant")
    st.caption("Ask about appointments, diagnoses, treatments, or medications.")

    sample_prompts = [
        f"Summarize {patient['name']}'s medical history",
        "Book a nephrologist appointment for my father",
        "What are the latest treatments for chronic kidney disease?",
        f"What medications is {patient['name']} currently on?",
    ]
    cols = st.columns(2)
    for i, sp in enumerate(sample_prompts):
        with cols[i % 2]:
            if st.button(sp, key=f"sp_{i}", use_container_width=True):
                add_msg("user", sp)
                with st.spinner("MediAssist is thinking..."):
                    r = st.session_state.agent.run(sp, patient_id=pid,
                                                    patient_name=patient["name"])
                add_msg("assistant", r.get("response",""))
                with st.sidebar:
                    st.subheader("🧠 Agent Plan")
                    for step, _ in r.get("plan",[]): st.markdown(f"✅ `{step}`")
                    st.metric("Duration", f"{r.get('duration_ms',0):.0f}ms")
                st.rerun()

    st.divider()
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if q := st.chat_input("Ask MediAssist anything..."):
        add_msg("user", q)
        with st.spinner("Thinking..."):
            r = st.session_state.agent.run(q, patient_id=pid, patient_name=patient["name"])
        add_msg("assistant", r.get("response",""))
        with st.sidebar:
            st.subheader("🧠 Agent Plan")
            for step, _ in r.get("plan",[]): st.markdown(f"✅ `{step}`")
            st.metric("Duration", f"{r.get('duration_ms',0):.0f}ms")
        st.rerun()

    if st.button("🗑️ Clear Chat"):
        st.session_state.chat_history = []
        st.session_state.agent.reset()
        st.rerun()

# ─── Tab 3: Appointments ──────────────────────────────────────────────────────
with tab3:
    st.subheader("📅 Appointment Booking & History")
    c_book, c_view = st.columns([1, 1])

    with c_book:
        st.markdown("#### 🔍 Find & Book")
        spec = st.selectbox("Specialization",
            ["Nephrologist","Cardiologist","Neurologist","Rheumatologist",
             "General Physician","Endocrinologist","Cardiologist"])
        if st.button("Search Doctors", type="primary"):
            sr = get_available_slots(spec)
            st.session_state.search_results = sr.get("doctors",[]) if sr.get("success") else []
            if not st.session_state.search_results:
                st.warning(f"No {spec} doctors with free slots found.")

        for doc in st.session_state.search_results:
            with st.expander(f"🩺 {doc['name']} — {doc['specialization']}"):
                st.markdown(f"**Hospital:** {doc['hospital']}  \n"
                            f"**Rating:** ⭐ {doc['rating']}  \n"
                            f"**Experience:** {doc['experience_years']} yrs  \n"
                            f"**Fee:** ₹{doc['consultation_fee']}")
                slot_opts = [f"{s['date']} at {s['time']}"
                             for s in doc["available_slots"]]
                chosen = st.selectbox("Slot", slot_opts, key=f"sl_{doc['doctor_id']}")
                reason = st.text_input("Reason", key=f"re_{doc['doctor_id']}")
                if st.button("✅ Book", key=f"bk_{doc['doctor_id']}", type="primary"):
                    d, t = chosen.split(" at ")
                    bk = book_appointment(pid, doc["doctor_id"], d, t,
                                          reason or "General consultation")
                    if bk.get("success"):
                        st.success(bk["message"])
                        st.session_state.search_results = []
                        st.rerun()
                    else:
                        st.error(bk.get("error"))

    with c_view:
        st.markdown("#### 📋 My Appointments")
        ar = get_appointments_by_patient(pid)
        if ar.get("success") and ar.get("appointments"):
            for a in ar["appointments"]:
                icon = "🟢" if a["status"]=="Confirmed" else "🔴"
                with st.expander(f"{icon} {a['date']} {a['time']} — {a['doctor_name']}"):
                    st.markdown(f"**Spec:** {a['specialization']}  \n"
                                f"**Status:** {a['status']}  \n"
                                f"**Reason:** {a['reason']}  \n"
                                f"**ID:** `{a['appointment_id']}`")
                    if a["status"]=="Confirmed":
                        if st.button("Cancel", key=f"cx_{a['appointment_id']}"):
                            cr = cancel_appointment(a["appointment_id"])
                            if cr.get("success"): st.success("Cancelled."); st.rerun()
                            else: st.error(cr.get("error"))
        else:
            st.info("No appointments found.")

# ─── Tab 4: Add Record ────────────────────────────────────────────────────────
with tab4:
    st.subheader("✏️ Add Medical Record")
    with st.form("rec_form"):
        c1, c2 = st.columns(2)
        with c1:
            rec_date  = st.date_input("Date")
            diagnosis = st.text_input("Diagnosis *")
            doc_name  = st.text_input("Doctor Name *")
        with c2:
            treatment = st.text_area("Treatment *", height=100)
            notes     = st.text_area("Notes", height=100)
        if st.form_submit_button("💾 Save Record", type="primary"):
            if diagnosis and doc_name and treatment:
                r = add_medical_record(pid, diagnosis, doc_name,
                                       treatment, notes, str(rec_date))
                if r.get("success"):
                    st.success(r["message"])
                    rebuild_vectorstore()
                    st.rerun()
                else:
                    st.error(r.get("error"))
            else:
                st.warning("Fill all required (*) fields.")

# ─── Tab 5: Medical Vault ─────────────────────────────────────────────────────
with tab5:
    st.subheader("🗄️ Medical Records Vault")
    st.caption("Upload lab results, imaging reports, discharge summaries with OCR extraction")
    
    # Vault statistics
    vault_stats = get_vault_statistics(pid)
    if vault_stats.get("success"):
        stats = vault_stats["statistics"]
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Records", stats["total_records"])
        c2.metric("Lab Results", stats["by_type"]["lab_results"])
        c3.metric("Imaging", stats["by_type"]["imaging"])
        c4.metric("Discharge", stats["by_type"]["discharge_summaries"])
        c5.metric("OCR Success", f"{stats['ocr_success_rate']:.0f}%")
        
        if stats["total_records"] > 0:
            st.caption(f"Total storage: {stats['total_size_mb']:.2f} MB")
    
    st.divider()
    
    # Upload section
    vault_col1, vault_col2 = st.columns([1, 1])
    
    with vault_col1:
        st.markdown("#### 📤 Upload New Record")
        
        with st.form("upload_form", clear_on_submit=True):
            record_type = st.selectbox(
                "Record Type *",
                ["lab_result", "imaging", "discharge_summary", "other"],
                format_func=lambda x: {
                    "lab_result": "🧪 Lab Result",
                    "imaging": "🩻 Imaging Report",
                    "discharge_summary": "📋 Discharge Summary",
                    "other": "📄 Other Document"
                }[x]
            )
            
            rec_title = st.text_input("Title *", placeholder="e.g., Blood Test - Jan 2024")
            rec_description = st.text_area("Description", placeholder="Optional notes about this record")
            rec_date_vault = st.date_input("Record Date")
            rec_doctor = st.text_input("Doctor/Lab Name", placeholder="Who ordered/created this record")
            
            uploaded_file = st.file_uploader(
                "Upload File *",
                type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp"],
                help="Supported: PDF, PNG, JPG, TIFF, BMP. OCR will extract text automatically."
            )
            
            enable_ocr = st.checkbox("Enable OCR/Text Extraction", value=True)
            
            submit_upload = st.form_submit_button("📤 Upload to Vault", type="primary")
            
            if submit_upload:
                if uploaded_file and rec_title:
                    with st.spinner("Uploading and processing... OCR may take a few seconds."):
                        # Read file data
                        file_bytes = uploaded_file.read()
                        
                        # Upload to vault
                        upload_result = upload_medical_record(
                            patient_id=pid,
                            record_type=record_type,
                            title=rec_title,
                            file_data=file_bytes,
                            filename=uploaded_file.name,
                            description=rec_description,
                            date_str=str(rec_date_vault),
                            doctor_name=rec_doctor,
                            extract_text=enable_ocr
                        )
                        
                        if upload_result.get("success"):
                            st.success(upload_result["message"])
                            
                            # Show extraction results
                            if upload_result.get("extracted_text"):
                                with st.expander("✅ Text Extracted (OCR)"):
                                    st.caption(f"Method: {upload_result.get('extraction_method')}")
                                    st.text_area("Extracted Text", 
                                                value=upload_result["extracted_text"],
                                                height=200, disabled=True)
                            elif enable_ocr:
                                st.info("ℹ️ No text could be extracted from this file.")
                            
                            st.rerun()
                        else:
                            st.error(f"Upload failed: {upload_result.get('error')}")
                else:
                    st.warning("Please provide title and select a file.")
    
    with vault_col2:
        st.markdown("#### 🔍 Search Records")
        
        search_query = st.text_input("Search", placeholder="Search by title, description, or extracted text")
        search_filter = st.selectbox(
            "Filter by Type",
            ["all", "lab_result", "imaging", "discharge_summary", "other"],
            format_func=lambda x: {
                "all": "All Types",
                "lab_result": "🧪 Lab Results",
                "imaging": "🩻 Imaging",
                "discharge_summary": "📋 Discharge Summaries",
                "other": "📄 Other"
            }[x]
        )
        
        if search_query:
            search_results = search_records(
                query=search_query,
                patient_id=pid,
                record_type=search_filter if search_filter != "all" else None
            )
            
            if search_results.get("success"):
                st.caption(f"Found {search_results['total_matches']} matching records")
        
    st.divider()
    
    # Display records
    st.markdown("#### 📚 My Medical Records")
    
    # Filter tabs
    filter_tab1, filter_tab2, filter_tab3, filter_tab4, filter_tab5 = st.tabs([
        "All", "🧪 Lab Results", "🩻 Imaging", "📋 Discharge", "📄 Other"
    ])
    
    filter_mapping = [None, "lab_result", "imaging", "discharge_summary", "other"]
    
    for idx, filter_tab in enumerate([filter_tab1, filter_tab2, filter_tab3, filter_tab4, filter_tab5]):
        with filter_tab:
            record_filter = filter_mapping[idx]
            records_result = get_patient_records(pid, record_type=record_filter)
            
            if records_result.get("success"):
                records = records_result["records"]
                
                if records:
                    for rec in records:
                        # Icon based on type
                        type_icon = {
                            "lab_result": "🧪",
                            "imaging": "🩻",
                            "discharge_summary": "📋",
                            "other": "📄"
                        }.get(rec["record_type"], "📄")
                        
                        with st.expander(f"{type_icon} {rec['title']} — {rec['record_date']}"):
                            col_info, col_actions = st.columns([3, 1])
                            
                            with col_info:
                                st.markdown(f"**Type:** {rec['record_type'].replace('_', ' ').title()}")
                                st.markdown(f"**Date:** {rec['record_date']}")
                                st.markdown(f"**Doctor/Lab:** {rec['doctor_name']}")
                                st.markdown(f"**Uploaded:** {rec['upload_date']}")
                                st.markdown(f"**File:** `{rec['filename']}` ({rec['file_size_bytes'] / 1024:.1f} KB)")
                                
                                if rec.get("description"):
                                    st.markdown(f"**Description:** {rec['description']}")
                                
                                # Show extracted text
                                if rec.get("extracted_text"):
                                    with st.expander("📄 View Extracted Text"):
                                        st.caption(f"Extraction method: {rec.get('extraction_method')}")
                                        st.text_area(
                                            "Text",
                                            value=rec["extracted_text"],
                                            height=200,
                                            disabled=True,
                                            key=f"text_{rec['record_id']}"
                                        )
                            
                            with col_actions:
                                # Download button
                                if os.path.exists(rec["file_path"]):
                                    with open(rec["file_path"], "rb") as f:
                                        file_data = f.read()
                                    st.download_button(
                                        "⬇️ Download",
                                        data=file_data,
                                        file_name=rec["filename"],
                                        mime="application/octet-stream",
                                        key=f"dl_{rec['record_id']}"
                                    )
                                
                                # Delete button
                                if st.button("🗑️ Delete", key=f"del_{rec['record_id']}", type="secondary"):
                                    del_result = delete_record(rec["record_id"])
                                    if del_result.get("success"):
                                        st.success("Deleted!")
                                        st.rerun()
                                    else:
                                        st.error(del_result.get("error"))
                else:
                    st.info("No records found in this category.")
            else:
                st.error(f"Error loading records: {records_result.get('error')}")
