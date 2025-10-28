from flask import Flask, render_template, jsonify, request
import os
from dotenv import load_dotenv
import pandas as pd
import json
from typing import List, Dict, Any
import chromadb
from chromadb.utils import embedding_functions
import requests
from functools import wraps, lru_cache
# Add Flask-Limiter
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
from logging.handlers import RotatingFileHandler

load_dotenv()

# LangSmith setup
try:
    # Set environment variables explicitly
    os.environ['LANGCHAIN_TRACING_V2'] = os.getenv('LANGCHAIN_TRACING_V2', 'true')
    os.environ['LANGCHAIN_API_KEY'] = os.getenv('LANGCHAIN_API_KEY', '')
    os.environ['LANGCHAIN_PROJECT'] = os.getenv('LANGCHAIN_PROJECT', 'econ-assistant')
    
    from langsmith import traceable, Client
    
    langsmith_client = Client(
        api_key=os.getenv('LANGCHAIN_API_KEY')
    )
    USE_LANGSMITH = True
    print("✓ LangSmith enabled for tracing")
except Exception as e:
    USE_LANGSMITH = False
    print(f"⚠ LangSmith not available: {e}")
    # Define a no-op decorator when LangSmith is disabled
    def traceable(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

app = Flask(__name__)

# Configuration
class Config:
    """Application configuration"""
    DATA_DIR = os.getenv('DATA_DIR', 'data')
    INITIAL_CSV = os.getenv('INITIAL_CSV', 'test_moldova_imports_2025.csv')
    CHROMA_PERSIST_DIR = os.getenv('CHROMA_PERSIST_DIR', 'chroma_db')
    MAX_QUERY_LENGTH = int(os.getenv('MAX_QUERY_LENGTH', 5000))
    MAX_ITERATIONS = int(os.getenv('MAX_ITERATIONS', 3))
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'mistral')
    
app.config.from_object(Config)

# Initialize Limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Global storage
current_dataset = None
dataset_info = {}
chroma_client = None
collection = None

# Initialize ChromaDB for RAG with persistence
def init_vector_db():
    global chroma_client, collection
    
    # Create persistent client
    chroma_client = chromadb.PersistentClient(path=app.config['CHROMA_PERSIST_DIR'])
    
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    collection = chroma_client.get_or_create_collection(
        name="dataset_knowledge",
        embedding_function=embedding_fn
    )
    
    print(f"✓ Vector DB initialized with {collection.count()} documents")

# Test Ollama connection
def test_ollama():
    try:
        import ollama
        models = ollama.list()
        if models and 'models' in models:
            model_names = [m.get('name', 'unknown') for m in models.get('models', [])]
            print(f"✓ Ollama connected. Available models: {model_names}")
        else:
            print(f"✓ Ollama connected. Models: {models}")
        return True
    except Exception as e:
        print(f"✗ Ollama error: {e}")
        import traceback
        traceback.print_exc()
        return False

# LLM Client with LangSmith tracing
@traceable(name="ollama_chat", run_type="llm")
def query_llm_with_tools(messages: List[Dict], tools: List[Dict] = None, model="mistral"):
    """Query Ollama with tool calling capability"""
    try:
        import ollama
        
        response = ollama.chat(
            model=model,
            messages=messages,
            tools=tools or [],
            stream=False
        )
        
        # Convert response to dict if it's an object
        if hasattr(response, '__dict__'):
            response_dict = {
                'model': response.model,
                'created_at': response.created_at,
                'message': {
                    'role': response.message.role,
                    'content': response.message.content,
                    'tool_calls': response.message.tool_calls
                },
                'done': response.done
            }
            return response_dict
        
        return response
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        return {"error": str(e)}

# Tools Definition
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_dataset",
            "description": "Search through the loaded dataset for specific information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find in the dataset"
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
            "description": "Search the web for current information not in the dataset. Results are automatically added to knowledge base.",
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
            "description": "Perform mathematical calculations",
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
            "description": "Get statistical analysis of a specific column",
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
                        "description": "Type of analysis to perform"
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
            "description": "Save important information or insights to the knowledge base for future reference",
            "parameters": {
                "type": "object",
                "properties": {
                    "information": {
                        "type": "string",
                        "description": "The information or insight to save"
                    },
                    "category": {
                        "type": "string",
                        "description": "Category of information (e.g., 'insight', 'definition', 'fact')"
                    }
                },
                "required": ["information"]
            }
        }
    }
]

