#!/bin/bash

echo "🚀 Starting all Bella Tracer services in the background..."

python main.py api-gateway &
python main.py order &
python main.py payment &
python main.py fraud &

echo "✅ All services are starting. Use 'jobs' to see them."
echo "   To stop them, run: pkill -f 'python main.py'"

wait


# sudo kill -9 $(sudo lsof -t -i:8000) && sudo kill -9 $(sudo lsof -t -i:8001) && sudo kill -9 $(sudo lsof -t -i:8002) && sudo kill -9 $(sudo lsof -t -i:8003)
