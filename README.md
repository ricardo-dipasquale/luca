# luca

Our GenAI Learning Project is an intelligent, interactive tutor designed to revolutionize how students engage with their courses. Powered by advanced generative AI, it provides personalized guidance, answers complex questions, and adapts to each student's unique learning style. 

## Pre requisites

Install Conda

    - create luca environment
    - conda activate luca

To start docker Neo4J:

    - cd db
    - Create directories 
        - data
        - plugins
        - logs
        - import
        - langfuse_clickhouse_data
        - langfuse_clickhouse_logs
        - langfuse_minio_data
        - postgres
    - Don't do thin in prod
        sudo chmod -R a+rw ./data
        sudo chmod -R a+rw ./plugins
        sudo chmod -R a+rw ./logs
        sudo chmod -R a+rw ./import
        sudo chmod -R a+rw ./langfuse_clickhouse_data
        sudo chmod -R a+rw ./langfuse_clickhouse_logs
    - Copy jar files (neo4j plugins) to plugins
        - neo4j-graph-data-science-2.13.2.jar
        - apoc-5.26.1-core.jar


To host the whole llm-graph-builder solution (to build KG):

    - Update npm, nodejs in your linux system
    - Install yarn:
        npm install --global yarn
    - git clone the llm-graph-builder project
    - Inside it:
        - Backend:
            - Create the backend/.env file by copy/pasting the backend/example.env. To streamline the initial setup and testing of the application, you can preconfigure user credentials directly within the backend .env file. This bypasses the login dialog and allows you to immediately connect with a predefined user.
            - NEO4J_URI: 
            - NEO4J_USERNAME:
            - NEO4J_PASSWORD:
            - If using local LLM change in .env: LLM_MODEL_CONFIG_ollama_llama3="deepseek,http://localhost:11434"
            - Run:
                cd backend
                pip install -r requirements.txt
                uvicorn score:app --reload
        - Frontend:
            - Create the frontend/.env file by copy/pasting the frontend/example.env.
            - Change values as needed
            - Run
                - cd frontend
                - (sudo) yarn
                - (sudo) yarn run dev
        - Browse: http://localhost:5173/

To run some code:

    - Create a .envrc
        export NEO4J_URI="xxx"
        export NEO4J_USER="xxx"
        export NEO4J_PASSWORD="xxx"
        export OPENAI_API_KEY="xxx"
        export GRAPHBUILDER_URI="http://127.0.0.1:8000/chat_bot"
        export POSTGRES_USER="postgres"
        export POSTGRES_PASSWORD="xxxx"
        export POSTGRES_DB="postgres"
        export REDIS_AUTH="xxx"
        export CLICKHOUSE_PASSWORD="xxx"
        export NEXTAUTH_SECRET="xxx"
        export LANGFUSE_INIT_ORG_ID="1"
        export LANGFUSE_INIT_ORG_NAME="UCA"
        export LANGFUSE_INIT_PROJECT_ID="1"
        export LANGFUSE_INIT_PROJECT_NAME="LUCA"
        export LANGFUSE_INIT_PROJECT_PUBLIC_KEY="xxx"
        export LANGFUSE_INIT_PROJECT_SECRET_KEY="xxx"
        export LANGFUSE_INIT_USER_EMAIL="xxx@uca.edu.ar"
        export LANGFUSE_INIT_USER_NAME="admin"
        export LANGFUSE_INIT_USER_PASSWORD="xxx"
        export SALT="xxx" 
        export ENCRYPTION_KEY="0000000000000000000000000000000000000000000000000000000000000000" #Generate with openssl
    - Install direnv
    - Configure direnv extension in vscode.
    
