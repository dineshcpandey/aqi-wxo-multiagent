# Multi-agent router workflow
# src/graphs/multi_agent_router.py
from typing import Dict, Any, List, Optional
from src.agents.agent_registry import AgentRegistry
from src.agents.query_parser import ParsedQuery

class MultiAgentRouter:
    """Routes queries to appropriate agents based on intent and requirements"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.registry = AgentRegistry()
        self.agent_instances = {}
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize all registered agents"""
        for name, capability in self.registry.agents.items():
            self.agent_instances[name] = capability.agent_class(self.db)
    
    async def route_query(self, parsed_query: ParsedQuery) -> Dict[str, Any]:
        """Route query to appropriate agent(s)"""
        
        # Step 1: Determine if location resolution is needed
        if self._needs_location_resolution(parsed_query):
            location_result = await self._resolve_location(parsed_query)
            
            if location_result.get('needs_disambiguation'):
                return location_result  # Return for user disambiguation
            
            # Add resolved location to entities
            parsed_query.entities['location'] = location_result.get('location')
        
        # Step 2: Get appropriate agent for intent
        agent_cap = self.registry.get_agent_for_intent(parsed_query.intent)
        
        if not agent_cap:
            return {
                "success": False,
                "error": f"No agent found for intent: {parsed_query.intent}"
            }
        
        # Step 3: Validate required entities
        missing = self._check_required_entities(agent_cap, parsed_query.entities)
        if missing:
            return {
                "success": False,
                "error": f"Missing required information: {', '.join(missing)}",
                "missing_entities": missing
            }
        
        # Step 4: Execute agent
        agent = self.agent_instances[self._get_agent_name(agent_cap)]
        result = await agent.run(parsed_query.entities)
        
        # Step 5: Post-process if needed
        if result.get('success'):
            result = await self._post_process(result, parsed_query)
        
        return result
    
    def _needs_location_resolution(self, parsed_query: ParsedQuery) -> bool:
        """Check if query needs location resolution"""
        # Most queries need location except global ones like "pollution in India"
        needs_location_intents = [
            'current_reading', 'trend', 'comparison', 
            'forecast', 'health', 'advisory'
        ]
        return (
            parsed_query.intent in needs_location_intents and
            'location' in parsed_query.entities and
            not isinstance(parsed_query.entities.get('location'), dict)
        )
    
    async def _resolve_location(self, parsed_query: ParsedQuery) -> Dict[str, Any]:
        """Resolve location using LocationResolverAgent"""
        location_agent = self.agent_instances['location_resolver']
        location_text = parsed_query.entities.get('location')
        
        result = await location_agent.run({"location_query": location_text})
        
        if result.get('needs_disambiguation'):
            return {
                "needs_disambiguation": True,
                "locations": result.get('locations'),
                "original_query": parsed_query.raw_query
            }
        
        if result.get('locations'):
            return {
                "success": True,
                "location": result['locations'][0]
            }
        
        return {
            "success": False,
            "error": f"Location not found: {location_text}"
        }
    
    def _check_required_entities(self, agent_cap, entities: Dict) -> List[str]:
        """Check if all required entities are present"""
        missing = []
        for required in agent_cap.required_entities:
            if required not in entities or entities[required] is None:
                missing.append(required)
        return missing
    
    def _get_agent_name(self, agent_cap) -> str:
        """Get agent name from capability"""
        for name, cap in self.registry.agents.items():
            if cap == agent_cap:
                return name
        return None
    
    async def _post_process(self, result: Dict, parsed_query: ParsedQuery) -> Dict:
        """Post-process results if needed"""
        # Add query metadata
        result['query_metadata'] = {
            'intent': parsed_query.intent,
            'confidence': parsed_query.confidence,
            'entities': parsed_query.entities
        }
        
        # Format response based on intent
        if parsed_query.intent == 'comparison':
            result = self._format_comparison_response(result)
        elif parsed_query.intent == 'trend':
            result = self._format_trend_response(result)
        
        return result
    
    def _format_comparison_response(self, result: Dict) -> Dict:
        """Special formatting for comparison results"""
        # Add natural language summary
        if result.get('rankings'):
            best = result['rankings'][0]
            worst = result['rankings'][-1]
            result['summary'] = (
                f"{best['location']} has the best air quality "
                f"({best['value']:.1f}), while {worst['location']} "
                f"has the worst ({worst['value']:.1f})"
            )
        return result
    
    def _format_trend_response(self, result: Dict) -> Dict:
        """Special formatting for trend results"""
        stats = result.get('statistics', {})
        trend = stats.get('trend')
        
        if trend:
            result['summary'] = f"Air quality is {trend}"
            if trend == 'increasing':
                result['alert'] = "Pollution levels are rising"
            elif trend == 'decreasing':
                result['alert'] = "Air quality is improving"
        
        return result