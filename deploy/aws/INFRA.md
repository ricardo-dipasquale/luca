# LUCA: infraestructura en AWS (para armar en la consola)

Este documento es para quien administra la cuenta de AWS. Describe qué recursos crear, con qué configuración y por qué. La instalación de la aplicación en el servidor la hace después el equipo de LUCA ([README.md](README.md)).

## Qué es y qué se arma

LUCA es un tutor web para la materia Bases de Datos (UCA). Corre en una sola máquina virtual con Docker: un proxy HTTPS (Caddy), la aplicación (Flask) y una base vectorial (Chroma). Los datos viven en el disco de esa máquina, en SQLite.

Como se usa sólo durante la cursada, **la máquina se apaga sola tras 1 hora sin uso**. Para que se pueda despertar, estudiantes y docentes entran siempre por la URL de una **Lambda**, que está siempre disponible:
- si la máquina está prendida, la Lambda redirige a la app;
- si está apagada, muestra un botón «Despertar a Luca», prende la máquina y redirige cuando la app responde (1 a 2 minutos).

```
navegador ──► Lambda luca-wake (Function URL pública)
                 ├─ máquina prendida ─► redirige a https://<Elastic IP> ─► EC2 luca (Caddy :443)
                 └─ máquina apagada ─► página con botón ─► ec2:StartInstances sobre esa instancia
EC2 luca: se apaga a sí misma (shutdown del sistema operativo) tras 60 min sin uso.
```

No hay dominio: la app se sirve en `https://<Elastic IP>`, con un certificado de Let's Encrypt para la IP, que obtiene Caddy.

| # | Recurso | Nombre sugerido | Para qué |
|---|---|---|---|
| 1 | Elastic IP | `luca` | Dirección fija de la app; no cambia al apagar y prender |
| 2 | Security group | `luca-web` | Entrada sólo por 80 y 443 |
| 3 | Rol IAM de la instancia | `luca-ec2` | Entrar por Session Manager, sin SSH |
| 4 | Instancia EC2 | `luca` | La aplicación |
| 5 | Lambda + Function URL | `luca-wake` | La URL pública, que despierta la máquina |
| 6 | Política de snapshots (DLM) | `luca-diario` | Backup diario del disco |
| 7 | Presupuesto (Budgets) | `luca` | Alerta si el gasto se dispara |
| 8 | Acceso para el equipo de LUCA | `luca-operador` | Entrar al servidor y prender o apagar la instancia, nada más |

