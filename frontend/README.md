# LUCA Frontend

Frontend web application for LUCA educational assistant built with Streamlit.

## Features

- 🎓 **Educational Chat Interface**: Clean, intuitive chat interface similar to Claude/OpenAI
- 🔐 **UCA Authentication**: Secure login with @uca.edu.ar email validation
- 📚 **Subject Selection**: Dynamic subject selector loaded from knowledge graph
- 💬 **Conversation Management**: Persistent conversation history with Neo4j storage
- 🎨 **Professional Design**: Modern UI with FICA and LUCA branding
- ⚡ **Real-time Streaming**: Live response streaming from Orchestrator agent
- 📱 **Responsive Layout**: Works on desktop and mobile devices

## Architecture

```
frontend/
├── app.py              # Main Streamlit application
├── auth.py             # User authentication and conversation management
├── chat.py             # Orchestrator client and communication
├── utils.py            # Utility functions (subjects, formatting)
├── run.py              # Application runner script
├── requirements.txt    # Frontend-specific dependencies
├── README.md          # This file
└── assets/            # Static assets
    ├── logo luca.png          # LUCA application logo
    └── Logo FICA uso excepcional color.png  # FICA university logo
```

## Quick Start

### Prerequisites

1. Neo4j database running with LUCA knowledge graph
2. Orchestrator agent available (local or service)
3. Python environment with main project dependencies

### Installation

```bash
# From the project root
cd frontend

# Install frontend dependencies
pip install -r requirements.txt

# Run the application
python run.py
```

### Access

Open your browser and navigate to: http://localhost:8501

## Authentication

### Test User

For development and testing, use these credentials:
- **Email**: visitante@uca.edu.ar
- **Password**: visitante!

### User Management

Users are stored in Neo4j with the following schema:

```cypher
(:Usuario {
  email: string,           # Must end with @uca.edu.ar
  password: string,        # Plain text for demo (use hashing in production)
  nombre: string,          # Display name
  created_at: datetime,    # Account creation date
  last_login: datetime     # Last login timestamp
})
```

### Creating New Users

```cypher
CREATE (u:Usuario {
  email: 'student@uca.edu.ar',
  password: 'secure_password',
  nombre: 'Student Name',
  created_at: datetime(),
  last_login: null
})
```

## Conversation Management

### Conversation Schema

```cypher
(:Conversacion {
  id: string,              # UUID
  title: string,           # Conversation title
  subject: string,         # Educational subject
  created_at: datetime,    # Creation date
  updated_at: datetime,    # Last update
  message_count: integer   # Number of messages
})

(:Usuario)-[:OWNS]->(:Conversacion)
```

### Features

- **Automatic Title Generation**: Based on first user message
- **Subject Association**: Each conversation linked to specific educational subject
- **Message Counting**: Track conversation activity
- **Chronological Ordering**: Most recent conversations first

## Chat Interface

### Orchestrator Integration

The frontend communicates directly with the Orchestrator agent through:

1. **Direct Integration**: Uses `OrchestratorAgentExecutor` directly
2. **Subject Injection**: Passes selected subject to orchestrator context
3. **Streaming Responses**: Real-time response updates
4. **Session Management**: Maintains conversation continuity

### Message Flow

```
User Input → Subject Validation → Orchestrator Stream → Response Display
```

### Streaming Display

- **Progress Indicators**: Shows thinking status and processing steps
- **Real-time Updates**: Displays intermediate processing messages
- **Error Handling**: Graceful error messages and fallbacks

## Styling and Branding

### Logo Configuration

- **LUCA Logo**: Center header, 200px width
- **FICA Logo**: Top right, 80px width
- **Responsive**: Scales appropriately on different screen sizes

### Theme

- **Primary Color**: #007bff (Blue)
- **Background**: Light theme with clean design
- **Message Bubbles**: User (blue, right) vs Assistant (gray, left)
- **Responsive Layout**: Sidebar + main content area

### Custom CSS

The application includes extensive custom CSS for:
- Message styling and alignment
- Sidebar conversation list
- Header and logo positioning
- Responsive design breakpoints
- Loading and thinking indicators

## Configuration

### Environment Variables

```bash
# Neo4j Configuration (inherited from main project)
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

# Optional: Orchestrator API (if using HTTP client)
ORCHESTRATOR_URL=http://localhost:10001
```

### Streamlit Configuration

The application includes optimized Streamlit settings:
- Custom port (8501)
- Disabled CORS for development
- Light theme with UCA branding colors
- Hidden Streamlit default UI elements

## Deployment

### Development

```bash
# Start from frontend directory
python run.py
```

### Production

```bash
# Install dependencies
pip install -r requirements.txt

# Run with production settings
streamlit run app.py \
  --server.port=8501 \
  --server.address=0.0.0.0 \
  --server.headless=true
```

### Docker (Optional)

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY frontend/ .
COPY kg/ ../kg/
COPY orchestrator/ ../orchestrator/
COPY tools/ ../tools/

RUN pip install -r requirements.txt

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## Troubleshooting

### Common Issues

1. **Neo4j Connection Error**
   - Verify Neo4j is running
   - Check connection credentials
   - Ensure knowledge graph is populated

2. **Orchestrator Connection Error**
   - Verify orchestrator agent is initialized
   - Check imports and dependencies
   - Review error logs in terminal

3. **Subject Loading Issues**
   - Verify KG contains Materia nodes
   - Check KGQueryInterface.get_subjects() method
   - Fallback to default subjects list

4. **Authentication Problems**
   - Verify Usuario node exists in Neo4j
   - Check email domain validation (@uca.edu.ar)
   - Review password matching logic

### Debug Mode

Enable debug logging by setting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Database Verification

```cypher
// Check user exists
MATCH (u:Usuario {email: 'visitante@uca.edu.ar'}) RETURN u;

// Check conversations
MATCH (u:Usuario)-[:OWNS]->(c:Conversacion) RETURN u.email, c.title;

// Check subjects
MATCH (m:Materia) RETURN m.nombre LIMIT 10;
```

## Contributing

1. Follow existing code style and patterns
2. Test authentication and conversation flows
3. Verify responsive design on different screen sizes
4. Ensure proper error handling and user feedback
5. Update documentation for new features

## Future Enhancements

- [ ] Message persistence in Neo4j
- [ ] File upload support
- [ ] Advanced conversation search
- [ ] User profile management
- [ ] Multi-language support
- [ ] Dark mode theme
- [ ] Mobile app version
- [ ] Advanced analytics dashboard