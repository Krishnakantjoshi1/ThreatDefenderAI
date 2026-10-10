"""Rule-based scam / phishing text analysis (English + Hinglish + Hindi).

Every rule belongs to one of the 7 Honeycomb dimensions:
money, offer, conversation, identity, urgency, credential, link.
A rule fires at most once. Weights are in (0,1]; weak "context only" rules use tiny weights
so ordinary messages (e.g. a genuine OTP notice) stay SAFE.
"""
import re
from typing import Dict, List, Tuple

from app.detectors.url_detector import noisy_or
from app.utils.text_utils import normalize_text

DIMENSIONS = ["money", "offer", "conversation", "identity", "urgency", "credential", "link"]

_BANKS = (r"sbi|hdfc|icici|axis|kotak|pnb|bank of baroda|paytm|phonepe|google ?pay|gpay|amazon|flipkart|paypal|"
          r"netflix|microsoft|apple|irctc|uidai|aadhaar|aadhar|income ?tax|epfo|jio|airtel|bank|upi|wallet|kyc|pan|card|account|sim")
_VERB_ASK = (r"share|send|enter|provide|confirm|submit|tell|give|update|verify|dena|batao|bataiye|bhejo|bhejiye|"
             r"daalo|dalo|batayein|batana|type|reply|forward|read out")
_SECRET = r"otp|cvv|pin|mpin|upi pin|atm pin|password|passcode|card number|expiry date|net ?banking|security code|login (?:id|details|credentials)"

