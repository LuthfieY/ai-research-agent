from typing import TypedDict, List, Annotated
import operator

class ResearchResult(TypedDict):
    source: str
    content: str

class AgentState(TypedDict):
    task: str                                               # The user's initial question
    content: Annotated[List[ResearchResult], operator.add]  # A list of research results gather so far
    draft: str                                              # The current version of the report
    critique: str                                           # Feedback from the critique agent
    revision_number: int                                    # The current revision number
    last_action: str                                        # To store the critic's decision (RESEARCH_MORE, REWRITE, APPROVE)