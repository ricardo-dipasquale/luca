# LUCA en AWS: se apaga sola y se despierta cuando alguien entra

Guía de instalación en el servidor. La infraestructura de AWS (instancia, IP fija, Lambda, permisos y backups) se arma antes, a mano, con quien administra la cuenta: [INFRA.md](INFRA.md). Usa la misma configuración endurecida de [deploy/README.md](../README.md) (Caddy, secretos como archivos, contenedores sin privilegios) sobre una instancia EC2. Le agrega dos cosas:

- **Apagado por inactividad**: si nadie usa LUCA durante 1 hora, la instancia se apaga sola.
- **Despertar a demanda**: la URL que reciben las y los estudiantes es la de una Lambda que está siempre disponible. Si la instancia está apagada, muestra el botón "Despertar a Luca" y redirige a la app cuando está lista.

No hace falta un dominio: la app se sirve en `https://<IP fija>`, con un certificado de Let's Encrypt para la IP.

## Cómo funciona

```
estudiante ──► URL de la Lambda (siempre disponible, gratis sin uso)
                 │  ¿la instancia está prendida y la app responde?
                 ├─ sí ─► redirige a https://<IP fija>  ──► Caddy ──► app + Chroma (EC2)
                 ├─ apagada ─► página "Luca está dormida" + botón ─► prende la instancia
                 └─ arrancando ─► "Se está despertando…" (se recarga cada 5 s hasta que la app responde)

EC2: cada 5 min, luca-idle.timer mira la última actividad; tras 60 min sin uso, apaga la máquina.
```

- **Qué cuenta como actividad**: sólo los pedidos de estudiantes logueados. La app toca el archivo `last_activity` del volumen de datos como máximo una vez por minuto. Los bots, los chequeos de salud y los logins fallidos no cuentan.
- **Por qué hay un botón**: en internet hay bots que visitan URLs todo el tiempo. Si una visita alcanzara para prender la máquina, no se apagaría nunca. Los bots no aprietan botones (no hacen POST).
- **Gracia al arrancar**: el arranque cuenta como actividad. Si alguien la despierta y no entra, se vuelve a apagar a la hora.
- **Qué se pierde al apagarse**: sólo lo que vive en memoria, es decir, los contadores del límite de intentos de login y de uso. Usuarios, conversaciones, memoria del tutor y apuntes están en el disco.
- **Cuánto tarda en despertar**: alrededor de 1 a 2 minutos (arranque de la máquina, Docker, Chroma y la app).

## Costos

