from flask import Flask, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import LoginManager, login_required, current_user
from models import db, User, Place, Spot, Category, Rating, PlannedRoute, datetime
from forms import PlaceForm
from auth import auth_bp
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from app import db
from sqlalchemy.sql.expression import func
from types import SimpleNamespace
from flask_wtf import CSRFProtect
import os
import random
import mimetypes

# ---------------- INIT APP ----------------
mimetypes.add_type('video/mp4', '.mp4')
app = Flask(__name__, template_folder='templates')
app.config["SECRET_KEY"] = "super-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "postgresql://database_zwh7_user:KGNKbpdqqLwAuwu8irdfzeE1EcFaws18@dpg-d5jpsv7fte5s738r7tpg-a/database_zwh7",
    "sqlite:///database.db"  # fallback for local dev
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['WTF_CSRF_ENABLED'] = True

# ---------------- BLUEPRINTS ----------------
app.register_blueprint(auth_bp)

# ---------------- DATABASE ----------------
db.init_app(app)
migrate = Migrate(app, db)

# ---------------- CSRF ----------------
csrf = CSRFProtect(app)

# ---------------- LOGIN MANAGER ----------------
login_manager = LoginManager()
login_manager.login_view = "auth_bp.login"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ---------------- PUBLIC ROUTES ----------------
@app.route("/")
def index():
    spots = Place.query.all()

    users_count = User.query.count()
    spots_count = Place.query.count()
    categories_count = 8

    for spot in spots:
        spot.avg_rating = round(sum(r.stars for r in spot.ratings)/len(spot.ratings), 1) if spot.ratings else 0

    top_spots = [s for s in spots if s.avg_rating >= 4]
    random.shuffle(top_spots)
    top_spots = top_spots[:10]

    if not top_spots:
        random.shuffle(spots)
        top_spots = spots[:10]

    categories = [
        SimpleNamespace(name="მთები", icon="mountains.svg", count=18),
        SimpleNamespace(name="ჩანჩქერები", icon="waterfall.svg", count=12),
        SimpleNamespace(name="ისტორიული", icon="historic.svg", count=15),
        SimpleNamespace(name="ტყეები", icon="forest.svg", count=10),
        SimpleNamespace(name="ხედები", icon="view.svg", count=22),
        SimpleNamespace(name="ლაშქრობა", icon="camp.svg", count=8),
        SimpleNamespace(name="ტბები", icon="lakes.svg", count=6),
        SimpleNamespace(name="მზის ამოსვლა", icon="sunset.svg", count=9),
    ]

    stats = SimpleNamespace(
        spots=len(top_spots),
        regions=12,
        visitors=1200
    )

    return render_template(
        "index.html",
        spots=top_spots,
        categories=categories,
        stats=stats,
        users_count=users_count,
        spots_count=spots_count,
        categories_count=categories_count
    )


# ---------------- LOGGED-IN ROUTES ----------------
@app.route("/home")
@login_required
def home():
    places = Place.query.all()

    suggested_places = random.sample(places, min(10, len(places)))
    for place in suggested_places:
        place.avg_rating = round(sum(r.stars for r in place.ratings) / len(place.ratings), 1) if place.ratings else 0

    user_favorites = current_user.favorites
    max_favorites = 6
    favorites_to_show = (
        random.sample(user_favorites, max_favorites)
        if len(user_favorites) > max_favorites else user_favorites
    )
    for fav in favorites_to_show:
        fav.avg_rating = round(sum(r.stars for r in fav.ratings) / len(fav.ratings), 1) if fav.ratings else 0

    user_favorite_ids = [p.id for p in current_user.favorites]
    planned_count = PlannedRoute.query.filter_by(user_id=current_user.id).count()

    return render_template(
        "home.html",
        places=places,
        suggested_places=suggested_places,
        favorites_to_show=favorites_to_show,
        user_favorite_ids=user_favorite_ids,
        planned_count=planned_count
    )

@app.route("/profile")
@login_required
def profile():
    my_places = Place.query.filter_by(user_id=current_user.id).all()
    try:
        favorites = current_user.favorites or []
    except Exception:
        favorites = []

    try:
        avg_rating = current_user.calculate_avg_rating()
    except Exception:
        avg_rating = 0

    planned_routes = PlannedRoute.query.filter(PlannedRoute.user_id == current_user.id).all()

    return render_template(
        "profile.html",
        favorites=favorites,
        planned_routes=planned_routes,
        my_places=my_places,
        avg_rating=avg_rating
    )

