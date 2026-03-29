import re
import json
import os
from openai import OpenAI

# Load .env for local development (no-op if file doesn't exist)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# API key: .env / env var (local) → Streamlit secrets (cloud)
def _get_api_key():
    key = os.environ.get("NVIDIA_API_KEY")
    if key:
        return key
    try:
        import streamlit as st
        return st.secrets["NVIDIA_API_KEY"]
    except Exception:
        return ""

_client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=_get_api_key()
)

_SYSTEM_PROMPT = """You are a precise business card data extraction expert handling cards from India, USA, and worldwide.
Given OCR text from a single business card, return ONLY a valid JSON object with exactly these keys:
Name, Title, Company, Email, Mobile, Phone, Address, City, State, Zip, Country, Website

=== EXTRACTION RULES ===

NAME:
- The individual person's full name ONLY (e.g. "Rajesh Kumar", "Priya Sharma", "Joshua Del Rio", "Philip J. Grasso")
- Include professional credentials: "Ph.D.", "P.E.", "MBA", "IAS", "Jr.", "Sr." etc.
- NEVER include '@', ':', 'http', 'www', digits, or URLs in the Name field
- NEVER use lines starting with labels like "Email:", "Phone:", "Tel:", "Fax:", "Web:", "Mobile:"
- A name is 2–5 words, all alphabetic (may include '.', '-', spaces)
- Do NOT put company name here — company is usually the largest/boldest text or appears first on the card
- If no clear human name exists, return ""

TITLE:
- The person's job title / position / designation
- Examples: "Sales Engineer", "Managing Director", "DGM – Sales & Marketing", "Head of Operations",
  "Vice President – Projects", "Assistant General Manager", "Senior Executive – BD"
- Include department if part of the title (e.g. "Manager, Automation & Drives")
- Do NOT truncate — capture the full title as written on the card

COMPANY:
- Full organization name (e.g. "Parijat Controlware Pvt. Ltd.", "TOSHIBA", "Siemens India Ltd.", "KEYENCE CORP OF AMERICA")
- Company names typically appear first and/or most prominently on the card, often in ALL CAPS or large bold text
- Do NOT include address or contact information here

EMAIL:
- PREFER personal/direct email over generic (info@, sales@, contact@, admin@, support@)
- Must contain '@' and look like a valid email address
- If only a generic email exists, use it

MOBILE:
- The number explicitly labeled "Mobile", "Cell", "M:", "Mob:", "Cell:" on the card
- CRITICAL: Must have at least 10 digits. A 5 or 6 digit number is a ZIP/PIN code — NEVER use it here.
- For Indian mobile: 10-digit starting with 6–9, format as "+91 XXXXX XXXXX"
- For US: format as "+1 XXX-XXX-XXXX"
- If no number is explicitly labeled as mobile/cell, return ""

PHONE:
- The number explicitly labeled "Phone", "Tel", "T:", "D:", "Direct", "Office", "Landline", "P:" on the card
- CRITICAL: Must have at least 10 digits. A 5 or 6 digit number is a ZIP/PIN code — NEVER use it here.
- For Indian landline: format as "0XX-XXXXXXXX" or "+91-XX-XXXXXXXX"
- For US: format as "(XXX) XXX-XXXX" or "+1 XXX-XXX-XXXX"
- If the card has only one phone number with no label, put it here and leave Mobile empty
- Do NOT include Fax numbers unless it is the only number on the card
- Fix obvious OCR errors in digits

ADDRESS:
- Street / building / flat / plot address ONLY — no city, state, or PIN/ZIP
- Indian format: "Flat 204, Anand Nagar" or "Plot 15, MIDC Industrial Area, Phase II" or "B-204, Kalani Nagar"
- US format: "1500 Post Oak Blvd, Suite 200"
- Include floor/suite/unit if present
- If only P.O. Box exists, use that

CITY:
- City name only (e.g. "Mumbai", "Pune", "Hyderabad", "Houston", "The Woodlands")

STATE:
- For India: full state name preferred (e.g. "Maharashtra", "Gujarat", "Telangana", "Karnataka")
  OR common abbreviation (MH, GJ, TS, KA) if that is what the card shows
- For USA: 2-letter code (TX, CA, GA, etc.)
- Other countries: province/state as shown

ZIP:
- US ZIP: 5-digit or 9-digit (e.g. "77387", "77387-1234")
- Indian PIN code: exactly 6 digits (e.g. "411001", "400072")
- Other: postal code as shown on the card
- NEVER put a ZIP/PIN code in the Mobile or Phone field

COUNTRY:
- If US state code (TX, CA, etc.) present and country not stated → "USA"
- If Indian state name / PIN code (6 digits) / Indian city present and country not stated → "India"
- If country is explicitly stated on the card, use that
- Leave blank only if genuinely ambiguous

WEBSITE:
- Company website, clean format (e.g. "parijatcontrolware.com", "keyence.com", "siemens.com")
- Keep Indian domains as-is: "example.co.in", "example.in"
- Do NOT derive website from email domain unless it is explicitly shown as a URL on the card
- Remove "www." prefix unless it is needed for clarity

=== OUTPUT FORMAT ===
Return ONLY the JSON object. No explanation, no markdown fences, no extra text.
Use "" for any field genuinely not found on the card."""


