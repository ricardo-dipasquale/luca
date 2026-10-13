from course.canonical import ar_set_operations, check_canonical

TALLER_DIVISION = """
SELECT DISTINCT X FROM A AS A1
WHERE NOT EXISTS (
    SELECT 1 FROM A AS A2, B
    WHERE A1.X = A2.X AND NOT EXISTS (
        SELECT 1 FROM A AS A3
        WHERE A3.X = A2.X AND A3.Y = B.Y))
"""

# Divides cliente by producto directly: double NOT EXISTS, but not deduced from the AR's dividend.
CLASSIC_DIVISION = """
SELECT DISTINCT c.codigo_cliente FROM cliente AS c
WHERE NOT EXISTS (
    SELECT 1 FROM producto AS p
    WHERE NOT EXISTS (
        SELECT 1 FROM detalle_pedido AS d
        WHERE d.codigo_cliente = c.codigo_cliente AND d.codigo_producto = p.codigo_producto))
"""

CTE_DIVISION = """
WITH CP AS (SELECT DISTINCT codigo_cliente, codigo_producto FROM pedido NATURAL JOIN detalle_pedido),
     B AS (SELECT DISTINCT codigo_producto FROM producto)
SELECT DISTINCT A1.codigo_cliente FROM CP AS A1
WHERE NOT EXISTS (
    SELECT 1 FROM CP AS A2 CROSS JOIN B
    WHERE A1.codigo_cliente = A2.codigo_cliente AND NOT EXISTS (
        SELECT 1 FROM CP AS A3
        WHERE A3.codigo_cliente = A2.codigo_cliente AND A3.codigo_producto = B.codigo_producto))
"""


def test_taller_division_template_is_canonical():
    assert check_canonical("A / B", TALLER_DIVISION)["ok"] is True
    assert check_canonical("Todos ← CP ÷ π_{codigo_producto}(producto)", CTE_DIVISION)["ok"] is True


def test_division_not_built_from_the_dividend_is_rejected():
    result = check_canonical("CP ÷ π_{codigo_producto}(producto)", CLASSIC_DIVISION)
    assert result["ok"] is False and "doble NOT EXISTS" in result["detalle"]


def test_difference_must_use_except():
    ar = "π_{codigo_cliente}(cliente) − π_{codigo_cliente}(pago)"
    not_exists = "SELECT codigo_cliente FROM cliente c WHERE NOT EXISTS (SELECT 1 FROM pago p WHERE p.codigo_cliente = c.codigo_cliente)"
    assert check_canonical(ar, not_exists) == {"ok": False, "detalle": "− se traduce con EXCEPT"}
    assert check_canonical(ar, "SELECT codigo_cliente FROM cliente EXCEPT SELECT codigo_cliente FROM pago")["ok"] is True


def test_union_and_intersection():
    assert check_canonical("R ∪ S", "SELECT a FROM r INTERSECT SELECT a FROM s")["detalle"] == "∪ se traduce con UNION"
    assert check_canonical("R ∩ S", "SELECT a FROM r INTERSECT SELECT a FROM s")["ok"] is True


def test_arithmetic_inside_subscripts_is_not_a_set_operation():
    assert ar_set_operations("σ_{fecha_entrega ≤ fecha_esperada − 2 días}(pedido)") == set()
    assert ar_set_operations("π_{x}(R) − π_{x}(S)") == {"−"}


def test_slash_inside_a_word_is_not_a_quotient():
    assert ar_set_operations("se aplica una extensión de orden/top-k") == set()
    assert ar_set_operations("π_{a,b} (VENTA) / π_{b} (PRODUCTO)") == {"÷"}
    assert ar_set_operations("C=A−B") == {"−"}


def test_ordering_in_ar_is_rejected():
    result = check_canonical("π_{nombre}(producto) con ordenación descendente", "SELECT nombre FROM producto ORDER BY nombre DESC")
    assert result["ok"] is False and "orden" in result["detalle"]


def test_missing_or_unparseable_sql():
    assert check_canonical("R", "")["ok"] is False
    assert check_canonical("R", "SELECT * FROM (")["detalle"] == "SQL no parseable"
