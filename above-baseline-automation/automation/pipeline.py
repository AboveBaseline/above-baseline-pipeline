"""
Above Baseline — Daily Automation Script
=========================================
Runs every morning at 4 AM via GitHub Actions.

1. Uses OpenAI to search for and write story drafts
2. Saves drafts as JSON for your review
3. Posts approved stories to WordPress via XML-RPC

Setup:
  pip install openai requests python-dotenv

Environment variables (set in GitHub Secrets):
  OPENAI_API_KEY
  WP_URL
  WP_USERNAME
  WP_PASSWORD
  NOTIFICATION_EMAIL (optional)
"""

import os
import json
import xmlrpc.client
import ssl
import feedparser
from datetime import datetime
from openai import OpenAI

# ─────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────
WP_URL      = os.environ.get('WP_URL', 'https://slategrey-turtle-183448.hostingersite.com')
WP_USER     = os.environ.get('WP_USERNAME', '')
WP_PASS     = os.environ.get('WP_PASSWORD', '')
OPENAI_KEY  = os.environ.get('OPENAI_API_KEY', '')

# WordPress category IDs — match what you created
CATEGORY_IDS = {
    'Small Molecule':       6,
    'ADCs':                 3,
    'ADA & Immunogenicity': 4,
    'PK/PD':                5,
    'My Picks':             7,
}

TOPICS = [
    'antibody-drug conjugates ADC linker payload DAR',
    'anti-drug antibody ADA immunogenicity assay NAb bioanalytical',
    'pharmacokinetics pharmacodynamics PK/PD population modeling NONMEM',
    'small molecule formulation BCS bioavailability solid state',
    'gene therapy AAV manufacturing cell therapy CAR-T',
    'mRNA LNP lipid nanoparticle delivery formulation',
    'FDA EMA regulatory guidance biologics biosimilar drug development',
    'CRO CDMO biotech pharma merger acquisition deal',
]

TODAY = datetime.now().strftime('%B %d, %Y')
DATE_FOR_WP = datetime.now().strftime('%Y-%m-%dT04:00:00')

# ─────────────────────────────────────────
# STEP 1: FIND & WRITE STORY DRAFTS
# ─────────────────────────────────────────
def fetch_real_articles():
    feeds = [
        "https://www.fiercebiotech.com/rss/xml",
        "https://endpts.com/feed/",
        "https://www.biopharmadive.com/feeds/news/",
    ]

    articles = []

    for url in feeds:
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:
            articles.append({
                "title": entry.title,
                "url": entry.link,
                "source": feed.feed.title if "title" in feed.feed else "Unknown"
            })

    return articles[:10]
  
