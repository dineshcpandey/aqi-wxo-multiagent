# src/graphs/pm_forecast_workflow.py
from typing import Dict, Any, Optional, TypedDict, List, Tuple
import re


class PMForecastState(TypedDict):
    user_query: str
    location_search_term: str
    locations: List[Dict[str, Any]]
    needs_disambiguation: bool
    selected_location: Optional[Dict[str, Any]]
    forecast_data: Optional[Dict[str, Any]]
    response: str
    error: Optional[str]
    waiting_for_user: bool


class PMForecastWorkflow:
    """Workflow to resolve location and fetch PM2.5 forecast values."""

    def __init__(self, location_agent, forecast_agent):
        self.location_agent = location_agent
        self.forecast_agent = forecast_agent

    def _extract_location_from_query(self, query: str) -> str:
        """Extract location from natural language query with improved logic"""
        # Clean the query
        q = query.lower().strip()
        q = q.replace('?', '').replace('!', '').replace('.', '')
        
        print(f"[ForecastWorkflow] Original query: '{query}'")
        print(f"[ForecastWorkflow] Cleaned query: '{q}'")
        
        # Method 1: Look for location after prepositions
        prepositions = [" in ", " at ", " for ", " of ", " near ", " around "]
        for prep in prepositions:
            if prep in q:
                parts = q.split(prep)
                # Take the last part after the preposition
                location = parts[-1].strip()
                # Remove timeline words from location
                location = re.sub(r'\s+(tomorrow|next \d+ days?|week|days?)$', '', location)
                if location and len(location) > 1:
                    print(f"[ForecastWorkflow] Found location after '{prep.strip()}': '{location}'")
                    return location
        
        # Method 2: Look for location after forecast-related keywords
        forecast_patterns = [
            r"(?:forecast|predicted?|tomorrow|future)\s+(?:pm2\.5|pm25|pm|aqi|air quality)\s+(?:in|at|for|of)?\s*(.+)",
            r"(?:pm2\.5|pm25|pm|aqi)\s+(?:forecast|prediction|tomorrow)\s+(?:in|at|for)?\s*(.+)",
            r"(?:what will be|what's the)\s+(?:pm2\.5|pm25|pm|aqi)\s+(?:in|at|for)?\s*(.+)"
        ]
        
        for pattern in forecast_patterns:
            match = re.search(pattern, q)
            if match:
                location = match.group(1).strip()
                # Remove trailing forecast words
                location = re.sub(r'\s+(tomorrow|next \d+ days?|forecast|prediction|week|days?)$', '', location)
                if location and len(location) > 1:
                    print(f"[ForecastWorkflow] Found location via forecast pattern: '{location}'")
                    return location
        
        # Method 3: If query starts with a location pattern
        if not any(word in q[:20] for word in ['what', 'show', 'tell', 'get', 'find', 'how']):
            words = q.split()
            if len(words) >= 2:
                # Check if forecast-related word is at the end
                if any(word in words[-2:] for word in ['forecast', 'tomorrow', 'prediction', 'future']):
                    location = ' '.join(words[:-2])
                    print(f"[ForecastWorkflow] Found location at start: '{location}'")
                    return location
        
        # Method 4: Last resort - take the last significant words
        common_words = ['what', 'is', 'the', 'show', 'me', 'tell', 'get', 'find', 
                       'current', 'latest', 'now', 'today', 'level', 'levels', 
                       'reading', 'value', 'please', 'can', 'you', 'will', 'be',
                       'forecast', 'prediction', 'tomorrow', 'future', 'next']
        
        words = q.split()
        filtered_words = [w for w in words if w not in common_words and len(w) > 2]
        
        if filtered_words:
            # Remove PM-related words
            pm_words = ['pm2.5', 'pm25', 'pm', 'aqi', 'air', 'quality']
            location_words = [w for w in filtered_words if w not in pm_words]
            
            if location_words:
                location = ' '.join(location_words)
                print(f"[ForecastWorkflow] Extracted via word filtering: '{location}'")
                return location
        
        print(f"[ForecastWorkflow] No location found in query")
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

    def _format_forecast_response(self, forecast_data: Dict, location: Dict) -> Dict:
        """Format forecast data into a user-friendly response with chart data"""
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
        from agents.response_formatter import ResponseFormatter
        
        # Prepare data for response formatter
        formatter_data = {
            **forecast_data,
            'location': location
        }
        
        # Use response formatter to handle text and chart generation
        formatter = ResponseFormatter()
        formatted_response = formatter.format_response("forecast", formatter_data)
        
        return formatted_response

    async def process_query(self, query: str) -> PMForecastState:
        """Process user query and return forecast data or disambiguation options"""
        print(f"[ForecastWorkflow] Processing new query: '{query}'")
        
        state: PMForecastState = {
            "user_query": query,
            "location_search_term": "",
            "locations": [],
            "needs_disambiguation": False,
            "selected_location": None,
            "forecast_data": None,
            "response": "",
            "error": None,
            "waiting_for_user": False
        }
        
        # Extract location from query
        location_term = self._extract_location_from_query(query)
        if not location_term:
            state["error"] = "Could not identify a location in your query. Please specify a location for the forecast."
            return state
        
        state["location_search_term"] = location_term
        print(f"[ForecastWorkflow] Searching for location: '{location_term}'")
        
        # Search for locations
        location_result = await self.location_agent.run({"location_query": location_term})
        
        if not location_result.get("success"):
            state["error"] = location_result.get("error", "Location search failed")
            return state
        
        locations = location_result.get("locations", [])
        state["locations"] = locations
        
        print(f"[ForecastWorkflow] Found {len(locations)} location(s)")
        
        if not locations:
            state["error"] = f"No locations found matching '{location_term}'"
            return state
        
        # Check if disambiguation is needed
        needs_disambiguation = location_result.get("needs_disambiguation", len(locations) > 1)
        state["needs_disambiguation"] = needs_disambiguation
        
        if needs_disambiguation:
            print(f"[ForecastWorkflow] Needs disambiguation: {needs_disambiguation}")
            print(f"[ForecastWorkflow] Waiting for user to select from {len(locations)} options")
            state["waiting_for_user"] = True
            return state
        
        # Single location found, proceed with forecast
        loc = locations[0]
        state["selected_location"] = loc
        
        # Fetch forecast data
        print(f"[ForecastWorkflow] Fetching forecast data for code={loc.get('code')}, level={loc.get('level')}")
        
        forecast_result = await self.forecast_agent.run({
            "location": loc,
            "query": query  # Pass original query to extract days
        })
        
        if not forecast_result.get("success"):
            state["error"] = forecast_result.get("error", "Failed to fetch forecast data")
            state["response"] = f"❌ Could not retrieve PM2.5 forecast for {loc.get('name')}. The forecasting service might be unavailable."
            return state
        
        state["forecast_data"] = forecast_result
        
        # Format response
        formatted_response = self._format_forecast_response(forecast_result, loc)
        state["response"] = formatted_response.get("text_response", "")
        state["chart_data"] = formatted_response.get("chart_data")
        state["has_chart"] = formatted_response.get("has_chart", False)
        state["chart_type"] = formatted_response.get("chart_type")
        print(f"[ForecastWorkflow] Successfully generated forecast response with chart: {state['has_chart']}")
        
        return state

    async def continue_with_selection(self, state: PMForecastState, selected_idx: int) -> PMForecastState:
        """Continue workflow after user selects from disambiguation options"""
        print(f"\n[ForecastWorkflow] Continuing with user selection: index={selected_idx}")
        
        # Validate selection
        locations = state.get("locations", [])
        if not locations or selected_idx < 0 or selected_idx >= len(locations):
            state["error"] = "Invalid location selection"
            return state
        
        # Set selected location
        state["selected_location"] = state["locations"][selected_idx]
        state["waiting_for_user"] = False
        
        loc = state["selected_location"]
        print(f"[ForecastWorkflow] User selected: {loc.get('name')} ({loc.get('level')})")
        
        # Fetch forecast data for selected location
        print(f"[ForecastWorkflow] Fetching forecast data for code={loc.get('code')}, level={loc.get('level')}")
        
        forecast_result = await self.forecast_agent.run({
            "location": loc,
            "query": state["user_query"]  # Pass original query to extract days
        })
        
        if not forecast_result.get("success"):
            state["error"] = forecast_result.get("error", "Failed to fetch forecast data")
            state["response"] = f"❌ Could not retrieve PM2.5 forecast for {loc.get('name')}. The forecasting service might be unavailable."
            return state
        
        state["forecast_data"] = forecast_result
        
        # Format response
        formatted_response = self._format_forecast_response(forecast_result, loc)
        state["response"] = formatted_response.get("text_response", "")
        state["chart_data"] = formatted_response.get("chart_data")
        state["has_chart"] = formatted_response.get("has_chart", False)
        state["chart_type"] = formatted_response.get("chart_type")
        print(f"[ForecastWorkflow] Successfully generated forecast response after selection with chart: {state['has_chart']}")
        
        return state