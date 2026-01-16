#!/bin/bash
# Kill any process on port 8000
echo "Killing processes on port 8000..."
fuser -k 8000/tcp || true
lsof -t -i:8000 | xargs -r kill -9 || true
# Also kill by name
pkill -9 -f "python app.py" || true

sleep 2

# Start server in background
echo "Starting server..."
/opt/mro_dash/.venv/bin/python app.py > debug.log 2>&1 &
PID=$!
echo "Server started with PID $PID"

# Wait for server to be ready
sleep 3

# Check if running
if ps -p $PID > /dev/null; then
   echo "Server is running."
   curl -v http://localhost:8000/api/commands > commands_output.json
   head -n 20 debug.log
else
   echo "Server failed to start."
   cat debug.log
fi
