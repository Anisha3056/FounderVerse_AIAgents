from app.agents.base_agent import BaseAgent


class SalesAgent(BaseAgent):

    agent_name = "Sales Agent"

    role = """
You are responsible for the startup's sales performance.

Analyze:
- leads
- sales pipeline
- conversion rates
- customer acquisition
- sales capacity
- customer expansion
- revenue opportunities
"""

    goals = [
        "Increase qualified sales opportunities",
        "Improve conversion rates",
        "Identify sales bottlenecks",
        "Improve customer acquisition",
        "Identify revenue expansion opportunities",
    ]