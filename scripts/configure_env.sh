#!/bin/bash

# LUCA Environment Configuration Script
# Interactive script to configure environment variables

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[INFO] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

# Prompt for user input with default value
prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local sensitive="$3"
    local input

    if [[ "$sensitive" == "true" ]]; then
        echo -n "$prompt [$default]: "
        read -s input
        echo
    else
        echo -n "$prompt [$default]: "
        read input
    fi

    if [[ -z "$input" ]]; then
        echo "$default"
    else
        echo "$input"
    fi
}

# Validate OpenAI API key format
validate_openai_key() {
    local key="$1"
    if [[ "$key" =~ ^sk-[a-zA-Z0-9]{48,}$ ]]; then
        return 0
    else
        return 1
    fi
}

# Generate secure random password
generate_secure_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
}

# Test Neo4j connection
test_neo4j_connection() {
    local username="$1"
    local password="$2"

    log "Testing Neo4j connection..."

    if command -v docker-compose &> /dev/null && [[ -f "/opt/luca/docker-compose.yml" ]]; then
        cd /opt/luca
        if docker-compose exec neo4j cypher-shell -u "$username" -p "$password" "RETURN 'Connection successful' as result" &>/dev/null; then
            echo "✅ Neo4j connection successful"
            return 0
        else
            echo "❌ Neo4j connection failed"
            return 1
        fi
    else
        warn "Cannot test Neo4j connection - docker-compose not available"
        return 0
    fi
}

# Test OpenAI API key
test_openai_key() {
    local api_key="$1"

    log "Testing OpenAI API key..."

    local response=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $api_key" \
        -H "Content-Type: application/json" \
        -d '{"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "test"}], "max_tokens": 1}' \
        https://api.openai.com/v1/chat/completions 2>/dev/null)

    local http_code="${response: -3}"

    if [[ "$http_code" == "200" ]]; then
        echo "✅ OpenAI API key is valid"
        return 0
    elif [[ "$http_code" == "401" ]]; then
        echo "❌ OpenAI API key is invalid"
        return 1
    else
        warn "Unable to validate OpenAI API key (HTTP: $http_code)"
        return 0
    fi
}

