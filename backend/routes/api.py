from __future__ import annotations
from backend.enums.http_status import HTTPStatus
from flask import Blueprint, request, session, g
from werkzeug.security import generate_password_hash, check_password_hash
from backend.extensions import db
from backend.routes.wrapper import login_required
from backend.models import User

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/login", methods=["POST"])
def login():
    """
    Login
    """
    data = request.get_json()
    u = data.get("username", "")
    p = data.get("password", "")

    user = User.get_by_username(u)
    if user is None or not check_password_hash(user.password_hash, p):
        return {"error": "invalid credentials"}, HTTPStatus.UNAUTHORIZED.value

    session["user"] = u
    return {"success": "logged in"}, HTTPStatus.OK.value

@api_bp.route("/register", methods=["POST"])
def register():
    """
    Register
    """
    data = request.get_json()
    u = data.get("username", "")
    p = data.get("password", "")

    user = User.get_by_username(u)

    if user is not None:
        return {"error": "username already taken"}, HTTPStatus.BAD_REQUEST.value

    user = User(username=u, password_hash=generate_password_hash(p))
    session["user"] = u
    db.session.add(user)
    db.session.commit()
    return {"success": "account created"}, HTTPStatus.CREATED.value

@api_bp.route("/logout")
@login_required
def logout():
    """
    Logout
    """
    session.clear()
    return {"success": "logged out"}, HTTPStatus.OK.value

@api_bp.route("/recommendation")
@login_required
def recommendation():
    """
    Recommendation from Gemini
    """
    pass