# Tool Implementations with tracing
@traceable(name="search_dataset", run_type="tool")
def search_dataset(query: str) -> str:
    """Search dataset and knowledge base using RAG"""
    if collection is None:
        return "Dataset not indexed yet"
    
    results = collection.query(
        query_texts=[query],
        n_results=5
    )
    
    if results['documents'] and results['documents'][0]:
        # Get metadata to show sources
        docs = results['documents'][0]
        metas = results['metadatas'][0] if results['metadatas'] else [{}] * len(docs)
        
        formatted_results = []
        for doc, meta in zip(docs, metas):
            source = meta.get('source', 'dataset')
            if source == 'web_search':
                formatted_results.append(f"[From web search] {doc}")
            elif source == 'learned':
                formatted_results.append(f"[Learned info] {doc}")
            else:
                formatted_results.append(f"[Dataset] {doc[:200]}")
        
        context = "\n\n".join(formatted_results)
        return f"Found relevant information:\n\n{context}"
    return "No matching information found"

@traceable(name="web_search", run_type="tool")
def web_search(query: str) -> str:
    """Search web using DuckDuckGo and add results to knowledge base"""
    try:
        url = f"https://api.duckduckgo.com/?q={query}&format=json"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        result_text = ""
        if data.get('AbstractText'):
            result_text = data['AbstractText']
        elif data.get('RelatedTopics'):
            results = []
            for topic in data['RelatedTopics'][:3]:
                if isinstance(topic, dict) and 'Text' in topic:
                    results.append(topic['Text'])
            result_text = "\n".join(results) if results else "No results found"
        else:
            result_text = "No results found"
        
        # Add to knowledge base if we got meaningful results
        if result_text and result_text != "No results found":
            add_knowledge(
                content=f"Query: {query}\nAnswer: {result_text}",
                source="web_search",
                metadata={"query": query}
            )
        
        return result_text
    except Exception as e:
        return f"Search error: {str(e)}"

@traceable(name="calculate", run_type="tool")
def calculate(expression: str) -> str:
    """Safe calculation using ast.literal_eval"""
    import ast
    import operator as op
    
    # Supported operations
    ops = {
        ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
        ast.Div: op.truediv, ast.Pow: op.pow, ast.Mod: op.mod,
        ast.USub: op.neg
    }
    
    def eval_expr(node):
        if isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.BinOp):
            return ops[type(node.op)](eval_expr(node.left), eval_expr(node.right))
        elif isinstance(node, ast.UnaryOp):
            return ops[type(node.op)](eval_expr(node.operand))
        else:
            raise ValueError(f"Unsupported operation: {type(node)}")
    
    try:
        return str(eval_expr(ast.parse(expression, mode='eval').body))
    except Exception as e:
        return f"Calculation error: {str(e)}"

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

@traceable(name="add_learned_info", run_type="tool")
def add_learned_info(information: str, category: str = "insight") -> str:
    """Save learned information to knowledge base"""
    success = add_knowledge(
        content=information,
        source="learned",
        metadata={"category": category}
    )
    
    if success:
        return f"Successfully saved {category}: {information[:50]}..."
    return "Failed to save information"

