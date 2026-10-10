from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    content: str
    kind: Optional[str] = None          # auto | url | text
    sender: Optional[str] = None
    online: bool = True                 # False = fast local-only scan (used by the browser extension)


class PageScanRequest(BaseModel):
    url: str
    title: Optional[str] = ""
    text: Optional[str] = ""
    has_password_field: bool = False
    forms: List[Dict[str, Any]] = Field(default_factory=list)
    hidden_iframes: int = 0
    online: bool = False


class FileScanRequest(BaseModel):
    filename: str
    content_b64: str


class ExplainRequest(BaseModel):
    scan_id: int
    content: Optional[str] = None       # original text stays on this device; used only for local AI
    lang: str = "en"                    # en | hinglish
    use_ai: bool = True


class SettingsUpdate(BaseModel):
    mode_preference: Optional[str] = None
    manual_mode: Optional[str] = None
    force_offline: Optional[bool] = None
    store_preview: Optional[bool] = None
    protection_enabled: Optional[bool] = None


class ProtectionUpdate(BaseModel):
    enabled: bool
