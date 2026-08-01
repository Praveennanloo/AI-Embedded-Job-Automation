from dataclasses import dataclass
from typing import List


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
