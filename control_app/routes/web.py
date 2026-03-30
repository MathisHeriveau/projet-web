from __future__ import annotations

from flask import Blueprint, render_template

from ..db import DATABASE_LABEL


web_bp = Blueprint("web", __name__)


@web_bp.get("/")
def index():
    return render_template("index.html", db_name=DATABASE_LABEL)
