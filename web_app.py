import asyncio
import os
import logging
from flask import Flask, request, jsonify, render_template
from app.agent.xinobi import XinobiAgent
from app.llm import LLMClient
from app.tool.collection import ToolCollection
from app.tool.execute_bash import ExecuteBash
from app.tool.file_saver import FileSaver
from app.tool.python_execute import PythonExecute
from app.tool.think import Think
from app.tool.finish import Finish
from app.tool.terminate import Terminate
from app.logger import setup_logger
from app.config.config import Config, LLMConfig

# Set up logging
logger = setup_logger("xinobi_web", "INFO")

app = Flask(__name__, template_folder="templates")

# Load configuration
config = Config()
config.load()

# Check for API key in environment
api_key = os.environ.get("OPENAI_API_KEY", "")
if api_key:
    # Override API key in config
    config.llm.api_key = api_key
    logger.info("Using API key from environment variables")
else:
    # Try to get from environment if config has placeholder
    if "${" in config.llm.api_key:
        env_var = config.llm.api_key.replace("${", "").replace("}", "")
        env_value = os.environ.get(env_var)
        if env_value:
            config.llm.api_key = env_value
            logger.info(f"Using API key from environment variable {env_var}")
        else:
            logger.warning(f"Environment variable {env_var} not found. API calls will fail.")
    else:
        logger.warning("OPENAI_API_KEY not found in environment variables. Using config file.")

# Initialize LLM client
llm = LLMClient(config=config.llm)

# Initialize tools
execute_bash_tool = ExecuteBash()
file_saver_tool = FileSaver()
python_execute_tool = PythonExecute()
think_tool = Think()
finish_tool = Finish()
terminate_tool = Terminate()

# Create tool collection
tools = [
    execute_bash_tool,
    file_saver_tool,
    python_execute_tool,
    think_tool,
    finish_tool,
    terminate_tool
]

# Create agent
agent = XinobiAgent(llm, tools)

# Create a global event loop for all requests
global_loop = asyncio.new_event_loop()
asyncio.set_event_loop(global_loop)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_input = data.get('message', '')
    
    if not user_input:
        return jsonify({'error': 'No message provided'}), 400
    
    logger.info(f"Received user input: {user_input[:50]}...")
    
    try:
        # Use the global event loop to run the agent
        result = global_loop.run_until_complete(agent.run(user_input))
        
        return jsonify({
            'response': result.get('response', ''),
            'state': result.get('state', 'IDLE')
        })
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({
            'error': 'エラーが発生しました。もう一度お試しください。',
            'details': str(e)
        }), 500

@app.route('/api/reset', methods=['POST'])
def reset():
    try:
        # Reset agent state and memory
        agent.reset()
        logger.info("Agent reset")
        
        return jsonify({'status': 'success', 'message': 'Agent reset'})
    except Exception as e:
        logger.error(f"Error resetting agent: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': 'Xinobi Agent is running'}), 200

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Get port from environment or use default
    port = int(os.environ.get("PORT", 8081))
    
    logger.info(f"Starting Xinobi Agent web server on port {port}")
    
    # Run the app
    app.run(host='0.0.0.0', port=port, debug=False)
