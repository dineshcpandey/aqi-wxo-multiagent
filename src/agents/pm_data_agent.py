# src/agents/pm_data_agent.py
from typing import Dict, Any
from .agent_base import AgentBase

class PMDataAgent(AgentBase):
    def __init__(self, db_connection):
        super().__init__(name="PMDataAgent")
        self.db = db_connection
        print("PMDataAgent initialized with DB connection")
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch PM2.5 data using gis.get_current_pm25_sensor(state_code, code, level)
        Falls back to gis.get_current_pm25(code, level) if state_code not available
        """
        print(f"PMDataAgent.run called with input: {input_data}")
        # Accept either separate code/level or a full location dict
        location = input_data.get("location")
        if location and isinstance(location, dict):
            location_code = location.get("code")
            location_level = location.get("level")
            location_name = location.get("name", "Unknown")
            state_code = location.get("state_code") or location.get("state")  # Support both field names
        else:
            location_code = input_data.get("location_code")
            location_level = input_data.get("location_level")
            location_name = input_data.get("location_name", "Unknown")
            state_code = input_data.get("state_code") or input_data.get("state")
        
        self.log(f"Fetching PM2.5 for {location_name} (code: {location_code}, level: {location_level}, state: {state_code})")
        
        try:
            # Try the new 3-parameter function first if we have state_code
            if state_code:
                self.log(f"Using new 3-parameter function with state_code: {state_code}")
                result = await self.db.execute_query(
                    "SELECT * FROM gis.get_current_pm25_sensor($1, $2, $3)",
                    [state_code, location_code, location_level]
                )
            else:
                # Return error if no state code available (as requested)
                return {
                    "success": False,
                    "error": "State code is required for PM2.5 data retrieval. Please ensure location data includes state_code."
                }
            
            if not result:
                return {
                    "success": False,
                    "error": "No PM2.5 data available for this location"
                }
            
            raw = result[0]

            # Handle response from new gis.get_current_pm25_sensor function
            # Returns: code, location_name, current_pm25, sensor_count
            # Or handle legacy gis.get_current_pm25 function response
            data_row = None
            if isinstance(raw, dict) and len(raw) == 1:
                # Some drivers return a single column named after the function
                first_val = next(iter(raw.values()))
                if isinstance(first_val, dict):
                    data_row = first_val
            if data_row is None:
                data_row = raw

            # Extract pm25 value from known keys (prioritize new function format)
            pm25_value = None
            for key in ("current_pm25", "pm25_value", "current_pm25_value", "value", "avg_value"):
                if data_row.get(key) is not None:
                    pm25_value = data_row.get(key)
                    break

            # Normalize numeric types: convert Decimal or numeric strings to float
            try:
                if pm25_value is not None:
                    # Some DB drivers return Decimal or string; coerce to float
                    pm25_value = float(pm25_value)
                    # Round to 2 decimal places as per DB/function contract
                    pm25_value = round(pm25_value, 2)
            except Exception:
                # Leave as-is if conversion fails
                pass

            # Extract other values (map new function fields to expected format)
            returned_code = data_row.get("code") or data_row.get("location_code")
            returned_location_name = data_row.get("location_name") or data_row.get("location")
            
            # Map sensor_count to station_count for backward compatibility
            sensor_count = data_row.get("sensor_count")
            station_count = data_row.get("station_count") or sensor_count

            return {
                "success": True,
                "pm25_value": pm25_value,
                "timestamp": data_row.get("timestamp"),
                "station_count": station_count,  # Backward compatible field name
                "sensor_count": sensor_count,    # New field from sensor function
                "measurement_type": data_row.get("measurement_type"),
                "location": {
                    "name": location_name or returned_location_name,
                    "code": location_code or returned_code,
                    "level": location_level,
                    "state_code": state_code  # Include state_code in response
                },
                "raw_data": data_row
            }
            
        except Exception as e:
            return self.handle_error(e, {
                "location_code": location_code,
                "location_level": location_level,
                "state_code": state_code
            })
    
    async def run_legacy(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Legacy method: Fetch PM2.5 data using old gis.get_current_pm25(code, level)
        Kept for backward compatibility and future use
        """
        print(f"PMDataAgent.run_legacy called with input: {input_data}")
        # Accept either separate code/level or a full location dict
        location = input_data.get("location")
        if location and isinstance(location, dict):
            location_code = location.get("code")
            location_level = location.get("level")
            location_name = location.get("name", "Unknown")
        else:
            location_code = input_data.get("location_code")
            location_level = input_data.get("location_level")
            location_name = input_data.get("location_name", "Unknown")
        
        self.log(f"Fetching PM2.5 (legacy) for {location_name} (code: {location_code}, level: {location_level})")
        
        try:
            # Call legacy PM2.5 function
            result = await self.db.execute_query(
                "SELECT * FROM gis.get_current_pm25($1, $2)",
                [location_code, location_level]
            )
            
            if not result:
                return {
                    "success": False,
                    "error": "No PM2.5 data available for this location"
                }
            
            raw = result[0]

            # Handle legacy function response format
            data_row = None
            if isinstance(raw, dict) and len(raw) == 1:
                # Some drivers return a single column named after the function
                first_val = next(iter(raw.values()))
                if isinstance(first_val, dict):
                    data_row = first_val
            if data_row is None:
                data_row = raw

            # Extract pm25 value from legacy function keys
            pm25_value = None
            for key in ("pm25_value", "current_pm25", "current_pm25_value", "value", "avg_value"):
                if data_row.get(key) is not None:
                    pm25_value = data_row.get(key)
                    break

            # Normalize numeric types: convert Decimal or numeric strings to float
            try:
                if pm25_value is not None:
                    pm25_value = float(pm25_value)
                    pm25_value = round(pm25_value, 2)
            except Exception:
                pass

            # Legacy function field mapping
            returned_code = data_row.get("code") or data_row.get("location_code")
            returned_location_name = data_row.get("location") or data_row.get("location_name")

            return {
                "success": True,
                "pm25_value": pm25_value,
                "timestamp": data_row.get("timestamp"),
                "station_count": data_row.get("station_count"),
                "measurement_type": data_row.get("measurement_type"),
                "location": {
                    "name": location_name or returned_location_name,
                    "code": location_code or returned_code,
                    "level": location_level
                },
                "raw_data": data_row,
                "method": "legacy"  # Indicate this was from legacy function
            }
            
        except Exception as e:
            return self.handle_error(e, {
                "location_code": location_code,
                "location_level": location_level,
                "method": "legacy"
            })