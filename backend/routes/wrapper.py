def login_required(f):
    """
        Login required wrapper
    """
    def wrapper(*args, **kwargs):
        pass
    wrapper.__name__ = f.__name__
    return wrapper