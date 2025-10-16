#!/usr/bin/env python3
"""
Demo script showing the complete hybrid parser integration with monitoring.
"""

import asyncio
from src.graphs.pm_query_workflow import PMQueryWorkflow

class DemoLocationAgent:
    """Demo location agent for final demonstration"""
    
    async def run(self, params):
        location_query = params.get("location_query", "").lower().strip()
        
        demo_locations = {
            "delhi": [{"code": "DL01", "name": "Delhi", "level": "city", "state_code": "DL"}],
            "lucknow": [{"code": "UP01", "name": "Lucknow", "level": "city", "state_code": "UP"}],
            "hazratganj": [{"code": "UP02", "name": "Hazratganj", "level": "locality", "state_code": "UP"}],
        }
        
        if location_query in demo_locations:
            return {"success": True, "locations": demo_locations[location_query], "needs_disambiguation": False}
        return {"success": False, "error": f"Location '{location_query}' not found", "locations": []}

class DemoPMAgent:
    """Demo PM agent"""
    
    async def run(self, params):
        location = params.get("location", {})
        pm_values = {"Delhi": 185.2, "Lucknow": 145.3, "Hazratganj": 156.7}
        pm_value = pm_values.get(location.get("name", ""), 120.0)
        
        return {
            "success": True, "pm25_value": pm_value, "timestamp": "2025-10-13T19:30:00Z", 
            "station_count": 2, "source": "demo"
        }

async def main():
    print("🎯 Hybrid Parser Integration - Final Demo")
    print("=" * 45)
    print("Demonstrating InstructLab + Regex parsing with comprehensive logging")
    print()
    
    # Initialize workflow
    workflow = PMQueryWorkflow(
        location_agent=DemoLocationAgent(),
        pm_agent=DemoPMAgent(),
        use_hybrid_parser=True,
        shadow_mode=True
    )
    
    demo_queries = [
        "What is PM2.5 in Delhi?",
        "PM level at Hazratganj", 
        "Compare Delhi vs Lucknow air quality"
    ]
    
    for query in demo_queries:
        print(f"🔍 Query: \"{query}\"")
        print("-" * 30)
        
        result = await workflow.process_query(query)
        
        if result.get('error'):
            print(f"❌ {result['error']}")
        else:
            print(f"✅ {result['response'][:80]}...")
        
        print()
    
    # Show statistics
    stats = workflow.get_parsing_stats()
    print("📊 Final Statistics:")
    print(f"  Total comparisons: {stats.get('total_comparisons', 0)}")
    print(f"  LLM advantage: {stats.get('llm_better_percentage', 0):.1f}%")
    
    print()
    print("✅ Integration Complete!")
    print("  • Hybrid parser active with shadow mode")
    print("  • Parsing comparisons logged to 'parsing_comparisons.log'")
    print("  • LLM performance tracking enabled")
    print("  • Ready for production deployment with monitoring")

if __name__ == "__main__":
    asyncio.run(main())