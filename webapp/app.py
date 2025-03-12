"""
OpenManus Web UI Application
"""
import os
import sys
import asyncio
import json
import base64
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quart import Quart, render_template, request, jsonify, websocket
from quart_cors import cors
import socketio

# Global variables
manus_agent = None
current_task = None
task_status = "idle"
task_result = None
screenshots = []
video_path = None

# Create Socket.IO server
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = Quart(__name__)
app = cors(app, allow_origin="*")
socket_app = socketio.ASGIApp(sio, app)

# Initialize Manus agent
async def initialize_manus():
    """Initialize the Manus agent with necessary tools."""
    try:
        from app.agent.manus import Manus
        from app.tool.browser_use_tool import BrowserUseTool
        from app.tool.web_search_report_tool import WebSearchReportTool
        
        # Create Manus agent
        agent = Manus()
        
        # Add browser tool
        browser_tool = BrowserUseTool()
        agent.available_tools.add_tool(browser_tool)
        
        # Add web search report tool
        web_search_tool = WebSearchReportTool()
        agent.available_tools.add_tool(web_search_tool)
        
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
        'screenshots': screenshots,
        'video_path': video_path,
        'result': task_result
    }, room=sid)

@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    print(f"Client disconnected: {sid}")

@sio.event
async def submit_task(sid, data):
    """Handle task submission from client."""
    global current_task, task_status, task_result, screenshots, video_path, manus_agent
    
    try:
        # Get task query
        query = data.get('query', '')
        if not query:
            await sio.emit('error', {'message': 'タスクが空です。何か入力してください。'}, room=sid)
            return
        
        # Initialize Manus agent if needed
        if manus_agent is None:
            manus_agent = await initialize_manus()
            if manus_agent is None:
                await sio.emit('error', {'message': 'Manusエージェントの初期化に失敗しました。'}, room=sid)
                return
        
        # Update task status
        current_task = query
        task_status = "running"
        task_result = None
        screenshots = []
        video_path = None
        
        # Notify clients of status change
        await sio.emit('status_update', {
            'status': task_status,
            'current_task': current_task
        })
        
        # Execute task in background
        asyncio.create_task(execute_task(query, sid))
        
        # Return success response
        await sio.emit('task_submitted', {'message': 'タスクが送信されました。'}, room=sid)
    
    except Exception as e:
        print(f"Error submitting task: {e}")
        await sio.emit('error', {'message': f'タスクの送信中にエラーが発生しました: {str(e)}'}, room=sid)

async def execute_task(query, sid):
    """Execute task in background."""
    global task_status, task_result, screenshots, video_path, manus_agent
    
    try:
        # Execute task
        result = await manus_agent.run(query)
        
        # Update task status
        task_status = "completed"
        task_result = result
        
        # Get screenshots from browser tool
        browser_tool = manus_agent.available_tools.get_tool("browser_use")
        if browser_tool and hasattr(browser_tool, 'get_screenshots'):
            screenshots = await browser_tool.get_screenshots()
        
        # Get video path from browser tool
        if browser_tool and hasattr(browser_tool, 'get_video_path'):
            video_path = await browser_tool.get_video_path()
        
        # Notify clients of task completion
        await sio.emit('task_completed', {
            'result': result,
            'screenshots': screenshots,
            'video_path': video_path
        })
        
        # Notify clients of status change
        await sio.emit('status_update', {
            'status': task_status,
            'current_task': current_task,
            'screenshots': screenshots,
            'video_path': video_path,
            'result': task_result
        })
    
    except Exception as e:
        print(f"Error executing task: {e}")
        task_status = "error"
        task_result = f"エラー: {str(e)}"
        
        # Notify clients of error
        await sio.emit('error', {'message': f'タスクの実行中にエラーが発生しました: {str(e)}'}, room=sid)
        
        # Notify clients of status change
        await sio.emit('status_update', {
            'status': task_status,
            'current_task': current_task,
            'result': task_result
        })

# API routes
@app.route('/')
async def index():
    """Render main page."""
    return await render_template('index.html')

@app.route('/search')
async def search():
    """Render search page."""
    return await render_template('search/index.html')

@app.route('/api/task', methods=['POST'])
async def api_submit_task():
    """API endpoint for submitting tasks."""
    global current_task, task_status, task_result, screenshots, video_path, manus_agent
    
    try:
        # Get task data
        data = await request.get_json()
        task = data.get('task', '')
        
        if not task:
            return jsonify({'status': 'error', 'message': 'タスクが空です。何か入力してください。'}), 400
        
        # Initialize Manus agent if needed
        if manus_agent is None:
            manus_agent = await initialize_manus()
            if manus_agent is None:
                return jsonify({'status': 'error', 'message': 'Manusエージェントの初期化に失敗しました。'}), 500
        
        # Update task status
        current_task = task
        task_status = "running"
        task_result = None
        screenshots = []
        video_path = None
        
        # Execute task in background
        asyncio.create_task(execute_task_api(task))
        
        # Return success response
        return jsonify({'status': 'success', 'message': 'タスクが送信されました。'})
    
    except Exception as e:
        print(f"Error submitting task via API: {e}")
        return jsonify({'status': 'error', 'message': f'タスクの送信中にエラーが発生しました: {str(e)}'}), 500

async def execute_task_api(task):
    """Execute task in background for API requests."""
    global task_status, task_result, screenshots, video_path, manus_agent
    
    try:
        # Execute task
        result = await manus_agent.run(task)
        
        # Update task status
        task_status = "completed"
        task_result = result
        
        # Get screenshots from browser tool
        browser_tool = manus_agent.available_tools.get_tool("browser_use")
        if browser_tool and hasattr(browser_tool, 'get_screenshots'):
            screenshots = await browser_tool.get_screenshots()
        
        # Get video path from browser tool
        if browser_tool and hasattr(browser_tool, 'get_video_path'):
            video_path = await browser_tool.get_video_path()
        
        # Notify clients of task completion via Socket.IO
        await sio.emit('task_completed', {
            'result': result,
            'screenshots': screenshots,
            'video_path': video_path
        })
        
        # Notify clients of status change via Socket.IO
        await sio.emit('status_update', {
            'status': task_status,
            'current_task': current_task,
            'screenshots': screenshots,
            'video_path': video_path,
            'result': task_result
        })
    
    except Exception as e:
        print(f"Error executing task via API: {e}")
        task_status = "error"
        task_result = f"エラー: {str(e)}"
        
        # Notify clients of error via Socket.IO
        await sio.emit('error', {'message': f'タスクの実行中にエラーが発生しました: {str(e)}'})
        
        # Notify clients of status change via Socket.IO
        await sio.emit('status_update', {
            'status': task_status,
            'current_task': current_task,
            'result': task_result
        })

@app.route('/api/task_status', methods=['GET'])
async def api_task_status():
    """API endpoint for getting task status."""
    return jsonify({
        'status': task_status,
        'current_task': current_task,
        'screenshots': screenshots,
        'video_path': video_path,
        'result': task_result
    })

# Import and register web search routes
try:
    from webapp.web_search_ui import register_web_search_routes
    asyncio.create_task(register_web_search_routes(app))
except ImportError:
    print("Web search UI module not found. Search functionality will be disabled.")
except Exception as e:
    print(f"Error registering web search routes: {e}")

# Main entry point
if __name__ == '__main__':
    app.run(debug=True, port=8080)
