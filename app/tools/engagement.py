"""
Engagement tool for generating contextual follow-up questions.
Helps users explore economic data more deeply.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Global reference to LLM service
llm_service = None

def set_llm_service(service):
    """Set the LLM service for engagement"""
    global llm_service
    llm_service = service


def suggest_followup(prompt: str, answer: str, prev_followup: Optional[str] = None) -> str:
    """
    Generate contextual follow-up question for economic queries.
    
    Args:
        prompt: Original user question
        answer: Answer provided by the assistant
        prev_followup: Previously suggested follow-up (to avoid repeats)
    
    Returns:
        Follow-up question string (max 120 chars)
    """
    if not llm_service:
        logger.warning("LLM service not set for engagement")
        return _fallback_followup(prompt, answer)
    
    try:
        # Extract key context from answer (first 500 chars)
        context = answer[:500] if len(answer) > 500 else answer
        
        # Build prompt for follow-up generation
        system_msg = """You are an economics data analyst helping users explore Moldova economic data.
Generate ONE insightful follow-up question that helps the user dive deeper.

Focus on:
- Comparisons (country A vs B, year over year, product categories)
- Breakdowns (by month, transport mode, origin country)
- Correlations (tariff rates vs import volumes, seasonal patterns)
- Trends (growth rates, percentage changes)
- Related insights they might not have considered

Output ONLY the question. Max 120 characters. Make it specific and actionable."""
        
        user_msg = f"""Original question: {prompt}

Answer excerpt: {context}"""
        
        if prev_followup:
            user_msg += f"\n\nPrevious follow-up (don't repeat): {prev_followup}"
        
        user_msg += "\n\nGenerate ONE follow-up question (max 120 chars):"
        
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ]
        
        # Call LLM
        response = llm_service.chat(messages, tools=None)
        
        if isinstance(response, dict) and 'message' in response:
            followup = response['message'].get('content', '').strip()
            
            # Validate length
            if len(followup) > 120:
                followup = followup[:117] + "..."
            
            # Ensure it's a question
            if followup and not followup.endswith('?'):
                followup += "?"
            
            return followup if followup else _fallback_followup(prompt, answer)
        
        return _fallback_followup(prompt, answer)
        
    except Exception as e:
        logger.error(f"Error generating follow-up: {e}")
        return _fallback_followup(prompt, answer)


def _fallback_followup(prompt: str, answer: str) -> str:
    """
    Generate fallback follow-up using heuristics.
    
    Args:
        prompt: Original question
        answer: Answer provided
    
    Returns:
        Heuristic-based follow-up question
    """
    prompt_lower = prompt.lower()
    answer_lower = answer.lower()
    
    # Extract entities from answer
    countries = []
    for country in ['germany', 'romania', 'china', 'turkey', 'ukraine', 'russia', 'poland', 'italy']:
        if country in answer_lower:
            countries.append(country.title())
    
    products = []
    for product in ['machinery', 'pharmaceuticals', 'textiles', 'food', 'electronics', 'chemicals']:
        if product in answer_lower:
            products.append(product)
    
    # Question type detection with specific follow-ups
    if 'average' in prompt_lower or 'mean' in prompt_lower:
        if countries:
            return f"How does {countries[0]}'s import value compare to other top trading partners?"
        return "What's the trend over the past year for this metric?"
    
    elif 'what' in prompt_lower and ('country' in prompt_lower or 'origin' in prompt_lower):
        return "What products dominate imports from this country?"
    
    elif 'import' in prompt_lower and 'value' in prompt_lower:
        if products:
            return f"How have {products[0]} imports changed over time?"
        return "What's driving this import volume?"
    
    elif 'trend' in prompt_lower or 'growth' in prompt_lower:
        return "What factors explain this trend?"
    
    elif 'compare' in prompt_lower:
        return "What's the year-over-year percentage change?"
    
    elif 'highest' in prompt_lower or 'largest' in prompt_lower:
        return "What's the second highest for comparison?"
    
    elif 'month' in prompt_lower:
        return "Are there seasonal patterns in this data?"
    
    elif 'product' in prompt_lower or 'category' in prompt_lower:
        if countries:
            return f"Which countries supply most of this product?"
        return "What's the price trend for this product category?"
    
    # Default fallbacks by data availability
    if countries and len(countries) >= 2:
        return f"How do {countries[0]} and {countries[1]} compare in total trade volume?"
    
    if products:
        return f"What's the tariff rate impact on {products[0]} imports?"
    
    # Generic economics fallbacks
    generic_followups = [
        "What's the month-over-month growth rate for this metric?",
        "How does this compare to the regional average?",
        "What's the main transport mode for these imports?",
        "Are there any seasonal patterns in this data?",
        "What countries are the top 3 trading partners?"
    ]
    
    # Simple hash to pick consistent followup for same question
    index = sum(ord(c) for c in prompt_lower) % len(generic_followups)
    return generic_followups[index]
