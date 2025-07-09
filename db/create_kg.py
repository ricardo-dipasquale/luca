import os
import ast
import pickle
import pandas as pd
import json
import openai
from neo4j import GraphDatabase

def crear_kg(
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    programa_path: str,
    practicas_path: str,
    embedding_cache_path: str = "embeddings_cache.pkl"
):
    # Conectar a Neo4j
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    with driver.session() as session:
        # 1. Limpiar grafo actual (labels involucrados)
        labels = [
            "Materia", "Carrera", "Profesor", "ObjetivoMateria", "UnidadTematica",
            "Tema", "Practica", "Tip", "SeccionPractica",
            "Seccion","Ejercicio", "Respuesta"
        ]
        for label in labels:
            session.run(f"MATCH (n:{label}) DETACH DELETE n")

        # 2. Procesar Programa.xlsx
        excel_prog = pd.ExcelFile(programa_path)

        # Cabecera
        df_cab = excel_prog.parse("Cabecera")
        for _, row in df_cab.iterrows():
            materia_props = {"nombre": row["Materia"]}
            session.run(
            "MERGE (m:Materia {nombre: $nombre})",
            materia_props
            )
            # Carrera (asume valor único)
            valor_carrera = row["Carrera"]
            session.run(
            "MERGE (n:Carrera {nombre: $valor})",
            {"valor": valor_carrera}
            )
            session.run(
            "MATCH (m:Materia {nombre: $nombre}), (n:Carrera {nombre: $valor}) "
            "MERGE (m)-[:HAS_CARRERA]->(n)",
            {"nombre": row["Materia"], "valor": valor_carrera}
            )
            # Profesor (puede ser lista)
            profesores = row["Profesor"]
            if isinstance(profesores, str):
                try:
                    profesores = ast.literal_eval(profesores)
                except Exception:
                    profesores = [profesores]
            if not isinstance(profesores, list):
                profesores = [profesores]
            for profesor in profesores:
                session.run(
                    "MERGE (n:Profesor {nombre: $valor})",
                    {"valor": profesor}
                )
                session.run(
                    "MATCH (m:Materia {nombre: $nombre}), (n:Profesor {nombre: $valor}) "
                    "MERGE (m)-[:HAS_PROFESOR]->(n)",
                    {"nombre": row["Materia"], "valor": profesor}
                )

        # Objetivos
        df_obj = excel_prog.parse("Objetivos")
        for _, row in df_obj.iterrows():
            session.run(
                "CREATE (o:ObjetivoMateria {descripcion: $desc})",
                {"desc": row["Objetivo"]}
            )
            session.run(
                "MATCH (m:Materia {nombre: $nombre}), (o:ObjetivoMateria {descripcion: $desc}) "
                "MERGE (m)-[:HAS_OBJETIVO]->(o)",
                {"nombre": df_cab.at[0, "Materia"], "desc": row["Objetivo"]}
            )

        # UnidadesTematicas
        df_ut = excel_prog.parse("UnidadesTematicas")
        for _, row in df_ut.iterrows():
            session.run(
                "CREATE (u:UnidadTematica {numero: $num, titulo: $titulo})",
                {"num": int(row["Numero"]), "titulo": row["Titulo"]}
            )
            session.run(
                "MATCH (m:Materia {nombre: $nombre}), (u:UnidadTematica {numero: $num}) "
                "MERGE (m)-[:HAS_UNIDAD_TEMATICA]->(u)",
                {"nombre": df_cab.at[0, "Materia"], "num": int(row["Numero"])}
            )

        # Temas
        df_temas = excel_prog.parse("Temas")
        for _, row in df_temas.iterrows():
            session.run(
                "CREATE (t:Tema {descripcion: $texto})",
                {"texto": row["Tema"]}
            )
            session.run(
                "MATCH (u:UnidadTematica {numero: $num}), (t:Tema {descripcion: $texto}) "
                "MERGE (u)-[:HAS_TEMA]->(t)",
                {"num": int(row["NumeroUnidadTematica"]), "texto": row["Tema"]}
            )
            # ApunteRelacionado es lista de strings, puede estar vacío o NaN
            referencias = row.get("Apunte Relacionado")
            if pd.notna(referencias) and str(referencias).strip():
                try:
                    referencias = ast.literal_eval(referencias)
                except Exception:
                    referencias = [referencias]
                if not isinstance(referencias, list):
                    referencias = [referencias]
                for doc in referencias:
                    session.run(
                        "MATCH (t:Tema {descripcion: $texto}), (d:Document {fileName: $file}) "
                        "MERGE (t)-[:APUNTE]->(d)",
                        {"texto": row["Tema"], "file": doc}
                    )

        # 3. Procesar Prácticas Bases de Datos.xlsx
        excel_prac = pd.ExcelFile(practicas_path)

        # Cabecera
        df_pcab = excel_prac.parse("Cabecera")
        for _, row in df_pcab.iterrows():
            props = {col.lower().replace(" ", "_"): row[col] for col in df_pcab.columns}
            session.run("CREATE (p:Practica $props)", {"props": props})
            # Teoría Relacionada
            temas_rel = ast.literal_eval(row["Teoría Relacionada"])
            for tema in temas_rel:
                session.run(
                    "MATCH (p:Practica {numeropractica: $num}), (t:Tema {descripcion: $tema}) "
                    "MERGE (p)-[:HAS_TEMA]->(t)",
                    {"num": row["NumeroPractica"], "tema": tema}
                )

        # TipsNivelPractica
        df_tips = excel_prac.parse("TipsNivelPractica")
        for _, row in df_tips.iterrows():
            session.run(
                "CREATE (tip:Tip {texto: $texto})",
                {"texto": row["Tip"]}
            )
            session.run(
                "MATCH (p:Practica {numeropractica: $num}), (tip:Tip {texto: $texto}) "
                "MERGE (p)-[:HAS_TIP]->(tip)",
                {"num": row["NumeroPractica"], "texto": row["Tip"]}
            )

        # Enunciado (Secciones y Ejercicios)
        df_en = excel_prac.parse("Enunciado")
        for _, row in df_en.iterrows():
            if row["Tipo"] == "S":
                # SeccionPractica
                session.run(
                    "CREATE (s:SeccionPractica {numero: $sec, enunciado: $enc})",
                    {"sec": str(row["Seccion"]), "enc": row["Enunciado"]}
                )
                session.run(
                    "MATCH (p:Practica {numeropractica: $num}), (s:SeccionPractica {numero: $sec}) "
                    "MERGE (p)-[:HAS_SECCION]->(s)",
                    {"num": row["NumeroPractica"], "sec": str(row["Seccion"])}
                )
                # Tips nivel sección
                tips_sec = row.get("Tips Nivel Ejercicio")
                if pd.notna(tips_sec) and str(tips_sec).strip():
                    try:
                        tips_sec = ast.literal_eval(tips_sec)
                    except Exception:
                        tips_sec = [tips_sec]
                    if not isinstance(tips_sec, list):
                        tips_sec = [tips_sec]
                    for tip in tips_sec:
                        session.run(
                            "CREATE (t:Tip {texto: $texto})",
                            {"texto": tip}
                        )
                        session.run(
                            "MATCH (s:SeccionPractica {numero: $sec}), (t:Tip {texto: $texto}) "
                            "MERGE (s)-[:HAS_TIP]->(t)",
                            {"sec": str(row["Seccion"]), "texto": tip}
                        )
            else:
                # Ejercicio
                session.run(
                    "CREATE (e:Ejercicio {numero: $ej, enunciado: $enc})",
                    {"ej": str(row["Ejercicio"]), "enc": row["Enunciado"]}
                )
                session.run(
                    "MATCH (s:SeccionPractica {numero: $sec}), (e:Ejercicio {numero: $ej}) "
                    "MERGE (s)-[:HAS_EJERCICIO]->(e)",
                    {"sec": str(row["Seccion"]), "ej": str(row["Ejercicio"])}
                )
                # Respuestas
                try:
                    respuestas = json.loads(row["Respuesta"])
                except Exception:
                    respuestas = [row["Respuesta"]]
                for resp in respuestas:
                    session.run(
                        "CREATE (r:Respuesta {texto: $texto})",
                        {"texto": resp}
                    )
                    session.run(
                        "MATCH (e:Ejercicio {numero: $ej}), (r:Respuesta {texto: $texto}) "
                        "MERGE (e)-[:HAS_RESPUESTA]->(r)",
                        {"ej": str(row["Ejercicio"]), "texto": resp}
                    )
                # Tips nivel ejercicio
                tips_ej = row.get("Tips Nivel Ejercicio")
                if pd.notna(tips_ej) and str(tips_ej).strip():
                    try:
                        tips_ej = ast.literal_eval(tips_ej)
                    except Exception:
                        tips_ej = [tips_ej]
                    if not isinstance(tips_ej, list):
                        tips_ej = [tips_ej]
                    for tip in tips_ej:
                        session.run(
                            "CREATE (t:Tip {texto: $texto})",
                            {"texto": tip}
                        )
                        session.run(
                            "MATCH (e:Ejercicio {numero: $ej}), (t:Tip {texto: $texto}) "
                            "MERGE (e)-[:HAS_TIP]->(t)",
                            {"ej": str(row["Ejercicio"]), "texto": tip}
                        )

        # 4. Crear embeddings y vector index
        create_embeddings(session, embedding_cache_path)
    driver.close()

