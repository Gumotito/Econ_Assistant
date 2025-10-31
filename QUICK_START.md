# Quick Start Guide - New Features

## 🚀 How to Run

```bash
# Start the server
cd d:\Python_Projects\Econ_Assistant
python run.py
```

Server starts on `http://localhost:5000`

---

## 🧪 Testing

### Quick Import Test
```bash
python test_imports.py
```

### Comprehensive Feature Test
```bash
# Terminal 1: Start server
python run.py

# Terminal 2: Run tests
python test_features.py
```

---

## 📊 New API Endpoints

### Analytics Summary
```bash
curl http://localhost:5000/api/analytics/summary
```

Returns:
- Performance metrics (avg time, success rate)
- Tool usage stats
- Popular queries
- Data gaps

### Recent Queries
```bash
curl http://localhost:5000/api/analytics/recent?limit=10
```

Returns last 10 queries with details.

---

## 💡 New Features in Action

### 1. Guardrails (Security)

**What it does:** Validates all inputs/outputs for safety

**Try this:**
```bash
# Normal query - passes
curl -X POST http://localhost:5000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Moldova GDP?"}'

# Empty query - blocked
curl -X POST http://localhost:5000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{"question": ""}'
```

### 2. TTL Caching (Performance)

**What it does:** Caches web searches for 15 minutes

**Try this:**
```bash
# Ask same question twice - second is much faster
curl -X POST http://localhost:5000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Moldova GDP in 2025?"}'
  
# Wait 1 second, ask again
curl -X POST http://localhost:5000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Moldova GDP in 2025?"}'
```

### 3. Engagement (Follow-ups)

**What it does:** Suggests related questions

**Try this:**
```bash
curl -X POST http://localhost:5000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Which country exports most to Moldova?"}'
```

Response now includes:
```json
{
  "answer": "...",
  "followup": "What products dominate imports from Romania?"
}
```

### 4. Analytics (Logging)

**What it does:** Tracks all queries and tool usage

**Check logs:**
```bash
# View query log
cat logs/query_analytics.jsonl

# View tool usage log
cat logs/tool_usage.jsonl

# Tail in real-time
tail -f logs/query_analytics.jsonl
```

---

## 🎨 Frontend Changes

Open `http://localhost:5000` in browser:

**New UI elements:**
- 💡 Orange follow-up suggestion box (clickable)
- Appears after every answer
- Click to auto-fill and re-ask

---

## ⚙️ Configuration

### Rate Limiting

Edit `app/services/guardrails.py`:
```python
guardrails = Guardrails(
    rate_limit_requests=50,  # Requests per window
    rate_limit_window=60     # Window in seconds
)
```

### Cache TTL

Edit `app/tools/web.py`:
```python
@ttl_cache(ttl_seconds=900, maxsize=256)  # 15 min, 256 entries
def web_search(query: str) -> str:
```

### Disable Features

Comment out in `app/routes/api_routes.py`:
```python
# Disable guardrails
# is_valid, error = guardrails.validate_input(question, user_id)

# Disable engagement
# followup = suggest_followup(question, validated_answer)

# Disable analytics
# analytics.log_query(...)
```

---

## 📁 File Locations

```
Econ_Assistant/
├── app/
│   ├── services/
│   │   ├── guardrails.py       ← Security validation
│   │   └── analytics.py        ← Usage tracking
│   ├── tools/
│   │   ├── engagement.py       ← Follow-up generation
│   │   └── web.py              ← TTL cached search
│   └── routes/
│       └── api_routes.py       ← Integration point
├── logs/                       ← Auto-created
│   ├── query_analytics.jsonl
│   └── tool_usage.jsonl
└── test_features.py            ← Comprehensive tests
```

---

## 🐛 Troubleshooting

### "Cannot connect to server"
```bash
# Check if running
curl http://localhost:5000

# Restart server
python run.py
```

### "Import error"
```bash
# Verify imports
python test_imports.py

# Check Python version (need 3.8+)
python --version
```

### "No logs directory"
```bash
# Logs created automatically on first query
# Force create:
mkdir logs
```

### "Guardrails blocking legitimate queries"
```bash
# Check logs
cat logs/query_analytics.jsonl | grep "error"

# Adjust limits in guardrails.py
```

---

## 📈 Monitoring

### Check System Health
```bash
curl http://localhost:5000/api/analytics/summary | python -m json.tool
```

Look for:
- `success_rate` > 95%
- `avg_query_time` < 2.0s
- `total_queries` increasing

### Check Cache Performance
```bash
# Ask same question 3 times
for i in {1..3}; do
  time curl -X POST http://localhost:5000/api/agent/query \
    -H "Content-Type: application/json" \
    -d '{"question": "Moldova GDP?"}'
done
```

First call: ~2s  
Subsequent: <0.2s

---

## 🎯 Next Steps

1. **Test thoroughly** - Run `test_features.py`
2. **Monitor logs** - Check `logs/` directory
3. **Adjust settings** - Rate limits, cache TTL
4. **Expand data** - Add Moldova datasets (Week 2)
5. **Multilingual** - Romanian/Russian (Week 3)

---

## 📚 Documentation

- **Implementation details:** `IMPLEMENTATION_COMPLETE.md`
- **Deep analysis:** `DEEP_ANALYSIS_ECON_VS_AI.md`
- **Strategy:** `MOLDOVA_ECONOMICS_STRATEGY.md`

---

## ✅ Quick Checklist

Before deploying:

- [ ] Run `python test_imports.py` - all pass
- [ ] Run `python test_features.py` - all pass
- [ ] Check `GET /api/analytics/summary` - returns data
- [ ] Test rate limiting - blocked after 50 requests
- [ ] Test caching - second query much faster
- [ ] Test follow-ups - appear in UI
- [ ] Check logs - `query_analytics.jsonl` populated

**All green? You're ready! 🚀**
