from __future__ import annotations

from flask import Blueprint, jsonify

from ..db import DATABASE_LABEL

from wrapper import login_required

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.get("/api/login")
def login():
    """
    Login
    """
    pass

@api_bp.get("/api/register")
def register():
    """
    Register
    """
    pass

@api_bp.get("/api/logout")
@login_required
def logout():
    """
    Logout
    """
    pass

@api_bp.get("/api/recommendation")
@login_required
def recommendation():
    """
    Recommendation from Gemini
    """
    pass
