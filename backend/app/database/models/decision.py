from datetime import datetime, timezone
from pydantic import BaseModel, Field


class DecisionCreate(BaseModel):
    company_id: str
    question: str
    decision: str
    explanation: str
    affected_agents: list[str] = Field(default_factory=list)
    boardroom_responses: list[dict] = Field(default_factory=list)


class DecisionState(BaseModel):
    company_id: str
    question: str
    decision: str
    explanation: str
    affected_agents: list[str] = Field(default_factory=list)
    boardroom_responses: list[dict] = Field(default_factory=list)
    simulation_month: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
