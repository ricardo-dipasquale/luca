# Deployment Guide

## 🚀 Production Deployment

This guide covers production deployment of the Luca system across different environments and platforms.

## 📋 Deployment Options

### 1. Docker Compose (Recommended for Small-Medium Scale)
### 2. Kubernetes (Enterprise Scale)
### 3. Cloud Platforms (AWS, GCP, Azure)
### 4. Hybrid Deployment

## 🐳 Docker Compose Deployment

### Complete Production Stack

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  # Neo4j Knowledge Graph
  neo4j:
    image: neo4j:5.26.1-enterprise
    container_name: luca-neo4j
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      - NEO4J_ACCEPT_LICENSE_AGREEMENT=yes
      - NEO4J_apoc_export_file_enabled=true
      - NEO4J_apoc_import_file_enabled=true
      - NEO4J_apoc_import_file_use__neo4j__config=true
      - NEO4JLABS_PLUGINS=["apoc","graph-data-science"]
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*,gds.*
      - NEO4J_dbms_memory_heap_initial_size=2G
      - NEO4J_dbms_memory_heap_max_size=4G
      - NEO4J_dbms_memory_pagecache_size=2G
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - neo4j_import:/var/lib/neo4j/import
      - neo4j_plugins:/plugins
      - ./backups:/backups
    networks:
      - luca-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "neo4j", "status"]
      interval: 30s
      timeout: 10s
      retries: 3

  # GapAnalyzer Agent
  gapanalyzer:
    image: luca-gapanalyzer:latest
    container_name: luca-gapanalyzer
    ports:
      - "10000:10000"
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DEFAULT_LLM_MODEL=gpt-4o-mini
      - DEFAULT_LLM_PROVIDER=openai
      - DEFAULT_LLM_TEMPERATURE=0.1
      - LANGFUSE_HOST=http://langfuse:3000
      - LANGFUSE_PUBLIC_KEY=${LANGFUSE_PUBLIC_KEY}
      - LANGFUSE_SECRET_KEY=${LANGFUSE_SECRET_KEY}
      - GRAPHBUILDER_URI=http://llm-graph-builder:8000/chat_bot
    depends_on:
      neo4j:
        condition: service_healthy
      langfuse:
        condition: service_healthy
    networks:
      - luca-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:10000/.well-known/agent.json"]
      interval: 30s
      timeout: 10s
      retries: 3

  # LLM Graph Builder API
  llm-graph-builder:
    image: neo4j/llm-graph-builder:latest
    container_name: luca-graph-builder
    ports:
      - "8000:8000"
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USERNAME=neo4j
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_MODEL=gpt-4o-mini
    depends_on:
      neo4j:
        condition: service_healthy
    networks:
      - luca-network
    restart: unless-stopped

  # Langfuse Observability Stack
  langfuse:
    image: langfuse/langfuse:2
    container_name: luca-langfuse
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://langfuse:${LANGFUSE_DB_PASSWORD}@postgres:5432/langfuse
      - NEXTAUTH_SECRET=${NEXTAUTH_SECRET}
      - SALT=${LANGFUSE_SALT}
      - NEXTAUTH_URL=http://localhost:3000
      - LANGFUSE_ENABLE_EXPERIMENTAL_FEATURES=true
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - luca-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/public/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # PostgreSQL for Langfuse
  postgres:
    image: postgres:15
    container_name: luca-postgres
    environment:
      - POSTGRES_DB=langfuse
      - POSTGRES_USER=langfuse
      - POSTGRES_PASSWORD=${LANGFUSE_DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - luca-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U langfuse"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis for Langfuse
  redis:
    image: redis:7-alpine
    container_name: luca-redis
    volumes:
      - redis_data:/data
    networks:
      - luca-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  # ClickHouse for Langfuse Analytics
  clickhouse:
    image: clickhouse/clickhouse-server:23.8
    container_name: luca-clickhouse
    environment:
      - CLICKHOUSE_DB=langfuse
      - CLICKHOUSE_USER=langfuse
      - CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT=1
      - CLICKHOUSE_PASSWORD=${CLICKHOUSE_PASSWORD}
    volumes:
      - clickhouse_data:/var/lib/clickhouse
    networks:
      - luca-network
    restart: unless-stopped

  # MinIO for Langfuse Storage
  minio:
    image: minio/minio:latest
    container_name: luca-minio
    command: server /data --console-address ":9090"
    ports:
      - "9000:9000"
      - "9090:9090"
    environment:
      - MINIO_ROOT_USER=${MINIO_ROOT_USER}
      - MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD}
    volumes:
      - minio_data:/data
    networks:
      - luca-network
    restart: unless-stopped

  # Nginx Load Balancer
  nginx:
    image: nginx:alpine
    container_name: luca-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/ssl/certs:ro
    depends_on:
      - gapanalyzer
      - langfuse
    networks:
      - luca-network
    restart: unless-stopped

