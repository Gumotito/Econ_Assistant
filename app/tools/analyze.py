"""Column analysis tool"""
import json
import pandas as pd

try:
    from langsmith import traceable
except:
    def traceable(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

# Global reference
current_dataset = None

def set_dataset(dataset):
    global current_dataset
    current_dataset = dataset

@traceable(name="analyze_column", run_type="tool")
def analyze_column(column: str, analysis_type: str = "summary") -> str:
    """Analyze dataset column"""
    if current_dataset is None:
        return "No dataset loaded"
    
    try:
        if column not in current_dataset.columns:
            return f"Column '{column}' not found. Available: {', '.join(current_dataset.columns)}"
        
        if analysis_type == "summary":
            stats = current_dataset[column].describe().to_dict()
            return json.dumps(stats, indent=2)
        elif analysis_type == "distribution":
            dist = current_dataset[column].value_counts().head(10).to_dict()
            return json.dumps(dist, indent=2)
        elif analysis_type == "correlation":
            if current_dataset[column].dtype in ['int64', 'float64']:
                corr = current_dataset.corr()[column].to_dict()
                return json.dumps(corr, indent=2)
            return f"Column '{column}' is not numeric"
    except Exception as e:
        return f"Analysis error: {str(e)}"
