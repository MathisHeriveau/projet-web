from __future__ import annotations

from flask import Blueprint, g, redirect, render_template, request, session, url_for

from backend.models import User
from backend.providers.tvmaze_api_provider import get_all_series_from_tvmaze

web_bp = Blueprint("web", __name__)
AUTH_ENDPOINTS = {"web.login", "web.register"}
FIRST_CONNECTION_ALLOWED_ENDPOINTS = AUTH_ENDPOINTS | {"web.gen_account", "web.logout"}

HOME_FEATURED_INDEXES = [0, 1, 2, 3]
HOME_LAST_VIEW_INDEXES = [4, 5, 6]
HOME_LAST_NOTE_INDEXES = [7, 8, 9]

HOME_LAST_VIEW_DISPLAY = [
    {
        "reaction": "liked",
        "reaction_icon": "bi-hand-thumbs-up-fill",
        "reaction_label": "Aimee",
    },
    {
        "reaction": "liked",
        "reaction_icon": "bi-hand-thumbs-up-fill",
        "reaction_label": "Aimee",
    },
    {
        "reaction": "neutral",
        "reaction_icon": "bi-dash-circle-fill",
        "reaction_label": "Mitigee",
    },
]

HOME_LAST_NOTE_DISPLAY = [
    {
        "timeline": "Notee il y a 2 jours",
        "reaction": "liked",
        "reaction_icon": "bi-hand-thumbs-up-fill",
        "reaction_label": "Aimee",
    },
    {
        "timeline": "Notee il y a 5 jours",
        "reaction": "neutral",
        "reaction_icon": "bi-dash-circle-fill",
        "reaction_label": "Mitigee",
    },
    {
        "timeline": "Notee il y a 1 semaine",
        "reaction": "disliked",
        "reaction_icon": "bi-hand-thumbs-down-fill",
        "reaction_label": "Pas aimee",
    },
]


def _pick_show_by_index(shows: list[dict], index: int) -> dict | None:
    if 0 <= index < len(shows):
        return shows[index]
    return None


def _show_name(show: dict) -> str:
    return show.get("name") or "Serie inconnue"


def _show_image(show: dict, fallback_image: str) -> str:
    image = show.get("image") or {}
    return image.get("original") or image.get("medium") or fallback_image


def _show_year(show: dict) -> str:
    premiered = show.get("premiered") or ""
    return premiered[:4] if premiered else "Annee inconnue"


def _show_genres(show: dict) -> str:
    genres = show.get("genres") or []
    return ", ".join(genres) if genres else "Genres inconnus"


def _show_meta(show: dict) -> str:
    runtime = show.get("averageRuntime") or show.get("runtime")
    if runtime:
        return f"{runtime} min"

    status = show.get("status")
    if status:
        return status

    return "Serie TV"


def _build_featured_shows(shows: list[dict], fallback_image: str) -> list[dict]:
    featured_shows = []

    for index in HOME_FEATURED_INDEXES:
        show = _pick_show_by_index(shows, index)
        if show is None:
            continue

        featured_shows.append(
            {
                "name": _show_name(show),
                "subtitle": show.get("type") or "Serie mise en avant",
                "year": _show_year(show),
                "genres": _show_genres(show),
                "meta": _show_meta(show),
                "image": _show_image(show, fallback_image),
            }
        )

    return featured_shows


def _build_last_view_shows(shows: list[dict], fallback_image: str) -> list[dict]:
    last_view_shows = []

    for index, display in zip(HOME_LAST_VIEW_INDEXES, HOME_LAST_VIEW_DISPLAY):
        show = _pick_show_by_index(shows, index)
        if show is None:
            continue

        last_view_shows.append(
            {
                "name": _show_name(show),
                "image": _show_image(show, fallback_image),
                **display,
            }
        )

    return last_view_shows


def _build_last_note_shows(shows: list[dict], fallback_image: str) -> list[dict]:
    last_note_shows = []

    for index, display in zip(HOME_LAST_NOTE_INDEXES, HOME_LAST_NOTE_DISPLAY):
        show = _pick_show_by_index(shows, index)
        if show is None:
            continue

        last_note_shows.append(
            {
                "name": _show_name(show),
                "image": _show_image(show, fallback_image),
                **display,
            }
        )

    return last_note_shows


def _home_context() -> dict[str, list]:
    placeholder_image = url_for("static", filename="images/no-image-blog.jpg")
    all_indexes = HOME_FEATURED_INDEXES + HOME_LAST_VIEW_INDEXES + HOME_LAST_NOTE_INDEXES
    required_count = (max(all_indexes) + 1) if all_indexes else 0

    try:
        shows = get_all_series_from_tvmaze(raw=True, limit=required_count)
    except Exception:
        shows = []

    return {
        "featured_shows": _build_featured_shows(shows, placeholder_image),
        "last_view_shows": _build_last_view_shows(shows, placeholder_image),
        "last_note_shows": _build_last_note_shows(shows, placeholder_image),
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
        return redirect(url_for("web.gen_account"))

    if not user.first_connection and endpoint == "web.gen_account":
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
    if _current_username() is None:
        return redirect(url_for("web.login"))

    return render_template("recommendation.html")


@web_bp.route("/gen_account")
def gen_account():
    try:
        shows = get_all_series_from_tvmaze(limit=24)
    except Exception:
        shows = []

    return render_template("gen_account.html", shows=shows)


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


@web_bp.route("/account", endpoint="legacy_account")
def legacy_account():
    return redirect(url_for("web.recommendations"))
