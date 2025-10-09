# Trend analysis agent
# src/agents/trend_agent.py
from typing import Dict, Any, List, Optional
from .agent_base import AgentBase
import json

class TrendAgent(AgentBase):
    """Agent for handling time-series trend queries"""
    
    def __init__(self, db_connection):
        super().__init__(name="TrendAgent")
        self.db = db_connection
        
        # Default configurations
        self.defaults = {
            'duration': 24,
            'unit': 'hours',
            'metric': 'pm25',
            'aggregation': 'hourly'
        }
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch trend data using gis.get_time_series
        Expected input:
        - location: resolved location dict
        - duration: number (e.g., 24)
        - unit: 'hours', 'days', 'weeks', 'months'
        - metric: 'pm25', 'aqi', 'no2', etc.
        - aggregation: 'hourly', 'daily', '6hourly'
        """
        location = input_data.get('location', {})
        duration = input_data.get('duration', self.defaults['duration'])
        unit = input_data.get('unit', self.defaults['unit'])
        metric = input_data.get('metric', self.defaults['metric'])
        aggregation = input_data.get('aggregation', self.defaults['aggregation'])
        
        self.log(f"Fetching {metric} trend for {location.get('name')} - {duration} {unit}")
        
        try:
            # Call the time series function
            result = await self.db.execute_query(
                """
                SELECT * FROM gis.get_time_series($1, $2, $3, $4, $5, $6)
                ORDER BY timestamp DESC
                """,
                [
                    location.get('code'),
                    location.get('level'),
                    metric,
                    duration,
                    unit,
                    aggregation
                ]
            )
            
            if not result:
                return {
                    "success": False,
                    "error": "No trend data available"
                }
            
            # Calculate statistics
            values = [r['avg_value'] for r in result if r['avg_value'] is not None]
            
            # Determine trend direction
            trend_direction = self._calculate_trend(values)
            
            # Find peak times
            peak_times = self._find_peak_times(result)
            
            return {
                "success": True,
                "data_points": result,
                "statistics": {
                    "mean": sum(values) / len(values) if values else 0,
                    "max": max(values) if values else 0,
                    "min": min(values) if values else 0,
                    "std_dev": self._calculate_std_dev(values),
                    "trend": trend_direction,
                    "peak_times": peak_times
                },
                "metadata": {
                    "location": location,
                    "metric": metric,
                    "duration": duration,
                    "unit": unit,
                    "aggregation": aggregation,
                    "data_points_count": len(result)
                }
            }
            
        except Exception as e:
            return self.handle_error(e, input_data)
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Determine if trend is increasing, decreasing, or stable"""
        if len(values) < 2:
            return "insufficient_data"
        
        # Simple linear regression slope
        n = len(values)
        x = list(range(n))
        
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return "stable"
        
        slope = numerator / denominator
        
        # Determine trend based on slope relative to mean
        if abs(slope) < y_mean * 0.01:  # Less than 1% change
            return "stable"
        elif slope > 0:
            return "increasing"
        else:
            return "decreasing"
    
    def _find_peak_times(self, data_points: List[Dict]) -> List[Dict]:
        """Find peak pollution times"""
        if not data_points:
            return []
        
        # Sort by value and get top 3
        sorted_points = sorted(
            data_points,
            key=lambda x: x.get('avg_value', 0),
            reverse=True
        )[:3]
        
        return [
            {
                'timestamp': p['timestamp'],
                'value': p['avg_value'],
                'hour': p['timestamp'].hour if hasattr(p['timestamp'], 'hour') else None
            }
            for p in sorted_points
        ]
    
    def _calculate_std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5