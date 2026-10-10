"""Static file analysis. Files are NEVER executed or opened - only inspected as bytes."""
import re
from typing import Dict, List

from app.detectors.url_detector import noisy_or
from app.intelligence import threat_database as db
from app.utils.file_utils import safe_filename
from app.utils.hashing import sha256_bytes

_EXEC_EXT = {"exe", "scr", "bat", "cmd", "com", "pif", "msi", "jar", "vbs", "vbe", "js", "jse", "wsf", "ps1", "hta", "lnk", "apk", "dll", "reg"}
_DOC_EXT = {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "jpg", "jpeg", "png", "gif", "mp3", "mp4", "csv", "rtf"}
_MACRO_EXT = {"docm", "xlsm", "pptm", "dotm", "xlam"}
_ARCHIVE_EXT = {"zip", "rar", "7z", "iso", "img", "gz", "tar"}
_WEB_EXT = {"html", "htm", "svg", "xhtml", "shtml"}

_SCRIPT_PATTERNS = [
    (re.compile(rb"powershell(?:\.exe)?\s+.{0,40}-(?:enc|encodedcommand|e)\b", re.I), "Encoded PowerShell command", 0.7),
    (re.compile(rb"eval\s*\(\s*(?:atob|unescape|String\.fromCharCode)", re.I), "Obfuscated JavaScript (eval + decode)", 0.6),
    (re.compile(rb"document\.write\s*\(\s*unescape", re.I), "Obfuscated JavaScript (document.write + unescape)", 0.5),
    (re.compile(rb"(?:cmd(?:\.exe)?\s*/c|WScript\.Shell|CreateObject\s*\(\s*[\"']WScript)", re.I), "Script launches system commands", 0.55),
    (re.compile(rb"<input[^>]+type\s*=\s*[\"']?password", re.I), "Contains a password input form", 0.35),
    (re.compile(rb"/(?:JavaScript|JS|Launch|OpenAction)\b"), "PDF with active content (JavaScript/Launch)", 0.35),
    (re.compile(rb"AutoOpen|Document_Open|Workbook_Open|Shell\s*\(", re.I), "Macro auto-run keywords", 0.4),
]


def _ind(code, label, weight, dimension="link", evidence=""):
    return {"code": code, "label": label, "weight": weight, "dimension": dimension,
            "evidence": evidence, "source": "file"}


def analyze_file(filename: str, data: bytes) -> Dict:
    name = safe_filename(filename)
    lower = name.lower()
    parts = lower.split(".")
    ext = parts[-1] if len(parts) > 1 else ""
    sha = sha256_bytes(data)
    ind: List[Dict] = []

    if db.is_known_bad_hash(sha):
        ind.append(_ind("known_bad_hash", "File hash matches a known malicious sample", 0.99, "link", sha[:16]))

    if ext in _EXEC_EXT:
        ind.append(_ind("executable_ext", f"Executable/script file type (.{ext})", 0.55, "link", "." + ext))
    elif ext in _MACRO_EXT:
        ind.append(_ind("macro_doc", f"Macro-enabled Office document (.{ext})", 0.45, "link", "." + ext))
    elif ext in _WEB_EXT:
        ind.append(_ind("html_attachment", "HTML file (often used to host fake login pages)", 0.3, "credential", "." + ext))
    elif ext in _ARCHIVE_EXT:
        ind.append(_ind("archive", "Archive file can hide malware", 0.15, "link", "." + ext))

    if len(parts) >= 3 and parts[-1] in _EXEC_EXT and parts[-2] in (_DOC_EXT | _WEB_EXT):
        ind.append(_ind("double_extension", f"Double extension (.{parts[-2]}.{parts[-1]}) disguises an executable", 0.85, "identity", name))
    if re.search(r"\s{3,}\.", name) or "\u202e" in filename:
        ind.append(_ind("hidden_ext", "Filename uses spacing/unicode tricks to hide its real type", 0.6, "identity", name))

    head = data[:4]
    if head[:2] == b"MZ" and ext not in _EXEC_EXT:
        ind.append(_ind("disguised_exe", "File is a Windows executable disguised as another type", 0.85, "identity", f".{ext or 'none'}"))
    if head == b"\x7fELF" and ext not in ("", "so", "bin", "elf", "o"):
        ind.append(_ind("disguised_elf", "File is a Linux executable disguised as another type", 0.7, "identity", f".{ext}"))

    text_like = ext in _WEB_EXT | {"js", "vbs", "ps1", "bat", "cmd", "hta", "txt", "pdf", "docm", "xlsm", "svg", "wsf", "jse"}
    scan_bytes = data[:400_000]
    if text_like or head[:2] != b"MZ":
        for rx, label, w in _SCRIPT_PATTERNS:
            m = rx.search(scan_bytes)
            if m:
                ind.append(_ind("content_" + re.sub(r"\W+", "_", label.lower())[:30], label, w, "credential" if "password" in label else "link",
                                m.group(0)[:50].decode("utf-8", "ignore")))

    if len(data) == 0:
        ind.append(_ind("empty_file", "File is empty", 0.05, "link", "0 bytes"))

    return {"filename": name, "extension": ext, "size": len(data), "sha256": sha,
            "score": int(round(100 * noisy_or([i["weight"] for i in ind]))), "indicators": ind,
            "text_preview": _text_for_analysis(ext, scan_bytes)}


def _text_for_analysis(ext: str, data: bytes) -> str:
    """Decoded text of text-like files so the text detector can also read phishing wording."""
    if ext in _WEB_EXT | {"txt", "csv", "rtf", "js", "ps1", "bat", "cmd", "vbs", "hta"}:
        txt = data.decode("utf-8", "ignore")
        txt = re.sub(r"(?is)<(script|style).*?</\1>", " ", txt)
        txt = re.sub(r"<[^>]+>", " ", txt)
        return re.sub(r"\s+", " ", txt)[:6000]
    return ""
