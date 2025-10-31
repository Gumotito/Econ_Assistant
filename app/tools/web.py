"""Web search tool with TTL caching"""
import requests
import time
from functools import lru_cache, wraps

try:
    from langsmith import traceable
except:
    def traceable(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

# Global reference
db_service = None

def set_db_service(service):
    global db_service
    db_service = service


def ttl_cache(ttl_seconds=900, maxsize=256):
    """
    Time-To-Live cache decorator.
    Caches function results for ttl_seconds, then expires.
    
    Args:
        ttl_seconds: Cache lifetime in seconds (default: 900 = 15 minutes)
        maxsize: Maximum number of cached entries (default: 256)
    """
    def decorator(func):
        cached_func = lru_cache(maxsize=maxsize)(func)
        cached_func.cache_timestamps = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            current_time = time.time()
            
            # Check if expired
            if key in cached_func.cache_timestamps:
                if current_time - cached_func.cache_timestamps[key] > ttl_seconds:
                    # Expired - clear cache
                    cached_func.cache_clear()
                    cached_func.cache_timestamps.clear()
            
            # Call cached function
            result = cached_func(*args, **kwargs)
            
            # Update timestamp
            cached_func.cache_timestamps[key] = current_time
            
            return result
        
        wrapper.cache_clear = cached_func.cache_clear
        wrapper.cache_info = cached_func.cache_info
        
        return wrapper
    return decorator

# Trusted data sources for Moldova economics
TRUSTED_SOURCES = {
    'high_value': [
        'statistica.md',           # Moldova National Bureau of Statistics
        'data.worldbank.org',      # World Bank
        'comtrade.un.org',         # UN Comtrade
        'imf.org',                 # International Monetary Fund
        'bnm.md',                  # National Bank of Moldova
    ],
    'medium_value': [
        'tradingeconomics.com',
        'ceicdata.com',
        'europa.eu/eurostat',
        'oecd.org',
    ]
}


@ttl_cache(ttl_seconds=900, maxsize=256)  # Cache for 15 minutes
@traceable(name="web_search", run_type="tool")
def web_search(query: str) -> str:
    """
    Search web using DuckDuckGo and save results (with 15-min cache).
    
    NOTE: This is a FALLBACK tool. For Moldova economics data, use search_official_sources() first!
    This tool should only be used when official sources don't have the answer.
    """
    try:
        # Auto-add Moldova context if it's an economic query without country specified
        economic_keywords = ['GDP', 'export', 'import', 'economy', 'inflation', 'trade', 
                           'growth', 'debt', 'budget', 'tariff', 'currency', 'exchange rate']
        
        has_country = any(country.lower() in query.lower() for country in 
                         ['Moldova', 'Ukraine', 'Romania', 'Russia', 'USA', 'US', 'EU', 
                          'Germany', 'Poland', 'China', 'United States'])
        
        has_economic_term = any(keyword.lower() in query.lower() for keyword in economic_keywords)
        
        # If it's an economic query without a country, assume Moldova
        if has_economic_term and not has_country:
            query = f"Moldova {query}"
            
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
        
        # Save to knowledge base
        if db_service and result_text and result_text != "No results found":
            db_service.add_knowledge(
                content=f"Query: {query}\nAnswer: {result_text}",
                source="web_search",
                metadata={"query": query, "trust_score": 0.6}
            )
        
        return result_text
    except Exception as e:
        return f"Search error: {str(e)}"


@ttl_cache(ttl_seconds=1800, maxsize=128)  # Cache for 30 minutes (official data changes slowly)
@traceable(name="search_official_sources", run_type="tool")
def search_official_sources(query: str) -> str:
    """
    Search only official/trusted sources for Moldova economics data.
    Prioritizes: National Statistics, World Bank, IMF, UN Comtrade.
    
    Args:
        query: Search query (e.g., "Moldova GDP 2025")
    
    Returns:
        Formatted results from trusted sources with source attribution
    """
    try:
        results = []
        
        # Search high-value sources first
        for site in TRUSTED_SOURCES['high_value']:
            try:
                # Site-specific search
                site_query = f"site:{site} {query}"
                url = f"https://api.duckduckgo.com/?q={site_query}&format=json"
                response = requests.get(url, timeout=5)
                data = response.json()
                
                result_text = ""
                if data.get('AbstractText'):
                    result_text = data['AbstractText']
                elif data.get('RelatedTopics'):
                    topics = []
                    for topic in data['RelatedTopics'][:2]:  # Limit to 2 per source
                        if isinstance(topic, dict) and 'Text' in topic:
                            topics.append(topic['Text'])
                    result_text = " | ".join(topics) if topics else ""
                
                if result_text:
                    results.append(f"[{site}] {result_text}")
                    
                    # Save with high trust score
                    if db_service:
                        db_service.add_knowledge(
                            content=f"Query: {query}\nSource: {site}\nAnswer: {result_text}",
                            source=site,
                            metadata={
                                "query": query,
                                "trust_score": 1.0,
                                "source_type": "official"
                            }
                        )
                
            except Exception as e:
                continue  # Skip failed sources
        
        # If no high-value results, try medium-value sources
        if not results:
            for site in TRUSTED_SOURCES['medium_value']:
                try:
                    site_query = f"site:{site} {query}"
                    url = f"https://api.duckduckgo.com/?q={site_query}&format=json"
                    response = requests.get(url, timeout=5)
                    data = response.json()
                    
                    if data.get('AbstractText'):
                        results.append(f"[{site}] {data['AbstractText']}")
                        break  # Found one medium-value result, that's enough
                        
                except Exception:
                    continue
        
        # Format results
        if results:
            formatted = "\n\n".join(results)
            return f"✓ Official sources found:\n\n{formatted}"
        else:
            # Fallback to general search
            fallback = web_search(query)
            return f"⚠ No official sources found. General search:\n\n{fallback}"
            
    except Exception as e:
        return f"Official search error: {str(e)}"
