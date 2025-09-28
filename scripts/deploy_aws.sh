#!/bin/bash

# LUCA AWS EC2 Deployment Script
# This script automates the deployment setup for LUCA on AWS EC2

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

# Check if running on Ubuntu
check_os() {
    if [[ ! -f /etc/lsb-release ]] || ! grep -q "Ubuntu" /etc/lsb-release; then
        error "This script is designed for Ubuntu. Please run on Ubuntu 22.04 LTS."
    fi
    log "✅ OS check passed - Running on Ubuntu"
}

# Install Docker and Docker Compose
install_docker() {
    log "📦 Installing Docker..."

    # Remove old Docker installations
    sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

    # Update package index
    sudo apt-get update

    # Install prerequisites
    sudo apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release

    # Add Docker's official GPG key
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    # Set up the repository
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker Engine
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Add user to docker group
    sudo usermod -aG docker $USER

    # Install Docker Compose standalone
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose

    # Enable Docker service
    sudo systemctl enable docker

    log "✅ Docker installed successfully"
    log "⚠️  Please log out and back in for Docker group changes to take effect"
}

# Setup application directory
setup_app_directory() {
    log "📁 Setting up application directory..."

    APP_DIR="/opt/luca"

    # Create application directory
    sudo mkdir -p $APP_DIR
    sudo chown $USER:$USER $APP_DIR

    # Create required subdirectories
    mkdir -p $APP_DIR/{db/{data,logs,import,plugins},ssl,backups,logs}

    # Set proper permissions for Neo4j directories
    chmod -R 755 $APP_DIR/db/

    log "✅ Application directory created at $APP_DIR"
    echo $APP_DIR
}

# Download Neo4j plugins
download_neo4j_plugins() {
    local app_dir=$1
    log "🔌 Downloading Neo4j plugins..."

    cd $app_dir/db/plugins

    # Download APOC plugin
    if [[ ! -f "apoc-5.26.0-core.jar" ]]; then
        log "Downloading APOC plugin..."
        wget -q https://github.com/neo4j-contrib/neo4j-apoc-procedures/releases/download/5.26.0/apoc-5.26.0-core.jar
    fi

    # Download Graph Data Science plugin
    if [[ ! -f "neo4j-graph-data-science-2.13.2.jar" ]]; then
        log "Downloading Graph Data Science plugin..."
        wget -q https://github.com/neo4j/graph-data-science/releases/download/2.13.2/neo4j-graph-data-science-2.13.2.jar
    fi

    log "✅ Neo4j plugins downloaded"
    ls -la $app_dir/db/plugins/
}

