from flask import session, g
from backend.models import User
from backend.enums.http_status import HTTPStatus

def login_required(f):
    """
        Login required wrapper
    """
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return {"error": "Vous devez etre connecte pour acceder a cette ressource."}, HTTPStatus.UNAUTHORIZED.value

        user = User.get_by_username(session["user"])
        if user is None:
            session.clear()
            return {"error": "La session utilisateur est invalide. Veuillez vous reconnecter."}, HTTPStatus.UNAUTHORIZED.value

        g.user = user
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper
