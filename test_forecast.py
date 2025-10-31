"""
Test forecasting tools
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools.forecast import EconomicForecaster
import json

# Sample data - Moldova monthly imports (in millions USD)
sample_data = [
    100, 105, 110, 108, 115, 120, 118, 125, 130, 128, 135, 140,  # Year 1
    142, 148, 155, 152, 160, 168, 165, 172, 178, 175, 182, 188   # Year 2
]

print("=" * 80)
print("ECONOMIC FORECASTING DEMO")
print("=" * 80)
print(f"\nHistorical Data (24 months): {sample_data}")
print(f"Last value: ${sample_data[-1]}M")
print("\n")

forecaster = EconomicForecaster()

# Test 1: Linear Trend
print("1. LINEAR TREND FORECAST")
print("-" * 80)
result = forecaster.linear_trend(sample_data, periods_ahead=6)
print(json.dumps(result, indent=2))
print("\n")

# Test 2: Exponential Smoothing
print("2. EXPONENTIAL SMOOTHING FORECAST")
print("-" * 80)
result = forecaster.exponential_smoothing(sample_data, alpha=0.3, periods_ahead=6)
print(json.dumps(result, indent=2))
print("\n")

# Test 3: Growth Rate (CAGR)
print("3. COMPOUND GROWTH RATE FORECAST")
print("-" * 80)
result = forecaster.growth_rate_forecast(sample_data, periods_ahead=6)
print(json.dumps(result, indent=2))
print("\n")

# Test 4: Moving Average
print("4. MOVING AVERAGE FORECAST")
print("-" * 80)
result = forecaster.moving_average(sample_data, window=3, periods_ahead=6)
print(json.dumps(result, indent=2))
print("\n")

# Test 5: Ensemble (Recommended)
print("5. ENSEMBLE FORECAST (RECOMMENDED)")
print("-" * 80)
result = forecaster.ensemble_forecast(sample_data, periods_ahead=6)
print(json.dumps(result, indent=2))
print("\n")

print("=" * 80)
print("INTERPRETATION:")
print("=" * 80)
print(f"Current value: ${sample_data[-1]}M")
if "forecasts" in result:
    print(f"Next period forecast: ${result['forecasts'][0]:.2f}M")
    change = ((result['forecasts'][0] - sample_data[-1]) / sample_data[-1] * 100)
    print(f"Expected change: {change:+.1f}%")
    print(f"6-month range: ${min(result['forecasts']):.2f}M to ${max(result['forecasts']):.2f}M")
    if "lower_bound" in result:
        print(f"Confidence interval: ${result['lower_bound'][0]:.2f}M - ${result['upper_bound'][0]:.2f}M")

print("\n" + "=" * 80)
print("KEY INSIGHTS:")
print("=" * 80)
print("• Ensemble method combines multiple models for more reliable forecasts")
print("• Use 'trend' for steady growth patterns")
print("• Use 'growth' for exponential/compound growth")
print("• Use 'smooth' for volatile data that needs smoothing")
print("• Longer historical data = more accurate forecasts")
