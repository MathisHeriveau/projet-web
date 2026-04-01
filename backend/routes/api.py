from __future__ import annotations
import html
import json
import re
from textwrap import wrap

from flask import Blueprint, request, send_file, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from backend.enums.http_status import HTTPStatus
from backend.enums.opinion_type import OpinionType
from backend.extensions import db
from backend.models import Opinion, Recommendation, User, Serie
from backend.providers.gemini_provider import GeminiProvider
from backend.providers.tvmaze_api_provider import get_all_series_from_tvmaze, search_series_from_tvmaze
from backend.routes.wrapper import login_required
from google.genai import types 

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO


api_bp = Blueprint("api", __name__, url_prefix="/api")
gemini_provider = GeminiProvider()


def _get_current_user():
    current_username = session.get("user")
    if not current_username:
        return None
    return User.get_by_username(current_username)


def _split_genres(genres):
    if isinstance(genres, list):
        return [str(genre).strip() for genre in genres if str(genre).strip()]
    return [genre.strip() for genre in str(genres or "").split(",") if genre.strip()]


def _clean_summary(summary):
    raw_summary = str(summary or "").strip()
    if not raw_summary:
        return ""

    without_tags = re.sub(r"<[^>]+>", "", raw_summary)
    return html.unescape(without_tags).strip()


def _serialize_recommendation_item(show, ai_pitch=""):
    image = show.get("image") or {}
    image_url = image.get("medium") or image.get("original")

    return {
        "id": show.get("id"),
        "title": str(show.get("title") or show.get("name") or "").strip(),
        "genres": _split_genres(show.get("genres")),
        "summary": _clean_summary(show.get("summary")),
        "image": {"medium": image_url} if image_url else None,
        "ai_pitch": str(ai_pitch or "").strip(),
    }


def _build_user_profile(user):
    liked_titles = []
    liked_genres = set()
    liked_summaries = []
    disliked_titles = []
    disliked_genres = set()

    for opinion in Opinion.get_by_user_id(user.id):
        serie = Serie.get_by_id(opinion.serie_id)
        if not serie:
            continue

        genres = _split_genres(serie.genres)
        summary = _clean_summary(serie.summary)

        if opinion.opinion == OpinionType.LIKED:
            liked_titles.append(serie.title)
            liked_genres.update(genres)
            if summary:
                liked_summaries.append(summary)
        elif opinion.opinion == OpinionType.DISLIKED:
            disliked_titles.append(serie.title)
            disliked_genres.update(genres)

    return {
        "liked_titles": liked_titles,
        "liked_genres": sorted(liked_genres),
        "liked_summaries": liked_summaries,
        "disliked_titles": disliked_titles,
        "disliked_genres": sorted(disliked_genres),
    }


def _generate_recommendation_text_for_user(user):
    profile = _build_user_profile(user)

    liked_str = ", ".join(profile["liked_titles"]) if profile["liked_titles"] else "No liked series yet"
    liked_genres_str = ", ".join(profile["liked_genres"]) if profile["liked_genres"] else "No liked genres yet"
    liked_summaries_str = " ".join(profile["liked_summaries"]) if profile["liked_summaries"] else "No summaries available"

    profile_context = f"""
    You are an expert TV show recommender.
    Here is the user's profile data:
    - Series they love: {liked_str}
    - Genres they love: {liked_genres_str}
    - Summary of loved series: {liked_summaries_str}

    Rules:
    1. Try to match the vibe of their 'love' list.
    2. Be as much precise as possible in your answer, do not be vague.
    3. Return a text written in a natural, engaging style, in first person like if the user was describing their own taste, and in french.
    """

    config = types.GenerateContentConfig(
        response_mime_type="text/plain",
        temperature=0.7,
        system_instruction=profile_context,
    )

    response = gemini_provider.client.models.generate_content(
        model=gemini_provider.model_id,
        contents="Based on my input data can you generate a text that describes my taste in series please?",
        config=config,
    )

    return str(response.text or "").strip()


