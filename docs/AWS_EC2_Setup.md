# AWS EC2 Setup Guide - LUCA Application

Esta guía explica cómo desplegar la aplicación LUCA en AWS EC2 usando Docker Compose como daemon persistente.

## 📋 Requisitos Previos

- Cuenta AWS activa
- Conocimientos básicos de AWS EC2
- Claves de API de OpenAI
- Dominio o subdominio para HTTPS (opcional pero recomendado)

## 🏗️ Configuración de la Instancia EC2

### 1. Especificaciones Recomendadas

**Para 20 conversaciones diarias:**
- **Tipo de instancia**: `t3.medium` (2 vCPU, 4 GB RAM)
- **Storage**: 20 GB gp3 (suficiente para logs y datos)
- **Sistema operativo**: Ubuntu 22.04 LTS
- **Costo estimado**: ~$30/mes

**Para mayor carga (50+ conversaciones/día):**
- **Tipo de instancia**: `t3.large` (2 vCPU, 8 GB RAM)
- **Storage**: 30 GB gp3
- **Costo estimado**: ~$60/mes

### 2. Configuración de Security Groups

Crear un Security Group con las siguientes reglas:

```bash
# SSH access (restringir a tu IP)
Port 22 - TCP - Source: Tu IP pública

# HTTPS access
Port 443 - TCP - Source: 0.0.0.0/0

# HTTP access (opcional para redirect)
Port 80 - TCP - Source: 0.0.0.0/0

# Neo4j Browser (opcional, solo para debugging)
Port 7474 - TCP - Source: Tu IP pública
```

### 3. Lanzar la Instancia

```bash
# 1. Seleccionar Ubuntu 22.04 LTS
# 2. Elegir t3.medium
# 3. Configurar storage: 20 GB gp3
# 4. Asignar Security Group creado
# 5. Crear o usar Key Pair existente
# 6. Lanzar instancia
```

## 🚀 Instalación y Configuración

### Opción A: Instalación Automática (Recomendada)

```bash
# Conectar a la instancia
ssh -i tu-keypair.pem ubuntu@tu-instancia-ip

# Clonar el repositorio
git clone https://github.com/tu-usuario/luca.git /tmp/luca
cd /tmp/luca

# Ejecutar script de instalación automática
./scripts/deploy_aws.sh

# Configurar variables de entorno interactivamente
./scripts/configure_env.sh

# Copiar código de aplicación
sudo cp -r . /opt/luca/
sudo chown -R ubuntu:ubuntu /opt/luca

# Iniciar la aplicación
sudo systemctl start luca.service

# Verificar el estado
./scripts/check_health.sh
```

### Opción B: Instalación Manual

### 1. Conexión SSH a la Instancia

```bash
# Conectar a la instancia
ssh -i tu-keypair.pem ubuntu@tu-instancia-ip

# Actualizar el sistema
sudo apt update && sudo apt upgrade -y
```

### 2. Instalación de Dependencias

```bash
# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
newgrp docker

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verificar instalación
docker --version
docker-compose --version
```

### 3. Preparación del Directorio de Aplicación

```bash
# Crear directorio para la aplicación
sudo mkdir -p /opt/luca
sudo chown ubuntu:ubuntu /opt/luca
cd /opt/luca

# Clonar el repositorio (o subir archivos)
git clone https://github.com/tu-usuario/luca.git .
# O subir archivos usando scp/rsync desde tu máquina local
```

### 4. Configuración de Variables de Entorno

```bash
# Crear archivo de configuración persistente
sudo nano /opt/luca/.env
```

**Contenido del archivo `.env`:**

```bash
# ===== CONFIGURACIÓN OBLIGATORIA =====

# Neo4j Database Configuration
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=tu_password_neo4j_seguro_123

# OpenAI API Configuration
OPENAI_API_KEY=sk-tu-clave-openai-aqui

# Flask Application Security
FLASK_SECRET_KEY=tu-clave-secreta-para-flask-muy-larga-y-segura

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
```

### 5. Configuración de SSL/HTTPS

#### Opción A: Certificados Auto-firmados (Para desarrollo/testing)

```bash
# Generar certificados SSL auto-firmados
cd /opt/luca
python scripts/generate_ssl_certs.py --domain=$(curl -s http://checkip.amazonaws.com) --output-dir=ssl

# Verificar que se crearon los certificados
ls -la ssl/
```

