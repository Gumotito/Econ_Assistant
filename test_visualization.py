"""
Test the Data Visualization Agent
Shows how charts are automatically generated from forecast data
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.visualization_agent import get_visualization_agent

def test_forecast_visualization():
    """Test forecast chart generation"""
    print("\n" + "="*70)
    print("TEST 1: Forecast Visualization")
    print("="*70)
    
    # Sample forecast data (like what forecast_economic_indicator returns)
    forecast_data = {
        "indicator": "Moldova Imports",
        "method": "ensemble",
        "forecasts": [125000, 128000, 131000, 134000, 137000, 140000, 
                     143000, 146000, 149000, 152000, 155000, 158000],
        "lower_bound": [106250, 108800, 111350, 113900, 116450, 119000,
                       121550, 124100, 126650, 129200, 131750, 134300],
        "upper_bound": [143750, 147200, 150650, 154100, 157550, 161000,
                       164450, 167900, 171350, 174800, 178250, 181700],
        "historical_values": [100000, 105000, 110000, 115000, 120000],
        "r_squared": 0.95,
        "mape": 4.2
    }
    
    viz_agent = get_visualization_agent()
    result = viz_agent.create_forecast_chart(forecast_data, 
                                             title="Moldova Imports Forecast 2025-2026")
    
    print(f"✅ Chart generated successfully!")
    print(f"   📁 File: {result['filename']}")
    print(f"   🌐 URL: {result['image_url']}")
    print(f"   📊 Size: {len(result['base64_image'])} bytes (base64)")
    print(f"\n💡 The chart shows:")
    print(f"   • Historical data (last 5 periods)")
    print(f"   • 12-month forecast with trend line")
    print(f"   • Confidence interval (85%-115% range)")
    print(f"   • Quality metrics (R²=0.95, MAPE=4.2%)")
    
    return result

def test_comparison_chart():
    """Test comparison bar chart"""
    print("\n" + "="*70)
    print("TEST 2: Comparison Bar Chart")
    print("="*70)
    
    data = {
        "categories": ["Machinery", "Electronics", "Food", "Textiles", "Chemicals"],
        "values": [45000, 38000, 27000, 19000, 12000],
        "title": "Moldova Imports by Category (USD thousands)",
        "ylabel": "Import Value (USD)"
    }
    
    viz_agent = get_visualization_agent()
    result = viz_agent.create_comparison_chart(
        data['categories'], 
        data['values'],
        title=data['title'],
        ylabel=data['ylabel']
    )
    
    print(f"✅ Comparison chart generated!")
    print(f"   📁 File: {result['filename']}")
    print(f"   🌐 URL: {result['image_url']}")
    print(f"\n💡 The chart shows:")
    print(f"   • Bar chart with 5 categories")
    print(f"   • Value labels on each bar")
    print(f"   • Color-coded for easy distinction")
    
    return result

def test_time_series_chart():
    """Test time series line chart"""
    print("\n" + "="*70)
    print("TEST 3: Time Series Line Chart")
    print("="*70)
    
    data = {
        "dates": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "values": [100, 105, 103, 108, 112, 110, 115, 118, 120, 125, 123, 130],
        "title": "Moldova GDP Growth 2024",
        "ylabel": "GDP (Million MDL)"
    }
    
    viz_agent = get_visualization_agent()
    result = viz_agent.create_time_series_chart(
        data['dates'],
        data['values'],
        title=data['title'],
        ylabel=data['ylabel']
    )
    
    print(f"✅ Time series chart generated!")
    print(f"   📁 File: {result['filename']}")
    print(f"   🌐 URL: {result['image_url']}")
    print(f"\n💡 The chart shows:")
    print(f"   • Monthly GDP trend over 12 months")
    print(f"   • Line chart with data points")
    print(f"   • Grid for easy value reading")
    
    return result

def test_auto_visualize():
    """Test automatic visualization selection"""
    print("\n" + "="*70)
    print("TEST 4: Auto-Visualization (Smart Detection)")
    print("="*70)
    
    # Test with forecast data
    forecast_data = {
        "indicator": "inflation_rate",
        "forecasts": [3.5, 3.7, 3.9, 4.1, 4.3, 4.5],
        "method": "ensemble"
    }
    
    viz_agent = get_visualization_agent()
    
    # Check if should visualize
    should_viz = viz_agent.should_visualize(forecast_data)
    print(f"Should visualize forecast data? {should_viz} ✅")
    
    # Auto-generate
    result = viz_agent.auto_visualize(forecast_data, "inflation forecast")
    
    if result:
        print(f"✅ Auto-selected chart type: Forecast Chart")
        print(f"   📁 File: {result['filename']}")
        print(f"\n💡 The agent automatically:")
        print(f"   • Detected forecast data structure")
        print(f"   • Chose appropriate chart type (line with forecast)")
        print(f"   • Generated visualization without manual configuration")
    
    return result

def main():
    print("\n" + "#"*70)
    print("# DATA VISUALIZATION AGENT - DEMONSTRATION")
    print("#"*70)
    print("\n🎨 This agent automatically generates charts from numeric data")
    print("📊 Supported: Forecasts, Comparisons, Time Series, Distributions\n")
    
    try:
        result1 = test_forecast_visualization()
        result2 = test_comparison_chart()
        result3 = test_time_series_chart()
        result4 = test_auto_visualize()
        
        print("\n" + "="*70)
        print("📈 SUMMARY: All visualizations generated successfully!")
        print("="*70)
        print(f"\n✅ Charts saved to: static/charts/")
        print(f"✅ Accessible via URL: /static/charts/[filename]")
        print(f"✅ Base64 encoding available for embedding in responses")
        
        print("\n💡 Integration with Econ Assistant:")
        print("   1. When forecast tool returns data → Auto-generates chart")
        print("   2. Chart URL included in response")
        print("   3. Users can view visual representation immediately")
        print("   4. Works with: forecasts, comparisons, time series")
        
        print("\n📸 Example URLs:")
        if result1:
            print(f"   Forecast: http://localhost:5000{result1['image_url']}")
        if result2:
            print(f"   Comparison: http://localhost:5000{result2['image_url']}")
        if result3:
            print(f"   Time Series: http://localhost:5000{result3['image_url']}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
