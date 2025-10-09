# src/training/comparison_logger.py
import json
from datetime import datetime
from pathlib import Path

class ParserComparisonLogger:
    """Log differences between regex and LLM parsing for analysis"""
    
    def __init__(self, log_dir: str = "logs/parser_comparison"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_file = self.log_dir / f"comparison_{datetime.now():%Y%m%d}.jsonl"
    
    async def log(self, query: str, regex_result: ParsedQuery, llm_result: ParsedQuery):
        """Log parsing comparison"""
        comparison = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "regex": {
                "intent": regex_result.intent,
                "entities": regex_result.entities,
                "confidence": regex_result.confidence
            },
            "llm": {
                "intent": llm_result.intent,
                "entities": llm_result.entities,
                "confidence": llm_result.confidence
            },
            "agreement": regex_result.intent == llm_result.intent,
            "entity_match": regex_result.entities == llm_result.entities
        }
        
        async with aiofiles.open(self.current_file, 'a') as f:
            await f.write(json.dumps(comparison) + '\n')