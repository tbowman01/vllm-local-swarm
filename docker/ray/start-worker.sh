#!/bin/bash

# Ray Worker Node Startup Script

set -e

echo "Starting Ray Worker Node..."

# Wait for Ray head to be available
echo "Waiting for Ray head node..."
until ray status --address=${RAY_HEAD_ADDRESS} > /dev/null 2>&1; do
  echo "Ray head is unavailable - sleeping"
  sleep 5
done
echo "Ray head is ready!"

# Join the Ray cluster
echo "Joining Ray cluster..."
ray start \
  --address=${RAY_HEAD_ADDRESS} \
  --num-cpus=${RAY_NUM_CPUS:-2} \
  --num-gpus=${RAY_NUM_GPUS:-0} \
  --object-store-memory=${RAY_OBJECT_STORE_MEMORY:-500000000} \
  --disable-usage-stats \
  --verbose

echo "Ray worker joined cluster successfully!"

# Start agent processes
echo "Starting agent processes..."
cd /app
python -m ray.agents &

# Keep the container running and monitor Ray
echo "Monitoring Ray worker..."
while true; do
  if ! ray status > /dev/null 2>&1; then
    echo "Ray worker disconnected! Reconnecting..."
    ray stop --force
    sleep 5
    ray start \
      --address=${RAY_HEAD_ADDRESS} \
      --num-cpus=${RAY_NUM_CPUS:-2} \
      --num-gpus=${RAY_NUM_GPUS:-0} \
      --object-store-memory=${RAY_OBJECT_STORE_MEMORY:-500000000} \
      --disable-usage-stats \
      --verbose
  fi
  sleep 30
done