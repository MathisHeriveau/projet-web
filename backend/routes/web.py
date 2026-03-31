from __future__ import annotations

from flask import Blueprint, g, redirect, render_template, request, session, url_for

from backend.models import User
from backend.providers.tvmaze_api_provider import get_all_series_from_tvmaze

web_bp = Blueprint("web", __name__)
AUTH_ENDPOINTS = {"web.login", "web.register"}
FIRST_CONNECTION_ALLOWED_ENDPOINTS = AUTH_ENDPOINTS | {"web.gen_profile", "web.logout"}


def _home_context() -> dict[str, list]:
    return {
        "featured_shows": [],
        "last_view_shows": [],
        "last_note_shows": [],
    }


def _current_username() -> str | None:
    return session.get("user")


@web_bp.before_request
def _guard_first_connection():
    endpoint = request.endpoint
    g.user = None
    if endpoint is None:
        return None

    username = _current_username()
    if username is None:
        if endpoint in AUTH_ENDPOINTS:
            return None
        return redirect(url_for("web.login"))

    user = User.get_by_username(username)
    if user is None:
        session.clear()
        if endpoint in AUTH_ENDPOINTS:
            return None
        return redirect(url_for("web.login"))

    g.user = user

    if user.first_connection and endpoint not in FIRST_CONNECTION_ALLOWED_ENDPOINTS:
        return redirect(url_for("web.gen_profile"))

    if not user.first_connection and endpoint == "web.gen_profile":
        return redirect(url_for("web.index"))

    return None


@web_bp.route("/", endpoint="index")
def index():
    if _current_username() is None:
        return redirect(url_for("web.login"))

    return render_template("index.html", **_home_context())


@web_bp.route("/series")
def series():
    return redirect(url_for("web.index"))


@web_bp.route("/recommendations")
def recommendations():
    return redirect(url_for("web.index"))


@web_bp.route("/genProfil")
def gen_profile():
    try:
        shows = get_all_series_from_tvmaze(limit=24)
    except Exception:
        shows = []

    return render_template("genProfil.html", shows=shows)


@web_bp.route("/register")
def register():
    if _current_username() is not None:
        return redirect(url_for("web.index"))

    return render_template("register.html")


@web_bp.route("/login")
def login():
    if _current_username() is not None:
        return redirect(url_for("web.index"))

    return render_template("login.html")


@web_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("web.login"))


@web_bp.route("/account")
def account():
    if _current_username() is None:
        return redirect(url_for("web.login"))

    return redirect(url_for("web.index"))
