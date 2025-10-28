"""LLM service for Ollama integration"""
from typing import List, Dict, Any

try:
    from langsmith import traceable
    USE_LANGSMITH = True
except:
    USE_LANGSMITH = False
    def traceable(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

class LLMService:
    def __init__(self, model: str = "mistral"):
        self.model = model
        
    def test_connection(self) -> bool:
        """Test Ollama connection"""
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
    
    @traceable(name="ollama_chat", run_type="llm")
    def chat(self, messages: List[Dict], tools: List[Dict] = None) -> Dict[str, Any]:
        """Query Ollama with tool calling capability"""
        try:
            import ollama
            
            response = ollama.chat(
                model=self.model,
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
