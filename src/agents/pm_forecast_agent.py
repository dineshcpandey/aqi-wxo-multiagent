# src/agents/pm_forecast_agent.py
from typing import Dict, Any
import re
import json
from .agent_base import AgentBase

class PMForecastAgent(AgentBase):
    def __init__(self, db_connection):
        super().__init__(name="PMForecastAgent")
        self.db = db_connection
        print("PMForecastAgent initialized with DB connection")
    
    def _extract_days_from_query(self, query: str) -> int:
        """Extract number of days from user query, default to 1"""
        query_lower = query.lower()
        
        # Pattern matching for days
        patterns = [
            r'next (\d+) days?',
            r'(\d+) days?',
            r'over (\d+) days?',
            r'for (\d+) days?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                try:
                    days = int(match.group(1))
                    # Limit to reasonable range
                    return min(max(days, 1), 7)  # 1-7 days
                except ValueError:
                    continue
        
        # Special keywords
        if 'tomorrow' in query_lower:
            return 1
        elif 'week' in query_lower:
            return 7
        elif '3 day' in query_lower or 'three day' in query_lower:
            return 3
        
        # Default to 1 day (24 hours)
        return 1
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch PM2.5 forecast data using gis.get_forecast_pm25_sensor_agg(state_code, code, level, days)
        """
        print(f"PMForecastAgent.run called with input: {input_data}")
        
        # Accept either separate code/level or a full location dict
        location = input_data.get("location")
        query = input_data.get("query", "")
        
        if location and isinstance(location, dict):
            location_code = location.get("code")
            location_level = location.get("level")
            location_name = location.get("name", "Unknown")
            state_code = location.get("state_code") or location.get("state")
        else:
            location_code = input_data.get("location_code")
            location_level = input_data.get("location_level")
            location_name = input_data.get("location_name", "Unknown")
            state_code = input_data.get("state_code") or input_data.get("state")
        
        # Extract forecast days from query
        forecast_days = input_data.get("days") or self._extract_days_from_query(query)
        
        self.log(f"Fetching PM2.5 forecast for {location_name} (code: {location_code}, level: {location_level}, state: {state_code}, days: {forecast_days})")
        
        try:
            # Require state_code (same as PM data agent)
            if not state_code:
                return {
                    "success": False,
                    "error": "State code is required for PM2.5 forecast data retrieval. Please ensure location data includes state_code."
                }
            
            self.log(f"Using forecast function with state_code: {state_code}")
            result = await self.db.execute_query(
                "SELECT * FROM gis.get_forecast_pm25_sensor_agg($1, $2, $3, $4)",
                [state_code, location_code, location_level, forecast_days]
            )
            
            if not result:
                return {
                    "success": False,
                    "error": "No PM2.5 forecast data available for this location"
                }
            
            raw = result[0]
            
            # Handle response from gis.get_forecast_pm25_sensor_agg function
            data_row = None
            if isinstance(raw, dict) and len(raw) == 1:
                # Some drivers return a single column named after the function
                first_val = next(iter(raw.values()))
                if isinstance(first_val, dict):
                    data_row = first_val
            if data_row is None:
                data_row = raw

            # Extract forecast PM2.5 value (function returns 'predicted_pm25')
            forecast_pm25 = None
            for key in ("predicted_pm25", "forecast_pm25", "pm25_forecast", "pm25_value", "current_pm25"):
                if data_row.get(key) is not None:
                    forecast_pm25 = data_row.get(key)
                    break

            # Normalize numeric types: convert Decimal or numeric strings to float
            try:
                if forecast_pm25 is not None:
                    forecast_pm25 = float(forecast_pm25)
                    forecast_pm25 = round(forecast_pm25, 2)
            except Exception:
                pass

            # Extract time series data
            time_series = data_row.get("pm25_time_series")
            if time_series and isinstance(time_series, str):
                try:
                    time_series = json.loads(time_series)
                except json.JSONDecodeError:
                    time_series = None

            # Extract other values
            returned_code = data_row.get("code") or data_row.get("location_code")
            returned_location_name = data_row.get("location_name") or data_row.get("location")
            sensor_count = data_row.get("sensor_count")

            return {
                "success": True,
                "forecast_pm25": forecast_pm25,
                "forecast_days": forecast_days,
                "pm25_time_series": time_series,
                "timestamp": data_row.get("timestamp"),
                "sensor_count": sensor_count,
                "location": {
                    "name": location_name or returned_location_name,
                    "code": location_code or returned_code,
                    "level": location_level,
                    "state_code": state_code
                },
                "raw_data": data_row,
                "method": "forecast"
            }
            
        except Exception as e:
            return self.handle_error(e, {
                "location_code": location_code,
                "location_level": location_level,
                "state_code": state_code,
                "forecast_days": forecast_days
            })