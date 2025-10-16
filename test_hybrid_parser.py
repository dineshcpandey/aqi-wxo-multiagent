#!/usr/bin/env python3
"""
Test script for hybrid parser integration with PMQueryWorkflow.
This script demonstrates the enhanced parsing capabilities and logging.
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.graphs.pm_query_workflow import PMQueryWorkflow
from src.agents.location_resolver import LocationResolverAgent
from src.agents.pm_data_agent import PMDataAgent
from src.training.comparison_logger import ParseComparisonAnalyzer

class MockLocationAgent:
    """Mock location agent for testing"""
    
    async def run(self, params):
        location_query = params.get("location_query", "")
        
        # Mock responses for common locations
        mock_locations = {
            "delhi": [{"code": "DL01", "name": "Delhi", "level": "city", "state_code": "DL"}],
            "mumbai": [{"code": "MH01", "name": "Mumbai", "level": "city", "state_code": "MH"}],
            "bangalore": [{"code": "KA01", "name": "Bangalore", "level": "city", "state_code": "KA"}],
            "hazratganj": [{"code": "UP01", "name": "Hazratganj", "level": "locality", "state_code": "UP"}]
        }
        
        location_key = location_query.lower().strip()
        if location_key in mock_locations:
            return {
                "success": True,
                "locations": mock_locations[location_key],
                "needs_disambiguation": False
            }
        else:
            return {
                "success": False,
                "error": f"Location '{location_query}' not found",
                "locations": []
            }

class MockPMAgent:
    """Mock PM data agent for testing"""
    
    async def run(self, params):
        location = params.get("location", {})
        location_name = location.get("name", "Unknown")
        
        # Mock PM2.5 values
        mock_values = {
            "Delhi": 156.7,
            "Mumbai": 87.3,
            "Bangalore": 45.2,
            "Hazratganj": 98.5
        }
        
        pm_value = mock_values.get(location_name, 75.0)
        
        return {
            "success": True,
            "pm25_value": pm_value,
            "timestamp": "2025-01-13T14:30:00Z",
            "station_count": 3,
            "source": "mock"
        }

async def test_queries():
    """Test various queries with the hybrid parser"""
    
    # Initialize agents
    location_agent = MockLocationAgent()
    pm_agent = MockPMAgent()
    
    # Initialize workflow with hybrid parser enabled
    workflow = PMQueryWorkflow(
        location_agent=location_agent,
        pm_agent=pm_agent,
        use_hybrid_parser=True,
        shadow_mode=True
    )
    
    # Test queries
    test_queries = [
        "What is PM2.5 in Delhi?",
        "Show me air quality in Hazratganj",
        "Current pollution level Mumbai", 
        "Delhi PM readings now",
        "Compare air quality between Delhi and Mumbai",
        "PM2.5 trend for Delhi last 24 hours",
        "Is it safe to exercise in Bangalore today?",
        "What's the current AQI at India Gate?",
        "Show pollution hotspots in NCR region"
    ]
    
    print("🚀 Testing Hybrid Parser Integration")
    print("=" * 50)
    
    results = []
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Test {i}: '{query}'")
        print("-" * 40)
        
        try:
            result = await workflow.process_query(query)
            
            print(f"✅ Success: {result.get('response', 'No response')[:100]}...")
            
            if result.get('error'):
                print(f"⚠️  Error: {result['error']}")
            
            results.append({
                "query": query,
                "success": not result.get('error'),
                "location_found": bool(result.get('selected_location')),
                "response_length": len(result.get('response', ''))
            })
            
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
            results.append({
                "query": query,
                "success": False,
                "error": str(e)
            })
    
    # Show parsing statistics if available
    print(f"\n📊 Parsing Statistics")
    print("=" * 30)
    
    try:
        stats = workflow.get_parsing_stats()
        if 'error' not in stats:
            print(f"Total comparisons: {stats.get('total_comparisons', 0)}")
            print(f"LLM better rate: {stats.get('llm_better_percentage', 0):.1f}%")
            print(f"Avg regex confidence: {stats.get('avg_regex_confidence', 0):.3f}")
            print(f"Avg LLM confidence: {stats.get('avg_llm_confidence', 0):.3f}")
        else:
            print("No parsing statistics available yet")
    except Exception as e:
        print(f"Error getting stats: {e}")
    
    # Show recent comparisons
    print(f"\n🔍 Recent Parsing Comparisons")
    print("=" * 35)
    
    try:
        recent_comparisons = workflow.get_recent_comparisons(limit=3)
        for comp in recent_comparisons:
            print(f"Query: '{comp['query']}'")
            print(f"  Regex: {comp['regex_result']['intent']} (conf: {comp['regex_result']['confidence']:.3f})")
            print(f"  LLM: {comp['llm_result']['intent']} (conf: {comp['llm_result']['confidence']:.3f})")
            print(f"  LLM Better: {comp['llm_better']}")
            print()
    except Exception as e:
        print(f"Error getting comparisons: {e}")
    
    # Summary
    successful_queries = sum(1 for r in results if r['success'])
    print(f"📈 Summary: {successful_queries}/{len(test_queries)} queries processed successfully")
    
    return results

async def analyze_parsing_logs():
    """Analyze parsing comparison logs if available"""
    print(f"\n🔬 Parsing Log Analysis")
    print("=" * 25)
    
    try:
        analyzer = ParseComparisonAnalyzer()
        report = analyzer.generate_report(days_back=1)  # Last 24 hours
        
        if report.get('summary', {}).get('total_comparisons', 0) > 0:
            summary = report['summary']
            print(f"Total comparisons: {summary['total_comparisons']}")
            print(f"LLM advantage rate: {summary['llm_advantage_rate']:.1f}%")
            
            # Show recommendations
            recommendations = report.get('recommendations', [])
            if recommendations:
                print(f"\n💡 Recommendations:")
                for rec in recommendations:
                    print(f"  - {rec}")
        else:
            print("No parsing log data found. Run some queries first!")
            
    except Exception as e:
        print(f"Analysis error: {e}")

def main():
    """Main function to run tests"""
    
    print("🎯 Air Quality Agent - Hybrid Parser Test")
    print("========================================")
    print("This script tests the integration of HybridQueryParser")
    print("with PMQueryWorkflow and demonstrates parsing comparison logging.\n")
    
    # Check if InstructLab is running
    print("🔧 Configuration:")
    print("  - InstructLab endpoint: http://localhost:8000")
    print("  - Shadow mode: Enabled (LLM runs in background)")
    print("  - Comparison logging: Enabled")
    print("  - Log file: parsing_comparisons.log\n")
    
    # Run async tests
    try:
        results = asyncio.run(test_queries())
        asyncio.run(analyze_parsing_logs())
        
        print(f"\n✅ Test completed successfully!")
        print(f"Check 'parsing_comparisons.log' for detailed comparison data.")
        
    except KeyboardInterrupt:
        print(f"\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    main()