# (dimension, code, label, regex, weight)
_RULES: List[Tuple[str, str, str, str, float]] = [
    # ---------------- URGENCY / PRESSURE ----------------
    ("urgency", "urgent_words", "Creates artificial urgency",
     r"\b(?:urgent(?:ly)?|immediately|right now|asap|last chance|final (?:notice|warning|reminder)|act now|today only|hurry|without delay|within \d+ ?(?:hours?|hrs?|minutes?|mins?))\b", 0.4),
    ("urgency", "threat_consequence", "Threatens account blocking or loss",
     r"\b(?:will be|has been|is being|gets?|shall be|get) (?:permanently )?(?:blocked|suspended|deactivated|closed|terminated|frozen|locked|disabled|cancelled|canceled|expired|seized)\b", 0.5),
    ("urgency", "expires", "Says the offer or account expires",
     r"\b(?:expires?|expiring|expired)\b.{0,25}\b(?:today|soon|tonight|tomorrow|in \d+)\b", 0.35),
    ("urgency", "hinglish_urgency", "Urgency in Hindi/Hinglish",
     r"\b(?:turant|abhi\b|jaldi|foran|aaj hi|aaj raat|24 ghante|band ho (?:jayega|jaega|jayegi|jaegi)|block ho (?:jayega|jaega|jayegi|jaegi)|suspend ho)", 0.4),
    ("urgency", "devanagari_urgency", "Urgency in Hindi script",
     r"(?:तुरंत|अभी|जल्दी|ब्लॉक हो|बंद हो|निलंबित)", 0.4),
    ("urgency", "legal_threat", "Threatens legal action or arrest",
     r"\b(?:legal action|arrest(?:ed)?|warrant|court (?:notice|case)|penalty|fine of|fir (?:will|has)|case (?:has been )?registered)\b", 0.45),

    # ---------------- CREDENTIAL REQUESTS ----------------
    ("credential", "ask_secret", "Asks you to share/enter a secret (OTP, PIN, password, CVV)",
     r"\b(?:" + _VERB_ASK + r")\b.{0,45}\b(?:" + _SECRET + r")\b", 0.8),
    ("credential", "ask_secret_rev", "Asks for an OTP / PIN / password",
     r"\b(?:" + _SECRET + r")\b.{0,25}\b(?:" + _VERB_ASK + r"|required|needed|here|below)\b", 0.6),
    ("credential", "verify_account", "Asks you to verify / update your account details",
     r"\b(?:verify|confirm|validate|update|re-?activate|unlock|restore) (?:your |ur |the )?(?:account|identity|details|kyc|pan|aadhaar|aadhar|card|profile|wallet|bank|information|info)\b", 0.45),
    ("credential", "kyc_scam", "KYC update/expiry pressure (common Indian bank scam)",
     r"\bkyc\b.{0,30}\b(?:update|expire[sd]?|pending|verification|incomplete|suspend|blocked?)\b", 0.5),
    ("credential", "login_prompt", "Asks you to log in or sign in via a link",
     r"\b(?:log ?in|sign ?in)\b.{0,25}\b(?:to (?:continue|avoid|verify|confirm|secure|unlock|claim)|here|now|below)\b", 0.4),
    ("credential", "remote_access", "Asks you to install a remote-access tool or APK",
     r"\b(?:anydesk|teamviewer|quick ?support|rustdesk|ammyy|remote access|install (?:the |this )?(?:apk|app)|download (?:the |this )?apk)\b", 0.65),
    ("credential", "otp_mention", "Mentions an OTP / PIN (context only)",
     r"\b(?:otp|cvv|mpin|upi pin)\b", 0.05),

    # ---------------- OFFER / REWARD BAIT ----------------
    ("offer", "prize", "Claims you won a prize or lottery",
     r"\b(?:you(?:'ve| have)? won|you are (?:the )?(?:lucky )?winner|lucky draw|lottery|jackpot|prize|kbc|lucky winner)\b", 0.5),
    ("offer", "reward", "Promises a reward, cashback or gift",
     r"\b(?:cashback|cash back|reward points?|free gift|gift card|gift voucher|bonus|voucher|redeem|reward)\b", 0.2),
    ("offer", "claim_now", "Pushes you to 'claim' something",
     r"\bclaim (?:your|now|it|the|this)\b|\bclaim\b.{0,20}\b(?:reward|prize|cashback|refund|gift)\b", 0.35),
    ("offer", "congrats", "Congratulations hook", r"\bcongratulations?\b", 0.08),
    ("offer", "hinglish_offer", "Prize/reward language in Hindi/Hinglish",
     r"(?:\binaam\b|\bjeet(?:a|e|i)\b|\bjeeta\b|इनाम|बधाई|जीत(?:ा|े)\b|लॉटरी)", 0.4),
    ("offer", "get_rich", "Unrealistic earning / investment promise",
     r"\b(?:guaranteed (?:returns?|profit)|double your money|sure ?shot|100% (?:profit|returns?|guaranteed)|earn (?:rs\.?|₹)?\s?\d[\d,]*\s?(?:per|a|/)\s?(?:day|daily|hour|week)|work from home|part[- ]time job|daily income|risk[- ]free)\b", 0.5),
    ("offer", "limited_offer", "Limited-time / exclusive offer pressure",
     r"\b(?:limited (?:time )?offer|exclusive offer|special offer|offer (?:ends|valid)|only \d+ (?:left|slots|spots))\b", 0.15),

    # ---------------- MONEY ----------------
    ("money", "ask_payment", "Asks you to pay / transfer money",
     r"\b(?:pay|send|transfer|deposit|remit|share)\b.{0,30}\b(?:money|amount|fee|fees|charges?|payment|rs\.?|rupees|₹|inr|funds)\b", 0.45),
    ("money", "advance_fee", "Asks for a small 'fee' to release something (advance-fee fraud)",
     r"\b(?:processing|registration|clearance|customs|delivery|redelivery|handling|release|activation|insurance|gst|tax) (?:fee|charge|payment|amount)s?\b", 0.55),
    ("money", "upi_qr", "Mentions UPI collect request / QR code payment",
     r"\b(?:collect request|scan (?:the |this )?qr|qr code|upi (?:id|request|collect)|pay via upi)\b", 0.35),
    ("money", "crypto_gift", "Payment through crypto or gift cards",
     r"\b(?:bitcoin|btc|usdt|crypto(?:currency)?|gift cards?|google play card|itunes card)\b", 0.3),
    ("money", "amount", "Mentions a money amount",
     r"(?:₹|rs\.?|inr|\$)\s?\d[\d,]*|\b\d[\d,]*\s?(?:rupees|lakh|crore)\b", 0.12),
    ("money", "refund_hook", "Refund / money-back hook", r"\b(?:refund|money back|reversal|chargeback)\b", 0.15),

    # ---------------- IDENTITY / IMPERSONATION ----------------
    ("identity", "account_alert", "Pretends to be an alert about YOUR bank / account",
     r"\b(?:your|ur|aapka|aapke|aapki)\s+(?:" + _BANKS + r")\b.{0,45}\b(?:blocked|suspended|expire[sd]?|closed|frozen|deactivated|locked|band|block|suspend|compromised|limited|restricted|misused)\b", 0.55),
    ("identity", "authority", "Claims to be a bank, government or police authority",
     r"\b(?:rbi|npci|cbi|income ?tax (?:dept|department|officer)|customs (?:department|officer)|cyber ?(?:cell|crime)|police (?:officer|department|station)|trai|enforcement directorate|narcotics|supreme court|high court)\b", 0.35),
    ("identity", "generic_greeting", "Generic greeting instead of your name",
     r"\b(?:dear (?:customer|user|account ?holder|valued|member|sir/madam|client)|valued customer|respected customer)\b", 0.2),
    ("identity", "support_claim", "Claims to be official support / security team",
     r"\b(?:customer (?:care|support|service)|help ?desk|security team|fraud (?:team|department|prevention)|official (?:notice|team|support)|technical support|tech support)\b", 0.15),
    ("identity", "brand_mention", "Mentions a well-known organisation (context only)",
     r"\b(?:" + _BANKS + r"|fedex|dhl|bluedart|india post|courier)\b", 0.04),

    # ---------------- CONVERSATION / SOCIAL ENGINEERING ----------------
    ("conversation", "family_impersonation", "Pretends to be a relative on a 'new number'",
     r"\b(?:new number|changed my number|lost my phone|phone (?:is )?(?:broken|damaged))\b|\bhi (?:mom|mum|dad|mummy|papa)\b", 0.45),
    ("conversation", "secrecy", "Asks you to keep it secret / not tell anyone",
     r"\b(?:don'?t|do not|dont|never) (?:tell|inform|share this with|call|disclose to) (?:anyone|anybody|family|police|the bank|your bank)\b|\bkeep (?:this )?(?:confidential|secret)\b|\bkisi ko (?:mat|na) (?:batana|batao)\b", 0.5),
    ("conversation", "digital_arrest", "Digital-arrest / parcel-seizure script",
     r"\b(?:digital arrest|parcel (?:contains|seized|detained)|drugs? (?:found|detected)|money laundering|your (?:aadhaar|aadhar|number) (?:is )?(?:linked|misused|used))\b", 0.7),
    ("conversation", "off_platform", "Pushes you to reply / call / move to another app",
     r"\b(?:reply (?:yes|y|1|stop)|whatsapp (?:me|us)|contact (?:us|me|our agent|the agent)|call (?:this|the) number|call back|message (?:us|me) on|join (?:our |my )?(?:telegram|whatsapp) (?:group|channel))\b", 0.3),
    ("conversation", "task_scam", "Task/review job scam wording",
     r"\b(?:like (?:and )?subscribe|youtube (?:videos?|tasks?)|rate (?:products?|hotels?)|complete (?:the |simple )?tasks?|prepaid tasks?)\b", 0.4),
    ("conversation", "emotional_pressure", "Emotional pressure (emergency / hospital / accident)",
     r"\b(?:emergency|hospital|accident|stuck|stranded|in trouble|need help)\b.{0,50}\b(?:money|pay|send|transfer|urgent)\b", 0.35),

    # ---------------- LINK ----------------
    ("link", "click_link", "Tells you to click / tap a link",
     r"\b(?:click|tap|open|visit|follow|press)\b.{0,15}\b(?:link|here|below|url|button)\b", 0.25),
    ("link", "apk_download", "Pushes a file/APK download",
     r"\b(?:download|install)\b.{0,25}\b(?:apk|file|attachment|app|software)\b", 0.3),
]