**Región:** usá la misma en todos los pasos. `sa-east-1` (São Paulo) tiene menos latencia desde Argentina; `us-east-1` es alrededor de un 50 % más barata. Costo estimado en `us-east-1`, con 60 horas de uso por mes: USD 9 a 10/mes. Se paga sólo mientras la máquina está prendida, salvo el disco (unos USD 2,4/mes) y la Elastic IP (unos USD 3,6/mes, que se cobra aunque la máquina esté apagada). Confirmalo en la [calculadora de AWS](https://calculator.aws/).

**Etiquetas:** conviene poner `Project = luca` en todos los recursos para identificar los costos.

## Datos a completar durante el armado

Pasale esta tabla completa al equipo de LUCA. No contiene secretos.

| Dato | Se obtiene en | Valor |
|---|---|---|
| Región | — | |
| Elastic IP | paso 1 | |
| Instance ID | paso 4 | `i-…` |
| Account ID | arriba a la derecha en la consola | |
| URL de la Lambda | paso 5.4 | `https://….lambda-url.….on.aws/` |
| Acceso del equipo de LUCA (usuario o permission set) | paso 8 | |

## 1. Elastic IP

**EC2 → Elastic IPs → Allocate Elastic IP address → Allocate.** Ponele el tag `Name = luca`.

## 2. Security group

**EC2 → Security Groups → Create security group**: nombre `luca-web`, en la VPC donde va la instancia (la default sirve).

| Entrada | Puerto | Origen | Motivo |
|---|---|---|---|
| HTTP | 80 | `0.0.0.0/0` | Let's Encrypt valida la IP por HTTP; Caddy redirige el resto a HTTPS |
| HTTPS | 443 | `0.0.0.0/0` | La app |

**Salida:** la regla por defecto (todo). La instancia necesita salir a internet para Let's Encrypt, la API de OpenAI, GitHub, Docker Hub y Session Manager.

**No abras el 22.** El acceso administrativo es por Session Manager (paso 3).

## 3. Rol de la instancia

**IAM → Roles → Create role**:

1. *Trusted entity type*: **AWS service**. *Use case*: **EC2**, la primera opción («Allows EC2 instances to call AWS services on your behalf»), no las de Spot ni las otras → *Next*.
2. *Add permissions*: buscá y tildá la política administrada **`AmazonSSMManagedInstanceCore`**. Es la única → *Next*.
3. *Role name*: **`luca-ec2`** → *Create role*.

Es el único permiso de la instancia: le permite registrarse en Session Manager. No puede leer ni modificar ningún otro recurso de la cuenta.

## 4. Instancia EC2

**EC2 → Instances → Launch instances**:

| Opción | Valor | Motivo |
|---|---|---|
| Name | `luca` | |
| AMI | **Ubuntu Server 24.04 LTS**, y en el selector *Architecture* (a la derecha) **64-bit (Arm)** | La consola propone x86 por defecto, y `t4g` no la acepta |
| Instance type | **`t4g.medium`** (2 vCPU, 4 GB, Arm) | La app y Chroma usan hasta 1 GB cada una, y la imagen se construye en el servidor. Con una AMI x86, el equivalente es `t3.medium` (alrededor de un 20 % más cara) |
| Key pair | *Proceed without a key pair* | Se entra por Session Manager |
| Subnet | Una pública (con ruta a un Internet Gateway) | |
| Auto-assign public IP | **Disable** | La IP pública es la Elastic IP |
| Security group | `luca-web` | |
| Storage | **30 GiB gp3**, *Encrypted*: **Yes** (la clave por defecto `aws/ebs` alcanza) | El disco tiene los datos de estudiantes |
| IAM instance profile | `luca-ec2` | |
| **Shutdown behavior** | **Stop** | **Crítico.** La instancia se apaga sola por inactividad; con *Terminate* se borraría |
| Termination protection | **Enable** | |
| Metadata version | **V2 only (token required)** | |
| Tags | `Name = luca`, `Project = luca` | El tag `Name` lo usan los snapshots (paso 6) |

**Launch instance.** Cuando esté *Running*: **Elastic IPs** → la IP `luca` → **Actions → Associate Elastic IP address** → instancia `luca`.

**Comprobación** (a los pocos minutos de asociar la Elastic IP): **EC2 → Instances** → tildá `luca` → **Connect** → pestaña **Session Manager**. Si el botón **Connect** está habilitado, la instancia quedó registrada. También aparece en **Systems Manager → Node Tools → Fleet Manager** con *SSM Agent ping status* **Online**. Si Systems Manager ofrece configurarse para la organización («Get started»), no hace falta.

Si no se registra en unos 10 minutos:
- **El rol.** En la pestaña **Security** de la instancia tiene que figurar *IAM Role* `luca-ec2`. Si no está, asignalo en **Actions → Security → Modify IAM role** y reiniciá la instancia.
- **La salida a internet.** Si Session Manager muestra *«SSM Agent unable to acquire credentials … RequestError: send request failed»*, es un problema de red, no del rol. Revisá estas tres cosas y después hacé **Instance state → Reboot instance**, para que el agente reintente enseguida en vez de esperar:
  1. la Elastic IP asociada: en la pestaña **Networking**, *Public IPv4 address*. Es la causa habitual, porque la instancia arranca sin IP pública hasta que se asocia;
  2. en el security group, la regla de salida *All traffic* a `0.0.0.0/0`;
  3. en la tabla de rutas de la subnet, `0.0.0.0/0` hacia un `igw-…`.

  El mensaje puede seguir figurando como «último error» un rato después de conectarse: lo que vale es que **Connect** quede habilitado.

## 5. Lambda `luca-wake`

**5.1 Crear.** **Lambda → Create function → Author from scratch**:
- Nombre `luca-wake`, runtime **Python 3.13**, arquitectura **arm64**.
- *Execution role*: **Create a new role with basic Lambda permissions**. Incluye sólo los logs de CloudWatch.

**5.2 Código.** En la pestaña **Code**, reemplazá el contenido de `lambda_function.py` por el archivo `deploy/aws/wake/lambda_function.py` que te pasa el equipo de LUCA. Usa sólo la biblioteca estándar y `boto3`, que ya viene en el runtime. Apretá **Deploy**. En **Runtime settings → Edit**, poné *Handler*: `lambda_function.handler`.

**5.3 Configuración** (pestaña **Configuration**):

| Opción | Valor |
|---|---|
| General → Timeout | **10 s** (memoria: 128 MB) |
| Environment variables | `LUCA_INSTANCE_ID` = el Instance ID del paso 4 · `LUCA_APP_URL` = `https://<Elastic IP>` (sin `/` al final) |
| Concurrency → Reserved concurrency | **5**. Acota el costo si alguien la bombardea |

**5.4 Permisos.** Abrí el rol de ejecución que se creó (*Configuration → Permissions → el nombre del rol*) → **Add permissions → Create inline policy → JSON** → nombre `luca-wake-start`. Reemplazá `REGION`, `CUENTA` e `INSTANCIA`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Sid": "ReadState", "Effect": "Allow", "Action": "ec2:DescribeInstances", "Resource": "*" },
    { "Sid": "StartLuca", "Effect": "Allow", "Action": "ec2:StartInstances",
      "Resource": "arn:aws:ec2:REGION:CUENTA:instance/INSTANCIA" }
  ]
}
```

`DescribeInstances` no admite restringirse a un recurso. `StartInstances` queda limitado a esa instancia: la Lambda no puede apagar, borrar ni prender ninguna otra cosa. Como el disco usa la clave por defecto `aws/ebs`, no hace falta ningún permiso de KMS para prenderla. Si usaste una clave propia, agregá `kms:CreateGrant` sobre esa clave.

**5.5 URL pública.** *Configuration → Function URL → Create function URL*:
- *Auth type*: **NONE**. Es pública a propósito: la abren estudiantes sin cuenta de AWS.
- *Invoke mode*: **BUFFERED**.

Esa URL es **la que se comparte con estudiantes**. La Lambda no atiende otras rutas (responde 404) y sólo prende la máquina con un POST, es decir, con el botón. Las visitas de bots no la despiertan.

## 6. Backups (Data Lifecycle Manager)

**EC2 → Lifecycle Manager → Create lifecycle policy → EBS snapshot policy**:
- *Target resource*: Instance, tag **`Name = luca`**.
- *Schedule*: diario, retención **7**.
- *Copy tags from source*: sí.

Los snapshots tienen datos de estudiantes (usuarios con contraseñas hasheadas, conversaciones). No los compartas con otras cuentas ni los hagas públicos.

## 7. Presupuesto

**Billing → Budgets → Create budget → Cost budget**: mensual, por ejemplo USD 20, con filtro por tag `Project = luca` si los tags de costos están activados. Configurá alertas al 80 % y al 100 % por email, a vos y al equipo de LUCA.

El gasto de OpenAI no pasa por AWS. Se controla con un límite de gasto en la cuenta de OpenAI, y de eso se ocupa el equipo de LUCA.

## 8. Acceso para el equipo de LUCA

El equipo necesita entrar al servidor por Session Manager para instalar y actualizar la app, y poder prender o apagar la instancia. No necesita nada más. Crealo como permission set de IAM Identity Center o como usuario o grupo de IAM, según cómo maneje los accesos la cuenta. Reemplazá `REGION`, `CUENTA` e `INSTANCIA`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Sid": "SeeTheInstance", "Effect": "Allow",
      "Action": ["ec2:DescribeInstances", "ec2:DescribeInstanceStatus", "ssm:DescribeInstanceInformation",
                 "ssm:DescribeSessions", "ssm:GetConnectionStatus"],
      "Resource": "*" },
    { "Sid": "StartStopLuca", "Effect": "Allow",
      "Action": ["ec2:StartInstances", "ec2:StopInstances", "ec2:RebootInstances"],
      "Resource": "arn:aws:ec2:REGION:CUENTA:instance/INSTANCIA" },
    { "Sid": "ShellOnLuca", "Effect": "Allow", "Action": "ssm:StartSession",
      "Resource": ["arn:aws:ec2:REGION:CUENTA:instance/INSTANCIA",
                   "arn:aws:ssm:REGION::document/SSM-SessionManagerRunShell"] },
    { "Sid": "OwnSessions", "Effect": "Allow", "Action": ["ssm:TerminateSession", "ssm:ResumeSession"],
      "Resource": "arn:aws:ssm:*:*:session/${aws:userid}-*" },
    { "Sid": "LambdaLogs", "Effect": "Allow",
      "Action": ["logs:DescribeLogStreams", "logs:GetLogEvents", "logs:FilterLogEvents"],
      "Resource": "arn:aws:logs:REGION:CUENTA:log-group:/aws/lambda/luca-wake:*" }
  ]
}
```

