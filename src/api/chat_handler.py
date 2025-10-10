from typing import Dict, Any, Optional
import re

class ChatQueryHandler:
    """Handles chat-specific query processing and response formatting"""
    
    def __init__(self, query_graph):
        self.query_graph = query_graph
        self.context_window = []  # Store recent queries for context
        
    async def process_chat_query(self, 
                                  query: str, 
                                  session_id: Optional[str] = None) -> Dict[str, Any]:
        """Process query with chat-specific enhancements"""
        
        # Check for follow-up patterns
        if self._is_followup(query):
            query = self._expand_followup(query)
        
        # Process through agent system
        result = await self.query_graph.process(query)
        
        # Format for chat display
        formatted_result = self._format_for_chat(result)
        
        # Store context
        self.context_window.append({
            "query": query,
            "result": result
        })
        
        # Keep only last 5 for context
        if len(self.context_window) > 5:
            self.context_window.pop(0)
        
        return formatted_result
    
    def _is_followup(self, query: str) -> bool:
        """Detect if query is a follow-up"""
        followup_patterns = [
            r"^(and |also |what about |how about )",
            r"^(same for |similarly for )",
            r"^(now |then )"
        ]
        return any(re.match(p, query.lower()) for p in followup_patterns)
    
    def _expand_followup(self, query: str) -> str:
        """Expand follow-up query with context"""
        if self.context_window:
            last_query = self.context_window[-1]["query"]
            # Extract location/metric from last query
            # Merge with current query
            # Return expanded query
        return query
    
    def _format_for_chat(self, result: Dict) -> Dict[str, Any]:
        """Format result for chat display"""
        # Add emoji indicators
        if "pm25" in str(result).lower():
            if result.get("value", 0) > 200:
                emoji = "🔴"  # Severe
            elif result.get("value", 0) > 100:
                emoji = "🟠"  # Poor
            else:
                emoji = "🟢"  # Good
        else:
            emoji = "ℹ️"
        
        formatted_response = f"{emoji} {result.get('formatted_response', '')}"
        
        return {
            "formatted_response": formatted_response,
            "raw_data": result.get("data"),
            "confidence": result.get("confidence", 1.0),
            "source": result.get("source"),
            "execution_time_ms": result.get("execution_time_ms")
        }