# Economic Forecasting Feature

## Overview

The Moldova Economics Assistant now includes **advanced forecasting capabilities** using established economic models and statistical methods. No more "further investigation needed" - the system can now predict future trends using your historical data.

## 🎯 Why This Feature?

**Before:** When asked "What will exports be next year?", the system would say:
> "Further investigation using official Moldovan economic sources or contacting relevant authorities would be necessary."

**Now:** The system uses statistical models to generate data-driven forecasts:
> "Based on ensemble forecasting (linear trend + growth rate + exponential smoothing), Moldova's exports are projected to reach $X million next month, representing a Y% increase."

## 📊 Available Forecasting Methods

### 1. **Ensemble (Recommended)** ⭐
Combines multiple forecasting methods with weighted averaging for the most reliable predictions.

**Use when:**
- You want the most reliable forecast
- You're not sure which method is best
- Making important predictions

**Methods combined:**
- Linear Trend (30% weight)
- Exponential Smoothing (30%)
- Growth Rate/CAGR (20%)
- Moving Average (20%)

**Example:**
```
forecast_economic_indicator("exports", 12, "ensemble")
```

### 2. **Linear Trend**
Uses least squares regression to fit a straight line through historical data.

**Formula:** `Y = a + bX`

**Use when:**
- Data shows steady increase or decrease
- Long-term trend is relatively stable
- Looking for simple projections

**Output includes:**
- Slope (rate of change per period)
- R-squared (model quality: >0.7 is good)
- Trend direction (increasing/decreasing)

### 3. **Growth Rate (CAGR)**
Compound Annual Growth Rate - calculates exponential growth.

**Formula:** `CAGR = (Ending Value / Beginning Value)^(1/n) - 1`

**Use when:**
- Data grows exponentially (like GDP, population)
- Economic indicators with compound growth
- Long-term projections

**Output includes:**
- CAGR percentage
- Average period-to-period growth
- Compounded forecasts

### 4. **Exponential Smoothing**
Weighted average that gives more importance to recent observations.

**Formula:** `S_t = α*Y_t + (1-α)*S_(t-1)`

**Use when:**
- Recent data is more relevant
- Data has noise but no strong trend
- Short to medium-term forecasts

**Output includes:**
- Alpha parameter (smoothing factor)
- MAPE (Mean Absolute Percentage Error)
- Accuracy rating

### 5. **Moving Average**
Simple average of last N periods.

**Use when:**
- Removing short-term fluctuations
- Data is very volatile
- Need a baseline expectation

**Output includes:**
- Window size
- Last moving average value

## 🛠️ How to Use

### Tool 1: `forecast_economic_indicator()`

Forecast any numeric economic indicator from your dataset.

**Parameters:**
- `indicator` (required): Name of the indicator (e.g., "GDP", "exports", "Value")
- `time_periods` (optional): How many periods ahead to forecast (default: 12)
- `method` (optional): Which method to use (default: "ensemble")

**Example Questions:**
- "Forecast exports for the next 6 months"
- "What will imports be next year?"
- "Predict GDP growth for 2026"
- "Use growth rate method to forecast trade value for next 12 months"

**Example Tool Call:**
```json
{
  "indicator": "Value",
  "time_periods": 6,
  "method": "ensemble"
}
```

**Example Response:**
```json
{
  "method": "Ensemble (Combined Methods)",
  "forecasts": [195.5, 198.2, 201.1, 203.8, 206.5, 209.3],
  "lower_bound": [166.2, 168.5, 170.9, 173.2, 175.5, 177.9],
  "upper_bound": [224.8, 227.9, 231.3, 234.4, 237.5, 240.7],
  "methods_used": ["Linear Trend", "Exponential Smoothing", "Growth Rate", "Moving Average"],
  "confidence": "moderate",
  "indicator": "Value",
  "historical_periods": 24,
  "forecast_periods": 6,
  "last_actual_value": 188.0,
  "forecast_change_percent": 4.0,
  "interpretation": "Forecast suggests 4.0% increase in the next period"
}
```

### Tool 2: `forecast_trade_balance()`

Forecast Moldova's trade balance (exports - imports) to predict surplus or deficit.

**Parameters:**
- `export_indicator` (optional): Column name for exports (default: "Value")
- `import_indicator` (optional): Column name for imports (default: "Value")
- `periods_ahead` (optional): Periods to forecast (default: 6)

**Example Questions:**
- "Will Moldova have a trade surplus next year?"
- "Forecast the trade balance for the next 6 months"
- "What is our expected trade deficit in 2026?"

**Example Response:**
```json
{
  "method": "Trade Balance Forecast",
  "export_forecast": [450, 455, 460, 465, 470, 475],
  "import_forecast": [520, 525, 530, 535, 540, 545],
  "trade_balance_forecast": [-70, -70, -70, -70, -70, -70],
  "current_balance": -65.0,
  "forecast_periods": 6,
  "interpretation": "Trade deficit expected: average $70,000"
}
```

## 📈 Understanding Forecast Quality

### R-squared (for Linear Trend)
- **> 0.7**: Good fit - data follows a clear trend
- **0.4 - 0.7**: Moderate fit - some trend but noisy
- **< 0.4**: Poor fit - data is too volatile for linear trend

### MAPE (for Exponential Smoothing)
- **< 10%**: Excellent accuracy
- **10-20%**: Good accuracy
- **> 20%**: Moderate accuracy

### Confidence Intervals (Ensemble)
- **Lower bound**: 85% of forecast (conservative estimate)
- **Upper bound**: 115% of forecast (optimistic estimate)
- **Forecast**: Most likely value

## 💡 Best Practices

