"""
Test the Dataset Curator Agent
Demonstrates how the agent evaluates datasets for inclusion in the core knowledge base
"""

import pandas as pd
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.curator_agent import DatasetCuratorAgent

def test_high_quality_moldova_dataset():
    """Test with a high-quality Moldova economics dataset"""
    print("\n" + "="*70)
    print("TEST 1: High-Quality Moldova Trade Dataset")
    print("="*70)
    
    # Create sample Moldova trade data
    data = {
        'Year': [2020, 2021, 2022, 2023, 2024],
        'Month': ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
        'Moldova_Exports_USD': [100000, 120000, 135000, 150000, 165000],
        'Moldova_Imports_USD': [150000, 155000, 160000, 170000, 180000],
        'Trade_Balance': [-50000, -35000, -25000, -20000, -15000],
        'GDP_Growth_Moldova': [2.5, 3.1, 3.8, 4.2, 4.5],
        'Inflation_Rate_Moldova': [3.2, 3.5, 2.8, 2.5, 2.3],
        'Exchange_Rate_MDL_USD': [17.5, 17.8, 18.2, 18.5, 18.8]
    }
    df = pd.DataFrame(data)
    
    metadata = {
        'source': 'National Bureau of Statistics Moldova (statistica.md)',
        'filename': 'moldova_trade_2020_2024.csv',
        'description': 'Official Moldova trade statistics',
        'url': 'https://statistica.md',
        'date_created': '2024-10-01',
        'verified': True
    }
    
    curator = DatasetCuratorAgent()
    evaluation = curator.evaluate_dataset(df, metadata)
    report = curator.generate_report(evaluation)
    
    print(report)
    return evaluation

def test_low_quality_irrelevant_dataset():
    """Test with a low-quality, irrelevant dataset"""
    print("\n" + "="*70)
    print("TEST 2: Low-Quality Irrelevant Dataset")
    print("="*70)
    
    # Create irrelevant data with quality issues
    data = {
        'Product': ['Widget A', 'Widget B', None, 'Widget D', 'Widget A'],  # Duplicates & missing
        'Sales': [100, 200, 300, 400, 100],  # Duplicate row
        'Price': ['$5', '$10', '$15', 'invalid', '$5'],  # Type inconsistency
        'Country': ['USA', 'Canada', 'Mexico', 'USA', 'USA']  # Not Moldova
    }
    df = pd.DataFrame(data)
    
    metadata = {
        'source': 'Unknown',
        'filename': 'random_sales.csv',
        'description': ''
    }
    
    curator = DatasetCuratorAgent()
    evaluation = curator.evaluate_dataset(df, metadata)
    report = curator.generate_report(evaluation)
    
    print(report)
    return evaluation

def test_moderate_dataset_needs_review():
    """Test with a moderate quality dataset that might need review"""
    print("\n" + "="*70)
    print("TEST 3: Moderate Quality Dataset - Needs Review")
    print("="*70)
    
    # Create Moldova data but with some issues
    data = {
        'Date': pd.date_range('2024-01-01', periods=12, freq='MS'),
        'Indicator': ['Exports'] * 12,
        'Value': [100000, 105000, None, 115000, 120000, 125000,  # Missing value
                  130000, 135000, 140000, 145000, 150000, 155000],
        'Currency': ['USD'] * 12,
        'Notes': ['Moldova data'] * 12
    }
    df = pd.DataFrame(data)
    
    metadata = {
        'source': 'Government report',
        'filename': 'trade_report_2024.xlsx',
        'description': 'Moldova monthly trade indicators',
        'url': 'https://gov.md/reports/trade'
    }
    
    curator = DatasetCuratorAgent()
    evaluation = curator.evaluate_dataset(df, metadata)
    report = curator.generate_report(evaluation)
    
    print(report)
    return evaluation

def test_summary():
    """Run all tests and show summary"""
    print("\n" + "#"*70)
    print("# DATASET CURATOR AGENT - TEST SUMMARY")
    print("#"*70)
    
    eval1 = test_high_quality_moldova_dataset()
    eval2 = test_low_quality_irrelevant_dataset()
    eval3 = test_moderate_dataset_needs_review()
    
    print("\n" + "="*70)
    print("📊 SUMMARY OF RECOMMENDATIONS")
    print("="*70)
    
    tests = [
        ("High-Quality Moldova Dataset", eval1),
        ("Low-Quality Irrelevant Dataset", eval2),
        ("Moderate Dataset", eval3)
    ]
    
    for name, evaluation in tests:
        rec = evaluation['recommendation']
        score = evaluation['overall_score']
        
        # Color-code based on recommendation
        if rec == 'ACCEPT':
            symbol = '✅'
        elif rec == 'ACCEPT_WITH_REVIEW':
            symbol = '⚠️'
        elif rec == 'CONDITIONAL':
            symbol = '❓'
        else:
            symbol = '❌'
        
        print(f"{symbol} {name:40} | {rec:20} | Score: {score}/1.0")
    
    print("="*70)
    print("\n💡 Key Takeaways:")
    print("  • High-quality Moldova economics data from trusted sources → ACCEPT")
    print("  • Low-quality or irrelevant data → REJECT")
    print("  • Decent data with issues → ACCEPT_WITH_REVIEW (manual check)")
    print("  • System protects knowledge base quality automatically!\n")

if __name__ == "__main__":
    test_summary()
