"""Alta de usuarios: planilla de Excel, reglas de contraseña y contraseñas provisorias.

Shared by scripts/import_usuarios.py and the admin page (/admin) so both validate the same way.
Planilla: columns by position, 1st nombre, 3rd email, 4th contraseña; the first row is the header.
"""

import re
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Optional, Union

import pandas as pd

from storage import db

EMAIL_DOMAIN = "@uca.edu.ar"
MIN_PASSWORD_CHARS = 8
MAX_PASSWORD_CHARS = 128
_EMAIL_RE = re.compile(r"^[a-z0-9._%+-]+@uca\.edu\.ar$")
# No 0/O, 1/l/I: provisional passwords are read aloud or copied by hand.
_ALPHABET = "abcdefghijkmnpqrstuvwxyzACDEFGHJKLMNPQRSTUVWXYZ23456789"


def email_problem(email: str) -> Optional[str]:
    if not email.endswith(EMAIL_DOMAIN):
        return f"el email tiene que ser {EMAIL_DOMAIN}"
    if not _EMAIL_RE.match(email):
        return "el email no es válido"
    return None


def password_problem(password: str, email: str) -> Optional[str]:
    """Why a password is not acceptable (in Spanish, for the user), or None."""
    if password != password.strip():
        return "la contraseña no puede empezar ni terminar con espacios"  # the login strips it
    if not MIN_PASSWORD_CHARS <= len(password) <= MAX_PASSWORD_CHARS:
        return f"la contraseña tiene que tener entre {MIN_PASSWORD_CHARS} y {MAX_PASSWORD_CHARS} caracteres"
    if password.lower() == email.strip().lower():
        return "la contraseña no puede ser el email"
    return None


def generate_provisional_password() -> str:
    """Like 'k7Qm-x4Rt-9pWa': easy to dictate, ~71 bits."""
    return "-".join("".join(secrets.choice(_ALPHABET) for _ in range(4)) for _ in range(3))


@dataclass
class ImportResult:
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)  # "fila N: motivo"


def read_planilla(source: Union[Path, IO[bytes]]) -> tuple[list[dict[str, str]], list[str]]:
    """Valid rows and the reasons for the skipped ones. Read as text: 0123 stays 0123, not 123.0."""
    users, skipped = [], []
    for i, row in pd.read_excel(source, dtype=str).iterrows():
        nombre, email, password = (str(row.iloc[c]).strip() if c < len(row) and pd.notna(row.iloc[c]) else ""
                                   for c in (0, 2, 3))
        email = email.lower()
        if not (nombre or email or password):
            continue  # blank row (the template has formatted, empty rows)
        problem = ("faltan datos" if not (nombre and email and password)
                   else email_problem(email) or password_problem(password, email))
        if problem:
            skipped.append(f"fila {i + 2}: {problem}")
        else:
            users.append({"nombre": nombre, "email": email, "password": password})
    return users, skipped


def import_users(users: list[dict[str, str]], reset_passwords: bool = False, dry_run: bool = False) -> ImportResult:
    """Creates the new users and updates the names of the existing ones; passwords are provisional.

    Existing users keep their password (they may have changed it) unless reset_passwords.
    """
    result = ImportResult()
    existing = {u["email"] for u in db.list_users()}
    for u in users:
        (result.updated if u["email"] in existing else result.created).append(u["email"])
        if not dry_run:
            db.upsert_user(u["email"], u["password"], u["nombre"], reset_password=reset_passwords, provisional=True)
    return result
