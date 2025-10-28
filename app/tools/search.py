"""Search dataset and knowledge base"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..services.vector_db import VectorDBService

try:
    from langsmith import traceable
except:
    def traceable(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

# Global reference (set by main app)
db_service = None

def set_db_service(service):
    global db_service
    db_service = service

@traceable(name="search_dataset", run_type="tool")
def search_dataset(query: str) -> str:
    """Search dataset and knowledge base using RAG"""
    if not db_service:
        return "Dataset not indexed yet"
    
    results = db_service.search(query, n_results=5)
    
    if results['documents'] and results['documents'][0]:
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
