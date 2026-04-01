from backend.extensions import db
from backend.enums.opinion_type import OpinionType

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    recommendation_text = db.Column(db.String(255), nullable=True)
    first_connection = db.Column(db.Boolean, default=True)

    @classmethod
    def get_by_username(cls, username):
        return cls.query.filter_by(username=username).first()

class Recommendation(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    serie_id = db.Column(db.Integer, db.ForeignKey('serie.id'), nullable=False)

    @classmethod
    def get_by_user_id(cls, user_id):
        return cls.query.filter_by(user_id=user_id).all()

class Opinion(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    serie_id = db.Column(db.Integer, db.ForeignKey('serie.id'), nullable=False)
    opinion = db.Column(db.Enum(OpinionType), nullable=False)
    viewed = db.Column(db.Boolean, nullable=False)

    @classmethod
    def get_by_user_id(cls, user_id):
        return cls.query.filter_by(user_id=user_id).all()
    
    @classmethod
    def get_viewed_by_user_id(cls, user_id):
        return cls.query.filter_by(user_id=user_id, viewed=True).all()
    
    @classmethod
    def get_opinion_by_user_id_and_serie_id(cls, user_id, serie_id):
        return cls.query.filter_by(user_id=user_id, serie_id=serie_id).first()
    
class Serie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    genres = db.Column(db.String(255), nullable=False)
    summary = db.Column(db.String(255), nullable=False)

    @classmethod
    def get_by_id(cls, id):
        return cls.query.filter_by(id=id).first()
