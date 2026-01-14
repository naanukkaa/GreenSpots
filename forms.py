from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, PasswordField, SubmitField, TextAreaField, FloatField, SelectField)
from wtforms.validators import DataRequired, Email, Length
from wtforms import StringField, PasswordField, SubmitField, EmailField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
ALLOWED_EMAIL_DOMAINS = {
    "gmail.com",
    "outlook.com",
    "hotmail.com",
    "yahoo.com",
    "icloud.com",
    "proton.me",
    "protonmail.com"
}


def validate_email_domain(form, field):
    email = field.data.lower()
    domain = email.split("@")[-1]
    if domain not in ALLOWED_EMAIL_DOMAINS:
        raise ValidationError(
            "Please use a real email provider (Gmail, Outlook, Yahoo, iCloud, Proton)."
        )

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email(message="Invalid email format"), validate_email_domain])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(message="invalid email address")])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

CATEGORY_CHOICES = [
    ('mountains', 'მთები'),
    ('waterfalls', 'ჩანჩქერები/კანიონები'),
    ('historic', 'ისტორიული'),
    ('forests', 'ტყეები'),
    ('views', 'ხედები'),
    ('hiking', 'ლაშქრობა'),
    ('lakes', 'ტბები'),
    ('sunrise', 'მზის ამოსვლა'),
]

REGION_CHOICES = [
    ('Tbilisi', 'თბილისი'),
    ('Adjara', 'აჭარა'),
    ('Abkhazia', 'აფხაზეთი'),
    ('Samegrelo', 'სამეგრელო'),
    ('Guria', 'გურია'),
    ('Imereti', 'იმერეთი'),
    ('Kakheti', 'კახეთი'),
    ('Racha-Lechkhumi', 'რაჭა-ლეჩხუმი'),
    ('Mtskheta-Mtianeti', 'მცხეთა-მთიანეთი'),
    ('Samtskhe-Javakheti', 'სამცხე-ჯავახეთი'),
    ('Svaneti', 'სვანეთი'),
    ('Shida Kartli', 'შიდა ქართლი'),
    ('Kvemo Kartli', 'ქვემო ქართლი'),

]

class PlaceForm(FlaskForm):
    name = StringField("ადგილის სახელი", validators=[DataRequired(), Length(max=150)])
    description = TextAreaField("აღწერა", validators=[DataRequired()])
    category = SelectField("კატეგორია", choices=CATEGORY_CHOICES, validators=[DataRequired()])
    region = SelectField("რეგიონი", choices=REGION_CHOICES)
    image = FileField("ატვირთე ფოტო", validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'მხოლოდ ფოტო!')])
    submit = SubmitField("დაამატე ადგილი")

