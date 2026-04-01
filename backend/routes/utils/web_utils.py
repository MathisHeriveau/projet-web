from __future__ import annotations

import html
import random
import re

from flask import abort, request, session, url_for 

from backend.enums.opinion_type import OpinionType
from backend.extensions import db
from backend.models import Opinion, Recommendation, Serie, User
from backend.providers.tvmaze_api_provider import (
    get_all_series_from_tvmaze,
    get_series_from_tvmaze_by_id,
)

def _show_year(show: dict) -> str:
    premiered = show.get("premiered") or ""
    return premiered[:4] if premiered else "Annee inconnue"


def _split_stored_genres(genres: str | None) -> list[str]:
    return [genre.strip() for genre in str(genres or "").split(",") if genre.strip()]


def _clean_summary(summary: str | None) -> str:
    raw_summary = str(summary or "").strip()
    if not raw_summary:
        return "Resume indisponible."

    without_tags = re.sub(r"<[^>]+>", "", raw_summary)
    cleaned = html.unescape(without_tags).strip()
    return cleaned or "Resume indisponible."


def _opinion_display(opinion: OpinionType | str | None) -> dict[str, str]:
    opinion_value = opinion.value if isinstance(opinion, OpinionType) else str(opinion or "")

    if opinion_value == OpinionType.LIKED.value:
        return {
            "reaction": "liked",
            "reaction_icon": "bi-hand-thumbs-up-fill",
            "reaction_label": "Aime",
        }

    if opinion_value == OpinionType.DISLIKED.value:
        return {
            "reaction": "disliked",
            "reaction_icon": "bi-hand-thumbs-down-fill",
            "reaction_label": "Pas aime",
        }

    if opinion_value == OpinionType.NEUTRAL.value:
        return {
            "reaction": "neutral",
            "reaction_icon": "bi-dash-circle-fill",
            "reaction_label": "Neutre",
        }

    return {
        "reaction": "viewed",
        "reaction_icon": "bi-eye-fill",
        "reaction_label": "Vue",
    }


def _build_home_show_payload(
    serie: Serie | None,
    fallback_image: str,
    tvmaze_show: dict | None = None,
) -> dict | None:
    if serie is None and tvmaze_show is None:
        return None

    show_id = (tvmaze_show or {}).get("id") or (serie.id if serie else None)
    if show_id is None:
        return None

    if tvmaze_show is None:
        try:
            tvmaze_show = get_series_from_tvmaze_by_id(show_id)
        except Exception:
            tvmaze_show = None

    image = (tvmaze_show or {}).get("image") or {}
    genres_list = (tvmaze_show or {}).get("genres") or _split_stored_genres(
        serie.genres if serie else ""
    )
    title = str(
        (tvmaze_show or {}).get("name")
        or (tvmaze_show or {}).get("title")
        or (serie.title if serie else "")
        or "Serie inconnue"
    ).strip()

    return {
        "id": show_id,
        "name": title or "Serie inconnue",
        "image": image.get("original") or image.get("medium") or fallback_image,
        "year": _show_year(tvmaze_show or {}),
        "genres": ", ".join(genres_list) if genres_list else "Genres inconnus",
        "subtitle": (tvmaze_show or {}).get("type") or "Recommendation IA",
    }


def _build_home_recommendations(user: User, fallback_image: str, limit: int = 10) -> list[dict]:
    items = []
    saved_recommendations = (
        Recommendation.query.filter_by(user_id=user.id)
        .order_by(Recommendation.id.asc())
        .all()
    )

    for saved_recommendation in saved_recommendations:
        serie = Serie.get_by_id(saved_recommendation.serie_id)
        payload = _build_home_show_payload(serie, fallback_image)
        if not payload:
            continue

        payload["subtitle"] = "Recommendation IA"
        items.append(payload)

        if len(items) >= limit:
            break

    return items


def _build_recent_viewed_shows(user: User, fallback_image: str, limit: int = 4) -> list[dict]:
    items = []
    viewed_opinions = (
        Opinion.query.filter_by(user_id=user.id, viewed=True)
        .order_by(Opinion.id.desc())
        .all()
    )

    for opinion in viewed_opinions:
        serie = Serie.get_by_id(opinion.serie_id)
        payload = _build_home_show_payload(serie, fallback_image)
        if not payload:
            continue

        payload.update(_opinion_display(opinion.opinion))
        items.append(payload)

        if len(items) >= limit:
            break

    return items


def _build_recent_note_shows(user: User, fallback_image: str, limit: int = 3) -> list[dict]:
    items = []
    recent_opinions = (
        Opinion.query.filter_by(user_id=user.id)
        .order_by(Opinion.id.desc())
        .all()
    )

    for opinion in recent_opinions:
        if opinion.opinion is None:
            continue

        serie = Serie.get_by_id(opinion.serie_id)
        payload = _build_home_show_payload(serie, fallback_image)
        if not payload:
            continue

        payload.update(_opinion_display(opinion.opinion))
        items.append(payload)

        if len(items) >= limit:
            break

    return items


