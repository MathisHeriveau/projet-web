import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

TVMAZE_BASE_URL = "https://api.tvmaze.com"
TVMAZE_TIMEOUT_SECONDS = 10


def _serialize_show(show):
    return {
        "id": show.get("id"),
        "name": show.get("name"),
        "type": show.get("type"),
        "language": show.get("language"),
        "genres": show.get("genres"),
        "status": show.get("status"),
        "runtime": show.get("runtime"),
        "averageRuntime": show.get("averageRuntime"),
        "premiered": show.get("premiered"),
        "ended": show.get("ended"),
        "rating": (show.get("rating") or {}).get("average"),
        "image": show.get("image"),
        "network": (show.get("network") or {}).get("name"),
        "webChannel": (show.get("webChannel") or {}).get("name"),
        "url": show.get("url"),
    }

def get_all_series_from_tvmaze(raw=False, limit=None):
    all_series = []
    page = 0

    while True:
        url = f"{TVMAZE_BASE_URL}/shows?page={page}"

        try:
            with urlopen(url, timeout=TVMAZE_TIMEOUT_SECONDS) as response:
                series = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code == 404:
                break
            raise Exception(f"Erreur TVMaze: {error.code}") from error
        except URLError as error:
            raise Exception("Erreur TVMaze: service indisponible") from error

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
