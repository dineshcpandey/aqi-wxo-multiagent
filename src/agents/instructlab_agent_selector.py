# src/agents/instructlab_agent_selector.py
class InstructLabAgentSelector:
    """Uses InstructLab to select appropriate agent for query"""
    
    def __init__(self):
        self.prompt_template = """You are an agent selector for an air quality system.

Available agents and their purposes:
- pm_data: Current air quality readings (PM2.5, AQI, etc.)
- trend: Historical trends and patterns over time
- comparison: Compare multiple locations
- hotspot: Find pollution hotspots
- forecast: Future predictions
- health_advisory: Health recommendations
- aggregate: Statistical summaries

Analyze the query and return the appropriate agent and extracted entities.

Query: {query}

Return JSON:
{
    "agent": "agent_name",
    "entities": {
        "location": "extracted_location",
        "metric": "pm25|aqi|no2|so2",
        "duration": number,
        "unit": "hours|days|weeks"
    }
}"""
    
    async def select_agent(self, query: str) -> Dict[str, Any]:
        # Call InstructLab with prompt
        prompt = self.prompt_template.format(query=query)
        # ... InstructLab call
        return result