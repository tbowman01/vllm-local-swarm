#!/bin/bash
set -e

echo "Starting Ray worker node..."

# Wait for Ray head to be available
while ! nc -z ray-head 10001; do
    echo "Waiting for Ray head to be available..."
    sleep 2
done

# Start Ray worker node
ray start --address=ray-head:10001 \
    --object-store-memory=1000000000 \
    --disable-usage-stats

echo "Ray worker node started successfully!"

# Keep the container running
tail -f /dev/null