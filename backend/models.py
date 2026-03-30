from .extensions import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    recommendation_text = db.Column(db.String(255), nullable=False)
    liked_films = db.Column(db.String(255), nullable=True)
    unliked_films = db.Column(db.String(255), nullable=True)
    neutral_films = db.Column(db.String(255), nullable=True)
    viewed_films = db.Column(db.String(255), nullable=True)

    @classmethod
    def get_by_username(cls, username):
        return cls.query.filter_by(username=username).first()
    
