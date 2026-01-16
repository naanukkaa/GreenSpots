from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from forms import RegistrationForm, LoginForm

auth_bp = Blueprint('auth_bp', __name__, template_folder='templates')

# ------------------- Registration -------------------
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    form = RegistrationForm()

    if form.validate_on_submit():
        # Check Username separately
        user_by_username = User.query.filter_by(username=form.username.data).first()
        if user_by_username:
            flash('ეს მომხმარებლის სახელი უკვე დაკავებულია.', 'danger')
            return redirect(url_for('auth_bp.register'))

        # Check Email separately
        user_by_email = User.query.filter_by(email=form.email.data).first()
        if user_by_email:
            flash('ეს ელ-ფოსტა უკვე გამოყენებულია.', 'danger')
            return redirect(url_for('auth_bp.register'))

        # If both are clear, create user
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash('რეგისტრაცია წარმატებით დასრულდა! ახლა შეგიძლიათ სისტემაში შესვლა.', 'success')
        return redirect(url_for('auth_bp.login'))

    # Flash validation errors (like password too short, etc.)
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{form[field].label.text}: {error}", 'danger')

    return render_template('register.html', form=form)

# ------------------- Login -------------------
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('home'))
        flash('Invalid email or password.', 'danger')

    return render_template('auth.html', form=form)


# ------------------- Logout -------------------
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('auth_bp.login'))


# ------------------- Delete Account -------------------
@auth_bp.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    user = current_user

    # logout FIRST (important)
    logout_user()

    # delete user
    db.session.delete(user)
    db.session.commit()

    flash('Your account has been permanently deleted.', 'info')
    return redirect(url_for('index'))