def _generate_recommendations_for_user(user):
    profile = _build_user_profile(user)

    liked_str = ", ".join(profile["liked_titles"]) if profile["liked_titles"] else "No liked series yet"
    liked_genres_str = ", ".join(profile["liked_genres"]) if profile["liked_genres"] else "No liked genres yet"
    disliked_str = ", ".join(profile["disliked_titles"]) if profile["disliked_titles"] else "No disliked series yet"
    disliked_genres_str = ", ".join(profile["disliked_genres"]) if profile["disliked_genres"] else "No disliked genres yet"

    profile_context = f"""
    You are an expert TV show recommender.
    Here is the user's profile data:
    - Series they love: {liked_str}
    - Genres they love: {liked_genres_str}
    - Series they dislike: {disliked_str}
    - Genres they dislike: {disliked_genres_str}

    And here is the recommendation text that the user has already written: {user.recommendation_text or ""}

    Rules:
    1. Never recommend anything in their 'dislike' list.
    2. Try to match the vibe of their 'love' list.
    3. Do not recommend series they already love (they already watched them).
    4. Return exactly 10 recommendations.
    5. Keep the official series title in its original language so it can be matched on TVMaze. Only the genres and pitch should be written in french.
    """

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=gemini_provider.series_recommendation_schema,
        temperature=0.7,
        system_instruction=profile_context,
    )

    response = gemini_provider.client.models.generate_content(
        model=gemini_provider.model_id,
        contents="Based on my input data can you recommend me 10 series please?",
        config=config,
    )

    gemini_data = json.loads(response.text or "{}")
    recommended_series = gemini_data.get("series_list", [])
    seen_ids = set()
    items = []

    for recommended_serie in recommended_series:
        title = str(recommended_serie.get("title") or "").strip()
        if not title:
            continue

        tvmaze_results = search_series_from_tvmaze(title, limit=1)
        if not tvmaze_results:
            continue

        show = _serialize_recommendation_item(tvmaze_results[0], recommended_serie.get("pitch"))
        if not show["id"] or show["id"] in seen_ids or not show["title"]:
            continue

        seen_ids.add(show["id"])
        items.append(show)

    for saved_recommendation in Recommendation.query.filter_by(user_id=user.id).all():
        db.session.delete(saved_recommendation)

    for item in items:
        genres_str = ", ".join(item["genres"])
        serie = Serie.get_by_id(item["id"])

        if not serie:
            serie = Serie(
                id=item["id"],
                title=item["title"],
                genres=genres_str,
                summary=item["summary"],
            )
            db.session.add(serie)
            db.session.flush()
        else:
            serie.title = item["title"] or serie.title
            serie.genres = genres_str or serie.genres
            serie.summary = item["summary"] or serie.summary

        db.session.add(
            Recommendation(
                ai_pitch=item["ai_pitch"],
                user_id=user.id,
                serie_id=serie.id,
            )
        )

    db.session.commit()
    return items


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


