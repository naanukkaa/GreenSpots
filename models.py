from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

favorites_table = db.Table(
    'favorites',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('place_id', db.Integer, db.ForeignKey('place.id'), primary_key=True)
)


planned_routes_table = db.Table('planned_routes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('place_id', db.Integer, db.ForeignKey('place.id'), primary_key=True)
)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    # Fixed favorites relationship
    favorites = db.relationship(
        'Place',
        secondary=favorites_table,
        lazy='select',  # Changed from default
        backref=db.backref('favorited_by', lazy='select')
    )

    role = db.Column(db.String(50), default="user")
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def calculate_avg_rating(self):
        if not self.favorites:
            return 0
        # Calculate based on the ratings of favorited places
        total_ratings = []
        for place in self.favorites:
            if place.ratings:
                avg = sum(r.stars for r in place.ratings) / len(place.ratings)
                total_ratings.append(avg)
        return round(sum(total_ratings) / len(total_ratings), 1) if total_ratings else 0

class Route(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    date = db.Column(db.Date, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Place(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    region = db.Column(db.String(50))
    image = db.Column(db.String(200))
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    rating = db.Column(db.Float)

    # Remove or make nullable if places aren't owned by users
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    ratings = db.relationship('Rating', backref='place', lazy=True)

    def __repr__(self):
        return f"<Place {self.name}>"

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    place_id = db.Column(db.Integer, db.ForeignKey('place.id'))
    stars = db.Column(db.Float, nullable=False)  # 0–5 scale
    comment = db.Column(db.Text)
    image = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='ratings')

class Spot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    region = db.Column(db.String(50), nullable=False)
    rating = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(150), nullable=False)
    badges = db.Column(db.String(150))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    icon = db.Column(db.String(50))
    count = db.Column(db.Integer)


class PlannedRoute(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    place_id = db.Column(db.Integer, db.ForeignKey('place.id'))
    date = db.Column(db.Date, nullable=False)

    user = db.relationship('User', backref='routes')
    place = db.relationship('Place', backref='planned_routes')