@app.route("/delete_route/<int:route_id>", methods=["POST"])
@login_required
def delete_route(route_id):
    route = PlannedRoute.query.get_or_404(route_id)
    if route.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    db.session.delete(route)
    db.session.commit()
    flash("მარშრუტი წაიშალა", "success")
    return redirect(url_for("profile"))


@app.route("/delete_place/<int:place_id>", methods=["POST"])
@login_required
def delete_place(place_id):
    if not current_user.is_admin:
        abort(403)

    place = Place.query.get_or_404(place_id)
    db.session.delete(place)
    db.session.commit()
    flash("Place deleted", "success")
    return redirect(url_for("categories"))


@app.route("/map")
def map_page():
    places = Place.query.filter(
        Place.latitude.isnot(None),
        Place.longitude.isnot(None)
    ).all()
    return render_template("map.html", places=places)


@app.route("/categories")
@login_required
def categories():
    # Get current page from URL (default is 1)
    page = request.args.get('page', 1, type=int)
    per_page = 20  # <--- HERE IS YOUR LIMIT

    search_query = request.args.get("q", "").strip()
    selected_category = request.args.get("category", "").strip()
    min_rating = request.args.get("rating", "").strip()
    selected_region = request.args.get("region", "").strip()
    favorites_only = request.args.get("favorites_only", "").strip()

    # Start the query
    query = Place.query

    # Apply filters in the database
    if selected_category:
        query = query.filter(Place.category == selected_category)
    if selected_region:
        query = query.filter(Place.region == selected_region)
    if search_query:
        query = query.filter(Place.name.ilike(f"%{search_query}%"))
    if favorites_only == "on":
        query = query.filter(Place.id.in_([p.id for p in current_user.favorites]))

    # Ratings filter is tricky because it's a calculated field.
    # For now, we fetch all filtered, calculate avg, then paginate.
    all_filtered = query.all()

    final_list = []
    for place in all_filtered:
        place.avg_rating = round(sum(r.stars for r in place.ratings) / len(place.ratings), 1) if place.ratings else 0
        if min_rating and place.avg_rating < float(min_rating):
            continue
        final_list.append(place)

    # Manual Pagination for the list
    total = len(final_list)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_places = final_list[start:end]

    # Calculate total pages
    total_pages = (total + per_page - 1) // per_page

    # Helpers for the filter dropdowns
    categories_list = [c[0] for c in db.session.query(Place.category).distinct()]
    region_map = {"Tbilisi": "თბილისი", "Adjara": "აჭარა", "Abkhazia": "აფხაზეთი", "Samegrelo": "სამეგრელო",
                  "Guria": "გურია", "Imereti": "იმერეთი", "Kakheti": "კახეთი", "Racha-Lechkhumi": "რაჭა-ლეჩხუმი",
                  "Mtskheta-Mtianeti": "მცხეთა-მთიანეთი", "Samtskhe-Javakheti": "სამცხე-ჯავახეთი", "Svaneti": "სვანეთი",
                  "Shida Kartli": "შიდა ქართლი", "Kvemo Kartli": "ქვემო ქართლი"}
    regions_list = [(code, name) for code, name in region_map.items()]

    return render_template(
        "categories.html",
        places=paginated_places,
        page=page,
        total_pages=total_pages,
        categories_list=categories_list,
        regions_list=regions_list,
        selected_category=selected_category,
        min_rating=min_rating,
        selected_region=selected_region,
        favorites_only=favorites_only,
        search_query=search_query
    )


