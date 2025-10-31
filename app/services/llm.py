"""LLM service for Ollama integration"""
from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

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
        self.failure_count = 0
        self.last_failure = None
        self.circuit_open = False
        self.circuit_threshold = 3  # Open circuit after 3 failures
        self.circuit_timeout = timedelta(minutes=5)  # Try again after 5 minutes
        
    def test_connection(self) -> bool:
        """Test Ollama connection"""
        try:
            import ollama
            models_response = ollama.list()
            
            # Handle different response formats
            if hasattr(models_response, 'models'):
                # Response is an object with models attribute
                models_list = models_response.models
                model_names = [m.model if hasattr(m, 'model') else m.get('model', 'unknown') 
                              for m in models_list]
            elif isinstance(models_response, dict) and 'models' in models_response:
                # Response is a dict with 'models' key
                model_names = [m.get('model', m.get('name', 'unknown')) 
                              for m in models_response['models']]
            else:
                model_names = ['Could not parse model list']
            
            print(f"✓ Ollama connected. Available models: {model_names}")
            
            # Verify our configured model is available
            if self.model not in model_names and not any(self.model in m for m in model_names):
                print(f"⚠ WARNING: Configured model '{self.model}' not found in available models!")
            
            return True
        except Exception as e:
            print(f"✗ Ollama error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _check_circuit_breaker(self):
        """Check if circuit breaker should block the request"""
        if self.circuit_open:
            if self.last_failure and datetime.now() - self.last_failure < self.circuit_timeout:
                raise Exception(f"Circuit breaker open - Ollama unavailable. Retry after {self.circuit_timeout.total_seconds()/60:.0f} minutes")
            else:
                # Timeout expired, try to close circuit
                logger.info("Circuit breaker timeout expired, attempting to reconnect...")
                self.circuit_open = False
                self.failure_count = 0
    
    def _record_success(self):
        """Record successful LLM call"""
        self.failure_count = 0
        self.circuit_open = False
    
    def _record_failure(self, error: Exception):
        """Record failed LLM call and potentially open circuit"""
        self.failure_count += 1
        self.last_failure = datetime.now()
        logger.error(f"LLM call failed ({self.failure_count}/{self.circuit_threshold}): {error}")
        
        if self.failure_count >= self.circuit_threshold:
            self.circuit_open = True
            logger.critical(f"Circuit breaker opened after {self.circuit_threshold} failures. Ollama appears unavailable.")
    
    @traceable(name="ollama_chat", run_type="llm")
    def chat(self, messages: List[Dict], tools: List[Dict] = None) -> Dict[str, Any]:
        """Query Ollama with tool calling capability and circuit breaker protection"""
        # Check circuit breaker first
        self._check_circuit_breaker()
        
        try:
            import ollama
            
            response = ollama.chat(
                model=self.model,
                messages=messages,
                tools=tools or [],
                stream=False
            )
            
            # Success - reset failure counter
            self._record_success()
            
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
            # Record failure and potentially open circuit
            self._record_failure(e)
            print(f"❌ LLM Error: {e}")
            return {'error': str(e)}
