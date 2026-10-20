"""Trending Posts tab component."""

try:
    import streamlit as st
except ImportError:
    st = None

from fixtures.posts import TRENDING_POSTS


def render_trending_posts_tab():
    """Render trending posts tab."""
    if st is None:
        return

    st.warning(
        "⚠️ **Sample Data — Demonstration Only**: All posts, authors, and engagement "
        "metrics are fictional."
    )

    st.subheader("Trending in Property Management")

    for post in TRENDING_POSTS:
        with st.container(border=True):
            # Author info
            col1, col2 = st.columns([0.1, 0.9])
            with col1:
                st.markdown(f"**{post.author_name[:2].upper()}**")
            with col2:
                st.markdown(
                    f"**{post.author_name}** · {post.author_title} @ {post.author_company}"
                )
                st.caption(post.post_date)

            # Post body
            st.markdown(post.post_body)

            # Engagement metrics
            col_l, col_c, col_s = st.columns(3)
            with col_l:
                st.markdown(f"👍 {post.likes}")
            with col_c:
                st.markdown(f"💬 {post.comments}")
            with col_s:
                st.markdown(f"🔄 {post.shares}")

            # AI Reply Draft button
            button_key = f"trending_reply_{post.post_id}"
            if st.button("View AI Reply Draft", key=button_key):
                st.info(
                    f"**AI-Suggested Reply (Example)**\n\n{post.ai_reply_draft}"
                )
