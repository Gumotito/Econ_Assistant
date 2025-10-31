# DataAgent Quick Start Guide

## 🚀 Starting the Application

```powershell
cd d:\Python_Projects\Econ_Assistant
python run.py
```

Then open: http://localhost:5000

---

## 📤 Uploading Datasets

### Via Web UI

1. Navigate to "Upload Dataset" section
2. Click "Choose File" and select CSV or Excel file
3. Enter dataset name (required)
4. Enter description (optional)
5. Select trust score:
   - **High Trust (0.9)** - Verified internal data
   - **Medium-High (0.8)** - Reliable third-party
   - **Medium (0.7)** - Default for user uploads
   - **Lower (0.6)** - Unverified data
6. Click "Upload Dataset"

### Supported Formats

- CSV (.csv)
- Excel (.xlsx, .xls)

### Example Datasets for Moldova

- `Moldova_GDP_Historical.csv` - GDP from National Statistics
- `Moldova_Trade_2024.xlsx` - UN Comtrade export data
- `BNM_Exchange_Rates.csv` - National Bank exchange rates
- `Population_Census.xlsx` - Demographics data

---

## 🔍 Using New Tools

### 1. Search Official Sources Only

Ask the agent:
```
"Search official sources for Moldova GDP 2023"
```

The agent will use `search_official_sources()` tool which searches:
- statistica.md
- data.worldbank.org
- imf.org
- comtrade.un.org
- bnm.md

Results are saved with **trust_score = 1.0** (highest)

### 2. Verify Data Claims

Ask the agent:
```
"Verify: Moldova's GDP in 2023 was $15.5 billion"
```

The agent will:
1. Search official sources
2. Cross-check the claim
3. Calculate confidence score (0-100%)
4. Provide recommendation

Example response:
```
✓ VERIFIED with HIGH confidence (95%)

Evidence from official sources:
- World Bank: $15.5B
- statistica.md: 15.5 miliarde USD
- IMF: Matches reported figure

Recommendation: Data is highly reliable. Can be used in reports.
```

### 3. List Available Datasets

Ask the agent:
```
"Show me all available datasets"
```

Or click "View Datasets" button in Upload section.

Returns:
- Dataset name
- Description
- Trust score
- Document count

### 4. Check Source Trust Score

Ask the agent:
```
"What is the trust score for tradingeconomics.com?"
```

Returns:
- Trust score (0-1)
- Category (HIGHEST/HIGH/MEDIUM/LOWER)
- Description of reliability

---

## 💡 Query Examples

### Basic Dataset Queries

```
"What's the average tariff rate?"
"Show me imports from Germany"
"Calculate total export value"
```

### Official Source Queries

```
"Search official sources for Moldova inflation rate 2024"
"What does World Bank say about Moldova's economy?"
"Get latest GDP data from National Statistics"
```

### Verification Queries

```
"Verify: Moldova population is 2.6 million"
"Cross-check Moldova's GDP growth rate"
"Is this data accurate: Moldova exports 40% to EU?"
```

### Combined Queries

```
"Upload my Moldova trade data and compare with World Bank figures"
"Search official sources and verify against my dataset"
"What's the most reliable source for Moldova economic data?"
```

---

## 📊 Understanding Trust Scores

### Trust Score Levels

| Score | Category | Sources | Usage |
|-------|----------|---------|-------|
| 1.0 | HIGHEST | statistica.md, World Bank, IMF, UN Comtrade, BNM | Official government/international org data |
| 0.85 | HIGH | Eurostat, OECD | Verified international databases |
| 0.8 | HIGH | TradingEconomics, CEIC | Reputable data aggregators |
| 0.7 | MEDIUM | User uploads | Your own datasets |
| 0.6 | LOWER | General web | DuckDuckGo search results |

### Trust Badges in UI

- **✓ Official** - Trust score ≥ 0.9 (green)
- **⚠ Medium** - Trust score 0.8-0.89 (orange)
- **• User** - Trust score < 0.8 (gray)

### How Trust Affects Search

When you search, results are **weighted by trust score**:

1. High-trust sources rank higher
2. Low-trust sources rank lower
3. You can filter by minimum trust:
   ```
   "Search with trust score above 0.8"
   ```

**Example:**
```
Query: "Moldova GDP"

Without trust weighting:
1. Blog post about Moldova (high semantic match, trust=0.6)
2. World Bank data (medium match, trust=1.0)

With trust weighting:
1. World Bank data (weighted higher due to trust=1.0)
2. Blog post (weighted lower due to trust=0.6)
```

---

## 🔧 Advanced Features

### Upload Large Datasets

For datasets > 10MB:
1. Split into smaller files (< 10MB each)
2. Upload separately with numbered names:
   - `Moldova_Trade_Part1.csv`
   - `Moldova_Trade_Part2.csv`

### Bulk Upload (via Python)

```python
from app.agents import get_data_agent
from app.services.vector_db import VectorDBService

db_service = VectorDBService()
db_service.initialize()
agent = get_data_agent(db_service)

# Upload multiple files
files = [
    'Moldova_GDP.csv',
    'Moldova_Trade.xlsx',
    'Moldova_Population.csv'
]

for file in files:
    result = agent.upload_dataset(
        file_path=file,
        name=file.replace('.csv', '').replace('.xlsx', ''),
        description=f"Official data from {file}",
        trust_score=0.9  # High trust
    )
    print(result)
```

### Update Trust Score

After verifying data quality:
```python
agent.update_source_trust('My Dataset', new_trust_score=0.85)
```

