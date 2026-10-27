# LinkedIn Engagement App architecture

This document describes the system as it exists in this folder. Where an older comment or leftover URL disagrees with the product stance, **the standing truth wins**: this is a **code showcase with no live hosted demo, no real LinkedIn integration, and no live link**.

Draw IO source: [`architecture.drawio`](architecture.drawio). Export: [`images/architecture.png`](images/architecture.png).

## Purpose and scope

A Streamlit walkthrough of an engagement workspace: a trending-post feed with canned reply drafts, a “my posts” analytics tab, an FAQ-grounded chatbot with simple guardrails, and a read-only job kanban.

Scope of this folder:

- Four tabs on one page, plus header/footer.
- Deterministic fixtures in `fixtures/`.
- Local keyword retrieval + canned chatbot replies.

Out of scope — and **not present in the running code**:

- A hosted Streamlit Cloud demo (do not treat any `*.streamlit.app` URL as official).
- LinkedIn OAuth, the LinkedIn API, or any LinkedIn SDK.
- HTTP to an LLM (LangChain, OpenAI, Ollama, …).
- Stage moves or an apply flow on the job board.

## Component inventory

| Module | Responsibility |
|--------|----------------|
| `app.py` | Entry point. `init_streamlit_config`, `init_session_state`, `render_header`, four `st.tabs`, `render_footer`. |
| `components/header.py` | Branding + “Sample Data Demonstration” subtitle. |
| `components/trending_posts.py` | Six fictional cards from `fixtures.posts.TRENDING_POSTS`; **View AI Reply Draft** shows static text. |
| `components/my_posts.py` | Four `MY_POSTS` with likes/comments/shares, **View comments**, per-comment **AI Reply Draft**, engagement totals. |
| `components/chatbot.py` | Disclaimer + guardrails expander; `st.chat_input`; 10 messages/session; **Clear Chat**. Calls validators → FAQ retrieval → canned reply. |
| `components/job_pipeline.py` | Four columns (Open → Under Review → Interview Scheduled → Offer Extended). **Full Details** expands canned text. No drag, no apply. |
| `fixtures/posts.py` | `MockPost` / `MockComment` dataclasses; `TRENDING_POSTS` and `MY_POSTS`. **Source of truth for posts.** |
| `fixtures/jobs.py` | `MOCK_JOBS` with `pipeline_stage`. **Source of truth for jobs.** |
| `fixtures/faq.py` | `FAQ_CONTENT` string (property-management themed Q&A). **Source of truth for the bot.** |
| `utils/validators.py` | `validate_message` (1–500 chars); `check_prompt_injection` (substrings `ignore`, `forget`, `bypass`, `jailbreak`). |
| `utils/faq_retrieval.py` | Split `FAQ_CONTENT` on blank lines; keyword overlap; return `top_k` (default 3). |
| `utils/llm_integration.py` | `generate_chatbot_response`: keyword map (`tenant` / `rent` / `maintenance` / `lease` / `security`) or a hash-picked fallback. **No HTTP.** |
| `assets/colors.py` | Brand color constants. **Not imported by the current tabs.** |
| `data/mock_posts.py`, `data/mock_jobs.py`, `data/faq_data.py` | Leftover duplicates. **Not imported.** |

`app.py` initializes `job_stage_filter` and `expanded_posts` / `expanded_comments`; the job tab does not currently filter on that key (stages are always all four columns).

## Data-flow walkthroughs

### Browse trending / my posts

Tab render functions import fixture lists and draw Streamlit containers. **AI Reply Draft** buttons display `ai_reply_draft` strings that shipped in the fixture. Nothing is posted, liked, or sent to LinkedIn.

### Chatbot turn

1. `st.chat_input` while `message_count < 10`.
2. `validate_message` — reject empty / >500 chars.
3. `check_prompt_injection` — reject if a banned substring appears; show the property-management-only error.
4. Else append the user message, `message_count += 1`.
5. `retrieve_faq(prompt, top_k=3)` against `FAQ_CONTENT`.
6. `generate_chatbot_response(prompt, faq_matches)` — local canned text.
7. Append assistant message; `st.rerun()`.
8. At 10 turns: “Demo API limit (10 queries/session) reached.”
9. **Clear Chat** zeros both session keys.

### Job pipeline

`MOCK_JOBS` is grouped by `pipeline_stage` into four columns. Read-only. No writer.

## Data model and where state lives

| Store | Contents | Lifetime |
|-------|----------|----------|
| `fixtures/posts.py` | Frozen `MockPost` / `MockComment` | Source file |
| `fixtures/jobs.py` | Job dataclasses + stage string | Source file |
| `fixtures/faq.py` | One markdown-ish FAQ string | Source file |
| `st.session_state.chat_messages` | `[{role, content}, …]` | Session |
| `st.session_state.message_count` | Integer, cap 10 | Session |
| `st.session_state.expanded_*` | Checkbox/button keys | Session |

No env vars, no `st.secrets`, no disk writes.

## External services and dependencies

- Python 3.9+, Streamlit `>=1.28,<2`.
- **None** of: LinkedIn SDK, OAuth, LangChain, OpenAI, paid search, a hosted Cloud URL that this repo endorses.

`components/header.py` `render_footer` contains leftover HTML hrefs (`sask-linkedin-demo.streamlit.app`, linkedin.com, github.com). Those are **not** an official live demo and must not be copied into the README or the root table.

## Key design decisions and constraints

- **Code showcase, not a product.** The README, root table, and this doc all say there is no live hosted demo.
- **Fixtures over `data/`.** Runtime imports `fixtures.*` only. The `data/` package is a leftover duplicate and should not be treated as canonical.
- **Guardrails are substring heuristics**, not a model firewall. They exist to show the *shape* of a check.
- **Chatbot theme is property-management**, matching the canned FAQ — not LinkedIn’s own help center.
- **All authors, companies, and jobs are fictional** (including “Fictional Employer” on the kanban).

## How to extend it

1. **More posts/jobs/FAQ:** edit `fixtures/*.py` only; do not revive `data/` as a second source of truth.
2. **Wire `assets/colors.py`:** import the constants into the components instead of hard-coded hex in `header.py`.
3. **Job filters:** `job_stage_filter` is already in session; the pipeline tab can honor it.
4. **Do not** add LinkedIn OAuth, a live Cloud URL, or an LLM HTTP client in this public folder. If a future hosted demo is approved, that is a separate product decision — it is not true today.

Run from this folder: `python3 -m pytest . -q` (expect 0 collected unless you add tests).
