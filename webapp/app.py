import os
import json
import time
import threading
import base64
from flask import Flask, render_template, request, jsonify, send_from_directory
from app.agent.manus import Manus
from app.utils.config import load_config

app = Flask(__name__, template_folder='templates', static_folder='static')

# Global variables
manus_agent = None
browser_screenshots = []
current_task = None
task_results = None
task_status = "idle"  # idle, running, completed, failed

def initialize_manus():
    """Initialize the Manus agent with configuration"""
    config = load_config()
    return Manus(config=config)

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('static', path)

@app.route('/api/submit_task', methods=['POST'])
def submit_task():
    """Submit a task to the Manus agent"""
    global manus_agent, current_task, task_status, browser_screenshots, task_results
    
    # Reset previous task data
    browser_screenshots = []
    task_results = None
    
    data = request.json
    query = data.get('query', '')
    
    if not query:
        return jsonify({"status": "error", "message": "Query cannot be empty"}), 400
    
    # Initialize Manus if not already initialized
    if manus_agent is None:
        try:
            manus_agent = initialize_manus()
        except Exception as e:
            return jsonify({"status": "error", "message": f"Failed to initialize Manus: {str(e)}"}), 500
    
    current_task = query
    task_status = "running"
    
    # Start task in a separate thread
    threading.Thread(target=run_manus_task, args=(query,)).start()
    
    return jsonify({"status": "success", "message": "Task submitted successfully"})

def run_manus_task(query):
    """Run the Manus task in a separate thread"""
    global manus_agent, task_status, task_results
    
    try:
        # Run the Manus agent with the query
        result = manus_agent.run(query)
        task_results = result
        task_status = "completed"
    except Exception as e:
        task_results = {"error": str(e)}
        task_status = "failed"

@app.route('/api/task_status', methods=['GET'])
def get_task_status():
    """Get the status of the current task"""
    global task_status, current_task, browser_screenshots, task_results
    
    response = {
        "status": task_status,
        "task": current_task,
        "screenshots": browser_screenshots,
        "results": task_results
    }
    
    return jsonify(response)

@app.route('/api/browser_screenshot', methods=['POST'])
def add_browser_screenshot():
    """Add a browser screenshot (called by the Manus agent)"""
    global browser_screenshots
    
    data = request.json
    screenshot = data.get('screenshot', '')
    
    if screenshot:
        # Store the screenshot (base64 encoded)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        browser_screenshots.append({
            "timestamp": timestamp,
            "data": screenshot
        })
        
        return jsonify({"status": "success"})
    
    return jsonify({"status": "error", "message": "No screenshot provided"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
