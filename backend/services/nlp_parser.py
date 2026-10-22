"""
backend/services/nlp_parser.py
Natural Language "Quick-Add" Expense Parser for PocketWise.

Designed specifically for college viva demonstration:
Clean, rule-based NLP combining:
1. Regular Expressions (RegEx) for numerical amount extraction & payment mode detection
2. Keyword & synonym dictionary mapping for 8 universal expense categories
3. Stopword filtering & text normalization for merchant / title extraction

Works 100% offline with zero external dependencies.
"""

import re
from datetime import date

# ---------------------------------------------------------------------------
# 1. KEYWORD DICTIONARIES FOR THE 8 UNIVERSAL EXPENSE CATEGORIES
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS = {
    "Groceries & Dining": [
        "swiggy", "zomato", "blinkit", "zepto", "instamart", "grocery", "groceries",
        "supermarket", "dining", "restaurant", "cafe", "starbucks", "lunch", "dinner",
        "breakfast", "pizza", "burger", "food", "meal", "snacks", "coffee", "tea",
        "bakery", "fruits", "vegetables", "milk", "dairy", "dmart", "bigbasket",
        "mcdonalds", "kfc", "subway", "dominos", "biryani", "canteen", "treat"
    ],
    "Utilities & Bills (Electricity, Wi-Fi, Phone)": [
        "wifi", "wi-fi", "broadband", "fiber", "electricity", "electric", "power",
        "water", "bill", "phone", "mobile", "recharge", "jio", "airtel", "vi", "bsnl",
        "cylinder", "lpg", "gas", "dth", "tatasky", "utility", "broadband bill",
        "electricity bill", "water bill"
    ],
    "Commute & Fuel": [
        "petrol", "fuel", "diesel", "cng", "uber", "ola", "rapido", "metro",
        "bus", "train", "auto", "cab", "taxi", "flight", "toll", "fastag",
        "parking", "fare", "commute", "transport", "railway", "irctc"
    ],
    "Housing & Rent": [
        "rent", "flat", "apartment", "landlord", "brokerage", "maintenance",
        "society", "lease", "house", "room", "plumbing", "carpenter", "repair",
        "home maintenance", "flat rent", "room rent"
    ],
    "Healthcare & Fitness": [
        "gym", "cult", "fitness", "workout", "trainer", "doctor", "hospital",
        "medicine", "pharmacy", "medical", "apollo", "1mg", "clinic", "test",
        "lab", "checkup", "dentist", "consultation", "tablets", "pharma"
    ],
    "Shopping & Lifestyle": [
        "amazon", "flipkart", "myntra", "shopping", "clothes", "apparel", "dress",
        "shirt", "pants", "shoes", "zara", "h&m", "lifestyle", "mall", "electronics",
        "headphones", "watch", "perfume", "salon", "haircut", "spa", "cosmetics",
        "skincare", "gadget", "laptop", "mouse", "keyboard"
    ],
    "Investments & Savings": [
        "sip", "mutual fund", "mutual funds", "stocks", "shares", "zerodha", "groww",
        "invest", "investment", "savings", "ppf", "fd", "fixed deposit", "gold",
        "crypto", "nps", "equity", "index fund", "recurring deposit"
    ],
    "Miscellaneous": [
        "misc", "miscellaneous", "stationery", "gift", "courier", "fee", "penalty",
        "donation", "subscription", "netflix", "spotify", "youtube", "prime", "charity"
    ]
}

# ---------------------------------------------------------------------------
# 2. PAYMENT MODE REGEX PATTERNS
# ---------------------------------------------------------------------------
PAYMENT_PATTERNS = [
    ("Net Banking", re.compile(r"\b(net\s*banking|netbanking|neft|rtgs|imps|bank\s*transfer|online\s*banking)\b", re.IGNORECASE)),
    ("UPI", re.compile(r"\b(upi|gpay|google\s*pay|phonepe|paytm|bhim|paytm\s*upi|scan|qr)\b", re.IGNORECASE)),
    ("Card", re.compile(r"\b(card|debit\s*card|credit\s*card|visa|mastercard|amex)\b", re.IGNORECASE)),
    ("Cash", re.compile(r"\b(cash|cod|cash\s*on\s*delivery)\b", re.IGNORECASE)),
]

# Common English connective stopwords to strip when extracting the title/merchant name
STOPWORDS = {
    "spent", "spend", "paying", "paid", "for", "on", "via", "using", "through",
    "by", "in", "to", "at", "with", "bought", "purchased", "purchase", "from",
    "rs", "inr", "rupees", "rupee", "bucks", "today", "yesterday", "cost", "worth",
    "amount", "of", "a", "an", "the", "my", "our", "and"
}