Unos USD 9 a 10/mes con 60 horas de uso, en `us-east-1`; el detalle está en [INFRA.md](INFRA.md#qué-es-y-qué-se-arma). El costo grande sigue siendo OpenAI: configurá el límite de gasto (paso 1 de [deploy/README.md](../README.md#1-la-key-de-openai-antes-de-tocar-el-servidor)).

## 1. Antes de empezar

- **La infraestructura**: se arma en la consola de AWS con quien administra la cuenta, siguiendo [INFRA.md](INFRA.md). Al terminar, te tiene que pasar la tabla de datos: región, Elastic IP, Instance ID, URL de la Lambda y tu acceso por Session Manager. En lo que sigue, `52.1.2.3` es la Elastic IP.
- **La key de OpenAI**: hacé el paso 1 de [deploy/README.md](../README.md#1-la-key-de-openai-antes-de-tocar-el-servidor): una key nueva, exclusiva de producción y con límite de gasto.

## 2. Instalar Docker y LUCA en la instancia

En la consola de AWS: **EC2 → la instancia `luca` → Connect → Session Manager → Connect**. La sesión arranca como `ssm-user`.

```bash
sudo -i                                   # todo lo que sigue, como root
curl -fsSL https://get.docker.com | sh    # Docker Engine + plugin de Compose (script oficial)
systemctl enable docker                   # que Docker (y los contenedores) arranquen con la máquina
```

**Código.** Si el repo es público, alcanza con HTTPS:

```bash
git clone https://github.com/ricardo-dipasquale/luca.git /opt/luca && cd /opt/luca
```

Si el repo es privado, usá una *deploy key* de sólo lectura, generada y usada por el mismo usuario (root):

```bash
ssh-keygen -t ed25519 -N "" -f ~/.ssh/luca_deploy
cat ~/.ssh/luca_deploy.pub     # GitHub → el repo → Settings → Deploy keys → Add (sin "Allow write access")
cat >> ~/.ssh/config <<'EOF'
Host github.com
  IdentityFile ~/.ssh/luca_deploy
EOF
git clone git@github.com:ricardo-dipasquale/luca.git /opt/luca && cd /opt/luca
```

Mientras esto no esté en `main`, agregá `git checkout deploy-aws-autostop`.

**Configuración** (`.env`, sin secretos). `LUCA_DOMAIN` es la Elastic IP:

```bash
cat > .env <<'EOF'
LUCA_DOMAIN=52.1.2.3
LUCA_ACME_EMAIL=tu-email@uca.edu.ar
LUCA_CADDYFILE=Caddyfile.ip
LUCA_ADMINS=tu-email@uca.edu.ar
EOF
```

`LUCA_ADMINS` es la cuenta (o las cuentas, separadas por coma) que ve `/admin` para dar de alta estudiantes.

Después seguí los pasos 4 (secretos) y 5 (levantar) de [deploy/README.md](../README.md#4-secretos). Al final:

```bash
curl -sI https://52.1.2.3/healthz | head -1     # HTTP/2 200, con certificado válido
```

**Cuenta de administración.** No hay una de fábrica: creá la tuya con una contraseña provisoria. `read -s` evita que quede en el historial; LUCA te la hace cambiar al primer ingreso:

```bash
read -rsp "Contraseña provisoria (8+ caracteres): " PROV; echo; export PROV
docker compose -f docker-compose.prod.yml run --rm --no-deps -e PROV luca python -c \
  "import os; from storage import db; db.upsert_user('tu-email@uca.edu.ar', os.environ['PROV'], 'Tu Nombre', provisional=True)"
unset PROV
```

El resto de los usuarios se carga desde `https://52.1.2.3/admin`: de a uno, o con la planilla (hay un enlace para descargar la plantilla).

Si el certificado no sale, mirá `docker compose -f docker-compose.prod.yml logs caddy` (ver [Problemas frecuentes](#problemas-frecuentes)).

## 3. Apagado por inactividad

En la instancia, como root, desde `/opt/luca`:

```bash
install -m 755 deploy/aws/luca-idle-check.sh /usr/local/bin/luca-idle-check
install -m 644 deploy/aws/luca-idle.service deploy/aws/luca-idle.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now luca-idle.timer
systemctl list-timers luca-idle.timer       # próxima revisión
```

Para cambiar el tiempo sin uso (por defecto 60 minutos): `echo LUCA_IDLE_MINUTES=90 > /etc/default/luca-idle`.

**Mantenimiento**: mientras trabajás en la máquina, `touch /etc/luca-idle-disabled` evita que se apague. Al terminar, `rm /etc/luca-idle-disabled`.

## 4. Verificar

1. Con la instancia prendida, abrí la URL de la Lambda: tiene que redirigir a `https://52.1.2.3/` y mostrar el login. Antes de terminar el paso 2 muestra «Se está despertando…», porque la app todavía no responde.
2. Probá el ciclo completo con un tiempo corto:
   - `echo LUCA_IDLE_MINUTES=10 > /etc/default/luca-idle`.
   - Esperá a que la instancia pase a *Stopped* en la consola. Como el arranque cuenta como actividad, tarda entre 10 y 15 minutos desde que arrancó o desde el último uso.
   - Abrí la URL de la Lambda: "Luca está dormida" → **Despertar a Luca** → "Se está despertando…" → login.
   - Volvé a 60: `rm /etc/default/luca-idle`.
3. Desde afuera, que no responda nada más que 80 y 443: `nc -zv 52.1.2.3 22 5000 8000`.

## Operación

- **Actualizar**: despertala, `touch /etc/luca-idle-disabled`, seguí *Actualizar* de [deploy/README.md](../README.md#operación) y después `rm /etc/luca-idle-disabled`.
- **Apagarla a mano**: **EC2 → Instance state → Stop**, o `systemctl poweroff` desde la sesión. La próxima visita la puede despertar.
- **Dejarla prendida un día entero** (por ejemplo, un parcial): `touch /etc/luca-idle-disabled` y borrarlo al terminar.
- **Ver cuándo se apagó**: `journalctl -u luca-idle.service`.

## Limitaciones

- **La URL es larga**: si molesta, se puede acortar más adelante con un dominio. En ese caso se pasa a `Caddyfile` con `LUCA_DOMAIN` igual al dominio.
- **Hay que entrar siempre por la URL de la Lambda.** Quien guarde `https://52.1.2.3` en favoritos y entre con la máquina apagada ve un error de conexión, porque nadie atiende en esa IP.
- **El navegador muestra la IP** en la barra de direcciones una vez dentro de la app.
- **Los certificados para IP duran 6 días.** Caddy los renueva solo. Si la máquina estuvo apagada más tiempo, los renueva al arrancar: la página "Se está despertando…" espera a que el certificado sea válido.

## Problemas frecuentes

- **Caddy no obtiene el certificado de la IP.** Revisá estas tres cosas:
  - que el puerto 80 esté abierto en el security group ([INFRA.md](INFRA.md#2-security-group));
  - que `LUCA_DOMAIN` sea exactamente la Elastic IP;
  - que `LUCA_CADDYFILE=Caddyfile.ip` esté en `.env`.

  Si Let's Encrypt sigue rechazando la IP, una alternativa sin dominio propio es `LUCA_DOMAIN=52-1-2-3.sslip.io` con `LUCA_CADDYFILE=Caddyfile`. Ese nombre resuelve a la IP y lleva un certificado común. En ese caso, `LUCA_APP_URL` de la Lambda también pasa a ese nombre: pedíselo a quien administra la cuenta.
- **La Lambda siempre muestra "Se está despertando…"**: la instancia está prendida, pero la Lambda no llega a `LUCA_APP_URL/healthz`. Probá `curl -sI https://52.1.2.3/healthz` desde tu máquina y mirá los logs de la Lambda en **Lambda → luca-wake → Monitor → View CloudWatch logs**. Si cambió la Elastic IP, hay que actualizar `LUCA_APP_URL` en la Lambda ([INFRA.md](INFRA.md#5-lambda-luca-wake)).
- **No se apaga nunca**: `journalctl -u luca-idle.service` muestra cada revisión. Revisá que no exista `/etc/luca-idle-disabled` y mirá la fecha de modificación del archivo de actividad: `stat $(docker volume inspect luca_luca_data -f '{{ .Mountpoint }}')/last_activity`.
