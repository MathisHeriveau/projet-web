import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen

TVMAZE_BASE_URL = "https://api.tvmaze.com"


def _serialize_show(show):
    return {
        "id": show.get("id"),
        "name": show.get("name"),
        "genres": show.get("genres"),
        "summary": show.get("summary"),
        "image": show.get("image"),
    }


def _read_tvmaze_payload(url):
    try:
        with urlopen(url) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        if error.code == 404:
            return []
        raise Exception(f"Erreur TVMaze: {error.code}") from error
    except URLError as error:
        raise Exception("Erreur TVMaze: service indisponible") from error

def get_all_series_from_tvmaze(raw=False, limit=None):
    all_series = []
    page = 0

    while True:
        url = f"{TVMAZE_BASE_URL}/shows?page={page}"
        series = _read_tvmaze_payload(url)

        if not series:
            break

        if raw:
            all_series.extend(series)
        else:
            all_series.extend(_serialize_show(serie) for serie in series)

        if limit is not None and len(all_series) >= limit:
            return all_series[:limit]

        page += 1

    return all_series


def search_series_from_tvmaze(query, limit=None):
    normalized_query = (query or "").strip()
    if not normalized_query:
        return []

    url = f"{TVMAZE_BASE_URL}/search/shows?q={quote(normalized_query)}"
    results = _read_tvmaze_payload(url)
    shows = [_serialize_show(entry.get("show") or {}) for entry in results if entry.get("show")]

    if limit is not None:
        return shows[:limit]

    return shows
