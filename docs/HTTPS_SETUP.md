# HTTPS Setup for LUCA Flask Application

This guide explains how to configure LUCA Flask application with HTTPS support using self-signed certificates.

## Quick Start

### 1. Generate SSL Certificates

```bash
# Generate self-signed certificates for HTTPS
python scripts/generate_ssl_certs.py --domain luca-app --verbose
```

This creates:
- `ssl/luca.crt` - SSL certificate
- `ssl/luca.key` - Private key

### 2. Run with HTTPS Locally

```bash
# Run Flask app with HTTPS
cd frontend
python run.py --https

# Custom port and domain
python run.py --https --port 8443 --host 0.0.0.0

# With custom certificates
python run.py --https --cert /path/to/cert.crt --key /path/to/key.key
```

### 3. Docker with HTTPS

```bash
# Start with Docker Compose (HTTPS enabled by default)
docker-compose up -d

# Access the application
# HTTPS: https://localhost:443
# HTTP (fallback): http://localhost:5000
```

## Configuration Options

### Environment Variables

Add to your `.env` file:

```bash
# HTTPS Configuration
LUCA_ENABLE_HTTPS=true          # Enable HTTPS in Docker
LUCA_HTTPS_PORT=443             # HTTPS port
LUCA_HTTP_PORT=5000             # HTTP fallback port

# Flask Security
FLASK_SECRET_KEY=your-secure-secret-key-for-production
```

### SSL Certificate Generation Options

```bash
# Basic certificate generation
python scripts/generate_ssl_certs.py

# Custom domain and validity
python scripts/generate_ssl_certs.py --domain mydomain.com --days 365

# Different output directory
python scripts/generate_ssl_certs.py --output-dir /path/to/certs

# Force Python cryptography (if OpenSSL not available)
python scripts/generate_ssl_certs.py --force-cryptography

# Show verbose output
python scripts/generate_ssl_certs.py --verbose
```

## Docker Configuration

### Port Mapping

The updated `docker-compose.yml` exposes both ports:

```yaml
ports:
  - "443:443"   # HTTPS port
  - "5000:5000" # HTTP port (for backwards compatibility)
```

### SSL Certificate Mounting

SSL certificates are mounted as read-only volume:

```yaml
volumes:
  # Mount SSL certificates directory
  - ./ssl:/app/ssl:ro
```

### Environment Variables

Configure HTTPS behavior:

```yaml
environment:
  # HTTPS Configuration
  LUCA_ENABLE_HTTPS: "${LUCA_ENABLE_HTTPS:-true}"
  LUCA_HTTPS_PORT: "${LUCA_HTTPS_PORT:-443}"
  LUCA_HTTP_PORT: "${LUCA_HTTP_PORT:-5000}"
```

## Local Development

### Running with HTTPS

```bash
cd frontend

# Basic HTTPS (uses ssl/luca.crt and ssl/luca.key)
python run.py --https

# Custom port
python run.py --https --port 8443

# Development with debug mode (HTTPS)
python run.py --https --port 8443

# Production mode (no debug)
python run.py --https --no-debug
```

### Running with HTTP (default)

```bash
cd frontend

# Basic HTTP
python run.py

# Custom port
python run.py --port 8080
```

## Browser Configuration

### Self-Signed Certificate Warnings

When using self-signed certificates, browsers will show security warnings:

1. **Chrome/Edge**: Click "Advanced" → "Proceed to localhost (unsafe)"
2. **Firefox**: Click "Advanced" → "Accept the Risk and Continue"
3. **Safari**: Click "Show Details" → "visit this website"

### Adding Certificate to Browser

For development, you can add the certificate to your browser's trusted certificates:

1. Open `ssl/luca.crt` in a text editor
2. Copy the certificate content
3. Import into browser's certificate manager
4. Mark as trusted for SSL/TLS

## Production Deployment

### Using Real SSL Certificates

For production, replace self-signed certificates with real certificates:

```bash
# Place your real certificates
cp your-certificate.crt ssl/luca.crt
cp your-private-key.key ssl/luca.key

# Ensure correct permissions
chmod 644 ssl/luca.crt
chmod 600 ssl/luca.key
```

### Reverse Proxy Configuration

