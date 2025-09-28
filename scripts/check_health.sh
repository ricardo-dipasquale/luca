#!/bin/bash

# LUCA Health Check Script
# Verifies the health and status of LUCA application components

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Check systemd service status
check_systemd_service() {
    log "🔧 Checking LUCA systemd service..."

    if systemctl is-active --quiet luca.service; then
        echo "✅ LUCA service is running"
    else
        error "❌ LUCA service is not running"
        echo "Status: $(systemctl is-active luca.service)"
        echo "Try: sudo systemctl start luca.service"
        return 1
    fi

    if systemctl is-enabled --quiet luca.service; then
        echo "✅ LUCA service is enabled for startup"
    else
        warn "⚠️  LUCA service is not enabled for startup"
        echo "Enable with: sudo systemctl enable luca.service"
    fi
}

# Check Docker containers
check_docker_containers() {
    log "🐳 Checking Docker containers..."

    if ! command -v docker-compose &> /dev/null; then
        error "❌ docker-compose not found"
        return 1
    fi

    cd /opt/luca

    # Check if containers are running
    local containers=$(docker-compose ps --services)
    local running_containers=$(docker-compose ps --services --filter "status=running")

    echo "📦 Container Status:"
    for container in $containers; do
        if docker-compose ps $container | grep -q "Up"; then
            echo "  ✅ $container: Running"
        else
            echo "  ❌ $container: Not running"
            docker-compose logs --tail=10 $container
        fi
    done
}

# Check application connectivity
check_application_connectivity() {
    log "🌐 Checking application connectivity..."

    # Check HTTPS endpoint
    if curl -k -f -s https://localhost/ > /dev/null; then
        echo "✅ HTTPS endpoint is responding"
    else
        error "❌ HTTPS endpoint is not responding"
    fi

    # Get and display public IP
    PUBLIC_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null || echo "Unable to determine")
    echo "📍 Public IP: $PUBLIC_IP"

    if [[ "$PUBLIC_IP" != "Unable to determine" ]]; then
        echo "🔗 Application URL: https://$PUBLIC_IP/"
    fi
}

# Check Neo4j connectivity
check_neo4j() {
    log "🗄️  Checking Neo4j database..."

    cd /opt/luca

    # Check Neo4j container health
    if docker-compose exec neo4j cypher-shell -u neo4j -p neo4jpassword "RETURN 'Neo4j is working' as message" 2>/dev/null | grep -q "Neo4j is working"; then
        echo "✅ Neo4j database is responding"

        # Get node count
        local node_count=$(docker-compose exec neo4j cypher-shell -u neo4j -p neo4jpassword "MATCH (n) RETURN count(n) as total" 2>/dev/null | grep -o '[0-9]\+' | head -1)
        echo "📊 Total nodes in database: ${node_count:-'Unable to determine'}"

    else
        error "❌ Neo4j database is not responding"
        echo "Check Neo4j logs with: docker-compose logs neo4j"
    fi
}

# Check SSL certificates
check_ssl_certificates() {
    log "🔒 Checking SSL certificates..."

    local ssl_dir="/opt/luca/ssl"

    if [[ -f "$ssl_dir/luca.crt" && -f "$ssl_dir/luca.key" ]]; then
        echo "✅ SSL certificates found"

        # Check certificate expiration
        local cert_expiry=$(openssl x509 -in "$ssl_dir/luca.crt" -noout -enddate 2>/dev/null | cut -d= -f2)
        if [[ -n "$cert_expiry" ]]; then
            echo "📅 Certificate expires: $cert_expiry"

            # Check if certificate expires in next 30 days
            local expiry_timestamp=$(date -d "$cert_expiry" +%s 2>/dev/null || echo "0")
            local current_timestamp=$(date +%s)
            local days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))

            if [[ $days_until_expiry -lt 30 && $days_until_expiry -gt 0 ]]; then
                warn "⚠️  Certificate expires in $days_until_expiry days"
            elif [[ $days_until_expiry -le 0 ]]; then
                error "❌ Certificate has expired!"
            else
                echo "✅ Certificate is valid for $days_until_expiry days"
            fi
        fi
    else
        error "❌ SSL certificates not found in $ssl_dir"
    fi
}

