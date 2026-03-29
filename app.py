from __future__ import annotations

import base64
import json
from io import BytesIO
from pathlib import Path

import matplotlib
import pandas as pd
from flask import Flask, jsonify, render_template, request, send_file

matplotlib.use("Agg")
import matplotlib.pyplot as plt


app = Flask(__name__)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
STATIC_IMG_DIR = BASE_DIR / "static" / "img"
SUPPORTED_EXTENSIONS = (".parquet", ".csv", ".json")


# -----------------------------
# Utilitaires data
# -----------------------------
def list_data_files() -> list[Path]:
    return sorted(
        [path for path in DATA_DIR.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS]
    )


def resolve_data_file(filename: str | None = None) -> Path:
    if filename:
        candidate = (DATA_DIR / filename).resolve()
        if DATA_DIR.resolve() not in candidate.parents and candidate != DATA_DIR.resolve():
            raise FileNotFoundError("Chemin de dataset invalide.")
        if candidate.exists():
            return candidate
        raise FileNotFoundError(f"Dataset introuvable: {filename}")

    files = list_data_files()
    if not files:
        raise FileNotFoundError("Aucun dataset disponible dans data/.")
    return files[0]


def load_dataframe(filename: str | None = None) -> tuple[pd.DataFrame, Path]:
    dataset_path = resolve_data_file(filename)
    suffix = dataset_path.suffix.lower()

    if suffix == ".parquet":
        dataframe = pd.read_parquet(dataset_path)
    elif suffix == ".csv":
        dataframe = pd.read_csv(dataset_path)
    elif suffix == ".json":
        with dataset_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        dataframe = pd.json_normalize(payload if isinstance(payload, list) else [payload])
    else:
        raise ValueError(f"Format non supporte: {suffix}")

    return dataframe, dataset_path


def dataframe_preview(dataframe: pd.DataFrame, limit: int = 10) -> list[dict]:
    preview = dataframe.head(limit).where(pd.notnull(dataframe.head(limit)), None)
    return preview.to_dict(orient="records")


# -----------------------------
# Utilitaires media / plot
# -----------------------------
def image_file_to_base64(filename: str) -> dict[str, str]:
    image_path = (STATIC_IMG_DIR / filename).resolve()
    if STATIC_IMG_DIR.resolve() not in image_path.parents and image_path != STATIC_IMG_DIR.resolve():
        raise FileNotFoundError("Chemin image invalide.")
    if not image_path.exists():
        raise FileNotFoundError(f"Image introuvable: {filename}")

    encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    mime_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    return {
        "filename": image_path.name,
        "mime_type": mime_type,
        "base64": encoded,
        "data_url": f"data:{mime_type};base64,{encoded}",
    }


def build_placeholder_plot(title: str = "Titre du plot", values: list[float] | None = None):
    figure, axis = plt.subplots(figsize=(5.2, 3))
    values = values or [1, 3, 2, 4]
    axis.plot(values, marker="o", color="#49657f")
    axis.set_title(title)
    axis.grid(alpha=0.2)
    figure.tight_layout()
    return figure


def figure_to_png_response(figure):
    image = BytesIO()
    figure.savefig(image, format="png", bbox_inches="tight")
    plt.close(figure)
    image.seek(0)
    return send_file(image, mimetype="image/png")


# -----------------------------
# Routes squelette
# -----------------------------
@app.route("/")
def index():
    return render_template("index.html", data_files=[path.name for path in list_data_files()])


@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok", "message": "Squelette Flask pret."})


@app.route("/api/get-example")
def api_get_example():
    # TODO: Recuperer les query params utiles puis brancher ta logique metier.
    return jsonify(
        {
            "method": "GET",
            "message": "Route squelette GET.",
            "query_params": request.args.to_dict(),
        }
    )


@app.route("/api/post-example", methods=["POST"])
def api_post_example():
    # TODO: Valider le payload JSON puis appeler ta logique metier.
    payload = request.get_json(silent=True) or {}
    return jsonify(
        {
            "method": "POST",
            "message": "Route squelette POST.",
            "received": payload,
        }
    )


@app.route("/api/run", methods=["GET", "POST"])
def api_run():
    # TODO: Route unifiee si tu veux gerer plusieurs modes d'execution.
    if request.method == "GET":
        return jsonify({"method": "GET", "message": "Squelette /api/run en GET."})

    payload = request.get_json(silent=True) or {}
    return jsonify({"method": "POST", "message": "Squelette /api/run en POST.", "received": payload})


@app.route("/api/data-preview")
def api_data_preview():
    # TODO: Remplir cette route si tu veux exposer un apercu d'un parquet / csv / json.
    filename = request.args.get("file")
    limit = request.args.get("limit", default=10, type=int)

    try:
        dataframe, dataset_path = load_dataframe(filename)
    except (FileNotFoundError, ValueError) as error:
        return jsonify({"error": str(error)}), 400

    return jsonify(
        {
            "source": dataset_path.name,
            "rows": len(dataframe),
            "columns": dataframe.columns.tolist(),
            "preview": dataframe_preview(dataframe, limit=max(1, min(limit, 100))),
        }
    )


@app.route("/api/image-base64")
def api_image_base64():
    # TODO: Reutiliser ce squelette pour encoder une image et la retourner au front.
    filename = request.args.get("filename", "logo.jpg")
    try:
        return jsonify(image_file_to_base64(filename))
    except FileNotFoundError as error:
        return jsonify({"error": str(error)}), 404


@app.route("/api/plot")
def api_plot():
    # TODO: Brancher ici ton vrai plot Matplotlib / Seaborn / autre.
    title = request.args.get("title", "Plot squelette")
    return figure_to_png_response(build_placeholder_plot(title=title))


if __name__ == "__main__":
    app.run(debug=True)
