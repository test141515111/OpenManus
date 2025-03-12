#!/usr/bin/env python3
"""
OpenManus Web UI Application
"""
import os
import sys
import asyncio
import json
from pathlib import Path
from quart import Quart, render_template, request, jsonify, redirect, url_for
from quart_cors import cors
import socketio

# Add the parent directory to the path so we can import from app
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Create the Quart app
app = Quart(__name__)
app = cors(app, allow_origin="*")

# Create the Socket.IO server
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio, app)

# Global variables
manus_agent = None
current_task = None
task_status = "idle"
task_result = None
screenshots = []

# Initialize Manus agent
async def initialize_manus():
    """Initialize the Manus agent."""
    try:
        from app.agent.manus import Manus
        
        # Initialize the agent
        agent = Manus()
        return agent
    except Exception as e:
        print(f"Error initializing Manus agent: {e}")
        return None

# Socket.IO events
@sio.event
async def connect(sid, environ):
    """Handle client connection."""
    print(f"Client connected: {sid}")
    await sio.emit('status_update', {
        'status': task_status,
        'current_task': current_task,
        'result': task_result,
        'screenshots': screenshots
    }, room=sid)

@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    print(f"Client disconnected: {sid}")

@sio.event
async def submit_task(sid, data):
    """Handle task submission."""
    global current_task, task_status, task_result, screenshots, manus_agent
    
    try:
        # Get the task from the data
        task = data.get('query', '')
        
        if not task:
            await sio.emit('error', {'message': 'タスクを入力してください'}, room=sid)
            return
        
        # Initialize Manus agent if needed
        if manus_agent is None:
            print("Initializing Manus agent")
            manus_agent = await initialize_manus()
            
        # Make sure the agent is initialized
        if manus_agent is None:
            await sio.emit('error', {'message': 'Manusエージェントの初期化に失敗しました'}, room=sid)
            return
        
        # Update task status
        current_task = task
        task_status = "running"
        task_result = None
        screenshots = []
        
        # Emit status update
        await sio.emit('status_update', {
            'status': task_status,
            'current_task': current_task,
            'result': task_result,
            'screenshots': screenshots
        }, room=sid)
        
        # Execute the task
        print(f"Executing task: {task}")
        result = await manus_agent.run(task)
        
        # Update task status
        task_status = "completed"
        task_result = result
        
        # Get screenshots if available
        try:
            browser_tool = manus_agent.available_tools.get_tool("browser_use")
            if browser_tool and hasattr(browser_tool, "get_screenshots"):
                screenshots = await browser_tool.get_screenshots()
        except Exception as e:
            print(f"Error getting screenshots: {e}")
        
        # Emit status update
        await sio.emit('status_update', {
            'status': task_status,
            'current_task': current_task,
            'result': task_result,
            'screenshots': screenshots
        }, room=sid)
        
    except Exception as e:
        print(f"Error executing task: {e}")
        task_status = "error"
        await sio.emit('error', {'message': f'タスクの実行中にエラーが発生しました: {str(e)}'}, room=sid)
        await sio.emit('status_update', {
            'status': task_status,
            'current_task': current_task,
            'result': None,
            'screenshots': screenshots
        }, room=sid)

# Routes
@app.route('/')
async def index():
    """Render the index page."""
    return await render_template('index.html')

@app.route('/search')
async def search():
    """Render the search page."""
    return await render_template('search/index.html')

@app.route('/api/task', methods=['POST'])
async def api_submit_task():
    """API endpoint for submitting tasks."""
    global current_task, task_status, task_result, screenshots, manus_agent
    
    try:
        data = await request.get_json()
        
        # Get the task from the data
        task = data.get('task', '')
        
        if not task:
            return jsonify({"status": "error", "message": "タスクを入力してください"}), 400
        
        # Initialize Manus agent if needed
        if manus_agent is None:
            print("Initializing Manus agent")
            manus_agent = await initialize_manus()
            
        # Make sure the agent is initialized
        if manus_agent is None:
            return jsonify({"status": "error", "message": "Manusエージェントの初期化に失敗しました"}), 500
        
        # Update task status
        current_task = task
        task_status = "running"
        task_result = None
        screenshots = []
        
        # Execute the task in the background
        asyncio.create_task(execute_task(task))
        
        return jsonify({"status": "success", "message": "タスクが送信されました"})
        
    except Exception as e:
        print(f"Error submitting task: {e}")
        return jsonify({"status": "error", "message": f"タスクの送信中にエラーが発生しました: {str(e)}"}), 500

async def execute_task(task):
    """Execute a task in the background."""
    global task_status, task_result, screenshots, manus_agent
    
    try:
        # Execute the task
        print(f"Executing task: {task}")
        result = await manus_agent.run(task)
        
        # Update task status
        task_status = "completed"
        task_result = result
        
        # Get screenshots if available
        try:
            browser_tool = manus_agent.available_tools.get_tool("browser_use")
            if browser_tool and hasattr(browser_tool, "get_screenshots"):
                screenshots = await browser_tool.get_screenshots()
        except Exception as e:
            print(f"Error getting screenshots: {e}")
        
        # Emit status update to all clients
        await sio.emit('status_update', {
            'status': task_status,
            'current_task': current_task,
            'result': task_result,
            'screenshots': screenshots
        })
        
    except Exception as e:
        print(f"Error executing task: {e}")
        task_status = "error"
        await sio.emit('error', {'message': f'タスクの実行中にエラーが発生しました: {str(e)}'})
        await sio.emit('status_update', {
            'status': task_status,
            'current_task': current_task,
            'result': None,
            'screenshots': screenshots
        })

@app.route('/api/task_status', methods=['GET'])
async def api_task_status():
    """API endpoint for getting task status."""
    return jsonify({
        'status': task_status,
        'current_task': current_task,
        'result': task_result,
        'screenshots': screenshots
    })

# Register web search routes
@app.before_serving
async def setup_web_search_routes():
    """Set up web search routes before serving."""
    try:
        from webapp.web_search_ui import register_web_search_routes
        await register_web_search_routes(app)
    except Exception as e:
        print(f"Error registering web search routes: {e}")

# Add a simple status endpoint
@app.route('/status')
async def status():
    """Return a simple status message."""
    return jsonify({
        "status": "ok",
        "message": "OpenManus Web UI is running"
    })

if __name__ == '__main__':
    import hypercorn.asyncio
    from hypercorn.config import Config as HyperConfig
    
    config = HyperConfig()
    config.bind = ["0.0.0.0:8081"]
    config.use_reloader = True
    
    asyncio.run(hypercorn.asyncio.serve(socket_app, config))
