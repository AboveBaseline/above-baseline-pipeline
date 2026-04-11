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
def generate_story_drafts():
    """Use OpenAI to find current stories and write Above Baseline drafts."""
    client = OpenAI(api_key=OPENAI_KEY)

    print(f"\n=== Above Baseline Morning Pipeline — {TODAY} ===\n")
    print("Generating story drafts with OpenAI...")

    prompt = f"""You are a scientific editor writing for a CRO-focused drug development intelligence briefing.

Today is {TODAY}.

Your task is to generate 6 HIGH-QUALITY, technically grounded story drafts.

CRITICAL REQUIREMENTS:
- Every story MUST be based on a REAL, verifiable recent development (FDA decision, clinical trial result, company announcement, regulatory guidance, or peer-reviewed publication)
- The source_name must be real (e.g. FDA, NEJM, Nature Biotechnology, company press release)
- The source_url must be a REAL, VALID, WORKING URL
- If you are not confident the URL is real, DO NOT include that story

CONTENT REQUIREMENTS:
- 6–8 sentences per story (NOT 3–4)
- Include specific technical details:
  - drug names
  - company names
  - modality (ADC, mAb, small molecule, etc.)
  - clinical phase or regulatory status
  - endpoints or key findings if applicable
- Explicitly explain WHY this matters for CROs:
  - bioanalysis
  - assay development
  - CMC/manufacturing
  - PK/PD
  - regulatory strategy

STYLE:
- Analytical, not promotional
- No generic summaries
- No vague statements like "this is important"
- Every sentence must add information

CATEGORIES (use exactly one per story):
- Small Molecule
- ADCs
- ADA & Immunogenicity
- PK/PD
- My Picks

OUTPUT FORMAT:
Return ONLY valid JSON array. No markdown. No explanation.

Each object must be:

{{
  "title": "Specific, factual headline (max 15 words)",
  "category": "one of: Small Molecule, ADCs, ADA & Immunogenicity, PK/PD, My Picks",
  "content": "6–8 sentence technically detailed analysis focused on CRO implications",
  "source_name": "Real publication or organization",
  "source_url": "REAL working URL (must not be fabricated)",
  "read_time": "3 min read",
  "date": "{TODAY}"
}}

FAILURE RULE:
If you cannot confidently provide real sources and URLs, return fewer stories instead of fabricating.
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

    content = f"""<p>{story['content']}</p>

<p><strong>Source:</strong> <a href="{story.get('source_url', '#')}" target="_blank" rel="noopener">{story['source_name']} ↗</a></p>"""

    post_data = {
        'post_title':   story['title'],
        'post_content': content,
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