@api_bp.route("/test")
@login_required
def test():
    """
    Test route to add 5 liked and 5 disliked opinions for the current user in the database 
    with real names of series, then return all the opinions of the user.
    """
    current_username = session.get("user")
    user = User.get_by_username(current_username)

    if not user:
        return {"error": "User not found"}, HTTPStatus.NOT_FOUND.value

    # 1. Define series data including the new 'genres' and 'summary' fields
    liked_series_data = [
        {"name": "Breaking Bad", "genres": "Drama, Crime", "summary": "A chemistry teacher turns to cooking meth."},
        {"name": "Stranger Things", "genres": "Sci-Fi, Horror", "summary": "Kids fight monsters from the Upside Down."},
        {"name": "The Crown", "genres": "Drama, History", "summary": "The reign of Queen Elizabeth II."},
        {"name": "The Mandalorian", "genres": "Sci-Fi, Action", "summary": "A lone bounty hunter navigates the outer reaches."},
        {"name": "The Witcher", "genres": "Fantasy, Action", "summary": "A monster hunter struggles to find his place."}
    ]
    
    disliked_series_data = [
        {"name": "Game of Thrones", "genres": "Fantasy, Drama", "summary": "Noble families fight for the Iron Throne."},
        {"name": "The Big Bang Theory", "genres": "Comedy", "summary": "Geeky physicists learn about life and love."},
        {"name": "Lost", "genres": "Sci-Fi, Mystery", "summary": "Survivors of a plane crash on a mysterious island."},
        {"name": "How I Met Your Mother", "genres": "Comedy, Romance", "summary": "A father recounts his youth to his kids."},
        {"name": "The Walking Dead", "genres": "Horror, Drama", "summary": "Survivors navigate a zombie apocalypse."}
    ]

    # Helper function to find a Serie or create it if it doesn't exist
    def get_or_create_serie(data):
        serie = Serie.query.filter_by(title=data["name"]).first()
        if not serie:
            serie = Serie(title=data["name"], genres=data["genres"], summary=data["summary"])
            db.session.add(serie)
            db.session.flush() # Flush pushes the insert to the DB to generate the ID without committing the whole transaction yet
        return serie

    # 2. Process Liked Series
    for data in liked_series_data:
        serie = get_or_create_serie(data)
        
        # Check if opinion already exists so we don't duplicate if you hit the test route twice
        existing_op = Opinion.get_opinion_by_user_id_and_serie_id(user.id, serie.id)
        if not existing_op:
            opinion = Opinion(user_id=user.id, serie_id=serie.id, opinion=OpinionType.LIKED, viewed=True)
            db.session.add(opinion)

    # 3. Process Disliked Series
    for data in disliked_series_data:
        serie = get_or_create_serie(data)
        
        existing_op = Opinion.get_opinion_by_user_id_and_serie_id(user.id, serie.id)
        if not existing_op:
            opinion = Opinion(user_id=user.id, serie_id=serie.id, opinion=OpinionType.DISLIKED, viewed=True)
            db.session.add(opinion)

    # Commit everything at once!
    db.session.commit()

    # 4. Fetch the opinions and construct the response
    opinions = Opinion.get_by_user_id(user.id)
    opinions_data = []
    
    for op in opinions:
        # Fetch the linked Serie object to retrieve the actual name
        serie = Serie.get_by_id(op.serie_id)
        opinions_data.append({
            "serie_name": serie.title if serie else "Unknown",
            "opinion": op.opinion.value, 
            "viewed": op.viewed,
        })

    return {"opinions": opinions_data}, HTTPStatus.OK.value

