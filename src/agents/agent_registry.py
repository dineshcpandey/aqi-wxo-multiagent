# Agent capability registry


# src/agents/agent_registry.py
from typing import Dict, Type, List, Any, Optional
from dataclasses import dataclass
from .agent_base import AgentBase

@dataclass
class AgentCapability:
    """Defines what an agent can handle"""
    agent_class: Type[AgentBase]
    intents: List[str]  # Intent types this agent handles
    required_entities: List[str]  # Required entities in query
    optional_entities: List[str]  # Optional entities
    db_functions: List[str]  # DB functions this agent uses
    description: str

class AgentRegistry:
    """Central registry of all available agents and their capabilities"""
    
    def __init__(self):
        self.agents: Dict[str, AgentCapability] = {}
        self._register_agents()
    
    def _register_agents(self):
        """Register all available agents with their capabilities"""
        
        # Existing agents
        self.agents['location_resolver'] = AgentCapability(
            agent_class=LocationResolverAgent,
            intents=['location_search', 'any'],  # Used for all queries needing location
            required_entities=['location_query'],
            optional_entities=[],
            db_functions=['gis.search_location_json', 'gis.search_location_with_sensors'],
            description="Resolves location names to codes and handles disambiguation"
        )
        
        self.agents['pm_data'] = AgentCapability(
            agent_class=PMDataAgent,
            intents=['current_reading'],
            required_entities=['location'],
            optional_entities=['metric'],
            db_functions=['gis.get_current_pm25', 'gis.get_current_readings'],
            description="Fetches current PM2.5 and air quality metrics"
        )
        
        # New agents to implement
        self.agents['trend'] = AgentCapability(
            agent_class=TrendAgent,
            intents=['trend', 'historical'],
            required_entities=['location'],
            optional_entities=['duration', 'unit', 'metric', 'aggregation'],
            db_functions=['gis.get_time_series'],
            description="Analyzes historical trends and patterns"
        )
        
        self.agents['comparison'] = AgentCapability(
            agent_class=ComparisonAgent,
            intents=['comparison', 'versus'],
            required_entities=['locations'],  # Multiple locations
            optional_entities=['metric', 'time_range'],
            db_functions=['gis.compare_locations'],
            description="Compares metrics across multiple locations"
        )
        
        self.agents['hotspot'] = AgentCapability(
            agent_class=HotspotAgent,
            intents=['hotspot', 'worst_areas'],
            required_entities=[],  # Can work without specific location
            optional_entities=['region', 'metric', 'threshold'],
            db_functions=['gis.find_hotspots'],
            description="Identifies pollution hotspots and clusters"
        )
        
        self.agents['forecast'] = AgentCapability(
            agent_class=ForecastAgent,
            intents=['forecast', 'prediction'],
            required_entities=['location'],
            optional_entities=['hours_ahead', 'metric'],
            db_functions=['gis.get_forecast'],
            description="Provides air quality predictions"
        )
        
        self.agents['health_advisory'] = AgentCapability(
            agent_class=HealthAdvisoryAgent,
            intents=['health', 'safety', 'advisory'],
            required_entities=['location'],
            optional_entities=[],
            db_functions=['gis.get_health_advisory', 'gis.get_current_readings'],
            description="Provides health recommendations based on air quality"
        )
        
        self.agents['aggregate'] = AgentCapability(
            agent_class=AggregateAgent,
            intents=['statistics', 'summary'],
            required_entities=['location'],
            optional_entities=['time_range', 'metrics'],
            db_functions=['gis.get_time_series', 'gis.get_current_readings'],
            description="Provides statistical summaries and aggregations"
        )
    
    def get_agent_for_intent(self, intent: str) -> Optional[AgentCapability]:
        """Get the appropriate agent for a given intent"""
        for agent_cap in self.agents.values():
            if intent in agent_cap.intents:
                return agent_cap
        return None
    
    def get_required_agents(self, intents: List[str]) -> List[AgentCapability]:
        """Get all agents needed for multiple intents (complex queries)"""
        required = []
        for intent in intents:
            agent = self.get_agent_for_intent(intent)
            if agent and agent not in required:
                required.append(agent)
        return required