 # utils.py
import json, uuid, time
from datetime import datetime
from typing import Optional, Dict, Any

def utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

def short_id() -> str:
    return str(uuid.uuid4())

def now_ms() -> int:
    return int(time.time() * 1000)

def extract_first_json_block(text: Optional[str]) -> Optional[Dict[str, Any]]:
    """Return first {...} JSON parsed from text (or None)."""
    if not text or not isinstance(text, str):
        return None
    text = text.strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start:end+1])
    except Exception:
        return None
