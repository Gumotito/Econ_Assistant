"""
Quick test to verify all imports work correctly
"""
print("Testing imports...")

try:
    print("1. Testing guardrails...")
    from app.services.guardrails import get_guardrails
    guardrails = get_guardrails()
    print("   ✓ Guardrails imported")
    
    print("2. Testing analytics...")
    from app.services.analytics import get_analytics
    analytics = get_analytics()
    print("   ✓ Analytics imported")
    
    print("3. Testing engagement...")
    from app.tools.engagement import suggest_followup
    print("   ✓ Engagement imported")
    
    print("4. Testing web tools...")
    from app.tools.web import web_search
    print("   ✓ Web tools imported")
    
    print("\n✓ All imports successful!")
    print("\nQuick validation tests:")
    
    # Test guardrails
    is_valid, error = guardrails.validate_input("Test question")
    print(f"   Guardrails validation: {is_valid} (error: {error})")
    
    # Test analytics
    summary = analytics.get_performance_summary()
    print(f"   Analytics summary: {summary}")
    
    print("\n✓ All systems operational!")
    
except Exception as e:
    print(f"\n✗ Import error: {e}")
    import traceback
    traceback.print_exc()
