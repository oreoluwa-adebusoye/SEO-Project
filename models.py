from extensions import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    age = db.Column(db.Integer)                         # optional
    school = db.Column(db.String(120))
    interests = db.Column(db.Text)                      # comma-separated or free text
    avatar_url = db.Column(db.String(255))              # profile pic

     # Relationship to Event model
    events = db.relationship("Event", backref="creator", lazy=True)

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)
    
    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"
    

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)
    # store HTML datetime-local string (e.g., 2025-08-08T19:30); it sorts fine lexicographically
    start = db.Column(db.String(32), nullable=False)
    location_text = db.Column(db.String(255))
    image_url = db.Column(db.String(255))
    is_private = db.Column(db.Boolean, default=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"Event('{self.title}', '{self.start}')"

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    read = db.Column(db.Boolean, default=False, index=True)

# who is going to which event (either user-created OR Ticketmaster)
class EventAttendee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    # internal (user-created) events
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=True, index=True)

    # external Ticketmaster events (store once locally so we can reference)
    external_event_id = db.Column(db.Integer, db.ForeignKey("external_event.id"), nullable=True, index=True)

    __table_args__ = (
        db.CheckConstraint("(event_id IS NOT NULL) OR (external_event_id IS NOT NULL)", name="attend_has_one"),
        db.UniqueConstraint("user_id", "event_id", name="uniq_user_event"),
        db.UniqueConstraint("user_id", "external_event_id", name="uniq_user_external_event"),
    )

class ExternalEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tm_id = db.Column(db.String(64), unique=True, nullable=False)  # Ticketmaster ID
    name = db.Column(db.String(200))
    start = db.Column(db.String(32))
    venue = db.Column(db.String(200))
    city = db.Column(db.String(120))
    image_url = db.Column(db.String(255))

    