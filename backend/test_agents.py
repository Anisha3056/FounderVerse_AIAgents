import asyncio

from app.agents.finance_agent import FinanceAgent
from app.agents.marketing_agent import MarketingAgent
from app.agents.sales_agent import SalesAgent
from app.agents.cto_agent import CTOAgent
from app.agents.legal_agent import LegalAgent

from app.agents.base_agent import AgentContext


async def main():

    company = {
        "company_name": "DemoStartup",
        "industry": "SaaS",
        "stage": "idea",
    }

    context = AgentContext(
        company=company,
        memories=[],
        retrieved_information=[],
    )

    agents = [
        FinanceAgent(),
        MarketingAgent(),
        SalesAgent(),
        CTOAgent(),
        LegalAgent(),
    ]

    question = "Should our startup invest more money into growth?"

    for agent in agents:

        print("\n" + "=" * 60)
        print(agent.agent_name)
        print("=" * 60)

        response = await agent.respond(
            founder_question=question,
            context=context,
        )

        print(response)


if __name__ == "__main__":
    asyncio.run(main())