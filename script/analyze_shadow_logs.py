# scripts/analyze_shadow_logs.py
import json
from pathlib import Path
import pandas as pd

def analyze_shadow_performance():
    """Analyze shadow mode logs to determine when to switch"""
    
    logs_dir = Path("logs/parser_comparison")
    all_comparisons = []
    
    for log_file in logs_dir.glob("*.jsonl"):
        with open(log_file) as f:
            for line in f:
                all_comparisons.append(json.loads(line))
    
    df = pd.DataFrame(all_comparisons)
    
    # Analysis metrics
    print(f"Total queries analyzed: {len(df)}")
    print(f"Intent agreement rate: {df['agreement'].mean():.2%}")
    print(f"Entity match rate: {df['entity_match'].mean():.2%}")
    
    # Where LLM performs better
    llm_better = df[df['llm.confidence'] > df['regex.confidence']]
    print(f"\nQueries where LLM has higher confidence: {len(llm_better)}")
    
    # Regex failures that LLM handles
    regex_failures = df[df['regex.intent'] == 'unknown']
    llm_success_on_failures = regex_failures[regex_failures['llm.intent'] != 'unknown']
    print(f"Regex failures recovered by LLM: {len(llm_success_on_failures)}/{len(regex_failures)}")