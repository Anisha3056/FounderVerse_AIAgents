import asyncio
import time
from typing import Any

from app.agents.base_agent import AgentContext
from app.agents.finance_agent import FinanceAgent
from app.agents.marketing_agent import MarketingAgent
from app.agents.sales_agent import SalesAgent
from app.agents.cto_agent import CTOAgent
from app.agents.legal_agent import LegalAgent

from app.database.repositories.decision_repository import DecisionRepository
from app.memory.memory_manager import MemoryManager
from app.memory.retrieval import MemoryRetriever

from app.llm.provider import LLMProvider
from app.llm.structured_output import (
    AgentResponse,
    AgentDiscussion,
    BoardroomSynthesis,
)


class BoardroomOrchestrator:
    def __init__(self) -> None:
        self.agents = [
            FinanceAgent(),
            MarketingAgent(),
            SalesAgent(),
            CTOAgent(),
            LegalAgent(),
        ]

        self.decision_repository = DecisionRepository()
        self.memory_manager = MemoryManager()
        self.memory_retriever = MemoryRetriever()

        # Used to generate the final boardroom synthesis.
        self.llm = LLMProvider()

    @staticmethod
    def _fallback_response(agent_name: str) -> dict[str, Any]:
        """Return an explicit failure result without inventing advice."""

        return {
            "agent_name": agent_name,
            "error": (
                "This agent could not produce a valid response. "
                "Please try consulting this agent again later."
            ),
            "response": {
                "summary": "Recommendation temporarily unavailable.",
                "reasoning": (
                    "The agent could not produce a valid structured response."
                ),
                "key_factors": [
                    "Valid response unavailable",
                    "Assessment incomplete",
                ],
                "risk": (
                    "Do not make a decision based on this agent's "
                    "unavailable assessment."
                ),
                "action": "Retry this agent before relying on its advice.",
            },
        }

    async def _get_agent_context(
        self,
        agent: Any,
        founder_question: str,
        company: dict[str, Any],
        previous_decisions: list[dict[str, Any]],
        company_id: str,
    ) -> AgentContext:
        """Build the relevant memory context for an individual agent."""

        agent_memories = []

        # Include the agent's recommendations from recent founder decisions.
        for decision in previous_decisions:
            previous_response = next(
                (
                    item.get("response", {})
                    for item in decision.get("boardroom_responses", [])
                    if item.get("agent_name") == agent.agent_name
                ),
                None,
            )

            if previous_response is None:
                continue

            agent_memories.append(
                {
                    "memory_type": "previous_decision",
                    "content": {
                        "previous_question": decision.get("question", ""),
                        "founder_decision": decision.get("decision", ""),
                        "founder_explanation": decision.get("explanation", ""),
                        "agent_recommendation": previous_response,
                        "simulation_month": decision.get("simulation_month"),
                    },
                }
            )

        # Retrieve semantically relevant memories for this agent.
        stored_memories = self.memory_retriever.retrieve_relevant_memories(
            agent_name=agent.agent_name,
            company_id=company_id,
            query=founder_question,
            limit=5,
        )

        print(
            f"[SEMANTIC MEMORY] {agent.agent_name}: "
            f"{len(stored_memories)} relevant memories retrieved"
        )

        for memory in stored_memories:
            agent_memories.append(
                {
                    "memory_type": memory.get("memory_type", "consultation"),
                    "content": memory.get("content", ""),
                    "metadata": memory.get("metadata", {}),
                }
            )

        return AgentContext(
            company=company,
            memories=agent_memories,
            retrieved_information=[],
        )

    async def _consult_one(
        self,
        agent: Any,
        founder_question: str,
        context: AgentContext,
    ) -> tuple[Any, AgentContext, AgentResponse | None, Exception | None]:
        """Run one independent consultation and preserve its outcome."""

        try:
            response = await agent.respond(
                founder_question=founder_question,
                context=context,
            )
            return agent, context, response, None

        except Exception as exc:
            print(
                f"[BOARDROOM] {agent.agent_name} initial consultation failed: {exc}"
            )
            return agent, context, None, exc

    async def _discuss_one(
        self,
        agent: Any,
        original_response: AgentResponse,
        context: AgentContext,
        founder_question: str,
        other_responses: list[dict[str, Any]],
    ) -> tuple[str, dict[str, Any] | None, str | None]:
        """Run one discussion round for a successful agent."""

        try:
            discussion = await agent.discuss(
                founder_question=founder_question,
                original_response=original_response,
                other_responses=other_responses,
                context=context,
            )

            return agent.agent_name, discussion.model_dump(), None

        except Exception as exc:
            print(f"[BOARDROOM] {agent.agent_name} discussion failed: {exc}")

            return (
                agent.agent_name,
                None,
                "This agent could not complete its discussion round.",
            )

    async def _synthesize(
        self,
        founder_question: str,
        company: dict[str, Any],
        responses: list[dict[str, Any]],
        discussions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate a final synthesis grounded in the actual boardroom output."""

        successful_responses = [
            item for item in responses if "error" not in item
        ]

        successful_discussions = [
            item for item in discussions if "error" not in item
        ]

        if not successful_responses:
            return {
                "status": "unavailable",
                "error": (
                    "The boardroom could not generate any valid initial "
                    "recommendations, so a final synthesis was not produced."
                ),
            }

        system_prompt = """
You are the Boardroom Synthesis Coordinator for a startup advisory system.

Your responsibility is to consolidate the independent opinions and discussion
of Finance, Marketing, Sales, Technology, and Legal executives.

Rules:
1. Base your synthesis only on the company information, original responses,
   and discussion responses supplied to you.
2. Do not invent company data, facts, financial figures, or outcomes.
3. Distinguish genuine agreement from disagreement.
4. Do not claim consensus merely because several agents agree on one point.
5. Preserve important minority opinions and unresolved disagreements.
6. Consider the consequences of the recommendation across business functions.
7. Recommend practical next steps.
8. Suggest useful success metrics without inventing current baselines.
9. State material information gaps and assumptions.
10. If an agent failed, do not attribute opinions to that agent.
11. Use clear, concise language suitable for a startup founder.
12. Return structured output matching the supplied schema.
"""

        user_prompt = f"""
FOUNDER'S QUESTION:
{founder_question}

COMPANY INFORMATION:
{company}

ORIGINAL INDEPENDENT AGENT RECOMMENDATIONS:
{successful_responses}

AGENT DISCUSSION RESULTS:
{successful_discussions}

Create the final boardroom synthesis.

Include:
- executive_summary
- recommended_action
- agreements
- disagreements
- key_risks
- next_steps
- success_metrics
- unresolved_assumptions

Only report conclusions supported by the supplied information.
If the agents disagree, explain the material disagreement rather than hiding it.
If discussion results are missing, base the synthesis on the available evidence
and acknowledge the limitations where relevant.
"""

        try:
            raw_response = await self.llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=2200,
                response_schema=BoardroomSynthesis,
            )

            synthesis = BoardroomSynthesis.model_validate_json(raw_response)

            return {
                "status": "success",
                **synthesis.model_dump(),
            }

        except Exception as exc:
            print(f"[BOARDROOM] Final synthesis failed: {exc}")

            return {
                "status": "unavailable",
                "error": (
                    "The agents' responses are available, but the final "
                    "synthesis could not be generated. Please try again."
                ),
            }

    async def consult(
        self,
        founder_question: str,
        company: dict[str, Any],
        mode: str = "collaborative",
    ) -> dict[str, Any]:
        """
        Run the collaborative boardroom workflow:

        Stage 1: Independent agent recommendations.
        Stage 2: Agent-to-agent discussion.
        Stage 3: Final boardroom synthesis.
        """

        consultation_started = time.perf_counter()
        company_id = str(company["_id"])

        # Retrieve recent decisions once for the entire consultation.
        previous_decisions = self.decision_repository.get_by_company(
            company_id
        )[:5]

        # Context preparation is measured as a backend stage.
        context_started = time.perf_counter()
        # Prepare a separate memory context for every agent.
        context_results = await asyncio.gather(
            *[
                self._get_agent_context(
                    agent=agent,
                    founder_question=founder_question,
                    company=company,
                    previous_decisions=previous_decisions,
                    company_id=company_id,
                )
                for agent in self.agents
            ],
            return_exceptions=True,
        )

        agent_contexts = {}

        for agent, result in zip(self.agents, context_results):
            if isinstance(result, Exception):
                print(
                    f"[BOARDROOM] Could not prepare context for "
                    f"{agent.agent_name}: {result}"
                )
                agent_contexts[agent.agent_name] = None
            else:
                agent_contexts[agent.agent_name] = result

        context_preparation_ms = (time.perf_counter() - context_started) * 1000

        # ---------------------------------------------------------
        # STAGE 1: Independent recommendations, run concurrently.
        # ---------------------------------------------------------
        initial_stage_started = time.perf_counter()
        initial_tasks = []

        for agent in self.agents:
            context = agent_contexts[agent.agent_name]

            if context is None:
                initial_tasks.append(None)
                continue

            initial_tasks.append(
                asyncio.create_task(
                    self._consult_one(
                        agent=agent,
                        founder_question=founder_question,
                        context=context,
                    )
                )
            )

        initial_results = await asyncio.gather(
            *[
                task if task is not None else asyncio.sleep(0, result=None)
                for task in initial_tasks
            ],
            return_exceptions=True,
        )

        responses = []
        successful_agents = []

        for agent, result in zip(self.agents, initial_results):
            if result is None or isinstance(result, Exception):
                responses.append(self._fallback_response(agent.agent_name))
                continue

            result_agent, context, response, error = result

            if error is not None or response is None:
                responses.append(self._fallback_response(agent.agent_name))
                continue

            response_data = response.model_dump()

            # Preserve the original response format used by the frontend.
            responses.append(
                {
                    "agent_name": result_agent.agent_name,
                    "response": response_data,
                }
            )

            successful_agents.append(
                {
                    "agent": result_agent,
                    "context": context,
                    "response": response,
                    "response_data": response_data,
                }
            )

            # Save the original consultation to memory.
            # This does not overwrite or replace the agent's original opinion.
            memory_content = (
                f"Founder question: {founder_question}\n"
                f"Recommendation: {response_data['summary']}\n"
                f"Reasoning: {response_data['reasoning']}\n"
                f"Main risk: {response_data['risk']}\n"
                f"Next action: {response_data['action']}"
            )

            try:
                self.memory_manager.save_memory(
                    agent_name=result_agent.agent_name,
                    company_id=company_id,
                    memory_type="consultation",
                    content=memory_content,
                    metadata={
                        "question": founder_question,
                        "simulation_month": company.get("current_month", 1),
                    },
                )
            except Exception as exc:
                # A memory write failure should not erase a valid recommendation.
                print(
                    f"[MEMORY] Could not save {result_agent.agent_name}'s "
                    f"consultation: {exc}"
                )

        initial_opinions_ms = (time.perf_counter() - initial_stage_started) * 1000

        # Individual mode and the first phase of Both Experiences stop here.
        # This is the API-cost saving: no discussion or synthesis calls occur.
        if mode in {"individual", "both"}:
            return {
                "question": founder_question,
                "mode": mode,
                "responses": responses,
                "discussions": [],
                "synthesis": None,
                "performance": {
                    "context_preparation_ms": round(context_preparation_ms, 2),
                    "initial_opinions_ms": round(initial_opinions_ms, 2),
                    "total_backend_ms": round((time.perf_counter() - consultation_started) * 1000, 2),
                    "measurement_scope": "Backend orchestration wall-clock time; excludes HTTP routing/authentication and frontend rendering.",
                },
            }

        # ---------------------------------------------------------
        # STAGE 2: Each successful agent reviews the others.
        # ---------------------------------------------------------
        discussion_started = time.perf_counter()
        discussions = []

        if successful_agents:
            discussion_tasks = []

            for item in successful_agents:
                current_agent = item["agent"]

                other_responses = [
                    {
                        "agent_name": other["agent"].agent_name,
                        "response": other["response_data"],
                    }
                    for other in successful_agents
                    if other["agent"].agent_name != current_agent.agent_name
                ]

                discussion_tasks.append(
                    self._discuss_one(
                        agent=current_agent,
                        original_response=item["response"],
                        context=item["context"],
                        founder_question=founder_question,
                        other_responses=other_responses,
                    )
                )

            discussion_results = await asyncio.gather(
                *discussion_tasks,
                return_exceptions=True,
            )

            for item, result in zip(successful_agents, discussion_results):
                agent_name = item["agent"].agent_name

                if isinstance(result, Exception):
                    print(
                        f"[BOARDROOM] Unexpected discussion error for "
                        f"{agent_name}: {result}"
                    )

                    discussions.append(
                        {
                            "agent_name": agent_name,
                            "error": (
                                "This agent could not complete its discussion "
                                "round."
                            ),
                        }
                    )
                    continue

                result_name, discussion_data, error = result

                if error or discussion_data is None:
                    discussions.append(
                        {
                            "agent_name": result_name,
                            "error": error
                            or "Discussion result unavailable.",
                        }
                    )
                else:
                    discussions.append(
                        {
                            "agent_name": result_name,
                            "discussion": discussion_data,
                        }
                    )

        discussion_ms = (time.perf_counter() - discussion_started) * 1000

        # ---------------------------------------------------------
        # STAGE 3: Synthesize the available opinions and discussions.
        # ---------------------------------------------------------
        synthesis_started = time.perf_counter()
        synthesis = await self._synthesize(
            founder_question=founder_question,
            company=company,
            responses=responses,
            discussions=discussions,
        )

        synthesis_ms = (time.perf_counter() - synthesis_started) * 1000

        return {
            "question": founder_question,
            "mode": mode,
            "responses": responses,
            "discussions": discussions,
            "synthesis": synthesis,
            "performance": {
                "context_preparation_ms": round(context_preparation_ms, 2),
                "initial_opinions_ms": round(initial_opinions_ms, 2),
                "discussion_ms": round(discussion_ms, 2),
                "synthesis_ms": round(synthesis_ms, 2),
                "total_backend_ms": round((time.perf_counter() - consultation_started) * 1000, 2),
                "measurement_scope": "Backend orchestration wall-clock time; excludes HTTP routing/authentication and frontend rendering.",
            },
        }

    async def continue_collaboration(
        self,
        founder_question: str,
        company: dict[str, Any],
        responses: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Continue a consultation using its existing independent opinions.

        This method deliberately does not call agent.respond().
        It runs the discussion stage and then generates the synthesis.
        """

        continuation_started = time.perf_counter()
        company_id = str(company["_id"])
        context_preparation_started = time.perf_counter()

        previous_decisions = self.decision_repository.get_by_company(
            company_id
        )[:5]

        agent_by_name = {
            agent.agent_name: agent
            for agent in self.agents
        }

        successful_items = []

        # Reconstruct the validated original responses and agent contexts.
        for item in responses:
            agent_name = item.get("agent_name")
            response_data = item.get("response")

            agent = agent_by_name.get(agent_name)

            if (
                agent is None
                or item.get("error")
                or not isinstance(response_data, dict)
            ):
                continue

            try:
                original_response = AgentResponse.model_validate(
                    response_data
                )

                context = await self._get_agent_context(
                    agent=agent,
                    founder_question=founder_question,
                    company=company,
                    previous_decisions=previous_decisions,
                    company_id=company_id,
                )

                successful_items.append(
                    {
                        "agent": agent,
                        "context": context,
                        "response": original_response,
                        "response_data": response_data,
                    }
                )

            except Exception as exc:
                print(
                    f"[BOARDROOM] Could not prepare {agent_name} "
                    f"for discussion: {exc}"
                )

        context_preparation_ms = (time.perf_counter() - context_preparation_started) * 1000

        # If no valid original responses remain, do not invent opinions.
        if not successful_items:
            return {
                "question": founder_question,
                "mode": "both",
                "responses": responses,
                "discussions": [],
                "synthesis": {
                    "status": "unavailable",
                    "error": (
                        "No valid agent opinions were available to continue "
                        "the boardroom discussion."
                    ),
                },
                "performance": {
                    "context_preparation_ms": round(context_preparation_ms, 2),
                    "discussion_ms": 0,
                    "synthesis_ms": 0,
                    "total_backend_ms": round((time.perf_counter() - continuation_started) * 1000, 2),
                    "measurement_scope": "Backend continuation orchestration wall-clock time; excludes HTTP routing/authentication and frontend rendering.",
                },
            }

        # STAGE 2: Ask each successful agent to review the others.
        discussion_started = time.perf_counter()
        discussion_tasks = []

        for item in successful_items:
            current_agent = item["agent"]

            other_responses = [
                {
                    "agent_name": other["agent"].agent_name,
                    "response": other["response_data"],
                }
                for other in successful_items
                if other["agent"].agent_name
                != current_agent.agent_name
            ]

            discussion_tasks.append(
                self._discuss_one(
                    agent=current_agent,
                    original_response=item["response"],
                    context=item["context"],
                    founder_question=founder_question,
                    other_responses=other_responses,
                )
            )

        discussion_results = await asyncio.gather(
            *discussion_tasks,
            return_exceptions=True,
        )

        discussions = []

        for item, result in zip(
            successful_items,
            discussion_results,
        ):
            agent_name = item["agent"].agent_name

            if isinstance(result, Exception):
                print(
                    f"[BOARDROOM] Unexpected discussion error for "
                    f"{agent_name}: {result}"
                )

                discussions.append(
                    {
                        "agent_name": agent_name,
                        "error": (
                            "This agent could not complete its discussion round."
                        ),
                    }
                )
                continue

            result_name, discussion_data, error = result

            if error or discussion_data is None:
                discussions.append(
                    {
                        "agent_name": result_name,
                        "error": error
                        or "Discussion result unavailable.",
                    }
                )
            else:
                discussions.append(
                    {
                        "agent_name": result_name,
                        "discussion": discussion_data,
                    }
                )

        discussion_ms = (time.perf_counter() - discussion_started) * 1000

        # STAGE 3: Generate the final synthesis from existing opinions
        # and the discussion results.
        synthesis_started = time.perf_counter()
        synthesis = await self._synthesize(
            founder_question=founder_question,
            company=company,
            responses=responses,
            discussions=discussions,
        )
        synthesis_ms = (time.perf_counter() - synthesis_started) * 1000

        return {
            "question": founder_question,
            "mode": "both",
            "responses": responses,
            "discussions": discussions,
            "synthesis": synthesis,
            "performance": {
                "context_preparation_ms": round(context_preparation_ms, 2),
                "discussion_ms": round(discussion_ms, 2),
                "synthesis_ms": round(synthesis_ms, 2),
                "total_backend_ms": round((time.perf_counter() - continuation_started) * 1000, 2),
                "measurement_scope": "Backend continuation orchestration wall-clock time; excludes HTTP routing/authentication and frontend rendering.",
            },
        }