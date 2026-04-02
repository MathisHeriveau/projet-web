from __future__ import annotations

from flask import Blueprint, g, redirect, render_template, request, session, url_for

from backend.models import User
from backend.providers.tvmaze_api_provider import (
    get_all_series_from_tvmaze,
    search_series_from_tvmaze,
)
from backend.routes.wrapper import login_required
from backend.routes.utils.web_utils import current_username, has_saved_recommendations, home_context, recommendation_context, save_series_opinion, series_context

web_bp = Blueprint("web", __name__)
AUTH_ENDPOINTS = {"web.login", "web.register"}
FIRST_CONNECTION_ALLOWED_ENDPOINTS = AUTH_ENDPOINTS | {"web.gen_account", "web.logout"}

@web_bp.before_request
def _guard_first_connection():
    endpoint = request.endpoint
    g.user = None
    if endpoint is None:
        return None

    username = current_username()
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
        return redirect(url_for("web.gen_account"))

    if not user.first_connection and endpoint == "web.gen_account":
        return redirect(url_for("web.index"))

    return None


@web_bp.route("/", endpoint="index")
@login_required
def index():
    if not has_saved_recommendations(g.user):
        return redirect(url_for("web.recommendations"))

    return render_template("index.html", **home_context(g.user))


@web_bp.route("/recommendations")
@login_required
def recommendations():
    return render_template("recommendation.html", **recommendation_context(g.user))


@web_bp.route("/series/<int:serie_id>", methods=["GET", "POST"])
@login_required
def series_detail(serie_id: int):
    context = series_context(serie_id, g.user)

    if request.method == "GET" and not context["current_viewed"]:
        save_series_opinion(g.user, context["show"], True, context["current_opinion"])
        context = series_context(serie_id, g.user)

    if request.method == "POST":
        opinion_value = str(request.form.get("opinion") or "").strip() or None
        save_series_opinion(g.user, context["show"], True, opinion_value)
        return redirect(url_for("web.series_detail", serie_id=serie_id, saved="1"))

    return render_template("series.html", **context)


@web_bp.route("/search")
@login_required
def search():
    query = (request.args.get("q") or "").strip()
    shows = []

    if query:
        try:
            shows = search_series_from_tvmaze(query, limit=30)
        except Exception:
            shows = []

    return render_template("search.html", query=query, shows=shows)


@web_bp.route("/gen_account")
def gen_account():
    try:
        shows = get_all_series_from_tvmaze(limit=24)
    except Exception:
        shows = []

    return render_template("gen_account.html", shows=shows)


@web_bp.route("/register")
def register():
    if current_username() is not None:
        return redirect(url_for("web.index"))

    return render_template("register.html")


@web_bp.route("/login")
def login():
    if current_username() is not None:
        return redirect(url_for("web.index"))

    return render_template("login.html")


@web_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("web.login"))