def _build_random_home_shows(
    fallback_image: str,
    excluded_ids: set[int],
    count: int = 12,
) -> list[dict]:
    try:
        shows = get_all_series_from_tvmaze(raw=True, limit=60)
    except Exception:
        return []

    available_shows = [show for show in shows if show.get("id") not in excluded_ids]
    random.shuffle(available_shows)
    items = []

    for show in available_shows:
        payload = _build_home_show_payload(None, fallback_image, tvmaze_show=show)
        if not payload:
            continue

        items.append(payload)
        if len(items) >= count:
            break

    return items


def home_context(user: User) -> dict[str, list]:
    placeholder_image = url_for("static", filename="images/no-image-blog.jpg")
    recommendation_shows = _build_home_recommendations(user, placeholder_image)
    last_view_shows = _build_recent_viewed_shows(user, placeholder_image)
    last_note_shows = _build_recent_note_shows(user, placeholder_image)

    excluded_ids = {
        show["id"]
        for show in recommendation_shows + last_view_shows + last_note_shows
        if show.get("id") is not None
    }

    return {
        "recommendation_shows": recommendation_shows,
        "last_view_shows": last_view_shows,
        "last_note_shows": last_note_shows,
        "random_shows": _build_random_home_shows(placeholder_image, excluded_ids),
    }


def has_saved_recommendations(user: User) -> bool:
    return Recommendation.query.filter_by(user_id=user.id).first() is not None


def series_context(serie_id: int, user: User) -> dict:
    placeholder_image = url_for("static", filename="images/no-image-blog.jpg")
    stored_serie = Serie.get_by_id(serie_id)

    try:
        tvmaze_show = get_series_from_tvmaze_by_id(serie_id)
    except Exception:
        tvmaze_show = None

    if not stored_serie and not tvmaze_show:
        abort(404)

    image = (tvmaze_show or {}).get("image") or {}
    title = str(
        (tvmaze_show or {}).get("name")
        or (tvmaze_show or {}).get("title")
        or (stored_serie.title if stored_serie else "")
        or "Serie inconnue"
    ).strip()
    genres = (tvmaze_show or {}).get("genres") or _split_stored_genres(
        stored_serie.genres if stored_serie else ""
    )
    summary = _clean_summary(
        (tvmaze_show or {}).get("summary")
        if tvmaze_show
        else (stored_serie.summary if stored_serie else "")
    )
    existing_opinion = Opinion.get_opinion_by_user_id_and_serie_id(user.id, serie_id)

    return {
        "show": {
            "id": serie_id,
            "title": title,
            "genres": genres,
            "summary": summary,
            "image": image.get("original") or image.get("medium") or placeholder_image,
        },
        "saved": request.args.get("saved") == "1",
        "current_viewed": existing_opinion.viewed if existing_opinion else False,
        "current_opinion": (
            existing_opinion.opinion.value if existing_opinion and existing_opinion.opinion else None
        ),
    }


def save_series_opinion(user: User, show: dict, viewed: bool, opinion_value: str | None) -> None:
    opinion_enum = None
    if opinion_value:
        try:
            opinion_enum = OpinionType(opinion_value)
        except ValueError:
            opinion_enum = None

    genres = [genre.strip() for genre in show.get("genres", []) if str(genre).strip()]
    summary = _clean_summary(show.get("summary"))
    serie = Serie.get_by_id(show["id"])

    if not serie:
        serie = Serie(
            id=show["id"],
            title=show["title"],
            genres=", ".join(genres),
            summary=summary,
        )
        db.session.add(serie)
        db.session.flush()
    else:
        serie.title = show["title"] or serie.title
        serie.genres = ", ".join(genres) or serie.genres
        serie.summary = summary or serie.summary

    existing_opinion = Opinion.get_opinion_by_user_id_and_serie_id(user.id, serie.id)
    if existing_opinion:
        existing_opinion.viewed = viewed
        existing_opinion.opinion = opinion_enum
    else:
        db.session.add(
            Opinion(
                user_id=user.id,
                serie_id=serie.id,
                viewed=viewed,
                opinion=opinion_enum,
            )
        )

    db.session.commit()


def recommendation_context(user: User) -> dict[str, list | str]:
    placeholder_image = url_for("static", filename="images/no-image-blog.jpg")
    recommendations = []

    saved_recommendations = (
        Recommendation.query.filter_by(user_id=user.id)
        .order_by(Recommendation.id.asc())
        .all()
    )

    for saved_recommendation in saved_recommendations:
        serie = Serie.get_by_id(saved_recommendation.serie_id)
        if not serie:
            continue

        image_url = placeholder_image

        try:
            tvmaze_show = get_series_from_tvmaze_by_id(serie.id)
        except Exception:
            tvmaze_show = None

        if tvmaze_show:
            image = tvmaze_show.get("image") or {}
            image_url = image.get("medium") or image.get("original") or placeholder_image

        recommendations.append(
            {
                "id": serie.id,
                "title": serie.title,
                "genres": _split_stored_genres(serie.genres),
                "summary": serie.summary,
                "ai_pitch": saved_recommendation.ai_pitch,
                "image": {"medium": image_url},
            }
        )

    return {
        "recommendation_text": user.recommendation_text or "",
        "recommendation_items": recommendations,
    }


def current_username() -> str | None:
    return session.get("user")