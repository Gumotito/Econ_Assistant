"""Learning tool for saving insights"""

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

@traceable(name="add_learned_info", run_type="tool")
def add_learned_info(information: str, category: str = "insight") -> str:
    """Save learned information to knowledge base"""
    if not db_service:
        return "Knowledge base not available"
    
    success = db_service.add_knowledge(
        content=information,
        source="learned",
        metadata={"category": category}
    )
    
    if success:
        return f"Successfully saved {category}: {information[:50]}..."
    return "Failed to save information"