# Generate SSL certificates
generate_ssl_certificates() {
    local app_dir=$1
    log "🔒 Generating SSL certificates..."

    cd $app_dir

    # Get public IP
    PUBLIC_IP=$(curl -s http://checkip.amazonaws.com || echo "localhost")

    # Generate self-signed certificates
    openssl req -x509 -newkey rsa:4096 -keyout ssl/luca.key -out ssl/luca.crt -days 365 -nodes \
        -subj "/C=AR/ST=Buenos Aires/L=Buenos Aires/O=UCA/OU=IT Department/CN=$PUBLIC_IP" \
        -addext "subjectAltName=DNS:localhost,DNS:$PUBLIC_IP,IP:127.0.0.1,IP:$PUBLIC_IP" 2>/dev/null

    # Set proper permissions
    chmod 600 ssl/luca.key
    chmod 644 ssl/luca.crt

    log "✅ SSL certificates generated for IP: $PUBLIC_IP"
}

# Create environment file
create_env_file() {
    local app_dir=$1
    log "⚙️  Creating environment configuration..."

    if [[ -f "$app_dir/.env" ]]; then
        warn "Environment file already exists. Backing up..."
        cp "$app_dir/.env" "$app_dir/.env.backup.$(date +%Y%m%d_%H%M%S)"
    fi

    cat > "$app_dir/.env" << 'EOF'
# ===== CONFIGURACIÓN OBLIGATORIA =====
# ⚠️  CAMBIAR ESTOS VALORES ANTES DE USAR EN PRODUCCIÓN

# Neo4j Database Configuration
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=CAMBIAR_PASSWORD_NEO4J_123

# OpenAI API Configuration
OPENAI_API_KEY=CAMBIAR_TU_CLAVE_OPENAI_AQUI

# Flask Application Security
FLASK_SECRET_KEY=CAMBIAR_CLAVE_SECRETA_FLASK_MUY_LARGA_Y_SEGURA

# ===== CONFIGURACIÓN DE MODELO LLM =====

# Default LLM Configuration
DEFAULT_LLM_MODEL=gpt-4o-mini
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_TEMPERATURE=0.1
DEFAULT_LLM_MAX_TOKENS=4096
DEFAULT_LLM_TIMEOUT=60

# ===== CONFIGURACIÓN DE HTTPS =====

# HTTPS Configuration
LUCA_ENABLE_HTTPS=true
LUCA_HTTPS_PORT=443
LUCA_HTTP_PORT=5000

# ===== CONFIGURACIÓN OPCIONAL =====

# Langfuse Observability (DESHABILITADO por defecto)
LANGFUSE_ENABLED=false
LANGFUSE_HOST=
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=

# Guardrails Configuration
GUARDRAILS_ENABLE_OPENAI_MODERATION=true
GUARDRAILS_ENABLE_PROFANITY_FILTER=true
GUARDRAILS_ENABLE_EDUCATIONAL_VALIDATION=true
GUARDRAILS_ENABLE_RATE_LIMITING=true
GUARDRAILS_ENABLE_RESPONSE_VALIDATION=true
GUARDRAILS_STRICT_ACADEMIC_MODE=false
GUARDRAILS_ALLOW_GENERAL_KNOWLEDGE=true
GUARDRAILS_MAX_REQUESTS_PER_MINUTE=30
GUARDRAILS_MAX_REQUESTS_PER_HOUR=200
GUARDRAILS_MAX_REQUESTS_PER_DAY=1000
EOF

    log "✅ Environment file created at $app_dir/.env"
    warn "🔑 IMPORTANTE: Editar $app_dir/.env y configurar las claves de API antes de continuar"
}

# Create systemd service
create_systemd_service() {
    local app_dir=$1
    log "🔧 Creating systemd service..."

    sudo tee /etc/systemd/system/luca.service > /dev/null << EOF
[Unit]
Description=LUCA Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$app_dir
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
ExecReload=/usr/local/bin/docker-compose restart
TimeoutStartSec=0
User=$USER
Group=docker

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable luca.service

    log "✅ Systemd service created and enabled"
}

# Create backup script
create_backup_script() {
    local app_dir=$1
    log "💾 Creating backup script..."

    cat > "$app_dir/backup.sh" << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/luca/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

echo "Creating backup at $DATE..."

# Backup de Neo4j
docker-compose exec neo4j neo4j-admin database dump --to-path=/tmp neo4j
docker cp $(docker-compose ps -q neo4j):/tmp/neo4j.dump $BACKUP_DIR/neo4j_$DATE.dump

# Backup de configuración
cp /opt/luca/.env $BACKUP_DIR/env_$DATE.backup

# Comprimir backup
tar -czf $BACKUP_DIR/luca_backup_$DATE.tar.gz $BACKUP_DIR/neo4j_$DATE.dump $BACKUP_DIR/env_$DATE.backup

# Limpiar archivos temporales
rm $BACKUP_DIR/neo4j_$DATE.dump $BACKUP_DIR/env_$DATE.backup

echo "Backup creado: $BACKUP_DIR/luca_backup_$DATE.tar.gz"

# Mantener solo los últimos 7 backups
find $BACKUP_DIR -name "luca_backup_*.tar.gz" -mtime +7 -delete
EOF

    chmod +x "$app_dir/backup.sh"

    log "✅ Backup script created at $app_dir/backup.sh"
}

# Configure firewall
configure_firewall() {
    log "🔥 Configuring firewall..."

    # Install ufw if not present
    sudo apt-get install -y ufw

    # Configure firewall rules
    sudo ufw --force enable
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw allow ssh
    sudo ufw allow 443/tcp
    sudo ufw allow 80/tcp

    log "✅ Firewall configured"
    sudo ufw status
}

# Main deployment function
main() {
    log "🚀 Starting LUCA AWS EC2 deployment..."
    log "================================================"

    # Check if running as root
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root. Please run as ubuntu user."
    fi

    # Perform all setup steps
    check_os
    install_docker
    APP_DIR=$(setup_app_directory)
    download_neo4j_plugins $APP_DIR
    generate_ssl_certificates $APP_DIR
    create_env_file $APP_DIR
    create_systemd_service $APP_DIR
    create_backup_script $APP_DIR
    configure_firewall

    log "================================================"
    log "🎉 LUCA deployment setup completed!"
    log "================================================"
    echo
    log "📋 PRÓXIMOS PASOS:"
    echo "1. 🔑 Editar el archivo de configuración:"
    echo "   sudo nano $APP_DIR/.env"
    echo
    echo "2. 📁 Copiar el código de la aplicación a:"
    echo "   $APP_DIR/"
    echo
    echo "3. 🚀 Iniciar la aplicación:"
    echo "   sudo systemctl start luca.service"
    echo
    echo "4. 📊 Verificar el estado:"
    echo "   sudo systemctl status luca.service"
    echo
    echo "5. 🌐 Acceder a la aplicación:"
    PUBLIC_IP=$(curl -s http://checkip.amazonaws.com)
    echo "   https://$PUBLIC_IP/"
    echo
    warn "⚠️  IMPORTANTE: Configurar las variables de entorno antes de iniciar"
    warn "⚠️  Log out and back in para que los cambios de Docker group tomen efecto"
}

# Run main function
main "$@"