volumes:
  neo4j_data:
  neo4j_logs:
  neo4j_import:
  neo4j_plugins:
  postgres_data:
  redis_data:
  clickhouse_data:
  minio_data:

networks:
  luca-network:
    driver: bridge
```

### Environment Configuration

Create `.env.prod`:

```bash
# Database Passwords
NEO4J_PASSWORD=your_secure_neo4j_password
LANGFUSE_DB_PASSWORD=your_secure_postgres_password
CLICKHOUSE_PASSWORD=your_secure_clickhouse_password

# OpenAI Configuration
OPENAI_API_KEY=sk-your-production-openai-key

# Langfuse Configuration
LANGFUSE_PUBLIC_KEY=pk-lf-your-production-public-key
LANGFUSE_SECRET_KEY=sk-lf-your-production-secret-key
NEXTAUTH_SECRET=your-secure-nextauth-secret-32-chars-min
LANGFUSE_SALT=your-secure-salt-16-chars-min

# MinIO Configuration
MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=your_secure_minio_password

# Security
JWT_SECRET=your-jwt-secret-key
API_RATE_LIMIT=1000
```

### Nginx Configuration

Create `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream gapanalyzer {
        server gapanalyzer:10000;
        # Add more instances for load balancing
        # server gapanalyzer-2:10000;
        # server gapanalyzer-3:10000;
    }

    upstream langfuse {
        server langfuse:3000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=ui:10m rate=30r/s;

    server {
        listen 80;
        server_name luca.yourdomain.com;

        # Redirect to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name luca.yourdomain.com;

        # SSL Configuration
        ssl_certificate /etc/ssl/certs/luca.crt;
        ssl_certificate_key /etc/ssl/certs/luca.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

        # GapAnalyzer API
        location /api/gapanalyzer/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://gapanalyzer/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        # Langfuse Dashboard
        location /langfuse/ {
            limit_req zone=ui burst=50 nodelay;
            proxy_pass http://langfuse/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Health checks
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }
}
```

### Deployment Commands

```bash
# Pull latest images
docker-compose -f docker-compose.prod.yml pull

# Start services
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Check service health
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f gapanalyzer

# Scale agents (if needed)
docker-compose -f docker-compose.prod.yml up -d --scale gapanalyzer=3
```

## ☸️ Kubernetes Deployment

### Namespace and ConfigMap

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: luca-system
---
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: luca-config
  namespace: luca-system
data:
  DEFAULT_LLM_MODEL: "gpt-4o-mini"
  DEFAULT_LLM_PROVIDER: "openai"
  DEFAULT_LLM_TEMPERATURE: "0.1"
  NEO4J_URI: "bolt://neo4j-service:7687"
  NEO4J_USER: "neo4j"
  LANGFUSE_HOST: "http://langfuse-service:3000"
```

### Secrets

```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: luca-secrets
  namespace: luca-system
type: Opaque
stringData:
  neo4j-password: "your_secure_password"
  openai-api-key: "sk-your-openai-key"
  langfuse-public-key: "pk-lf-your-key"
  langfuse-secret-key: "sk-lf-your-key"
```

### Neo4j Deployment

```yaml
# neo4j-deployment.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: neo4j
  namespace: luca-system
spec:
  serviceName: neo4j-service
  replicas: 1
  selector:
    matchLabels:
      app: neo4j
  template:
    metadata:
      labels:
        app: neo4j
    spec:
      containers:
      - name: neo4j
        image: neo4j:5.26.1-enterprise
        ports:
        - containerPort: 7474
        - containerPort: 7687
        env:
        - name: NEO4J_AUTH
          valueFrom:
            secretKeyRef:
              name: luca-secrets
              key: neo4j-password
        - name: NEO4J_ACCEPT_LICENSE_AGREEMENT
          value: "yes"
        - name: NEO4JLABS_PLUGINS
          value: '["apoc","graph-data-science"]'
        volumeMounts:
        - name: neo4j-data
          mountPath: /data
        - name: neo4j-logs
          mountPath: /logs
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
  volumeClaimTemplates:
  - metadata:
      name: neo4j-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 100Gi
  - metadata:
      name: neo4j-logs
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
---
apiVersion: v1
kind: Service
metadata:
  name: neo4j-service
  namespace: luca-system
spec:
  selector:
    app: neo4j
  ports:
  - name: http
    port: 7474
    targetPort: 7474
  - name: bolt
    port: 7687
    targetPort: 7687
```

### GapAnalyzer Deployment

```yaml
# gapanalyzer-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gapanalyzer
  namespace: luca-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: gapanalyzer
  template:
    metadata:
      labels:
        app: gapanalyzer
    spec:
      containers:
      - name: gapanalyzer
        image: luca-gapanalyzer:latest
        ports:
        - containerPort: 10000
        env:
        - name: NEO4J_PASSWORD
          valueFrom:
            secretKeyRef:
              name: luca-secrets
              key: neo4j-password
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: luca-secrets
              key: openai-api-key
        envFrom:
        - configMapRef:
            name: luca-config
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1"
        livenessProbe:
          httpGet:
            path: /.well-known/agent.json
            port: 10000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /.well-known/agent.json
            port: 10000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: gapanalyzer-service
  namespace: luca-system
spec:
  selector:
    app: gapanalyzer
  ports:
  - port: 10000
    targetPort: 10000
  type: ClusterIP
```

### Ingress Configuration

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: luca-ingress
  namespace: luca-system
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - luca.yourdomain.com
    secretName: luca-tls
  rules:
  - host: luca.yourdomain.com
    http:
      paths:
      - path: /api/gapanalyzer
        pathType: Prefix
        backend:
          service:
            name: gapanalyzer-service
            port:
              number: 10000
      - path: /langfuse
        pathType: Prefix
        backend:
          service:
            name: langfuse-service
            port:
              number: 3000
```

## ☁️ Cloud Platform Deployment

### AWS ECS Deployment

```yaml
# ecs-task-definition.json
{
  "family": "luca-gapanalyzer",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "gapanalyzer",
      "image": "your-account.dkr.ecr.region.amazonaws.com/luca-gapanalyzer:latest",
      "portMappings": [
        {
          "containerPort": 10000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DEFAULT_LLM_MODEL",
          "value": "gpt-4o-mini"
        }
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:luca/openai-key"
        },
        {
          "name": "NEO4J_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:luca/neo4j-password"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/luca-gapanalyzer",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "curl -f http://localhost:10000/.well-known/agent.json || exit 1"
        ],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

### Google Cloud Run Deployment

```yaml
# cloudrun-service.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: luca-gapanalyzer
  namespace: default
  annotations:
    run.googleapis.com/ingress: all
    run.googleapis.com/execution-environment: gen2
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: "10"
        autoscaling.knative.dev/minScale: "1"
        run.googleapis.com/cpu-throttling: "false"
        run.googleapis.com/memory: "2Gi"
        run.googleapis.com/cpu: "1"
    spec:
      containerConcurrency: 10
      containers:
      - image: gcr.io/your-project/luca-gapanalyzer:latest
        ports:
        - containerPort: 10000
        env:
        - name: DEFAULT_LLM_MODEL
          value: "gpt-4o-mini"
        - name: NEO4J_URI
          value: "bolt://your-neo4j-instance:7687"
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: luca-secrets
              key: openai-api-key
        resources:
          limits:
            memory: "2Gi"
            cpu: "1"
        livenessProbe:
          httpGet:
            path: /.well-known/agent.json
            port: 10000
          initialDelaySeconds: 30
          periodSeconds: 10
```

## 🔧 Production Configuration

### Environment Variables

```bash
# Production .env template
# Copy to .env.prod and fill in actual values

# === REQUIRED CONFIGURATION ===
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=CHANGE_ME

OPENAI_API_KEY=sk-CHANGE_ME

# === LLM CONFIGURATION ===
DEFAULT_LLM_MODEL=gpt-4o-mini
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_TEMPERATURE=0.1
DEFAULT_LLM_MAX_TOKENS=4096

# === LANGFUSE OBSERVABILITY ===
LANGFUSE_HOST=http://langfuse:3000
LANGFUSE_PUBLIC_KEY=pk-lf-CHANGE_ME
LANGFUSE_SECRET_KEY=sk-lf-CHANGE_ME
NEXTAUTH_SECRET=CHANGE_ME_32_CHARS_MIN
LANGFUSE_SALT=CHANGE_ME_16_CHARS

# === DATABASE PASSWORDS ===
LANGFUSE_DB_PASSWORD=CHANGE_ME
CLICKHOUSE_PASSWORD=CHANGE_ME

# === STORAGE ===
MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=CHANGE_ME

# === SECURITY ===
JWT_SECRET=CHANGE_ME
API_RATE_LIMIT=1000
CORS_ORIGINS=https://yourdomain.com

# === MONITORING ===
LOG_LEVEL=INFO
SENTRY_DSN=https://your-sentry-dsn
ENABLE_METRICS=true
```

### Production Docker Image

```dockerfile
# Dockerfile.prod
FROM registry.access.redhat.com/ubi8/python-312:1-77 AS builder

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY requirements.txt requirements-prod.txt ./

# Install dependencies in virtual environment
RUN uv venv /opt/venv
RUN uv pip install --system -r requirements-prod.txt

# Production stage
FROM registry.access.redhat.com/ubi8/python-312:1-77

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY . /app
WORKDIR /app

# Create non-root user
USER 1001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:10000/.well-known/agent.json || exit 1

# Expose port
EXPOSE 10000

# Production command
CMD ["python", "-m", "gapanalyzer", "--host", "0.0.0.0", "--port", "10000"]
```

### Build and Push Script

```bash
#!/bin/bash
# scripts/build-prod.sh

set -e

IMAGE_NAME="luca-gapanalyzer"
IMAGE_TAG=${1:-latest}
REGISTRY=${REGISTRY:-your-registry.com}

echo "Building production image..."
docker build -f Dockerfile.prod -t ${IMAGE_NAME}:${IMAGE_TAG} .

echo "Tagging for registry..."
docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}

echo "Pushing to registry..."
docker push ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}

echo "Build and push completed: ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
```

## 📊 Monitoring and Observability

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'luca-gapanalyzer'
    static_configs:
      - targets: ['gapanalyzer:10000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'neo4j'
    static_configs:
      - targets: ['neo4j:2004']
    scrape_interval: 30s

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:9113']
    scrape_interval: 15s
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Luca System Monitoring",
    "panels": [
      {
        "title": "Agent Response Times",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(gapanalyzer_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "LLM Token Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(langfuse_tokens_total[5m])",
            "legendFormat": "Tokens per second"
          }
        ]
      },
      {
        "title": "Knowledge Graph Queries",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(neo4j_database_query_execution_latency_millis_count[5m])",
            "legendFormat": "Queries per second"
          }
        ]
      }
    ]
  }
}
```

### Log Aggregation

```yaml
# logging-stack.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.8.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - es_data:/usr/share/elasticsearch/data

  logstash:
    image: docker.elastic.co/logstash/logstash:8.8.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf

  kibana:
    image: docker.elastic.co/kibana/kibana:8.8.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200

