# src/agents/instructlab_parser.py
import asyncio
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
import aiohttp
from .query_parser import ParsedQuery

@dataclass
class InstructLabConfig:
    model_path: str = "models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
    endpoint: str = "http://localhost:8000/v1/chat/completions"  # InstructLab endpoint
    temperature: float = 0.1  # Low for consistency
    max_tokens: int = 150

class InstructLabParser:
    """LLM-based query parser using InstructLab"""
    
    def __init__(self, config: Optional[InstructLabConfig] = None):
        self.config = config or InstructLabConfig()
        self.prompt_template = self._load_prompt_template()
        
    def _load_prompt_template(self) -> str:
        """Load the prompt template for query parsing"""
        return """You are a query parser for an air quality monitoring system.
        
Available database functions:
1. gis.search_location_json(location_text) - Search for location
2. gis.get_current_pm25(code, level) - Get current PM2.5 value
3. gis.get_pm25_trend(code, level, duration, unit) - Get historical trend

Parse the user query and extract:
- intent: current_reading|trend|comparison|forecast|hotspot|unknown
- location: the location mentioned
- metric: pm25|aqi|no2|so2 (default: pm25)
- duration: number (if time period mentioned)
- unit: hours|days|weeks|months

User Query: {query}

Return JSON only:"""

    async def parse(self, query: str) -> ParsedQuery:
        """Parse query using InstructLab model"""
        prompt = self.prompt_template.format(query=query)
        
        try:
            response = await self._call_instructlab(prompt)
            parsed = self._extract_json(response)
            
            return ParsedQuery(
                intent=parsed.get('intent', 'unknown'),
                entities=parsed.get('entities', {}),
                confidence=parsed.get('confidence', 0.7),
                raw_query=query
            )
        except Exception as e:
            # Fallback response
            return ParsedQuery(
                intent='unknown',
                entities={'query': query, 'error': str(e)},
                confidence=0.0,
                raw_query=query
            )