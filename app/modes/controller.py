"""Mode controller.

OFFLINE  - nothing leaves the device. All detection + local AI keep working.
HYBRID   - private text stays local; only a domain name may go to online reputation tools.
ONLINE   - like hybrid, plus tools that accept a full URL (e.g. Safe Browsing) may be used.

AUTO picks OFFLINE without internet, HYBRID with internet (privacy-first).
MANUAL lets the user choose, but we never pretend: if the chosen mode needs internet that
is gone, we fall back to OFFLINE and say so.
"""
from typing import Dict

from app.modes import mode_state, network_monitor


def resolve_mode() -> Dict:
    connected = network_monitor.internet_available()
    pref = mode_state.get_preference()
    requested = "auto" if pref == "auto" else mode_state.get_manual_mode()
    note = ""
    fallback = False

    if pref == "auto":
        effective = "hybrid" if connected else "offline"
        note = ("Internet available: hybrid protection (private content stays local)."
                if connected else "No internet: fully local protection is active.")
    else:
        effective = requested
        if effective in ("online", "hybrid") and not connected:
            effective, fallback = "offline", True
            note = f"{requested.upper()} selected but there is no internet. Local protection remains active (OFFLINE FALLBACK)."
        elif effective == "offline":
            note = "Offline mode: nothing is sent to the internet."
        elif effective == "hybrid":
            note = "Hybrid mode: only domain names may be checked online."
        else:
            note = "Online mode: URLs/domains may be checked by online tools."

    return {
        "preference": pref,
        "requested": requested,
        "effective": effective,
        "network": "connected" if connected else "disconnected",
        "fallback": fallback,
        "available_modes": ["offline"] + (["hybrid", "online"] if connected else []),
        "simulated_offline": network_monitor.is_forced_offline(),
        "note": note,
    }
