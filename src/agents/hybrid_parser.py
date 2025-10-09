# src/agents/hybrid_parser.py
from typing import Dict, Any, Optional
import asyncio
from .query_parser import QueryParser, ParsedQuery
from .instructlab_parser import InstructLabParser
from src.utils.monitoring import QueryMonitor

class HybridQueryParser:
    """Combines regex and LLM parsing with shadow mode support"""
    
    def __init__(self, shadow_mode: bool = True):
        self.regex_parser = QueryParser()
        self.llm_parser = InstructLabParser()
        self.shadow_mode = shadow_mode
        self.monitor = QueryMonitor()
        self.comparison_log = []
        
    async def parse(self, query: str) -> ParsedQuery:
        """Parse with regex first, optionally shadow with LLM"""
        
        # Always run regex parser
        regex_result = self.regex_parser.parse(query)
        
        if self.shadow_mode:
            # Run LLM in background without blocking
            asyncio.create_task(self._shadow_parse(query, regex_result))
            return regex_result
        else:
            # Production mode: use confidence threshold
            if regex_result.confidence >= 0.85:
                return regex_result
            else:
                # Low confidence - use LLM
                llm_result = await self.llm_parser.parse(query)
                await self._log_comparison(query, regex_result, llm_result)
                return llm_result
    
    async def _shadow_parse(self, query: str, regex_result: ParsedQuery):
        """Run LLM parsing in shadow mode for comparison"""
        try:
            llm_result = await self.llm_parser.parse(query)
            await self._log_comparison(query, regex_result, llm_result)
        except Exception as e:
            await self.monitor.log_error(e, {"query": query, "mode": "shadow"})