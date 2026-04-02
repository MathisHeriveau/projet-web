from functools import wraps

from flask import g, redirect, request, session, url_for

from backend.models import User
from backend.enums.http_status import HTTPStatus

def login_required(f):
    """
        Login required wrapper
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            if request.blueprint == "web":
                return redirect(url_for("web.login"))
            return {"error": "Vous devez etre connecte pour acceder a cette ressource."}, HTTPStatus.UNAUTHORIZED.value

        user = User.get_by_username(session["user"])
        if user is None:
            session.clear()
            if request.blueprint == "web":
                return redirect(url_for("web.login"))
            return {"error": "La session utilisateur est invalide. Veuillez vous reconnecter."}, HTTPStatus.UNAUTHORIZED.value

        g.user = user
        return f(*args, **kwargs)

    return wrapper
