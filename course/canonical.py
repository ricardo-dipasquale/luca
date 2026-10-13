"""¿El SQL resuelve las operaciones de conjunto y el cociente del AR con su forma canónica (course/rules.py)?"""

import re
from typing import Any

import sqlglot
from sqlglot import exp


def _strip_subscripts(ar: str) -> str:
    """Drop the contents of _{…}: arithmetic like `fecha − 2` inside σ conditions is not a set operation."""
    out, i = [], 0
    while i < len(ar):
        if ar.startswith("_{", i):
            depth, i = 1, i + 2
            while i < len(ar) and depth and ar[i] != "\n":  # an unclosed subscript ends at the line
                depth += {"{": 1, "}": -1}.get(ar[i], 0)
                i += 1
            continue
        out.append(ar[i])
        i += 1
    return "".join(out)


def ar_set_operations(ar: str) -> set[str]:
    text = _strip_subscripts(ar)
    ops = {op for op in ("∪", "∩", "−") if op in text}
    # "/" counts as a quotient only between operands, not inside a word like "orden/top-k".
    if "÷" in text or re.search(r"(\)\s*/|\s/\s)", text):
        ops.add("÷")
    return ops


def _relations(select: exp.Select) -> list[str]:
    tables = []
    from_ = select.args.get("from_") or select.args.get("from")  # renamed to from_ in recent sqlglot
    if from_:
        tables += [t.name for t in from_.find_all(exp.Table)]
    for join in select.args.get("joins") or []:
        tables += [t.name for t in join.find_all(exp.Table)]
    return tables


def _not_exists_in(select: exp.Select) -> list[exp.Select]:
    """Subqueries of NOT EXISTS predicates that belong to this SELECT (not to a nested one)."""
    return [
        n.this.this for n in select.find_all(exp.Not)
        if isinstance(n.this, exp.Exists) and n.parent_select is select and isinstance(n.this.this, exp.Select)
    ]


def has_canonical_division(tree: exp.Expression) -> bool:
    """Taller #8 template: A AS A1 / NOT EXISTS (A AS A2, B / NOT EXISTS (A AS A3)) with the same dividend A."""
    for outer in tree.find_all(exp.Select):
        for middle in _not_exists_in(outer):
            if len(_relations(middle)) < 2:
                continue
            for inner in _not_exists_in(middle):
                if set(_relations(outer)) & set(_relations(middle)) & set(_relations(inner)):
                    return True
    return False


def check_canonical(ar: str, sql: str) -> dict[str, Any]:
    if not sql.strip():
        return {"ok": False, "detalle": "sin SQL"}
    try:
        trees = sqlglot.parse(sql)
    except sqlglot.errors.SqlglotError:
        return {"ok": False, "detalle": "SQL no parseable"}

    def has(kind: type) -> bool:
        return any(t.find(kind) for t in trees if t)

    faltantes = []
    ops = ar_set_operations(ar)
    if "∪" in ops and not has(exp.Union):
        faltantes.append("∪ se traduce con UNION")
    if "∩" in ops and not has(exp.Intersect):
        faltantes.append("∩ se traduce con INTERSECT")
    if "−" in ops and not has(exp.Except):
        faltantes.append("− se traduce con EXCEPT")
    if "÷" in ops and not any(has_canonical_division(t) for t in trees if t):
        faltantes.append("÷ se traduce con el doble NOT EXISTS de la plantilla (A AS A1 / A AS A2, B / A AS A3)")
    if re.search(r"\b(orden|ordenaci[oó]n|order by)\b", _strip_subscripts(ar), re.I):
        faltantes.append("el AR no expresa orden: el orden va sólo en el SQL")
    if faltantes:
        return {"ok": False, "detalle": "; ".join(faltantes)}
    return {"ok": True, "detalle": "operaciones de conjunto y cociente en forma canónica" if ops else "sin operaciones de conjunto"}
