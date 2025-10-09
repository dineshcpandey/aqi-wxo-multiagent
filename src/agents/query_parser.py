# src/agents/query_parser.py
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass
class ParsedQuery:
    intent: str
    entities: Dict[str, Any]
    confidence: float
    raw_query: str
    
class QueryParser:
    def __init__(self):
        self.location_keywords = set()  # Load from DB
        self.metric_synonyms = {
            'pm': 'pm25', 'pm2.5': 'pm25', 'pm25': 'pm25',
            'aqi': 'aqi', 'air quality': 'aqi', 'air quality index': 'aqi',
            'no2': 'no2', 'nitrogen': 'no2',
            'so2': 'so2', 'sulfur': 'so2',
            'ozone': 'o3', 'o3': 'o3'
        }
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for different query types"""
        self.patterns = {
            'current_reading': [
                (r"(?:what(?:'s| is)|show me|tell me) (?:the )?(?:current |latest |present )?(\w+)(?: level| reading)? (?:in|at|for) ([\w\s]+?)(?:\?|$)", 2),
                (r"(\w+) in ([\w\s]+?)(?:\?|$)", 2),
                (r"([\w\s]+?) (\w+) level", 2)
            ],
            'trend': [
                (r"(?:show |display |get )?(\w+) (?:trend|history|pattern) (?:for |in )?([\w\s]+?) (?:for |over )?(?:the )?(?:last|past) (\d+) (\w+)", 4),
                (r"([\w\s]+?) (\w+) (?:for |over )?(?:the )?(?:last|past) (\d+) (\w+)", 4),
                (r"how (?:has |did )(\w+) (?:changed?|varied) in ([\w\s]+?) (?:over |in )?(?:the )?(?:last|past) (\d+) (\w+)", 4)
            ],
            'comparison': [
                (r"compare (\w+) (?:between |in |across )([\w\s]+?) (?:and|with|vs) ([\w\s]+)", 3),
                (r"([\w\s]+?) vs\.? ([\w\s]+?)(?: for)? (\w+)", 3),
                (r"which (?:is |has )(?:better|worse|higher|lower)(?: \w+)? ([\w\s]+?) or ([\w\s]+)", 2)
            ],
            'forecast': [
                (r"(?:what will|predict|forecast|expected) (\w+) (?:be |in |for )?([\w\s]+?) (?:tomorrow|today|next (\d+) (\w+))", 4),
                (r"([\w\s]+?) (\w+) forecast(?: for)? (?:next |coming )?(\d+)? ?(\w+)?", 4),
                (r"will (\w+) (?:increase|decrease|improve|worsen) in ([\w\s]+)", 2)
            ],
            'hotspot': [
                (r"(?:show |find |get )?(?:pollution |air quality )?hotspots? (?:in |for |around )?([\w\s]+)?", 1),
                (r"(?:most |least )polluted (?:areas?|locations?|places?) (?:in |around )?([\w\s]+)?", 1),
                (r"where (?:is |are )(?:the )?(?:worst|best) air quality (?:in |around )?([\w\s]+)?", 1)
            ],
            'alert': [
                (r"(?:is |are )?([\w\s]+?) (?:safe|dangerous|hazardous|unhealthy)", 1),
                (r"should I (?:go out|exercise|wear mask) in ([\w\s]+)", 1),
                (r"health (?:advisory|alert|warning) (?:for |in )?([\w\s]+)", 1)
            ]
        }
    
    def parse(self, query: str) -> ParsedQuery:
        """Parse query and extract intent and entities"""
        query_lower = query.lower().strip()
        
        # Try each pattern type
        for intent, patterns in self.patterns.items():
            for pattern_tuple in patterns:
                pattern = pattern_tuple[0]
                expected_groups = pattern_tuple[1] if len(pattern_tuple) > 1 else 1
                
                match = re.search(pattern, query_lower)
                if match:
                    entities = self._extract_entities(match, intent, expected_groups)
                    confidence = self._calculate_confidence(query_lower, intent, entities)
                    
                    return ParsedQuery(
                        intent=intent,
                        entities=entities,
                        confidence=confidence,
                        raw_query=query
                    )
        
        # No pattern matched
        return ParsedQuery(
            intent='unknown',
            entities={'query': query},
            confidence=0.0,
            raw_query=query
        )
    
    def _extract_entities(self, match: re.Match, intent: str, expected_groups: int) -> Dict[str, Any]:
        """Extract entities based on intent type"""
        groups = match.groups()
        entities = {}
        
        if intent == 'current_reading':
            if len(groups) >= 2:
                entities['metric'] = self._normalize_metric(groups[0])
                entities['location'] = groups[1].strip()
                
        elif intent == 'trend':
            if len(groups) >= 4:
                entities['metric'] = self._normalize_metric(groups[0]) if not groups[0].strip() in self.location_keywords else 'pm25'
                entities['location'] = groups[1].strip() if groups[1].strip() not in self.metric_synonyms else groups[0].strip()
                entities['duration'] = int(groups[2])
                entities['unit'] = self._normalize_time_unit(groups[3])
                
        elif intent == 'comparison':
            if len(groups) >= 2:
                entities['locations'] = [groups[i].strip() for i in range(min(3, len(groups))) if groups[i]]
                entities['metric'] = self._extract_metric_from_query(match.string) or 'pm25'
                
        elif intent == 'forecast':
            entities['metric'] = 'pm25'  # default
            entities['location'] = groups[0].strip() if groups[0] else None
            if len(groups) >= 3 and groups[2]:
                entities['duration'] = int(groups[2])
                entities['unit'] = self._normalize_time_unit(groups[3]) if len(groups) > 3 else 'hours'
            else:
                entities['duration'] = 24
                entities['unit'] = 'hours'
                
        elif intent in ['hotspot', 'alert']:
            entities['location'] = groups[0].strip() if groups[0] else None
            entities['metric'] = 'pm25'  # default for air quality
            
        return entities
    
    def _normalize_metric(self, metric_str: str) -> str:
        """Normalize metric names"""
        metric_lower = metric_str.lower().strip()
        return self.metric_synonyms.get(metric_lower, metric_lower)
    
    def _normalize_time_unit(self, unit: str) -> str:
        """Normalize time units to standard format"""
        unit_lower = unit.lower().strip()
        unit_map = {
            'hour': 'hours', 'hours': 'hours', 'hr': 'hours', 'hrs': 'hours',
            'day': 'days', 'days': 'days', 'd': 'days',
            'week': 'weeks', 'weeks': 'weeks', 'wk': 'weeks', 'wks': 'weeks',
            'month': 'months', 'months': 'months', 'mo': 'months',
            'year': 'years', 'years': 'years', 'yr': 'years', 'yrs': 'years'
        }
        return unit_map.get(unit_lower, unit_lower)
    
    def _extract_metric_from_query(self, query: str) -> Optional[str]:
        """Extract metric from anywhere in the query"""
        query_lower = query.lower()
        for synonym, metric in self.metric_synonyms.items():
            if synonym in query_lower:
                return metric
        return None
    
    def _calculate_confidence(self, query: str, intent: str, entities: Dict) -> float:
        """Calculate confidence score for the parse"""
        confidence = 0.8  # Base confidence for pattern match
        
        # Boost confidence if all required entities are present
        if intent == 'current_reading' and entities.get('location') and entities.get('metric'):
            confidence = 0.95
        elif intent == 'trend' and all(k in entities for k in ['location', 'duration', 'unit']):
            confidence = 0.9
        elif intent == 'comparison' and len(entities.get('locations', [])) >= 2:
            confidence = 0.9
            
        return confidence