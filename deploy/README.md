# Publicar LUCA

Guía para levantar LUCA en un servidor (por ejemplo, una instancia EC2 con Ubuntu) con `docker-compose.prod.yml`.

La key de OpenAI ya fue robada una vez. Por eso esta guía está armada para que la key esté siempre en un solo lugar del servidor (un archivo legible sólo por la app) y para que ningún servicio interno quede expuesto a internet.

## Qué protege esta configuración

| Riesgo | Medida |
|---|---|
| La key queda en la imagen, en el repo o en `docker inspect` | Se monta como Docker secret (`/run/secrets/openai_api_key`); nunca va en `environment:`. `.dockerignore` y `.gitignore` excluyen `secrets/`, `.env*`, `*.pem`, `*.key`, `ssl/` |
| Un servicio interno publicado sin autenticación (como el `llm-graph-builder` del despliegue anterior, con la key adentro) | Sólo Caddy publica puertos (80/443). La app y Chroma no tienen puertos publicados; Chroma está en una red interna sin salida a internet |
| Docker se saltea el firewall del host | Docker publica puertos por fuera de `ufw`: no alcanza con el firewall. Por eso ningún otro servicio publica puertos, y el security group de AWS es la barrera real |
| Tráfico sin cifrar o cookies robables | TLS automático (Let's Encrypt) con HSTS; cookies de sesión `Secure`, `HttpOnly`, `SameSite=Lax`, vencen a las 12 h |
| Contenedor comprometido | Usuario sin privilegios (uid 10001), sistema de archivos de sólo lectura, sin capabilities, `no-new-privileges`, límites de memoria y procesos |
| Fuerza bruta en el login | Máximo 5 intentos fallidos por email y 20 por IP cada 15 minutos (la IP la fija Caddy; no se puede falsificar con `X-Forwarded-For`) |
| Gasto descontrolado de la key | Mensajes de hasta 4000 caracteres; límite por alumno (10/min, 100/h, 300/día por defecto); límite de gasto en OpenAI (ver abajo) |
| XSS o librerías de CDN alteradas | CSP restrictiva, respuestas del tutor sanitizadas, hash de integridad (SRI) en cada librería de CDN |
| Errores que filtran detalles internos | El cliente recibe un mensaje genérico; el detalle queda en los logs del servidor |

## 1. La key de OpenAI (antes de tocar el servidor)

En [platform.openai.com](https://platform.openai.com):

1. **Revocá la key anterior** y cualquier key que haya estado en un `.env`, en un chat o en un servidor viejo.
2. Creá un **proyecto exclusivo para producción** y una key nueva dentro de ese proyecto. No uses la misma key en desarrollo.
3. En el proyecto, configurá un **límite de gasto mensual** y alertas de uso. Si la key se filtra, el daño queda acotado.
4. Restringí los permisos de la key a lo que LUCA usa: modelos de chat y embeddings.
5. Revisá periódicamente el uso del proyecto; un pico inexplicable es la primera señal de una filtración.

## 2. Servidor

- Ubuntu con Docker Engine y el plugin de Compose (`docker compose version`).
- **Security group / firewall de la nube**: entrada sólo 80 y 443 desde cualquier lado, y 22 (SSH) sólo desde tu IP. Nada más.
- Un registro DNS `A` del dominio (por ejemplo `luca.uca.edu.ar`) apuntando a la IP pública del servidor, antes del primer arranque: Caddy lo necesita para obtener el certificado.

## 3. Código y configuración

```bash
git clone git@github.com:ricardo-dipasquale/luca.git && cd luca
```

`.env` (sólo configuración no secreta, la lee `docker compose`):

```bash
cat > .env <<'EOF'
LUCA_DOMAIN=luca.uca.edu.ar
LUCA_ACME_EMAIL=tu-email@uca.edu.ar
EOF
```

Opcionales en `.env`: `DEFAULT_LLM_MODEL`, `EMBEDDING_MODEL`, `GUARDRAILS_MAX_REQUESTS_PER_MINUTE/HOUR/DAY`.

## 4. Secretos

```bash
mkdir -p secrets
umask 077
read -rsp "OpenAI API key: " KEY && printf '%s' "$KEY" > secrets/openai_api_key && unset KEY; echo
python3 -c "import secrets; print(secrets.token_hex(32), end='')" > secrets/flask_secret_key
sudo chown 10001:10001 secrets/*      # el usuario de la app dentro del contenedor
sudo chmod 400 secrets/*
```

`read -s` evita que la key quede en el historial de la terminal o en pantalla. Después de este paso, ni tu usuario puede leer los archivos sin `sudo`.

## 5. Levantar

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d chroma
docker compose -f docker-compose.prod.yml --profile tools run --rm ingest   # prácticas + apuntes
docker compose -f docker-compose.prod.yml up -d
```

La ingesta en el servidor sólo reconstruye las prácticas e indexa los apuntes. Las soluciones (`content/soluciones_generadas.json`) se generan y revisan en desarrollo y llegan por `git pull`, así el servidor nunca modifica el contenido.

Usuarios (planilla con nombre en la 1.ª columna, email en la 3.ª y contraseña en la 4.ª):

```bash
docker compose -f docker-compose.prod.yml run --rm --no-deps \
  -v "$PWD/usuarios-luca.xlsx:/tmp/usuarios.xlsx:ro" luca \
  python scripts/import_usuarios.py --file /tmp/usuarios.xlsx
rm usuarios-luca.xlsx    # tiene contraseñas en texto plano
```

A quien ya existe no se le cambia la contraseña, porque puede haberla cambiado desde LUCA. Para blanquear la de quien la olvidó, agregá `--reset-passwords` con una planilla que tenga sólo esas filas.

## 6. Verificar

```bash
curl -sI https://luca.uca.edu.ar/healthz | grep -iE "^HTTP|strict-transport|content-security"
curl -s -o /dev/null -w "%{http_code}\n" http://luca.uca.edu.ar/        # 308: redirige a HTTPS
docker compose -f docker-compose.prod.yml ps                              # sólo caddy con puertos
docker compose -f docker-compose.prod.yml config | grep -c "sk-"         # 0: la key no está en la config
```

Y desde afuera del servidor, que ningún otro puerto responda (por ejemplo `nc -zv luca.uca.edu.ar 5000 8000 7474`).

## Operación

**Actualizar** (código, contenido o soluciones aprobadas):

```bash
git pull
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml --profile tools run --rm ingest
docker compose -f docker-compose.prod.yml up -d
```

**Rotar la key de OpenAI**: crear la nueva en OpenAI, reemplazar `secrets/openai_api_key` (mismo procedimiento del paso 4), `docker compose -f docker-compose.prod.yml up -d --force-recreate luca`, y recién entonces revocar la anterior.

**Backup de usuarios y conversaciones** (volumen `luca_luca_data`):

```bash
docker compose -f docker-compose.prod.yml exec luca python -c \
  "import sqlite3; sqlite3.connect('/app/data/luca.db').backup(sqlite3.connect('/app/data/backup.db'))"
mkdir -p backups
docker run --rm -v luca_luca_data:/data:ro -v "$PWD/backups:/backup" alpine \
  cp /data/backup.db "/backup/luca-$(date +%F).db"
```

Guardá los backups fuera del servidor: tienen los hashes de las contraseñas y las conversaciones de los alumnos.

**Logs**: `docker compose -f docker-compose.prod.yml logs -f luca` (rotan a 5 × 10 MB por servicio).

## Notas

- La app corre con un solo proceso de gunicorn (8 threads): el límite de intentos de login y el de uso por alumno viven en memoria, y SQLite admite un solo escritor.
- `docker-compose.yml` (sin `.prod`) es sólo para desarrollo local.