@api_bp.route("/save_liked_series", methods=["POST"])
@login_required
def save_liked_series():
    """
    Save the user's liked series
    """
    user = _get_current_user()

    if not user:
        return {"error": "User not found"}, HTTPStatus.NOT_FOUND.value
    
    data = request.get_json(silent=True) or {}
    valid_count = 0

    for show in data.get("shows", []):
        id_serie = show.get("id")
        title = str(show.get("title") or "").strip()
        genres = _split_genres(show.get("genres"))
        summary = _clean_summary(show.get("summary"))

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
        user.recommendation_text = _generate_recommendation_text_for_user(user)
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
    user = _get_current_user()

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
    user = _get_current_user()

    if not user:
        return {"error": "User not found"}, HTTPStatus.NOT_FOUND.value

    try:
        text = _generate_recommendation_text_for_user(user)
    except Exception as error:
        return {"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR.value

    return {"text": text}, HTTPStatus.OK.value


@api_bp.route("/recommendation", methods=["GET"])
@login_required
def recommendation():
    """
    Recommendation from Gemini
    """
    user = _get_current_user()

    if not user:
        return {"error": "User not found"}, HTTPStatus.NOT_FOUND.value

    try:
        items = _generate_recommendations_for_user(user)
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
    user = _get_current_user()

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

    theme_background = "#030910"
    theme_surface = "#101c27"
    theme_border = "#192d3f"
    theme_text = "#ffffff"
    theme_muted = "#9da2a5"
    liked_color = "#b81e21"
    disliked_color = "#ff7a7d"

    fig, ax = plt.subplots(
        figsize=(8.2, 8.2),
        subplot_kw=dict(polar=True),
        facecolor=theme_background,
    )
    fig.patch.set_facecolor(theme_background)
    ax.set_facecolor(theme_surface)
    ax.spines["polar"].set_color(theme_border)
    ax.spines["polar"].set_linewidth(1.1)

    if not genre_counts:
        ax.text(
            0.5,
            0.5,
            "Aucune donnee de genre disponible",
            ha="center",
            va="center",
            color=theme_text,
            fontsize=14,
            transform=ax.transAxes,
        )
        ax.set_axis_off()
    else:
        sorted_genres = sorted(
            genre_counts.items(),
            key=lambda item: item[1]["liked"] + item[1]["disliked"],
            reverse=True,
        )

        genres = [genre for genre, _counts in sorted_genres]
        liked_counts = [genre_counts[g]["liked"] for g in genres]
        disliked_counts = [genre_counts[g]["disliked"] for g in genres]

        liked_counts += liked_counts[:1]
        disliked_counts += disliked_counts[:1]
        
        angles = [n / float(len(genres)) * 2 * np.pi for n in range(len(genres))]
        angles += angles[:1]

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels([])

        ax.set_rlabel_position(0)
        max_val = max(max(liked_counts), max(disliked_counts))
        label_radius = max_val + max(1.3, max_val * 0.42)
        ax.set_ylim(0, label_radius)
        ax.set_yticks(range(1, max_val + 1))
        ax.set_yticklabels(
            [str(value) for value in range(1, max_val + 1)],
            color=theme_muted,
            fontsize=8,
        )
        ax.tick_params(pad=6)
        ax.yaxis.grid(True, color=theme_border, alpha=0.75, linewidth=0.8)
        ax.xaxis.grid(True, color=theme_border, alpha=0.45, linewidth=0.8)

        for angle, genre in zip(angles[:-1], genres):
            angle_degrees = np.degrees(angle)
            wrapped_genre = "\n".join(wrap(genre, 14))

            if 80 <= angle_degrees <= 100 or 260 <= angle_degrees <= 280:
                horizontal_alignment = "center"
            elif 90 < angle_degrees < 270:
                horizontal_alignment = "right"
            else:
                horizontal_alignment = "left"

            ax.text(
                angle,
                label_radius,
                wrapped_genre,
                color=theme_text,
                fontsize=10.5,
                fontweight="semibold",
                ha=horizontal_alignment,
                va="center",
                clip_on=False,
                bbox={
                    "boxstyle": "round,pad=0.26",
                    "facecolor": theme_background,
                    "edgecolor": theme_border,
                    "linewidth": 0.9,
                },
            )

        ax.plot(
            angles,
            liked_counts,
            color=liked_color,
            linewidth=2.6,
            linestyle="solid",
        )
        ax.fill(angles, liked_counts, color=liked_color, alpha=0.28)

        ax.plot(
            angles,
            disliked_counts,
            color=disliked_color,
            linewidth=2.2,
            linestyle="solid",
        )
        ax.fill(angles, disliked_counts, color=disliked_color, alpha=0.14)

    img = BytesIO()
    fig.savefig(
        img,
        format="png",
        bbox_inches="tight",
        pad_inches=0.4,
        facecolor=fig.get_facecolor(),
    )
    img.seek(0)
    plt.close(fig)

    return send_file(img, mimetype="image/png")