def create_embeddings(session, cache_path):
    # Cargar o inicializar cache
    if os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            cache = pickle.load(f)
    else:
        cache = {}

    target_nodes = [
        ("ObjetivoMateria", "descripcion"),
        ("UnidadTematica", "titulo"),
        ("Tema", "descripcion"),
        ("Practica", "descripcion"),
        ("Practica", "objetivos"),
        ("Tip", "texto"),
        ("SeccionPractica", "enunciado"),
        ("Ejercicio", "enunciado"),
        ("Respuesta", "texto")
    ]

    for label, prop in target_nodes:
        results = session.run(f"MATCH (n:{label}) RETURN n.{prop} AS text, id(n) AS id")
        for record in results:
            text = record["text"]
            if text is not None:
                node_id = record["id"]
                cache_key = f"{label}:{prop}:{text}"
                if cache_key not in cache:
                    response = openai.embeddings.create(input=[text], model="text-embedding-ada-002")
                    emb = response.data[0].embedding
                    session.run(
                        f"MATCH (n:{label}) WHERE id(n) = $id SET n.embedding_{prop} = $emb",
                        {"id": node_id, "emb": emb}
                    )
                    session.run(
                        "CREATE VECTOR INDEX idx_" + label + "_" + prop + " IF NOT EXISTS FOR (n:" + label + ") ON (n.embedding_" + prop + ") "
                        "OPTIONS { indexConfig: {`vector.dimensions`: 1536,`vector.similarity_function`: 'cosine'}}"
                    )
                    cache[cache_key] = emb

    # Guardar cache
    with open(cache_path, "wb") as f:
        pickle.dump(cache, f)

# Ejemplo de uso
if __name__ == "__main__":
    crear_kg(
        neo4j_uri=os.environ["NEO4J_URI"],
        neo4j_user=os.environ["NEO4J_USER"],
        neo4j_password=os.environ["NEO4J_PASSWORD"],
        programa_path="./db/datasources/Programa.xlsx",
        practicas_path="./db/datasources/Prácticas Bases de Datos.xlsx"
    )

