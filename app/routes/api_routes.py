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
    
    def format_forecast_result(result_json: str, tool_name: str) -> tuple:
        """Format forecast results in user-friendly way with optional visualization
        
        Returns:
            tuple: (formatted_string, updated_json_with_viz) or (formatted_string, None)
        """
        try:
            data = json.loads(result_json)
            
            if "error" in data:
                return result_json, None
            
            # Format forecast results nicely
            if tool_name in ["forecast_economic_indicator", "forecast_trade_balance"]:
                indicator = data.get("indicator", "the indicator")
                forecasts = data.get("forecasts", [])
                
                if not forecasts:
                    return result_json, None
                
                # Try to generate visualization
                viz_result = None
                try:
                    from app.agents.visualization_agent import get_visualization_agent
                    viz_agent = get_visualization_agent()
                    viz_result = viz_agent.auto_visualize(data, f"forecast {indicator}")
                except Exception as e:
                    logger.warning(f"Visualization failed: {e}")
                
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
                
                # Add visualization link if generated
                if viz_result:
                    output.append(f"\n📈 **Visualization:** [View Chart]({viz_result['image_url']})")
                    # Store in data for JSON response
                    data['visualization'] = viz_result
                
                return "\n".join(output), json.dumps(data)
            
            return result_json, None
            
        except Exception as e:
            logger.error(f"Error formatting forecast result: {e}")
            return result_json, None
    
    def execute_tool(tool_name: str, arguments: dict) -> tuple:
        """Execute a tool by name with intelligent auto-recovery
        
        Returns:
            tuple: (result_string, visualization_data or None)
        """
        if tool_name in TOOL_MAP:
            try:
                result = TOOL_MAP[tool_name](**arguments)
            except TypeError as e:
                # Handle tool argument mismatch - likely LLM called wrong tool
                error_msg = str(e)
                if "unexpected keyword argument" in error_msg:
                    logger.error(f"Tool argument error: {tool_name} called with {arguments}")
                    
                    # Provide helpful error message
                    if tool_name == "calculate" and "indicator" in arguments:
                        return "ERROR: You called calculate() but meant to call forecast_economic_indicator(). The calculate() tool is for math expressions like '2+2', while forecast_economic_indicator() is for economic forecasts. Please call forecast_economic_indicator() with the indicator parameter instead.", None
                    
                    return f"ERROR: Tool '{tool_name}' was called with incorrect arguments {arguments}. Please check the tool definition and call it with the correct parameters. Error: {error_msg}", None
                raise  # Re-raise if it's a different TypeError
            
            # INTELLIGENT AUTO-RECOVERY: If forecast fails due to missing data, automatically search for it
            if tool_name in ["forecast_economic_indicator", "forecast_trade_balance"]:
                try:
                    result_data = json.loads(result)
                    if "error" in result_data and "Could not find indicator" in result_data.get("error", ""):
                        # Extract indicator name
                        indicator = arguments.get('indicator') or arguments.get('query', 'unknown')
                        
                        logger.info(f"🔄 Auto-recovery: Forecast failed for '{indicator}', searching official sources...")
                        
                        # Try to find the data from official sources
                        search_query = f"Moldova {indicator} historical data statistics"
                        search_result = search_official_sources(search_query)
                        
                        # Also try web search as backup
                        web_result = web_search(f"Moldova {indicator} 2024 2025 statistica.md")
                        
                        # Save the learned information FIRST
                        combined_info = f"Official sources for {indicator}: {search_result}\n\nAdditional context: {web_result}"
                        add_learned_info(combined_info, f"Moldova {indicator}")
                        
                        # Now re-query the knowledge base with the newly learned info
                        logger.info(f"✅ External data found and saved. Re-searching knowledge base for '{indicator}'...")
                        kb_result = search_dataset(f"Moldova {indicator}")
                        
                        # Check if searches returned useful data
                        search_empty = (len(search_result) < 50 or "No results" in search_result) and \
                                      (len(web_result) < 50 or "No results" in web_result)
                        
                        if search_empty:
                            # Provide context-aware guidance with known Moldova economic indicators
                            guidance = {
                                "inflation": "Moldova's inflation rate typically ranges 3-8% annually. The National Bank of Moldova (NBM) at bnm.md publishes monthly inflation reports. Recent trends show moderate inflation around 4-5% in 2024-2025.",
                                "gdp": "Moldova's GDP growth has averaged 3-5% in recent years. Check World Bank Moldova page or statistica.md for quarterly GDP data.",
                                "unemployment": "Moldova's unemployment rate is typically 3-5%. National Bureau of Statistics (statistica.md) publishes quarterly labor market statistics.",
                                "exchange": "MDL/USD exchange rate fluctuates between 17-19 MDL per USD. NBM provides daily rates at bnm.md.",
                                "wage": "Average wage in Moldova is approximately 10,000-12,000 MDL/month. Statistica.md publishes monthly wage statistics.",
                            }
                            
                            # Find matching guidance
                            guidance_text = None
                            for key, text in guidance.items():
                                if key in indicator.lower():
                                    guidance_text = text
                                    break
                            
                            if not guidance_text:
                                guidance_text = f"For {indicator} data, check: National Bureau of Statistics (statistica.md), National Bank of Moldova (bnm.md), World Bank Moldova, or IMF Moldova reports."
                            
                            # Return informative message with the guidance for user
                            return f"📚 AUTO-RECOVERY: External search completed.\n\nContext found: {guidance_text}\n\nKnowledge base contains: {kb_result[:200]}\n\n⚠️ CRITICAL INSTRUCTION: The dataset doesn't have numerical time-series data for {indicator} forecasting. However, you MUST provide an informed qualitative analysis based on the context above. DO NOT tell users to 'check external sources' - that's lazy. Instead:\n1. Summarize the key trend from the context (e.g., '3-5% growth historically')\n2. Provide a reasonable projection for next year based on that trend\n3. Explain your reasoning\n4. Give a specific answer, not a referral.", None
                        else:
                            # Data found! Return it for the LLM to use - be VERY explicit
                            return f"✅ AUTO-RECOVERY SUCCESSFUL!\n\nExternal data found and saved to knowledge base for Moldova {indicator}.\n\nKnowledge base now contains:\n{kb_result[:500]}\n\nAdditional web context:\n{combined_info[:300]}\n\n⚠️ CRITICAL INSTRUCTION FOR LLM:\n- The dataset still lacks numerical time-series data for forecasting charts\n- You CANNOT generate a forecast chart without historical numerical data\n- DO NOT mention checking external sources like 'statistica.md' or 'World Bank' - that's what I just did!\n- DO NOT create fake chart references\n- MUST provide qualitative analysis using the information above\n- Extract specific numbers/trends from the text above and present them\n- Give a projection based on the context provided\n- Be specific and authoritative in your answer\n\nExample good response: 'Based on recent data, Moldova's {indicator} has shown X trend. Historical analysis indicates Y. For next year, we can expect Z based on current conditions.'\n\nNOW ANSWER THE USER'S QUESTION USING THIS INFORMATION!", None
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.debug(f"Auto-recovery not applicable: {e}")
                    pass  # Continue with normal forecast formatting
                
                # Format successful forecast results
                formatted_text, updated_json = format_forecast_result(result, tool_name)
                # Extract visualization data if present
                viz_data = None
                if updated_json:
                    try:
                        data = json.loads(updated_json)
                        viz_data = data.get('visualization')
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Could not extract visualization data: {e}")
                return formatted_text, viz_data
            
            return result, None
        return f"Unknown tool: {tool_name}", None
    
    def parse_tool_calls_from_text(content: str):
        """Parse tool calls from LLM text response - handles multiple formats"""
        tools_executed = []
        
        # Try to parse JSON-formatted tool calls (Qwen format: {"name": "tool", "arguments": {...}})
        json_pattern = r'\{["\']name["\']\s*:\s*["\'](\w+)["\']\s*,\s*["\']arguments["\']\s*:\s*(\{[^}]+\})\}'
        json_matches = re.finditer(json_pattern, content, re.IGNORECASE)
        
        for match in json_matches:
            tool_name = match.group(1)
            try:
                args_str = match.group(2)
                tool_args = json.loads(args_str)
                
                if tool_name in TOOL_MAP:
                    result = execute_tool(tool_name, tool_args)
                    tools_executed.append({'tool': tool_name, 'arguments': tool_args, 'result': result})
            except Exception as e:
                logger.error(f"Failed to parse JSON tool call: {e}")
        
        # If JSON parsing found tools, return those
        if tools_executed:
            return tools_executed
        
        # Fallback to regex parsing for Python-style function calls
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
        
        # Forecast economic indicator - flexible parameter order
        forecast_match = re.search(r'forecast_economic_indicator\s*\(([^)]+)\)', content, re.IGNORECASE)
        if forecast_match:
            args_str = forecast_match.group(1)
            
            # Extract indicator
            indicator_match = re.search(r'indicator\s*=\s*["\']([^"\']+)["\']', args_str, re.IGNORECASE)
            indicator = indicator_match.group(1) if indicator_match else None
            
            # Extract time_periods
            periods_match = re.search(r'(?:time_periods|periods)\s*=\s*(\d+)', args_str, re.IGNORECASE)
            time_periods = int(periods_match.group(1)) if periods_match else 12
            
            # Extract method
            method_match = re.search(r'method\s*=\s*["\']([^"\']+)["\']', args_str, re.IGNORECASE)
            method = method_match.group(1) if method_match else "ensemble"
            
            if indicator:
                result = forecast_economic_indicator(indicator=indicator, time_periods=time_periods, method=method)
                # Format the result and extract visualization
                formatted_result, updated_json = format_forecast_result(result, 'forecast_economic_indicator')
                tool_entry = {'tool': 'forecast_economic_indicator', 'arguments': {'indicator': indicator, 'time_periods': time_periods, 'method': method}, 'result': formatted_result}
                # Check for visualization data
                if updated_json:
                    try:
                        data = json.loads(updated_json)
                        if 'visualization' in data:
                            tool_entry['visualization'] = data['visualization']
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.debug(f"No visualization in forecast result: {e}")
                tools_executed.append(tool_entry)
        
        # Forecast trade balance
        trade_forecast_match = re.search(r'forecast_trade_balance\s*\(\s*export_indicator\s*=\s*["\']([^"\']+)["\']\s*,\s*import_indicator\s*=\s*["\']([^"\']+)["\']\s*(?:,\s*periods_ahead\s*=\s*(\d+))?\s*\)', content, re.IGNORECASE)
        if trade_forecast_match:
            export_ind = trade_forecast_match.group(1)
            import_ind = trade_forecast_match.group(2)
            periods = int(trade_forecast_match.group(3)) if trade_forecast_match.group(3) else 12
            result = forecast_trade_balance(export_indicator=export_ind, import_indicator=import_ind, periods_ahead=periods)
            # Format the result and extract visualization
            formatted_result, updated_json = format_forecast_result(result, 'forecast_trade_balance')
            tool_entry = {'tool': 'forecast_trade_balance', 'arguments': {'export_indicator': export_ind, 'import_indicator': import_ind, 'periods_ahead': periods}, 'result': formatted_result}
            # Check for visualization data
            if updated_json:
                try:
                    data = json.loads(updated_json)
                    if 'visualization' in data:
                        tool_entry['visualization'] = data['visualization']
                except (json.JSONDecodeError, KeyError) as e:
                    logger.debug(f"No visualization in trade forecast result: {e}")
            tools_executed.append(tool_entry)
        
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

