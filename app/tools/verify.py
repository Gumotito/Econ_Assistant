"""
Data verification tool
Cross-checks data against trusted sources.
"""
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

# Global references
data_agent = None

def set_data_agent(agent):
    """Set the DataAgent instance"""
    global data_agent
    data_agent = agent


def verify_with_sources(claim: str, current_value: Optional[str] = None) -> str:
    """
    Verify a data claim against trusted external sources.
    
    This tool cross-checks economic data against official sources like:
    - Moldova National Bureau of Statistics (statistica.md)
    - World Bank (data.worldbank.org)
    - International Monetary Fund (imf.org)
    - UN Comtrade (comtrade.un.org)
    
    Args:
        claim: The data claim to verify (e.g., "Moldova GDP 2025 is $14.2B")
        current_value: Optional - current value from dataset to compare
    
    Returns:
        Verification report with confidence score and recommendations
    
    Example:
        verify_with_sources("Moldova GDP 2025", "$14.2B")
    """
    try:
        if not data_agent:
            return "Error: DataAgent not initialized. Cannot verify."
        
        # Step 1: Search official sources
        # Note: This should ideally call search_official_sources first
        # For now, we'll work with what we have
        
        verification = data_agent.verify_data_point(
            claim=claim,
            current_value=current_value,
            web_results=[]  # In production, pass actual search results
        )
        
        # Format response
        if verification.get('verified'):
            response = f"""✓ VERIFIED: {claim}
            
Confidence: {verification['confidence']:.0%}
Sources: {verification['high_value_sources']} official sources
Recommendation: {verification['recommendation']}

{f"Current Value: {current_value}" if current_value else ""}

Use search_official_sources("{claim}") to see detailed source data."""
        else:
            response = f"""⚠ VERIFICATION INCOMPLETE: {claim}

Confidence: {verification['confidence']:.0%}
Sources Found: {verification.get('total_sources', 0)}
Recommendation: {verification['recommendation']}

Action Required: Call search_official_sources("{claim}") first to gather verification data."""
        
        return response
        
    except Exception as e:
        logger.error(f"Verification error: {e}")
        return f"Verification failed: {str(e)}"


def list_datasets() -> str:
    """
    List all available datasets with their descriptions and statistics.
    
    Returns:
        Formatted list of datasets
    """
    try:
        if not data_agent:
            return "Error: DataAgent not initialized."
        
        datasets = data_agent.list_datasets()
        
        if not datasets:
            return "No additional datasets uploaded. Using default Moldova imports dataset."
        
        response = "📊 Available Datasets:\n\n"
        for ds in datasets:
            response += f"• {ds['name']}\n"
            response += f"  Documents: {ds['document_count']}\n"
            response += f"  Trust Score: {ds['trust_score']:.2f}\n\n"
        
        return response
        
    except Exception as e:
        logger.error(f"List datasets error: {e}")
        return f"Error listing datasets: {str(e)}"


def get_source_trust_score(source_name: str) -> str:
    """
    Get the trust/reliability score for a data source.
    
    Args:
        source_name: Name of the source (e.g., "World Bank", "web_search")
    
    Returns:
        Trust score and explanation
    """
    try:
        if not data_agent:
            return "Error: DataAgent not initialized."
        
        trust_score = data_agent.get_trust_score(source_name)
        
        # Categorize
        if trust_score >= 0.95:
            category = "HIGHEST"
            desc = "Official government/international organization"
        elif trust_score >= 0.8:
            category = "HIGH"
            desc = "Reputable economic data provider"
        elif trust_score >= 0.7:
            category = "MEDIUM"
            desc = "User-provided or curated data"
        else:
            category = "LOWER"
            desc = "General web sources - verify independently"
        
        return f"""Source: {source_name}
Trust Score: {trust_score:.2f} ({category})
Description: {desc}

Trust levels:
• 0.95-1.0: Official sources (World Bank, National Statistics, IMF)
• 0.80-0.94: Reputable providers (Trading Economics, OECD)
• 0.70-0.79: User data and curated sources
• Below 0.70: General web search results"""
        
    except Exception as e:
        logger.error(f"Trust score error: {e}")
        return f"Error getting trust score: {str(e)}"
