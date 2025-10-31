"""
Econ Assistant - Self-Learning Dataset Expert
Main application entry point
"""
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import logging
from logging.handlers import RotatingFileHandler

from app.config import Config
from app.services.vector_db import VectorDBService
from app.services.llm import LLMService
from app import tools
import pandas as pd

# Initialize Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config.from_object(Config)

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Initialize services
db_service = VectorDBService(persist_dir=Config.CHROMA_PERSIST_DIR)
llm_service = LLMService(model=Config.OLLAMA_MODEL)

# Global dataset storage using a class for proper state management
class DatasetState:
    def __init__(self):
        self.dataset = None
        self.info = {}

dataset_state = DatasetState()

def load_initial_dataset():
    """Load dataset on startup"""
    # Build absolute path relative to this script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, Config.INITIAL_CSV)
    
    if not os.path.exists(csv_path):
        print(f"⚠ Initial dataset not found: {csv_path}")
        return False
    
    try:
        dataset_state.dataset = pd.read_csv(csv_path)
        
        # Index in vector DB
        db_service.index_dataframe(dataset_state.dataset, clear_existing=False)
        
        # Generate info
        dataset_state.info = {
            'rows': len(dataset_state.dataset),
            'columns': list(dataset_state.dataset.columns),
            'dtypes': {k: str(v) for k, v in dataset_state.dataset.dtypes.to_dict().items()},
            'missing': {k: int(v) for k, v in dataset_state.dataset.isnull().sum().to_dict().items()},
            'summary': dataset_state.dataset.describe().to_dict()
        }
        
        print(f"✓ Loaded initial dataset: {csv_path}")
        print(f"  {dataset_state.info['rows']} rows, {len(dataset_state.info['columns'])} columns")
        return True
    except Exception as e:
        print(f"✗ Failed to load initial dataset: {e}")
        import traceback
        traceback.print_exc()
        return False

def setup_tools():
    """Configure tools with service dependencies"""
    from app.tools import search, web, analyze, learn
    
    search.set_db_service(db_service)
    web.set_db_service(db_service)
    learn.set_db_service(db_service)
    analyze.set_dataset(dataset_state.dataset)

def setup_logging():
    """Configure application logging"""
    if not app.debug:
        os.makedirs('logs', exist_ok=True)
        file_handler = RotatingFileHandler(
            'logs/econ_assistant.log',
            maxBytes=10240,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Econ Assistant startup')

# Initialize everything BEFORE registering blueprints
def initialize_app():
    """Initialize all services and load data"""
    print("\nInitializing...")
    print("1. Testing Ollama connection...")
    llm_service.test_connection()
    
    print("2. Initializing persistent vector database...")
    db_service.initialize()
    
    print("3. Loading initial dataset...")
    load_initial_dataset()
    
    print("4. Setting up tools...")
    setup_tools()
    
    print("\n✓ Ready! The agent will:")
    print("  • Remember information across sessions")
    print("  • Auto-save web search results")
    print("  • Learn from user interactions")
    print("="*60 + "\n")

# Initialize before registering blueprints
initialize_app()

# NOW register blueprints with initialized data
from app.routes.main_routes import main_bp
from app.routes.api_routes import create_api_blueprint

app.register_blueprint(main_bp)
app.register_blueprint(
    create_api_blueprint(llm_service, db_service, lambda: dataset_state.dataset, lambda: dataset_state.info),
    url_prefix='/api'
)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    from flask import jsonify
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f'Server Error: {error}')
    from flask import jsonify
    return jsonify({'error': 'Internal server error'}), 500

def validate_production_config():
    """Validate critical configuration before starting"""
    import sys
    errors = []
    warnings = []
    
    # Critical checks
    if Config.SECRET_KEY == 'dev-secret-key-change-in-production':
        if not Config.DEBUG:
            errors.append("SECRET_KEY must be changed for production deployment")
        else:
            warnings.append("SECRET_KEY using default dev value (OK for development)")
    
    if Config.LANGCHAIN_TRACING_V2 == 'true' and not Config.LANGCHAIN_API_KEY:
        warnings.append("LANGCHAIN_TRACING_V2 enabled but LANGCHAIN_API_KEY missing - tracing will fail")
    
    # Environment-specific checks
    if not Config.DEBUG:
        if not os.getenv('OLLAMA_HOST'):
            warnings.append("OLLAMA_HOST not set - using default localhost:11434")
        
        if Config.RATELIMIT_STORAGE_URL == 'memory://':
            warnings.append("Using in-memory rate limiting - not suitable for multi-worker deployments")
    
    # Display results
    if errors:
        print("\n" + "="*60)
        print("❌ CONFIGURATION ERRORS - Cannot start")
        print("="*60)
        for err in errors:
            print(f"  ✗ {err}")
        print("\nFix these issues and try again.")
        print("="*60 + "\n")
        sys.exit(1)
    
    if warnings:
        print("\n⚠️  Configuration Warnings:")
        for warn in warnings:
            print(f"  • {warn}")

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🤖 Econ Assistant - Self-Learning Dataset Expert")
    print("="*60)
    
    # Validate configuration
    validate_production_config()
    
    # Check LangSmith
    if Config.LANGCHAIN_API_KEY:
        print(f"✅ LangSmith tracing enabled")
        print(f"   Project: {Config.LANGCHAIN_PROJECT}")
        print(f"   Dashboard: https://smith.langchain.com/")
    else:
        print("⚠ LangSmith tracing disabled")
    
    setup_logging()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