🚨 MANDATORY WORKFLOW - FOLLOW THIS EXACTLY:
Step 1: ALWAYS call search_dataset() first with relevant keywords
Step 2: If no data found, call search_official_sources() with "Moldova [topic]"
Step 3: If historical data found, use it for context or forecasting base
Step 4: ONLY say "no data available" if BOTH searches return nothing
Step 5: For future predictions, use forecast_economic_indicator() with historical data

EXAMPLES OF CORRECT WORKFLOW:
❌ WRONG: "Dataset doesn't have inflation data" → Immediately forecast
✅ CORRECT: search_dataset("Moldova inflation") → search_official_sources("Moldova inflation rate") → Use results to forecast or answer

❌ WRONG: "No historical data, using forecast methods"
✅ CORRECT: search_dataset("inflation") → search_official_sources("Moldova inflation historical") → IF found: base forecast on it, IF not found: use default parameters

TOOL USAGE PRIORITY FOR MOLDOVA ECONOMICS:
1. search_dataset() - MANDATORY FIRST STEP - Check if we already have the answer
2. search_official_sources() - MANDATORY SECOND STEP if search_dataset returns nothing
3. forecast_economic_indicator() - Use AFTER searching, with historical context if available
4. verify_with_sources() - Verify important claims
5. web_search() - ONLY if official sources don't have the answer

