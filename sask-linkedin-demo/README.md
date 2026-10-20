# LinkedIn Engagement App — SASK SW Services Demo

A Streamlit portfolio demo built by **SASK SW Services** (SASK LLC, Saratoga,
CA), demonstrating AI-driven content and engagement tooling. The application is
entirely mock-data driven — no external APIs, no keys, nothing leaves the app.

## Features

- **Trending Posts** — browse mock LinkedIn posts with AI-suggested reply drafts
- **My Posts** — portfolio posts with engagement metrics and comment management
- **AI Chatbot** — FAQ-grounded assistant with prompt-injection guardrails
- **Job Pipeline** — kanban-style job tracker with four pipeline stages

## Tech stack

- Streamlit 1.28+, Python 3.9+
- Deterministic mock fixtures (posts, jobs, FAQ) — no paid APIs

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy

This folder is published in the SASK public showcase repository
(github.com/saskllc-blip/public). On Streamlit Community Cloud, create an app
from that repository, branch `main`, with main file path
`sask-linkedin-demo/app.py`. No secrets are required.

---
© 2026 SASK LLC — SW Services · Public portfolio demonstration.
AI tools for speed, human review and automated testing for reliability.
