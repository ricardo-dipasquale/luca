#!/bin/bash
echo "=== DOCKER COMPOSE STATUS ==="
docker-compose ps

echo -e "\n=== LUCA CONTAINER LOGS ==="
docker logs luca-app --tail=20 2>&1 || echo "No logs available"

echo -e "\n=== CONTAINER PROCESSES ==="
docker exec luca-app ps aux 2>/dev/null || echo "Cannot access container"

echo -e "\n=== PORT STATUS ==="
ss -tlnp | grep -E ':(443|5000)' || echo "No services on ports 443/5000"

echo -e "\n=== DOCKER IMAGES ==="
docker images | grep luca

echo -e "\n=== CONTAINER INSPECT ==="
docker inspect luca-app --format='{{.State.Status}}: {{.State.Error}}' 2>/dev/null || echo "Container not found"