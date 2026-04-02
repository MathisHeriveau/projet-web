import html
import re
import json
from concurrent.futures import ThreadPoolExecutor

from backend.models import Opinion, Recommendation, User, Serie
from backend.providers.gemini_provider import GeminiProvider
from backend.enums.opinion_type import OpinionType
from backend.extensions import db
from backend.providers.tvmaze_api_provider import search_series_from_tvmaze 

from flask import session

from google.genai import types

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
from textwrap import wrap

gemini_provider = GeminiProvider()

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

        genres = split_genres(serie.genres)
        summary = clean_summary(serie.summary)

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

def _serialize_recommendation_item(show, ai_pitch="", explanation=""):
    image = show.get("image") or {}
    image_url = image.get("original") or image.get("medium")

    return {
        "id": show.get("id"),
        "title": str(show.get("title") or show.get("name") or "").strip(),
        "genres": split_genres(show.get("genres")),
        "summary": clean_summary(show.get("summary")),
        "image": {"original": image_url, "medium": image_url} if image_url else None,
        "premiered_year": str(show.get("premiered") or "").strip()[:4],
        "ai_pitch": str(ai_pitch or "").strip(),
        "explanation": str(explanation or "").strip(),
    }


def _resolve_recommended_serie(recommended_serie):
    title = str(recommended_serie.get("title") or "").strip()
    if not title:
        return None

    tvmaze_results = search_series_from_tvmaze(title, limit=1)
    if not tvmaze_results:
        return None

    show = _serialize_recommendation_item(tvmaze_results[0], recommended_serie.get("pitch"), recommended_serie.get("explanation"))
    if not show["id"] or not show["title"]:
        return None

    return show

def get_current_user():
    current_username = session.get("user")
    if not current_username:
        return None
    return User.get_by_username(current_username)

def split_genres(genres):
    if isinstance(genres, list):
        return [str(genre).strip() for genre in genres if str(genre).strip()]
    return [genre.strip() for genre in str(genres or "").split(",") if genre.strip()]


def clean_summary(summary):
    raw_summary = str(summary or "").strip()
    if not raw_summary:
        return ""

    without_tags = re.sub(r"<[^>]+>", "", raw_summary)
    return html.unescape(without_tags).strip()

def generate_recommendation_text_for_user(user):
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

def generate_recommendations_for_user(user):
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
    5. For each recommendation, provide a short explanation of why you recommended it, based on the user's profile and recommendation text.
    6. Keep the official series title in its original language so it can be matched on TVMaze. Only the genres and pitch should be written in french.
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
    recommended_series = [
        recommended_serie
        for recommended_serie in recommended_series
        if str(recommended_serie.get("title") or "").strip()
    ]
    max_workers = min(10, len(recommended_series))
    resolved_shows = []
    if max_workers > 0:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            resolved_shows = list(executor.map(_resolve_recommended_serie, recommended_series))
    for show in resolved_shows:
        if not show or show["id"] in seen_ids:
            continue

        seen_ids.add(show["id"])
        items.append(show)
    for saved_recommendation in Recommendation.query.filter_by(user_id=user.id).all():
        db.session.delete(saved_recommendation)
    for item in items:
        genres_str = ", ".join(item["genres"])
        image = item.get("image") or {}
        image_url = image.get("original") or image.get("medium")
        premiered_year = str(item.get("premiered_year") or "").strip() or None
        serie = Serie.get_by_id(item["id"])
        
        if not serie:
            serie = Serie(
                id=item["id"],
                title=item["title"],
                genres=genres_str,
                summary=item["summary"],
                image_url=image_url,
                premiered_year=premiered_year,
            )
            db.session.add(serie)
            db.session.flush()
        else:
            serie.title = item["title"] or serie.title
            serie.genres = genres_str or serie.genres
            serie.summary = item["summary"] or serie.summary
            if image_url:
                serie.image_url = image_url
            if premiered_year:
                serie.premiered_year = premiered_year

        db.session.add(
            Recommendation(
                ai_pitch=item["ai_pitch"],
                explanation=item["explanation"],
                user_id=user.id,
                serie_id=serie.id,
            )
        )

    db.session.commit()
    return items

def generate_user_genre_chart(genre_counts):
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
    return img