def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Execute the requested tool"""
    tools_map = {
        "search_dataset": search_dataset,
        "web_search": web_search,
        "calculate": calculate,
        "analyze_column": analyze_column,
        "add_learned_info": add_learned_info
    }
    
    if tool_name in tools_map:
        return tools_map[tool_name](**arguments)
    return f"Unknown tool: {tool_name}"

# Use vectorized operations
def analyze_dataset(df, clear_existing=False):
    """Generate dataset analysis and index for RAG"""
    info = {
        'rows': len(df),
        'columns': list(df.columns),
        'dtypes': {k: str(v) for k, v in df.dtypes.to_dict().items()},
        'missing': {k: int(v) for k, v in df.isnull().sum().to_dict().items()},
        'summary': df.describe().to_dict()
    }
    
    # Index dataset for RAG
    if collection is not None:
        try:
            if clear_existing:
                # Clear only dataset rows, keep learned knowledge
                existing_ids = collection.get()['ids']
                dataset_ids = [id for id in existing_ids if id.startswith('row_')]
                if dataset_ids:
                    collection.delete(ids=dataset_ids)
                    print(f"✓ Cleared {len(dataset_ids)} old dataset rows")
        except:
            pass
        
        documents = []
        metadatas = []
        ids = []
        
        # Vectorized string concatenation
        for idx in range(len(df)):
            row = df.iloc[idx]
            doc = " | ".join([f"{col}: {row[col]}" for col in df.columns])
            documents.append(doc)
            metadatas.append({"row_id": idx, "source": "dataset"})
            ids.append(f"row_{idx}")
        
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i+batch_size]
            batch_meta = metadatas[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            
            collection.add(
                documents=batch_docs,
                metadatas=batch_meta,
                ids=batch_ids
            )
        print(f"✓ Indexed {len(documents)} dataset rows")
    
    return info

def load_initial_dataset():
    """Load initial dataset on startup"""
    global current_dataset, dataset_info
    
    csv_path = app.config['INITIAL_CSV']
    if not os.path.exists(csv_path):
        print(f"⚠ Initial dataset not found: {csv_path}")
        return False
    
    try:
        current_dataset = pd.read_csv(csv_path)
        dataset_info = analyze_dataset(current_dataset, clear_existing=False)
        print(f"✓ Loaded initial dataset: {csv_path}")
        print(f"  {dataset_info['rows']} rows, {len(dataset_info['columns'])} columns")
        return True
    except Exception as e:
        print(f"✗ Failed to load initial dataset: {e}")
        return False

def add_knowledge(content: str, source: str = "web_search", metadata: Dict = None):
    """Add new knowledge to the vector database"""
    if collection is None:
        return False
    
    try:
        import hashlib
        # Generate unique ID based on content
        content_hash = hashlib.md5(content.encode()).hexdigest()
        doc_id = f"{source}_{content_hash[:16]}"
        
        # Check if already exists
        existing = collection.get(ids=[doc_id])
        if existing['ids']:
            print(f"ℹ Knowledge already exists: {doc_id}")
            return True
        
        meta = metadata or {}
        meta.update({"source": source, "added_at": str(pd.Timestamp.now())})
        
        collection.add(
            documents=[content],
            metadatas=[meta],
            ids=[doc_id]
        )
        
        print(f"✓ Added new knowledge: {doc_id[:30]}...")
        return True
    except Exception as e:
        print(f"✗ Failed to add knowledge: {e}")
        return False

# Add validation decorator
def validate_input(max_length=10000):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            data = request.get_json()
            if data:
                for key, value in data.items():
                    if isinstance(value, str) and len(value) > max_length:
                        return jsonify({'error': f'{key} exceeds maximum length'}), 400
            return func(*args, **kwargs)
        return wrapper
    return decorator

def validate_env_vars():
    """Validate required environment variables"""
    required = {
        'LANGCHAIN_API_KEY': 'LangSmith API key',
        'LANGCHAIN_PROJECT': 'LangSmith project name'
    }
    
    missing = []
    for var, description in required.items():
        if not os.getenv(var):
            missing.append(f"{var} ({description})")
    
    if missing:
        app.logger.warning(f"Missing env vars: {', '.join(missing)}")
        return False
    return True

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_dataset():
    """Upload and index dataset (replaces current dataset)"""
    global current_dataset, dataset_info
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        current_dataset = pd.read_csv(file)
        dataset_info = analyze_dataset(current_dataset, clear_existing=True)
        
        return jsonify({
            'success': True,
            'message': f'Dataset reloaded: {file.filename}',
            'info': dataset_info,
            'knowledge_base_size': collection.count() if collection else 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/agent/query', methods=['POST'])
@limiter.limit("20 per minute")
@validate_input(max_length=5000)
@traceable(name="agent_query", run_type="chain")
def agent_query():
    """Main agent endpoint with function calling"""
    if current_dataset is None:
        return jsonify({'error': 'No dataset loaded'}), 400
    
    data = request.json
    question = data.get('question', '')
    
    if not question:
        return jsonify({'error': 'Question required'}), 400
    
    try:
        system_msg = f"""You are a self-improving data analyst assistant with a persistent knowledge base.

