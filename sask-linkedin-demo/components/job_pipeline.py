"""Job Pipeline tab component."""

try:
    import streamlit as st
except ImportError:
    st = None

from fixtures.jobs import MOCK_JOBS


def render_job_pipeline_tab():
    """Render job pipeline tab with Kanban-style layout."""
    if st is None:
        return

    st.warning("⚠️ **Sample Data — Demonstration Only**")

    st.subheader("Job Pipeline")

    jobs = MOCK_JOBS
    stages = ["Open", "Under Review", "Interview Scheduled", "Offer Extended"]

    # Create columns for each stage
    cols = st.columns(len(stages))

    for col_idx, stage in enumerate(stages):
        with cols[col_idx]:
            st.subheader(stage)
            stage_jobs = [j for j in jobs if j.pipeline_stage == stage]
            st.caption(f"{len(stage_jobs)} jobs")

            for job in stage_jobs:
                with st.container(border=True):
                    st.markdown(f"**{job.title}**")
                    st.caption(f"{job.company} · {job.location}")
                    st.markdown(job.description_summary)

                    if job.salary_range:
                        st.caption(f"💰 {job.salary_range}")

                    st.caption(f"Posted {job.posted_date}")

                    button_key = f"job_{job.job_id}"
                    if st.button("Full Details", key=button_key):
                        st.markdown(job.description_full)

    # Summary stats
    st.subheader("Pipeline Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Jobs", len(jobs))
    with col2:
        st.markdown("**By Stage**")
        for stage in stages:
            count = len([j for j in jobs if j.pipeline_stage == stage])
            st.caption(f"{stage}: {count}")
    with col3:
        if jobs:
            # Simple estimate: assume "X days ago" format
            oldest_days = 12  # Placeholder
            st.metric("Days Since Oldest", oldest_days)
