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

    prompt = f"""You are the editor of Above Baseline, a drug development news blog for CRO professionals.

Today is {TODAY}.

Write 6 story drafts for today's edition. Cover a mix of these areas:
- ADC development (linker chemistry, DAR, conjugation, clinical data)
- ADA & immunogenicity (assay development, regulatory guidance, NAb testing)
- PK/PD (population modeling, bioanalytical methods, dose optimization)
- Small molecule (formulation, BCS, process development)
- Gene/cell therapy (AAV, CAR-T, manufacturing, safety)
- mRNA/LNPs (delivery, formulation, clinical programs)
- Regulatory (FDA/EMA guidance, IND, BLA, approval decisions)
- Industry (CRO/CDMO deals, M&A, major program updates)

Write from the perspective of a CRO professional. Be neutral and factual. Focus on what developments mean for drug development, manufacturing, and analytical work. No hype, no clickbait.

Return ONLY a valid JSON array. No markdown fences, no preamble. Each object must have:
{{
  "title": "Clear factual headline, max 15 words",
  "category": "one of: Small Molecule, ADCs, ADA & Immunogenicity, PK/PD, My Picks",
  "content": "3-4 sentence post. What happened, what was found, why it matters to CRO/pharma professionals. Include specific details like mechanisms, numbers, or implications.",
  "source_name": "Publication or organization name (e.g. NEJM, FDA.gov, Nature Biotechnology)",
  "source_url": "Realistic URL to the type of source this would come from",
  "read_time": "3 min read",
  "date": "{TODAY}"
}}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
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
