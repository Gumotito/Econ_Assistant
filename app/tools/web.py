"""Web search tool"""
import requests

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

@traceable(name="web_search", run_type="tool")
def web_search(query: str) -> str:
    """Search web using DuckDuckGo and save results"""
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
        
        # Save to knowledge base
        if db_service and result_text and result_text != "No results found":
            db_service.add_knowledge(
                content=f"Query: {query}\nAnswer: {result_text}",
                source="web_search",
                metadata={"query": query}
            )
        
        return result_text
    except Exception as e:
        return f"Search error: {str(e)}"