FORECASTING GUIDANCE:
- When asked about future trends, predictions, or "what will happen next year" → FIRST search for historical data, THEN use forecast_economic_indicator()
- NEVER say "dataset doesn't contain X data" without calling search_dataset() and search_official_sources() first
- NEVER respond with "further investigation needed" or "contact authorities" for forecasts
- Use method="ensemble" for most reliable forecasts (combines multiple models)
- For trade predictions → use forecast_trade_balance()
- Forecasting uses: Linear Trend, CAGR, Exponential Smoothing, Moving Average, Ensemble

CRITICAL INSTRUCTIONS FOR FORECASTING:
1. When user asks for forecasts/predictions, YOU MUST use the structured tool calling mechanism
2. NEVER write "forecast_economic_indicator(...)" as text - use the actual tool call
3. DO NOT say "I'll proceed with the forecast" or "Let me forecast" - just call the tool
4. BEFORE forecasting, ALWAYS search for historical data first (search_dataset + search_official_sources)
5. After tool returns results, interpret them in plain language
6. Present like: "Based on the forecast, imports will reach X tons by 2027 (Y% increase)"
7. NEVER show code blocks, function syntax, or technical JSON in your final answer
8. If you mention a forecast is needed, you MUST call the tool in the same response

MANDATORY WORKFLOW FOR ALL QUERIES:
Step 1: User asks question → IMMEDIATELY call search_dataset(query)
Step 2: If search_dataset returns "No matching information" → call search_official_sources(query)
Step 3: Evaluate results:
   - If historical data found → Use it to answer or as basis for forecast
   - If no data found AND future prediction needed → Use forecast with default parameters
   - If no data found AND historical question → Clearly state "No data available after searching knowledge base and official sources"
