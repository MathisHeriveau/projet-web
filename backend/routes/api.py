from __future__ import annotations
import json

from flask import Blueprint, request, send_file, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from backend.enums.http_status import HTTPStatus
from backend.enums.opinion_type import OpinionType
from backend.extensions import db
from backend.models import Opinion, User, Serie
from backend.providers.tvmaze_api_provider import get_all_series_from_tvmaze, search_series_from_tvmaze
from backend.routes.utils.api_utils import clean_summary, generate_recommendation_text_for_user, generate_recommendations_for_user, generate_user_genre_chart, get_current_user, split_genres
from backend.routes.wrapper import login_required


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
        return {"error": "invalid credentials", "redirect": url_for("web.index")}, HTTPStatus.UNAUTHORIZED.value

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
        return {"error": "username already taken", "redirect": url_for("web.index")}, HTTPStatus.BAD_REQUEST.value

    user = User(username=u, password_hash=generate_password_hash(p, method="pbkdf2:sha256"))
    session["user"] = u
    db.session.add(user)
    db.session.commit()
    return {"success": "account created", "redirect": url_for("web.index")}, HTTPStatus.CREATED.value


@api_bp.route("/logout")
@login_required
def logout():
    """
    Logout
    """
    session.clear()
    return {"success": "logged out", "redirect": url_for("web.login")}, HTTPStatus.OK.value


@api_bp.route("/save_liked_series", methods=["POST"])
@login_required
def save_liked_series():
    """
    Save the user's liked series
    """
    user = get_current_user()

    if not user:
        return {"error": "User not found"}, HTTPStatus.NOT_FOUND.value
    
    data = request.get_json(silent=True) or {}
    valid_count = 0

    for show in data.get("shows", []):
        id_serie = show.get("id")
        title = str(show.get("title") or "").strip()
        genres = split_genres(show.get("genres"))
        summary = clean_summary(show.get("summary"))

        if not id_serie or not title:
            continue

        valid_count += 1
        serie = Serie.get_by_id(id_serie)
        if not serie:
            genres_str = ", ".join(genres)
            serie = Serie(
                id=id_serie,
                title=title,
                genres=genres_str,
                summary=summary,
            )
            db.session.add(serie)
            db.session.flush()
        else:
            serie.genres = (", ".join(genres) or serie.genres)
            if summary:
                serie.summary = summary

        existing_op = Opinion.get_opinion_by_user_id_and_serie_id(user.id, serie.id)
        if not existing_op:
            opinion = Opinion(user_id=user.id, serie_id=serie.id, opinion=OpinionType.LIKED, viewed=True)
            db.session.add(opinion)
    
    if valid_count == 0:
        return {"error": "No valid series were saved"}, HTTPStatus.BAD_REQUEST.value

    user.first_connection = False

    try:
        user.recommendation_text = generate_recommendation_text_for_user(user)
    except Exception:
        if not user.recommendation_text:
            user.recommendation_text = ""

    db.session.commit()

    return {
        "success": "liked series saved",
        "recommendation_text": user.recommendation_text or "",
        "redirect": url_for("web.recommendations"),
    }, HTTPStatus.OK.value

@api_bp.route("/save_recommendation_text", methods=["POST"])
@login_required
def save_recommendation_text():
    """
    Save the recommendation text
    """
    user = get_current_user()

    if not user:
        return {"error": "User not found"}, HTTPStatus.NOT_FOUND.value
    
    data = request.get_json(silent=True) or {}
    recommendation_text = str(data.get("recommendation_text") or "").strip()
    user.recommendation_text = recommendation_text

    db.session.commit()
    
    return {"success": "recommendation text saved", "text": user.recommendation_text}, HTTPStatus.OK.value


