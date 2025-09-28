# Scripts de Automatización - LUCA

Esta documentación describe los scripts de automatización incluidos en LUCA para facilitar el despliegue y mantenimiento en AWS EC2.

## 📋 Resumen de Scripts

| Script | Propósito | Uso |
|--------|-----------|-----|
| `deploy_aws.sh` | Instalación automática completa | `./scripts/deploy_aws.sh` |
| `configure_env.sh` | Configuración interactiva de variables | `./scripts/configure_env.sh` |
| `check_health.sh` | Verificación de estado del sistema | `./scripts/check_health.sh` |

## 🚀 `deploy_aws.sh` - Script de Despliegue

### Propósito
Automatiza la instalación completa de LUCA en una instancia EC2 Ubuntu 22.04 LTS nueva.

### Funcionalidades
- ✅ Verificación de sistema operativo (Ubuntu)
- ✅ Instalación de Docker y Docker Compose
- ✅ Configuración de directorios de aplicación (`/opt/luca`)
- ✅ Descarga automática de plugins Neo4j (APOC, Graph Data Science)
- ✅ Generación de certificados SSL auto-firmados
- ✅ Creación de archivo `.env` con valores por defecto
- ✅ Configuración de servicio systemd para inicio automático
- ✅ Creación de script de backup
- ✅ Configuración básica de firewall (UFW)

### Uso
```bash
# Desde una instancia EC2 Ubuntu nueva
wget https://raw.githubusercontent.com/tu-repo/luca/main/scripts/deploy_aws.sh
chmod +x deploy_aws.sh
./deploy_aws.sh
```

### Resultado
- Directorio `/opt/luca` configurado
- Docker instalado y configurado
- Servicio systemd `luca.service` creado pero no iniciado
- Certificados SSL generados
- Archivo `.env` creado (requiere configuración)

### Siguientes Pasos Después del Script
1. Configurar variables de entorno con `configure_env.sh`
2. Copiar código de aplicación a `/opt/luca`
3. Iniciar servicio con `systemctl start luca.service`

## ⚙️ `configure_env.sh` - Configuración Interactiva

### Propósito
Proporciona configuración guiada e interactiva de todas las variables de entorno necesarias.

### Funcionalidades
- ✅ Interfaz interactiva con valores por defecto
- ✅ Validación de formato de claves OpenAI API
- ✅ Test de conectividad con OpenAI API
- ✅ Generación automática de passwords seguros
- ✅ Test de conectividad con Neo4j
- ✅ Backup automático de configuración existente
- ✅ Soporte para configuraciones sensibles (ocultar input)

### Variables Configuradas

#### Obligatorias:
- `NEO4J_USERNAME` - Usuario de Neo4j
- `NEO4J_PASSWORD` - Password de Neo4j (generado automáticamente si es nuevo)
- `OPENAI_API_KEY` - Clave API de OpenAI (validada)
- `FLASK_SECRET_KEY` - Clave secreta de Flask (generada automáticamente)

#### Opcionales:
- `DEFAULT_LLM_MODEL` - Modelo LLM a usar
- `DEFAULT_LLM_TEMPERATURE` - Temperatura del modelo
- `LANGFUSE_ENABLED` - Habilitar/deshabilitar observabilidad

### Uso
```bash
cd /opt/luca
./scripts/configure_env.sh
```

### Validaciones Incluidas
- **OpenAI API Key**: Formato `sk-*` con longitud mínima y test de conectividad
- **Neo4j Connection**: Test de conectividad si Docker está corriendo
- **Password Security**: Generación de passwords de 25+ caracteres

## 🏥 `check_health.sh` - Verificación de Estado

### Propósito
Realiza un health check completo del sistema LUCA para verificar que todos los componentes funcionen correctamente.

### Verificaciones Realizadas

#### 1. Systemd Service
- ✅ Estado del servicio `luca.service`
- ✅ Configuración de inicio automático

#### 2. Docker Containers
- ✅ Estado de contenedores (neo4j, luca, llm-graph-builder)
- ✅ Logs recientes en caso de errores

#### 3. Conectividad de Aplicación
- ✅ Respuesta del endpoint HTTPS
- ✅ Detección de IP pública
- ✅ URLs de acceso

#### 4. Base de Datos Neo4j
- ✅ Conectividad con Neo4j
- ✅ Conteo de nodos en la base de datos
- ✅ Estado del contenedor

#### 5. Certificados SSL
- ✅ Presencia de archivos de certificado
- ✅ Fecha de expiración
- ✅ Alertas para certificados próximos a vencer

