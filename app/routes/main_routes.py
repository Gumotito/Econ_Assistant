"""Main routes (HTML pages)"""
from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Homepage"""
    return render_template('index.html')

@main_bp.route('/health')
def health():
    """
    Comprehensive health check endpoint for monitoring.
    Checks all critical components: Ollama, ChromaDB, dataset.
    """
    from flask import jsonify
    from datetime import datetime
    from run import llm_service, db_service, dataset_state
    
    checks = {}
    all_healthy = True
    
    # Check Ollama/LLM service
    try:
        if hasattr(llm_service, 'circuit_open') and llm_service.circuit_open:
            checks['ollama'] = {'status': 'unhealthy', 'message': 'Circuit breaker open'}
            all_healthy = False
        else:
            checks['ollama'] = {'status': 'healthy', 'model': llm_service.model}
    except Exception as e:
        checks['ollama'] = {'status': 'error', 'message': str(e)}
        all_healthy = False
    
    # Check ChromaDB
    try:
        if db_service.health_check():
            doc_count = db_service.collection.count() if db_service.collection else 0
            checks['chromadb'] = {'status': 'healthy', 'documents': doc_count}
        else:
            checks['chromadb'] = {'status': 'unhealthy', 'message': 'Connection failed'}
            all_healthy = False
    except Exception as e:
        checks['chromadb'] = {'status': 'error', 'message': str(e)}
        all_healthy = False
    
    # Check dataset
    try:
        if dataset_state.dataset is not None and not dataset_state.dataset.empty:
            checks['dataset'] = {
                'status': 'healthy',
                'rows': len(dataset_state.dataset),
                'columns': len(dataset_state.dataset.columns)
            }
        else:
            checks['dataset'] = {'status': 'warning', 'message': 'No dataset loaded'}
            # Not critical - don't set all_healthy = False
    except Exception as e:
        checks['dataset'] = {'status': 'error', 'message': str(e)}
    
    # Overall status
    status_code = 200 if all_healthy else 503
    
    return jsonify({
        'status': 'healthy' if all_healthy else 'degraded',
        'timestamp': datetime.now().isoformat(),
        'checks': checks
    }), status_code

@main_bp.route('/metrics')
def metrics():
    """
    Get application metrics including cache statistics.
    Useful for monitoring performance and cache hit rates.
    """
    from flask import jsonify
    from app.services.cache import get_forecast_cache, get_search_cache
    from datetime import datetime
    
    try:
        forecast_cache = get_forecast_cache()
        search_cache = get_search_cache()
        
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'caches': {
                'forecast': forecast_cache.stats(),
                'search': search_cache.stats()
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
