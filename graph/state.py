from typing import Dict
from typing import List
from typing_extensions import TypedDict


class ResearchState(TypedDict):
    topic: str

    subtasks: List[str]

    raw_research: Dict[str, str]
    sources: Dict[str, List[str]]

    analyzed_insights: Dict[str, str]

    draft_report: str
    revision_count: int

    fact_check_report: str
    fact_check_passed: bool
    
    claims: List[str]
    fact_check_report: str

    approved: bool
    human_feedback: str

    final_report: str