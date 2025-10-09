# src/agents/disambiguation_agent.py
from typing import Dict, Any, List, Optional
from .agent_base import AgentBase
import json

class DisambiguationAgent(AgentBase):
    """
    Handles ambiguous queries by asking clarifying questions
    """
    def __init__(self, db_connection=None):
        super().__init__(name="DisambiguationAgent")
        self.db = db_connection
        
    async def check_disambiguation_needed(self, 
                                         location_results: List[Dict]) -> Dict[str, Any]:
        """
        Check if disambiguation is needed based on location search results
        """
        if not location_results:
            return {
                "needs_disambiguation": False,
                "reason": "no_matches"
            }
        
        # Check for multiple matches at different levels
        levels = set(r.get('level') for r in location_results)
        
        # If we have matches at different administrative levels
        if len(levels) > 1 or len(location_results) > 1:
            return {
                "needs_disambiguation": True,
                "reason": "multiple_matches",
                "options": self._format_options(location_results)
            }
        
        return {
            "needs_disambiguation": False,
            "selected": location_results[0]
        }
    
    def _format_options(self, results: List[Dict]) -> List[Dict]:
        """Format disambiguation options for display"""
        options = []
        
        for idx, result in enumerate(results[:5]):  # Limit to 5 options
            option = {
                "id": f"option_{idx}",
                "display_text": self._create_display_text(result),
                "value": result,
                "metadata": {
                    "level": result.get('level'),
                    "state": result.get('state_name'),
                    "district": result.get('district_name'),
                    "confidence": result.get('similarity', 1.0)
                }
            }
            options.append(option)
        
        return options
    
    def _create_display_text(self, result: Dict) -> str:
        """Create human-readable option text"""
        level = result.get('level', 'unknown')
        name = result.get('name', 'Unknown')
        
        if level == 'district':
            return f"📍 {name} District, {result.get('state_name', '')}"
        elif level == 'district_hq':
            return f"🏛️ {name} City (District HQ), {result.get('state_name', '')}"
        elif level == 'sub_district':
            return f"📌 {name} Sub-district, {result.get('district_name', '')}, {result.get('state_name', '')}"
        elif level == 'ward':
            return f"🏘️ {name} Ward, {result.get('district_name', '')}"
        else:
            return f"📍 {name} ({level})"