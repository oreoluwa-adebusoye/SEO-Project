from flask import Flask, render_template, url_for, flash, redirect, request
from forms import RegistrationForm, LoginForm
import os
from datetime import datetime
from event_search import search_ticketmaster
from flask_login import login_user, login_required, logout_user, current_user
from extensions import db, migrate, bcrypt, login_manager
from sqlalchemy import or_, desc

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'

db.init_app(app)
migrate.init_app(app, db)
bcrypt.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Import models after db initialization
from models import User, Event, Message, ExternalEvent, EventAttendee

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



# ==========================
# Landing Page
# ==========================
@app.route("/")
def landing():
    return render_template("landing.html")

# ==========================
# Home Page
# ==========================
@app.route("/home")
@login_required
def home():
    # --- Profile summary
    me = current_user

    # --- Suggested people (priority: share an RSVP; fallback: shared interests/school)
    from models import User, Message, EventAttendee, Event, ExternalEvent

    # set of user_ids you already messaged (to avoid suggesting them)
    talked_to_ids = {m.recipient_id for m in Message.query.filter_by(sender_id=me.id)} | \
                    {m.sender_id for m in Message.query.filter_by(recipient_id=me.id)} | {me.id}

    # 1) people from events I attend
    my_internal_ids = db.session.query(EventAttendee.event_id)\
        .filter_by(user_id=me.id).filter(EventAttendee.event_id.isnot(None)).subquery()
    my_external_ids = db.session.query(EventAttendee.external_event_id)\
        .filter_by(user_id=me.id).filter(EventAttendee.external_event_id.isnot(None)).subquery()

    event_people = db.session.query(User).join(EventAttendee, User.id == EventAttendee.user_id)\
        .filter(User.id.notin_(talked_to_ids))\
        .filter(
            (EventAttendee.event_id.in_(my_internal_ids)) |
            (EventAttendee.external_event_id.in_(my_external_ids))
        ).distinct().limit(6).all()

    # 2) fallback: interests / school overlap (simple LIKEs for MVP)
    suggestions = event_people
    if len(suggestions) < 6:
        remain = 6 - len(suggestions)
        q = User.query.filter(User.id.notin_(talked_to_ids))
        if me.interests:
            q = q.filter(User.interests.ilike(f"%{me.interests.split(',')[0].strip()}%"))
        elif me.school:
            q = q.filter(User.school == me.school)
        more = q.limit(remain).all()
        # avoid duplicates
        seen = {u.id for u in suggestions}
        suggestions += [u for u in more if u.id not in seen]

    # --- Upcoming RSVPs (internal + external)
    upcoming_internal = db.session.query(Event)\
        .join(EventAttendee, Event.id == EventAttendee.event_id)\
        .filter(EventAttendee.user_id == me.id)\
        .order_by(Event.start.asc()).limit(4).all()

    upcoming_external = db.session.query(ExternalEvent)\
        .join(EventAttendee, ExternalEvent.id == EventAttendee.external_event_id)\
        .filter(EventAttendee.user_id == me.id)\
        .limit(4).all()

    # --- Unread messages count
    unread = Message.query.filter_by(recipient_id=me.id, read=False).count()

    return render_template(
        "home.html",
        me=me,
        unread=unread,
        suggestions=suggestions,
        upcoming_internal=upcoming_internal,
        upcoming_external=upcoming_external,
    )


# ==========================
# Sign Up Page
# ==========================
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)  # <-- hashes & stores in password_hash
        db.session.add(user)
        db.session.commit()
        flash("Signup successful! You can now log in.", "success")
        return redirect(url_for('login'))

    return render_template('signup.html', form=form)

# ==========================
# LogIn Page
# ==========================
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():  # only runs on POST with valid form
        account = User.query.filter_by(email=form.email.data).first()
        if account and account.check_password(form.password.data):
            login_user(account)
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        flash("Invalid email or password. Please try again.", "danger")
    return render_template('login.html', form=form)

# ==========================
# Logout
# ==========================
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for('landing'))


