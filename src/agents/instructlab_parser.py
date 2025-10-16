# src/agents/instructlab_parser.py
import asyncio
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
import aiohttp
from .query_parser import ParsedQuery

@dataclass
class FineTunedModelConfig:
    endpoint: str = "http://localhost:8000/inference"  # Fine-tuned model inference endpoint
    temperature: float = 0.1  # Low for consistency
    max_tokens: int = 150
    model_name: str = "air-quality-parser"  # Fine-tuned model name

class FineTunedParser:
    """LLM-based query parser using fine-tuned model"""
    
    def __init__(self, config: Optional[FineTunedModelConfig] = None):
        self.config = config or FineTunedModelConfig()
        self.prompt_template = self._load_prompt_template()
        
    def _load_prompt_template(self) -> str:
        """Load the prompt template for fine-tuned model (matches training format)"""
        return "### Question: {query}\n\n### Answer: "

    async def parse(self, query: str) -> ParsedQuery:
        """Parse query using fine-tuned model"""
        prompt = self.prompt_template.format(query=query)
        
        try:
            response = await self._call_finetuned_model(prompt)
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
    
    async def _call_finetuned_model(self, prompt: str) -> str:
        """Make API call to fine-tuned model using query parameter"""
        import urllib.parse
        
        # Extract just the query from the prompt (remove "### Question: " and "### Answer: ")
        query = prompt.replace("### Question: ", "").replace("\n\n### Answer: ", "")
        
        # URL encode the query for the parameter
        encoded_query = urllib.parse.quote(f'"{query}"')
        
        # Build the full URL with query parameter
        url = f"{self.config.endpoint}?query={encoded_query}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    # Handle your specific response format: {"message": "JSON_STRING"}
                    if isinstance(result, dict) and "message" in result:
                        return result["message"].strip()
                    elif isinstance(result, dict):
                        # If response is already a dict (JSON), return it as string for _extract_json
                        return json.dumps(result)
                    elif isinstance(result, str):
                        return result.strip()
                    else:
                        # Fallback: return the whole response as string
                        return str(result)
                else:
                    raise Exception(f"Fine-tuned model API error: {response.status}")
    
    def _extract_json(self, response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response"""
        try:
            # Try to parse the entire response as JSON
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to find JSON within the response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            # Fallback: manual parsing for common patterns
            return self._manual_parse(response)
    
    def _manual_parse(self, response: str) -> Dict[str, Any]:
        """Manual parsing as fallback"""
        result = {
            "intent": "unknown",
            "entities": {},
            "confidence": 0.5
        }
        
        # Simple pattern matching
        if "current" in response.lower() or "pm" in response.lower():
            result["intent"] = "current_reading"
            result["confidence"] = 0.6
        elif "trend" in response.lower() or "history" in response.lower():
            result["intent"] = "trend"
            result["confidence"] = 0.6
        elif "compare" in response.lower() or "vs" in response.lower():
            result["intent"] = "comparison"
            result["confidence"] = 0.6
        
        return result