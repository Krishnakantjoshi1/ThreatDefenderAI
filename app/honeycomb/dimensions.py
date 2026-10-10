"""The seven Honeycomb dimensions: display metadata."""
DIMENSIONS = ["money", "offer", "conversation", "identity", "urgency", "credential", "link"]

META = {
    "money":        {"label": "Money",        "hint": "Asks you to pay or transfer money"},
    "offer":        {"label": "Offer",        "hint": "Reward, prize or too-good-to-be-true bait"},
    "conversation": {"label": "Conversation", "hint": "Social-engineering conversation tricks"},
    "identity":     {"label": "Identity",     "hint": "Pretends to be a bank, brand or authority"},
    "urgency":      {"label": "Urgency",      "hint": "Pressure: act now or lose access"},
    "credential":   {"label": "Credential",   "hint": "Wants OTP, PIN, password or login"},
    "link":         {"label": "Link",         "hint": "Dangerous link, file or page"},
}