def parse_natural_language_expense(query_text: str, available_categories: list) -> dict:
    """
    Parses a natural language expense query and extracts:
    - Amount (float)
    - Payment Mode (UPI, Cash, Card, Net Banking)
    - Category ID & Name (matched from available categories)
    - Title / Merchant Name (string)
    - Expense Date (ISO format string)

    Example query: 'Spent 650 on Swiggy via UPI'
    Returns:
    {
        'success': True,
        'amount': 650.0,
        'payment_mode': 'UPI',
        'category_name': 'Groceries & Dining',
        'category_id': 2,
        'title': 'Swiggy',
        'expense_date': '2026-10-20',
        'notes': "Logged via AI Quick Add: 'Spent 650 on Swiggy via UPI'"
    }
    """
    if not query_text or not query_text.strip():
        return {"success": False, "message": "Query text cannot be empty."}

    original_query = query_text.strip()
    working_text = original_query.lower()

    # -----------------------------------------------------------------------
    # Step 1: Detect and Extract Payment Mode
    # -----------------------------------------------------------------------
    detected_mode = "UPI"  # Default in India if not specified
    matched_mode_span = None

    for mode_name, pattern in PAYMENT_PATTERNS:
        match = pattern.search(working_text)
        if match:
            detected_mode = mode_name
            matched_mode_span = match.span()
            # Remove the payment mode token from working text to prevent pollution
            working_text = working_text[:matched_mode_span[0]] + " " + working_text[matched_mode_span[1]:]
            break

    # -----------------------------------------------------------------------
    # Step 2: Extract Numerical Amount
    # Supports: ₹650, Rs 1800, 1,450, 500.50, "paid 650", "650 rs"
    # -----------------------------------------------------------------------
    amount = None
    
    # Pattern A: Preceded by currency sign (₹ or Rs or INR)
    curr_match = re.search(r"(?:₹|rs\.?|inr)\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]{1,2})?)", working_text, re.IGNORECASE)
    if curr_match:
        raw_val = curr_match.group(1).replace(",", "")
        try:
            amount = float(raw_val)
            working_text = working_text[:curr_match.start()] + " " + working_text[curr_match.end():]
        except ValueError:
            pass

    # Pattern B: Plain number with optional suffix or prefix
    if amount is None:
        num_match = re.search(r"\b([0-9]+(?:,[0-9]+)*(?:\.[0-9]{1,2})?)\s*(?:rs|inr|rupees|bucks)?\b", working_text, re.IGNORECASE)
        if num_match:
            raw_val = num_match.group(1).replace(",", "")
            try:
                amount = float(raw_val)
                working_text = working_text[:num_match.start()] + " " + working_text[num_match.end():]
            except ValueError:
                pass

    if amount is None or amount <= 0:
        return {
            "success": False,
            "message": "Could not identify an expense amount. Please include a number like '650' or '₹1800'."
        }

    # -----------------------------------------------------------------------
    # Step 3: Match Category using Keyword Scoring
    # -----------------------------------------------------------------------
    scores = {cat_name: 0 for cat_name in CATEGORY_KEYWORDS}
    
    # Check words and n-grams in original query
    clean_lower_query = original_query.lower()
    for cat_name, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            # Word boundary regex search
            if re.search(r"\b" + re.escape(kw) + r"\b", clean_lower_query):
                # Longer keywords give higher match confidence
                scores[cat_name] += 10 + len(kw)

    best_category_name = max(scores, key=scores.get)
    # If no keyword matched, fallback to Miscellaneous
    if scores[best_category_name] == 0:
        best_category_name = "Miscellaneous"

    # Match best category name against the user's available categories in DB
    matched_category_id = None
    matched_full_name = best_category_name

    for cat in available_categories:
        c_name = cat.get("category_name", "")
        # Exact match or prefix match (e.g. "Utilities & Bills" matches "Utilities & Bills (Electricity, Wi-Fi, Phone)")
        if c_name == best_category_name or best_category_name in c_name or c_name in best_category_name:
            matched_category_id = cat.get("category_id")
            matched_full_name = c_name
            break

    # If still not found, pick first category as fallback
    if matched_category_id is None and available_categories:
        matched_category_id = available_categories[0].get("category_id")
        matched_full_name = available_categories[0].get("category_name")

    # -----------------------------------------------------------------------
    # Step 4: Extract Title / Merchant Name
    # Remove stopwords, symbols, and remaining payment tokens
    # -----------------------------------------------------------------------
    # Split working text into tokens
    raw_tokens = re.findall(r"[a-zA-Z0-9\-]+", working_text)
    meaningful_tokens = [t for t in raw_tokens if t.lower() not in STOPWORDS]

    if meaningful_tokens:
        extracted_title = " ".join(meaningful_tokens).strip()
        # Title case first letter of each word (e.g. "Swiggy", "Electricity Bill")
        extracted_title = " ".join([w.capitalize() for w in extracted_title.split()])
    else:
        # If all words were stopwords, fallback to category name
        extracted_title = matched_full_name.split("(")[0].strip()

    # Cap length to 80 chars
    extracted_title = extracted_title[:80]

    return {
        "success": True,
        "amount": round(amount, 2),
        "payment_mode": detected_mode,
        "category_id": matched_category_id,
        "category_name": matched_full_name,
        "title": extracted_title,
        "expense_date": date.today().isoformat(),
        "notes": f"Quick Add: '{original_query}'"
    }