def generate_story_drafts():
    """Use OpenAI to find current stories and write Above Baseline drafts."""  
    articles = fetch_real_articles()
    client = OpenAI(api_key=OPENAI_KEY)

    print(f"\n=== Above Baseline Morning Pipeline — {TODAY} ===\n")
    print("Generating story drafts with OpenAI...")

    prompt = f"""You are a senior scientific editor for Above Baseline, a newsletter written for scientists and project managers at CROs and biotech companies — people working in bioanalysis, CMC, PK/PD, regulatory affairs, and drug development.

Today is {TODAY}.

Below are REAL news articles. Use ONLY these as your sources.

Articles:
{json.dumps(articles, indent=2)}

═══════════════════════════════════════
TASK
═══════════════════════════════════════
Write up to 6 story drafts based ONLY on these articles. If fewer than 6 articles are worth covering, write fewer — quality over quantity.

═══════════════════════════════════════
STRICT RULES
═══════════════════════════════════════
- Do NOT invent facts, data, or quotes
- Do NOT change or fabricate URLs — use the exact URL from the source article
- You may combine two closely related articles into one story if they cover the same event
- If you cannot write a story with real, verifiable details, omit it entirely

═══════════════════════════════════════
FORMAT FOR EACH STORY
═══════════════════════════════════════

Each story must have this exact structure:

TITLE
A sharp, specific headline. Lead with the finding or event, not the company name.
Good: "AAV Integration Event Triggers Clinical Hold, Raises Genotoxicity Questions"
Bad: "REGENXBIO Reports Clinical Hold on AAV Program"

EXCERPT (2 sentences max)
A punchy summary of the finding and why it matters. This is what appears in RSS feeds and email previews. Write it to make a busy scientist stop scrolling.

CONTENT (3 paragraphs)

  Paragraph 1 — The News:
  State the finding or event clearly and specifically. Include any key data points, drug names, mechanisms, or regulatory actions. Do not bury the lead.

  Paragraph 2 — The Context:
  Why does this matter beyond the press release? What does it mean for the field, the science, or the regulatory landscape? Challenge assumptions where warranted.

  Paragraph 3 — The CRO/Industry Implication:
  This is the most important paragraph for our readers. Tailor it to the story's category:
  - Small Molecule: formulation strategy, bioavailability, solid-state considerations, BCS class implications
  - ADCs: linker stability, DAR characterization, bioanalytical assay design, payload PK
  - ADA & Immunogenicity: assay sensitivity, cut point strategy, NAb vs. ADA distinction, regulatory submission implications
  - PK/PD: modeling approaches, study design, biomarker strategy, dose selection implications
  - My Picks / General: what CROs and sponsors should be watching, doing, or questioning as a result of this news

CATEGORY
Pick exactly one: Small Molecule, ADCs, ADA & Immunogenicity, PK/PD, My Picks

═══════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════
Return a JSON array only. No preamble, no markdown fences, no commentary.

[
  {{
    "title": "...",
    "category": "...",
    "excerpt": "...",
    "content": "...",
    "source_name": "...",
    "source_url": "...",
    "read_time": "3 min read",
    "date": "{TODAY}"
  }}
]

FAILURE RULE:
If you cannot confidently cover a story with real sourced details, return fewer stories. An empty array is acceptable. Never fabricate.
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    raw = response.choices[0].message.content.strip()
    raw = raw.replace('```json', '').replace('```', '').strip()

    drafts = json.loads(raw)
    print(f"✓ Generated {len(drafts)} story drafts")
    return drafts


# ─────────────────────────────────────────
# STEP 2: SAVE DRAFTS FOR REVIEW
# ─────────────────────────────────────────
def save_drafts(drafts):
    """Save drafts to JSON file for review dashboard."""
    os.makedirs('drafts', exist_ok=True)
    filename = f"drafts/{datetime.now().strftime('%Y-%m-%d')}.json"

    with open(filename, 'w') as f:
        json.dump({
            'date': TODAY,
            'generated_at': datetime.now().isoformat(),
            'stories': drafts
        }, f, indent=2)
    # ALSO save as latest.json for dashboard auto-load
    with open("drafts/latest.json", 'w') as f:
        json.dump({
            'date': TODAY,
            'generated_at': datetime.now().isoformat(),
            'stories': drafts
        }, f, indent=2)
    print(f"✓ Drafts saved to {filename}")
    return filename


# ─────────────────────────────────────────
# STEP 3: POST TO WORDPRESS VIA XML-RPC
# ─────────────────────────────────────────
def post_to_wordpress(story):
    """Post a single story to WordPress via XML-RPC."""
    xmlrpc_url = f"{WP_URL}/xmlrpc.php"

    # Handle SSL
    context = ssl.create_default_context()
    transport = xmlrpc.client.SafeTransport(context=context)
    server = xmlrpc.client.ServerProxy(xmlrpc_url, transport=transport)

    cat_id = CATEGORY_IDS.get(story['category'], 7)
    
    # Format content: paragraphs split by double newline
    paragraphs = story['content'].strip().split('\n\n')
    formatted = ''.join(f'<p>{p.strip()}</p>\n' for p in paragraphs if p.strip())
    formatted += f'\n<p><strong>Source:</strong> <a href="{story.get("source_url", "#")}" target="_blank" rel="noopener">{story["source_name"]} ↗</a></p>'

    post_data = {
        'post_title':   story['title'],
        'post_content': formatted,
        'post_excerpt': story.get('excerpt', ''),
        'post_status':  'publish',
        'post_type':    'post',
        'terms_names':  {'category': [story['category']]},
        'custom_fields': [
            {'key': '_ab_source_url',  'value': story.get('source_url', '')},
            {'key': '_ab_read_time',   'value': story.get('read_time', '3 min read')},
        ]
    }

    post_id = server.wp.newPost('', WP_USER, WP_PASS, post_data)
    return post_id


def publish_approved_drafts(draft_file=None):
    """Read the draft file and publish all approved stories."""
    if not draft_file:
        draft_file = f"drafts/{datetime.now().strftime('%Y-%m-%d')}.json"

    with open(draft_file) as f:
        data = json.load(f)

    stories = data.get('stories', [])
    approved = [s for s in stories if s.get('approved', False)]

    if not approved:
        print("No approved stories found. Mark stories as approved in the review dashboard first.")
        return

    print(f"\nPublishing {len(approved)} approved stories to WordPress...")

    for story in approved:
        try:
            post_id = post_to_wordpress(story)
            print(f"✓ Posted: {story['title']} (ID: {post_id})")
        except Exception as e:
            print(f"✗ Failed: {story['title']} — {e}")


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'publish':
        # Run with: python pipeline.py publish
        # Publishes approved stories from today's draft file
        draft_file = sys.argv[2] if len(sys.argv) > 2 else None
        publish_approved_drafts(draft_file)
    else:
        # Default: generate drafts
        drafts = generate_story_drafts()
        save_drafts(drafts)
        print("\n=== Done ===")
        print("Review drafts in the dashboard, approve the ones you want,")
        print("then run: python pipeline.py publish")
