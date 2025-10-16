# src/agents/hybrid_parser.py
from typing import Dict, Any, Optional, List
import asyncio
import json
import logging
from datetime import datetime
from .query_parser import QueryParser, ParsedQuery
from .instructlab_parser import FineTunedParser

# Configure logger for parsing comparisons
logging.basicConfig(level=logging.INFO)
comparison_logger = logging.getLogger('parsing_comparisons')

# Create file handler for comparison logs
comparison_handler = logging.FileHandler('parsing_comparisons.log')
comparison_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
comparison_handler.setFormatter(formatter)
comparison_logger.addHandler(comparison_handler)

class QueryMonitor:
    """Simple monitor for tracking query parsing performance"""
    
    async def log_error(self, error: Exception, context: Dict[str, Any]):
        """Log parsing errors"""
        logging.error(f"Parsing error: {error}, Context: {context}")

class HybridQueryParser:
    """Combines regex and LLM parsing with shadow mode support"""
    
    def __init__(self, shadow_mode: bool = True):
        self.regex_parser = QueryParser()
        self.llm_parser = FineTunedParser()
        self.shadow_mode = shadow_mode
        self.monitor = QueryMonitor()
        self.comparison_log = []
        
    async def parse(self, query: str) -> ParsedQuery:
        """Parse with regex first, optionally shadow with LLM"""
        
        # Always run regex parser
        regex_result = self.regex_parser.parse(query)
        
        if self.shadow_mode:
            # Run LLM parsing and log comparison
            try:
                llm_result = await self.llm_parser.parse(query)
                await self._log_comparison(query, regex_result, llm_result)
                print(f"[HybridParser] Shadow mode: Logged comparison for '{query[:30]}...'")
            except Exception as e:
                await self.monitor.log_error(e, {"query": query, "mode": "shadow"})
                print(f"[HybridParser] Shadow mode error: {e}")
            
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
    
    async def _log_comparison(self, query: str, regex_result: ParsedQuery, llm_result: ParsedQuery):
        """Log comparison between regex and LLM parsing"""
        comparison = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "regex_result": {
                "intent": regex_result.intent,
                "entities": regex_result.entities,
                "confidence": regex_result.confidence
            },
            "llm_result": {
                "intent": llm_result.intent,
                "entities": llm_result.entities,
                "confidence": llm_result.confidence
            },
            "differences": self._analyze_differences(regex_result, llm_result),
            "llm_better": self._is_llm_better(regex_result, llm_result)
        }
        
        # Log to file
        comparison_logger.info(json.dumps(comparison, indent=2))
        
        # Add to in-memory log for analysis
        self.comparison_log.append(comparison)
        
        # Keep only last 100 comparisons in memory
        if len(self.comparison_log) > 100:
            self.comparison_log = self.comparison_log[-100:]
    
    def _analyze_differences(self, regex_result: ParsedQuery, llm_result: ParsedQuery) -> Dict[str, Any]:
        """Analyze differences between parsing results"""
        differences = {}
        
        # Check intent differences
        if regex_result.intent != llm_result.intent:
            differences["intent"] = {
                "regex": regex_result.intent,
                "llm": llm_result.intent
            }
        
        # Check entity differences
        regex_entities = set(regex_result.entities.keys())
        llm_entities = set(llm_result.entities.keys())
        
        if regex_entities != llm_entities:
            differences["entities"] = {
                "regex_only": list(regex_entities - llm_entities),
                "llm_only": list(llm_entities - regex_entities),
                "common": list(regex_entities & llm_entities)
            }
        
        # Check confidence difference
        conf_diff = abs(regex_result.confidence - llm_result.confidence)
        if conf_diff > 0.1:  # Significant confidence difference
            differences["confidence_diff"] = conf_diff
        
        return differences
    
    def _is_llm_better(self, regex_result: ParsedQuery, llm_result: ParsedQuery) -> bool:
        """Determine if LLM parsing is better than regex"""
        
        # LLM is better if it has higher confidence
        if llm_result.confidence > regex_result.confidence + 0.1:
            return True
        
        # LLM is better if it extracted more entities when regex had low confidence
        if (regex_result.confidence < 0.7 and 
            len(llm_result.entities) > len(regex_result.entities)):
            return True
        
        # LLM is better if it found a valid intent when regex couldn't
        if regex_result.intent == 'unknown' and llm_result.intent != 'unknown':
            return True
        
        return False
    
    def get_comparison_stats(self) -> Dict[str, Any]:
        """Get statistics about parsing comparisons"""
        if not self.comparison_log:
            return {"total_comparisons": 0}
        
        total = len(self.comparison_log)
        llm_better_count = sum(1 for comp in self.comparison_log if comp["llm_better"])
        
        intent_differences = sum(1 for comp in self.comparison_log 
                               if "intent" in comp["differences"])
        
        entity_differences = sum(1 for comp in self.comparison_log 
                               if "entities" in comp["differences"])
        
        return {
            "total_comparisons": total,
            "llm_better_count": llm_better_count,
            "llm_better_percentage": (llm_better_count / total) * 100,
            "intent_differences": intent_differences,
            "entity_differences": entity_differences,
            "avg_regex_confidence": sum(comp["regex_result"]["confidence"] 
                                      for comp in self.comparison_log) / total,
            "avg_llm_confidence": sum(comp["llm_result"]["confidence"] 
                                    for comp in self.comparison_log) / total
        }