_COMPILED = [(d, c, l, re.compile(rx, re.IGNORECASE | re.DOTALL), w) for d, c, l, rx, w in _RULES]

# Phrases that turn "share your OTP" into the legitimate "do NOT share your OTP".
_SAFE_NOTICE = re.compile(
    r"(?:do not|don'?t|dont|never|kisi ke saath|kisi se|mat|na)\s+(?:\w+\s+){0,3}?(?:share|tell|give|disclose|batana|batayein|bataye|karein)[^.!\n]{0,60}",
    re.IGNORECASE,
)


def analyze_text(text: str) -> Dict:
    """Return {score, indicators, dimension_scores, legit_notice}."""
    original = normalize_text(text)
    # Remove "never share your OTP" style warnings before searching for requests.
    cleaned = _SAFE_NOTICE.sub(" ", original)
    legit_notice = cleaned != original

    indicators: List[Dict] = []
    for dim, code, label, rx, weight in _COMPILED:
        target = cleaned if dim == "credential" and code.startswith("ask_secret") else original
        m = rx.search(target)
        if m:
            snippet = re.sub(r"\s+", " ", m.group(0)).strip()[:70]
            indicators.append({"code": code, "label": label, "weight": weight, "dimension": dim,
                               "evidence": snippet, "source": "text"})

    dim_scores = {d: 0 for d in DIMENSIONS}
    for d in DIMENSIONS:
        ws = [i["weight"] for i in indicators if i["dimension"] == d]
        dim_scores[d] = int(round(100 * noisy_or(ws)))
    score = int(round(100 * noisy_or([i["weight"] for i in indicators])))
    return {"score": score, "indicators": indicators, "dimension_scores": dim_scores,
            "legit_notice": legit_notice}
