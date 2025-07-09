# luca
Our GenAI Learning Project is an intelligent, interactive tutor designed to revolutionize how students engage with their courses. Powered by advanced generative AI, it provides personalized guidance, answers complex questions, and adapts to each student's unique learning style. 

Pre requisites

Install Conda
    - create luca environment
    - conda activate luca

To start docker Neo4J:
    - cd db
    - Create directories 
        - ./data
        - ./plugins
        - ./logs
        - ./import
    - Don't do thin in prod
        sudo chmod -R a+rw ./data
        sudo chmod -R a+rw ./plugins
        sudo chmod -R a+rw ./logs
        sudo chmod -R a+rw ./import
    - Copy jar files (neo4j plugins) to plugins
        - neo4j-graph-data-science-2.13.2.jar
        - apoc-5.26.1-core.jar
    - If you have an env File:
        docker run -d --env-file .env -u {$LINUX_USER} -p 7474:7474 -p 7687:7687 -v ./data:/data -v ./logs:/logs -v ./import:/var/lib/neo4j/import -v ./plugins:/plugins -e NEO4J_AUTH={$NEO4J_AUTH_ENV} -e NEO4J_apoc_export_file_enabled=true -e NEO4J_apoc_import_file_enabled=true -e NEO4J_apoc_import_file_use__neo4j__config=true --name neo4j neo4j:5.26.1
    - If you don't:
        docker run -d -p 7474:7474 -p 7687:7687 -v ./data:/data -v ./logs:/logs -v ./import:/var/lib/neo4j/import -v ./plugins:/plugins  -e NEO4J_AUTH="neo4jusr/neo4jpassword" -e NEO4J_apoc_export_file_enabled=true -e NEO4J_apoc_import_file_enabled=true -e NEO4J_apoc_import_file_use__neo4j__config=true -e NEO4JLABS_PLUGINS=\[\"apoc\",\"graph-data-science\"\] -e NEO4J_dbms_security_procedures_unrestricted=apoc.\\\* --name neo4j neo4j:5.26.1

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
    - Install direnv
    - Configure direnv extension in vscode.
    