#!/usr/bin/env python3
"""
Summary analysis of hybrid parser performance with UP locations.
This script provides insights on where LLM parsing excels over regex.
"""

import re
import json

def extract_comparisons_from_log():
    """Extract all comparison data from log file"""
    comparisons = []
    
    try:
        with open('parsing_comparisons.log', 'r') as f:
            content = f.read()
            
        # Find all JSON objects in the log
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, content, re.DOTALL)
        
        for match in matches:
            try:
                # Clean up the match and parse JSON
                clean_match = match.strip()
                if '"timestamp"' in clean_match and '"query"' in clean_match:
                    comp = json.loads(clean_match)
                    comparisons.append(comp)
            except json.JSONDecodeError:
                continue
                
    except FileNotFoundError:
        print("Log file not found")
        return []
    
    return comparisons

def analyze_up_parsing_performance():
    """Analyze parsing performance for UP locations"""
    
    comparisons = extract_comparisons_from_log()
    
    if not comparisons:
        print("No comparison data found")
        return
    
    print("🏛️ Uttar Pradesh Air Quality - Parsing Analysis")
    print("=" * 50)
    print(f"Total comparisons: {len(comparisons)}")
    print()
    
    # Basic statistics
    llm_better = [c for c in comparisons if c.get('llm_better', False)]
    intent_differences = [c for c in comparisons if c.get('differences', {}).get('intent')]
    entity_differences = [c for c in comparisons if c.get('differences', {}).get('entities')]
    
    print("📊 Overall Performance:")
    print(f"  LLM better cases: {len(llm_better)}/{len(comparisons)} ({len(llm_better)/len(comparisons)*100:.1f}%)")
    print(f"  Intent differences: {len(intent_differences)} ({len(intent_differences)/len(comparisons)*100:.1f}%)")
    print(f"  Entity differences: {len(entity_differences)} ({len(entity_differences)/len(comparisons)*100:.1f}%)")
    print()
    
    # UP-specific analysis
    up_keywords = ['lucknow', 'kanpur', 'agra', 'varanasi', 'hazratganj', 'gomti', 'aminabad', 
                   'noida', 'meerut', 'ghaziabad', 'taj mahal', 'bara imambara', 'charbagh',
                   'allahabad', 'prayagraj', 'up capital']
    
    up_comparisons = []
    for comp in comparisons:
        query_lower = comp['query'].lower()
        if any(keyword in query_lower for keyword in up_keywords):
            up_comparisons.append(comp)
    
    print(f"📍 UP-Specific Analysis ({len(up_comparisons)} queries):")
    
    up_llm_better = [c for c in up_comparisons if c.get('llm_better', False)]
    print(f"  LLM better in UP queries: {len(up_llm_better)}/{len(up_comparisons)} ({len(up_llm_better)/len(up_comparisons)*100:.1f}%)")
    
    # Intent analysis
    print("\n🎯 Intent Detection Analysis:")
    intent_improvements = {}
    for comp in intent_differences:
        regex_intent = comp['regex_result']['intent']
        llm_intent = comp['llm_result']['intent']
        pattern = f"{regex_intent} → {llm_intent}"
        intent_improvements[pattern] = intent_improvements.get(pattern, 0) + 1
    
    for pattern, count in sorted(intent_improvements.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {pattern}: {count} times")
    
    # Query pattern analysis
    print(f"\n🔍 Where LLM Excelled (Top 10 cases):")
    for i, comp in enumerate(llm_better[:10], 1):
        query = comp['query']
        regex_intent = comp['regex_result']['intent']
        llm_intent = comp['llm_result']['intent']
        regex_conf = comp['regex_result']['confidence']
        llm_conf = comp['llm_result']['confidence']
        
        print(f"  {i:2d}. \"{query}\"")
        print(f"      Regex: {regex_intent} (conf: {regex_conf:.2f})")
        print(f"      LLM:   {llm_intent} (conf: {llm_conf:.2f})")
    
    # Specific UP advantages
    print(f"\n🏛️ UP-Specific LLM Advantages:")
    
    landmark_queries = []
    complex_location_queries = []
    historical_name_queries = []
    conversational_queries = []
    
    for comp in up_llm_better:
        query = comp['query'].lower()
        
        if any(landmark in query for landmark in ['taj mahal', 'bara imambara', 'charbagh', 'ghats']):
            landmark_queries.append(comp)
        
        if len(query.split()) > 6:
            complex_location_queries.append(comp)
            
        if 'allahabad' in query:  # Historical name
            historical_name_queries.append(comp)
            
        if any(word in query for word in ['safe', 'should', 'is it', 'how bad']):
            conversational_queries.append(comp)
    
    print(f"  Landmark-based queries: {len(landmark_queries)} better")
    print(f"  Complex location queries: {len(complex_location_queries)} better") 
    print(f"  Historical names (Allahabad): {len(historical_name_queries)} better")
    print(f"  Conversational queries: {len(conversational_queries)} better")
    
    # Recommendations
    print(f"\n💡 Key Findings & Recommendations:")
    
    llm_advantage_rate = (len(llm_better) / len(comparisons)) * 100
    
    if llm_advantage_rate > 30:
        print("  🟢 HIGH LLM Advantage - Consider hybrid approach with LLM fallback")
    elif llm_advantage_rate > 15:
        print("  🟡 MEDIUM LLM Advantage - Use LLM for complex queries")
    else:
        print("  🔴 LOW LLM Advantage - Regex performing adequately")
    
    if len(landmark_queries) > 0:
        print("  • LLM excels at landmark-based location queries")
    
    if len(conversational_queries) > 0:
        print("  • LLM better handles conversational/safety questions")
        
    if len(intent_differences) > len(comparisons) * 0.3:
        print("  • Consider improving regex patterns for intent detection")
    
    # Specific UP location insights
    print(f"\n🗺️ UP Location Insights:")
    
    successful_locations = set()
    for comp in up_comparisons:
        if comp['llm_result']['intent'] != 'unknown':
            entities = comp['llm_result']['entities']
            if 'location' in entities:
                successful_locations.add(entities['location'])
    
    print(f"  Locations successfully parsed by LLM: {len(successful_locations)}")
    print("  Examples:", ", ".join(list(successful_locations)[:8]))

if __name__ == "__main__":
    analyze_up_parsing_performance()