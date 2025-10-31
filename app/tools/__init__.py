"""Tool implementations for the agent"""
from .search import search_dataset
from .web import web_search, search_official_sources
from .calculate import calculate
from .analyze import analyze_column
from .learn import add_learned_info
from .verify import verify_with_sources, list_datasets, get_source_trust_score
from .forecast import forecast_economic_indicator, forecast_trade_balance

__all__ = [
    'search_dataset',
    'web_search',
    'search_official_sources',
    'calculate',
    'analyze_column',
    'add_learned_info',
    'verify_with_sources',
    'list_datasets',
    'get_source_trust_score',
    'forecast_economic_indicator',
    'forecast_trade_balance'
]

# Tool definitions for Ollama
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_dataset",
            "description": "PRIORITY 1: ALWAYS USE THIS FIRST. Search dataset AND all previously learned information (web searches, insights, etc.). For Moldova economics questions, always try this before any other tool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query (automatically assumes Moldova context)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_official_sources",
            "description": "PRIORITY 2: Use AFTER search_dataset. Search ONLY official Moldova sources: statistica.md (National Statistics), World Bank Moldova, IMF Moldova, UN Comtrade, National Bank of Moldova. Use this for authoritative Moldova economic data before using web_search.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for Moldova official economic data (Moldova context automatically assumed)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "PRIORITY 3: FALLBACK ONLY. General web search - use ONLY if search_dataset and search_official_sources did not find the answer. Automatically adds Moldova context to economic queries. Results saved to knowledge base.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query (Moldova context auto-added for economic terms)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Perform safe mathematical calculations ONLY (e.g., '2+2', '100*0.05'). NOT for forecasting! Use forecast_economic_indicator() for predictions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate (e.g., '2+2', '100*1.05'). ONLY math, not indicator names!"
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_column",
            "description": "Get statistical analysis of a dataset column",
            "parameters": {
                "type": "object",
                "properties": {
                    "column": {
                        "type": "string",
                        "description": "Column name to analyze"
                    },
                    "analysis_type": {
                        "type": "string",
                        "enum": ["summary", "distribution", "correlation"],
                        "description": "Type of analysis"
                    }
                },
                "required": ["column"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_learned_info",
            "description": "Save important information for future reference",
            "parameters": {
                "type": "object",
                "properties": {
                    "information": {
                        "type": "string",
                        "description": "The information to save"
                    },
                    "category": {
                        "type": "string",
                        "description": "Category (e.g., 'insight', 'fact')"
                    }
                },
                "required": ["information"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_official_sources",
            "description": "Search ONLY official high-trust sources: statistica.md, World Bank, IMF, UN Comtrade, National Bank of Moldova. Use this for authoritative economic data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for official economic data"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "verify_with_sources",
            "description": "Cross-check a data claim against official sources (World Bank, IMF, National Statistics) to verify accuracy and provide confidence score.",
            "parameters": {
                "type": "object",
                "properties": {
                    "claim": {
                        "type": "string",
                        "description": "The data claim or fact to verify (e.g., 'Moldova GDP 2023 was $15.5B')"
                    },
                    "current_value": {
                        "type": "string",
                        "description": "Optional current value to compare against"
                    }
                },
                "required": ["claim"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_datasets",
            "description": "List all available datasets with descriptions, including user-uploaded and system datasets.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_source_trust_score",
            "description": "Get the trust/reliability score (0-1) for a data source with explanation of its credibility level.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_name": {
                        "type": "string",
                        "description": "Name of the data source (e.g., 'statistica.md', 'World Bank', 'tradingeconomics.com')"
                    }
                },
                "required": ["source_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "forecast_economic_indicator",
            "description": "Forecast future values of economic indicators using statistical models (linear trend, growth rate, exponential smoothing, ensemble). Use this to predict GDP, exports, imports, inflation rate, trade values, or any numeric indicator. IMPORTANT: Call this AFTER searching for historical data with search_dataset() and search_official_sources().",
            "parameters": {
                "type": "object",
                "properties": {
                    "indicator": {
                        "type": "string",
                        "description": "Name of the indicator to forecast. Use exact column names like 'Value', 'GDP', 'exports', 'imports', or economic terms like 'inflation_rate', 'trade_balance'"
                    },
                    "time_periods": {
                        "type": "integer",
                        "description": "Number of periods ahead to forecast (default: 12). For 'next year' use 12 months, for '6 months' use 6."
                    },
                    "method": {
                        "type": "string",
                        "description": "Forecasting method: 'ensemble' (RECOMMENDED - combines all models), 'trend' (linear), 'growth' (CAGR), 'smooth' (exponential), 'moving_average'",
                        "enum": ["ensemble", "trend", "growth", "smooth", "moving_average"]
                    }
                },
                "required": ["indicator"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "forecast_trade_balance",
            "description": "Forecast Moldova's trade balance (exports - imports) for future periods. Predicts whether Moldova will have trade surplus or deficit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "export_indicator": {
                        "type": "string",
                        "description": "Column name for export values (default: 'Value')"
                    },
                    "import_indicator": {
                        "type": "string",
                        "description": "Column name for import values (default: 'Value')"
                    },
                    "periods_ahead": {
                        "type": "integer",
                        "description": "Number of periods to forecast (default: 6)"
                    }
                },
                "required": []
            }
        }
    }
]
