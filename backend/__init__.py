from __future__ import annotations

import sqlite3
from pathlib import Path
from stat import S_IWUSR

from flask import Flask, render_template
from .extensions import db, sess
from .routes.api import api_bp
from .routes.web import web_bp

BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"
DB_PATH = INSTANCE_DIR / "GenFlixBD.db"


def _prepare_instance_storage() -> None:
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

    if DB_PATH.exists():
        DB_PATH.chmod(DB_PATH.stat().st_mode | S_IWUSR)


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )

    app.config["SECRET_KEY"] = "dev-secret"
    _prepare_instance_storage()

    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["SESSION_TYPE"] = "sqlalchemy"
    app.config["SESSION_SQLALCHEMY"] = db

    db.init_app(app)
    sess.init_app(app)
    
    with app.app_context():
        db.drop_all()
        db.create_all()

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp)

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("404.html"), 404

    return app
