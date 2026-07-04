from typing import Dict, List, Optional
from typing_extensions import TypedDict


class ResearchState(TypedDict):
    topic: str

    subtasks: List[str]

    raw_research: Dict[str, str]
    sources: Dict[str, List[str]]

    analyzed_insights: Dict[str, str]

    draft_report: str
    revision_count: int

    claims: List[str]                        # was missing
    claim_verdicts: Dict[str, str]           # was missing
    fact_check_report: str                   # was duplicated — now once
    fact_check_passed: bool

    approved: bool
    human_feedback: str

    rejection_count: int 

    final_report: str