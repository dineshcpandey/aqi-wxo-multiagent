#!/usr/bin/env python3
"""
Test script to verify the fine-tuned model integration.
"""

import asyncio
import json
from src.agents.instructlab_parser import FineTunedParser, FineTunedModelConfig

async def test_finetuned_model():
    """Test the fine-tuned model parser"""
    
    print("🧪 Testing Fine-tuned Model Integration")
    print("=" * 45)
    
    # Initialize parser
    config = FineTunedModelConfig(
        endpoint="http://localhost:8000/inference",
        temperature=0.1,
        max_tokens=150
    )
    
    parser = FineTunedParser(config)
    
    # Test queries that match your training format
    test_queries = [
        "What is PM2.5 in Delhi?",
        "Show air quality in Lucknow",
        "Compare Delhi vs Mumbai pollution",
        "PM2.5 trend for last 24 hours in Kanpur",
        "Is it safe to exercise in Ghaziabad?",
        "Pollution hotspots in NCR"
    ]
    
    print("🔍 Testing Query Parsing:")
    print("-" * 25)
    
    for i, query in enumerate(test_queries, 1):
        print(f"{i}. Query: \"{query}\"")
        
        try:
            # Test the prompt format
            prompt = parser.prompt_template.format(query=query)
            print(f"   Prompt: {prompt}")
            
            # Test parsing
            result = await parser.parse(query)
            
            print(f"   Intent: {result.intent}")
            print(f"   Entities: {result.entities}")
            print(f"   Confidence: {result.confidence}")
            
            if result.intent != 'unknown':
                print("   ✅ Success")
            else:
                print(f"   ❌ Failed: {result.entities.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"   💥 Exception: {e}")
        
        print()
    
    print("📊 Expected Training Data Format:")
    print("=" * 35)
    
    expected_formats = [
        {
            "text": "### Question: What is PM2.5 in Delhi?\n\n### Answer: {\"intent\": \"current_reading\", \"entities\": {\"location\": \"Delhi\", \"metric\": \"pm25\"}, \"confidence\": 0.95}"
        },
        {
            "text": "### Question: Compare Delhi vs Mumbai pollution\n\n### Answer: {\"intent\": \"comparison\", \"entities\": {\"locations\": [\"Delhi\", \"Mumbai\"], \"metric\": \"pm25\"}, \"confidence\": 0.9}"
        }
    ]
    
    for i, example in enumerate(expected_formats, 1):
        print(f"{i}. {example['text']}")
        print()
    
    print("💡 API Endpoint Test:")
    print("=" * 20)
    
    test_query = "What is PM2.5 in Delhi?"
    import urllib.parse
    encoded_query = urllib.parse.quote(f'"{test_query}"')
    test_url = f"http://localhost:8000/inference?query={encoded_query}"
    
    print("Test URL for your endpoint:")
    print(test_url)
    print()
    print("Expected response format:")
    print('{"intent": "current_reading", "entities": {"location": "Delhi", "metric": "pm25"}, "confidence": 0.95}')
    
    print()
    print("🔧 Configuration Summary:")
    print(f"  Endpoint: {config.endpoint}")
    print(f"  Model: {config.model_name}")
    print(f"  Temperature: {config.temperature}")
    print(f"  Max Tokens: {config.max_tokens}")
    print()
    print("📋 Response Format Detected:")
    print('  {"message": "{\\"intent\\": \\"current_reading\\", ...}"}')

async def test_endpoint_connectivity():
    """Test if the endpoint is accessible"""
    import aiohttp
    import urllib.parse
    
    print("\n🌐 Testing Endpoint Connectivity:")
    print("-" * 35)
    
    # Test with the actual inference endpoint format
    test_query = "what is NO2 in hazratganj"
    encoded_query = urllib.parse.quote(f'"{test_query}"')
    endpoint = f"http://localhost:8000/inference?query={encoded_query}"
    
    print(f"Testing URL: {endpoint}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Endpoint accessible")
                    print(f"   Status: {response.status}")
                    print(f"   Response type: {type(result)}")
                    if isinstance(result, dict):
                        print(f"   Response keys: {list(result.keys())}")
                    print(f"   Sample response: {str(result)[:200]}...")
                else:
                    print(f"❌ Endpoint returned status: {response.status}")
                    text = await response.text()
                    print(f"   Error response: {text[:100]}...")
                    
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("   Make sure your fine-tuned model is running on localhost:8000")

def main():
    """Main function"""
    
    print("🎯 Fine-tuned Model Migration Test")
    print("=" * 40)
    print("This script tests the migration from InstructLab to fine-tuned model")
    print()
    
    try:
        # Test endpoint first
        asyncio.run(test_endpoint_connectivity())
        
        # Test parser
        asyncio.run(test_finetuned_model())
        
        print("\n✅ Migration testing completed!")
        print("\n📝 Next Steps:")
        print("1. Ensure your model returns JSON in the expected format")
        print("2. Adjust the response parsing in _call_finetuned_model() if needed")
        print("3. Test with the hybrid parser using: python test_up_parsing.py")
        
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    main()