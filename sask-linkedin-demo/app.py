"""
LinkedIn Engagement App — SASK LLC Demo

A Streamlit application demonstrating AI-driven content and engagement
capabilities using mock data for public GitHub deployment.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Standalone package: put this app folder on sys.path so the subpackages import cleanly.
_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

try:
    import streamlit as st
except ImportError:
    st = None

from components.header import render_header, render_footer
from components.trending_posts import render_trending_posts_tab
from components.my_posts import render_my_posts_tab
from components.chatbot import render_chatbot_tab
from components.job_pipeline import render_job_pipeline_tab


def init_streamlit_config():
    """Initialize Streamlit page configuration."""
    if st is None:
        return

    st.set_page_config(
        page_title="LinkedIn Engagement App",
        page_icon="💼",
        layout="wide",
        initial_sidebar_state="collapsed",
    )


def init_session_state():
    """Initialize session state variables."""
    if st is None:
        return

    # Chatbot state
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "message_count" not in st.session_state:
        st.session_state.message_count = 0

    # Post expansions
    if "expanded_posts" not in st.session_state:
        st.session_state.expanded_posts = {}
    if "expanded_comments" not in st.session_state:
        st.session_state.expanded_comments = {}

    # Job pipeline filters
    if "job_stage_filter" not in st.session_state:
        st.session_state.job_stage_filter = None


def main():
    """Main app entry point."""
    if st is None:
        print("ERROR: Streamlit is not installed. Install with: pip install streamlit")
        return

    # Initialize config and session
    init_streamlit_config()
    init_session_state()

    # Render header
    render_header()

    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "Trending Posts",
        "My Posts",
        "AI Chatbot",
        "Job Pipeline"
    ])

    # Render each tab
    with tab1:
        render_trending_posts_tab()

    with tab2:
        render_my_posts_tab()

    with tab3:
        render_chatbot_tab()

    with tab4:
        render_job_pipeline_tab()

    # Render footer
    render_footer()


main()