def _extract_with_llm(text: str) -> dict:
    completion = _client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Extract contact information from this business card OCR text:\n\n{text}"}
        ],
        temperature=0.0,
        top_p=1,
        max_tokens=512,
        stream=False
    )
    raw = completion.choices[0].message.content.strip()

    # Strip markdown code fences if model includes them
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

    return json.loads(raw)


def _extract_with_regex(text: str) -> dict:
    """Regex fallback when LLM API is unavailable."""
    data = {k: '' for k in ['Name', 'Title', 'Company', 'Email', 'Mobile', 'Phone',
                             'Address', 'City', 'State', 'Zip', 'Country', 'Website']}

    emails = re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', text)
    # Prefer personal email (not generic prefix)
    generic = {'info', 'sales', 'contact', 'admin', 'support', 'orders', 'hello', 'mail'}
    personal = [e for e in emails if e.split('@')[0].lower() not in generic]
    data['Email'] = (personal[0] if personal else emails[0]).strip() if emails else ''

    # Phone/Mobile: only accept numbers with at least 10 digits (never ZIP/PIN)
    # Indian 10-digit mobiles (start with 6–9) → Mobile; everything else → Phone
    stripped = re.sub(r'\s', '', text)
    indian_mobiles = re.findall(r'(?:\+91[\s\-]?)?[6-9]\d{9}', stripped)
    if indian_mobiles:
        num = re.sub(r'\D', '', indian_mobiles[0])
        num = num[-10:]  # last 10 digits
        data['Mobile'] = f"+91 {num[:5]} {num[5:]}"

    # Look for labeled phone numbers (Tel, Phone, Direct, T:, D:, P:)
    mobile_match = re.search(
        r'(?:mob(?:ile)?|cell)[:\s.]*(\+?[\d][\d\s.\-()]{9,}\d)', text, re.IGNORECASE)
    phone_match  = re.search(
        r'(?:tel(?:ephone)?|ph(?:one)?|direct|office|t[:\s]|d[:\s]|p[:\s])[:\s.]*(\+?[\d][\d\s.\-()]{9,}\d)',
        text, re.IGNORECASE)

    if mobile_match and not data['Mobile']:
        candidate = re.sub(r'\s+', ' ', mobile_match.group(1)).strip()
        if len(re.sub(r'\D', '', candidate)) >= 10:
            data['Mobile'] = candidate

    if phone_match:
        candidate = re.sub(r'\s+', ' ', phone_match.group(1)).strip()
        if len(re.sub(r'\D', '', candidate)) >= 10:
            data['Phone'] = candidate

    # If no labeled phone found, pick first unlabeled number with ≥10 digits
    if not data['Phone']:
        all_phones = re.findall(r'(\+?[\d][\d\s.\-()]{9,}\d)', text)
        for ph in all_phones:
            digits = re.sub(r'\D', '', ph)
            if len(digits) >= 10:
                # Skip if it's already captured as Mobile
                if digits[-10:] not in re.sub(r'\D', '', data.get('Mobile', '')):
                    data['Phone'] = re.sub(r'\s+', ' ', ph).strip()
                    break

    # Match US ZIP (5-digit / 9-digit) or Indian PIN code (6 digits)
    zips = re.findall(r'\b\d{6}\b|\b\d{5}(?:-\d{4})?\b', text)
    if zips:
        data['Zip'] = zips[0]

    urls = re.findall(r'(?:https?://)?(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/\S*)?', text)
    if emails:
        dom = emails[0].split('@')[1]
        urls = [u for u in urls if dom not in u and '@' not in u and len(u) > 5]
    for u in urls:
        if 'www' in u or 'http' in u or '.' in u:
            data['Website'] = u.strip()
            break

    address_kw = ['st', 'ave', 'blvd', 'rd', 'dr', 'ln', 'ct', 'way', 'pkwy', 'box', 'floor']
    titles_kw = ['director', 'manager', 'president', 'ceo', 'cto', 'engineer', 'developer',
                 'consultant', 'sales', 'lead', 'vp', 'partner', 'owner', 'founder',
                 'specialist', 'executive', 'purchasing', 'shipping']

    lines = [l.strip() for l in text.split('\n') if l.strip()]
    for line in lines:
        ll = line.lower()
        if not data['Title'] and len(line) < 60 and any(t in ll for t in titles_kw):
            data['Title'] = line
        elif not data['Address'] and re.search(r'\b\d+\b', ll) and any(k in ll for k in address_kw):
            data['Address'] = line

    skip = {data['Email'], data['Phone'], data['Website'], data['Title'], data['Address']}
    for line in lines:
        if line in skip:
            continue
        words = line.split()
        if not data['Name'] and 1 < len(words) <= 5 and not re.search(r'\d', line):
            data['Name'] = line
        elif not data['Company'] and len(words) <= 7:
            data['Company'] = line

    return data


def extract_fields(text: str) -> dict:
    """
    Extract structured contact fields from raw OCR text.
    Uses NVIDIA gpt-oss-120b LLM for accuracy; falls back to regex on error.
    """
    empty = {k: '' for k in ['Name', 'Title', 'Company', 'Email', 'Mobile', 'Phone',
                              'Address', 'City', 'State', 'Zip', 'Country', 'Website']}
    if not text or not text.strip():
        return empty

    try:
        result = _extract_with_llm(text)
        for key in empty:
            val = result.get(key)
            result[key] = str(val).strip() if val else ''
        return result
    except Exception:
        return _extract_with_regex(text)
