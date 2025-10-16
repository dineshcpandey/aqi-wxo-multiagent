#!/usr/bin/env python3
"""
Test script for hybrid parser with Uttar Pradesh specific locations.
This script tests parsing capabilities with regional place names from UP.
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.graphs.pm_query_workflow import PMQueryWorkflow
from src.training.comparison_logger import ParseComparisonAnalyzer

class MockLocationAgent:
    """Mock location agent with UP-specific locations"""
    
    def __init__(self):
        # UP locations database
        self.up_locations = {
            "lucknow": [{"code": "UP01", "name": "Lucknow", "level": "city", "state_code": "UP"}],
            "hazratganj": [{"code": "UP02", "name": "Hazratganj", "level": "locality", "state_code": "UP"}],
            "gomti nagar": [{"code": "UP03", "name": "Gomti Nagar", "level": "locality", "state_code": "UP"}],
            "aminabad": [{"code": "UP04", "name": "Aminabad", "level": "locality", "state_code": "UP"}],
            "alambagh": [{"code": "UP05", "name": "Alambagh", "level": "locality", "state_code": "UP"}],
            "kanpur": [{"code": "UP06", "name": "Kanpur", "level": "city", "state_code": "UP"}],
            "agra": [{"code": "UP07", "name": "Agra", "level": "city", "state_code": "UP"}],
            "varanasi": [{"code": "UP08", "name": "Varanasi", "level": "city", "state_code": "UP"}],
            "allahabad": [{"code": "UP09", "name": "Prayagraj", "level": "city", "state_code": "UP"}],
            "prayagraj": [{"code": "UP09", "name": "Prayagraj", "level": "city", "state_code": "UP"}],
            "meerut": [{"code": "UP10", "name": "Meerut", "level": "city", "state_code": "UP"}],
            "ghaziabad": [{"code": "UP11", "name": "Ghaziabad", "level": "city", "state_code": "UP"}],
            "noida": [{"code": "UP12", "name": "Noida", "level": "city", "state_code": "UP"}],
            "greater noida": [{"code": "UP13", "name": "Greater Noida", "level": "city", "state_code": "UP"}],
            "taj mahal": [{"code": "UP14", "name": "Taj Mahal Area", "level": "locality", "state_code": "UP"}],
            "bara imambara": [{"code": "UP15", "name": "Bara Imambara Area", "level": "locality", "state_code": "UP"}],
            "charbagh": [{"code": "UP16", "name": "Charbagh", "level": "locality", "state_code": "UP"}],
            "lalbagh": [{"code": "UP17", "name": "Lalbagh", "level": "locality", "state_code": "UP"}],
            "kaiserbagh": [{"code": "UP18", "name": "Kaiserbagh", "level": "locality", "state_code": "UP"}],
        }
    
    async def run(self, params):
        location_query = params.get("location_query", "").lower().strip()
        
        # Direct match
        if location_query in self.up_locations:
            return {
                "success": True,
                "locations": self.up_locations[location_query],
                "needs_disambiguation": False
            }
        
        # Partial match for similar names
        matches = []
        for key, location in self.up_locations.items():
            if location_query in key or key in location_query:
                matches.extend(location)
        
        if matches:
            return {
                "success": True,
                "locations": matches,
                "needs_disambiguation": len(matches) > 1
            }
        
        return {
            "success": False,
            "error": f"Location '{location_query}' not found",
            "locations": []
        }

class MockPMAgent:
    """Mock PM data agent with UP-specific pollution data"""
    
    def __init__(self):
        # Mock PM2.5 values for UP locations (realistic ranges)
        self.up_pm_values = {
            "Lucknow": 145.3,
            "Hazratganj": 156.7,
            "Gomti Nagar": 134.2,
            "Aminabad": 167.8,
            "Alambagh": 142.5,
            "Kanpur": 189.4,  # Higher industrial pollution
            "Agra": 158.9,
            "Varanasi": 162.1,
            "Prayagraj": 139.6,
            "Meerut": 174.3,
            "Ghaziabad": 198.7,  # NCR pollution
            "Noida": 187.2,
            "Greater Noida": 165.4,
            "Taj Mahal Area": 152.1,
            "Bara Imambara Area": 148.9,
            "Charbagh": 159.3,
            "Lalbagh": 143.7,
            "Kaiserbagh": 151.2,
        }
    
    async def run(self, params):
        location = params.get("location", {})
        location_name = location.get("name", "Unknown")
        
        pm_value = self.up_pm_values.get(location_name, 150.0)
        
        return {
            "success": True,
            "pm25_value": pm_value,
            "timestamp": "2025-10-13T19:30:00Z",
            "station_count": 2,
            "source": "up_mock"
        }

async def test_up_queries():
    """Test various UP-specific queries"""
    
    # Initialize agents
    location_agent = MockLocationAgent()
    pm_agent = MockPMAgent()
    
    # Initialize workflow with hybrid parser
    workflow = PMQueryWorkflow(
        location_agent=location_agent,
        pm_agent=pm_agent,
        use_hybrid_parser=True,
        shadow_mode=True
    )
    
    # UP-specific test queries
    up_test_queries = [
        # Simple city queries
        "What is PM2.5 in Lucknow?",
        "Show air quality in Kanpur",
        "Current pollution level Agra",
        
        # Locality queries  
        "PM2.5 reading at Hazratganj",
        "Air quality in Gomti Nagar",
        "Show me pollution in Aminabad market",
        
        # Landmark-based queries
        "What's the air quality near Taj Mahal?",
        "PM2.5 level at Bara Imambara",
        "Pollution near Charbagh station",
        
        # Complex/conversational queries
        "Is it safe to visit Varanasi ghats today?",
        "Should I wear mask in Meerut?",
        "How bad is air quality in Ghaziabad right now?",
        
        # Comparison queries
        "Compare air quality between Lucknow and Kanpur",
        "Noida vs Greater Noida pollution level",
        
        # Trend queries
        "Lucknow PM2.5 trend last 24 hours",
        "Show Agra air quality history",
        
        # Ambiguous/challenging queries
        "Allahabad air quality",  # Old name for Prayagraj
        "Air pollution in UP capital",  # Indirect reference
        "PM near railway station Lucknow",  # Generic + specific
    ]
    
    print("🏛️ Uttar Pradesh Air Quality - Hybrid Parser Test")
    print("=" * 55)
    print("Testing parsing capabilities with UP-specific locations")
    print(f"Total test queries: {len(up_test_queries)}")
    print()
    
    results = []
    parsing_stats = {
        "regex_better": 0,
        "llm_better": 0,
        "tie": 0,
        "intent_differences": 0,
        "entity_differences": 0
    }
    
    for i, query in enumerate(up_test_queries, 1):
        print(f"📝 Test {i:2d}: '{query}'")
        print("-" * 45)
        
        try:
            result = await workflow.process_query(query)
            
            success = not result.get('error')
            location_found = bool(result.get('selected_location'))
            
            if success:
                loc_name = result.get('selected_location', {}).get('name', 'Unknown')
                print(f"✅ Success: Location '{loc_name}' found")
                print(f"   Response: {result.get('response', '')[:80]}...")
            else:
                print(f"❌ Failed: {result.get('error', 'Unknown error')}")
            
            results.append({
                "query": query,
                "success": success,
                "location_found": location_found,
                "location_name": result.get('selected_location', {}).get('name') if location_found else None
            })
            
        except Exception as e:
            print(f"💥 Exception: {str(e)}")
            results.append({
                "query": query,
                "success": False,
                "error": str(e)
            })
        
        print()
    
    # Analysis
    print("📊 Test Results Analysis")
    print("=" * 30)
    
    successful = sum(1 for r in results if r['success'])
    locations_found = sum(1 for r in results if r.get('location_found'))
    
    print(f"Successful queries: {successful}/{len(up_test_queries)} ({successful/len(up_test_queries)*100:.1f}%)")
    print(f"Locations resolved: {locations_found}/{len(up_test_queries)} ({locations_found/len(up_test_queries)*100:.1f}%)")
    
    # Show parsing statistics
    stats = workflow.get_parsing_stats()
    if 'error' not in stats:
        print(f"\n🔍 Parsing Comparison Stats:")
        print(f"Total comparisons: {stats.get('total_comparisons', 0)}")
        print(f"LLM better rate: {stats.get('llm_better_percentage', 0):.1f}%")
        print(f"Intent differences: {stats.get('intent_differences', 0)}")
        print(f"Entity differences: {stats.get('entity_differences', 0)}")
    
    # Show locations successfully identified
    print(f"\n🗺️ UP Locations Successfully Identified:")
    unique_locations = set()
    for result in results:
        if result.get('location_name'):
            unique_locations.add(result['location_name'])
    
    for location in sorted(unique_locations):
        print(f"  • {location}")
    
    return results

async def analyze_up_parsing():
    """Analyze parsing performance for UP queries"""
    print(f"\n🔬 UP Parsing Analysis")
    print("=" * 25)
    
    try:
        analyzer = ParseComparisonAnalyzer()
        
        # Get recent comparisons
        comparisons = analyzer.load_comparisons(days_back=1)
        
        if not comparisons:
            print("No comparison data available")
            return
            
        # Filter for UP-related queries
        up_comparisons = []
        up_keywords = ['lucknow', 'kanpur', 'agra', 'varanasi', 'hazratganj', 'gomti', 'noida', 'meerut', 'taj mahal', 'allahabad', 'prayagraj']
        
        for comp in comparisons:
            query_lower = comp['query'].lower()
            if any(keyword in query_lower for keyword in up_keywords):
                up_comparisons.append(comp)
        
        print(f"Total UP-related comparisons: {len(up_comparisons)}")
        
        if not up_comparisons:
            print("No UP-specific comparisons found")
            return
        
        # Analyze UP-specific patterns
        llm_better_count = sum(1 for comp in up_comparisons if comp.get('llm_better', False))
        intent_differences = sum(1 for comp in up_comparisons 
                               if comp['regex_result']['intent'] != comp['llm_result']['intent'])
        
        print(f"LLM better in UP queries: {llm_better_count}/{len(up_comparisons)} ({llm_better_count/len(up_comparisons)*100:.1f}%)")
        print(f"Intent differences: {intent_differences}/{len(up_comparisons)} ({intent_differences/len(up_comparisons)*100:.1f}%)")
        
        # Show examples where LLM was better
        llm_better_examples = [comp for comp in up_comparisons if comp.get('llm_better', False)]
        if llm_better_examples:
            print(f"\n💡 Examples where LLM outperformed regex:")
            for i, comp in enumerate(llm_better_examples[:3], 1):
                print(f"  {i}. Query: '{comp['query']}'")
                print(f"     Regex: {comp['regex_result']['intent']} (conf: {comp['regex_result']['confidence']:.2f})")
                print(f"     LLM:   {comp['llm_result']['intent']} (conf: {comp['llm_result']['confidence']:.2f})")
                
    except Exception as e:
        print(f"Analysis error: {e}")

def main():
    """Main function"""
    
    print("🎯 UP Air Quality Agent - Hybrid Parser Test")
    print("=" * 45)
    print("Testing InstructLab hybrid parsing with Uttar Pradesh locations")
    print("This will help identify where LLM parsing excels over regex")
    print()
    
    try:
        # Run tests
        results = asyncio.run(test_up_queries())
        
        # Analyze results
        asyncio.run(analyze_up_parsing())
        
        print(f"\n✅ UP testing completed!")
        print("Check 'parsing_comparisons.log' for detailed comparison data")
        
    except KeyboardInterrupt:
        print(f"\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    main()