@api_bp.route("/recommendation/text", methods=["GET"])
@login_required
def recommendation_text():
    """
    Generate a recommendation text from Gemini based on the user's liked series
    """
    user = get_current_user()

    if not user:
        return {"error": "User not found"}, HTTPStatus.NOT_FOUND.value

    try:
        text = generate_recommendation_text_for_user(user)
    except Exception as error:
        return {"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR.value

    return {"text": text}, HTTPStatus.OK.value


@api_bp.route("/recommendation", methods=["GET"])
@login_required
def recommendation():
    """
    Recommendation from Gemini
    """
    user = get_current_user()

    if not user:
        return {"error": "User not found"}, HTTPStatus.NOT_FOUND.value

    try:
        items = generate_recommendations_for_user(user)
    except json.JSONDecodeError:
        return {"error": "Failed to parse Gemini response"}, HTTPStatus.INTERNAL_SERVER_ERROR.value
    except Exception as error:
        return {"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR.value

    return {
        "success": "recommendations generated",
        "items": items,
    }, HTTPStatus.OK.value


@api_bp.route("/get_all_series")
@login_required
def get_all_series():
    """
    Fetch all shows from TVMaze.
    """
    format_value = (request.args.get("format") or "structured").lower()
    raw = format_value == "raw"

    try:
        shows = get_all_series_from_tvmaze(raw=raw)
    except Exception as error:
        return {"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR.value

    return {
        "source": "tvmaze",
        "format": "raw" if raw else "structured",
        "count": len(shows),
        "items": shows,
    }, HTTPStatus.OK.value


@api_bp.route("/search_series")
@login_required
def search_series():
    """
    Fetch shows from TVMaze by name.
    """
    query = (request.args.get("q") or "").strip()
    if not query:
        return {
            "source": "tvmaze",
            "query": "",
            "count": 0,
            "items": [],
        }, HTTPStatus.OK.value

    try:
        shows = search_series_from_tvmaze(query, limit=24)
    except Exception as error:
        return {"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR.value

    return {
        "source": "tvmaze",
        "query": query,
        "count": len(shows),
        "items": shows,
    }, HTTPStatus.OK.value

@api_bp.route("/set_opinion", methods=["POST"])
@login_required
def set_opinion():
    """
    Set an opinion for a serie
    """
    current_username = session.get("user")
    user = User.get_by_username(current_username)

    if not user:
        return {"error": "User not found"}, HTTPStatus.NOT_FOUND.value
    
    data = request.get_json()
    serie_id = data.get("serie_id")
    opinion_value = data.get("opinion")

    if not serie_id or not opinion_value:
        return {"error": "Missing serie_id or opinion"}, HTTPStatus.BAD_REQUEST.value

    try:
        opinion_enum = OpinionType(opinion_value)
    except ValueError:
        return {"error": "Invalid opinion value"}, HTTPStatus.BAD_REQUEST.value

    serie = Serie.get_by_id(serie_id)
    if not serie:
        return {"error": "Serie not found"}, HTTPStatus.NOT_FOUND.value

    existing_opinion = Opinion.get_opinion_by_user_id_and_serie_id(user.id, serie.id)
    
    if existing_opinion:
        existing_opinion.opinion = opinion_enum
        existing_opinion.viewed = True
    else:
        new_opinion = Opinion(user_id=user.id, serie_id=serie.id, opinion=opinion_enum, viewed=True)
        db.session.add(new_opinion)

    db.session.commit()

    return {"success": "Opinion saved"}, HTTPStatus.OK.value

@api_bp.route("/gen_genre_chart")
@login_required
def gen_genre_chart():
    """
    Generate data for a genre distribution chart based on the user's opinions.
    """
    user = get_current_user()

    if not user:
        return {"error": "User not found"}, HTTPStatus.NOT_FOUND.value

    user_opinions = Opinion.get_by_user_id(user.id)
    
    genre_counts = {}

    for op in user_opinions:
        serie = Serie.get_by_id(op.serie_id)
        if serie:
            genres = [g.strip() for g in serie.genres.split(",")]
            for genre in genres:
                if genre not in genre_counts:
                    genre_counts[genre] = {"liked": 0, "disliked": 0}
                if op.opinion == OpinionType.LIKED:
                    genre_counts[genre]["liked"] += 1
                elif op.opinion == OpinionType.DISLIKED:
                    genre_counts[genre]["disliked"] += 1

    img = generate_user_genre_chart(genre_counts)

    return send_file(img, mimetype="image/png")