### 1. **Minimum Data Requirements**
- **2 periods**: Minimum for any forecast
- **6+ periods**: Better for trend analysis
- **12+ periods**: Good for seasonal patterns
- **24+ periods**: Best for reliable long-term forecasts

### 2. **Choosing the Right Method**

| Data Characteristic | Recommended Method |
|---------------------|-------------------|
| Steady growth/decline | Linear Trend |
| Exponential growth | Growth Rate (CAGR) |
| Volatile data | Exponential Smoothing |
| Seasonal patterns | Seasonal Naive* |
| Not sure | **Ensemble** ⭐ |

*Seasonal naive available but requires season_length parameter

### 3. **Interpreting Results**

**Trust forecasts MORE when:**
- High R-squared (>0.7) or low MAPE (<10%)
- Long historical data (20+ periods)
- Stable, predictable patterns
- Recent data follows the trend

**Trust forecasts LESS when:**
- Short historical data (<6 periods)
- High volatility or randomness
- Recent disruptions (crisis, policy change)
- Structural breaks in the data

### 4. **Combining with Official Sources**

Best practice workflow:
1. Generate forecast using historical data
2. Use `search_official_sources()` to find expert forecasts
3. Use `verify_with_sources()` to cross-check your forecast
4. Report both: "Model forecasts X, official sources predict Y"

## 🔬 Technical Details

### Formulas Used

**Linear Trend:**
```
Slope (b) = Σ[(X - X̄)(Y - Ȳ)] / Σ[(X - X̄)²]
Intercept (a) = Ȳ - b*X̄
Forecast = a + b*X
```

**CAGR:**
```
CAGR = (Ending Value / Beginning Value)^(1/n) - 1
Future Value = Current Value * (1 + CAGR)^periods
```

**Exponential Smoothing:**
```
S_t = α*Y_t + (1-α)*S_(t-1)
where α = smoothing parameter (0.3 default)
```

**Moving Average:**
```
MA_t = (Y_t + Y_(t-1) + ... + Y_(t-n+1)) / n
```

**R-squared:**
```
R² = 1 - (SS_res / SS_tot)
where SS_res = Σ(Y - Ŷ)²
      SS_tot = Σ(Y - Ȳ)²
```

## 📝 Example Use Cases

### Use Case 1: Predict Next Year's Exports

**Question:** "What will Moldova's exports be in 2026?"

**System workflow:**
1. Searches dataset for export values
2. Extracts historical time series
3. Calls `forecast_economic_indicator("exports", 12, "ensemble")`
4. Interprets results with confidence intervals
5. Cross-checks with `search_official_sources()` if available

**Response:**
> "Based on ensemble forecasting using 24 months of historical data, Moldova's exports are projected to reach $X million by end of 2026, representing a Y% increase from current levels. The forecast has a confidence interval of $A million (conservative) to $B million (optimistic). Official IMF forecasts predict similar growth of Z%."

### Use Case 2: Trade Balance Projection

**Question:** "Will we have a trade surplus next year?"

**System workflow:**
1. Calls `forecast_trade_balance(periods_ahead=12)`
2. Analyzes export and import trends separately
3. Calculates projected balance (exports - imports)
4. Interprets surplus vs deficit

**Response:**
> "Based on current trends, Moldova is projected to maintain a trade deficit throughout 2026, averaging $X million per month. Exports are forecasted to grow 5% annually, but imports are expected to grow 7%, widening the trade gap slightly."

### Use Case 3: GDP Growth Forecast

**Question:** "Forecast GDP growth using CAGR method for next 5 years"

**System workflow:**
1. User explicitly requested "CAGR method"
2. Calls `forecast_economic_indicator("GDP", 60, "growth")`
3. Returns compound growth projections

**Response:**
> "Using compound annual growth rate (CAGR), Moldova's GDP is projected to grow from $X billion to $Y billion by 2030, representing a CAGR of Z%. This assumes the historical growth rate of the past decade continues."

## 🚨 Limitations & Disclaimers

1. **Past Performance ≠ Future Results**
   - Forecasts assume historical patterns continue
   - Cannot predict black swan events, crises, or policy changes

2. **Data Quality Matters**
   - Garbage in = garbage out
   - Verify your input data is accurate and complete

3. **Short-term vs Long-term**
   - More accurate for short-term (1-6 months)
   - Long-term (>2 years) forecasts have higher uncertainty

4. **External Factors**
   - Cannot account for: wars, pandemics, policy changes, global crises
   - Use expert judgment alongside statistical forecasts

5. **Complement, Don't Replace**
   - Use forecasts as ONE input to decision-making
   - Always cross-check with official sources
   - Consider expert analysis and qualitative factors

## 🎓 Learning Resources

**Statistical Forecasting:**
- Hyndman & Athanasopoulos: "Forecasting: Principles and Practice"
- Box-Jenkins ARIMA models (future enhancement)
- Seasonal decomposition methods

**Economic Indicators:**
- IMF: World Economic Outlook
- World Bank: Global Economic Prospects
- OECD: Economic Outlook

## 🔄 Future Enhancements

Planned features:
- [ ] ARIMA (Auto-Regressive Integrated Moving Average)
- [ ] Seasonal decomposition (STL)
- [ ] Prophet (Facebook's forecasting tool)
- [ ] Machine learning models (LSTM, XGBoost)
- [ ] Confidence intervals from bootstrap sampling
- [ ] Multi-variate forecasting (consider multiple indicators)
- [ ] Scenario analysis (best/worst/base case)

## 📞 Support

If forecasts seem unrealistic:
1. Check input data quality
2. Try different forecasting methods
3. Use ensemble for most reliable results
4. Cross-check with official sources
5. Consider external factors not in the data

---

**Remember:** Forecasting is an art AND a science. Use these tools wisely, cross-check with official sources, and always apply critical thinking to the results! 🎯
