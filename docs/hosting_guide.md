# Hosting the Stage 1 IAA App on Streamlit Community Cloud

Free hosting guide for the blind annotation UI (`streamlit_apps/stage1_app.py`).
Once deployed, both annotators access the same URL with a shared password
and download their committed envelopes for out-of-band submission.

## What gets hosted vs. stays local

| Item | Location |
|---|---|
| Streamlit app (`streamlit_apps/stage1_app.py`) | Streamlit Cloud server |
| 30 trial input data (`streamlit_apps/data/`) | Committed in GitHub repo, served by SCC |
| IAA trial filter (`iaa_pipeline_spec/iaa_8trials.txt`) | Committed — dropdown shows only these 8 |
| Annotator drafts | **Browser session state only** — never written to SCC disk |
| Committed envelopes | Downloaded by annotator, manually uploaded to shared submission folder |
| Shared password | Streamlit Cloud "secrets" (not in git) |

The dropdown shows only the 8 IAA-evaluation trials by design — annotators
shouldn't waste blind-annotation effort on trials outside the stratified
sample. See `iaa_pipeline_spec/iaa_8trials_selection.md` for the rationale.
To work on the remaining 22 trials later (e.g., single-annotator follow-up),
either rename/remove `iaa_8trials.txt` or write a separate phase-2 app
pointed at the full bundle.

Server has no annotator-specific persistence. Refreshing the browser tab
loses unsaved progress. Annotators should periodically "Download draft"
during long sessions.

---

## One-time setup

### 1. Prepare the GitHub repository

```bash
# Verify the bundle is in place
ls streamlit_apps/data/ | wc -l       # expect 30
du -sh streamlit_apps/data/           # expect ~500KB

# Stage and push
git add streamlit_apps/ requirements.txt .streamlit/secrets.toml.example \
        docs/hosting_guide.md .gitignore
git commit -m "Hosted Stage 1 annotation app"
git push origin main
```

The repo can be public OR private. For free private repos, Streamlit
Community Cloud requires you to authorize the SCC GitHub app on your account.

### 2. Create the Streamlit Cloud app

1. Go to https://share.streamlit.io
2. Sign in with GitHub
3. Click **"New app"**
4. Settings:
   - **Repository**: `<your-username>/graphrag-clinical-screening`
   - **Branch**: `main`
   - **Main file path**: `streamlit_apps/stage1_app.py`
   - **App URL (custom subdomain)**: e.g. `nsclc-iaa-stage1`
     (full URL becomes `https://nsclc-iaa-stage1.streamlit.app`)
5. Click **"Advanced settings"** → **Secrets** → paste:
   ```toml
   SHARED_PASSWORD = "your-actual-password-here"
   ```
   Use a password you'll communicate to the other annotator out-of-band
   (e.g. via Signal / encrypted email).
6. Click **"Deploy!"**

Initial deploy takes 2-5 minutes (pip install + container build).

### 3. Verify

Open `https://nsclc-iaa-stage1.streamlit.app` in an incognito window:

1. Should see the password gate
2. Enter the password → main UI loads
3. Sidebar shows 30 trials
4. Pick a trial → criteria form renders
5. No "🤖 LLM Output" tab visible (Stage 1 is blind from-scratch)
6. No "📊 IAA" tab visible (out-of-band IAA computation)

If you see errors, click "Manage app" → check the logs panel.

---

## Annotator workflow

Each annotator (EHJ, DYK) does the following on their own machine:

1. Open `https://nsclc-iaa-stage1.streamlit.app`
2. Enter shared password
3. In the sidebar:
   - Type your annotator ID (initials, e.g. `EHJ`)
   - Pick a trial from the dropdown
4. Work through each criterion's form
5. Click **"💾 Save draft (in session)"** periodically — stores in browser session
6. To resume in a future session, also click **"📥 Download draft"** and keep the file
7. When done with the trial:
   - Click **"🔒 Commit (final)"** (only enabled if no validation errors)
   - Click **"📥 Download committed envelope"**
   - Upload the downloaded JSON to the shared submission folder
     (e.g. `/shared/iaa/submissions/EHJ/NCT03425643_stage1.json`)

To resume work later (browser closed, container restarted, etc.):

1. Open the URL again, authenticate
2. In sidebar, click **"Upload a draft you downloaded earlier"** and pick your saved JSON
3. The form re-populates with your saved values
4. Continue from where you stopped

The app refuses to load an uploaded draft whose `annotator` field doesn't
match the typed annotator ID — this prevents accidentally loading
someone else's file.

---

## IAA computation (out-of-band)

After both annotators have uploaded their committed envelopes to the
shared submission folder, a coordinator (or either annotator) runs:

```bash
python scripts/compute_iaa.py /shared/iaa/submissions/ --trial NCT03425643 --stage 1
```

This is intentionally outside the hosted UI: it ensures the IAA statistic
is computed from final committed work, not from real-time partial state
that could leak between sessions.

*(`scripts/compute_iaa.py` is a follow-up — for now, use the existing
`iaa_pipeline.metrics.compute_stage1_iaa()` from a Python shell.)*

---

## Future stages (2-5)

Each later stage will be a separate Streamlit Cloud deployment with its own
URL. Suggested naming:

| Stage | App file | Suggested URL |
|---|---|---|
| 1 | `streamlit_apps/stage1_app.py` | `nsclc-iaa-stage1.streamlit.app` |
| 2 | `streamlit_apps/stage2_app.py` *(TBD)* | `nsclc-iaa-stage2.streamlit.app` |
| 3 | `streamlit_apps/stage3_app.py` *(TBD)* | `nsclc-iaa-stage3.streamlit.app` |
| 4 | `streamlit_apps/stage4_app.py` *(TBD)* | `nsclc-iaa-stage4.streamlit.app` |
| 5 | `streamlit_apps/stage5_app.py` *(TBD)* | `nsclc-iaa-stage5.streamlit.app` |

Stages 1, 2 are `from_scratch` mode (no LLM access).
Stages 3, 4, 5 are `llm_assisted` (LLM Output tab visible) — annotator
uploads the upstream stage's gold envelope at session start.

---

## Limitations / caveats

- **Ephemeral filesystem**: SCC restarts wipe everything. Annotators must
  download their work; in-progress state lives only in `st.session_state`
  (per-browser-tab).
- **Honor-system identity**: annotator ID is self-declared. Mitigated by
  the upload guard (refuses if the file's `annotator` field doesn't match).
- **Shared password**: not per-user. Sufficient gating for a 2-annotator
  academic project where the URL is communicated privately.
- **Cold-start latency**: first request after inactivity may take 10-30s
  while the container spins up. This is normal for SCC free tier.
- **US-based servers**: all annotation traffic flows through SCC's US
  infrastructure. AACT criteria text is public data and annotator metadata
  is methodological — no PHI involved.

---

## Pulling the app down

If you want to stop hosting (e.g. after the IAA experiment is done):

1. Streamlit Cloud dashboard → **"Settings"** → **"Delete app"**
2. The committed envelopes in your shared submission folder are unaffected
3. The GitHub repo and code remain — you can redeploy any time
