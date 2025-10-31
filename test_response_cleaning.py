"""
Test that forecast responses are user-friendly
"""
import re

# Simulated LLM responses - BEFORE fixes
bad_response = """From the dataset provided:
- The largest import volumes by tons in recent months are:
- **Petroleum Products**:
  - June: 1950 tons (Romania)
  - October: 1750 tons (Romania)

To forecast for the next two years:
```python
forecast_economic_indicator(indicator="Import_Volume_Tons", time_periods=24, method="ensemble")
```

For a more specific forecast on Food Products:
```python
forecast_trade_balance(export_indicator=None, import_indicator="Food_Products", periods_ahead=24)
```

I'll proceed with the forecast now."""

# GOOD response - what we want
good_response = """From the dataset provided:
- The largest import volumes by tons in recent months are:
- **Petroleum Products**:
  - June: 1950 tons (Romania)
  - October: 1750 tons (Romania)

📊 **Forecast Results for Import_Volume_Tons:**

Period 1: 2,150 tons
Period 6: 2,300 tons
Period 12: 2,450 tons
Period 18: 2,600 tons
Period 24: 2,750 tons

💡 Based on ensemble forecasting, Moldova's import volumes are projected to increase by 28% over the next 2 years, reaching approximately 2,750 tons by 2027. This growth is driven by steady historical trends showing an average 1.2% monthly increase."""

print("=" * 80)
print("RESPONSE CLEANING TEST")
print("=" * 80)

# Test cleaning function
def clean_response(content):
    """Clean up forecast responses"""
    # Remove code blocks that show tool calls
    content = re.sub(r'```python\s*forecast_[^`]+```', '', content)
    content = re.sub(r'```\s*forecast_[^`]+```', '', content)
    
    # Remove phrases like "I'll proceed with the forecast now"
    content = re.sub(r"I'?ll proceed with (?:the )?(?:forecast|analysis).*?(?:\.|$)", '', content, flags=re.IGNORECASE)
    content = re.sub(r"Let me (?:proceed|run|execute).*?(?:forecast|analysis).*?(?:\.|$)", '', content, flags=re.IGNORECASE)
    
    # Clean up extra whitespace
    content = re.sub(r'\n{3,}', '\n\n', content).strip()
    
    return content

print("\nBAD RESPONSE (Before):")
print("-" * 80)
print(bad_response)
print("\n")

print("CLEANED RESPONSE (After):")
print("-" * 80)
cleaned = clean_response(bad_response)
print(cleaned)
print("\n")

print("GOOD RESPONSE (Target):")
print("-" * 80)
print(good_response)
print("\n")

# Check what was removed
print("=" * 80)
print("CLEANING ANALYSIS:")
print("=" * 80)
print(f"Original length: {len(bad_response)} chars")
print(f"Cleaned length: {len(cleaned)} chars")
print(f"Removed: {len(bad_response) - len(cleaned)} chars")
print(f"\nCode blocks removed: {'YES' if '```python' not in cleaned else 'NO'}")
print(f"'I'll proceed' removed: {'YES' if 'proceed' not in cleaned.lower() else 'NO'}")
print(f"Technical details hidden: {'YES' if 'forecast_economic_indicator' not in cleaned else 'NO'}")
