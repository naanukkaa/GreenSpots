from flask import Flask, render_template, redirect, url_for, flash, request, abort, jsonify, g
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
from deep_translator import GoogleTranslator

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

@app.before_request
def load_language():
    g.lang = request.cookies.get('lang', 'ge')

#-------------------TRANSLATOR-------------------
def translate_text(text):
    if text and hasattr(g, 'lang') and g.lang == 'en':
        try:
            return GoogleTranslator(source='auto', target='en').translate(text)
        except Exception as e:
            print(f"Translation failed: {e}")
            return text
    return text
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

    # 1. Get counts from DB grouped by category string
    category_counts = db.session.query(
        Place.category, func.count(Place.id)
    ).group_by(Place.category).all()

    # 2. Create a translation mapping to group them into English "buckets"
    mapping = {
        "mountains": "Mountains", "Mountains": "Mountains", "მთები": "Mountains",
        "waterfalls": "Waterfalls", "Waterfalls": "Waterfalls", "ჩანჩქერები": "Waterfalls",
        "historic": "Historical", "Historical": "Historical", "ისტორიული": "Historical",
        "forests": "Forests", "Forests": "Forests", "ტყეები": "Forests",
        "views": "Viewpoints", "Viewpoints": "Viewpoints", "ხედები": "Viewpoints",
        "hiking": "Hiking", "Hiking": "Hiking", "ლაშქრობა": "Hiking",
        "lakes": "Lakes", "Lakes": "Lakes", "ტბები": "Lakes",
        "sunrise": "Sunrise", "Sunrise": "Sunrise", "მზის ამოსვლა": "Sunrise"
    }

    # 3. Sum up the counts into a standardized dictionary
    total_counts = {}
    for cat_name, count in category_counts:
        if cat_name:
            # Convert the DB value to lowercase before looking it up
            standard_key = mapping.get(cat_name.lower(), cat_name)
            total_counts[standard_key] = total_counts.get(standard_key, 0) + count

    categories = [
        SimpleNamespace(name="მთები", en_name="Mountains", icon="mountains.svg", count=total_counts.get("Mountains", 0)),
        SimpleNamespace(name="ჩანჩქერები", en_name="Waterfalls", icon="waterfall.svg", count=total_counts.get("Waterfalls", 0)),
        SimpleNamespace(name="ისტორიული", en_name="Historical", icon="historic.svg", count=total_counts.get("Historical", 0)),
        SimpleNamespace(name="ტყეები", en_name="Forests", icon="forest.svg", count=total_counts.get("Forests", 0)),
        SimpleNamespace(name="ხედები", en_name="Viewpoints", icon="view.svg", count=total_counts.get("Viewpoints", 0)),
        SimpleNamespace(name="ლაშქრობა", en_name="Hiking", icon="camp.svg", count=total_counts.get("Hiking", 0)),
        SimpleNamespace(name="ტბები", en_name="Lakes", icon="lakes.svg", count=total_counts.get("Lakes", 0)),
        SimpleNamespace(name="მზის ამოსვლა", en_name="Sunrise", icon="sunset.svg", count=total_counts.get("Sunrise", 0)),
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

    if g.lang == 'en':
        for place in suggested_places:
            place.name = translate_text(place.name)
            place.description = translate_text(place.description)

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
    favorites = current_user.favorites or []
    planned_routes = PlannedRoute.query.filter(PlannedRoute.user_id == current_user.id).all()
    try:
        favorites = current_user.favorites or []
    except Exception:
        favorites = []

    try:
        avg_rating = current_user.calculate_avg_rating()
    except Exception:
        avg_rating = 0

    for p in my_places:
        p.name = translate_text(p.name)

    for f in favorites:
        f.name = translate_text(f.name)

    for route in planned_routes:
        if route.place:
            route.place.name = translate_text(route.place.name)

    return render_template(
        "profile.html",
        favorites=favorites,
        planned_routes=planned_routes,
        my_places=my_places,
        avg_rating=current_user.calculate_avg_rating() if hasattr(current_user, 'calculate_avg_rating') else 0
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
@login_required
def map_page():
    places = Place.query.filter(
        Place.latitude.isnot(None),
        Place.longitude.isnot(None)
    ).all()
    return render_template("map.html", places=places)


@app.route("/categories")
@login_required
def categories():
    # Detect language from cookie (default to 'ge')
    lang = request.cookies.get('lang', 'ge')

    page = request.args.get('page', 1, type=int)
    per_page = 20

    search_query = request.args.get("q", "").strip()
    selected_category = request.args.get("category", "").strip()
    min_rating = request.args.get("rating", "").strip()
    selected_region = request.args.get("region", "").strip()
    favorites_only = request.args.get("favorites_only", "").strip()


    query = Place.query

    if selected_category:
        query = query.filter(Place.category == selected_category)
    if selected_region:
        query = query.filter(Place.region == selected_region)
    if search_query:
        query = query.filter(Place.name.ilike(f"%{search_query}%"))
    if favorites_only == "on":
        query = query.filter(Place.id.in_([p.id for p in current_user.favorites]))

    all_filtered = query.all()
    final_list = []
    for place in all_filtered:
        place.avg_rating = round(sum(r.stars for r in place.ratings) / len(place.ratings), 1) if place.ratings else 0
        if min_rating and place.avg_rating < float(min_rating):
            continue
        final_list.append(place)

    total = len(final_list)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_places = final_list[start:end]
    total_pages = (total + per_page - 1) // per_page

    # DYNAMIC CATEGORIES:
    # If your DB stores keys like 'mountains', we map them for the display
    raw_categories = [c[0] for c in db.session.query(Place.category).distinct()]
    category_map_en = {'mountains': 'Mountains', 'waterfalls': 'Waterfalls', 'historic': 'Historic',
                       'forests': 'Forests', 'views': 'Views', 'hiking': 'Hiking', 'lakes': 'Lakes',
                       'sunrise': 'Sunrise'}
    category_map_ge = {'mountains': 'მთები', 'waterfalls': 'ჩანჩქერები', 'historic': 'ისტორიული', 'forests': 'ტყეები',
                       'views': 'ხედები', 'hiking': 'ლაშქრობა', 'lakes': 'ტბები', 'sunrise': 'მზის ამოსვლა'}

    current_cat_map = category_map_en if lang == 'en' else category_map_ge
    # Create list of tuples (database_value, display_name)
    categories_list = [(cat, current_cat_map.get(cat, cat)) for cat in raw_categories]

    # DYNAMIC REGIONS
    region_map_ge = {"Tbilisi": "თბილისი", "Adjara": "აჭარა", "Abkhazia": "აფხაზეთი", "Samegrelo": "სამეგრელო",
                     "Guria": "გურია", "Imereti": "იმერეთი", "Kakheti": "კახეთი", "Racha-Lechkhumi": "რაჭა-ლეჩხუმი",
                     "Mtskheta-Mtianeti": "მცხეთა-მთიანეთი", "Samtskhe-Javakheti": "სამცხე-ჯავახეთი",
                     "Svaneti": "სვანეთი", "Shida Kartli": "შიდა ქართლი", "Kvemo Kartli": "ქვემო ქართლი"}

    # If English, we use the key as the name (e.g., "Tbilisi"), else we use the Georgian value
    regions_list = [(code, code if lang == 'en' else name) for code, name in region_map_ge.items()]

    for place in paginated_places:
        place.name = translate_text(place.name)
        place.description = translate_text(place.description)

    return render_template(
        "categories.html",
        places=paginated_places,
        page=page,
        total_pages=total_pages,
        categories_list=categories_list,  # Now returns list of tuples
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
    # Detect language
    lang = request.cookies.get('lang', 'ge')
    form = PlaceForm()

    # 1. Update Form Labels & Choices based on language
    if lang == 'en':
        form.name.label.text = "Place Name"
        form.description.label.text = "Description"
        form.category.label.text = "Category"
        form.region.label.text = "Region"
        form.image.label.text = "Upload Photo"
        form.submit.label.text = "Add Place"

        # English Choices
        form.category.choices = [
            ('mountains', 'Mountains'), ('waterfalls', 'Waterfalls'),
            ('historic', 'Historic'), ('forests', 'Forests'),
            ('views', 'Views'), ('hiking', 'Hiking'),
            ('lakes', 'Lakes'), ('sunrise', 'Sunrise')
        ]
        form.region.choices = [
            ('Tbilisi', 'Tbilisi'), ('Adjara', 'Adjara'), ('Abkhazia', 'Abkhazia'),
            ('Samegrelo', 'Samegrelo'), ('Guria', 'Guria'), ('Imereti', 'Imereti'),
            ('Kakheti', 'Kakheti'), ('Racha-Lechkhumi', 'Racha-Lechkhumi'),
            ('Mtskheta-Mtianeti', 'Mtskheta-Mtianeti'), ('Samtskhe-Javakheti', 'Samtskhe-Javakheti'),
            ('Svaneti', 'Svaneti'), ('Shida Kartli', 'Shida Kartli'), ('Kvemo Kartli', 'Kvemo Kartli')
        ]
    else:
        # Default labels are already in Georgian in your form class,
        # but we re-declare them here for consistency
        form.name.label.text = "ადგილის სახელი"
        form.description.label.text = "აღწერა"
        form.category.label.text = "კატეგორია"
        form.region.label.text = "რეგიონი"
        form.image.label.text = "ატვირთე ფოტო"
        form.submit.label.text = "დაამატე ადგილი"

    if form.validate_on_submit():
        place_name = form.name.data.strip()
        existing_place = Place.query.filter(Place.name.ilike(place_name)).first()

        if existing_place:
            msg = f"Place '{place_name}' already exists!" if lang == 'en' else f"ადგილი სახელით '{place_name}' უკვე არსებობს ბაზაში!"
            flash(msg, "warning")
            return render_template("add-place.html", form=form)

        filename = None
        if form.image.data:
            filename = secure_filename(form.image.data.filename)
            form.image.data.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")

        if not latitude or not longitude:
            msg = "Please select a location on the map" if lang == 'en' else "გთხოვ აირჩიე ადგილი რუკაზე"
            flash(msg, "danger")
            return render_template("add-place.html", form=form)

        try:
            place = Place(
                name=place_name,
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

            msg = "Place added successfully!" if lang == 'en' else "ადგილი წარმატებით დაემატა!"
            flash(msg, "success")
            return redirect(url_for("categories"))

        except Exception as e:
            db.session.rollback()
            msg = "An error occurred while saving." if lang == 'en' else "მოხდა შეცდომა შენახვისას."
            flash(msg, "danger")
            print(f"Error: {e}")

    return render_template("add-place.html", form=form)

@app.route("/place/<int:place_id>", methods=["GET", "POST"])
@login_required
def place_detail(place_id):
    place = Place.query.get_or_404(place_id)

    place.name = translate_text(place.name)
    place.description = translate_text(place.description)

    # Translate the comments in the ratings
    for rating in place.ratings:
        if rating.comment:
            rating.comment = translate_text(rating.comment)

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
@csrf.exempt
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

    for spot in spots:
        spot.name = translate_text(spot.name)

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
@login_required
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
