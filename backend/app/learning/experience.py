from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class Experience(BaseModel):
    company_id: str

    agent_name: str

    state: dict[str, Any]

    action: dict[str, Any]

    reward: float = 0.0

    next_state: dict[str, Any] | None = None

    founder_feedback: dict[str, Any] = Field(
        default_factory=dict
    )

    outcome: dict[str, Any] = Field(
        default_factory=dict
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )