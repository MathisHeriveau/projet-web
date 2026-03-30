from __future__ import annotations

from pathlib import Path

from flask import Flask, render_template
from .extensions import db, sess
from .routes.api import api_bp
from .routes.web import web_bp

BASE_DIR = Path(__file__).resolve().parent.parent


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )

    app.config["SECRET_KEY"] = "dev-secret"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///GenFlixBD.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["SESSION_TYPE"] = "sqlalchemy"
    app.config["SESSION_SQLALCHEMY"] = db

    db.init_app(app)
    sess.init_app(app)
    
    with app.app_context():
        db.create_all()

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp)

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("404.html"), 404

    return app
