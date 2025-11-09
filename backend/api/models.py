# models.py
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class AskPayload(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = {}

class ManipulationReport(BaseModel):
    market_id: Optional[str] = None
    riskScore: Optional[float] = None
    flags: List[str] = []
    explanation: Optional[str] = None
    details: Optional[Dict[str, Any]] = {}
    confidence: Optional[float] = None
