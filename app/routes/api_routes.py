"""API routes"""
from flask import Blueprint, request, jsonify, session
import json
import re
import logging
import time
import pandas as pd
from datetime import datetime
from app.services.guardrails import get_guardrails, GuardrailViolation
from app.services.analytics import get_analytics

logger = logging.getLogger(__name__)

def create_api_blueprint(llm_service, db_service, get_dataset, get_dataset_info):
    """Create API blueprint with injected dependencies"""
    api_bp = Blueprint('api', __name__)
    
    from app.tools import (TOOLS, search_dataset, web_search, calculate, analyze_column, 
                          add_learned_info, search_official_sources, verify_with_sources, 
                          list_datasets, get_source_trust_score, forecast_economic_indicator,
                          forecast_trade_balance)
    from app.tools.engagement import suggest_followup, set_llm_service
    from app.agents import get_data_agent
    from app.agents.curator_agent import get_curator_agent
    from app.tools.verify import set_data_agent
    
    # Initialize guardrails, analytics, data agent, and curator
    guardrails = get_guardrails()
    analytics = get_analytics()
    data_agent = get_data_agent(db_service)
    curator_agent = get_curator_agent(db_service, llm_service)
    
    # Set dependencies for tools
    set_llm_service(llm_service)
    set_data_agent(data_agent)
    
    # Tool execution map
    TOOL_MAP = {
        "search_dataset": search_dataset,
        "web_search": web_search,
        "calculate": calculate,
        "analyze_column": analyze_column,
        "add_learned_info": add_learned_info,
        "search_official_sources": search_official_sources,
        "verify_with_sources": verify_with_sources,
        "list_datasets": list_datasets,
        "get_source_trust_score": get_source_trust_score,
        "forecast_economic_indicator": forecast_economic_indicator,
        "forecast_trade_balance": forecast_trade_balance
    }
    
    def format_forecast_result(result_json: str, tool_name: str) -> str:
        """Format forecast results in user-friendly way"""
        try:
            data = json.loads(result_json)
            
            if "error" in data:
                return result_json
            
            # Format forecast results nicely
            if tool_name in ["forecast_economic_indicator", "forecast_trade_balance"]:
                indicator = data.get("indicator", "the indicator")
                forecasts = data.get("forecasts", [])
                
                if not forecasts:
                    return result_json
                
                # Create human-readable summary
                output = []
                output.append(f"\n📊 **Forecast Results for {indicator}:**\n")
                
                if len(forecasts) <= 6:
                    # Show all periods
                    for i, val in enumerate(forecasts, 1):
                        output.append(f"Period {i}: {val:,.0f}")
                else:
                    # Show first, middle, and last
                    output.append(f"Next period: {forecasts[0]:,.0f}")
                    output.append(f"Mid-point (period {len(forecasts)//2}): {forecasts[len(forecasts)//2]:,.0f}")
                    output.append(f"Final period ({len(forecasts)}): {forecasts[-1]:,.0f}")
                
                # Add interpretation
                if "interpretation" in data:
                    output.append(f"\n💡 {data['interpretation']}")
                
                # Add confidence if available
                if "lower_bound" in data and "upper_bound" in data:
                    output.append(f"\nConfidence range: {data['lower_bound'][0]:,.0f} - {data['upper_bound'][0]:,.0f}")
                
                return "\n".join(output)
            
            return result_json
            
        except:
            return result_json
    
    def execute_tool(tool_name: str, arguments: dict) -> str:
        """Execute a tool by name"""
        if tool_name in TOOL_MAP:
            result = TOOL_MAP[tool_name](**arguments)
            # Format forecast results for better readability
            if tool_name in ["forecast_economic_indicator", "forecast_trade_balance"]:
                return format_forecast_result(result, tool_name)
            return result
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
        """Main agent endpoint with guardrails"""
        dataset = get_dataset()
        if dataset is None:
            return jsonify({'error': 'No dataset loaded'}), 400
        
        data = request.json
        question = data.get('question', '')
        
        if not question:
            return jsonify({'error': 'Question required'}), 400
        
        # Get user ID for rate limiting (use session ID or IP)
        user_id = session.get('user_id') or request.remote_addr
        
        # GUARDRAILS: Validate input
        is_valid, error_msg = guardrails.validate_input(question, user_id=user_id)
        if not is_valid:
            logger.warning(f"Input validation failed: {error_msg}")
            return jsonify({'error': error_msg}), 400
        
        # GUARDRAILS: Sanitize prompt
        question = guardrails.sanitize_prompt(question)
        
        # ANALYTICS: Track query start time
        query_start_time = time.time()
        
        try:
            dataset_info = get_dataset_info()
            
            # Get current date for context
            from datetime import datetime
            current_date = datetime.now().strftime("%B %d, %Y")
            
            system_msg = f"""You are a Moldova economics data analyst assistant with a persistent knowledge base.

CURRENT DATE: {current_date}
IMPORTANT: Today is {current_date}. When users ask about recent data or "this year", they mean 2025.

CRITICAL CONTEXT: 
- ALL questions are about MOLDOVA unless explicitly specified otherwise
- ALWAYS assume Moldova context (Moldova GDP, Moldova exports, Moldova economy, etc.)
- Republic of Moldova is the default country for all economic queries

Dataset Info:
- Rows: {dataset_info['rows']}
- Columns: {', '.join(dataset_info['columns'])}
- Knowledge Base: {db_service.collection.count() if db_service.collection else 0} total documents

Available Tools (use in this EXACT priority order):
1. search_dataset(query): ALWAYS TRY THIS FIRST - searches dataset + learned information
2. search_official_sources(query): For MOLDOVA data, use official sources (statistica.md, World Bank Moldova, NBM, IMF Moldova)
3. forecast_economic_indicator(indicator, time_periods, method): **NEW** Forecast future values using statistical models
4. forecast_trade_balance(export_indicator, import_indicator, periods_ahead): **NEW** Forecast Moldova's trade balance
5. analyze_column(column, analysis_type): Get statistics from dataset
6. calculate(expression): Perform calculations
7. verify_with_sources(claim): Cross-check important data against official sources
8. web_search(query): General web search ONLY as last resort - use search_official_sources first
9. add_learned_info(information, category): Save insights for future use

TOOL USAGE PRIORITY FOR MOLDOVA ECONOMICS:
1. search_dataset() - Check if we already have the answer
2. search_official_sources() - Get authoritative Moldova data from statistica.md, World Bank, IMF, NBM
3. forecast_economic_indicator() - **NEVER say "further investigation needed" - use this to forecast!**
4. verify_with_sources() - Verify important claims
5. web_search() - ONLY if official sources don't have the answer

FORECASTING GUIDANCE:
- When asked about future trends, predictions, or "what will happen next year" → USE forecast_economic_indicator()
- NEVER respond with "further investigation needed" or "contact authorities" for forecasts
- Use method="ensemble" for most reliable forecasts (combines multiple models)
- For trade predictions → use forecast_trade_balance()
- Forecasting uses: Linear Trend, CAGR, Exponential Smoothing, Moving Average, Ensemble

CRITICAL INSTRUCTIONS FOR FORECASTING:
1. When user asks for forecasts/predictions, YOU MUST use the structured tool calling mechanism
2. NEVER write "forecast_economic_indicator(...)" as text - use the actual tool call
3. DO NOT say "I'll proceed with the forecast" or "Let me forecast" - just call the tool
4. After tool returns results, interpret them in plain language
5. Present like: "Based on the forecast, imports will reach X tons by 2027 (Y% increase)"
6. NEVER show code blocks, function syntax, or technical JSON in your final answer
7. If you mention a forecast is needed, you MUST call the tool in the same response

WORKFLOW:
1. For ANY Moldova economics question, first call search_dataset()
2. If not found, use search_official_sources() for authoritative Moldova data
3. For FUTURE predictions/forecasts, ACTUALLY CALL forecast_economic_indicator() and present results clearly
4. ONLY use web_search() as a last resort if official sources lack the information
5. Always verify important statistics with verify_with_sources()
6. Always specify "Moldova" in search queries even if user didn't (e.g., "Moldova GDP" not just "GDP")

RESPONSE FORMAT:
- Use clear, conversational language
- Present numbers with context and units
- Explain what forecasts mean (e.g., "20% increase means...")
- Hide technical details (R-squared, MAPE) unless specifically asked
- Focus on actionable insights

Remember: Moldova context is ALWAYS assumed unless user explicitly mentions another country!"""

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
                        # Clean up response - remove code blocks showing function calls
                        content = message['content']
                        
                        # Remove code blocks that show tool calls
                        content = re.sub(r'```python\s*forecast_[^`]+```', '', content)
                        content = re.sub(r'```\s*forecast_[^`]+```', '', content)
                        
                        # Remove phrases like "I'll proceed with the forecast now"
                        content = re.sub(r"I'?ll proceed with (?:the )?(?:forecast|analysis).*?(?:\.|$)", '', content, flags=re.IGNORECASE)
                        content = re.sub(r"Let me (?:proceed|run|execute).*?(?:forecast|analysis).*?(?:\.|$)", '', content, flags=re.IGNORECASE)
                        
                        # Clean up extra whitespace
                        content = re.sub(r'\n{3,}', '\n\n', content).strip()
                        
                        # GUARDRAILS: Validate output before returning
                        try:
                            validated_answer = guardrails.validate_output(content)
                            
                            # ENGAGEMENT: Generate follow-up question
                            followup = suggest_followup(question, validated_answer)
                            
                            # ANALYTICS: Log successful query
                            query_time = time.time() - query_start_time
                            tools_list = [tr['tool'] for tr in tool_results]
                            analytics.log_query(
                                prompt=question,
                                answer=validated_answer,
                                tools_used=tools_list,
                                query_time=query_time,
                                success=True
                            )
                            
                            return jsonify({
                                'question': question, 
                                'answer': validated_answer, 
                                'tool_calls': tool_results,
                                'followup': followup
                            })
                        except GuardrailViolation as e:
                            logger.error(f"Output validation failed: {e.message}")
                            
                            # ANALYTICS: Log failed query
                            query_time = time.time() - query_start_time
                            analytics.log_query(
                                prompt=question,
                                answer="",
                                tools_used=[],
                                query_time=query_time,
                                success=False,
                                error=f"Guardrail violation: {e.violation_type}"
                            )
                            
                            return jsonify({'error': 'Response blocked by safety filter', 'details': e.violation_type}), 400
                    
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
                        # GUARDRAILS: Validate fallback answer
                        validated_answer = guardrails.validate_output(answer)
                        
                        # ENGAGEMENT: Generate follow-up
                        followup = suggest_followup(question, validated_answer)
                        
                        # ANALYTICS: Log fallback answer
                        query_time = time.time() - query_start_time
                        tools_list = [tr['tool'] for tr in tool_results]
                        analytics.log_query(
                            prompt=question,
                            answer=validated_answer,
                            tools_used=tools_list,
                            query_time=query_time,
                            success=True
                        )
                        
                        return jsonify({
                            'question': question, 
                            'answer': validated_answer, 
                            'tool_calls': tool_results,
                            'followup': followup
                        })
                    except GuardrailViolation as e:
                        logger.error(f"Fallback answer validation failed: {e.message}")
                        
                        # ANALYTICS: Log error
                        query_time = time.time() - query_start_time
                        analytics.log_query(
                            prompt=question,
                            answer="",
                            tools_used=[],
                            query_time=query_time,
                            success=False,
                            error=f"Guardrail violation: {e.message}"
                        )
                        
                        return jsonify({'error': 'Response blocked by safety filter'}), 400
                    except:
                        pass
            
            # ANALYTICS: Log fallback "Could not generate answer"
            query_time = time.time() - query_start_time
            analytics.log_query(
                prompt=question,
                answer="Could not generate answer",
                tools_used=[],
                query_time=query_time,
                success=False,
                error="No answer generated"
            )
            
            return jsonify({'question': question, 'answer': "Could not generate answer", 'tool_calls': tool_results})
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            
            # ANALYTICS: Log exception
            query_time = time.time() - query_start_time
            analytics.log_query(
                prompt=question,
                answer="",
                tools_used=[],
                query_time=query_time,
                success=False,
                error=str(e)
            )
            
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
    
    @api_bp.route('/analytics/summary', methods=['GET'])
    def analytics_summary():
        """Get analytics summary"""
        return jsonify({
            'performance': analytics.get_performance_summary(),
            'tool_usage': analytics.get_tool_usage_stats(),
            'popular_queries': analytics.get_popular_queries(limit=5),
            'data_gaps': analytics.identify_data_gaps(limit=5)
        })
    
    @api_bp.route('/analytics/recent', methods=['GET'])
    def analytics_recent():
        """Get recent queries"""
        limit = request.args.get('limit', 10, type=int)
        return jsonify({
            'recent_queries': analytics.get_recent_queries(limit=limit)
        })
    
    @api_bp.route('/dataset/upload', methods=['POST'])
    def upload_dataset():
        """Upload a new dataset (CSV/Excel) with curation evaluation"""
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get metadata
        name = request.form.get('name')
        description = request.form.get('description', '')
        source = request.form.get('source', 'User upload')
        trust_score = request.form.get('trust_score', type=float)
        add_to_core = request.form.get('add_to_core', 'auto')  # 'auto', 'yes', 'no'
        
        if not name:
            return jsonify({'error': 'Dataset name required'}), 400
        
        # Validate file type
        if not file.filename.lower().endswith(('.csv', '.xlsx', '.xls')):
            return jsonify({'error': 'Only CSV and Excel files supported'}), 400
        
        try:
            # Save temporarily
            import os
            from werkzeug.utils import secure_filename
            temp_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'uploads')
            os.makedirs(temp_dir, exist_ok=True)
            
            filename = secure_filename(file.filename)
            filepath = os.path.join(temp_dir, filename)
            file.save(filepath)
            
            # Load dataset for evaluation
            if filepath.endswith('.csv'):
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath)
            
            # CURATION: Evaluate dataset quality and relevance
            metadata = {
                'filename': filename,
                'source': source,
                'description': description,
                'upload_date': datetime.now().isoformat()
            }
            
            evaluation = curator_agent.evaluate_dataset(df, metadata)
            evaluation_report = curator_agent.generate_report(evaluation)
            
            logger.info(f"Dataset evaluation:\n{evaluation_report}")
            
            # Decide whether to add to core based on evaluation
            should_add_to_core = False
            
            if add_to_core == 'yes':
                should_add_to_core = True
                logger.info(f"User forced add to core: {name}")
            elif add_to_core == 'auto':
                # Auto-decide based on curator recommendation
                if evaluation['recommendation'] in ['ACCEPT', 'ACCEPT_WITH_REVIEW']:
                    should_add_to_core = True
                    logger.info(f"Auto-accepted to core (score: {evaluation['overall_score']}): {name}")
                else:
                    logger.info(f"Not adding to core (score: {evaluation['overall_score']}): {name}")
            
            # Upload to DataAgent (user-specific or core)
            result = data_agent.upload_dataset(
                file_path=filepath,
                name=name,
                description=description,
                trust_score=trust_score
            )
            
            # If approved, also add to core knowledge base with higher trust score
            if should_add_to_core and evaluation['recommendation'] == 'ACCEPT':
                # Index with high trust score for core knowledge
                core_trust_score = 0.85 if evaluation['details']['trust']['is_trusted_source'] else 0.75
                
                # Add each row as a document to core knowledge base
                rows_indexed = 0
                for idx, row in df.iterrows():
                    row_text = ' | '.join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
                    
                    db_service.add_document(
                        text=row_text,
                        metadata={
                            'source': 'curated_dataset',
                            'dataset_name': name,
                            'trust_score': core_trust_score,
                            'row_index': idx,
                            'added_to_core': True
                        }
                    )
                    rows_indexed += 1
                
                logger.info(f"Added {rows_indexed} rows from {name} to core knowledge base")
            
            # Clean up temp file
            os.remove(filepath)
            
            return jsonify({
                'success': True,
                'message': result,
                'dataset_name': name,
                'evaluation': {
                    'recommendation': evaluation['recommendation'],
                    'overall_score': evaluation['overall_score'],
                    'scores': evaluation['scores'],
                    'action': evaluation['action'],
                    'reason': evaluation['reason'],
                    'added_to_core': should_add_to_core
                },
                'report': evaluation_report
            })
            
        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/dataset/list', methods=['GET'])
    def list_user_datasets():
        """List all uploaded datasets"""
        try:
            datasets = data_agent.list_datasets()
            return jsonify({
                'datasets': datasets
            })
        except Exception as e:
            logger.error(f"Failed to list datasets: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @api_bp.route('/dataset/<dataset_name>', methods=['DELETE'])
    def delete_user_dataset(dataset_name):
        """Delete a dataset"""
        try:
            result = data_agent.delete_dataset(dataset_name)
            return jsonify({
                'success': True,
                'message': result
            })
        except Exception as e:
            logger.error(f"Failed to delete dataset: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    return api_bp
