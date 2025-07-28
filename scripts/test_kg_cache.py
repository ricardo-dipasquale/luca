#!/usr/bin/env python3
"""
Test script for KG Tools Cache implementation.

This script tests all three cached functions to ensure they're working correctly:
- _get_fallback_theoretical_content
- search_knowledge_graph_tool  
- get_theoretical_content_tool
"""

import sys
import os
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.kg_tools import (
    _get_fallback_theoretical_content,
    search_knowledge_graph_tool,
    get_theoretical_content_tool,
    get_cache_stats,
    clear_kg_cache,
    kg_cache_stats_tool
)


def test_function_with_cache(func_name, func, input_data):
    """Test a function with cache timing."""
    print(f"\n🔍 Testing {func_name}...")
    print(f"Input: {input_data}")
    
    # First call - should miss cache
    print("First call (cache miss):")
    start_time = time.time()
    try:
        result1 = func.invoke(input_data)
        time1 = time.time() - start_time
        print(f"  ✅ Success - Time: {time1:.2f}s, Length: {len(result1)} chars")
    except Exception as e:
        time1 = time.time() - start_time
        print(f"  ❌ Error - Time: {time1:.2f}s, Error: {str(e)}")
        return False
    
    # Second call - should hit cache
    print("Second call (cache hit):")
    start_time = time.time()
    try:
        result2 = func.invoke(input_data)
        time2 = time.time() - start_time
        
        results_match = result1 == result2
        if time2 > 0:
            speed_improvement = time1 / time2
        else:
            speed_improvement = float('inf')
        
        print(f"  ✅ Success - Time: {time2:.3f}s, Length: {len(result2)} chars")
        print(f"  📊 Results match: {results_match}")
        print(f"  🚀 Speed improvement: {speed_improvement:.1f}x faster")
        
        return results_match and time2 < time1
        
    except Exception as e:
        time2 = time.time() - start_time
        print(f"  ❌ Error - Time: {time2:.2f}s, Error: {str(e)}")
        return False


def main():
    """Main test function."""
    print("🧪 KG Tools Cache Implementation Test")
    print("=" * 60)
    
    # Clear cache to start fresh
    clear_kg_cache()
    print("✅ Cache cleared")
    
    # Test results
    test_results = []
    
    # Test 1: _get_fallback_theoretical_content (raw function)
    print("\n🔍 Testing _get_fallback_theoretical_content...")
    print("Input: 'SQL JOINS'")
    
    # First call - should miss cache
    print("First call (cache miss):")
    start_time = time.time()
    try:
        result1 = _get_fallback_theoretical_content("SQL JOINS")
        time1 = time.time() - start_time
        print(f"  ✅ Success - Time: {time1:.2f}s, Length: {len(result1)} chars")
        
        # Second call - should hit cache
        print("Second call (cache hit):")
        start_time = time.time()
        result2 = _get_fallback_theoretical_content("SQL JOINS")
        time2 = time.time() - start_time
        
        results_match = result1 == result2
        speed_improvement = time1 / time2 if time2 > 0 else float('inf')
        
        print(f"  ✅ Success - Time: {time2:.3f}s, Length: {len(result2)} chars")
        print(f"  📊 Results match: {results_match}")
        print(f"  🚀 Speed improvement: {speed_improvement:.1f}x faster")
        
        result1 = results_match and time2 < time1
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        result1 = False
    
    test_results.append(("_get_fallback_theoretical_content", result1))
    
    # Test 2: search_knowledge_graph_tool
    result2 = test_function_with_cache(
        "search_knowledge_graph_tool", 
        search_knowledge_graph_tool,
        {"query_text": "SQL", "limit": 3}
    )
    test_results.append(("search_knowledge_graph_tool", result2))
    
    # Test 3: get_theoretical_content_tool
    result3 = test_function_with_cache(
        "get_theoretical_content_tool",
        get_theoretical_content_tool,
        {"topic_description": "Database normalization"}
    )
    test_results.append(("get_theoretical_content_tool", result3))
    
    # Show final cache statistics
    print(f"\n📊 Final Cache Statistics:")
    print("-" * 40)
    cache_stats = kg_cache_stats_tool.invoke({})
    print(cache_stats)
    
    # Summary
    print(f"\n📋 Test Summary:")
    print("-" * 40)
    passed = 0
    total = len(test_results)
    
    for func_name, passed_test in test_results:
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"  {func_name}: {status}")
        if passed_test:
            passed += 1
    
    print(f"\nOverall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All cache tests passed!")
        return 0
    else:
        print("⚠️  Some cache tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)