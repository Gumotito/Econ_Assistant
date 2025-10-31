# Data Visualization Agent 📊

## Overview

The **Data Visualization Agent** automatically generates professional charts and graphs when numeric data is returned from queries. No manual configuration needed - it intelligently detects the data type and creates the appropriate visualization.

## What It Looks Like

### 1. Forecast Charts
When you ask for predictions like *"forecast imports for next year"*, the system generates:

![Forecast Example](docs/forecast_example_description.md)

**Features:**
- 📈 Historical data (blue line with circles)
- 🔮 Forecast predictions (purple line with squares)  
- 📊 Confidence interval (shaded area 85%-115%)
- 📉 Quality metrics (R², MAPE displayed)
- 🎯 Clear labels and grid

**Visual Style:**
```
┌─────────────────────────────────────────┐
│  Moldova Imports Forecast 2025-2026    │
│  Method: Ensemble                       │
├─────────────────────────────────────────┤
│                                         │
│     ●──●──●──●──● Historical           │
│                   ■- - ■- - ■ Forecast │
│                   ░░░░░░░░░ Confidence  │
│                                         │
│  R² = 0.950      MAPE = 4.2%           │
└─────────────────────────────────────────┘
```

### 2. Comparison Bar Charts
For queries like *"compare imports by category"*:

**Features:**
- 🎨 Color-coded bars
- 🔢 Value labels on each bar
- 📊 Automatic scaling
- 🏷️ Category names

**Visual Style:**
```
Moldova Imports by Category
┌───────────────────────┐
│  45,000               │
│  ████████  Machinery  │
│  38,000               │
│  ███████   Electronics│
│  27,000               │
│  █████     Food       │
└───────────────────────┘
```

### 3. Time Series Charts
For historical data like *"show GDP over time"*:

**Features:**
- 📅 Date labels on X-axis
- 📈 Smooth line with data points
- 🌐 Grid for easy reading
- 📊 Professional styling

**Visual Style:**
```
Moldova GDP Growth 2024
┌──────────────────────┐
│  130 ●               │
│  125 ●   ●           │
│  120 ●   ●   ●       │
│  115 ●   ●   ●   ●   │
│  Jan Feb Mar Apr May │
└──────────────────────┘
```

### 4. Pie Charts
For distribution queries like *"trade partners by share"*:

**Features:**
- 🥧 Proportional slices
- 📊 Percentage labels
- 🎨 Distinct colors
- 🏷️ Category legends

## How It Works

### Automatic Integration

1. **User asks question:**
   > "Forecast Moldova imports for next 12 months"

2. **System processes:**
   - Runs forecast_economic_indicator()
   - Returns numeric forecast data
   - **Visualization agent auto-detects** suitable data
   - Generates chart automatically

3. **Response includes:**
   ```
   📊 Forecast Results for Moldova Imports:
   
   Period 1: 125,000
   Period 2: 128,000
   ...
   Period 12: 158,000
   
   💡 Imports are projected to grow 26.4% over the next year
   
   📈 Visualization: View Chart
   http://localhost:5000/static/charts/forecast_Moldova_Imports_20251031.png
   ```

### Chart Types

| Data Type | Chart Generated | Use Case |
|-----------|----------------|----------|
| Forecast results | Line chart with confidence intervals | Future predictions |
| Category comparisons | Bar chart | Compare categories |
| Time series | Line chart | Historical trends |
| Proportions | Pie chart | Show distribution |

## Technical Details

### File Storage
- **Location**: `static/charts/`
- **Format**: PNG (150 DPI)
- **Naming**: `{type}_{indicator}_{timestamp}.png`
- **Example**: `forecast_Moldova_Imports_20251031_154832.png`

### Response Formats

**1. File URL** (for web display):
```
/static/charts/forecast_Moldova_Imports_20251031.png
```

**2. Base64 Encoding** (for embedding):
```json
{
  "base64_image": "iVBORw0KGgoAAAANSUhEUgA...",
  "filename": "forecast_Moldova_Imports_20251031.png"
}
```

### Chart Specifications

**Dimensions:**
- Forecast charts: 12" × 7" (1800×1050 pixels)
- Comparison charts: 10" × 6" (1500×900 pixels)
- Time series: 12" × 6" (1800×900 pixels)

**Colors:**
- Historical data: Blue (#2E86AB)
- Forecasts: Purple (#A23B72)
- Confidence intervals: Light purple (20% opacity)
- Comparisons: Seaborn "husl" palette

**Fonts:**
- Title: 14pt bold
- Axes labels: 12pt bold
- Data labels: 10pt
- Metrics box: 10pt regular

## Usage Examples

### Example 1: Forecast with Visualization
```python
# User query
"Forecast Moldova exports for next 6 months"

# System response
📊 Forecast Results for exports:
Period 1: 125,000
Period 2: 128,000
...
📈 Visualization: [View Chart](/static/charts/forecast_exports_123.png)
```

### Example 2: Comparison Chart
```python
# User query
"Compare imports by product category"

# Chart shows:
- Bar chart with 5 categories
- Values labeled on each bar
- Color-coded for distinction
```

### Example 3: Time Series
```python
# User query
"Show GDP trend for 2024"

# Chart shows:
- Monthly data points
- Smooth line connecting points
- Date labels on X-axis
```

## Configuration

### Enable/Disable Visualizations
In `app/routes/api_routes.py`:
```python
# Disable visualizations
viz_result = None

# Enable visualizations (default)
viz_result = viz_agent.auto_visualize(data, context)
```

### Customize Chart Style
In `app/agents/visualization_agent.py`:
```python
# Change colors
plt.rcParams['axes.prop_cycle'] = plt.cycler(color=['red', 'blue', 'green'])

# Change size
plt.rcParams['figure.figsize'] = (12, 8)

# Change style
sns.set_style("darkgrid")  # or "whitegrid", "dark", "white", "ticks"
```

## Benefits

✅ **Automatic**: No manual chart configuration needed
✅ **Professional**: Publication-quality styling
✅ **Fast**: Generated in <1 second
✅ **Accessible**: Available as URL or base64
✅ **Informative**: Includes metrics, labels, legends
✅ **Responsive**: Scales to different screen sizes

## Future Enhancements

Potential improvements:
- [ ] Interactive charts with plotly/D3.js
- [ ] Export to PDF/SVG
- [ ] Custom color themes per user
- [ ] Multi-chart dashboards
- [ ] Real-time chart updates (websockets)
- [ ] Mobile-optimized sizes

## Testing

Run the test suite:
```bash
python test_visualization.py
```

Generates 4 sample charts demonstrating all chart types.

## Summary

**The Visualization Agent makes data come alive!** 🎨

Instead of just numbers:
```
Period 1: 125000
Period 2: 128000
Period 3: 131000
```

Users get beautiful, professional charts that make trends immediately obvious:
📈 Line going up = Growth trend visible at a glance
📊 Confidence bands = Uncertainty quantified visually
🎯 Quality metrics = Trust in forecast displayed
