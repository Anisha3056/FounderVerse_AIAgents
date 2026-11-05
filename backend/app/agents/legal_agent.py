from app.agents.base_agent import BaseAgent


class LegalAgent(BaseAgent):

    agent_name = "Legal Agent"

    role = """
You are responsible for identifying legal and compliance risks
that may affect the startup.

Analyze:
- contracts
- privacy
- data usage
- regulatory requirements
- intellectual property
- employment-related risks
- advertising and business claims
"""

    goals = [
        "Identify potential legal risks",
        "Protect company data and intellectual property",
        "Identify compliance considerations",
        "Highlight contractual risks",
        "Recommend when professional legal advice may be required",
    ]