# src/agents/response_formatter.py
from typing import Dict, Any, Optional, List
import pandas as pd
from datetime import datetime, timedelta

class ResponseFormatter:
    """Formats agent responses for chat display with chart support"""
    
    def __init__(self):
        self.chart_generators = {
            'time_series': self._generate_time_series_chart,
            'comparison': self._generate_comparison_chart,
            'hotspot': self._generate_hotspot_map,
            'distribution': self._generate_distribution_chart
        }
    
    def format_response(self, 
                       query_type: str,
                       data: Dict[str, Any],
                       metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Main formatting method"""
        
        response = {
            "text_response": "",
            "has_chart": False,
            "chart_data": None,
            "chart_type": None,
            "metadata": metadata or {}
        }
        
        # Format based on query type
        if query_type == "current_reading":
            response.update(self._format_current_reading(data))
        elif query_type == "time_series":
            response.update(self._format_time_series(data))
        elif query_type == "comparison":
            response.update(self._format_comparison(data))
        elif query_type == "hotspot":
            response.update(self._format_hotspot(data))
        else:
            response["text_response"] = str(data)
        
        return response
    
    def _format_current_reading(self, data: Dict) -> Dict:
        """Format current reading response"""
        value = data.get('value', 0)
        metric = data.get('metric', 'PM2.5')
        location = data.get('location', 'Unknown')
        unit = data.get('unit', 'µg/m³')
        
        # Determine air quality category
        category, emoji = self._get_air_quality_category(metric, value)
        
        text = f"{emoji} The current {metric} level in {location} is **{value} {unit}** ({category})"
        
        # Add recommendations
        if category in ["Unhealthy", "Very Unhealthy", "Hazardous"]:
            text += f"\n\n⚠️ **Health Advisory**: {self._get_health_advisory(category)}"
        
        return {
            "text_response": text,
            "has_chart": False
        }
    
    def _format_time_series(self, data: List[Dict]) -> Dict:
        """Format time series response with chart"""
        if not data:
            return {"text_response": "No data available for the specified period."}
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Calculate statistics
        avg_value = df['value'].mean()
        max_value = df['value'].max()
        min_value = df['value'].min()
        trend = "increasing" if df['value'].iloc[-1] > df['value'].iloc[0] else "decreasing"
        
        text = f"""📊 **Air Quality Trend Analysis**
        
**Average**: {avg_value:.1f} µg/m³
**Peak**: {max_value:.1f} µg/m³
**Lowest**: {min_value:.1f} µg/m³
**Trend**: {trend}

The chart below shows the detailed trend over the selected period."""
        
        return {
            "text_response": text,
            "has_chart": True,
            "chart_data": df,
            "chart_type": "time_series"
        }
    
    def _format_comparison(self, data: Dict) -> Dict:
        """Format comparison response with chart"""
        locations = list(data.keys())
        
        # Create comparison DataFrame
        comparison_data = []
        for location, values in data.items():
            comparison_data.append({
                'location': location,
                'PM2.5': values.get('pm25', 0),
                'AQI': values.get('aqi', 0),
                'NO2': values.get('no2', 0)
            })
        
        df = pd.DataFrame(comparison_data)
        
        # Find best and worst
        best = df.loc[df['AQI'].idxmin()]['location']
        worst = df.loc[df['AQI'].idxmax()]['location']
        
        text = f"""🆚 **Air Quality Comparison**
        
**Best Air Quality**: {best} (AQI: {df.loc[df['location']==best, 'AQI'].values[0]:.0f})
**Worst Air Quality**: {worst} (AQI: {df.loc[df['location']==worst, 'AQI'].values[0]:.0f})

See the detailed comparison in the chart below."""
        
        return {
            "text_response": text,
            "has_chart": True,
            "chart_data": df,
            "chart_type": "comparison"
        }
    
    def _get_air_quality_category(self, metric: str, value: float) -> tuple:
        """Determine air quality category and emoji"""
        if metric.upper() == "PM2.5":
            if value <= 30:
                return "Good", "🟢"
            elif value <= 60:
                return "Satisfactory", "🟡"
            elif value <= 90:
                return "Moderate", "🟠"
            elif value <= 120:
                return "Poor", "🔴"
            elif value <= 250:
                return "Very Poor", "🟣"
            else:
                return "Severe", "🟤"
        
        # Add more metrics as needed
        return "Unknown", "❓"
    
    def _get_health_advisory(self, category: str) -> str:
        """Get health advisory based on air quality category"""
        advisories = {
            "Poor": "Sensitive groups should limit prolonged outdoor exertion.",
            "Very Poor": "Everyone should limit prolonged outdoor exertion.",
            "Severe": "Everyone should avoid all outdoor exertion. Stay indoors."
        }
        return advisories.get(category, "Take necessary precautions.")