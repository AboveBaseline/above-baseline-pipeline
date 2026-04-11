# Above Baseline — Automated Morning Pipeline

## How It Works

1. **GitHub Actions** runs `pipeline.py` at 4 AM every day
2. Script uses OpenAI GPT-4o to find and write story drafts
3. Drafts saved as `drafts/YYYY-MM-DD.json` in the repo
4. You open `review_dashboard.html`, load the draft file
5. Edit headlines/content, approve what you want, skip the rest
6. Click **Publish** — approved stories post to WordPress automatically

---

## Setup (One Time)

### Step 1 — Create GitHub Repository

1. Go to github.com → New repository
2. Name it `above-baseline-pipeline`
3. Set to **Private**
4. Upload all files from this folder

### Step 2 — Add GitHub Secrets

In your repo: Settings → Secrets → Actions → New repository secret

Add these four secrets:

| Secret Name | Value |
|---|---|
| `OPENAI_API_KEY` | Your OpenAI API key (sk-...) |
| `WP_URL` | https://slategrey-turtle-183448.hostingersite.com |
| `WP_USERNAME` | jimmy.f.goncalves@gmail.com |
| `WP_PASSWORD` | Your WordPress password |

### Step 3 — Enable GitHub Actions

1. Go to your repo → Actions tab
2. Click "Enable Actions"
3. The workflow will now run automatically at 4 AM Central every day

### Step 4 — Test It

Click Actions → "Above Baseline Morning Pipeline" → "Run workflow"
Watch it run — check the `drafts/` folder for the output JSON file.

---

## Daily Workflow (Your Part)

1. Wake up — drafts were generated at 4 AM automatically
2. Open `review_dashboard.html` in your browser
3. Click "Load draft file" → find today's file in the `drafts/` folder
4. Enter your WordPress URL, username, password once
5. Read each story — click **Edit** to change anything
6. Click **Approve** on the ones you want
7. Click **Publish to Above Baseline**
8. Done — takes 5-10 minutes

---

## File Structure

```
above-baseline-pipeline/
├── .github/
│   └── workflows/
│       └── morning-pipeline.yml   ← GitHub Actions schedule
├── pipeline.py                    ← Main automation script
├── review_dashboard.html          ← Your morning review interface
├── requirements.txt               ← Python dependencies
├── drafts/                        ← Generated draft files (auto-created)
│   └── 2026-04-11.json
└── README.md
```

---

## Troubleshooting

**Drafts not generating:**
- Check GitHub Actions logs (Actions tab → click the run)
- Verify OPENAI_API_KEY secret is set correctly

**Can't publish to WordPress:**
- Make sure your WP password is correct
- Try visiting: https://yoursite.com/xmlrpc.php (should say "XML-RPC server accepts POST requests only")

**Wrong category IDs:**
- In WordPress: Posts → Categories → hover over each category → check the ID in the URL
- Update CATEGORY_IDS in pipeline.py and review_dashboard.html