#### 6. Recursos del Sistema
- ✅ Uso de disco (alertas >80%, >90%)
- ✅ Uso de memoria (alertas >80%, >90%)
- ✅ Uso de disco de Docker

#### 7. Configuración
- ✅ Validación de variables críticas
- ✅ Detección de valores por defecto no configurados
- ✅ Estado de Langfuse

#### 8. Logs y Diagnósticos
- ✅ Logs recientes de aplicación
- ✅ Logs de Neo4j
- ✅ Información de sistema

### Uso
```bash
cd /opt/luca
./scripts/check_health.sh

# Para monitoreo continuo
watch -n 30 './scripts/check_health.sh'
```

### Ejemplo de Salida
```
🏥 LUCA Health Check
====================

🔧 Checking LUCA systemd service...
✅ LUCA service is running
✅ LUCA service is enabled for startup

🐳 Checking Docker containers...
📦 Container Status:
  ✅ neo4j: Running
  ✅ luca: Running
  ✅ llm-graph-builder: Running

🌐 Checking application connectivity...
✅ HTTPS endpoint is responding
📍 Public IP: 54.123.45.67
🔗 Application URL: https://54.123.45.67/

🗄️ Checking Neo4j database...
✅ Neo4j database is responding
📊 Total nodes in database: 1247

🔒 Checking SSL certificates...
✅ SSL certificates found
📅 Certificate expires: Dec 25 23:59:59 2024 GMT
✅ Certificate is valid for 89 days

💾 Checking disk usage...
💽 Root disk usage: 23%
✅ Disk usage is acceptable

🧠 Checking memory usage...
💭 Memory usage: 45.2%
✅ Memory usage is acceptable

⚙️ Checking environment configuration...
✅ Environment file found
✅ NEO4J_PASSWORD is configured
✅ OPENAI_API_KEY is configured
✅ FLASK_SECRET_KEY is configured
✅ Langfuse is disabled (recommended for basic setup)
```

## 🔄 Flujo de Trabajo Típico

### Despliegue Inicial
```bash
# 1. Conexión a EC2
ssh -i keypair.pem ubuntu@ec2-ip

# 2. Despliegue automático
git clone https://github.com/tu-repo/luca.git /tmp/luca
cd /tmp/luca
./scripts/deploy_aws.sh

# 3. Configuración
./scripts/configure_env.sh

# 4. Instalación de código
sudo cp -r . /opt/luca/
sudo chown -R ubuntu:ubuntu /opt/luca

# 5. Inicialización
cd /opt/luca
sudo systemctl start luca.service

# 6. Verificación
./scripts/check_health.sh
```

### Mantenimiento Regular
```bash
# Health check diario
./scripts/check_health.sh

# Backup manual
/opt/luca/backup.sh

# Reconfiguración si es necesario
./scripts/configure_env.sh
sudo systemctl restart luca.service
```

### Troubleshooting
```bash
# Verificar estado completo
./scripts/check_health.sh

# Ver logs detallados
sudo systemctl status luca.service
docker-compose logs luca
docker-compose logs neo4j

# Reiniciar servicios
sudo systemctl restart luca.service

# Reconfigurar si hay problemas de variables
./scripts/configure_env.sh
```

## 🔧 Personalización de Scripts

### Modificar Variables por Defecto
Editar las variables en `configure_env.sh`:
```bash
# Cambiar modelo LLM por defecto
local llm_model=$(prompt_with_default "LLM Model" "gpt-4o")  # En lugar de gpt-4o-mini
```

### Agregar Validaciones Adicionales
En `check_health.sh`, agregar nuevas verificaciones:
```bash
# Ejemplo: verificar puerto específico
check_custom_port() {
    if nc -z localhost 8080; then
        echo "✅ Custom service on port 8080 is running"
    else
        echo "❌ Custom service on port 8080 is not responding"
    fi
}
```

### Personalizar Configuración de Sistema
En `deploy_aws.sh`, modificar la configuración del firewall:
```bash
# Agregar puertos adicionales
sudo ufw allow 8080/tcp  # Para servicio personalizado
```

## 📚 Recursos Adicionales

- **Documentación completa**: [`docs/AWS_EC2_Setup.md`](./AWS_EC2_Setup.md)
- **Variables de entorno**: Ver `.env.example` en el directorio raíz
- **Troubleshooting**: Sección específica en la documentación principal
- **Monitoreo**: Scripts incluyen alertas automáticas para problemas comunes

---

Estos scripts están diseñados para hacer el despliegue de LUCA en AWS EC2 lo más simple y confiable posible, minimizando la configuración manual y proporcionando verificación continua del estado del sistema.