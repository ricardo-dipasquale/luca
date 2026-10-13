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
- División (cociente) R ÷ S (también R / S): "para todos". R(Z), S(X), X ⊆ Z: devuelve los valores de Z − X \
asociados con TODOS los de S. Equivale a π_X(A) − π_X((π_X(A) × B) − A). Las consultas con "todos" se plantean con ÷.
- Funciones agregadas: _{atributos de agrupamiento} F _{funciones}(R) con SUMA, PROMEDIO, MÁXIMO, MÍNIMO, CUENTA. \
Sin atributos de agrupamiento devuelve una sola tupla (sigue siendo una relación).
- Resultados intermedios con asignación: A ← expresión. Conviene resolver por pasos con nombres claros.
- {σ, π, ∪, ρ, −, ×} es completo: el resto (∩, juntas, ÷) se puede expresar con ellos.
- El AR no tiene orden: si la consigna pide ordenar, el AR no lo expresa (ni lo menciona).
- Notación: π_{...}, σ_{...}, ⋈_{...}; constantes entre comillas simples.
"""

AR_TO_SQL = """\
TRADUCCIÓN DE AR A SQL ANSI: FORMA CANÓNICA (obligatoria)
Todo problema se plantea primero en AR y el SQL se deduce del AR operador por operador. Cada operador tiene \
una forma canónica; la solución usa esa forma:
- π → SELECT DISTINCT columnas (el AR elimina duplicados; sin DISTINCT el SQL los conserva).
- σ → WHERE (AND / OR / NOT).
- ρ → AS (alias de tabla o columna).
- × → CROSS JOIN (o FROM a, b sin condición).
- ⋈ natural → NATURAL JOIN. ⋈_{cond} → INNER JOIN … ON cond.
- Junta izquierda / derecha → LEFT JOIN / RIGHT JOIN … ON.
- ∪ → UNION (UNION ALL sólo para la unión de multiconjuntos).
- ∩ → INTERSECT.
- − → EXCEPT.
- ÷ → doble NOT EXISTS con esta plantilla, donde A es el dividendo (atributos X, Y) y B el divisor (atributo Y), \
los mismos operandos del cociente en el AR:
  (si A o B son expresiones, primero CREATE VIEW A AS …; CREATE VIEW B AS …;)
    SELECT DISTINCT A1.X FROM A AS A1
    WHERE NOT EXISTS (
        SELECT 1 FROM A AS A2, B
        WHERE A1.X = A2.X AND NOT EXISTS (
            SELECT 1 FROM A AS A3
            WHERE A3.X = A2.X AND A3.Y = B.Y))
  Idea: "no hay ningún Y de B que le falte a ese X". No resolver el cociente con GROUP BY/COUNT ni dividiendo \
otras tablas que no sean los operandos del AR.
- F → GROUP BY (izquierda de F) con COUNT/SUM/AVG/MAX/MIN (derecha de F); HAVING filtra grupos.
- No se usan bloques WITH. Si un resultado intermedio A ← expresión necesita nombre en SQL (por ejemplo, el \
dividendo o el divisor de un cociente), se crea una vista con el mismo nombre: CREATE VIEW A AS …; y la consulta \
final usa A como tabla. Las vistas se usan sólo cuando hace falta: no encadenar vistas innecesarias.
- Orden: el AR no expresa orden; si la consigna lo pide, el SQL agrega ORDER BY y se le aclara al alumno que el \
orden sólo existe en SQL.
- NOT IN / NOT EXISTS (para −) e IN (para ∩) son alternativas para motores sin EXCEPT / INTERSECT: se pueden \
mencionar como alternativa, no son la solución. NOT IN falla si la subconsulta trae NULL.
- Orden lógico de evaluación: FROM/JOIN → WHERE → GROUP BY → HAVING → SELECT → ORDER BY.
- SQL ANSI: EXCEPT (no MINUS). Identificadores con espacios o caracteres especiales van entre comillas dobles.
"""

TERMINOLOGY = """\
TERMINOLOGÍA (español de Argentina)
- JOIN se dice "junta"; LEFT OUTER JOIN, "junta izquierda"; RIGHT OUTER JOIN, "junta derecha".
- UNION es "unión" de conjuntos y UNION ALL, unión de multiconjuntos. No confundir unión con junta.
"""

ALL_RULES = "\n".join([AR_RULES, AR_TO_SQL, TERMINOLOGY])