For production, consider using a reverse proxy like Nginx:

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /path/to/ssl/luca.crt;
    ssl_certificate_key /path/to/ssl/luca.key;

    location / {
        proxy_pass https://luca-app:443;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Troubleshooting

### Common Issues

1. **Certificates not found**
   ```
   ❌ SSL certificates not found!
   💡 Generate certificates with: python scripts/generate_ssl_certs.py
   ```
   **Solution**: Run the certificate generation script

2. **Permission denied**
   ```
   Permission denied: ssl/luca.key
   ```
   **Solution**: Check file permissions
   ```bash
   chmod 600 ssl/luca.key
   chmod 644 ssl/luca.crt
   ```

3. **Port already in use**
   ```
   Address already in use: Port 443
   ```
   **Solution**: Stop other services or use different port
   ```bash
   python run.py --https --port 8443
   ```

4. **Docker container not starting**
   ```
   Error starting container: SSL certificates not mounted
   ```
   **Solution**: Ensure SSL certificates exist before starting Docker
   ```bash
   # Generate certificates first
   python scripts/generate_ssl_certs.py
   # Then start Docker
   docker-compose up -d
   ```

### Certificate Information

Check certificate details:

```bash
# View certificate information
openssl x509 -in ssl/luca.crt -text -noout

# Check certificate validity
openssl x509 -in ssl/luca.crt -noout -dates

# Verify certificate and key match
openssl x509 -in ssl/luca.crt -noout -modulus | openssl md5
openssl rsa -in ssl/luca.key -noout -modulus | openssl md5
```

### Testing HTTPS Connection

```bash
# Test HTTPS connection
curl -k https://localhost:443/

# Test with certificate verification (will fail for self-signed)
curl https://localhost:443/

# Test HTTP fallback
curl http://localhost:5000/
```

## Security Considerations

### Self-Signed Certificates

- ⚠️ **Development only**: Self-signed certificates should only be used for development
- 🔒 **No validation**: Browsers will show security warnings
- 🚫 **Not trusted**: Self-signed certificates are not trusted by default

### Production Security

- 🔐 **Real certificates**: Use certificates from trusted Certificate Authorities (CA)
- 🔄 **Auto-renewal**: Implement automatic certificate renewal (Let's Encrypt)
- 🛡️ **Security headers**: Add security headers (HSTS, CSP, etc.)
- 🔍 **Regular updates**: Keep SSL/TLS configurations updated

### File Permissions

Ensure correct permissions for certificate files:

```bash
# Private key: owner read/write only
chmod 600 ssl/luca.key

# Certificate: owner read/write, others read
chmod 644 ssl/luca.crt

# Directory: accessible but not listable
chmod 755 ssl/
```

## Integration with LUCA Components

### Neo4j Connection

HTTPS doesn't affect Neo4j connections (uses Bolt protocol on port 7687).

### Langfuse Observability

Langfuse integration works with both HTTP and HTTPS modes.

### Guardrails System

All guardrails functionality is preserved with HTTPS.

### Agent Communication

A2A (Agent-to-Agent) communication continues to work with HTTPS.

## Command Reference

### Certificate Generation

```bash
# Basic generation
python scripts/generate_ssl_certs.py

# All options
python scripts/generate_ssl_certs.py \
  --domain luca-app \
  --days 365 \
  --key-size 2048 \
  --output-dir ssl \
  --verbose
```

### Flask Application

```bash
# Local development
cd frontend

# HTTPS modes
python run.py --https                    # Default HTTPS
python run.py --https --port 8443        # Custom port
python run.py --https --no-debug         # Production mode

# HTTP modes
python run.py                            # Default HTTP
python run.py --port 8080                # Custom port

# Help
python run.py --help
```

### Docker Commands

```bash
# Start with HTTPS (default)
docker-compose up -d

# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f luca

# Stop services
docker-compose down
```

## Next Steps

1. **Generate certificates**: `python scripts/generate_ssl_certs.py`
2. **Test locally**: `cd frontend && python run.py --https`
3. **Deploy with Docker**: `docker-compose up -d`
4. **Access application**: `https://localhost:443`
5. **Accept certificate warning** in browser for self-signed certificates

For production deployment, replace self-signed certificates with real certificates from a trusted Certificate Authority.