# Check disk usage
check_disk_usage() {
    log "💾 Checking disk usage..."

    local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    echo "💽 Root disk usage: ${disk_usage}%"

    if [[ $disk_usage -gt 80 ]]; then
        warn "⚠️  Disk usage is above 80%"
    elif [[ $disk_usage -gt 90 ]]; then
        error "❌ Disk usage is above 90%"
    else
        echo "✅ Disk usage is acceptable"
    fi

    # Check Docker disk usage
    echo "🐳 Docker system usage:"
    docker system df 2>/dev/null || echo "Unable to check Docker disk usage"
}

# Check memory usage
check_memory_usage() {
    log "🧠 Checking memory usage..."

    local mem_info=$(free -m | awk 'NR==2{printf "%.1f", $3*100/$2}')
    echo "💭 Memory usage: ${mem_info}%"

    if (( $(echo "$mem_info > 80" | bc -l) )); then
        warn "⚠️  Memory usage is above 80%"
    elif (( $(echo "$mem_info > 90" | bc -l) )); then
        error "❌ Memory usage is above 90%"
    else
        echo "✅ Memory usage is acceptable"
    fi
}

# Check environment configuration
check_environment() {
    log "⚙️  Checking environment configuration..."

    local env_file="/opt/luca/.env"

    if [[ -f "$env_file" ]]; then
        echo "✅ Environment file found"

        # Check critical variables
        local critical_vars=("NEO4J_PASSWORD" "OPENAI_API_KEY" "FLASK_SECRET_KEY")

        for var in "${critical_vars[@]}"; do
            if grep -q "^${var}=CAMBIAR" "$env_file" 2>/dev/null; then
                error "❌ $var still has default value - needs to be configured"
            elif grep -q "^${var}=" "$env_file" 2>/dev/null; then
                echo "✅ $var is configured"
            else
                warn "⚠️  $var not found in environment file"
            fi
        done

        # Check Langfuse status
        if grep -q "^LANGFUSE_ENABLED=false" "$env_file" 2>/dev/null; then
            echo "✅ Langfuse is disabled (recommended for basic setup)"
        elif grep -q "^LANGFUSE_ENABLED=true" "$env_file" 2>/dev/null; then
            echo "ℹ️  Langfuse is enabled"
        fi

    else
        error "❌ Environment file not found at $env_file"
    fi
}

# Show recent logs
show_recent_logs() {
    log "📋 Recent application logs..."

    cd /opt/luca

    echo "🔍 Last 10 lines from LUCA application:"
    docker-compose logs --tail=10 luca 2>/dev/null || echo "Unable to fetch logs"

    echo
    echo "🔍 Last 5 lines from Neo4j:"
    docker-compose logs --tail=5 neo4j 2>/dev/null || echo "Unable to fetch logs"
}

# Generate summary report
generate_summary() {
    log "📊 Health Check Summary"
    echo "=================================="
    echo "🕒 Check completed at: $(date)"
    echo "🖥️  Hostname: $(hostname)"
    echo "📍 Public IP: $(curl -s http://checkip.amazonaws.com 2>/dev/null || echo 'Unable to determine')"
    echo "🔗 Application URL: https://$(curl -s http://checkip.amazonaws.com 2>/dev/null || echo 'your-ip')/"
    echo "=================================="
}

# Main health check function
main() {
    echo "🏥 LUCA Health Check"
    echo "===================="
    echo

    # Perform all health checks
    check_systemd_service
    echo

    check_docker_containers
    echo

    check_application_connectivity
    echo

    check_neo4j
    echo

    check_ssl_certificates
    echo

    check_disk_usage
    echo

    check_memory_usage
    echo

    check_environment
    echo

    show_recent_logs
    echo

    generate_summary

    echo
    log "🎉 Health check completed!"
}

# Check if script is run with proper permissions
if [[ ! -d "/opt/luca" ]]; then
    error "LUCA application directory not found at /opt/luca"
    echo "Run the deployment script first: ./scripts/deploy_aws.sh"
    exit 1
fi

# Run main function
main "$@"