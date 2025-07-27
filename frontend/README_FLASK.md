# LUCA Flask Frontend

## 🚀 Nuevo Frontend Flask para LUCA

Este frontend Flask reemplaza la aplicación Streamlit para resolver los problemas de compatibilidad con AsyncIO y persistencia de LangGraph en conversaciones multi-turno.

## 📋 Características

### ✅ Ventajas sobre Streamlit
- **Sin conflictos de AsyncIO**: Cada request maneja su propio event loop
- **Conversaciones multi-turno estables**: No hay colgado en mensajes de seguimiento
- **Mejor manejo de persistencia**: Compatible con Neo4j persistence de LangGraph
- **Interfaz más responsive**: Sin recargas de página completas
- **Mejor debugging**: Logs más claros y debugging más fácil

### 🎨 Interfaz de Usuario
- **Diseño moderno con Bootstrap 5**: Interfaz limpia y profesional
- **Branding UCA**: Colores y estilo institucional
- **Chat en tiempo real**: Mensajes streaming con indicadores de progreso
- **Sidebar de conversaciones**: Gestión de múltiples conversaciones
- **Selector de materias**: Dropdown con materias disponibles del KG
- **Autenticación UCA**: Login con credenciales @uca.edu.ar

## 🛠️ Instalación y Ejecución

### 1. Instalar dependencias
```bash
cd frontend
pip install flask flask-cors
```

### 2. Ejecutar la aplicación
```bash
python run_flask.py
```

### 3. Acceder a la aplicación
- **URL**: http://localhost:5000
- **Credenciales de prueba**:
  - Email: `visitante@uca.edu.ar`
  - Contraseña: `visitante!`

## 🏗️ Arquitectura

### Estructura de archivos
```
frontend/
├── flask_app.py              # Aplicación Flask principal
├── run_flask.py              # Script de ejecución
├── templates/
│   ├── base.html              # Template base con estilos
│   ├── login.html             # Página de login
│   └── chat.html              # Interfaz principal de chat
├── auth.py                    # Módulo de autenticación (reutilizado)
├── utils.py                   # Utilidades (reutilizado)
└── README_FLASK.md            # Esta documentación
```

### Flujo de datos
```
User Browser → Flask Routes → OrchestratorAgentExecutor → LangGraph → Neo4j
                    ↓
               JSON Response ← AsyncIO (fresh event loop) ← Streaming chunks
```

## 🔧 Configuración

### Variables de entorno
```bash
# Opcional - Flask secret key (por defecto usa clave de desarrollo)
export FLASK_SECRET_KEY="your-secret-key-here"

# Opcional - Modo de Flask (por defecto: development)
export FLASK_ENV="development"
```

### Configuración de Neo4j
La aplicación utiliza las mismas variables de entorno que el resto del sistema:
```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your_password"
```

## 🚦 Endpoints de la API

### Autenticación
- `GET /` - Página principal (login si no autenticado, chat si autenticado)
- `POST /login` - Autenticación de usuario
- `GET /logout` - Cerrar sesión

### Chat
- `POST /chat` - Procesar mensaje de chat (con streaming response)
- `GET /conversations` - Obtener conversaciones del usuario
- `POST /conversations` - Crear nueva conversación
- `GET /subjects` - Obtener materias disponibles

## 🔍 Debugging y Logs

### Logs del sistema
Los logs incluyen información detallada sobre:
- Procesamiento de mensajes
- Estados de sesión
- Errores de AsyncIO
- Interacciones con Neo4j

### Ejemplo de log normal
```
🎯 Flask processing message: El punto a de la práctica 2 no lo entiendo
🎯 Session: temp_session_abc123
🎯 Subject: Bases de Datos Relacionales
🔍 Processing with context: {'session_id': 'temp_session_abc123', 'user_id': 'flask_user', 'educational_subject': 'Bases de Datos Relacionales'}
📦 Received chunk: Analizando tu mensaje y recuperando contexto de conversación...
📦 Received chunk: Clasificando tu intención y determinando la mejor forma de ayudarte...
✅ Final response received
```

## 🆚 Comparación con Streamlit

| Aspecto | Streamlit | Flask |
|---------|-----------|--------|
| **Multi-turn conversations** | ❌ Se cuelga | ✅ Funciona perfectamente |
| **AsyncIO compatibility** | ❌ Conflictos | ✅ Event loops aislados |
| **Neo4j persistence** | ❌ Problemas | ✅ Compatible |
| **Development speed** | ✅ Muy rápido | ⚠️ Más código |
| **Debugging** | ❌ Difícil | ✅ Estándar |
| **Production ready** | ⚠️ Limitado | ✅ Completamente |

## 🚀 Ventajas del nuevo sistema

### 1. **Solución definitiva a multi-turn**
- Cada request tiene su propio event loop con `asyncio.run()`
- No hay state sharing problemático entre requests
- Sessions manejadas correctamente por Flask

### 2. **Mejor experiencia de usuario**
- No hay recargas de página
- Indicadores de progreso reales
- Interfaz más responsive

### 3. **Escalabilidad**
- Puede manejar múltiples usuarios concurrentes
- Compatible con deployment en producción
- Fácil de dockerizar

## 🔄 Migración desde Streamlit

Para migrar desde el frontend Streamlit:

1. **Detener Streamlit**: `Ctrl+C` en la aplicación Streamlit
2. **Ejecutar Flask**: `python frontend/run_flask.py`
3. **Usar la nueva URL**: http://localhost:5000
4. **Mismo backend**: Utiliza el mismo orchestrator y persistence

## 🐛 Troubleshooting

### Problema: "Address already in use"
```bash
# Verificar qué está usando el puerto 5000
lsof -i :5000

# Usar un puerto diferente
export FLASK_RUN_PORT=5001
python run_flask.py
```

### Problema: Errores de autenticación
- Verificar que Neo4j esté ejecutándose
- Verificar credenciales en la base de datos
- Usar credenciales de prueba: visitante@uca.edu.ar / visitante!

### Problema: No encuentra materias
- Verificar conexión a Neo4j
- Verificar que el knowledge graph esté poblado
- Ejecutar: `python db/create_kg.py`

## 📝 Conclusión

El frontend Flask soluciona definitivamente los problemas de multi-turn conversations que tenía Streamlit, proporcionando una experiencia de usuario más estable y profesional.