# ==========================
# Event
# ==========================
@app.route("/events")
def events():
    q = request.args.get("q") or "art"
    city = request.args.get("city") or "New York"

    # 1) Ticketmaster
    public_events = []
    try:
        public_events = search_ticketmaster(keyword=q, city=city, size=20)
    except Exception as ex:
        print("Ticketmaster error:", ex)
        flash("Couldn’t fetch Ticketmaster events. Check API key or params.", "warning")

    # 2)  user-created public events (non-private)
    user_events = Event.query.filter_by(is_private=False).order_by(Event.start.asc()).all()
    user_events_norm = [{
        "id": f"user-{e.id}",
        "name": e.title,
        "url": url_for('view_user_event', event_id=e.id),  # internal detail page
        "description": e.description,
        "start": e.start,
        "venue": e.location_text,
        "city": None,
        "image_url": e.image_url,
        "creator_username": e.creator.username,
    } for e in user_events]

    # 3) Combine (created events first)
    events_combined = user_events_norm + public_events

    return render_template(
        "events.html",
        events=events_combined,
        pagination={"page": 1, "has_more_items": False},
    )


    
try:
    from dateutil import parser as date_parser
except Exception:
    date_parser = None

@app.template_filter("datetimeformat_safe")
def datetimeformat_safe(value, fmt="%b %d, %Y %I:%M %p"):
    """
    Robustly format ISO8601 strings (e.g., '2025-08-08T19:30:00Z' or with offsets/millis).
    Falls back to the original value if parsing fails.
    """
    if not value:
        return ""
    try:
        if date_parser:
            dt = date_parser.isoparse(value)
        else:
            # Fallback: handle trailing Z and basic ISO without dateutil
            v = value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(v)
    except Exception:
        return value  # don't crash the page
    try:
        # convert to local timezone before formatting (optional but nice)
        dt = dt.astimezone()
    except Exception:
        pass
    return dt.strftime(fmt)


def _can_view_event(e):
    if not e.is_private:
        return True
    # MVP: private events visible only to creator for now
    return current_user.is_authenticated and e.created_by == current_user.id

# ==========================
# Create event
# ==========================
@app.route("/events/new", methods=["GET", "POST"])
@login_required
def create_event():
    if request.method == "POST":
        title = request.form.get("title")
        start = request.form.get("start")               # HTML datetime-local
        location_text = request.form.get("location_text")
        description = request.form.get("description")
        image_url = request.form.get("image_url")
        is_private = bool(request.form.get("is_private"))

        if not (title and start and location_text):
            flash("Title, Start, and Location are required.", "danger")
            return redirect(url_for("create_event"))

        e = Event(
            title=title,
            start=start,
            location_text=location_text,
            description=description,
            image_url=image_url,
            is_private=is_private,
            created_by=current_user.id,   # <-- tie to the logged-in user
        )
        db.session.add(e); db.session.commit()
        flash("Event created!", "success")
        return redirect(url_for("view_user_event", event_id=e.id))

    # render the create form (event.html in create mode)
    return render_template("event.html", create_mode=True)

@app.route("/my-event/<int:event_id>")
@login_required
def view_user_event(event_id):
    e = Event.query.get_or_404(event_id)
    if not _can_view_event(e):
        flash("This event is private.", "warning")
        return redirect(url_for("events"))
    return render_template("event.html", event=e, create_mode=False)

# ==========================
# Messaging
# ==========================
def _get_conversations(user_id: int):
    msgs = Message.query.filter(
        or_(Message.sender_id == user_id, Message.recipient_id == user_id)
    ).order_by(desc(Message.created_at)).all()
    seen = set(); convos = []
    for m in msgs:
        other_id = m.recipient_id if m.sender_id == user_id else m.sender_id
        pair = tuple(sorted((user_id, other_id)))
        if pair in seen: continue
        seen.add(pair)
        other = User.query.get(other_id)
        if other: convos.append((other, m))
    return convos

@app.route("/messages", methods=["GET", "POST"])
@login_required
def messages_index():
    if request.method == "POST":
        target = (request.form.get("username") or "").strip()
        if target:
            return redirect(url_for("messages_thread", username=target))
    conversations = _get_conversations(current_user.id)
    return render_template("messages.html", conversations=conversations, current_chat=None, messages=[])

