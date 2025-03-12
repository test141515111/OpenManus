"""UI components for Web Search Report integration in the web interface."""
import base64
import json
import time
from typing import Dict, List, Optional

from quart import jsonify, request

# Routes for Web Search Report API
async def register_web_search_routes(app):
    """Register Web Search Report API routes with the Quart app."""
    
    @app.route('/api/web_search/report', methods=['POST'])
    async def generate_search_report():
        """Generate a web search report."""
        try:
            data = await request.get_json()
            
            # Get parameters from request
            query = data.get('query', '')
            num_results = int(data.get('num_results', 3))
            language = data.get('language', 'ja')
            include_images = data.get('include_images', True)
            
            # Validate parameters
            if not query:
                return jsonify({"status": "error", "message": "検索クエリを入力してください"}), 400
            
            if num_results < 1 or num_results > 5:
                return jsonify({"status": "error", "message": "検索結果の数は1から5の間で指定してください"}), 400
            
            # Get the Manus agent from the global context
            from webapp.app import manus_agent, initialize_manus
            
            try:
                # Initialize Manus agent if needed
                if manus_agent is None:
                    print("Initializing Manus agent for web search")
                    manus_agent = await initialize_manus()
                    
                # Make sure the agent is initialized
                if manus_agent is None:
                    return jsonify({"status": "error", "message": "Manusエージェントの初期化に失敗しました"}), 500
            except Exception as e:
                print(f"Error initializing Manus agent: {e}")
                return jsonify({"status": "error", "message": f"Manusエージェントの初期化に失敗しました: {str(e)}"}), 500
            
            # Execute the Web Search Report tool
            try:
                result = await manus_agent.available_tools.get_tool("web_search_report").execute(
                    query=query,
                    num_results=num_results,
                    language=language,
                    include_images=include_images,
                )
            except Exception as e:
                print(f"Error executing web search report tool: {e}")
                return jsonify({"status": "error", "message": f"検索の実行中にエラーが発生しました: {str(e)}"}), 500
            
            if hasattr(result, 'error') and result.error:
                return jsonify({"status": "error", "message": result.error}), 500
            
            # Return the generated report
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            
            response = {
                "status": "success",
                "message": "検索レポートが生成されました",
                "report": None,
                "query": query,
                "timestamp": timestamp
            }
            
            # Add report to response
            if hasattr(result, 'report') and result.report:
                response["report"] = result.report
            
            # Notify clients of new report via Socket.IO
            from webapp.app import sio
            await sio.emit('new_search_report', {
                "query": query,
                "timestamp": timestamp,
                "report": response["report"]
            })
            
            return jsonify(response)
            
        except Exception as e:
            return jsonify({"status": "error", "message": f"検索レポートの生成に失敗しました: {str(e)}"}), 500
