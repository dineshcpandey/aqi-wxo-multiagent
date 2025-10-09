# Location comparison agent
# src/agents/comparison_agent.py
from typing import Dict, Any, List
from .agent_base import AgentBase
import json

class ComparisonAgent(AgentBase):
    """Agent for comparing air quality across multiple locations"""
    
    def __init__(self, db_connection):
        super().__init__(name="ComparisonAgent")
        self.db = db_connection
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare metrics across multiple locations
        Expected input:
        - locations: List of resolved location dicts
        - metric: 'pm25', 'aqi', etc.
        - time_range: 'current', 'today_avg', 'week_avg'
        """
        locations = input_data.get('locations', [])
        metric = input_data.get('metric', 'pm25')
        time_range = input_data.get('time_range', 'current')
        
        if not locations or len(locations) < 2:
            return {
                "success": False,
                "error": "Need at least 2 locations for comparison"
            }
        
        self.log(f"Comparing {metric} across {len(locations)} locations")
        
        try:
            # Prepare locations JSON for DB function
            locations_json = json.dumps([
                {"code": loc.get('code'), "level": loc.get('level')}
                for loc in locations
            ])
            
            result = await self.db.execute_query(
                "SELECT * FROM gis.compare_locations($1::jsonb, $2, $3)",
                [locations_json, metric, time_range]
            )
            
            if not result:
                return {
                    "success": False,
                    "error": "No comparison data available"
                }
            
            # Generate insights
            insights = self._generate_insights(result, metric)
            
            # Create ranking
            rankings = self._create_rankings(result)
            
            return {
                "success": True,
                "comparison_data": result,
                "rankings": rankings,
                "insights": insights,
                "metadata": {
                    "locations_count": len(locations),
                    "metric": metric,
                    "time_range": time_range
                }
            }
            
        except Exception as e:
            return self.handle_error(e, input_data)
    
    def _generate_insights(self, data: List[Dict], metric: str) -> Dict[str, Any]:
        """Generate comparison insights"""
        if not data:
            return {"error": "No data for insights"}
        
        values = [d['metric_value'] for d in data if d.get('metric_value') is not None]
        
        if not values:
            return {"error": "No valid values for comparison"}
        
        best = min(data, key=lambda x: x.get('metric_value', float('inf')))
        worst = max(data, key=lambda x: x.get('metric_value', 0))
        
        # Calculate spread
        spread = max(values) - min(values)
        spread_percentage = (spread / min(values) * 100) if min(values) > 0 else 0
        
        return {
            "best_location": {
                "name": best.get('location_name'),
                "value": best.get('metric_value'),
                "category": best.get('category')
            },
            "worst_location": {
                "name": worst.get('location_name'),
                "value": worst.get('metric_value'),
                "category": worst.get('category')
            },
            "spread": {
                "absolute": spread,
                "percentage": spread_percentage
            },
            "all_safe": all(self._is_safe(v, metric) for v in values),
            "all_unhealthy": all(self._is_unhealthy(v, metric) for v in values)
        }
    
    def _create_rankings(self, data: List[Dict]) -> List[Dict]:
        """Create rankings with relative scores"""
        if not data:
            return []
        
        # Sort by value (lower is better for pollution metrics)
        sorted_data = sorted(data, key=lambda x: x.get('metric_value', float('inf')))
        
        rankings = []
        for idx, item in enumerate(sorted_data, 1):
            rankings.append({
                "rank": idx,
                "location": item.get('location_name'),
                "value": item.get('metric_value'),
                "category": item.get('category'),
                "relative_to_best": (
                    ((item.get('metric_value', 0) / sorted_data[0].get('metric_value', 1)) - 1) * 100
                    if sorted_data[0].get('metric_value', 0) > 0 else 0
                )
            })
        
        return rankings
    
    def _is_safe(self, value: float, metric: str) -> bool:
        """Check if value is in safe range"""
        safe_thresholds = {
            'pm25': 30,
            'aqi': 50,
            'no2': 40,
            'so2': 40,
            'co': 2,
            'o3': 50
        }
        return value <= safe_thresholds.get(metric, 50)
    
    def _is_unhealthy(self, value: float, metric: str) -> bool:
        """Check if value is unhealthy"""
        unhealthy_thresholds = {
            'pm25': 90,
            'aqi': 200,
            'no2': 80,
            'so2': 80,
            'co': 10,
            'o3': 168
        }
        return value > unhealthy_thresholds.get(metric, 200)