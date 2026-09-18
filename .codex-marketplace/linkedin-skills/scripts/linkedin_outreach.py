#!/usr/bin/env python3
"""
LinkedIn New Connection Personalized Outreach Generator
For Aaleen Mirza / Hireomatic

Generates hyper-personalized outreach messages for new connections based on:
1. Their profile (Headline, Role, Company, and Focus Areas)
2. Whether they have posted any job openings recently

Template:
Hi [FirstName], great to connect!
I noticed your experience as [Role/Headline] at [Company], with a strong focus on [Focus Area].
[If job posted: I also noticed you recently posted about hiring for a [JobRole]!]
I thought I’d reach out because Hireomatic can help HR teams automate candidate screening
and first-round interviews, while making the overall hiring process faster and more efficient.

🎁 Special offer for first-time users: 
✅ 1 Month FREE 
✅ Up to 100 AI interviews 
✅ Use it for your active hiring requirements 
✅ No long-term commitment to get started

Would you be open to a 15-minute demo? I’d be happy to show you how Hireomatic can fit into your recruitment workflow.

📧 aaleen@technest.ventures
🔗 www.hireomatic.com

Usage:
    python scripts/linkedin_outreach.py --name "Dheeraj" --headline "HR Professional and People Process Transformation Specialist"
    python scripts/linkedin_outreach.py --name "Sarah" --headline "Head of Talent Acquisition" --company "Fintech Corp" --job "Senior Backend Engineer"
    python scripts/linkedin_outreach.py --url "https://www.linkedin.com/in/username/"
    python scripts/linkedin_outreach.py --batch connections.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

OUTREACH_DIR = ROOT / "drafts" / "outreach"
OUTREACH_DIR.mkdir(parents=True, exist_ok=True)

# Hiring signal keywords in recent activity
HIRING_KEYWORDS = [
    r"\bwe(?:'re| are) hiring\b",
    r"\bhiring for\b",
    r"\blooking for a\b",
    r"\bopen role\b",
    r"\bopenings?\b",
    r"\bjoin (?:our|the) team\b",
    r"\bapply (?:now|here)\b",
    r"\bjob alert\b",
    r"\bseeking a\b"
]

def extract_first_name(full_name: str) -> str:
    """Extract clean first name, handling titles and prefixes."""
    parts = full_name.strip().split()
    if not parts:
        return "there"
    # Filter out titles like Dr., Mr., etc.
    if parts[0].lower().rstrip(".") in ("dr", "mr", "mrs", "ms", "prof") and len(parts) > 1:
        return parts[1]
    return parts[0]

def analyze_profile_headline(headline: str) -> Dict[str, str]:
    """Parse role and key focus areas from LinkedIn headline."""
    headline = headline.strip()
    
    # Check for common separators: |, -, •, /, at, @
    focus = ""
    role = headline
    
    separators = [" | ", " - ", " • ", " / ", " @ ", " at "]
    for sep in separators:
        if sep in headline:
            parts = headline.split(sep, 1)
            role = parts[0].strip()
            focus = parts[1].strip()
            break
            
    if not focus:
        # If no separator, extract themes
        if "recruitment" in headline.lower() or "talent" in headline.lower():
            focus = "recruitment and talent acquisition"
        elif "hr" in headline.lower():
            focus = "HR transformation and people processes"
        elif "engineer" in headline.lower() or "tech" in headline.lower():
            focus = "engineering leadership and technical hiring"
        else:
            focus = "scaling teams and operational excellence"

    return {"role": role, "focus": focus}

def detect_hiring_signal(text: str) -> Optional[str]:
    """Check text for recent job posting signals and extract role if found."""
    if not text:
        return None
    for pattern in HIRING_KEYWORDS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Try to grab the role phrase following the match
            start = match.end()
            snippet = text[start:start+60].strip()
            role_match = re.search(r"^[:\- ]*([A-Za-z0-9 ]+?)(?:\.|\n|,|!|\?|$)", snippet)
            if role_match and len(role_match.group(1).strip()) > 3:
                return role_match.group(1).strip()
            return "new team members"
    return None

def generate_outreach_message(
    name: str,
    headline: str,
    company: Optional[str] = None,
    focus: Optional[str] = None,
    job_posted: Optional[str] = None,
) -> str:
    """Generate the personalized outreach message following Aaleen's exact structure."""
    first_name = extract_first_name(name)
    analysis = analyze_profile_headline(headline)
    role = analysis["role"]
    focus_area = focus if focus else analysis["focus"]
    
    # Build personalized observation
    company_phrase = f" at {company}" if company else ""
    
    if job_posted:
        observation = (
            f"I noticed your experience as an {role}{company_phrase}, with a strong focus on {focus_area}. "
            f"I also saw that you recently posted about hiring for a {job_posted}!"
        )
    else:
        observation = (
            f"I noticed your experience as an {role}{company_phrase}, with a strong focus on {focus_area}."
        )

    message = f"""Hi {first_name}, great to connect!
{observation} I thought I’d reach out because Hireomatic can help HR teams automate candidate screening and first-round interviews, while making the overall hiring process faster and more efficient.

🎁 Special offer for first-time users: 
✅ 1 Month FREE 
✅ Up to 100 AI interviews 
✅ Use it for your active hiring requirements 
✅ No long-term commitment to get started

Would you be open to a 15-minute demo? I’d be happy to show you how Hireomatic can fit into your recruitment workflow.

📧 aaleen@technest.ventures
🔗 www.hireomatic.com"""

    return message

