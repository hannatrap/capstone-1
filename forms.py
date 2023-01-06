from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField
from wtforms.validators import DataRequired, Email, Length, InputRequired


class UserAddForm(FlaskForm):
    """Form for adding users."""

    username = StringField('Username', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[Length(min=6)])
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    image_url = StringField('(Optional) Image URL')


class LoginForm(FlaskForm):
    """Login form."""

    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[Length(min=6)])


class EditUserForm(FlaskForm):
    """Edit user form."""

    username = StringField('Username', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[Length(min=6)])

class NewPlaylistForm(FlaskForm):
    title = StringField("Playlist Title", validators=[InputRequired(), Length(max=40)])
    text = StringField("Playlist Text", validators=[InputRequired(), Length(max=120)])


class SearchForm(FlaskForm):
    s = StringField("Movie Title", validators=[InputRequired(), Length(max=40)])

class LikeAddForm(FlaskForm):
    """form for adding a like"""