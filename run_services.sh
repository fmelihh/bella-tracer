#!/bin/bash

echo "🚀 Starting all Bella Tracer services in the background..."

python main.py api-gateway &
python main.py order &
python main.py payment &
python main.py fraud &

echo "✅ All services are starting. Use 'jobs' to see them."
echo "   To stop them, run: pkill -f 'python main.py'"

wait
