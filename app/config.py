"""Application configuration"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # Data
    DATA_DIR = os.getenv('DATA_DIR', 'data')
    INITIAL_CSV = os.getenv('INITIAL_CSV', 'test_moldova_imports_2025.csv')
    CHROMA_PERSIST_DIR = os.getenv('CHROMA_PERSIST_DIR', 'chroma_db')
    
    # LLM
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5:14b')
    MAX_QUERY_LENGTH = int(os.getenv('MAX_QUERY_LENGTH', 5000))
    MAX_ITERATIONS = int(os.getenv('MAX_ITERATIONS', 3))
    
    # LangSmith
    LANGCHAIN_API_KEY = os.getenv('LANGCHAIN_API_KEY')
    LANGCHAIN_TRACING_V2 = os.getenv('LANGCHAIN_TRACING_V2', 'true')
    LANGCHAIN_PROJECT = os.getenv('LANGCHAIN_PROJECT', 'econ-assistant')
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.getenv('REDIS_URL', 'memory://')
    RATELIMIT_ENABLED = True
