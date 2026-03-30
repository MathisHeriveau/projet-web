from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import g


BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"


class GenFlixDatabase:
    def __init__(self, label: str = "GenFlixBD"):
        self.label = label
        self.path = INSTANCE_DIR / f"{label}.db"

    def connect(self) -> sqlite3.Connection:
        if "db_connection" not in g:
            INSTANCE_DIR.mkdir(exist_ok=True)
            g.db_connection = sqlite3.connect(self.path)
            g.db_connection.row_factory = sqlite3.Row
        return g.db_connection

    def close(self, _error=None) -> None:
        connection = g.pop("db_connection", None)
        if connection is not None:
            connection.close()

    def create_tables(self) -> None:
        connection = self.connect()
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL
            )
            """
        )

        row = connection.execute("SELECT COUNT(*) AS total FROM movies").fetchone()
        if row and row["total"] == 0:
            connection.execute(
                "INSERT INTO movies (title) VALUES (?)",
                ("Film exemple",),
            )

        connection.commit()

    def init_app(self, app) -> None:
        app.teardown_appcontext(self.close)


db = GenFlixDatabase()
DATABASE_LABEL = db.label
