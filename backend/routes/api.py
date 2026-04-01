from __future__ import annotations

from flask import Blueprint, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from backend.enums.http_status import HTTPStatus
from backend.enums.opinion_type import OpinionType
from backend.extensions import db
from backend.models import Opinion, User, Serie
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
        return {"error": "invalid credentials", "redirect": "/"}, HTTPStatus.UNAUTHORIZED.value

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
        return {"error": "username already taken", "redirect": "/"}, HTTPStatus.BAD_REQUEST.value

    user = User(username=u, password_hash=generate_password_hash(p, method="pbkdf2:sha256"))
    session["user"] = u
    db.session.add(user)
    db.session.commit()
    return {"success": "account created", "redirect": "/"}, HTTPStatus.CREATED.value


@api_bp.route("/logout")
@login_required
def logout():
    """
    Logout
    """
    session.clear()
    return {"success": "logged out", "redirect": "/login"}, HTTPStatus.OK.value


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
        serie = Serie.query.filter_by(name=data["name"]).first()
        if not serie:
            serie = Serie(name=data["name"], genres=data["genres"], summary=data["summary"])
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
            "serie_name": serie.name if serie else "Unknown",
            "opinion": op.opinion.value, 
            "viewed": op.viewed,
        })

    return {"opinions": opinions_data}, HTTPStatus.OK.value


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
                liked_list.append(serie.name)
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
                liked_list.append(serie.name)
                liked_genres_set.update(serie.genres.split(", "))
            elif op.opinion == OpinionType.DISLIKED:
                disliked_list.append(serie.name)
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

    return {"success": response.text}, HTTPStatus.OK.value


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
