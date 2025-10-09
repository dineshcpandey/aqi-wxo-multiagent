# src/agents/pattern_matcher.py
import re
from typing import Dict, Tuple, Optional

class QueryPatternMatcher:
    def __init__(self):
        self.patterns = {
            'current_reading': [
                (r"what(?:'s| is) the (?:current )?(\w+) in (\w+)", ["metric", "location"]),
                (r"show me (?:current )?(\w+) for (\w+)", ["metric", "location"])
            ],
            'time_series': [
                (r"(\w+) trend for (?:the )?last (\d+) (\w+)", ["metric", "duration", "unit"]),
            ],
            'hotspot': [
                (r"(?:show |find )?hotspots in (\w+)", ["location"]),
            ]
        }
    
    def match(self, query: str) -> Tuple[str, Dict[str, str]]:
        query_lower = query.lower()
        
        for intent, patterns in self.patterns.items():
            for pattern, param_names in patterns:
                match = re.search(pattern, query_lower)
                if match:
                    params = dict(zip(param_names, match.groups()))
                    return intent, params
        
        return "unknown", {}
