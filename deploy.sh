#!/bin/bash
set -e

# Install dependencies
pip install -r requirements.txt
pip install -r webapp/requirements.txt

# Create config directory if it doesn't exist
mkdir -p config

# Create config.toml if it doesn't exist
if [ ! -f config/config.toml ]; then
    echo "Creating config.toml with OpenAI API key"
    cat > config/config.toml << EOT
# Global LLM configuration
[llm]
provider = "openai"
model = "gpt-4"
api_key = "${oepnai_api}"
temperature = 0.7
max_tokens = 4096

[agent]
name = "manus"
memory_enabled = true

[tools]
python_execute = true
file_saver = true
browser_use = true
google_search = true
EOT
fi

# Function to check if port is in use
check_port() {
    nc -z localhost $1 >/dev/null 2>&1
    return $?
}

# Function to find an available port
find_available_port() {
    local port=8080
    while check_port $port; do
        echo "Port $port is in use, trying next port..."
        port=$((port + 1))
        if [ $port -gt 8100 ]; then
            echo "No available ports between 8080-8100"
            return 1
        fi
    done
    echo $port
}

# Check if port 8080 is already in use
if check_port 8080; then
    echo "Port 8080 is already in use. Stopping the process..."
    PID=$(ps aux | grep "python.*run.py" | grep -v grep | awk '{print $2}')
    if [ ! -z "$PID" ]; then
        echo "Killing process $PID"
        kill -9 $PID || true
    else
        echo "Could not find process using port 8080"
        # Try to find an available port
        PORT=$(find_available_port)
        if [ $? -eq 0 ]; then
            echo "Using alternative port: $PORT"
            export OPENMANUS_PORT=$PORT
        else
            echo "Failed to find available port"
            exit 1
        fi
    fi
    sleep 2
fi

# Run the web UI
cd webapp
if [ ! -z "$OPENMANUS_PORT" ]; then
    echo "Starting OpenManus Web UI on port $OPENMANUS_PORT"
    python -c "import os; import sys; port = int(os.environ.get('OPENMANUS_PORT', 8080)); sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname('__file__'), '..'))); from webapp.async_app import socket_app; import uvicorn; uvicorn.run(socket_app, host='0.0.0.0', port=port)" &
else
    echo "Starting OpenManus Web UI on default port 8080"
    python run.py &
fi

PID=$!
echo "OpenManus Web UI started with PID: $PID"

# Determine the port for the access URL
PORT=${OPENMANUS_PORT:-8080}
echo "Access the UI at: http://localhost:$PORT"

# Wait for the application to start
sleep 3

# Check if the application is running
if ps -p $PID > /dev/null; then
    echo "Application started successfully!"
else
    echo "Failed to start the application. Check the logs for errors."
    exit 1
fi