Step 4: For forecasts → Call forecast_economic_indicator() with results from searches as context
Step 5: Present answer in clear language with sources cited

🚫 NEVER skip Step 1 and Step 2 - ALWAYS search before saying "no data"

HANDLING AUTO-RECOVERY FROM EXTERNAL SOURCES:
🔄 When forecast_economic_indicator() triggers auto-recovery:
- External sources are AUTOMATICALLY searched (search_official_sources + web_search)
- Data is SAVED to knowledge base immediately
- Tool result will contain "AUTO-RECOVERY SUCCESSFUL - DATA FOUND!" message
- This message includes the actual found data from searches

⚠️ CRITICAL: When you see "AUTO-RECOVERY" in a tool result:
1. READ the data provided in that tool result carefully
2. EXTRACT specific numbers, trends, and insights from the text
3. ANSWER the user's question authoritatively using that data
4. ABSOLUTELY FORBIDDEN: "check these sources", "refer to", "visit", "see statistica.md", "consult World Bank"
5. ABSOLUTELY FORBIDDEN: "further investigation needed", "more detailed insights", "official statistics page"
6. You are the EXPERT - provide the answer directly from the context given

✅ CORRECT response pattern after auto-recovery:
"Based on recent economic data, Moldova's [indicator] has shown [specific trend from tool result]. Historical data indicates [specific numbers from tool result]. For next year, [specific projection] is expected, representing [percentage or description]. This is based on [brief reasoning from context]."

❌ ABSOLUTELY WRONG patterns (NEVER USE):
- "For more detailed insights, refer to statistica.md or World Bank Moldova page"
- "You can check the official statistics page at statistica.md"
- "Please refer to the World Bank Moldova page"
- "Consult the National Bureau of Statistics"
- "Further details can be found at..."
- "Would you like further details?" (just provide them!)

