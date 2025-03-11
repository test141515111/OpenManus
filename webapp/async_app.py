"""Async web application for OpenManus with browser screenshot sharing and video recording"""
import os
import json
import time
import asyncio
import base64
from pathlib import Path
from quart import Quart, render_template, request, jsonify, send_from_directory
import socketio
from app.utils.config import load_config

# Create Quart app
app = Quart(__name__, template_folder='templates', static_folder='static')

# Create Socket.IO server
sio = socketio.AsyncServer(async_mode='asgi')
socket_app = socketio.ASGIApp(sio, app)

# Global variables
manus_agent = None
browser_tool = None
browser_screenshots = []
browser_videos = []
current_task = None
task_results = None
task_status = "idle"  # idle, running, completed, failed
task_lock = asyncio.Lock()

async def initialize_manus():
    """Initialize the Manus agent with configuration"""
    try:
        # Dynamically import Manus to avoid circular imports
        from app.agent.manus import Manus
        
        config = load_config()
        return Manus(config=config)
    except Exception as e:
        print(f"Error initializing Manus: {e}")
        raise

async def initialize_browser_tool():
    """Initialize the browser tool"""
    try:
        # Dynamically import BrowserTool to avoid circular imports
        from webapp.browser_tool import BrowserTool
        
        # Initialize with endpoints for sharing screenshots and videos
        browser_tool = BrowserTool(
            screenshot_endpoint="http://localhost:8080/api/browser_screenshot",
            video_endpoint="http://localhost:8080/api/browser_video"
        )
        return browser_tool
    except Exception as e:
        print(f"Error initializing BrowserTool: {e}")
        raise

@app.route('/')
async def index():
    """Render the main page"""
    return await render_template('index.html')

@app.route('/static/<path:path>')
async def serve_static(path):
    """Serve static files"""
    return await send_from_directory('static', path)

@app.route('/api/submit_task', methods=['POST'])
async def http_submit_task():
    """Submit a task to the Manus agent via HTTP"""
    global manus_agent, browser_tool, current_task, task_status, browser_screenshots, browser_videos, task_results
    
    # Reset previous task data
    browser_screenshots = []
    browser_videos = []
    task_results = None
    
    data = await request.get_json()
    query = data.get('query', '')
    
    if not query:
        return jsonify({"status": "error", "message": "タスクや質問を入力してください"}), 400
    
    # Initialize Manus if not already initialized
    if manus_agent is None:
        try:
            manus_agent = await initialize_manus()
        except Exception as e:
            return jsonify({"status": "error", "message": f"Manusの初期化に失敗しました: {str(e)}"}), 500
    
    # Initialize browser tool if not already initialized
    if browser_tool is None:
        try:
            browser_tool = await initialize_browser_tool()
        except Exception as e:
            return jsonify({"status": "error", "message": f"ブラウザツールの初期化に失敗しました: {str(e)}"}), 500
    
    current_task = query
    task_status = "running"
    
    # Notify clients that task is running
    await sio.emit('task_update', {
        'status': task_status,
        'task': current_task
    })
    
    # Start task in a background task
    asyncio.create_task(run_manus_task(query))
    
    return jsonify({"status": "success", "message": "タスクが正常に送信されました"})

async def run_manus_task(query):
    """Run the Manus task asynchronously"""
    global manus_agent, browser_tool, task_status, task_results
    
    async with task_lock:
        try:
            # Initialize Manus if not already initialized
            if manus_agent is None:
                manus_agent = await initialize_manus()
                
            # Initialize browser tool if not already initialized
            if browser_tool is None:
                browser_tool = await initialize_browser_tool()
            
            # Run the Manus agent with the query
            result = await manus_agent.run(query)
            task_results = result
            task_status = "completed"
            
            # Notify clients that task is complete
            await sio.emit('task_update', {
                'status': task_status,
                'task': query,
                'results': task_results
            })
        except Exception as e:
            print(f"Error running task: {e}")
            task_results = {"error": str(e)}
            task_status = "failed"
            
            # Notify clients of failure
            await sio.emit('task_update', {
                'status': task_status,
                'task': query,
                'error': str(e)
            })

@app.route('/api/task_status', methods=['GET'])
async def get_task_status():
    """Get the status of the current task"""
    global task_status, current_task, browser_screenshots, browser_videos, task_results
    
    response = {
        "status": task_status,
        "task": current_task,
        "screenshots": browser_screenshots,
        "videos": browser_videos,
        "results": task_results
    }
    
    return jsonify(response)

@app.route('/api/browser_screenshot', methods=['POST'])
async def add_browser_screenshot():
    """Add a browser screenshot (called by the Manus agent)"""
    global browser_screenshots
    
    data = await request.get_json()
    screenshot = data.get('screenshot', '')
    
    if screenshot:
        # Store the screenshot (base64 encoded)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        screenshot_data = {
            "timestamp": timestamp,
            "data": screenshot
        }
        
        browser_screenshots.append(screenshot_data)
        
        # Notify clients of new screenshot
        await sio.emit('new_screenshot', screenshot_data)
        
        return jsonify({"status": "success"})
    
    return jsonify({"status": "error", "message": "スクリーンショットが提供されていません"}), 400

@app.route('/api/browser_video', methods=['POST'])
async def add_browser_video():
    """Add a browser video (called by the Manus agent)"""
    global browser_videos
    
    data = await request.get_json()
    video = data.get('video', '')
    
    if video:
        # Store the video (base64 encoded)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        video_data = {
            "timestamp": timestamp,
            "data": video
        }
        
        browser_videos.append(video_data)
        
        # Notify clients of new video
        await sio.emit('new_video', video_data)
        
        return jsonify({"status": "success"})
    
    return jsonify({"status": "error", "message": "動画が提供されていません"}), 400

# Socket.IO event handlers
@sio.event
async def connect(sid, environ):
    """Handle client connection"""
    print(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    """Handle client disconnection"""
    print(f"Client disconnected: {sid}")

@sio.event
async def submit_task(sid, data):
    """Handle task submission from Socket.IO client"""
    global current_task, task_status
    
    query = data.get('query', '')
    if not query:
        await sio.emit('task_update', {
            'status': 'error',
            'error': 'タスクや質問を入力してください'
        }, room=sid)
        return
    
    # Reset previous task data
    global browser_screenshots, browser_videos, task_results
    browser_screenshots = []
    browser_videos = []
    task_results = None
    
    current_task = query
    task_status = "running"
    
    # Notify clients that task is running
    await sio.emit('task_update', {
        'status': task_status,
        'task': current_task
    })
    
    # Start task in a separate task
    asyncio.create_task(run_manus_task(query))

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(socket_app, host='0.0.0.0', port=8080)

# Additional Socket.IO event handlers for task status updates
@sio.event
async def request_task_status(sid):
    """Handle client request for task status"""
    global task_status, current_task, browser_screenshots, browser_videos, task_results
    
    response = {
        "status": task_status,
        "task": current_task,
        "screenshots": browser_screenshots,
        "videos": browser_videos,
        "results": task_results
    }
    
    await sio.emit('task_status_update', response, room=sid)

@sio.event
async def request_screenshots(sid):
    """Handle client request for screenshots"""
    global browser_screenshots
    
    await sio.emit('screenshots_update', {"screenshots": browser_screenshots}, room=sid)

@sio.event
async def request_videos(sid):
    """Handle client request for videos"""
    global browser_videos
    
    await sio.emit('videos_update', {"videos": browser_videos}, room=sid)
