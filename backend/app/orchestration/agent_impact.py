import json
import logging

from pydantic import BaseModel

from app.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class AgentImpactResponse(BaseModel):
    affected_agents: list[str]


class AgentImpactClassifier:
    def __init__(self) -> None:
        self.llm = LLMProvider()

    async def identify_affected_agents(
        self,
        question: str,
        boardroom_responses: list[dict],
    ) -> tuple[list[str], str | None]:
        agent_responses = {
            item["agent_name"]: item["response"]
            for item in boardroom_responses
            if isinstance(item, dict)
            and isinstance(item.get("agent_name"), str)
            and isinstance(item.get("response"), dict)
        }

        if not agent_responses:
            return (
                [],
                "Decision recorded, but no boardroom responses were available "
                "to identify affected agents.",
            )

        try:
            raw_result = await self.llm.generate(
                system_prompt=(
                    "You identify which startup executives are materially "
                    "affected by a founder's decision. Select only agents whose "
                    "responsibilities are directly and meaningfully impacted "
                    "by the question. Do not include an agent merely because "
                    "they could offer general advice, and do not select every "
                    "agent by default. Return only names from the provided "
                    "agent list; an empty list is allowed if none are directly "
                    "affected."
                ),
                user_prompt=(
                    f"Founder question:\n{question}\n\n"
                    "Boardroom agent responses (agent name and their analysis):\n"
                    f"{json.dumps(agent_responses, ensure_ascii=True)}\n\n"
                    "Return the names of the agents materially affected by "
                    "this question."
                ),
                max_tokens=500,
                response_schema=AgentImpactResponse,
            )

            json_start = raw_result.find("{")
            if json_start == -1:
                raise ValueError(
                    "Impact classifier response did not contain a JSON object."
                )

            parsed_result, _ = json.JSONDecoder().raw_decode(
                raw_result,
                json_start,
            )
            result = AgentImpactResponse.model_validate(parsed_result)

            available_agents = set(agent_responses)
            invalid_agents = set(result.affected_agents) - available_agents
            if invalid_agents:
                raise ValueError(
                    "Impact classifier returned agents without boardroom "
                    f"responses: {', '.join(sorted(invalid_agents))}."
                )

            if len(result.affected_agents) != len(set(result.affected_agents)):
                raise ValueError(
                    "Impact classifier returned duplicate agent names."
                )

            return result.affected_agents, None
        except Exception:
            logger.exception(
                "Unable to classify affected agents for decision question."
            )
            return (
                [],
                "Decision recorded, but affected agents could not be "
                "identified. Please try again later.",
            )
