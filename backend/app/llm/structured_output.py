from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    summary: str = Field(
        description=(
            "A concise recommendation in no more than "
            "2 short sentences."
        )
    )

    reasoning: str = Field(
        description=(
            "Brief reasoning in no more than "
            "3 short sentences."
        )
    )

    key_factors: list[str] = Field(
        description=(
            "Exactly 2 important company-specific factors."
        )
    )

    risk: str = Field(
        description=(
            "The main risk in no more than "
            "2 short sentences."
        )
    )

    action: str = Field(
        description=(
            "One practical next action in one sentence."
        )
    )


class AgentDiscussion(BaseModel):
    agreements: list[str] = Field(
        description=(
            "Important points from other agents that this agent "
            "agrees with. Use an empty list if there are none."
        )
    )

    disagreements: list[str] = Field(
        description=(
            "Specific recommendations or assumptions from other "
            "agents that this agent challenges, with brief reasons. "
            "Use an empty list if there are none."
        )
    )

    additional_insight: str = Field(
        description=(
            "One important consideration that the initial "
            "recommendations did not adequately address."
        )
    )

    revised_position: str = Field(
        description=(
            "State whether the original recommendation is maintained "
            "or changed after reviewing the other agents' opinions. "
            "Explain briefly why."
        )
    )


class BoardroomSynthesis(BaseModel):
    executive_summary: str = Field(
        description=(
            "A concise, balanced summary of the boardroom's "
            "overall recommendation and the reasoning behind it."
        )
    )

    recommended_action: str = Field(
        description=(
            "The primary practical action recommended to the founder."
        )
    )

    agreements: list[str] = Field(
        description=(
            "Important conclusions supported by multiple agents. "
            "Do not claim consensus unless the responses support it."
        )
    )

    disagreements: list[str] = Field(
        description=(
            "Material disagreements that remain unresolved after "
            "the collaborative discussion."
        )
    )

    key_risks: list[str] = Field(
        description=(
            "The most important risks identified by the participating "
            "agents. Do not invent company-specific facts."
        )
    )

    next_steps: list[str] = Field(
        description=(
            "Concrete steps the founder can take to evaluate or "
            "implement the recommendation."
        )
    )

    success_metrics: list[str] = Field(
        description=(
            "Measurable indicators the founder could monitor to "
            "evaluate the outcome. Do not invent baseline values "
            "or claim unverified targets are established facts."
        )
    )

    unresolved_assumptions: list[str] = Field(
        description=(
            "Missing information, uncertain assumptions, or questions "
            "that should be resolved before making the decision."
        )
    )