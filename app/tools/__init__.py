"""Tool implementations for the agent"""
from .search import search_dataset
from .web import web_search
from .calculate import calculate
from .analyze import analyze_column
from .learn import add_learned_info

__all__ = [
    'search_dataset',
    'web_search', 
    'calculate',
    'analyze_column',
    'add_learned_info'
]

# Tool definitions for Ollama
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_dataset",
            "description": "Search both dataset AND all previously learned information (web searches, insights, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
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
            "description": "Search the web - results are automatically saved to knowledge base",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
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
            "description": "Perform safe mathematical calculations",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate"
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
    }
]
