"""My Posts tab component."""

try:
    import streamlit as st
except ImportError:
    st = None

from fixtures.posts import MY_POSTS


def render_my_posts_tab():
    """Render my posts tab with engagement summary."""
    if st is None:
        return

    st.warning("⚠️ **Sample Data — Demonstration Only**")

    st.subheader("My Posts")

    total_likes = 0
    total_comments = 0
    total_shares = 0

    for post in MY_POSTS:
        with st.container(border=True):
            st.markdown(post.post_body)

            col_l, col_c, col_s = st.columns(3)
            with col_l:
                st.markdown(f"👍 {post.likes}")
                total_likes += post.likes
            with col_c:
                st.markdown(f"💬 {post.comments}")
                total_comments += post.comments
            with col_s:
                st.markdown(f"🔄 {post.shares}")
                total_shares += post.shares

            # Comments section
            expand_key = f"expand_comments_{post.post_id}"
            if st.checkbox("View comments", key=expand_key):
                for comment in post.comments_list[:3]:
                    st.markdown(f"**{comment.commenter_name}**")
                    st.markdown(comment.comment_body)
                    st.caption(comment.comment_timestamp)

                    reply_key = f"reply_{post.post_id}_{comment.commenter_name}"
                    if st.button("AI Reply Draft", key=reply_key):
                        st.info(
                            f"**AI-Suggested Reply (Example)**\n\n{comment.ai_reply_draft}"
                        )
                    st.divider()

    # Summary card
    st.subheader("Engagement Summary")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Likes", total_likes)
    with col2:
        st.metric("Total Comments", total_comments)
    with col3:
        st.metric("Total Shares", total_shares)
    with col4:
        avg_rate = (
            (total_likes + total_comments + total_shares) / len(MY_POSTS)
            if MY_POSTS
            else 0
        )
        st.metric("Avg Engagement", f"{avg_rate:.1f}")
