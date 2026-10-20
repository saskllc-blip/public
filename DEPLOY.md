# Deploying the SASK Stripe demo to Streamlit Community Cloud (free)

This folder is a complete, standalone Streamlit app. No secrets, no API keys,
no environment variables — the demo is simulation-only by design. Deploy time
is about 5 minutes, and the same steps will work for the chatbot demo later
(one GitHub repo + one Streamlit app per demo).

## What's in the package

- `app.py` — the app (entry point). Plus `catalog.py`, `checkout.py`,
  `models.py`, `store.py`, `webhooks.py`.
- `requirements.txt` — Streamlit only.
- `.streamlit/config.toml` — SASK theme (gold accent).
- `screenshots/` — 8 frames for the Fiverr gig gallery / Upwork portfolio.
- `README.md` — the repo's public readme.

## Step 1 — Create the GitHub repo (Kiran, ~2 minutes)

1. Go to https://github.com/new — name it `sask-stripe-demo`, set it to
   **Public**, no template files. Create.
2. On the empty-repo page choose "uploading an existing file" and drag in
   **all files and folders from this package** (`app.py`, the other `.py`
   files, `requirements.txt`, `README.md`, the `.streamlit` folder, and
   `screenshots/`). Commit them to `main`.
   - Alternative from a terminal: unzip, `cd sask-stripe-demo`,
     `git init && git add . && git commit -m "SASK Stripe demo"`,
     `git branch -M main`,
     `git remote add origin https://github.com/<your-username>/sask-stripe-demo.git`,
     `git push -u origin main`.

## Step 2 — Connect Streamlit Cloud (Kiran, ~3 minutes)

1. Go to https://share.streamlit.io and sign in with GitHub.
2. **Create app** → pick the `sask-stripe-demo` repo, branch `main`,
   main file path `app.py`.
3. Click **Deploy**. First build takes a minute or two.
4. Your public URL will look like `https://sask-stripe-demo.streamlit.app`.

## Step 3 — Send Buddy the URL

Once it's live, send the URL in chat. Buddy will put it (with the screenshots)
into the Upwork "API Development" portfolio entry and the Fiverr API
Integration gig, per the standing launch plan.

## Notes

- Free tier: the app sleeps after inactivity; the first visit may take
  ~30 seconds to wake. Normal for portfolio demos.
- Do NOT add Stripe keys or secrets — public mode is simulation-only, and
  that is the point of the demo.
- Local check anytime: `streamlit run app.py` inside this folder.
