from __future__ import annotations

from flask import Blueprint, redirect, render_template, session, url_for

web_bp = Blueprint("web", __name__)


def _home_context() -> dict[str, list]:
    return {
        "featured_shows": [],
        "last_view_shows": [],
        "last_note_shows": [],
    }


def _current_username() -> str | None:
    return session.get("username") or session.get("user")


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
