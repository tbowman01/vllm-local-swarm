#!/bin/bash

# Ray Head Node Startup Script

set -e

echo "Starting Ray Head Node..."

# Wait for Redis to be available
echo "Waiting for Redis..."
until redis-cli -h redis -p 6379 ping; do
  echo "Redis is unavailable - sleeping"
  sleep 2
done
echo "Redis is ready!"

# Initialize Ray head node
echo "Initializing Ray head node..."
ray start \
  --head \
  --port=6379 \
  --redis-port=6379 \
  --object-manager-port=8076 \
  --node-manager-port=8077 \
  --dashboard-host=0.0.0.0 \
  --dashboard-port=8265 \
  --num-cpus=${RAY_NUM_CPUS:-4} \
  --num-gpus=${RAY_NUM_GPUS:-0} \
  --object-store-memory=${RAY_OBJECT_STORE_MEMORY:-1000000000} \
  --disable-usage-stats \
  --verbose

echo "Ray head node started successfully!"

# Start the SwarmCoordinator service
echo "Starting SwarmCoordinator..."
cd /app
python -m ray.coordinator &

# Keep the container running and monitor Ray
echo "Monitoring Ray cluster..."
while true; do
  if ! ray status > /dev/null 2>&1; then
    echo "Ray head node failed! Restarting..."
    ray stop --force
    sleep 5
    ray start \
      --head \
      --port=6379 \
      --redis-port=6379 \
      --object-manager-port=8076 \
      --node-manager-port=8077 \
      --dashboard-host=0.0.0.0 \
      --dashboard-port=8265 \
      --num-cpus=${RAY_NUM_CPUS:-4} \
      --num-gpus=${RAY_NUM_GPUS:-0} \
      --object-store-memory=${RAY_OBJECT_STORE_MEMORY:-1000000000} \
      --disable-usage-stats \
      --verbose
  fi
  sleep 30
done