### Delete Dataset

```python
agent.delete_dataset('Old Dataset Name')
```

Or via API:
```bash
curl -X DELETE http://localhost:5000/api/dataset/Old_Dataset_Name
```

---

## 🐛 Troubleshooting

### Upload Fails

**Error:** "Only CSV and Excel files supported"
- **Fix:** Ensure file has .csv, .xlsx, or .xls extension

**Error:** "Dataset name required"
- **Fix:** Enter a name in the "Dataset name" field

**Error:** "Failed to read file"
- **Fix:** Check file format (must be valid CSV/Excel)
- **Fix:** Try opening file in Excel first to verify

### Search Returns No Results

**Issue:** Official source search returns nothing
- **Cause:** Network issue or source unavailable
- **Fix:** Try regular `web_search` instead
- **Fix:** Check internet connection

### Verification Confidence Low

**Issue:** "Confidence: 30% - UNCERTAIN"
- **Cause:** Conflicting data from different sources
- **Action:** Review each source manually
- **Action:** Search more official sources

### Trust Score Not Applying

**Issue:** Results don't seem weighted by trust
- **Cause:** No trust_score metadata on old documents
- **Fix:** Re-upload datasets after this update
- **Fix:** Web search results saved before update won't have scores

---

## 📝 Best Practices

### 1. Naming Datasets

Good names:
- `Moldova_GDP_2020-2024`
- `Trade_Balance_Monthly_2024`
- `NBM_Exchange_Rates_Historical`

Bad names:
- `data.csv`
- `file123.xlsx`
- `untitled`

### 2. Adding Descriptions

Good descriptions:
- "GDP data from National Bureau of Statistics, annual 2000-2024"
- "Monthly trade balance from UN Comtrade, Moldova exports/imports"
- "Exchange rates from National Bank of Moldova, daily USD/MDL"

Bad descriptions:
- "data"
- (empty)
- "some numbers"

### 3. Setting Trust Scores

- **0.9** - Official government source, verified accuracy
- **0.8** - Reputable third-party, cross-checked
- **0.7** - Internal/user data, not independently verified
- **0.6** - Experimental/preliminary data

### 4. Verification Workflow

For important claims:
1. Search official sources first
2. Upload your own data
3. Ask agent to verify the claim
4. Review confidence score
5. Check source details
6. If confidence < 80%, investigate further

---

## 🎓 Tutorial: Complete Workflow

### Scenario: Verify Moldova's 2024 Trade Balance

#### Step 1: Upload Your Data
```
1. Prepare file: Moldova_Trade_2024.csv
2. Upload via UI:
   - Name: "Moldova Trade 2024"
   - Description: "Trade data from company database"
   - Trust: Medium (0.7)
3. Click Upload
```

#### Step 2: Search Official Sources
```
Ask: "Search official sources for Moldova trade balance 2024"

Agent searches:
- UN Comtrade
- National Statistics
- World Bank

Results saved with trust=1.0
```

#### Step 3: Verify Your Data
```
Ask: "Verify: Moldova trade deficit was $2.5B in 2024"

Agent response:
✓ VERIFIED with MEDIUM confidence (75%)
- UN Comtrade: -$2.4B
- Your dataset: -$2.5B
- Difference: $0.1B (4%)

Recommendation: Data is reasonably accurate. 
Small discrepancy may be due to different methodology.
```

#### Step 4: Deep Analysis
```
Ask: "Compare my trade data with official sources. 
What are the main differences?"

Agent will:
1. Search both your dataset and official sources
2. Calculate differences by country/product
3. Identify discrepancies
4. Suggest reasons
```

#### Step 5: Generate Report
```
Ask: "Create a summary of Moldova's 2024 trade balance 
using highest trust sources only"

Agent will:
1. Filter for trust >= 0.9
2. Use only official sources
3. Generate summary with citations
```

---

## 📈 Measuring Success

### Metrics to Track

1. **Upload Count** - How many datasets uploaded
2. **Verification Usage** - How often verify tool used
3. **Trust Distribution** - Percentage of high/medium/low trust data
4. **Query Accuracy** - User feedback on answer quality

### Expected Improvements

With DataAgent features:
- **Accuracy**: +30% (more official sources)
- **User Trust**: +40% (transparency via trust scores)
- **Coverage**: +50% (user datasets fill gaps)
- **Engagement**: +25% (more interactive features)

---

## 🔗 Related Documentation

- **DATAAGENT_IMPLEMENTATION_COMPLETE.md** - Technical implementation details
- **DEEP_ANALYSIS_ECON_VS_AI.md** - Feature comparison analysis
- **MOLDOVA_ECONOMICS_STRATEGY.md** - Moldova-specific strategy
- **IMPLEMENTATION_COMPLETE.md** - Previous features (guardrails, caching, etc.)

---

## 🆘 Getting Help

### Check Logs

```powershell
# View application logs
cat d:\Python_Projects\Econ_Assistant\logs\app.log

# View analytics
cat d:\Python_Projects\Econ_Assistant\logs\query_analytics.jsonl
cat d:\Python_Projects\Econ_Assistant\logs\tool_usage.jsonl
```

### Run Tests

```powershell
cd d:\Python_Projects\Econ_Assistant
python test_data_agent.py
```

### Check Database Stats

Ask the agent:
```
"Show database statistics"
```

Or use API:
```bash
curl http://localhost:5000/api/dataset/info
```

---

**Ready to Use! Start uploading datasets and verifying data! 🚀**
