"""Main routes (HTML pages)"""
from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Homepage"""
    return render_template('index.html')

@main_bp.route('/health')
def health():
    """Health check endpoint"""
    from flask import jsonify
    return jsonify({'status': 'healthy'})
