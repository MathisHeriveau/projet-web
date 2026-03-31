from __future__ import annotations

from backend.enums.http_status import HTTPStatus
from backend.enums.opinion_type import OpinionType
from backend.models import Opinion
from backend.extensions import db
from backend.routes.wrapper import login_required
from backend.models import User
from backend.providers.gemini import GeminiProvider

from flask import Blueprint, request, session, g
from werkzeug.security import generate_password_hash, check_password_hash

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
    Test route to add 5 liked and 5 disliked opinions for the current user in the database with real names of series, then return all the opinions of the user.
    """
    current_username = session.get("user")
    user = User.get_by_username(current_username)

    if not user:
        return {"error": "User not found"}, HTTPStatus.NOT_FOUND.value

    # Add 5 liked opinions
    liked_series = ["Breaking Bad", "Stranger Things", "The Crown", "The Mandalorian", "The Witcher"]
    for serie in liked_series:
        opinion = Opinion(user_id=user.id, serie_name=serie, opinion=OpinionType.LIKED, viewed=True)
        db.session.add(opinion)

    # Add 5 disliked opinions
    disliked_series = ["Game of Thrones", "The Big Bang Theory", "Lost", "How I Met Your Mother", "The Walking Dead"]
    for serie in disliked_series:
        opinion = Opinion(user_id=user.id, serie_name=serie, opinion=OpinionType.DISLIKED, viewed=True)
        db.session.add(opinion)

    db.session.commit()

    # Return all opinions of the user
    opinions = Opinion.get_by_user_id(user.id)
    opinions_data = [
        {
            "serie_name": op.serie_name,
            "opinion": op.opinion.value,
            "viewed": op.viewed
        }
        for op in opinions
    ]

    return {"opinions": opinions_data}, HTTPStatus.OK.value


@api_bp.route("/recommendation/text", methods=["GET"])
@login_required
def recommendation_text():
    """
    Generate a recommendation text from Gemini based on the user's liked and disliked series
    """
    current_username = session.get("user")
    user = User.get_by_username(current_username)

    if not user:
        return {"error": "User not found"}, HTTPStatus.NOT_FOUND.value

    user_opinions = Opinion.get_by_user_id(user.id)
    liked_list = [op.serie_name for op in user_opinions if op.opinion == OpinionType.LIKED]
    liked_str = ", ".join(liked_list) if liked_list else "No liked series yet"

    profile_context = f"""
    You are an expert TV show recommender. 
    Here is the user's profile data:
    - Series they love: {liked_str}

    Rules:
    1. Try to match the vibe of their 'love' list.
    2. Be as much precise as possible in your answer, do not be vague.
    3. Return a text written in a natural, engaging style, in first person like if the user was describing their own taste, and in french.
    """

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.7,
        system_instruction=profile_context
    )

    response = gemini_provider.client.models.generate_content(
        model=gemini_provider.model_id,
        contents="Based on my input data can you generate a text that describes my taste in series please?",
        config=config
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
    liked_list = [op.serie_name for op in user_opinions if op.opinion == OpinionType.LIKED]
    disliked_list = [op.serie_name for op in user_opinions if op.opinion == OpinionType.DISLIKED]

    liked_str = ", ".join(liked_list) if liked_list else "No liked series yet"
    disliked_str = ", ".join(disliked_list) if disliked_list else "No disliked series yet"

    profile_context = f"""
    You are an expert TV show recommender. 
    Here is the user's profile data:
    - Series they love: {liked_str}
    - Series they dislike: {disliked_str}

    Rules:
    1. Never recommend anything in their 'dislike' list.
    2. Try to match the vibe of their 'love' list.
    3. Do not recommend series they already love (they already watched them).
    4. Return exactly 10 recommendations.
    """

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=gemini_provider.series_recommendation_schema,
        temperature=0.7,
        system_instruction=profile_context
    )

    response = gemini_provider.client.models.generate_content(
        model=gemini_provider.model_id,
        contents="Based on my input data can you recommend me 10 series please?",
        config=config
    )

    return {"success": response.text}, HTTPStatus.OK.value
