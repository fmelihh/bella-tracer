

up:
	echo "🚀 Starting all Bella Tracer services in the background..."

	uv run api_gateway &
	uv run order &
	uv run payment &
	uv run fraud &

	echo "✅ All services are starting. Use 'jobs' to see them."
	echo "   To stop them, run: pkill -f 'python main.py'"

	wait


# sudo kill -9 $(sudo lsof -t -i:8000) && sudo kill -9 $(sudo lsof -t -i:8001) && sudo kill -9 $(sudo lsof -t -i:8002) && sudo kill -9 $(sudo lsof -t -i:8003)
