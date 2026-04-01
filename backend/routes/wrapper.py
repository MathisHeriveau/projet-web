from flask import session, g
from backend.models import User
from backend.enums.http_status import HTTPStatus

def login_required(f):
    """
        Login required wrapper
    """
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return {"error": "you are not logged in"}, HTTPStatus.UNAUTHORIZED.value

        user = User.get_by_username(session["user"])
        if user is None:
            session.clear()
            return {"error": "invalid user"}, HTTPStatus.UNAUTHORIZED.value

        g.user = user
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper