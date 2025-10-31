# Dataset Curator Agent 🎯

## Overview

The **Dataset Curator Agent** is an intelligent gatekeeper that automatically evaluates uploaded datasets to determine if they should be added to the core knowledge base. This ensures the LLM only learns from high-quality, relevant data.

## Purpose

When users upload datasets, we want to:
1. ✅ **Accept** high-quality Moldova economics data from trusted sources
2. ⚠️ **Review** good data with minor issues before adding
3. ❓ **Keep user-specific** data that's useful but not relevant to everyone
4. ❌ **Reject** low-quality or irrelevant data

## Evaluation Criteria

The curator evaluates datasets across **5 dimensions**:

### 1. **Quality Score** (25% weight)
- **Completeness**: % of non-missing values
- **Type Consistency**: Proper data types (numbers as numbers, not strings)
- **Uniqueness**: No duplicate rows
- **Outlier Detection**: Reasonable values (flags excessive outliers)

**Example**: A dataset with 95% complete data, no duplicates, proper types → 1.0/1.0

### 2. **Relevance Score** (30% weight) - HIGHEST PRIORITY
- **Moldova Focus**: Keywords like "moldova", "moldovan", "lei", "chisinau"
- **Economic Indicators**: GDP, exports, imports, inflation, trade, etc.
- **Content Analysis**: Checks column names AND actual data
- **Metadata**: Source description mentions Moldova

**Example**: Dataset with "Moldova_Exports" and "GDP_Moldova" columns → High relevance

### 3. **Novelty Score** (20% weight)
- **Content Overlap**: Compares against existing knowledge base
- **New Time Periods**: Recent data (2024-2025) gets bonus points
- **Unique Information**: Not a duplicate of existing data

**Example**: Brand new 2025 trade data → High novelty

### 4. **Coverage Score** (15% weight)
- **Time Range**: Years of historical data
- **Granularity**: Monthly/quarterly is better than annual
- **Dimensions**: Number of indicators/columns

**Example**: 5 years of monthly data with 10+ indicators → Good coverage

### 5. **Trust Score** (10% weight)
- **Trusted Sources**: statistica.md, World Bank, IMF, NBM, gov.md
- **Metadata Quality**: Complete source, date, description
- **Verification**: Official government sources

**Example**: Data from "National Bureau of Statistics Moldova" → 0.9/1.0

## Decision Matrix

| Overall Score | Recommendation | Action |
|--------------|----------------|--------|
| ≥ 0.75 | **ACCEPT** | Add to core knowledge base immediately |
| 0.60 - 0.74 | **ACCEPT_WITH_REVIEW** | Add after manual verification |
| 0.45 - 0.59 | **CONDITIONAL** | Keep for user only, don't add to core |
| < 0.45 | **REJECT** | Don't add anywhere |

## API Integration

### Upload Endpoint

```
POST /dataset/upload
```

**Parameters**:
- `file`: CSV or Excel file
- `name`: Dataset name (required)
- `description`: What the data contains
- `source`: Where it came from
- `add_to_core`: 'auto' (default), 'yes', or 'no'

**Response**:
```json
{
  "success": true,
  "dataset_name": "moldova_trade_2024",
  "evaluation": {
    "recommendation": "ACCEPT",
    "overall_score": 0.83,
    "scores": {
      "quality": 1.0,
      "relevance": 0.75,
      "novelty": 1.0,
      "coverage": 0.39,
      "trust": 0.93
    },
    "action": "Add to core knowledge base",
    "reason": "High-quality, relevant dataset that enriches existing knowledge",
    "added_to_core": true
  },
  "report": "Full detailed report..."
}
```

## Usage Examples

### Example 1: Auto-Accept High-Quality Data

Upload official Moldova statistics:
```python
files = {'file': open('moldova_exports_2024.csv', 'rb')}
data = {
    'name': 'Moldova Trade 2024',
    'description': 'Official export data',
    'source': 'statistica.md',
    'add_to_core': 'auto'  # Let curator decide
}
response = requests.post('http://localhost:5000/dataset/upload', 
                        files=files, data=data)
```

**Result**: Automatically added to core (score: 0.85)

### Example 2: Reject Low-Quality Data

Upload random sales data:
```python
# Irrelevant dataset (no Moldova, USA data)
# Result: CONDITIONAL or REJECT
# Action: Kept for user only, not added to core
```

### Example 3: Manual Override

Force add regardless of score:
```python
data = {
    'name': 'Special Dataset',
    'add_to_core': 'yes'  # Force add
}
```

## Benefits

1. **Quality Protection**: Core knowledge base stays clean
2. **Automatic Filtering**: No manual review for obvious cases
3. **Smart Decisions**: Multi-dimensional evaluation (not just one metric)
4. **User Feedback**: Detailed reports explain why datasets were accepted/rejected
5. **Enrichment**: Only valuable data improves the LLM

## Architecture

```
User Upload → Curator Agent → Evaluation
                    ↓
            ┌───────┴───────┐
            ↓               ↓
       ACCEPT          REJECT/CONDITIONAL
            ↓               ↓
    Core Knowledge    User-Only Storage
```

## Testing

Run the test suite:
```bash
python test_curator_agent.py
```

See examples of:
- ✅ High-quality Moldova dataset (ACCEPT)
- ❌ Low-quality irrelevant dataset (CONDITIONAL)
- ⚠️ Moderate dataset (ACCEPT_WITH_REVIEW)

## Future Enhancements

1. **Learning from Usage**: Track which datasets users query most
2. **Temporal Decay**: Reduce scores for outdated data
3. **Cross-Dataset Validation**: Check consistency with existing data
4. **Source Reputation**: Build trust scores based on historical accuracy
5. **User Feedback Loop**: Let users rate dataset usefulness

## Configuration

Adjust weights in `curator_agent.py`:
```python
weights = {
    'quality': 0.25,
    'relevance': 0.30,  # Highest priority
    'novelty': 0.20,
    'coverage': 0.15,
    'trust': 0.10
}
```

Modify thresholds:
```python
if overall_score >= 0.75:  # ACCEPT threshold
    recommendation = "ACCEPT"
```

## Key Takeaways

- 🎯 **Relevance is king**: Moldova economics focus gets 30% weight
- 📊 **Quality matters**: Complete, consistent data scores higher
- ✨ **Novelty counts**: New data is more valuable than duplicates
- 🔒 **Trust protects**: Official sources get priority
- 🤖 **Automatic decisions**: 75%+ score = instant accept
