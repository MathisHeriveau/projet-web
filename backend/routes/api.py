from __future__ import annotations

from flask import Blueprint, jsonify

from ..db import DATABASE_LABEL


api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.get("/example")
def example():
    return jsonify({"message": "Exemple API", "database": DATABASE_LABEL})