@app.route("/add-place", methods=["GET", "POST"])
@login_required
def add_place():
    form = PlaceForm()
    if form.validate_on_submit():
        place_name = form.name.data.strip()

        existing_place = Place.query.filter(Place.name.ilike(place_name)).first()

        if existing_place:
            flash(f"ადგილი სახელით '{place_name}' უკვე არსებობს ბაზაში!", "warning")
            return render_template("add-place.html", form=form)

        filename = None
        if form.image.data:
            filename = secure_filename(form.image.data.filename)
            form.image.data.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # 3. Handle Coordinates
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")

        if not latitude or not longitude:
            flash("გთხოვ აირჩიე ადგილი რუკაზე", "danger")
            return render_template("add-place.html", form=form)

        # 4. Save the New Place
        try:
            place = Place(
                name=place_name,  # Use the cleaned name
                description=form.description.data,
                category=form.category.data,
                region=form.region.data,
                image=filename,
                latitude=float(latitude),
                longitude=float(longitude),
                user_id=current_user.id
            )

            db.session.add(place)
            db.session.commit()
            flash("ადგილი წარმატებით დაემატა!", "success")
            return redirect(url_for("categories"))

        except Exception as e:
            db.session.rollback()
            flash("მოხდა შეცდომა შენახვისას.", "danger")
            print(f"Error: {e}")

    return render_template("add-place.html", form=form)

@app.route("/place/<int:place_id>", methods=["GET", "POST"])
@login_required
def place_detail(place_id):
    place = Place.query.get_or_404(place_id)

    if request.method == "POST":
        action = request.form.get("action")
        if action == "favorite":
            if place in current_user.favorites:
                current_user.favorites.remove(place)
            else:
                current_user.favorites.append(place)

        elif action == "route":
            existing_route = PlannedRoute.query.filter_by(user_id=current_user.id, place_id=place.id).first()
            if not existing_route:
                planned_route = PlannedRoute(user_id=current_user.id, place_id=place.id, date=datetime.utcnow())
                db.session.add(planned_route)

        elif action == "rating":
            stars = float(request.form.get("stars"))
            comment = request.form.get("comment")
            image_file = request.files.get("image")
            filename = None
            if image_file and image_file.filename != "":
                filename = secure_filename(image_file.filename)
                image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_rating = Rating(user_id=current_user.id, place_id=place.id, stars=stars, comment=comment, image=filename)
            db.session.add(new_rating)

        db.session.commit()
        return redirect(url_for("place_detail", place_id=place.id))

    avg_rating = round(sum(r.stars for r in place.ratings)/len(place.ratings), 1) if place.ratings else 0
    return render_template("place_detail.html", place=place, ratings=place.ratings, avg_rating=avg_rating)


@app.route("/category/<string:category_name>")
@login_required
def category_places(category_name):
    suggested_places = Place.query.filter_by(category=category_name).all()
    user_favorite_ids = [p.id for p in current_user.favorites]
    return render_template(
        "dashboard.html",
        suggested_places=suggested_places,
        user_favorite_ids=user_favorite_ids
    )


@app.route("/toggle_favorite/<int:place_id>", methods=["POST"])
@login_required
def toggle_favorite(place_id):
    # Modern SQLAlchemy 2.0 way
    place = db.session.get(Place, place_id)
    if not place:
        return jsonify({"status": "error", "message": "Place not found"}), 404

    try:
        if place in current_user.favorites:
            current_user.favorites.remove(place)
            status = "removed"
        else:
            current_user.favorites.append(place)
            status = "added"
        db.session.commit()
        return jsonify({"status": status})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/booking', methods=['GET', 'POST'])
@login_required
def booking():
    spots = Place.query.all()

    if request.method == 'POST':
        spot_name = request.form['spot']
        date_selected = request.form['date']
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']

        spot = Place.query.filter_by(name=spot_name).first()
        if not spot:
            flash("აირჩიე ვალიდური ადგილი!", "danger")
            return redirect(url_for('booking'))

        new_route = PlannedRoute(
            user_id=current_user.id,
            place_id=spot.id,
            date=datetime.strptime(date_selected, "%Y-%m-%d")
        )
        db.session.add(new_route)
        db.session.commit()

        flash("თქვენი შეკვეთა წარმატებით გაიგზავნა!", "success")
        return redirect(url_for('profile'))

    return render_template("booking.html", spots=spots)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        subject = request.form["subject"]
        message = request.form["message"]

        flash("შეტყობინება გაგზავნილია!", "success")
        return redirect(url_for("contact"))

    return render_template("contact.html")


@app.route("/delete_rating/<int:rating_id>", methods=["POST"])
@login_required
def delete_rating(rating_id):
    rating = Rating.query.get_or_404(rating_id)

    # Check if the user is the owner or an admin
    if rating.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    db.session.delete(rating)
    db.session.commit()
    return jsonify({"status": "success"})

# ---------------- RUN ----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
