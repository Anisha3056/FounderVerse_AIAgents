from dataclasses import dataclass, field
from typing import Any

from app.llm.provider import LLMProvider
from app.database.repositories.company_repository import CompanyRepository
from app.llm.structured_output import AgentResponse, AgentDiscussion


@dataclass
class AgentContext:

    company: dict[str, Any]

    memories: list[dict[str, Any]] = field(
        default_factory=list
    )

    retrieved_information: list[dict[str, Any]] = field(
        default_factory=list
    )


class BaseAgent:

    agent_name: str = "Base Agent"

    role: str = "General business executive"

    goals: list[str] = []

    def __init__(self) -> None:

        self.llm = LLMProvider()

        self.company_repository = CompanyRepository()

    def build_system_prompt(self) -> str:

        goals = "\n".join(
            f"- {goal}"
            for goal in self.goals
        )

        return f"""
You are the {self.agent_name} of a startup.

Your role:
{self.role}

Your goals:
{goals}

You are participating in an AI startup boardroom.

Analyze the founder's question ONLY from your
executive perspective.

Rules:

1. Speak in simple language.
2. Do not invent company numbers.
3. Use the company data provided.
4. Be concise.
5. Give a practical recommendation.
6. Explain the reasoning briefly.
7. Mention the most important risk.
8. Identify exactly two important factors.
9. Give one practical next action.
10. Stay within your executive role.

Keep every response short enough for a boardroom discussion.

Return the response using the provided structured
response schema.
"""

    async def respond(
        self,
        founder_question: str,
        context: AgentContext,
    ) -> AgentResponse:

        prompt = f"""
Company information:

{context.company}


Previous relevant memory:

{context.memories}


Retrieved company information:

{context.retrieved_information}


Founder question:

{founder_question}


Give your executive recommendation.

Keep the response concise.

Remember:

- summary: maximum 2 short sentences
- reasoning: maximum 3 short sentences
- key_factors: exactly 2 items
- risk: maximum 2 short sentences
- action: exactly 1 practical sentence
"""

       
        system_prompt = self.build_system_prompt()

        # First attempt: normal structured generation.
        raw_response = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=prompt,
            max_tokens=1800,
            response_schema=AgentResponse,
        )

        try:
            return AgentResponse.model_validate_json(raw_response)

        except Exception as first_error:
            print(
                f"{self.agent_name} returned invalid structured output. "
                "Retrying this agent once only."
            )
            print(f"First validation error: {first_error}")

        # Second attempt: only the failed agent is called again.
        retry_prompt = prompt + """

IMPORTANT: Your previous response was not valid structured JSON.
Return one complete response matching the required schema.
Keep every field concise. The response must not be cut off.
key_factors must contain exactly two short strings.
Do not include Markdown fences or text outside the JSON object.
"""

        raw_response = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=retry_prompt,
            max_tokens=1800,
            response_schema=AgentResponse,
        )

        try:
            return AgentResponse.model_validate_json(raw_response)

        except Exception as retry_error:
            print(
                f"{self.agent_name} failed structured output "
                "validation after one retry."
            )
            print(f"Retry validation error: {retry_error}")
            print(f"Retry response: {raw_response[:1500]}")

            raise RuntimeError(
                f"{self.agent_name} failed to return valid structured output "
                "after one retry."
            ) from retry_error
            
    async def discuss(
        self,
        founder_question: str,
        original_response: AgentResponse,
        other_responses: list[dict[str, Any]],
        context: AgentContext,
    ) -> AgentDiscussion:
        """
        Let an agent review other executives' original recommendations,
        identify agreements and disagreements, and reconsider its position.
        """

        system_prompt = f"""
You are the {self.agent_name} participating in an AI startup boardroom.

Your executive role:
{self.role}

Your goals:
{chr(10).join(f"- {goal}" for goal in self.goals)}

You have already given an independent recommendation.
Now you must review the recommendations from the other executives.

Rules:
1. Stay within your executive role.
2. Evaluate other recommendations fairly and critically.
3. Agree only when there is a good reason to agree.
4. Disagree respectfully and explain why.
5. Do not invent company data, numbers, or facts.
6. If information is missing, explicitly acknowledge the uncertainty.
7. Do not change your position merely to agree with the majority.
8. You may maintain or change your original recommendation.
9. Identify an important consideration that was previously overlooked.
10. Use simple, concise language.
11. Return valid structured output matching the provided schema.
"""

        user_prompt = f"""
FOUNDER'S QUESTION:
{founder_question}

COMPANY INFORMATION:
{context.company}

YOUR RELEVANT MEMORIES:
{context.memories}

YOUR ORIGINAL INDEPENDENT RECOMMENDATION:
{original_response.model_dump()}

OTHER EXECUTIVES' ORIGINAL RECOMMENDATIONS:
{other_responses}

Review the recommendations and provide your discussion response.

Your response must contain:
- agreements: important points you genuinely agree with
- disagreements: specific points you challenge and why
- additional_insight: one important consideration not adequately addressed
- revised_position: whether you maintain or change your original recommendation, and why

Use empty lists for agreements or disagreements if there are none.
Do not manufacture a disagreement just to fill a field.
Keep every field concise.
"""

        raw_response = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=1200,
            response_schema=AgentDiscussion,
        )

        try:
            return AgentDiscussion.model_validate_json(raw_response)

        except Exception as first_error:
            print(
                f"{self.agent_name} returned invalid discussion output. "
                "Retrying once."
            )
            print(f"First validation error: {first_error}")

        retry_prompt = user_prompt + """

IMPORTANT:
Your previous response did not match the required structured schema.
Return one complete JSON object matching the schema.
Do not include Markdown fences or text outside the JSON object.
Keep all fields concise.
Use empty arrays when there are no genuine agreements or disagreements.
"""

        raw_response = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=retry_prompt,
            max_tokens=1200,
            response_schema=AgentDiscussion,
        )

        try:
            return AgentDiscussion.model_validate_json(raw_response)

        except Exception as retry_error:
            print(
                f"{self.agent_name} failed discussion validation after retry: "
                f"{retry_error}"
            )
            raise RuntimeError(
                f"{self.agent_name} could not produce a valid discussion response."
            ) from retry_error
