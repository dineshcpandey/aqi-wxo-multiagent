# Health advisory agent
# src/agents/health_advisory_agent.py
from typing import Dict, Any
from .agent_base import AgentBase

class HealthAdvisoryAgent(AgentBase):
    """Agent for providing health advisories based on air quality"""
    
    def __init__(self, db_connection):
        super().__init__(name="HealthAdvisoryAgent")
        self.db = db_connection
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate health advisory for a location
        Expected input:
        - location: resolved location dict
        - user_profile: Optional user health profile (age_group, conditions)
        """
        location = input_data.get('location', {})
        user_profile = input_data.get('user_profile', {})
        
        self.log(f"Generating health advisory for {location.get('name')}")
        
        try:
            # Get health advisory from DB
            result = await self.db.execute_query(
                "SELECT gis.get_health_advisory($1, $2) as advisory",
                [location.get('code'), location.get('level')]
            )
            
            if not result or not result[0].get('advisory'):
                return {
                    "success": False,
                    "error": "Unable to generate health advisory"
                }
            
            advisory = result[0]['advisory']
            
            # Customize based on user profile
            if user_profile:
                advisory = self._customize_for_user(advisory, user_profile)
            
            # Generate specific recommendations
            recommendations = self._generate_recommendations(advisory)
            
            return {
                "success": True,
                "advisory": advisory,
                "recommendations": recommendations,
                "metadata": {
                    "location": location,
                    "generated_at": "now"
                }
            }
            
        except Exception as e:
            return self.handle_error(e, input_data)
    
    def _customize_for_user(self, advisory: Dict, profile: Dict) -> Dict:
        """Customize advisory based on user profile"""
        age_group = profile.get('age_group')
        conditions = profile.get('conditions', [])
        
        # Adjust recommendations for sensitive groups
        if age_group in ['child', 'elderly'] or 'asthma' in conditions:
            if advisory.get('category') in ['moderate', 'poor']:
                advisory['outdoor_activity'] = 'avoid'
                advisory['special_recommendation'] = (
                    "You are in a sensitive group. "
                    "Extra caution is recommended even at moderate pollution levels."
                )
        
        return advisory
    
    def _generate_recommendations(self, advisory: Dict) -> List[Dict]:
        """Generate specific action recommendations"""
        category = advisory.get('category')
        recommendations = []
        
        if category == 'good':
            recommendations.append({
                'type': 'outdoor_activity',
                'action': 'enjoy',
                'text': 'Perfect conditions for outdoor activities'
            })
        elif category == 'satisfactory':
            recommendations.append({
                'type': 'outdoor_activity',
                'action': 'normal',
                'text': 'Outdoor activities can be continued normally'
            })
        elif category in ['moderate', 'poor']:
            recommendations.extend([
                {
                    'type': 'mask',
                    'action': 'wear',
                    'text': 'Wear N95/N99 mask when going outside'
                },
                {
                    'type': 'outdoor_activity',
                    'action': 'limit',
                    'text': 'Limit prolonged outdoor exertion'
                },
                {
                    'type': 'indoor',
                    'action': 'purify',
                    'text': 'Use air purifiers indoors if available'
                }
            ])
        elif category in ['very_poor', 'severe']:
            recommendations.extend([
                {
                    'type': 'outdoor_activity',
                    'action': 'avoid',
                    'text': 'Avoid all outdoor activities'
                },
                {
                    'type': 'windows',
                    'action': 'close',
                    'text': 'Keep windows and doors closed'
                },
                {
                    'type': 'medical',
                    'action': 'monitor',
                    'text': 'Monitor for respiratory symptoms'
                }
            ])
        
        return recommendations