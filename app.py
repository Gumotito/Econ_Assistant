from flask import Flask, render_template, jsonify
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/hello', methods=['GET'])
def hello():
    return jsonify({'message': 'Hello from Econ_Assistant!'})

if __name__ == '__main__':
    app.run(debug=True)