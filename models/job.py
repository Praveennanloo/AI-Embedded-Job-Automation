from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Job:

    title: str
    company: str
    location: str
    experience: str
    source: str
    url: str
    skills: List[str]
    posted_date: str
    status: str = "NEW"
    match_score: int = 0
    rejection_reasons: List[str] = field(default_factory=list)
    match_breakdown: Dict[str, Any] = field(default_factory=dict)
