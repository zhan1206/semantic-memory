# Build
docker build -t semantic-memory .

# Run API server
docker run -d \
  --name semantic-memory \
  -p 8765:8765 \
  -v ~/.qclaw/data:/data \
  semantic-memory

# Run CLI
docker run --rm \
  -v ~/.qclaw/data:/data \
  semantic-memory \
  python scripts/run.py stats

# Watch logs
docker logs -f semantic-memory

# Stop
docker stop semantic-memory
docker rm semantic-memory