Con Identity Center, la variable de sesión puede requerir `${aws:username}` en lugar de `${aws:userid}`. Si al terminar una sesión aparece *AccessDenied*, probá con la otra.

Si preferís que el equipo no prenda ni apague la instancia desde la consola, sacá el bloque `StartStopLuca`. Pueden despertarla desde la URL de la Lambda.

## Lista de control

- [ ] Elastic IP asociada a la instancia `luca`
- [ ] Security group con entrada sólo 80 y 443; sin 22
- [ ] Instancia: Ubuntu 24.04 Arm, `t4g.medium`, disco 30 GiB gp3 **cifrado**, IMDSv2, **Shutdown behavior = Stop**, termination protection
- [ ] La instancia aparece *Online* en Fleet Manager
- [ ] Lambda `luca-wake`: código, handler `lambda_function.handler`, timeout 10 s, variables de entorno, concurrencia reservada 5, política `luca-wake-start`
- [ ] Function URL creada (NONE, BUFFERED). Al abrirla, muestra «Luca está dormida» si la instancia está apagada, o «Se está despertando…» si está prendida y la app todavía no está instalada
- [ ] Snapshots diarios con retención 7
- [ ] Presupuesto con alertas
- [ ] Acceso del equipo de LUCA creado y probado: abre una sesión en la instancia desde *Connect → Session Manager*
- [ ] Tabla de [datos](#datos-a-completar-durante-el-armado) completa y enviada al equipo de LUCA

## Para más adelante

- **Dominio propio** (por ejemplo `luca.uca.edu.ar`): un registro A a la Elastic IP. El equipo de LUCA cambia la configuración de Caddy; la infraestructura no cambia.
- **Borrar todo:** desactivá la termination protection y terminá la instancia. Después borrá la Lambda y su rol, la política DLM y los snapshots, el security group y el rol `luca-ec2`, y liberá la Elastic IP (si queda asignada sin usar, se sigue cobrando).