volumes:
  es_data:
```

## 🔒 Security Configuration

### SSL/TLS Setup

```bash
# Generate SSL certificates
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout luca.key -out luca.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=luca.yourdomain.com"

# Or use Let's Encrypt with certbot
certbot certonly --webroot -w /var/www/html -d luca.yourdomain.com
```

### Security Headers

```nginx
# Additional nginx security configuration
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';";
add_header Referrer-Policy "strict-origin-when-cross-origin";
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()";
```

### Network Security

```yaml
# docker-compose security additions
networks:
  luca-network:
    driver: bridge
    driver_opts:
      com.docker.network.bridge.enable_icc: "false"
      com.docker.network.bridge.enable_ip_masquerade: "true"
```

## 📈 Scaling and Performance

### Horizontal Scaling

```bash
# Scale GapAnalyzer agents
docker-compose -f docker-compose.prod.yml up -d --scale gapanalyzer=5

# Kubernetes scaling
kubectl scale deployment gapanalyzer --replicas=5 -n luca-system
```

### Performance Tuning

```yaml
# Neo4j performance configuration
environment:
  - NEO4J_dbms_memory_heap_initial_size=4G
  - NEO4J_dbms_memory_heap_max_size=8G
  - NEO4J_dbms_memory_pagecache_size=4G
  - NEO4J_dbms_query_cache_size=1000
  - NEO4J_dbms_tx_log_rotation_retention_policy=1G size
```

### Auto-scaling (Kubernetes)

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: gapanalyzer-hpa
  namespace: luca-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: gapanalyzer
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## 🔄 Backup and Recovery

### Database Backup

```bash
#!/bin/bash
# scripts/backup-neo4j.sh

BACKUP_DIR="/backups/neo4j/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Backup database
docker exec luca-neo4j neo4j-admin database dump --to-path=/backups neo4j

# Compress backup
tar -czf ${BACKUP_DIR}/neo4j-backup.tar.gz -C /backups neo4j.dump

# Clean old backups (keep 7 days)
find /backups/neo4j -type d -mtime +7 -exec rm -rf {} +
```

### Automated Backup

```yaml
# backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: neo4j-backup
  namespace: luca-system
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: neo4j:5.26.1
            command:
            - /bin/bash
            - -c
            - |
              neo4j-admin database dump --to-path=/backups neo4j
              aws s3 cp /backups/neo4j.dump s3://luca-backups/$(date +%Y%m%d)/
            volumeMounts:
            - name: backup-storage
              mountPath: /backups
          restartPolicy: OnFailure
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
```

This deployment guide provides comprehensive coverage for deploying Luca in various production environments with proper security, monitoring, and scaling considerations.