# Main configuration function
main() {
    log "🔧 LUCA Environment Configuration"
    echo "================================="
    echo

    # Check if .env file exists
    local env_file="/opt/luca/.env"
    if [[ ! -f "$env_file" ]]; then
        error "Environment file not found at $env_file"
        echo "Please run the deployment script first: ./scripts/deploy_aws.sh"
        exit 1
    fi

    # Backup existing file
    local backup_file="${env_file}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$env_file" "$backup_file"
    log "Existing environment file backed up to: $backup_file"
    echo

    # Read current values
    log "Reading current configuration..."
    local current_neo4j_user=$(grep "^NEO4J_USERNAME=" "$env_file" | cut -d= -f2)
    local current_neo4j_pass=$(grep "^NEO4J_PASSWORD=" "$env_file" | cut -d= -f2)
    local current_openai_key=$(grep "^OPENAI_API_KEY=" "$env_file" | cut -d= -f2)
    local current_flask_secret=$(grep "^FLASK_SECRET_KEY=" "$env_file" | cut -d= -f2)

    echo
    log "=== CONFIGURACIÓN OBLIGATORIA ==="
    echo

    # Neo4j Configuration
    log "🗄️  Neo4j Database Configuration"
    local neo4j_username=$(prompt_with_default "Neo4j Username" "${current_neo4j_user:-neo4j}")

    if [[ "$current_neo4j_pass" == "CAMBIAR_PASSWORD_NEO4J_123" || -z "$current_neo4j_pass" ]]; then
        local suggested_password=$(generate_secure_password)
        local neo4j_password=$(prompt_with_default "Neo4j Password" "$suggested_password" "true")
    else
        local neo4j_password=$(prompt_with_default "Neo4j Password (current)" "***KEEP_CURRENT***" "true")
        if [[ "$neo4j_password" == "***KEEP_CURRENT***" ]]; then
            neo4j_password="$current_neo4j_pass"
        fi
    fi

    echo
    log "🤖 OpenAI API Configuration"
    local openai_key
    while true; do
        openai_key=$(prompt_with_default "OpenAI API Key" "${current_openai_key}" "true")

        if [[ "$openai_key" == "$current_openai_key" && "$current_openai_key" != "CAMBIAR_TU_CLAVE_OPENAI_AQUI" ]]; then
            echo "✅ Using existing OpenAI API key"
            break
        elif validate_openai_key "$openai_key"; then
            if test_openai_key "$openai_key"; then
                break
            else
                warn "API key validation failed. Please try again."
            fi
        else
            warn "Invalid OpenAI API key format. Should start with 'sk-' and be at least 50 characters."
        fi
    done

    echo
    log "🔐 Flask Application Security"
    if [[ "$current_flask_secret" == "CAMBIAR_CLAVE_SECRETA_FLASK_MUY_LARGA_Y_SEGURA" || -z "$current_flask_secret" ]]; then
        local suggested_secret=$(generate_secure_password)$(generate_secure_password)
        local flask_secret=$(prompt_with_default "Flask Secret Key" "$suggested_secret")
    else
        local flask_secret=$(prompt_with_default "Flask Secret Key (current)" "***KEEP_CURRENT***")
        if [[ "$flask_secret" == "***KEEP_CURRENT***" ]]; then
            flask_secret="$current_flask_secret"
        fi
    fi

    echo
    log "=== CONFIGURACIÓN OPCIONAL ==="
    echo

    # LLM Configuration
    log "🧠 LLM Model Configuration"
    local current_model=$(grep "^DEFAULT_LLM_MODEL=" "$env_file" | cut -d= -f2)
    local llm_model=$(prompt_with_default "LLM Model" "${current_model:-gpt-4o-mini}")

    local current_temp=$(grep "^DEFAULT_LLM_TEMPERATURE=" "$env_file" | cut -d= -f2)
    local llm_temperature=$(prompt_with_default "LLM Temperature (0.0-1.0)" "${current_temp:-0.1}")

    # Langfuse Configuration
    echo
    log "📊 Langfuse Observability (Optional)"
    local current_langfuse_enabled=$(grep "^LANGFUSE_ENABLED=" "$env_file" | cut -d= -f2)
    echo "Current status: ${current_langfuse_enabled:-false}"
    echo "Langfuse provides observability and monitoring for LLM calls."
    echo "For basic setup, keep it disabled (false)."
    local langfuse_enabled=$(prompt_with_default "Enable Langfuse? (true/false)" "${current_langfuse_enabled:-false}")

    # Write new configuration
    echo
    log "✍️  Writing new configuration..."

    cat > "$env_file" << EOF
# ===== CONFIGURACIÓN OBLIGATORIA =====
# Generated by configure_env.sh on $(date)

# Neo4j Database Configuration
NEO4J_USERNAME=$neo4j_username
NEO4J_PASSWORD=$neo4j_password

# OpenAI API Configuration
OPENAI_API_KEY=$openai_key

# Flask Application Security
FLASK_SECRET_KEY=$flask_secret

# ===== CONFIGURACIÓN DE MODELO LLM =====

# Default LLM Configuration
DEFAULT_LLM_MODEL=$llm_model
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_TEMPERATURE=$llm_temperature
DEFAULT_LLM_MAX_TOKENS=4096
DEFAULT_LLM_TIMEOUT=60

# ===== CONFIGURACIÓN DE HTTPS =====

# HTTPS Configuration
LUCA_ENABLE_HTTPS=true
LUCA_HTTPS_PORT=443
LUCA_HTTP_PORT=5000

# ===== CONFIGURACIÓN OPCIONAL =====

# Langfuse Observability
LANGFUSE_ENABLED=$langfuse_enabled
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

    echo "✅ Configuration written to $env_file"
    echo

    # Test connections if possible
    log "🧪 Testing configuration..."
    if test_neo4j_connection "$neo4j_username" "$neo4j_password"; then
        echo "✅ Neo4j configuration looks good"
    fi

    echo
    log "🎉 Configuration completed successfully!"
    echo
    log "📋 Next steps:"
    echo "1. Start/restart the LUCA service:"
    echo "   sudo systemctl restart luca.service"
    echo
    echo "2. Check service status:"
    echo "   sudo systemctl status luca.service"
    echo
    echo "3. Run health check:"
    echo "   ./scripts/check_health.sh"
    echo
    local public_ip=$(curl -s http://checkip.amazonaws.com 2>/dev/null || echo "your-server-ip")
    echo "4. Access the application:"
    echo "   https://$public_ip/"
    echo
}

# Check if running as the correct user
if [[ $EUID -eq 0 ]]; then
    error "This script should not be run as root. Please run as ubuntu user."
    exit 1
fi

# Run main function
main "$@"