@app.route("/messages/<username>", methods=["GET", "POST"])
@login_required
def messages_thread(username):
    other = User.query.filter_by(username=username).first_or_404()
    if request.method == "POST":
        content = (request.form.get("content") or "").strip()
        if content:
            m = Message(sender_id=current_user.id, recipient_id=other.id, content=content)
            db.session.add(m); db.session.commit()
            flash("Message sent.", "success")
        return redirect(url_for("messages_thread", username=other.username))

    thread = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.recipient_id == other.id)) |
        ((Message.sender_id == other.id) & (Message.recipient_id == current_user.id))
    ).order_by(Message.created_at.asc()).all()

    for m in thread:
        if m.recipient_id == current_user.id and not m.read:
            m.read = True
    db.session.commit()
    conversations = _get_conversations(current_user.id)
    return render_template("messages.html", conversations=conversations, current_chat=other, messages=thread)


# ==========================
# User Profile
# ==========================
@app.route("/profile/<username>")
def profile_view(username):
    u = User.query.filter_by(username=username).first_or_404()
    can_edit = current_user.is_authenticated and current_user.id == u.id
    return render_template("profile.html", user=u, can_edit=can_edit)

@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def profile_edit():
    if request.method == "POST":
        # grab values from form
        current_user.avatar_url = request.form.get("avatar_url") or None
        current_user.school = request.form.get("school") or None
        current_user.interests = request.form.get("interests") or None

        # age: safely cast to int if provided
        age_raw = (request.form.get("age") or "").strip()
        try:
            current_user.age = int(age_raw) if age_raw else None
        except ValueError:
            flash("Age must be a number.", "warning")

        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("profile_view", username=current_user.username))

    return render_template("profile_edit.html", user=current_user)


# ==========================
# People page (event-based)
# ==========================

@app.route("/rsvp/internal/<int:event_id>", methods=["POST"])
@login_required
def rsvp_internal(event_id):
    e = Event.query.get_or_404(event_id)
    exists = EventAttendee.query.filter_by(user_id=current_user.id, event_id=e.id).first()
    if not exists:
        db.session.add(EventAttendee(user_id=current_user.id, event_id=e.id))
        db.session.commit()
    flash("RSVP saved.", "success")
    return redirect(url_for("view_user_event", event_id=e.id))

@app.route("/unrsvp/internal/<int:event_id>", methods=["POST"])
@login_required
def unrsvp_internal(event_id):
    row = EventAttendee.query.filter_by(user_id=current_user.id, event_id=event_id).first()
    if row:
        db.session.delete(row); db.session.commit()
    flash("RSVP removed.", "info")
    return redirect(url_for("view_user_event", event_id=event_id))

@app.route("/rsvp/tm", methods=["POST"])
@login_required
def rsvp_tm():
    tm_id = request.form.get("tm_id")
    if not tm_id:
        flash("Missing event id.", "danger"); return redirect(url_for("events"))

    # upsert ExternalEvent
    ev = ExternalEvent.query.filter_by(tm_id=tm_id).first()
    if not ev:
        ev = ExternalEvent(
            tm_id=tm_id,
            name=request.form.get("name"),
            start=request.form.get("start"),
            venue=request.form.get("venue"),
            city=request.form.get("city"),
            image_url=request.form.get("image_url"),
        )
        db.session.add(ev); db.session.commit()

    exists = EventAttendee.query.filter_by(user_id=current_user.id, external_event_id=ev.id).first()
    if not exists:
        db.session.add(EventAttendee(user_id=current_user.id, external_event_id=ev.id))
        db.session.commit()
    flash("RSVP saved.", "success")
    return redirect(url_for("events"))

@app.route("/people")
@login_required
def people():
    # events I attend (internal + external)
    my_internal_ids = db.session.query(EventAttendee.event_id)\
        .filter_by(user_id=current_user.id)\
        .filter(EventAttendee.event_id.isnot(None)).subquery()

    my_external_ids = db.session.query(EventAttendee.external_event_id)\
        .filter_by(user_id=current_user.id)\
        .filter(EventAttendee.external_event_id.isnot(None)).subquery()

    # users who attend any of those events (excluding me)
    others_internal = db.session.query(User).join(EventAttendee, User.id == EventAttendee.user_id)\
        .filter(EventAttendee.event_id.in_(my_internal_ids))\
        .filter(User.id != current_user.id)

    others_external = db.session.query(User).join(EventAttendee, User.id == EventAttendee.user_id)\
        .filter(EventAttendee.external_event_id.in_(my_external_ids))\
        .filter(User.id != current_user.id)

    people = others_internal.union(others_external).distinct().all()
    return render_template("people.html", people=people)


if __name__ == "__main__":
    app.run(debug=True)
