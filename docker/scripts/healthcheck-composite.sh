#!/bin/bash
# Health check script for composite container

# Check all three services
curl -f http://localhost:8005/health || exit 1
curl -f http://localhost:8004/health || exit 1  
curl -f http://localhost:8003/health || exit 1

echo "All services healthy"
exit 0