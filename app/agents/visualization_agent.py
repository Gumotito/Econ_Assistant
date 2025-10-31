"""Data Visualization Agent - Automatically generates charts from numeric data"""
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
from datetime import datetime
import base64
from io import BytesIO

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 10

class DataVisualizationAgent:
    """
    Automatically detects when data can be visualized and generates appropriate charts.
    Supports: line charts, bar charts, forecasts, comparisons, trends.
    """
    
    def __init__(self, output_dir="static/charts"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def should_visualize(self, data: dict) -> bool:
        """Determine if data is suitable for visualization"""
        # Check if data contains numeric values
        if isinstance(data, dict):
            # Has forecast results
            if 'forecasts' in data and isinstance(data['forecasts'], list):
                return len(data['forecasts']) > 0
            
            # Has time series data
            if 'values' in data and isinstance(data['values'], list):
                return len(data['values']) >= 2
            
            # Has comparison data
            if 'categories' in data and 'values' in data:
                return True
        
        return False
    
    def create_forecast_chart(self, data: dict, title: str = "Economic Forecast") -> dict:
        """
        Create a forecast visualization with historical data and predictions.
        
        Returns:
            Dict with image_path, image_url, and base64_image
        """
        fig, ax = plt.subplots(figsize=(12, 7))
        
        # Extract data
        forecasts = data.get('forecasts', [])
        indicator = data.get('indicator', 'Value')
        method = data.get('method', 'ensemble')
        
        # Historical data (if available)
        historical = data.get('historical_values', [])
        
        # Create time axis
        if historical:
            hist_x = list(range(1, len(historical) + 1))
            forecast_x = list(range(len(historical) + 1, len(historical) + len(forecasts) + 1))
        else:
            forecast_x = list(range(1, len(forecasts) + 1))
            hist_x = []
        
        # Plot historical data
        if historical:
            ax.plot(hist_x, historical, 'o-', linewidth=2, markersize=6, 
                   label='Historical Data', color='#2E86AB')
        
        # Plot forecasts
        ax.plot(forecast_x, forecasts, 's--', linewidth=2, markersize=6,
               label='Forecast', color='#A23B72')
        
        # Add confidence interval if available
        if 'lower_bound' in data and 'upper_bound' in data:
            lower = data['lower_bound']
            upper = data['upper_bound']
            ax.fill_between(forecast_x, lower, upper, alpha=0.2, color='#A23B72',
                           label='Confidence Interval (85%-115%)')
        
        # Formatting
        ax.set_xlabel('Time Period', fontsize=12, fontweight='bold')
        ax.set_ylabel(f'{indicator}', fontsize=12, fontweight='bold')
        ax.set_title(f'{title}\nMethod: {method.capitalize()}', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.legend(loc='best', frameon=True, shadow=True)
        ax.grid(True, alpha=0.3)
        
        # Add quality metrics if available
        if 'r_squared' in data or 'mape' in data:
            metrics_text = []
            if 'r_squared' in data:
                metrics_text.append(f"R² = {data['r_squared']:.3f}")
            if 'mape' in data:
                metrics_text.append(f"MAPE = {data['mape']:.1f}%")
            
            if metrics_text:
                ax.text(0.02, 0.98, '\n'.join(metrics_text),
                       transform=ax.transAxes, fontsize=10,
                       verticalalignment='top',
                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"forecast_{indicator}_{timestamp}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        
        # Convert to base64 for embedding
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        
        plt.close()
        
        return {
            'image_path': filepath,
            'image_url': f'/static/charts/{filename}',
            'base64_image': image_base64,
            'filename': filename
        }
    
    def create_comparison_chart(self, categories: list, values: list, 
                               title: str = "Comparison", ylabel: str = "Value") -> dict:
        """Create a bar chart for comparing categories"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Create bar chart
        bars = ax.bar(categories, values, color=sns.color_palette("husl", len(categories)),
                     edgecolor='black', linewidth=1.2)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:,.0f}',
                   ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, axis='y', alpha=0.3)
        
        # Rotate labels if many categories
        if len(categories) > 5:
            plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comparison_{timestamp}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        
        plt.close()
        
        return {
            'image_path': filepath,
            'image_url': f'/static/charts/{filename}',
            'base64_image': image_base64,
            'filename': filename
        }
    
    def create_time_series_chart(self, dates: list, values: list,
                                 title: str = "Time Series", ylabel: str = "Value") -> dict:
        """Create a time series line chart"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(dates, values, 'o-', linewidth=2, markersize=5, color='#2E86AB')
        
        ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3)
        
        # Rotate date labels
        plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"timeseries_{timestamp}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        
        plt.close()
        
        return {
            'image_path': filepath,
            'image_url': f'/static/charts/{filename}',
            'base64_image': image_base64,
            'filename': filename
        }
    
    def create_pie_chart(self, categories: list, values: list, 
                        title: str = "Distribution") -> dict:
        """Create a pie chart for showing proportions"""
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Create pie chart
        colors = sns.color_palette("Set2", len(categories))
        wedges, texts, autotexts = ax.pie(values, labels=categories, autopct='%1.1f%%',
                                          colors=colors, startangle=90,
                                          textprops={'fontsize': 11, 'weight': 'bold'})
        
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        
        plt.tight_layout()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pie_{timestamp}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        
        plt.close()
        
        return {
            'image_path': filepath,
            'image_url': f'/static/charts/{filename}',
            'base64_image': image_base64,
            'filename': filename
        }
    
    def auto_visualize(self, data: dict, context: str = "") -> dict:
        """
        Automatically choose the best visualization based on data structure.
        
        Args:
            data: Dictionary containing data to visualize
            context: Context string to help determine chart type
        
        Returns:
            Visualization result dict or None if not suitable
        """
        if not self.should_visualize(data):
            return None
        
        # Forecast data
        if 'forecasts' in data:
            title = f"Moldova {data.get('indicator', 'Economic Indicator')} Forecast"
            return self.create_forecast_chart(data, title)
        
        # Comparison data
        if 'categories' in data and 'values' in data:
            categories = data['categories']
            values = data['values']
            
            # Determine chart type based on context
            if 'distribution' in context.lower() or 'share' in context.lower():
                return self.create_pie_chart(categories, values, 
                                            data.get('title', 'Distribution'))
            else:
                return self.create_comparison_chart(categories, values,
                                                    data.get('title', 'Comparison'),
                                                    data.get('ylabel', 'Value'))
        
        # Time series data
        if 'dates' in data and 'values' in data:
            return self.create_time_series_chart(data['dates'], data['values'],
                                                data.get('title', 'Time Series'),
                                                data.get('ylabel', 'Value'))
        
        return None


def get_visualization_agent():
    """Factory function to get visualization agent instance"""
    return DataVisualizationAgent()
