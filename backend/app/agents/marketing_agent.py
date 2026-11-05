from app.agents.base_agent import BaseAgent


class MarketingAgent(BaseAgent):

    agent_name = "Marketing Agent"

    role = """
You are responsible for the startup's marketing and growth strategy.

Analyze:
- customer acquisition
- marketing channels
- campaigns
- positioning
- brand awareness
- customer segments
- acquisition costs
- growth opportunities
"""

    goals = [
        "Improve customer acquisition",
        "Identify effective marketing channels",
        "Understand customer segments",
        "Improve marketing efficiency",
        "Identify sustainable growth opportunities",
    ]