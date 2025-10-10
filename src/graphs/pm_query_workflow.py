# src/graphs/pm_query_workflow.py
from typing import Dict, Any, Optional, TypedDict, List, Tuple
import re


class PMQueryState(TypedDict):
    user_query: str
    location_search_term: str
    locations: List[Dict[str, Any]]
    needs_disambiguation: bool
    selected_location: Optional[Dict[str, Any]]
    pm_data: Optional[Dict[str, Any]]
    response: str
    error: Optional[str]
    waiting_for_user: bool


class PMQueryWorkflow:
    """Workflow to resolve location and fetch PM2.5 values with improved location extraction."""

    def __init__(self, location_agent, pm_agent):
        self.location_agent = location_agent
        self.pm_agent = pm_agent

    def _extract_location_from_query(self, query: str) -> str:
        """Extract location from natural language query with improved logic"""
        # Clean the query
        q = query.lower().strip()
        q = q.replace('?', '').replace('!', '').replace('.', '')
        
        print(f"[Workflow] Original query: '{query}'")
        print(f"[Workflow] Cleaned query: '{q}'")
        
        # Method 1: Look for location after prepositions
        prepositions = [" in ", " at ", " for ", " of ", " near ", " around "]
        for prep in prepositions:
            if prep in q:
                parts = q.split(prep)
                # Take the last part after the preposition
                location = parts[-1].strip()
                if location and len(location) > 1:
                    print(f"[Workflow] Found location after '{prep.strip()}': '{location}'")
                    return location
        
        # Method 2: Look for location after PM-related keywords
        pm_patterns = [
            r"(?:pm2\.5|pm25|pm 2\.5|pm|aqi|air quality)\s+(?:in|at|for|of)?\s*(.+)",
            r"(?:current|latest|show|what is|what's the)\s+(?:pm2\.5|pm25|pm|aqi)\s+(?:in|at|for)?\s*(.+)",
            r"(?:pm2\.5|pm25|pm|aqi)\s+(?:level|levels|reading|value)?\s*(?:in|at|for)?\s*(.+)"
        ]
        
        for pattern in pm_patterns:
            match = re.search(pattern, q)
            if match:
                location = match.group(1).strip()
                # Remove trailing words like "level", "reading", etc.
                location = re.sub(r'\s+(level|levels|reading|value|now|today|current)$', '', location)
                if location and len(location) > 1:
                    print(f"[Workflow] Found location via pattern: '{location}'")
                    return location
        
        # Method 3: If query starts with a location pattern
        if not any(word in q[:20] for word in ['what', 'show', 'tell', 'get', 'find', 'how']):
            # Might be direct location query like "Delhi PM2.5"
            words = q.split()
            if len(words) >= 2:
                # Check if PM-related word is at the end
                if any(pm in words[-1] for pm in ['pm', 'pm2.5', 'pm25', 'aqi']):
                    location = ' '.join(words[:-1])
                    print(f"[Workflow] Found location at start: '{location}'")
                    return location
        
        # Method 4: Last resort - take the last significant words
        # Remove common query words
        common_words = ['what', 'is', 'the', 'show', 'me', 'tell', 'get', 'find', 
                       'current', 'latest', 'now', 'today', 'level', 'levels', 
                       'reading', 'value', 'please', 'can', 'you']
        
        words = q.split()
        filtered_words = [w for w in words if w not in common_words and len(w) > 2]
        
        if filtered_words:
            # Remove PM-related words
            pm_words = ['pm2.5', 'pm25', 'pm', 'aqi', 'air', 'quality']
            location_words = [w for w in filtered_words if w not in pm_words]
            
            if location_words:
                location = ' '.join(location_words)
                print(f"[Workflow] Extracted via word filtering: '{location}'")
                return location
        
        print(f"[Workflow] No location found in query")
        return ""

    def _get_air_quality_category(self, pm25_value: Optional[float]) -> Tuple[str, str]:
        """Get air quality category and emoji based on PM2.5 value"""
        if pm25_value is None:
            return "Unknown", "❓"
        if pm25_value <= 30:
            return "Good", "🟢"
        if pm25_value <= 60:
            return "Satisfactory", "🟡"
        if pm25_value <= 90:
            return "Moderate", "🟠"
        if pm25_value <= 120:
            return "Poor", "🔴"
        if pm25_value <= 250:
            return "Very Poor", "🟣"
        return "Severe", "🟤"

    def _format_pm_response(self, pm_data: Dict, location: Dict) -> str:
        """Format PM data into a user-friendly response"""
        pm_value = pm_data.get("pm25_value")
        category, emoji = self._get_air_quality_category(pm_value)
        
        location_name = location.get("name", "Unknown")
        location_level = location.get("level", "")
        
        # Format PM value
        if pm_value is None:
            pm_text = "N/A"
        else:
            try:
                pm_text = f"{pm_value:.1f}"
            except:
                pm_text = str(pm_value)
        
        # Build response
        response = f"{emoji} **PM2.5 in {location_name}**\n\n"
        response += f"📊 **Current Level:** {pm_text} µg/m³\n"
        response += f"📈 **Air Quality:** {category}\n"
        
        if location_level:
            response += f"📍 **Location Type:** {location_level.replace('_', ' ').title()}\n"
        
        # Add timestamp if available
        if pm_data.get("timestamp"):
            response += f"🕐 **Last Updated:** {pm_data['timestamp']}\n"
        
        # Add station count if available
        if pm_data.get("station_count"):
            response += f"📡 **Data Sources:** {pm_data['station_count']} monitoring stations\n"
        
        # Add health advisory for poor air quality
        if pm_value and pm_value > 90:
            response += "\n⚠️ **Health Advisory:**\n"
            if pm_value > 250:
                response += "- Avoid all outdoor activities\n- Keep windows closed\n- Use air purifiers if available"
            elif pm_value > 120:
                response += "- Limit prolonged outdoor activities\n- Sensitive groups should stay indoors"
            else:
                response += "- Sensitive individuals should limit outdoor exposure"
        
        return response

    async def process_query(self, query: str) -> PMQueryState:
        """Process a natural language query about PM2.5"""
        print(f"\n[Workflow] Processing new query: '{query}'")
        
        # Initialize state
        state: PMQueryState = {
            "user_query": query,
            "location_search_term": "",
            "locations": [],
            "needs_disambiguation": False,
            "selected_location": None,
            "pm_data": None,
            "response": "",
            "error": None,
            "waiting_for_user": False,
        }
        
        # Extract location from query
        location_term = self._extract_location_from_query(query)
        state["location_search_term"] = location_term
        
        if not location_term:
            state["error"] = "Could not identify a location in your query. Please specify a location."
            state["response"] = "❌ I couldn't identify a location in your query. Please try asking with a specific location, like 'What is PM2.5 in Delhi?'"
            return state
        
        # Resolve location
        print(f"[Workflow] Searching for location: '{location_term}'")
        location_result = await self.location_agent.run({"location_query": location_term})
        
        if not location_result.get("success"):
            state["error"] = location_result.get("error", "Location search failed")
            state["response"] = f"❌ Could not find location '{location_term}'. Please check the spelling and try again."
            return state
        
        state["locations"] = location_result.get("locations", [])
        state["needs_disambiguation"] = location_result.get("needs_disambiguation", False)
        
        print(f"[Workflow] Found {len(state['locations'])} location(s)")
        print(f"[Workflow] Needs disambiguation: {state['needs_disambiguation']}")
        
        # Check if we need user input for disambiguation
        if state["needs_disambiguation"] and len(state["locations"]) > 1:
            state["waiting_for_user"] = True
            print(f"[Workflow] Waiting for user to select from {len(state['locations'])} options")
            return state
        
        # Single location or no disambiguation needed
        if state["locations"]:
            state["selected_location"] = state["locations"][0]
            print(f"[Workflow] Selected location: {state['selected_location'].get('name')} ({state['selected_location'].get('level')})")
        else:
            state["error"] = "No location found"
            state["response"] = f"❌ Location '{location_term}' not found in our database."
            return state
        
        # Fetch PM data
        loc = state["selected_location"]
        print(f"[Workflow] Fetching PM data for code={loc.get('code')}, level={loc.get('level')}")

        
        pm_result = await self.pm_agent.run({
            "location_code": loc.get("code"),
            "location_level": loc.get("level"),
            "location_name": loc.get("name"),
        })
        
        if not pm_result.get("success"):
            state["error"] = pm_result.get("error", "Failed to fetch PM data")
            state["response"] = f"❌ Could not retrieve PM2.5 data for {loc.get('name')}. The monitoring station might be offline or data unavailable."
            return state
        
        state["pm_data"] = pm_result
        
        # Format response
        state["response"] = self._format_pm_response(pm_result, loc)
        print(f"[Workflow] Successfully generated response")
        
        return state

    async def continue_with_selection(self, state: PMQueryState, selected_idx: int) -> PMQueryState:
        """Continue workflow after user selects from disambiguation options"""
        print(f"\n[Workflow] Continuing with user selection: index={selected_idx}")
        
        # Validate selection
        if not state.get("locations"):
            state["error"] = "No locations to select from"
            state["response"] = "❌ Error: No locations available for selection."
            return state
        
        if selected_idx < 0 or selected_idx >= len(state["locations"]):
            state["error"] = f"Invalid selection index: {selected_idx}"
            state["response"] = f"❌ Error: Invalid selection. Please choose a number between 1 and {len(state['locations'])}."
            return state
        
        # Set selected location
        state["selected_location"] = state["locations"][selected_idx]
        state["waiting_for_user"] = False
        
        loc = state["selected_location"]
        print(f"[Workflow] User selected: {loc.get('name')} ({loc.get('level')})")
        
        # Fetch PM data for selected location
        print(f"[Workflow] Fetching PM data for code={loc.get('code')}, level={loc.get('level')}")
        
        pm_result = await self.pm_agent.run({
            "location_code": loc.get("code"),
            "location_level": loc.get("level"),
            "location_name": loc.get("name"),
        })
        
        if not pm_result.get("success"):
            state["error"] = pm_result.get("error", "Failed to fetch PM data")
            state["response"] = f"❌ Could not retrieve PM2.5 data for {loc.get('name')}. The monitoring station might be offline or data unavailable."
            return state
        
        state["pm_data"] = pm_result
        
        # Format response
        state["response"] = self._format_pm_response(pm_result, loc)
        print(f"[Workflow] Successfully generated response after selection")
        
        return state
