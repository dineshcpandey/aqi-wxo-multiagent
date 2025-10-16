# src/training/comparison_logger.py
"""
Logging and analysis utilities for parsing comparison tracking.
This module helps identify where LLM parsing outperforms regex parsing.
"""

import json
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path

class ParseComparisonAnalyzer:
    """Analyze parsing comparisons to identify LLM advantages"""
    
    def __init__(self, log_file_path: str = "parsing_comparisons.log"):
        self.log_file_path = log_file_path
        
    def load_comparisons(self, days_back: int = 7) -> List[Dict[str, Any]]:
        """Load comparison logs from the last N days"""
        comparisons = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        try:
            with open(self.log_file_path, 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('INFO'):
                        # Skip the logging prefix and parse JSON
                        json_start = line.find('{')
                        if json_start > -1:
                            try:
                                comp = json.loads(line[json_start:])
                                comp_date = datetime.fromisoformat(comp['timestamp'])
                                if comp_date >= cutoff_date:
                                    comparisons.append(comp)
                            except json.JSONDecodeError:
                                continue
        except FileNotFoundError:
            print(f"Log file {self.log_file_path} not found")
            
        return comparisons
    
    def analyze_llm_advantages(self, comparisons: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze where LLM performs better than regex"""
        if not comparisons:
            return {"error": "No comparisons found"}
        
        total_comparisons = len(comparisons)
        llm_better_cases = [comp for comp in comparisons if comp.get('llm_better', False)]
        llm_better_count = len(llm_better_cases)
        
        analysis = {
            "summary": {
                "total_comparisons": total_comparisons,
                "llm_better_count": llm_better_count,
                "llm_advantage_rate": (llm_better_count / total_comparisons) * 100,
                "analysis_date": datetime.now().isoformat()
            },
            "llm_advantages": {
                "intent_detection": self._analyze_intent_advantages(llm_better_cases),
                "entity_extraction": self._analyze_entity_advantages(llm_better_cases),
                "confidence_patterns": self._analyze_confidence_patterns(llm_better_cases),
                "query_patterns": self._analyze_query_patterns(llm_better_cases)
            },
            "recommendations": self._generate_recommendations(llm_better_cases)
        }
        
        return analysis
    
    def _analyze_intent_advantages(self, llm_better_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze intent detection advantages"""
        intent_improvements = []
        
        for case in llm_better_cases:
            regex_intent = case['regex_result']['intent']
            llm_intent = case['llm_result']['intent']
            
            if regex_intent != llm_intent:
                intent_improvements.append({
                    "query": case['query'],
                    "regex_intent": regex_intent,
                    "llm_intent": llm_intent,
                    "improvement_type": self._classify_intent_improvement(regex_intent, llm_intent)
                })
        
        return {
            "total_intent_improvements": len(intent_improvements),
            "improvement_types": self._count_improvement_types(intent_improvements),
            "examples": intent_improvements[:5]  # Top 5 examples
        }
    
    def _analyze_entity_advantages(self, llm_better_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze entity extraction advantages"""
        entity_improvements = []
        
        for case in llm_better_cases:
            differences = case.get('differences', {})
            if 'entities' in differences:
                entity_improvements.append({
                    "query": case['query'],
                    "regex_entities": list(case['regex_result']['entities'].keys()),
                    "llm_entities": list(case['llm_result']['entities'].keys()),
                    "llm_only_entities": differences['entities'].get('llm_only', []),
                    "improvement_score": len(differences['entities'].get('llm_only', []))
                })
        
        return {
            "total_entity_improvements": len(entity_improvements),
            "avg_additional_entities": sum(imp['improvement_score'] for imp in entity_improvements) / max(len(entity_improvements), 1),
            "examples": sorted(entity_improvements, key=lambda x: x['improvement_score'], reverse=True)[:5]
        }
    
    def _analyze_confidence_patterns(self, llm_better_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze confidence score patterns"""
        confidence_data = []
        
        for case in llm_better_cases:
            regex_conf = case['regex_result']['confidence']
            llm_conf = case['llm_result']['confidence']
            confidence_data.append({
                "query": case['query'],
                "regex_confidence": regex_conf,
                "llm_confidence": llm_conf,
                "confidence_gap": llm_conf - regex_conf
            })
        
        if confidence_data:
            avg_regex_conf = sum(d['regex_confidence'] for d in confidence_data) / len(confidence_data)
            avg_llm_conf = sum(d['llm_confidence'] for d in confidence_data) / len(confidence_data)
            avg_gap = sum(d['confidence_gap'] for d in confidence_data) / len(confidence_data)
        else:
            avg_regex_conf = avg_llm_conf = avg_gap = 0
        
        return {
            "avg_regex_confidence": avg_regex_conf,
            "avg_llm_confidence": avg_llm_conf,
            "avg_confidence_gap": avg_gap,
            "low_regex_confidence_cases": len([d for d in confidence_data if d['regex_confidence'] < 0.5])
        }
    
    def _analyze_query_patterns(self, llm_better_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze query patterns where LLM excels"""
        query_patterns = {}
        
        for case in llm_better_cases:
            query = case['query'].lower()
            
            # Identify patterns
            if 'complex' in query or len(query.split()) > 8:
                query_patterns['complex_queries'] = query_patterns.get('complex_queries', 0) + 1
            
            if any(word in query for word in ['compare', 'vs', 'versus', 'better', 'worse']):
                query_patterns['comparison_queries'] = query_patterns.get('comparison_queries', 0) + 1
            
            if any(word in query for word in ['trend', 'history', 'past', 'change', 'over time']):
                query_patterns['temporal_queries'] = query_patterns.get('temporal_queries', 0) + 1
            
            if '?' not in query and not query.startswith(('what', 'show', 'get', 'tell')):
                query_patterns['implicit_queries'] = query_patterns.get('implicit_queries', 0) + 1
            
            if any(char.isdigit() for char in query):
                query_patterns['numeric_queries'] = query_patterns.get('numeric_queries', 0) + 1
        
        return query_patterns
    
    def _classify_intent_improvement(self, regex_intent: str, llm_intent: str) -> str:
        """Classify the type of intent improvement"""
        if regex_intent == 'unknown' and llm_intent != 'unknown':
            return "unknown_to_specific"
        elif regex_intent == 'current_reading' and llm_intent in ['trend', 'comparison', 'forecast']:
            return "basic_to_advanced"
        else:
            return "intent_correction"
    
    def _count_improvement_types(self, improvements: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count different types of improvements"""
        types = {}
        for imp in improvements:
            imp_type = imp['improvement_type']
            types[imp_type] = types.get(imp_type, 0) + 1
        return types
    
    def _generate_recommendations(self, llm_better_cases: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        if len(llm_better_cases) == 0:
            recommendations.append("Regex parser performing well. Consider maintaining current approach.")
            return recommendations
        
        # Intent detection improvements
        intent_cases = [case for case in llm_better_cases if 'intent' in case.get('differences', {})]
        if len(intent_cases) > len(llm_better_cases) * 0.3:
            recommendations.append("Consider improving regex patterns for intent detection")
        
        # Entity extraction improvements  
        entity_cases = [case for case in llm_better_cases if 'entities' in case.get('differences', {})]
        if len(entity_cases) > len(llm_better_cases) * 0.3:
            recommendations.append("LLM shows significant advantage in entity extraction")
        
        # Low confidence patterns
        low_conf_cases = [case for case in llm_better_cases if case['regex_result']['confidence'] < 0.5]
        if len(low_conf_cases) > len(llm_better_cases) * 0.5:
            recommendations.append("Consider using LLM for queries with low regex confidence (<0.5)")
        
        # Complex queries
        complex_queries = [case for case in llm_better_cases if len(case['query'].split()) > 8]
        if len(complex_queries) > len(llm_better_cases) * 0.3:
            recommendations.append("LLM handles complex queries better - consider length-based routing")
        
        return recommendations
    
    def generate_report(self, days_back: int = 7) -> Dict[str, Any]:
        """Generate comprehensive analysis report"""
        comparisons = self.load_comparisons(days_back)
        analysis = self.analyze_llm_advantages(comparisons)
        
        # Add timing information
        analysis['report_info'] = {
            "generated_at": datetime.now().isoformat(),
            "days_analyzed": days_back,
            "comparisons_loaded": len(comparisons)
        }
        
        return analysis
    
    def export_report(self, days_back: int = 7, output_file: str = "parsing_analysis_report.json"):
        """Export analysis report to JSON file"""
        report = self.generate_report(days_back)
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Analysis report exported to {output_file}")
        return output_file

class ParserComparisonLogger:
    """Simple logger for backwards compatibility"""
    
    def __init__(self, log_dir: str = "logs/parser_comparison"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_file = self.log_dir / f"comparison_{datetime.now():%Y%m%d}.jsonl"
    
    async def log(self, query: str, regex_result, llm_result):
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
        
        with open(self.current_file, 'a') as f:
            f.write(json.dumps(comparison) + '\n')

if __name__ == "__main__":
    # Example usage
    analyzer = ParseComparisonAnalyzer()
    report = analyzer.generate_report(days_back=7)
    
    print("Parsing Analysis Summary:")
    print(f"Total comparisons: {report.get('summary', {}).get('total_comparisons', 0)}")
    print(f"LLM advantage rate: {report.get('summary', {}).get('llm_advantage_rate', 0):.2f}%")
    
    if 'recommendations' in report:
        print("\nRecommendations:")
        for rec in report['recommendations']:
            print(f"- {rec}")