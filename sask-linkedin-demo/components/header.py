"""Header and footer components."""

try:
    import streamlit as st
except ImportError:
    st = None


def render_header():
    """Render app header with branding and disclaimer."""
    if st is None:
        return

    st.markdown(
        """
        <style>
        .header-container {
            text-align: center;
            padding: 20px 0;
            border-bottom: 2px solid #f0f0f0;
        }
        .header-title {
            font-size: 2.5em;
            font-weight: bold;
            color: #1F1F1F;
            margin: 0;
        }
        .header-subtitle {
            font-size: 1.1em;
            color: #666;
            margin: 5px 0 0 0;
        }
        </style>
        <div class="header-container">
            <div class="header-title">LinkedIn Engagement App</div>
            <div class="header-subtitle">SASK LLC — Sample Data Demonstration</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()


def render_footer():
    """Render app footer with disclaimer and links."""
    if st is None:
        return

    st.divider()

    st.markdown(
        """
        <div style="text-align: center; color: #666; font-size: 0.9em; padding: 20px 0;">
            <p>© 2026 SASK LLC | <a href="https://sask-linkedin-demo.streamlit.app/">Website</a> |
            <a href="https://www.linkedin.com/">LinkedIn</a> |
            <a href="https://github.com/">Portfolio</a></p>
            <p style="margin-top: 10px;">
            <strong>Disclaimer:</strong> This is a demonstration application. All data is mock/fictional
            and for demonstration purposes only.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