#### Opción B: Let's Encrypt (Para producción - RECOMENDADO)

```bash
# Instalar Certbot
sudo apt install certbot -y

# Obtener certificados (reemplazar con tu dominio)
sudo certbot certonly --standalone -d tu-dominio.com

# Copiar certificados al directorio de la aplicación
sudo mkdir -p /opt/luca/ssl
sudo cp /etc/letsencrypt/live/tu-dominio.com/fullchain.pem /opt/luca/ssl/luca.crt
sudo cp /etc/letsencrypt/live/tu-dominio.com/privkey.pem /opt/luca/ssl/luca.key
sudo chown ubuntu:ubuntu /opt/luca/ssl/*

# Configurar renovación automática
sudo crontab -e
# Agregar línea: 0 12 * * * /usr/bin/certbot renew --quiet && docker-compose -f /opt/luca/docker-compose.yml restart luca
```

### 6. Preparación de Directorios de Neo4j

```bash
# Crear directorios para Neo4j con permisos correctos
cd /opt/luca
mkdir -p db/data db/logs db/import db/plugins
sudo chmod -R 755 db/
```

### 7. Descargar Plugins de Neo4j

```bash
# Descargar APOC plugin
cd /opt/luca/db/plugins
wget https://github.com/neo4j-contrib/neo4j-apoc-procedures/releases/download/5.26.0/apoc-5.26.0-core.jar

# Descargar Graph Data Science plugin
wget https://github.com/neo4j/graph-data-science/releases/download/2.13.2/neo4j-graph-data-science-2.13.2.jar

# Verificar descarga
ls -la /opt/luca/db/plugins/
```

## 🔧 Configuración de Docker Compose como Daemon

### 1. Crear Servicio Systemd

```bash
# Crear archivo de servicio
sudo nano /etc/systemd/system/luca.service
```

**Contenido del archivo `luca.service`:**

```ini
[Unit]
Description=LUCA Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/luca
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
ExecReload=/usr/local/bin/docker-compose restart
TimeoutStartSec=0
User=ubuntu
Group=docker

[Install]
WantedBy=multi-user.target
```

### 2. Configurar Reinicio Automático de Docker

```bash
# Configurar Docker para restart automático
sudo systemctl enable docker

# Crear archivo de configuración para restart policy
sudo nano /etc/docker/daemon.json
```

**Contenido de `daemon.json`:**

```json
{
  "live-restore": true,
  "restart": true
}
```

```bash
# Reiniciar Docker daemon
sudo systemctl restart docker
```

### 3. Habilitar y Probar el Servicio

```bash
# Recargar systemd
sudo systemctl daemon-reload

# Habilitar el servicio para inicio automático
sudo systemctl enable luca.service

# Iniciar el servicio
sudo systemctl start luca.service

# Verificar estado
sudo systemctl status luca.service

# Ver logs del servicio
journalctl -u luca.service -f
```

## 🗄️ Inicialización de la Base de Datos

### 1. Esperar que Neo4j esté disponible

```bash
# Verificar que Neo4j esté funcionando
docker-compose logs neo4j

# Esperar mensaje: "Remote interface available at http://localhost:7474/"
```

### 2. Crear el Knowledge Graph

```bash
# Navegar al directorio de la aplicación
cd /opt/luca

# Ejecutar script de creación del grafo
docker-compose exec luca python db/create_kg.py

# Verificar que el grafo se creó correctamente
docker-compose exec luca python -c "
from kg.connection import KGConnection
conn = KGConnection()
with conn.get_session() as session:
    result = session.run('MATCH (n) RETURN count(n) as total')
    print(f'Total nodes: {result.single()[\"total\"]}')
"
```

### 3. Crear Usuario Inicial (Opcional)

```bash
# Crear usuario de prueba
docker-compose exec luca python -c "
from kg.connection import KGConnection
import datetime

conn = KGConnection()
with conn.get_session() as session:
    session.run('''
        MERGE (u:Usuario {email: 'admin@uca.edu.ar'})
        SET u.password = 'admin123',
            u.nombre = 'Administrador',
            u.created_at = datetime(),
            u.last_login = datetime()
    ''')
    print('Usuario admin@uca.edu.ar creado con password: admin123')
"
```

## 🔍 Verificación y Testing

