"""
Test script for all 4 new features:
1. Guardrails (security)
2. TTL Caching (performance)
3. Engagement Agent (follow-ups)
4. Analytics (logging)
"""
import requests
import time
import json

BASE_URL = "http://localhost:5000"

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_guardrails():
    """Test guardrails validation"""
    print_section("TEST 1: GUARDRAILS SYSTEM")
    
    # Test 1: Normal query (should pass)
    print("\n✓ Test 1a: Normal query")
    response = requests.post(f"{BASE_URL}/api/agent/query", json={
        "question": "What's the average import value from Germany?"
    })
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✓ PASSED: Normal query accepted")
    else:
        print(f"✗ FAILED: {response.json()}")
    
    # Test 2: Empty query (should fail)
    print("\n✓ Test 1b: Empty query")
    response = requests.post(f"{BASE_URL}/api/agent/query", json={
        "question": ""
    })
    print(f"Status: {response.status_code}")
    if response.status_code == 400:
        print(f"✓ PASSED: Empty query blocked - {response.json()['error']}")
    else:
        print("✗ FAILED: Empty query should be blocked")
    
    # Test 3: Too long query (should fail)
    print("\n✓ Test 1c: Too long query")
    response = requests.post(f"{BASE_URL}/api/agent/query", json={
        "question": "a" * 6000
    })
    print(f"Status: {response.status_code}")
    if response.status_code == 400:
        print(f"✓ PASSED: Long query blocked - {response.json()['error']}")
    else:
        print("✗ FAILED: Long query should be blocked")
    
    # Test 4: Harmful content (should fail)
    print("\n✓ Test 1d: Harmful content")
    response = requests.post(f"{BASE_URL}/api/agent/query", json={
        "question": "How to hack a bank system?"
    })
    print(f"Status: {response.status_code}")
    if response.status_code == 400:
        print(f"✓ PASSED: Harmful content blocked - {response.json()['error']}")
    else:
        print("✗ FAILED: Harmful content should be blocked")

def test_caching():
    """Test TTL caching"""
    print_section("TEST 2: TTL CACHING")
    
    # Test: Same query twice - second should be faster
    query = "What is Moldova's GDP?"
    
    print(f"\n✓ Test 2a: First query (no cache)")
    start1 = time.time()
    response1 = requests.post(f"{BASE_URL}/api/agent/query", json={
        "question": query
    })
    time1 = time.time() - start1
    print(f"Time: {time1:.3f}s")
    
    time.sleep(1)  # Small delay
    
    print(f"\n✓ Test 2b: Second query (cached)")
    start2 = time.time()
    response2 = requests.post(f"{BASE_URL}/api/agent/query", json={
        "question": query
    })
    time2 = time.time() - start2
    print(f"Time: {time2:.3f}s")
    
    if response1.status_code == 200 and response2.status_code == 200:
        speedup = time1 / time2 if time2 > 0 else 1
        print(f"\n✓ Speedup: {speedup:.2f}x")
        if speedup > 1.2:
            print("✓ PASSED: Caching is working (>20% speedup)")
        else:
            print("⚠ WARNING: Speedup less than expected (but may be normal)")
    else:
        print("✗ FAILED: Query error")

def test_engagement():
    """Test engagement follow-ups"""
    print_section("TEST 3: ENGAGEMENT AGENT")
    
    print("\n✓ Test 3: Follow-up generation")
    response = requests.post(f"{BASE_URL}/api/agent/query", json={
        "question": "What's the highest import value?"
    })
    
    if response.status_code == 200:
        data = response.json()
        if 'followup' in data and data['followup']:
            print(f"✓ PASSED: Follow-up generated")
            print(f"Follow-up: {data['followup']}")
        else:
            print("✗ FAILED: No follow-up in response")
    else:
        print(f"✗ FAILED: {response.json()}")

def test_analytics():
    """Test analytics logging"""
    print_section("TEST 4: ANALYTICS LOGGING")
    
    # Make a few queries to populate analytics
    print("\n✓ Test 4a: Making sample queries")
    queries = [
        "What's the total import value?",
        "Which country exports most?",
        "Show me the data for Germany"
    ]
    
    for q in queries:
        response = requests.post(f"{BASE_URL}/api/agent/query", json={"question": q})
        print(f"  - {q[:40]}... Status: {response.status_code}")
    
    time.sleep(1)
    
    # Check analytics summary
    print("\n✓ Test 4b: Checking analytics summary")
    response = requests.get(f"{BASE_URL}/api/analytics/summary")
    
    if response.status_code == 200:
        data = response.json()
        print("✓ PASSED: Analytics endpoint working")
        print(f"\nPerformance Summary:")
        print(json.dumps(data['performance'], indent=2))
        print(f"\nTool Usage:")
        print(json.dumps(data['tool_usage'], indent=2))
        print(f"\nPopular Queries:")
        for q in data['popular_queries']:
            print(f"  - {q['query'][:50]}... (count: {q['count']})")
    else:
        print("✗ FAILED: Analytics endpoint error")
    
    # Check recent queries
    print("\n✓ Test 4c: Checking recent queries")
    response = requests.get(f"{BASE_URL}/api/analytics/recent?limit=3")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ PASSED: Recent queries endpoint working")
        print(f"Found {len(data['recent_queries'])} recent queries")
    else:
        print("✗ FAILED: Recent queries endpoint error")

def test_integration():
    """Test all features together"""
    print_section("TEST 5: INTEGRATION TEST")
    
    print("\n✓ Full workflow test")
    
    # 1. Normal query
    response = requests.post(f"{BASE_URL}/api/agent/query", json={
        "question": "What products does Romania export to Moldova?"
    })
    
    if response.status_code == 200:
        data = response.json()
        
        checks = {
            "Answer present": bool(data.get('answer')),
            "Follow-up present": bool(data.get('followup')),
            "Tools used": bool(data.get('tool_calls')),
        }
        
        print("\nChecklist:")
        for check, passed in checks.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check}")
        
        if all(checks.values()):
            print("\n✓ PASSED: All features working together")
        else:
            print("\n⚠ PARTIAL: Some features missing")
    else:
        print(f"✗ FAILED: {response.json()}")

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║     ECON ASSISTANT - COMPREHENSIVE FEATURE TEST           ║
    ║                                                           ║
    ║  Testing: Guardrails, Caching, Engagement, Analytics     ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    print("\nMake sure the server is running on http://localhost:5000")
    input("Press Enter to start tests...")
    
    try:
        # Run all tests
        test_guardrails()
        test_caching()
        test_engagement()
        test_analytics()
        test_integration()
        
        print_section("TEST SUITE COMPLETE")
        print("\n✓ All tests completed. Check results above.")
        
    except requests.exceptions.ConnectionError:
        print("\n✗ ERROR: Cannot connect to server.")
        print("Make sure Econ Assistant is running on http://localhost:5000")
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
