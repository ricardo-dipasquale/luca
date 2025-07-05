# luca
Our GenAI Learning Project is an intelligent, interactive tutor designed to revolutionize how students engage with their courses. Powered by advanced generative AI, it provides personalized guidance, answers complex questions, and adapts to each student's unique learning style. 

Pre requisites

To host the whole llm-graph-builder solution (to build KG):

    - Build docker images from project llm-graph-builder
    - llm-graph-builder/backend$ uvicorn score:app --reload
    - neo4j-desktop-1.6.1-x86_64.AppImag (to visualize neo4j graph)
    - llm-graph-builder/frontend$ sudo yarn run dev

    luca/db => docker logs -f neo4j