"""API routes"""
from flask import Blueprint, request, jsonify
import json
import re

def create_api_blueprint(llm_service, db_service, get_dataset, get_dataset_info):
    """Create API blueprint with injected dependencies"""
    api_bp = Blueprint('api', __name__)
    
    from app.tools import TOOLS, search_dataset, web_search, calculate, analyze_column, add_learned_info
    
    # Tool execution map
    TOOL_MAP = {
        "search_dataset": search_dataset,
        "web_search": web_search,
        "calculate": calculate,
        "analyze_column": analyze_column,
        "add_learned_info": add_learned_info
    }
    
    def execute_tool(tool_name: str, arguments: dict) -> str:
        """Execute a tool by name"""
        if tool_name in TOOL_MAP:
            return TOOL_MAP[tool_name](**arguments)
        return f"Unknown tool: {tool_name}"
    
    def parse_tool_calls_from_text(content: str):
        """Parse tool calls from LLM text response"""
        tools_executed = []
        
        # Web search
        web_match = re.search(r'web_search\s*\(\s*query\s*=\s*["\']([^"\']+)["\']\s*\)', content, re.IGNORECASE)
        if web_match:
            query = web_match.group(1)
            result = web_search(query)
            tools_executed.append({'tool': 'web_search', 'arguments': {'query': query}, 'result': result})
        
        # Analyze column
        analyze_match = re.search(r'analyze_column\s*\(\s*column\s*=\s*["\']([^"\']+)["\']\s*(?:,\s*analysis_type\s*=\s*["\']([^"\']+)["\']\s*)?\)', content, re.IGNORECASE)
        if analyze_match:
            col = analyze_match.group(1)
            analysis_type = analyze_match.group(2) or "summary"
            result = analyze_column(col, analysis_type)
            tools_executed.append({'tool': 'analyze_column', 'arguments': {'column': col, 'analysis_type': analysis_type}, 'result': result})
        
        # Search dataset
        search_match = re.search(r'search_dataset\s*\(\s*query\s*=\s*["\']([^"\']+)["\']\s*\)', content, re.IGNORECASE)
        if search_match:
            query = search_match.group(1)
            result = search_dataset(query)
            tools_executed.append({'tool': 'search_dataset', 'arguments': {'query': query}, 'result': result})
        
        return tools_executed
    
    @api_bp.route('/agent/query', methods=['POST'])
    def agent_query():
        """Main agent endpoint"""
        dataset = get_dataset()
        if dataset is None:
            return jsonify({'error': 'No dataset loaded'}), 400
        
        data = request.json
        question = data.get('question', '')
        
        if not question:
            return jsonify({'error': 'Question required'}), 400
        
        try:
            dataset_info = get_dataset_info()
            system_msg = f"""You are a self-improving data analyst assistant with a persistent knowledge base.

Dataset Info:
- Rows: {dataset_info['rows']}
- Columns: {', '.join(dataset_info['columns'])}
- Knowledge Base: {db_service.collection.count() if db_service.collection else 0} total documents

Available Tools (use them in this priority):
1. search_dataset(query): ALWAYS TRY THIS FIRST - searches both dataset AND all previously learned information
2. analyze_column(column, analysis_type): Get statistics
3. calculate(expression): Perform calculations
4. web_search(query): Search web ONLY if search_dataset didn't find answer - results auto-saved
5. add_learned_info(information, category): Manually save insights

WORKFLOW:
1. For ANY question, first call search_dataset
2. If not found, use web_search or other tools
3. Provide a clear answer based on tool results

The knowledge base remembers everything across sessions!"""

            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": question}
            ]
            
            response = llm_service.chat(messages, tools=TOOLS)
            tool_results = []
            max_iterations = 3
            
            for iteration in range(max_iterations):
                if isinstance(response, dict):
                    if 'error' in response:
                        return jsonify({'question': question, 'answer': f"Error: {response['error']}", 'tool_calls': tool_results})
                    
                    message = response.get('message', {})
                    
                    # Parse text for tool calls (fallback)
                    if not message.get('tool_calls') and message.get('content'):
                        tools_executed = parse_tool_calls_from_text(message.get('content', ''))
                        
                        if tools_executed:
                            tool_results.extend(tools_executed)
                            tool_context = "\n\n".join([f"Tool: {t['tool']}\nResult: {t['result']}" for t in tools_executed])
                            
                            messages.append({"role": "assistant", "content": message.get('content', '')})
                            messages.append({"role": "user", "content": f"Tool results:\n{tool_context}\n\nBased on these results, provide a clear answer."})
                            response = llm_service.chat(messages, tools=None)
                            continue
                    
                    # Check if done
                    if message.get('content') and not message.get('tool_calls'):
                        return jsonify({'question': question, 'answer': message['content'], 'tool_calls': tool_results})
                    
                    # Execute structured tool calls
                    if message.get('tool_calls'):
                        for tool_call in message['tool_calls']:
                            func = tool_call['function']
                            tool_name = func['name']
                            tool_args = json.loads(func['arguments']) if isinstance(func['arguments'], str) else func['arguments']
                            
                            result = execute_tool(tool_name, tool_args)
                            tool_results.append({'tool': tool_name, 'arguments': tool_args, 'result': result})
                            
                            messages.append(message)
                            messages.append({"role": "tool", "content": result})
                        
                        messages.append({"role": "user", "content": "Based on the tool results above, provide a clear answer."})
                        response = llm_service.chat(messages, tools=None)
                    else:
                        break
            
            # Fallback answer generation
            if tool_results:
                first_result = tool_results[0]
                if first_result['tool'] == 'analyze_column':
                    try:
                        stats = json.loads(first_result['result'])
                        answer = f"Based on analysis, the average {first_result['arguments']['column']} is {stats.get('mean', 'N/A')}"
                        return jsonify({'question': question, 'answer': answer, 'tool_calls': tool_results})
                    except:
                        pass
            
            return jsonify({'question': question, 'answer': "Could not generate answer", 'tool_calls': tool_results})
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'question': question, 'answer': f"Error: {str(e)}", 'tool_calls': []})
    
    @api_bp.route('/dataset/info', methods=['GET'])
    def dataset_info():
        """Get dataset and knowledge base info"""
        dataset = get_dataset()
        if dataset is None:
            return jsonify({'error': 'No dataset loaded'}), 400
        
        return jsonify({
            'dataset': get_dataset_info(),
            'knowledge_base': db_service.get_stats()
        })
    
    return api_bp