def fetch_profile_via_apify(profile_url: str) -> Dict[str, Any]:
    """Fetch LinkedIn profile details via Apify if token is present."""
    from lib import ApifyClient
    token = os.getenv("APIFY_TOKEN")
    if not token:
        return {}
    
    client = ApifyClient(token=token)
    # Use Apify actor if available or fall back
    try:
        # Check user's recent comments or posts for hiring signals
        recent_comments = client.fetch_user_recent_comments(profile_url)
        return {"recent_comments": recent_comments}
    except Exception as e:
        print(f"Apify profile fetch note: {e}")
        return {}

def save_outreach_draft(name: str, message: str, meta: Dict[str, Any]) -> Path:
    """Save outreach draft to drafts/outreach directory."""
    clean_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name).lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = OUTREACH_DIR / f"outreach_{clean_name}_{timestamp}.md"
    
    content = f"""# Personalized Outreach — {name}
Date: {datetime.now().isoformat()}
Recipient: {name}
Headline: {meta.get('headline', '')}
Company: {meta.get('company', '')}
Recent Job Detected: {meta.get('job_posted', 'None')}

---

{message}
"""
    filepath.write_text(content, encoding="utf-8")
    return filepath

def main():
    parser = argparse.ArgumentParser(description="Generate Personalized LinkedIn Connection Outreach for Hireomatic")
    parser.add_argument("--name", help="Connection's full or first name")
    parser.add_argument("--headline", help="Connection's LinkedIn headline or job title")
    parser.add_argument("--company", help="Connection's current company (optional)")
    parser.add_argument("--focus", help="Specific focus area / expertise to highlight (optional)")
    parser.add_argument("--job", help="Title of recently posted job opening (optional)")
    parser.add_argument("--url", help="LinkedIn profile URL (optional)")
    parser.add_argument("--batch", help="Path to JSON file containing a list of connections to process")
    parser.add_argument("--text", help="Pasted snippet of their profile or recent post")
    args = parser.parse_args()

    print("=" * 68)
    print("  HIREOMATIC — NEW CONNECTION PERSONALIZED OUTREACH ENGINE")
    print("  Sender: Aaleen Mirza (aaleen@technest.ventures)")
    print("=" * 68)

    if args.batch:
        batch_path = Path(args.batch)
        if not batch_path.exists():
            print(f"Error: Batch file {args.batch} not found.")
            return 1
        with open(batch_path, "r", encoding="utf-8") as f:
            connections = json.load(f)
            
        print(f"\nProcessing {len(connections)} connections from {args.batch}...\n")
        for i, item in enumerate(connections, 1):
            name = item.get("name", "Connection")
            headline = item.get("headline", "HR and People Operations")
            company = item.get("company")
            job = item.get("job_posted") or item.get("job")
            
            msg = generate_outreach_message(
                name=name,
                headline=headline,
                company=company,
                focus=item.get("focus"),
                job_posted=job
            )
            filepath = save_outreach_draft(name, msg, item)
            print(f"[{i}/{len(connections)}] Drafted for {name} -> {filepath.name}")
        print(f"\nAll outreach drafts saved in: {OUTREACH_DIR}")
        return 0

    # Single connection mode
    name = args.name or "there"
    headline = args.headline or ""
    company = args.company
    job_posted = args.job

    # If pasted text provided, inspect for hiring signals
    if args.text and not job_posted:
        job_posted = detect_hiring_signal(args.text)
        if job_posted:
            print(f"Detected recent hiring signal from text: '{job_posted}'")

    if not args.name and not args.headline and not args.url:
        print("\nInteractive Quick Outreach Drafter:")
        name = input("Connection Name (e.g. Dheeraj): ").strip() or "there"
        headline = input("Headline / Role (e.g. HR Professional and People Process Transformation Specialist): ").strip()
        company = input("Company (optional, e.g. TechCorp): ").strip() or None
        job_posted = input("Did they recently post a job? (Leave blank or enter role, e.g. Senior Backend Engineer): ").strip() or None

    msg = generate_outreach_message(
        name=name,
        headline=headline or "HR Professional and People Operations Specialist",
        company=company,
        focus=args.focus,
        job_posted=job_posted
    )

    meta = {
        "headline": headline,
        "company": company,
        "job_posted": job_posted,
        "url": args.url
    }
    saved_path = save_outreach_draft(name, msg, meta)

    print("\n" + "-" * 50)
    print("PERSONALIZED OUTREACH MESSAGE PREVIEW:")
    print("-" * 50 + "\n")
    print(msg)
    print("\n" + "-" * 50)
    print(f"Draft saved to: {saved_path}")
    print("Ready to copy-paste or review before sending!\n")

if __name__ == "__main__":
    main()
