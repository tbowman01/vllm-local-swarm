#!/bin/bash
set -e

echo "Starting Ray head node..."

# Wait for Redis to be available
while ! nc -z redis 6379; do
    echo "Waiting for Redis to be available..."
    sleep 2
done

# Start Ray head node
ray start --head \
    --port=6379 \
    --dashboard-host=0.0.0.0 \
    --dashboard-port=8265 \
    --object-store-memory=1000000000 \
    --disable-usage-stats \
    --include-dashboard=true

echo "Ray head node started successfully!"

# Keep the container running
tail -f /dev/null