### 1. Verificar Estado de los Servicios

```bash
# Ver estado de todos los contenedores
docker-compose ps

# Ver logs de la aplicación
docker-compose logs luca

# Ver logs de Neo4j
docker-compose logs neo4j

# Ver logs del LLM Graph Builder
docker-compose logs llm-graph-builder
```

### 2. Probar Conectividad

```bash
# Obtener IP pública de la instancia
PUBLIC_IP=$(curl -s http://checkip.amazonaws.com)
echo "IP Pública: $PUBLIC_IP"

# Probar HTTPS (desde tu máquina local)
curl -k -I https://$PUBLIC_IP/

# O desde la instancia
curl -k -I https://localhost/
```

### 3. Probar la Aplicación Web

1. **Abrir navegador** en: `https://tu-ip-publica-ec2`
2. **Aceptar certificado** auto-firmado (o usar dominio si configuraste Let's Encrypt)
3. **Login** con: `visitante@uca.edu.ar` / `visitante!`
4. **Probar conversación** con el agente

## 🔄 Persistencia y Recuperación

### 1. Persistencia de Datos

Los siguientes datos son persistentes y sobreviven a reinicios de EC2:

```bash
# Datos de Neo4j
/opt/luca/db/data/          # Base de datos del grafo
/opt/luca/db/logs/          # Logs de Neo4j

# Configuración
/opt/luca/.env              # Variables de entorno
/opt/luca/ssl/              # Certificados SSL

# Logs de aplicación (dentro de contenedores Docker)
```

### 2. Verificar Persistencia después de Reinicio

```bash
# Simular reinicio (CUIDADO: esto reinicia la instancia)
sudo reboot

# Después del reinicio, verificar que todo esté funcionando
ssh -i tu-keypair.pem ubuntu@tu-instancia-ip
sudo systemctl status luca.service
docker-compose ps
```

### 3. Backup y Recuperación

#### Backup de la Base de Datos

```bash
# Crear script de backup
cat > /opt/luca/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/luca/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

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
EOF

chmod +x /opt/luca/backup.sh
```

#### Programar Backups Automáticos

```bash
# Agregar al crontab
crontab -e

# Agregar línea para backup diario a las 2 AM
0 2 * * * /opt/luca/backup.sh
```

## 🔐 Configuración de Seguridad

### 1. Firewall con UFW

```bash
# Instalar y configurar firewall
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 443/tcp
sudo ufw allow 80/tcp
sudo ufw status
```

### 2. Configuración de SSH

```bash
# Deshabilitar login con password (solo key-based)
sudo nano /etc/ssh/sshd_config

# Cambiar/agregar estas líneas:
# PasswordAuthentication no
# PubkeyAuthentication yes
# PermitRootLogin no

# Reiniciar SSH
sudo systemctl restart sshd
```

### 3. Actualizaciones Automáticas

```bash
# Instalar actualizaciones automáticas
sudo apt install unattended-upgrades -y
sudo dpkg-reconfigure unattended-upgrades

# Configurar actualizaciones automáticas
echo 'Unattended-Upgrade::Automatic-Reboot "false";' | sudo tee -a /etc/apt/apt.conf.d/50unattended-upgrades
```

## 📊 Monitoreo y Logs

### 1. Monitoreo Básico

```bash
# Ver uso de recursos
htop

# Ver logs en tiempo real
docker-compose logs -f luca

# Ver espacio en disco
df -h

# Ver memoria
free -m
```

### 2. Configurar Rotación de Logs

```bash
# Configurar logrotate para Docker
sudo nano /etc/logrotate.d/docker-compose

# Contenido:
/opt/luca/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    notifempty
    create 644 ubuntu ubuntu
}
```

### 3. Alertas Básicas

```bash
# Script de health check
cat > /opt/luca/health-check.sh << 'EOF'
#!/bin/bash
if ! curl -k -f https://localhost/ > /dev/null 2>&1; then
    echo "ALERT: LUCA application is down!" | mail -s "LUCA Health Check Failed" tu-email@gmail.com
    sudo systemctl restart luca.service
fi
EOF

chmod +x /opt/luca/health-check.sh

# Agregar al crontab para verificar cada 5 minutos
echo "*/5 * * * * /opt/luca/health-check.sh" | crontab -
```

## 🚨 Troubleshooting

### Problemas Comunes

1. **Servicio no inicia**:
   ```bash
   sudo systemctl status luca.service
   journalctl -u luca.service
   ```

2. **Puerto 443 ocupado**:
   ```bash
   sudo lsof -i :443
   sudo systemctl stop apache2  # Si Apache está instalado
   ```

3. **Permisos de SSL**:
   ```bash
   sudo chown ubuntu:ubuntu /opt/luca/ssl/*
   sudo chmod 600 /opt/luca/ssl/luca.key
   sudo chmod 644 /opt/luca/ssl/luca.crt
   ```

4. **Neo4j no inicia**:
   ```bash
   docker-compose logs neo4j
   sudo chown -R 7474:7474 /opt/luca/db/data
   ```

### Logs Importantes

```bash
# Logs del sistema
journalctl -u luca.service

# Logs de la aplicación
docker-compose logs luca

# Logs de Neo4j
docker-compose logs neo4j

# Logs del sistema
sudo tail -f /var/log/syslog
```

## 🤖 Scripts de Automatización

LUCA incluye varios scripts para automatizar tareas comunes de despliegue y mantenimiento:

### 1. Script de Despliegue Automático

```bash
# Instalación completa automatizada
./scripts/deploy_aws.sh
```

**Funcionalidades:**
- ✅ Instalación de Docker y Docker Compose
- ✅ Configuración de directorios de aplicación
- ✅ Descarga de plugins de Neo4j
- ✅ Generación de certificados SSL auto-firmados
- ✅ Creación de servicio systemd
- ✅ Configuración de firewall
- ✅ Creación de script de backup automático

### 2. Script de Configuración de Variables

```bash
# Configuración interactiva de variables de entorno
./scripts/configure_env.sh
```

**Funcionalidades:**
- ✅ Configuración guiada de variables obligatorias
- ✅ Validación de claves de API de OpenAI
- ✅ Generación de passwords seguros
- ✅ Test de conectividad con Neo4j
- ✅ Backup automático de configuración existente

### 3. Script de Verificación de Estado

```bash
# Health check completo del sistema
./scripts/check_health.sh
```

**Funcionalidades:**
- ✅ Estado de servicio systemd
- ✅ Estado de contenedores Docker
- ✅ Conectividad de aplicación (HTTPS)
- ✅ Estado de base de datos Neo4j
- ✅ Validación de certificados SSL
- ✅ Uso de disco y memoria
- ✅ Verificación de configuración
- ✅ Logs recientes de aplicación

### Uso Típico de los Scripts

```bash
# 1. Despliegue inicial
./scripts/deploy_aws.sh

# 2. Configurar variables
./scripts/configure_env.sh

# 3. Copiar código de aplicación
sudo cp -r . /opt/luca/
sudo chown -R ubuntu:ubuntu /opt/luca

# 4. Iniciar servicio
sudo systemctl start luca.service

# 5. Verificar estado
./scripts/check_health.sh

# 6. Monitoreo continuo
watch -n 30 './scripts/check_health.sh'
```

## 📝 Resumen de Comandos Útiles

```bash
# Estado del servicio
sudo systemctl status luca.service

# Reiniciar aplicación
sudo systemctl restart luca.service

# Ver logs en tiempo real
docker-compose logs -f

# Backup manual
/opt/luca/backup.sh

# Health check completo
./scripts/check_health.sh

# Reconfigurar variables
./scripts/configure_env.sh

# Verificar conectividad
curl -k -I https://localhost/

# Entrar a Neo4j browser (desde tu IP)
# http://tu-ip-ec2:7474

# Conectar por SSH
ssh -i tu-keypair.pem ubuntu@tu-ip-ec2
```

## 💰 Estimación de Costos

**Para instancia t3.medium en us-east-1:**
- **EC2**: ~$30/mes
- **Storage (20 GB)**: ~$2/mes
- **Data Transfer**: ~$1-5/mes (dependiendo del tráfico)
- **Total estimado**: ~$35-40/mes

**Optimizaciones de costo:**
- Usar Reserved Instances (descuento 30-60%)
- Programar parada automática en horarios no laborales
- Usar Spot Instances para testing/desarrollo

---

Esta configuración asegura que la aplicación LUCA funcione como daemon persistente en EC2, manteniéndose disponible a través de reinicios y con toda la configuración necesaria para un entorno de producción.