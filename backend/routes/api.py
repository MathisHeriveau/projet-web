from __future__ import annotations
import json

from flask import Blueprint, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from backend.enums.http_status import HTTPStatus
from backend.enums.opinion_type import OpinionType
from backend.extensions import db
from backend.models import Opinion, Recommendation, User, Serie
from backend.providers.gemini_provider import GeminiProvider
from backend.providers.tvmaze_api_provider import get_all_series_from_tvmaze, search_series_from_tvmaze
from backend.routes.wrapper import login_required
from google.genai import types 


api_bp = Blueprint("api", __name__, url_prefix="/api")
gemini_provider = GeminiProvider()


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
    current_username = session.get("user")
    user = User.get_by_username(current_username)

    if not user:
        return {"error": "User not found"}, HTTPStatus.NOT_FOUND.value
    
    data = request.get_json(silent=True) or {}
    saved_count = 0

    for show in data.get("shows", []):
        id_serie = show.get("id")
        title = str(show.get("title") or "").strip()
        genres = show.get("genres") or []
        summary = str(show.get("summary") or "").strip()

        if not id_serie or not title:
            continue

        serie = Serie.get_by_id(id_serie)
        if not serie:
            genres_str = ", ".join(genres) if isinstance(genres, list) else str(genres)
            serie = Serie(
                id=id_serie,
                title=title,
                genres=genres_str,
                summary=summary,
            )
            db.session.add(serie)
            db.session.flush()
        else:
            if isinstance(genres, list):
                serie.genres = (", ".join(genres) or serie.genres)
            elif genres:
                serie.genres = str(genres)

            if summary:
                serie.summary = summary

        existing_op = Opinion.get_opinion_by_user_id_and_serie_id(user.id, serie.id)
        if not existing_op:
            opinion = Opinion(user_id=user.id, serie_id=serie.id, opinion=OpinionType.LIKED, viewed=True)
            db.session.add(opinion)
            saved_count += 1
    
    if saved_count == 0:
        return {"error": "No valid series were saved"}, HTTPStatus.BAD_REQUEST.value

    user.first_connection = False
    db.session.commit()

    return {"success": "liked series saved", "redirect": url_for("web.account")}, HTTPStatus.OK.value

@api_bp.route("/save_recommendation_text", methods=["POST"])
@login_required
def save_recommendation_text():
    """
    Save the recommendation text
    """
    current_username = session.get("user")
    user = User.get_by_username(current_username)

    if not user:
        return {"error": "User not found"}, HTTPStatus.NOT_FOUND.value
    
    data = request.get_json()
    recommendation_text = data.get("recommendation_text", "")
    user.recommendation_text = recommendation_text

    db.session.commit()
    
    return {"success": "recommendation text saved"}, HTTPStatus.OK.value


@api_bp.route("/recommendation/text", methods=["GET"])
@login_required
def recommendation_text():
    """
    Generate a recommendation text from Gemini based on the user's liked series
    """
    current_username = session.get("user")
    user = User.get_by_username(current_username)

    if not user:
        return {"error": "User not found"}, HTTPStatus.NOT_FOUND.value

    user_opinions = Opinion.get_by_user_id(user.id)

    liked_list = []
    liked_genres_set = set()
    liked_summaries_list = []

    for op in user_opinions:
        if op.opinion == OpinionType.LIKED:
            serie = Serie.get_by_id(op.serie_id)
            if serie:
                liked_list.append(serie.title)
                liked_genres_set.update(serie.genres.split(", "))
                liked_summaries_list.append(serie.summary)

    liked_str = ", ".join(liked_list) if liked_list else "No liked series yet"
    liked_genres_str = ", ".join(liked_genres_set) if liked_genres_set else "No liked genres yet"
    liked_summaries_str = " ".join(liked_summaries_list) if liked_summaries_list else "No summaries available"

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
        response_mime_type="application/json",
        temperature=0.7,
        system_instruction=profile_context,
    )

    response = gemini_provider.client.models.generate_content(
        model=gemini_provider.model_id,
        contents="Based on my input data can you generate a text that describes my taste in series please?",
        config=config,
    )

    return {"success": response.text}, HTTPStatus.OK.value


@api_bp.route("/recommendation", methods=["GET"])
@login_required
def recommendation():
    """
    Recommendation from Gemini
    """
    current_username = session.get("user")
    user = User.get_by_username(current_username)

    if not user:
        return {"error": "User not found"}, HTTPStatus.NOT_FOUND.value

    user_opinions = Opinion.get_by_user_id(user.id)
    
    liked_list = []
    liked_genres_set = set()
    disliked_list = []
    disliked_genres_set = set()

    for op in user_opinions:
        serie = Serie.get_by_id(op.serie_id)
        if serie:
            if op.opinion == OpinionType.LIKED:
                liked_list.append(serie.title)
                liked_genres_set.update(serie.genres.split(", "))
            elif op.opinion == OpinionType.DISLIKED:
                disliked_list.append(serie.title)
                disliked_genres_set.update(serie.genres.split(", "))

    liked_str = ", ".join(liked_list) if liked_list else "No liked series yet"
    liked_genres_str = ", ".join(liked_genres_set) if liked_genres_set else "No liked genres yet"
    disliked_str = ", ".join(disliked_list) if disliked_list else "No disliked series yet"
    disliked_genres_str = ", ".join(disliked_genres_set) if disliked_genres_set else "No disliked genres yet"

    profile_context = f"""
    You are an expert TV show recommender.
    Here is the user's profile data:
    - Series they love: {liked_str}
    - Genres they love: {liked_genres_str}
    - Series they dislike: {disliked_str}
    - Genres they dislike: {disliked_genres_str}

    And here is the recommendation text that the user has already written: {user.recommendation_text}

    Rules:
    1. Never recommend anything in their 'dislike' list.
    2. Try to match the vibe of their 'love' list.
    3. Do not recommend series they already love (they already watched them).
    4. Return exactly 10 recommendations.
    5. The serie's name, genres and summary has to be written in french.
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

    try:
        gemini_data = json.loads(response.text)
    except json.JSONDecodeError:
        return {"error": "Failed to parse Gemini response"}, HTTPStatus.INTERNAL_SERVER_ERROR.value

    recommended_series = gemini_data.get("series_list", [])
    enriched_recommendations = []

    for series in recommended_series:
        title = series.get("title")
        if not title:
            continue
            
        try:
            tvmaze_results = search_series_from_tvmaze(title, limit=1)
            if tvmaze_results:
                real_show_data = tvmaze_results[0]
                real_show_data["ai_pitch"] = series.get("pitch") 
                enriched_recommendations.append(real_show_data)
            else:
                enriched_recommendations.append({
                    "title": title,
                    "ai_pitch": series.get("pitch"),
                    "error": "Show not found on TVMaze"
                })

        except Exception as e:
            print(f"TVMaze error for {title}: {e}")

    for rec in enriched_recommendations:
        serie = Serie.get_by_id(rec.get("id"))
        if not serie:
            serie = Serie(id=rec.get("id"), title=rec.get("name"), genres=", ".join(rec.get("genres", [])), summary=rec.get("summary", ""))
            db.session.add(serie)
            db.session.flush()

        recommendation = Recommendation(ai_pitch=rec.get("ai_pitch"), user_id=user.id, serie_id=serie.id)
        db.session.add(recommendation)

    db.session.commit()

    return {'success': 'recommedations generated'}, HTTPStatus.OK.value


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
