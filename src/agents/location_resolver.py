# src/agents/location_resolver.py
import json
from typing import Dict, Any, List, Optional
from .agent_base import AgentBase


class LocationResolverAgent(AgentBase):
    """Agent for resolving location queries to specific geographic entities"""
    
    def __init__(self, db_connection):
        super().__init__(name="LocationResolverAgent")
        self.db = db_connection
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calls gis.search_location_json and returns all matches
        """
        query_text = input_data.get("location_query", "").strip()
        
        if not query_text:
            self.log("Empty location query received")
            return {
                "success": False,
                "locations": [],
                "error": "No location query provided"
            }
        
        self.log(f"Searching for location: '{query_text}'")
        
        try:
            # Call your search function
            result = await self.db.execute_query(
                "SELECT gis.search_location_json($1) as locations", 
                [query_text]
            )
            
            if not result or not result[0]['locations']:
                self.log(f"No locations found for query: '{query_text}'")
                return {
                    "success": False,
                    "locations": [],
                    "error": f"No locations found matching '{query_text}'"
                }
            
            # Parse JSON result
            locations = result[0]['locations']
            if isinstance(locations, str):
                locations = json.loads(locations)
            
            # Ensure it's a list
            if not isinstance(locations, list):
                locations = [locations]
            
            self.log(f"Found {len(locations)} location(s) for '{query_text}'")
            
            # Format for disambiguation
            formatted_locations = []
            for loc in locations:
                formatted_location = {
                    "code": loc.get("code", ""),
                    "level": loc.get("level", ""),
                    "name": self._get_location_name(loc),
                    "display_name": self._format_display_name(loc),
                    "state": loc.get("state_name", ""),
                    "district": loc.get("district_name", ""),
                    "parent": loc.get("parent_name", ""),
                   # "raw": loc  # Keep original data
                }
                formatted_locations.append(formatted_location)
                
                self.log(f"  - {formatted_location['display_name']} (code={formatted_location['code']}, level={formatted_location['level']})")
            
            # Determine if disambiguation is needed
            needs_disambiguation = len(formatted_locations) > 1
            
            # If multiple locations at same level with same name, might not need disambiguation
            if needs_disambiguation:
                unique_combinations = set()
                for loc in formatted_locations:
                    unique_combinations.add((loc['name'], loc['level']))
                
                # If all locations are essentially the same, no disambiguation needed
                if len(unique_combinations) == 1:
                    needs_disambiguation = False
                    self.log("Multiple locations found but all are equivalent - no disambiguation needed")
            
            return {
                "success": True,
                "locations": formatted_locations,
                "count": len(formatted_locations),
                "needs_disambiguation": needs_disambiguation,
                "query": query_text
            }
            
        except Exception as e:
            self.log(f"Error searching for location: {e}")
            return self.handle_error(e, {"location_query": query_text})
    
    def _get_location_name(self, location: Dict) -> str:
        """Extract the most appropriate name from location data"""
        # Priority order for name fields
        name_fields = ['name', 'location_name', 'place_name', 'area_name']
        
        for field in name_fields:
            if location.get(field):
                return str(location[field])
        
        # Fallback to code if no name found
        if location.get('code'):
            return f"Location {location['code']}"
        
        return "Unknown Location"
    
    def _format_display_name(self, location: Dict) -> str:
        """Create user-friendly display name with full context"""
        level = location.get('level', '').lower()
        name = self._get_location_name(location)
        
        # Ensure we have a valid name
        if not name or name == "Unknown Location":
            # Try to construct from other fields
            if location.get('code'):
                name = f"Area Code {location['code']}"
            else:
                name = "Unknown Area"
        
        # Build hierarchical display name based on level
        parts = [name]
        
        # Add context based on administrative level
        if level == 'ward':
            # Ward level - show district and state
            if location.get('district_name'):
                parts.append(f"Ward in {location['district_name']}")
            if location.get('state_name'):
                parts.append(location['state_name'])
                
        elif level == 'sub_district' or level == 'subdistrict':
            # Sub-district level
            parts[0] = f"{name} Sub-district"
            if location.get('district_name'):
                parts.append(location['district_name'])
            if location.get('state_name'):
                parts.append(location['state_name'])
                
        elif level == 'district':
            # District level
            parts[0] = f"{name} District"
            if location.get('state_name'):
                parts.append(location['state_name'])
                
        elif level == 'district_hq':
            # District headquarters (city)
            parts[0] = f"{name} City"
            parts.append("District HQ")
            if location.get('state_name'):
                parts.append(location['state_name'])
                
        elif level == 'city':
            # City level
            parts[0] = f"{name} City"
            if location.get('district_name'):
                parts.append(location['district_name'])
            if location.get('state_name'):
                parts.append(location['state_name'])
                
        elif level == 'state':
            # State level
            parts = [f"{name} State"]
            
        else:
            # Unknown level - provide as much context as possible
            if location.get('parent_name'):
                parts.append(location['parent_name'])
            if location.get('district_name') and location['district_name'] not in parts:
                parts.append(location['district_name'])
            if location.get('state_name') and location['state_name'] not in parts:
                parts.append(location['state_name'])
        
        # Join parts with separator
        display_name = " | ".join(filter(None, parts))
        
        # Add emoji prefix based on level
        emoji_map = {
            'state': '🏛️',
            'district': '📍',
            'district_hq': '🏙️',
            'city': '🏙️',
            'sub_district': '📌',
            'subdistrict': '📌',
            'ward': '🏘️',
            'village': '🏡',
            'town': '🏪'
        }
        
        emoji = emoji_map.get(level, '📍')
        display_name = f"{emoji} {display_name}"
        
        return display_name
    
    async def search_by_code(self, code: str, level: str = None) -> Dict[str, Any]:
        """Direct search by location code"""
        self.log(f"Searching by code: {code} (level: {level})")
        
        try:
            # Implement direct code search if your DB supports it
            # This is a placeholder - adjust based on your actual DB schema
            sql = "SELECT * FROM gis.locations WHERE code = $1"
            params = [code]
            
            if level:
                sql += " AND level = $2"
                params.append(level)
            
            result = await self.db.execute_query(sql, params)
            
            if result:
                location = result[0]
                return {
                    "success": True,
                    "location": {
                        "code": location.get("code"),
                        "level": location.get("level"),
                        "name": self._get_location_name(location),
                        "display_name": self._format_display_name(location),
                        "raw": location
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"No location found with code: {code}"
                }
                
        except Exception as e:
            return self.handle_error(e, {"code": code, "level": level})