Dataset Info:
- Rows: {dataset_info['rows']}
- Columns: {', '.join(dataset_info['columns'])}
- Knowledge Base: {collection.count() if collection else 0} total documents

Available Tools (use them in this priority):
1. search_dataset(query): ALWAYS TRY THIS FIRST - searches both dataset AND all previously learned information (web searches, insights, etc.)
2. analyze_column(column, analysis_type): Get statistics (analysis_type: "summary", "distribution", "correlation")
3. calculate(expression): Perform calculations
4. web_search(query): Search the web ONLY if search_dataset didn't find the answer - results are auto-saved
5. add_learned_info(information, category): Manually save insights for future reference

WORKFLOW:
1. For ANY question, first call search_dataset to check if we already know the answer
2. If not found, then use web_search or other tools
3. Provide a clear, direct answer based on tool results

Example Flow:
User: "What's Moldova's GDP?"
→ search_dataset(query="Moldova GDP") 
→ If found: Answer directly
→ If not found: web_search(query="Moldova GDP 2025") → Answer (auto-saved for next time)

The knowledge base remembers everything across sessions!"""

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": question}
        ]
        
        print(f"\n🔍 Question: {question}")
        response = query_llm_with_tools(messages, tools=TOOLS)
        print(f"📥 Response type: {type(response)}")
        print(f"📥 Response keys: {response.keys() if isinstance(response, dict) else 'N/A'}")
        
        tool_results = []
        max_iterations = 3
        
        for iteration in range(max_iterations):
            print(f"\n🔄 Iteration {iteration + 1}")
            
            if isinstance(response, dict):
                # Check for error
                if 'error' in response:
                    return jsonify({
                        'question': question,
                        'answer': f"Error: {response['error']}",
                        'tool_calls': tool_results
                    })
                
                # Get message
                message = response.get('message', {})
                print(f"💬 Message content: {message.get('content', 'None')[:200]}")
                print(f"🔧 Tool calls: {message.get('tool_calls', 'None')}")
                
                # Fallback: Parse tool calls from text if model doesn't use structured tool calling
                if not message.get('tool_calls') and message.get('content'):
                    content = message.get('content', '')
                    import re
                    
                    tools_executed = []
                    
                    # Look for web_search
                    web_match = re.search(r'web_search\s*\(\s*query\s*=\s*["\']([^"\']+)["\']\s*\)', content, re.IGNORECASE)
                    if web_match:
                        query = web_match.group(1)
                        print(f"🤖 Detected: web_search({query})")
                        result = web_search(query)
                        tools_executed.append({
                            'tool': 'web_search',
                            'arguments': {'query': query},
                            'result': result
                        })
                    
                    # Look for analyze_column
                    analyze_match = re.search(r'analyze_column\s*\(\s*column\s*=\s*["\']([^"\']+)["\']\s*(?:,\s*analysis_type\s*=\s*["\']([^"\']+)["\']\s*)?\)', content, re.IGNORECASE)
                    if analyze_match:
                        col = analyze_match.group(1)
                        analysis_type = analyze_match.group(2) or "summary"
                        print(f"🤖 Detected: analyze_column({col}, {analysis_type})")
                        result = analyze_column(col, analysis_type)
                        tools_executed.append({
                            'tool': 'analyze_column',
                            'arguments': {'column': col, 'analysis_type': analysis_type},
                            'result': result
                        })
                    
                    # Look for add_learned_info
                    learned_match = re.search(r'add_learned_info\s*\(\s*information\s*=\s*["\']([^"\']+)["\']\s*(?:,\s*category\s*=\s*["\']([^"\']+)["\']\s*)?\)', content, re.IGNORECASE)
                    if learned_match:
                        info = learned_match.group(1)
                        category = learned_match.group(2) or "insight"
                        print(f"🤖 Detected: add_learned_info({info[:30]}..., {category})")
                        result = add_learned_info(info, category)
                        tools_executed.append({
                            'tool': 'add_learned_info',
                            'arguments': {'information': info, 'category': category},
                            'result': result
                        })
                    
                    # Look for search_dataset
                    search_match = re.search(r'search_dataset\s*\(\s*query\s*=\s*["\']([^"\']+)["\']\s*\)', content, re.IGNORECASE)
                    if search_match:
                        query = search_match.group(1)
                        print(f"🤖 Detected: search_dataset({query})")
                        result = search_dataset(query)
                        tools_executed.append({
                            'tool': 'search_dataset',
                            'arguments': {'query': query},
                            'result': result
                        })
                    
                    # If we executed tools, add results and continue
                    if tools_executed:
                        tool_results.extend(tools_executed)
                        
                        # Build context with tool results
                        tool_context = "\n\n".join([
                            f"Tool: {t['tool']}\nArguments: {t['arguments']}\nResult: {t['result']}"
                            for t in tools_executed
                        ])
                        
                        messages.append({"role": "assistant", "content": content})
                        messages.append({
                            "role": "user",
                            "content": f"Tool results:\n{tool_context}\n\nBased on these results, provide a clear, concise answer to the original question. Just give the answer, don't mention the tools."
                        })
                        response = query_llm_with_tools(messages, tools=None)
                        continue
                
                # Check if done
                if message.get('content') and not message.get('tool_calls'):
                    return jsonify({
                        'question': question,
                        'answer': message['content'],
                        'tool_calls': tool_results
                    })
                
                # Execute tool calls
                if message.get('tool_calls'):
                    for tool_call in message['tool_calls']:
                        func = tool_call['function']
                        tool_name = func['name']
                        tool_args = json.loads(func['arguments']) if isinstance(func['arguments'], str) else func['arguments']
                        
                        print(f"🛠️  Calling {tool_name}({tool_args})")
                        result = execute_tool(tool_name, tool_args)
                        print(f"✅ Result: {result[:100]}...")
                        
                        tool_results.append({
                            'tool': tool_name,
                            'arguments': tool_args,
                            'result': result
                        })
                        
                        # Add assistant message first, then tool result
                        messages.append(message)
                        messages.append({
                            "role": "tool",
                            "content": result
                        })
                    
                    # After tool execution, ask for final answer WITHOUT tools
                    messages.append({
                        "role": "user", 
                        "content": "Based on the tool results above, provide a clear, concise answer to the original question. Do not call more tools."
                    })
                    response = query_llm_with_tools(messages, tools=None)  # No tools on follow-up
                else:
                    # No content and no tool calls
                    break
            else:
                return jsonify({
                    'question': question,
                    'answer': f"Unexpected response format: {str(response)}",
                    'tool_calls': tool_results
                })
        
        # If we have tool results but no final answer, generate one
        if tool_results and not any('answer' in str(tr) for tr in tool_results):
            # Create a simple answer from the first tool result
            first_result = tool_results[0]
            if first_result['tool'] == 'analyze_column':
                try:
                    stats = json.loads(first_result['result'])
                    answer = f"Based on the analysis, the average {first_result['arguments']['column']} is {stats.get('mean', 'N/A')}"
                    return jsonify({
                        'question': question,
                        'answer': answer,
                        'tool_calls': tool_results
                    })
                except:
                    pass
        
        return jsonify({
            'question': question,
            'answer': "Could not generate answer after maximum iterations",
            'tool_calls': tool_results
        })
        
    except Exception as e:
        print(f"❌ Error in agent_query: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'question': question,
            'answer': f"Error: {str(e)}",
            'tool_calls': []
        })

@app.route('/api/dataset/info', methods=['GET'])
def get_dataset_info():
    if current_dataset is None:
        return jsonify({'error': 'No dataset loaded'}), 400
    
    # Add knowledge base stats
    kb_info = {
        'total_documents': collection.count() if collection else 0,
    }
    
    # Count by source
    if collection and collection.count() > 0:
        all_docs = collection.get()
        sources = {}
        for meta in all_docs['metadatas']:
            source = meta.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
        kb_info['by_source'] = sources
    
    return jsonify({
        'dataset': dataset_info,
        'knowledge_base': kb_info
    })

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Quick analysis endpoint"""
    if current_dataset is None:
        return jsonify({'error': 'No dataset loaded'}), 400
    
    data = request.json
    analysis_type = data.get('type', 'summary')
    
    try:
        if analysis_type == 'summary':
            result = current_dataset.describe().to_dict()
        elif analysis_type == 'correlation':
            numeric_cols = current_dataset.select_dtypes(include=['number'])
            result = numeric_cols.corr().to_dict()
        elif analysis_type == 'distribution':
            result = {}
            for col in current_dataset.columns[:10]:  # First 10 columns
                result[col] = current_dataset[col].value_counts().head(5).to_dict()
        else:
            return jsonify({'error': 'Invalid analysis type'}), 400
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/filter', methods=['POST'])
def filter_data():
    """Filter dataset endpoint"""
    if current_dataset is None:
        return jsonify({'error': 'No dataset loaded'}), 400
    
    data = request.json
    column = data.get('column')
    operator = data.get('operator')
    value = data.get('value')
    
    if not column or not operator or value is None:
        return jsonify({'error': 'Missing filter parameters'}), 400
    
    try:
        if column not in current_dataset.columns:
            return jsonify({'error': f'Column {column} not found'}), 400
        
        # Convert value to appropriate type
        if current_dataset[column].dtype in ['int64', 'float64']:
            value = float(value)
        
        # Apply filter
        if operator == '==':
            filtered = current_dataset[current_dataset[column] == value]
        elif operator == '!=':
            filtered = current_dataset[current_dataset[column] != value]
        elif operator == '>':
            filtered = current_dataset[current_dataset[column] > value]
        elif operator == '<':
            filtered = current_dataset[current_dataset[column] < value]
        elif operator == '>=':
            filtered = current_dataset[current_dataset[column] >= value]
        elif operator == '<=':
            filtered = current_dataset[current_dataset[column] <= value]
        else:
            return jsonify({'error': 'Invalid operator'}), 400
        
        result = {
            'rows_before': len(current_dataset),
            'rows_after': len(filtered),
            'data': filtered.head(20).to_dict(orient='records')
        }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Memoized (cached) version of search_dataset
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def cached_search_dataset(query_hash: str, query: str) -> str:
    """Cached version of search_dataset"""
    if collection is None:
        return "Dataset not indexed yet"
    
    results = collection.query(query_texts=[query], n_results=5)
    
    if results['documents'] and results['documents'][0]:
        # Get metadata to show sources
        docs = results['documents'][0]
        metas = results['metadatas'][0] if results['metadatas'] else [{}] * len(docs)
        
        formatted_results = []
        for doc, meta in zip(docs, metas):
            source = meta.get('source', 'dataset')
            if source == 'web_search':
                formatted_results.append(f"[From web search] {doc}")
            elif source == 'learned':
                formatted_results.append(f"[Learned info] {doc}")
            else:
                formatted_results.append(f"[Dataset] {doc[:200]}")
        
        context = "\n\n".join(formatted_results)
        return f"Found relevant information:\n\n{context}"
    return "No matching information found"

