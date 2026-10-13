"""Reglas de álgebra relacional y su traducción a SQL ANSI.

Fuentes: apunte "Lenguajes relacionales" (Taller #3) y "Del Álgebra Relacional al SQL" (Taller #8).
Las usan la ingesta de soluciones y el agente, siempre en el prompt (no por RAG).
"""

AR_RULES = """\
REGLAS DE ÁLGEBRA RELACIONAL (AR)
- El AR es cerrado: cada operador recibe relaciones y devuelve una relación. Semántica de conjuntos: \
una relación no tiene tuplas duplicadas.
- Selección σ_{condición}(R): filtro horizontal. Compara atributos con constantes u otros atributos \
(=, ≠, <, ≤, >, ≥) combinados con ∧ (AND), ∨ (OR), ¬ (NOT). Mismo esquema que R.
- Proyección π_{atributos}(R): recorte vertical; elimina duplicados.
- Renombre ρ_{S(B1,…,Bn)}(R) o ρ_{S}(R): obligatorio en una autojunta para distinguir los roles; \
también para compatibilizar nombres antes de una junta natural.
- Unión ∪, intersección ∩, diferencia −: requieren relaciones compatibles con la unión (mismo grado, \
dominios compatibles por posición); el resultado toma los nombres de la primera. La diferencia no es conmutativa.
- Producto cartesiano R × S: todas las combinaciones (|R|·|S| tuplas, n+m atributos).
- Junta (theta) R ⋈_{condición} S ≡ σ_{condición}(R × S). Equijoin si la condición sólo usa igualdades \
(conserva ambos atributos). Junta natural R ⋈ S: iguala los atributos homónimos y conserva una copia; \
cuidado, dos homónimos no siempre son el mismo concepto.
- Juntas externas: junta izquierda (izq⋈) y derecha (⋈der) conservan las tuplas sin pareja del lado indicado, \
completando con NULL.
- División R ÷ S: "para todos". R(Z), S(X), X ⊆ Z: devuelve los valores de Z − X asociados con TODOS los de S. \
Equivale a π_X(A) − π_X((π_X(A) × B) − A).
- Funciones agregadas: _{atributos de agrupamiento} F _{funciones}(R) con SUMA, PROMEDIO, MÁXIMO, MÍNIMO, CUENTA. \
Sin atributos de agrupamiento devuelve una sola tupla (sigue siendo una relación).
- Resultados intermedios con asignación: A ← expresión. Conviene resolver por pasos con nombres claros.
- {σ, π, ∪, ρ, −, ×} es completo: el resto (∩, juntas, ÷) se puede expresar con ellos.
- Notación: π_{...}, σ_{...}, ⋈_{...}; constantes entre comillas simples.
"""

AR_TO_SQL = """\
TRADUCCIÓN DE AR A SQL ANSI (todo problema se plantea primero en AR; el SQL se deriva del AR)
- π → SELECT DISTINCT columnas (el AR elimina duplicados; sin DISTINCT el SQL los conserva).
- σ → WHERE (AND / OR / NOT).
- ρ → AS (alias de tabla o columna).
- × → FROM a, b sin condición, o CROSS JOIN.
- ⋈ natural → NATURAL JOIN. ⋈_{cond} → INNER JOIN … ON cond.
- Junta izquierda / derecha → LEFT JOIN / RIGHT JOIN … ON.
- ∪ → UNION (UNION ALL conserva duplicados: unión de multiconjuntos). ∩ → INTERSECT (o IN). \
− → EXCEPT (o NOT EXISTS / NOT IN). NOT IN falla si la subconsulta trae NULL: preferir NOT EXISTS.
- ÷ → doble NOT EXISTS ("no hay ningún Y de B que le falte a ese X").
- F → GROUP BY (izquierda de F) con COUNT/SUM/AVG/MAX/MIN (derecha de F); HAVING filtra grupos.
- Resultados intermedios del AR → subconsultas, CTE (WITH) o vistas.
- Orden lógico: FROM/JOIN → WHERE → GROUP BY → HAVING → SELECT → ORDER BY.
- SQL ANSI: EXCEPT (no MINUS). Identificadores con espacios o caracteres especiales van entre comillas dobles.
"""

TERMINOLOGY = """\
TERMINOLOGÍA (español de Argentina)
- JOIN se dice "junta"; LEFT OUTER JOIN, "junta izquierda"; RIGHT OUTER JOIN, "junta derecha".
- UNION es "unión" de conjuntos y UNION ALL, unión de multiconjuntos. No confundir unión con junta.
"""

ALL_RULES = "\n".join([AR_RULES, AR_TO_SQL, TERMINOLOGY])
