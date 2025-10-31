"""Economic forecasting tools using established economic models and formulas"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
from datetime import datetime
import json

class EconomicForecaster:
    """Economic forecasting using time series analysis and economic models"""
    
    def __init__(self, dataset: pd.DataFrame = None):
        self.dataset = dataset
    
    def linear_trend(self, values: List[float], periods_ahead: int = 1) -> Dict[str, Any]:
        """
        Simple linear trend forecast using least squares regression
        Y = a + bX where b = slope, a = intercept
        """
        n = len(values)
        if n < 2:
            return {"error": "Need at least 2 data points for trend analysis"}
        
        x = np.arange(n)
        y = np.array(values)
        
        # Calculate slope and intercept
        x_mean = np.mean(x)
        y_mean = np.mean(y)
        
        numerator = np.sum((x - x_mean) * (y - y_mean))
        denominator = np.sum((x - x_mean) ** 2)
        
        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
        
        # Forecast
        forecast_periods = np.arange(n, n + periods_ahead)
        forecasts = intercept + slope * forecast_periods
        
        # Calculate R-squared for model quality
        y_pred = intercept + slope * x
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - y_mean) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        return {
            "method": "Linear Trend",
            "forecasts": forecasts.tolist(),
            "slope": float(slope),
            "intercept": float(intercept),
            "r_squared": float(r_squared),
            "trend": "increasing" if slope > 0 else "decreasing",
            "quality": "good" if r_squared > 0.7 else "moderate" if r_squared > 0.4 else "poor"
        }
    
    def exponential_smoothing(self, values: List[float], alpha: float = 0.3, 
                             periods_ahead: int = 1) -> Dict[str, Any]:
        """
        Exponential smoothing forecast
        S_t = α*Y_t + (1-α)*S_(t-1)
        Good for data with no trend or seasonality
        """
        if len(values) < 2:
            return {"error": "Need at least 2 data points"}
        
        # Initialize with first value
        smoothed = [values[0]]
        
        # Calculate smoothed values
        for i in range(1, len(values)):
            s_t = alpha * values[i] + (1 - alpha) * smoothed[-1]
            smoothed.append(s_t)
        
        # Forecast (using last smoothed value)
        forecasts = [smoothed[-1]] * periods_ahead
        
        # Calculate Mean Absolute Percentage Error (MAPE)
        errors = [abs(values[i] - smoothed[i]) / values[i] * 100 
                 for i in range(1, len(values)) if values[i] != 0]
        mape = np.mean(errors) if errors else 0
        
        return {
            "method": "Exponential Smoothing",
            "forecasts": forecasts,
            "alpha": alpha,
            "last_smoothed": float(smoothed[-1]),
            "mape": float(mape),
            "accuracy": "excellent" if mape < 10 else "good" if mape < 20 else "moderate"
        }
    
    def moving_average(self, values: List[float], window: int = 3, 
                      periods_ahead: int = 1) -> Dict[str, Any]:
        """
        Moving average forecast
        MA_t = (Y_t + Y_(t-1) + ... + Y_(t-n+1)) / n
        """
        if len(values) < window:
            return {"error": f"Need at least {window} data points for {window}-period moving average"}
        
        # Calculate moving averages
        moving_avgs = []
        for i in range(window - 1, len(values)):
            ma = np.mean(values[i - window + 1:i + 1])
            moving_avgs.append(ma)
        
        # Forecast using last moving average
        last_ma = np.mean(values[-window:])
        forecasts = [last_ma] * periods_ahead
        
        return {
            "method": f"{window}-Period Moving Average",
            "forecasts": forecasts,
            "window": window,
            "last_ma": float(last_ma)
        }
    
    def growth_rate_forecast(self, values: List[float], periods_ahead: int = 1) -> Dict[str, Any]:
        """
        Compound growth rate forecast
        CAGR = (Ending Value / Beginning Value)^(1/n) - 1
        Future Value = Current Value * (1 + CAGR)^n
        """
        if len(values) < 2:
            return {"error": "Need at least 2 data points"}
        
        beginning = values[0]
        ending = values[-1]
        n_periods = len(values) - 1
        
        if beginning <= 0 or ending <= 0:
            return {"error": "Growth rate requires positive values"}
        
        # Calculate CAGR
        cagr = (ending / beginning) ** (1 / n_periods) - 1
        
        # Forecast
        forecasts = []
        current = ending
        for i in range(periods_ahead):
            current = current * (1 + cagr)
            forecasts.append(current)
        
        # Calculate average period-to-period growth
        period_growth = [values[i] / values[i-1] - 1 
                        for i in range(1, len(values)) if values[i-1] != 0]
        avg_growth = np.mean(period_growth) if period_growth else 0
        
        return {
            "method": "Compound Annual Growth Rate (CAGR)",
            "forecasts": forecasts,
            "cagr": float(cagr),
            "cagr_percent": float(cagr * 100),
            "avg_period_growth": float(avg_growth * 100),
            "beginning_value": float(beginning),
            "ending_value": float(ending)
        }
    
    def seasonal_naive(self, values: List[float], season_length: int = 12, 
                      periods_ahead: int = 1) -> Dict[str, Any]:
        """
        Seasonal naive forecast - uses value from same season last year
        Good for data with strong seasonality (e.g., monthly data)
        """
        if len(values) < season_length:
            return {"error": f"Need at least {season_length} periods for seasonal forecast"}
        
        # Forecast by repeating seasonal pattern
        forecasts = []
        for i in range(periods_ahead):
            seasonal_index = (len(values) + i) % season_length
            if seasonal_index < len(values):
                forecasts.append(values[-(season_length - seasonal_index)])
            else:
                forecasts.append(values[-1])
        
        return {
            "method": f"Seasonal Naive (season={season_length})",
            "forecasts": forecasts,
            "season_length": season_length
        }
    
    def ensemble_forecast(self, values: List[float], periods_ahead: int = 1) -> Dict[str, Any]:
        """
        Ensemble forecast combining multiple methods
        Uses weighted average of different forecasting methods
        """
        if len(values) < 3:
            return {"error": "Need at least 3 data points for ensemble forecast"}
        
        methods = []
        
        # Linear trend (weight: 0.3)
        trend = self.linear_trend(values, periods_ahead)
        if "forecasts" in trend:
            methods.append(("Linear Trend", trend["forecasts"], 0.3, trend.get("r_squared", 0)))
        
        # Exponential smoothing (weight: 0.3)
        exp_smooth = self.exponential_smoothing(values, periods_ahead=periods_ahead)
        if "forecasts" in exp_smooth:
            methods.append(("Exponential Smoothing", exp_smooth["forecasts"], 0.3, 
                          1 - exp_smooth.get("mape", 100) / 100))
        
        # Growth rate (weight: 0.2)
        growth = self.growth_rate_forecast(values, periods_ahead)
        if "forecasts" in growth:
            methods.append(("Growth Rate", growth["forecasts"], 0.2, 0.5))
        
        # Moving average (weight: 0.2)
        ma = self.moving_average(values, window=min(3, len(values)), periods_ahead=periods_ahead)
        if "forecasts" in ma:
            methods.append(("Moving Average", ma["forecasts"], 0.2, 0.5))
        
        if not methods:
            return {"error": "No valid forecasting methods could be applied"}
        
        # Calculate weighted ensemble
        ensemble_forecasts = []
        for period in range(periods_ahead):
            weighted_sum = sum(m[1][period] * m[2] for m in methods)
            total_weight = sum(m[2] for m in methods)
            ensemble_forecasts.append(weighted_sum / total_weight)
        
        # Calculate confidence bounds (±15% as simple approximation)
        lower_bound = [f * 0.85 for f in ensemble_forecasts]
        upper_bound = [f * 1.15 for f in ensemble_forecasts]
        
        return {
            "method": "Ensemble (Combined Methods)",
            "forecasts": ensemble_forecasts,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "methods_used": [m[0] for m in methods],
            "confidence": "moderate"
        }


# Global forecaster instance
forecaster = EconomicForecaster()


def forecast_economic_indicator(indicator: str = None, query: str = None, 
                                time_periods: int = 12, method: str = "ensemble") -> str:
    """
    Forecast future values of an economic indicator using historical data.
    
    Args:
        indicator: Name of the economic indicator (e.g., "GDP", "exports", "imports", "Value")
        query: Alternative parameter name for indicator (for compatibility)
        time_periods: Number of periods ahead to forecast (default: 12 months)
        method: Forecasting method - "ensemble", "trend", "growth", "smooth", "moving_average"
    
    Returns:
        JSON string with forecast results
    
    Available methods:
    - ensemble: Combines multiple methods (RECOMMENDED)
    - trend: Linear trend analysis (good for steady growth/decline)
    - growth: Compound growth rate (good for exponential patterns)
    - smooth: Exponential smoothing (good for stable data)
    - moving_average: Simple moving average (good for removing noise)
    
    Example: forecast_economic_indicator("exports", 6, "ensemble")
    """
    # Handle both parameter names for compatibility
    if query and not indicator:
        indicator = query
    
    if not indicator:
        return json.dumps({"error": "indicator parameter is required"})
    
    try:
        from run import dataset_state
        
        if dataset_state.dataset is None or dataset_state.dataset.empty:
            return json.dumps({
                "error": "No dataset loaded. Please upload data first.",
                "available_methods": ["ensemble", "trend", "growth", "smooth", "moving_average"]
            })
        
        df = dataset_state.dataset
        
        # Find relevant column
        value_col = None
        for col in df.columns:
            if indicator.lower() in col.lower():
                value_col = col
                break
        
        if value_col is None:
            return json.dumps({
                "error": f"Could not find indicator '{indicator}' in current dataset",
                "available_columns": list(df.columns),
                "suggestion": f"The current dataset contains import data only. For '{indicator}' data, try: 1) search_official_sources('Moldova {indicator}') to find authoritative data, or 2) Upload a dataset containing '{indicator}' column",
                "next_steps": [
                    f"search_official_sources('Moldova {indicator} historical data')",
                    f"web_search('Moldova {indicator} statistics statistica.md')"
                ]
            })
        
        # Extract time series data
        values = df[value_col].dropna().tolist()
        
        if len(values) < 2:
            return json.dumps({
                "error": f"Insufficient data for '{indicator}'. Need at least 2 data points.",
                "data_points": len(values)
            })
        
        # Update forecaster with current dataset
        forecaster.dataset = df
        
        # Apply selected forecasting method
        if method == "ensemble":
            result = forecaster.ensemble_forecast(values, time_periods)
        elif method == "trend":
            result = forecaster.linear_trend(values, time_periods)
        elif method == "growth":
            result = forecaster.growth_rate_forecast(values, time_periods)
        elif method == "smooth":
            result = forecaster.exponential_smoothing(values, periods_ahead=time_periods)
        elif method == "moving_average":
            result = forecaster.moving_average(values, periods_ahead=time_periods)
        else:
            return json.dumps({
                "error": f"Unknown method '{method}'",
                "available_methods": ["ensemble", "trend", "growth", "smooth", "moving_average"]
            })
        
        # Add metadata
        result["indicator"] = indicator
        result["historical_periods"] = len(values)
        result["forecast_periods"] = time_periods
        result["last_actual_value"] = float(values[-1])
        result["data_range"] = f"{min(values):.2f} to {max(values):.2f}"
        
        # Add interpretation
        if "forecasts" in result:
            forecast_change = ((result["forecasts"][0] - values[-1]) / values[-1] * 100)
            result["forecast_change_percent"] = float(forecast_change)
            result["interpretation"] = (
                f"Forecast suggests {abs(forecast_change):.1f}% "
                f"{'increase' if forecast_change > 0 else 'decrease'} "
                f"in the next period"
            )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"Forecasting error: {str(e)}",
            "indicator": indicator,
            "method": method
        })


def forecast_trade_balance(export_indicator: str = "Value", 
                          import_indicator: str = "Value",
                          periods_ahead: int = 6) -> str:
    """
    Forecast trade balance (exports - imports) based on historical patterns.
    
    Args:
        export_indicator: Column name for exports (default: "Value")
        import_indicator: Column name for imports (default: "Value")
        periods_ahead: Number of periods to forecast (default: 6)
    
    Returns:
        JSON string with trade balance forecast
    
    Example: forecast_trade_balance("Value", "Value", 12)
    """
    try:
        from run import dataset_state
        
        if dataset_state.dataset is None or dataset_state.dataset.empty:
            return json.dumps({"error": "No dataset loaded"})
        
        df = dataset_state.dataset
        
        # Try to identify export and import data
        # Assuming dataset has Flow column or similar
        if 'Flow' in df.columns:
            exports_df = df[df['Flow'].str.contains('Export', case=False, na=False)]
            imports_df = df[df['Flow'].str.contains('Import', case=False, na=False)]
            
            export_values = exports_df[export_indicator].dropna().tolist() if not exports_df.empty else []
            import_values = imports_df[import_indicator].dropna().tolist() if not imports_df.empty else []
        else:
            # If no Flow column, use all values
            export_values = df[export_indicator].dropna().tolist()
            import_values = []
        
        if len(export_values) < 2:
            return json.dumps({
                "error": "Insufficient export data for forecast",
                "suggestion": "Use forecast_economic_indicator() for individual indicators"
            })
        
        # Forecast exports
        export_forecast = forecaster.ensemble_forecast(export_values, periods_ahead)
        
        # Forecast imports if available
        import_forecast = None
        if len(import_values) >= 2:
            import_forecast = forecaster.ensemble_forecast(import_values, periods_ahead)
        
        # Calculate trade balance
        if import_forecast and "forecasts" in import_forecast:
            trade_balance = [
                export_forecast["forecasts"][i] - import_forecast["forecasts"][i]
                for i in range(periods_ahead)
            ]
            
            current_balance = export_values[-1] - import_values[-1] if import_values else export_values[-1]
        else:
            trade_balance = export_forecast.get("forecasts", [])
            current_balance = export_values[-1]
        
        result = {
            "method": "Trade Balance Forecast",
            "export_forecast": export_forecast.get("forecasts", []),
            "import_forecast": import_forecast.get("forecasts", []) if import_forecast else "Not available",
            "trade_balance_forecast": trade_balance,
            "current_balance": float(current_balance),
            "forecast_periods": periods_ahead,
            "interpretation": ""
        }
        
        # Add interpretation
        if trade_balance:
            avg_forecast_balance = np.mean(trade_balance)
            if avg_forecast_balance > 0:
                result["interpretation"] = f"Trade surplus expected: average ${avg_forecast_balance:,.0f}"
            else:
                result["interpretation"] = f"Trade deficit expected: average ${abs(avg_forecast_balance):,.0f}"
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"Trade balance forecast error: {str(e)}"})