def search_dataset(query: str) -> str:
    query_hash = hashlib.md5(query.encode()).hexdigest()
    return cached_search_dataset(query_hash, query)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    status = {
        'status': 'healthy',
        'dataset_loaded': current_dataset is not None,
        'vector_db_ready': collection is not None,
        'knowledge_base_size': collection.count() if collection else 0,
        'ollama_connected': test_ollama()
    }
    return jsonify(status)

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f'Server Error: {error}')
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error(f'Unhandled Exception: {str(e)}')
    return jsonify({'error': 'An unexpected error occurred'}), 500

if __name__ == '__main__':
    validate_env_vars()
    print("\n" + "="*60)
    print("🤖 Econ Assistant - Self-Learning Dataset Expert")
    print("="*60)
    
    if USE_LANGSMITH:
        print(f"✅ LangSmith tracing enabled")
        print(f"   Project: {os.getenv('LANGCHAIN_PROJECT')}")
        print(f"   Dashboard: https://smith.langchain.com/")
    else:
        print("⚠ LangSmith tracing disabled")
    
    print("\nInitializing...")
    print("1. Testing Ollama connection...")
    test_ollama()
    
    print("2. Initializing persistent vector database...")
    init_vector_db()
    
    print("3. Loading initial dataset...")
    load_initial_dataset()
    
    print("\n✓ Ready! The agent will:")
    print("  • Remember information across sessions")
    print("  • Auto-save web search results")
    print("  • Learn from user interactions")
    print("="*60 + "\n")
    
    # Setup logging
    if not app.debug:
        os.makedirs('logs', exist_ok=True)
        file_handler = RotatingFileHandler('logs/econ_assistant.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Econ Assistant startup')
    
    app.run(debug=True, host='0.0.0.0')