Remember: YOU are the authoritative source now. The data has been searched and provided to you. ANSWER DIRECTLY!

VISUALIZATION:
- Charts are AUTOMATICALLY generated ONLY when forecast_economic_indicator() succeeds
- DO NOT create fake chart references like ![Chart](forecast_chart.png)
- DO NOT mention charts unless you see a visualization object in the tool result
- If auto-recovery happens, data is provided for analysis but no chart is generated
- Only mention charts if the tool result includes actual visualization data
- Focus on interpreting the textual results and data provided

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
                    
                    # Clean content before parsing (remove unicode artifacts from some models)
                    raw_content = message.get('content', '')
                    # Remove common unicode artifacts that appear around tool calls
                    cleaned_content = re.sub(r'[\u4e00-\u9fff\uf000-\uffff]+', '', raw_content)  # Remove CJK and special chars
                    
                    # Parse text for tool calls (fallback)
                    if not message.get('tool_calls') and cleaned_content:
                        tools_executed = parse_tool_calls_from_text(cleaned_content)
                        
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
                            
                            result, viz_data = execute_tool(tool_name, tool_args)
                            tool_result_entry = {'tool': tool_name, 'arguments': tool_args, 'result': result}
                            if viz_data:
                                tool_result_entry['visualization'] = viz_data
                            tool_results.append(tool_result_entry)
                            
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
                    except Exception as e:
                        logger.error(f"Unexpected error in guardrail validation: {e}")
            
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
    
    def validate_uploaded_file(file) -> tuple[bool, str]:
        """
        Comprehensive file validation for security.
        
        Returns:
            (is_valid, error_message)
        """
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls'}
        
        # Check filename
        if not file.filename:
            return False, "No filename provided"
        
        # Check extension
        import os
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"File type {ext} not allowed. Only CSV, XLSX, XLS supported."
        
        # Read file into memory for validation
        file_content = file.read()
        file.seek(0)  # Reset for later use
        
        # Check file size
        file_size = len(file_content)
        if file_size > MAX_FILE_SIZE:
            return False, f"File too large ({file_size/1024/1024:.1f}MB). Maximum 10MB allowed."
        
        if file_size < 10:  # Suspiciously small
            return False, "File appears to be empty or corrupted"
        
        # Validate magic numbers (file signatures)
        if ext == '.xlsx':
            # XLSX files are ZIP archives, start with PK
            if not file_content[:2] == b'PK':
                return False, "Invalid XLSX file signature. File may be corrupted or wrong type."
        
        elif ext == '.xls':
            # Old Excel format starts with D0 CF
            if not file_content[:2] == b'\xD0\xCF':
                return False, "Invalid XLS file signature. File may be corrupted or wrong type."
        
        elif ext == '.csv':
            # CSV should be valid text - try decoding first 1KB
            try:
                file_content[:1024].decode('utf-8')
            except UnicodeDecodeError:
                try:
                    file_content[:1024].decode('latin-1')
                except UnicodeDecodeError:
                    return False, "CSV file encoding not supported. Please use UTF-8 or Latin-1."
        
        return True, ""
    
    @api_bp.route('/dataset/upload', methods=['POST'])
    def upload_dataset():
        """Upload a new dataset (CSV/Excel) with comprehensive security validation and curation evaluation"""
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # SECURITY: Validate file thoroughly
        is_valid, error_msg = validate_uploaded_file(file)
        if not is_valid:
            logger.warning(f"File upload validation failed: {error_msg}")
            return jsonify({'error': error_msg}), 400
        
        # Get metadata
        name = request.form.get('name')
        description = request.form.get('description', '')
        source = request.form.get('source', 'User upload')
        trust_score = request.form.get('trust_score', type=float)
        add_to_core = request.form.get('add_to_core', 'auto')  # 'auto', 'yes', 'no'
        
        if not name:
            return jsonify({'error': 'Dataset name required'}), 400
        
        # Validate name (prevent path traversal)
        if not name.replace('_', '').replace('-', '').replace(' ', '').isalnum():
            return jsonify({'error': 'Dataset name contains invalid characters'}), 400
        
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
