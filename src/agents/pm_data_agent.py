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
        Fetch PM2.5 data using gis.get_current_pm25(code, level)
        """
        print(f"PMDataAgent.run called with input: {input_data}")
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
        
        self.log(f"Fetching PM2.5 for {location_name} (code: {location_code}, level: {location_level})")
        
        try:
            # Call your PM2.5 function
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

            # Different DB versions may return different column names.
            # Normalize to a stable shape consumed by workflows/UI.
            # Possible names: 'pm25_value', 'current_pm25', 'current_pm25_value', 'value'
            # Also accept wrapper names like {'get_current_pm25': {...}}
            data_row = None
            if isinstance(raw, dict) and len(raw) == 1:
                # Some drivers return a single column named after the function
                first_val = next(iter(raw.values()))
                if isinstance(first_val, dict):
                    data_row = first_val
            if data_row is None:
                data_row = raw

            # Extract pm25 value from known keys
            pm25_value = None
            for key in ("pm25_value", "current_pm25", "current_pm25_value", "value", "avg_value"):
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

            # Also support a top-level 'code' and 'location' keys returned by DB
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
                "raw_data": data_row
            }
            
        except Exception as e:
            return self.handle_error(e, {
                "location_code": location_code,
                "location_level": location_level
            })