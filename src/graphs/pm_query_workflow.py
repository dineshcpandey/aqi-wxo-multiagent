# Modify src/graphs/pm_query_workflow.py
class PMQueryWorkflow:
    def __init__(self, location_agent, pm_agent, use_hybrid_parser=False):
        self.location_agent = location_agent
        self.pm_agent = pm_agent
        
        # Add parser selection
        if use_hybrid_parser:
            from src.agents.hybrid_parser import HybridQueryParser
            self.parser = HybridQueryParser(shadow_mode=True)
        else:
            from src.agents.query_parser import QueryParser
            self.parser = QueryParser()
    
    async def process_query(self, query: str) -> PMQueryState:
        # Parse query first
        parsed = await self.parser.parse(query) if asyncio.iscoroutinefunction(self.parser.parse) else self.parser.parse(query)
        
        # Extract location from parsed entities
        location_term = parsed.entities.get('location', '')
        
        # Rest of your existing logic...