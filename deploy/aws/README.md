# LUCA en AWS: se apaga sola y se despierta cuando alguien entra

Guía paso a paso desde la consola de AWS. Usa la misma configuración endurecida de [deploy/README.md](../README.md) (Caddy, secretos como archivos, contenedores sin privilegios) sobre una instancia EC2. Le agrega dos cosas:

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

## Costos aproximados

Son valores de referencia en `us-east-1`; confirmalos en la [calculadora de AWS](https://calculator.aws/). En `sa-east-1` (São Paulo) la latencia desde Argentina es menor y los precios, un 50 % más altos.

| Recurso | Cuándo se paga | Aproximado |
|---|---|---|
| EC2 `t4g.medium` (2 vCPU, 4 GB) | sólo prendida | USD 0,034/hora |
| Disco EBS gp3 30 GB | siempre | USD 2,4/mes |
| Elastic IP | siempre (prendida o apagada) | USD 3,6/mes |
| Lambda + Function URL | por uso | prácticamente USD 0 |
| Snapshots diarios (7 días) | siempre | USD 1 a 2/mes |

Por ejemplo, con 60 horas de uso por mes queda en unos USD 9 a 10. El costo grande sigue siendo OpenAI: configurá el límite de gasto (paso 1 de [deploy/README.md](../README.md#1-la-key-de-openai-antes-de-tocar-el-servidor)).

`t4g.medium` usa procesadores ARM (Graviton). Todas las imágenes (Caddy, Chroma, la app) tienen versión ARM. Con 2 GB (`t4g.small`) la memoria queda justa: la app y Chroma tienen hasta 1 GB cada una, y además está el build de la imagen.

## 1. Antes de empezar

- Hacé el paso 1 de [deploy/README.md](../README.md#1-la-key-de-openai-antes-de-tocar-el-servidor): una key de OpenAI nueva, exclusiva de producción y con límite de gasto.
- Elegí la región en la consola (arriba a la derecha) y usá la misma en todos los pasos.

## 2. IP fija (Elastic IP)

**EC2 → Elastic IPs → Allocate Elastic IP address → Allocate.**

Anotá la IP (por ejemplo `52.1.2.3`). Es la dirección de la app y no cambia al apagar y prender la instancia.

## 3. Security group

**EC2 → Security Groups → Create security group**, nombre `luca-web`:

| Tipo | Puerto | Origen |
|---|---|---|
| HTTP | 80 | `0.0.0.0/0` |
| HTTPS | 443 | `0.0.0.0/0` |

No abras el 22 (SSH): se entra con Session Manager (paso 4), que no necesita puertos abiertos. El puerto 80 hace falta para que Let's Encrypt valide la IP; Caddy redirige todo lo demás a HTTPS.

## 4. Rol de la instancia (para entrar sin SSH)

**IAM → Roles → Create role** → *AWS service* → *EC2* → política **`AmazonSSMManagedInstanceCore`** → nombre `luca-ec2`.

Con este rol, la instancia queda accesible desde **EC2 → la instancia → Connect → Session Manager**, sin claves SSH ni puertos abiertos. El rol no tiene ningún otro permiso: la instancia no puede tocar nada más de la cuenta.

## 5. Crear la instancia

**EC2 → Instances → Launch instances**:

- **Name**: `luca`
- **AMI**: Ubuntu Server 24.04 LTS, arquitectura **64-bit (Arm)**
- **Instance type**: `t4g.medium`
- **Key pair**: *Proceed without a key pair* (se entra por Session Manager)
- **Network settings → Edit**: *Auto-assign public IP*: **Disable** (la IP pública es la Elastic IP); *Select existing security group*: `luca-web`
- **Storage**: 30 GiB, **gp3**, y en *Advanced* → **Encrypted: Yes**
- **Advanced details**:
  - *IAM instance profile*: `luca-ec2`
  - *Shutdown behavior*: **Stop**. **Importante**: con *Terminate*, el apagado por inactividad borraría la instancia.
  - *Termination protection*: **Enable**
  - *Metadata version*: **V2 only (token required)**

**Launch instance.** Después, en **Elastic IPs**, elegí la IP → **Actions → Associate Elastic IP address** → la instancia `luca`.

Anotá el **Instance ID** (`i-0...`): lo usa la Lambda.

## 6. Instalar Docker y LUCA en la instancia

Entrá por **Connect → Session Manager → Connect**. La sesión arranca como `ssm-user`.

```bash
sudo -i                                   # todo lo que sigue, como root
curl -fsSL https://get.docker.com | sh    # Docker Engine + plugin de Compose (script oficial)
systemctl enable docker                   # que Docker (y los contenedores) arranquen con la máquina
```

**Código.** Si el repo es privado, usá una *deploy key* de sólo lectura:

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
EOF
```

Después seguí los pasos 4 (secretos) y 5 (levantar) de [deploy/README.md](../README.md#4-secretos), incluida la carga de usuarios. Al final:

```bash
curl -sI https://52.1.2.3/healthz | head -1     # HTTP/2 200, con certificado válido
```

Si el certificado no sale, mirá `docker compose -f docker-compose.prod.yml logs caddy` (ver [Problemas frecuentes](#problemas-frecuentes)).

## 7. Apagado por inactividad

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

## 8. La Lambda que la despierta

**8.1 Crear la función.** **Lambda → Create function**:

- *Author from scratch*, nombre `luca-wake`, runtime **Python 3.13**, arquitectura **arm64**
- *Permissions*: *Create a new role with basic Lambda permissions*

En la pestaña **Code**, reemplazá el contenido de `lambda_function.py` por el de [wake/lambda_function.py](wake/lambda_function.py) y apretá **Deploy**. En **Runtime settings → Edit**, poné *Handler*: `lambda_function.handler`.

**8.2 Configuración** (pestaña **Configuration**):

- *General configuration → Edit*: **Timeout 10 s**, memoria 128 MB.
- *Environment variables*:
  - `LUCA_INSTANCE_ID` = `i-0...` (paso 5)
  - `LUCA_APP_URL` = `https://52.1.2.3`
- *Concurrency → Edit → Reserve concurrency*: **5**. Así, aunque alguien la bombardee, el costo queda acotado.

**8.3 Permisos.** En *Permissions*, hacé clic en el rol → **Add permissions → Create inline policy → JSON**. Reemplazá región, cuenta e instancia:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": "ec2:DescribeInstances", "Resource": "*" },
    { "Effect": "Allow", "Action": "ec2:StartInstances",
      "Resource": "arn:aws:ec2:REGION:CUENTA:instance/i-0..." }
  ]
}
```

`DescribeInstances` no admite limitarse a una instancia; `StartInstances` sí. La Lambda sólo puede prender esa máquina: no puede apagarla, borrarla ni tocar ninguna otra cosa.

**8.4 URL pública.** *Configuration → Function URL → Create function URL*: **Auth type NONE**, *Invoke mode* **BUFFERED**. La URL que aparece (`https://xxxx.lambda-url.REGION.on.aws/`) es **la que se comparte con estudiantes**.

## 9. Verificar

1. Con la instancia prendida, abrí la URL de la Lambda: tiene que redirigir a `https://52.1.2.3/` y mostrar el login.
2. Probá el ciclo completo con un tiempo corto:
   - `echo LUCA_IDLE_MINUTES=10 > /etc/default/luca-idle`.
   - Esperá a que la instancia pase a *Stopped* en la consola. Como el arranque cuenta como actividad, tarda entre 10 y 15 minutos desde que arrancó o desde el último uso.
   - Abrí la URL de la Lambda: "Luca está dormida" → **Despertar a Luca** → "Se está despertando…" → login.
   - Volvé a 60: `rm /etc/default/luca-idle`.
3. Desde afuera, que no responda nada más que 80 y 443: `nc -zv 52.1.2.3 22 5000 8000`.

## 10. Backups automáticos

**EC2 → Lifecycle Manager → Create lifecycle policy** → *EBS snapshot policy*:

- Target: la instancia `luca` (por tag `Name = luca`)
- Frecuencia: diaria
- Retención: 7

El snapshot incluye la base SQLite (usuarios con sus hashes y conversaciones), así que no lo compartas. Para backups puntuales, ver *Backup* en [deploy/README.md](../README.md#operación).

## Operación

- **Actualizar**: despertala, `touch /etc/luca-idle-disabled`, seguí *Actualizar* de [deploy/README.md](../README.md#operación) y después `rm /etc/luca-idle-disabled`.
- **Apagarla a mano**: **EC2 → Instance state → Stop**. La próxima visita la puede despertar.
- **Dejarla prendida un día entero** (por ejemplo, un parcial): `touch /etc/luca-idle-disabled` y borrarlo al terminar.
- **Ver cuándo se apagó**: `journalctl -u luca-idle.service`.

## Limitaciones

- **La URL es larga**: si molesta, se puede acortar más adelante con un dominio. En ese caso se pasa a `Caddyfile` con `LUCA_DOMAIN` igual al dominio.
- **Hay que entrar siempre por la URL de la Lambda.** Quien guarde `https://52.1.2.3` en favoritos y entre con la máquina apagada ve un error de conexión, porque nadie atiende en esa IP.
- **El navegador muestra la IP** en la barra de direcciones una vez dentro de la app.
- **Los certificados para IP duran 6 días.** Caddy los renueva solo. Si la máquina estuvo apagada más tiempo, los renueva al arrancar: la página "Se está despertando…" espera a que el certificado sea válido.

## Problemas frecuentes

- **Caddy no obtiene el certificado de la IP.** Revisá estas tres cosas:
  - que el puerto 80 esté abierto (paso 3);
  - que `LUCA_DOMAIN` sea exactamente la Elastic IP;
  - que `LUCA_CADDYFILE=Caddyfile.ip` esté en `.env`.

  Si Let's Encrypt sigue rechazando la IP, una alternativa sin dominio propio es `LUCA_DOMAIN=52-1-2-3.sslip.io` con `LUCA_CADDYFILE=Caddyfile`. Ese nombre resuelve a la IP y lleva un certificado común. En ese caso, `LUCA_APP_URL` de la Lambda también pasa a ese nombre.
- **La Lambda siempre muestra "Se está despertando…"**: la instancia está prendida, pero la Lambda no llega a `LUCA_APP_URL/healthz`. Probá `curl -sI https://52.1.2.3/healthz` desde tu máquina y mirá los logs de la Lambda en **Monitor → View CloudWatch logs**.
- **No se apaga nunca**: `journalctl -u luca-idle.service` muestra cada revisión. Revisá que no exista `/etc/luca-idle-disabled` y mirá la fecha de modificación del archivo de actividad: `stat $(docker volume inspect luca_luca_data -f '{{ .Mountpoint }}')/last_activity`.
