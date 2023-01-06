import os

from flask import Flask, render_template, request, flash, redirect, session, g, abort
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError
import requests
from forms import UserAddForm, LoginForm, EditUserForm, NewPlaylistForm, SearchForm, LikeAddForm
from models import db, connect_db, User, Playlist

CURR_USER_KEY = "curr_user"
# API_KEY = "43cfb6f4"
API_BASE_URL = "http://www.omdbapi.com/?apikey=43cfb6f4&"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgresql:///movie-passport'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
toolbar = DebugToolbarExtension(app)

app.debug=True

with app.app_context():
    connect_db(app)
    db.create_all()


##############################################################################
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """
    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]
    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""
        
    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)



@app.route('/logout')
def logout():
    """Handle logout of user."""
    do_logout()

    flash("You have successfully logged out of Warbler", 'success')

    return redirect('/login')


    # IMPLEMENT THIS


##############################################################################
# General user routes:

@app.route('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.route('/users/<int:user_id>')
def users_show(user_id):
    """Show user profile."""

    user = User.query.get_or_404(user_id)

    # snagging playlists in order from the database;
    # user.playlist won't be in order by default
    playlist = (Playlist
                .query
                .filter(Playlist.user_id == user_id)
                # .order_by(Playlist.timestamp_created.desc())
                .limit(5)
                .all())
    
    likes = [playlist.id for playlist in user.likes]
    return render_template('users/show.html', user=user, playlist=playlist, likes=likes)





########################################################
#likes



@app.route('/users/<int:user_id>/likes', methods=["GET"])
def show_likes(user_id):
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    user = User.query.get_or_404(user_id)
    return render_template('users/likes.html', user=user, likes=user.likes)


@app.route('/users/add_like/<int:playlist_id>', methods=['POST'])
def add_like(playlist_id):
    """Toggle a liked message for the currently-logged-in user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    liked_playlist = Playlist.query.get_or_404(playlist_id)
    if liked_playlist.user_id == g.user.id:
        return abort(403)

    user_likes = g.user.likes

    if liked_playlist in user_likes:
        g.user.likes = [like for like in user_likes if like != liked_playlist]
    else:
        g.user.likes.append(liked_playlist)
    

    db.session.commit()
    return redirect("/")






@app.route('/users/profile', methods=["GET", "POST"])
def profile():
    """Update profile for current user."""
    # IMPLEMENT THIS

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    user = g.user
    form = EditUserForm(obj=user)
   


    if form.validate_on_submit():
        if User.authenticate(user.username, form.password.data):
            user.username = form.username.data
            user.email = form.email.data
            user.image_url = form.image_url.data or "/static/images/default-pic.png"
            # user.header_image_url = form.header_image_url.data or "/static/images/warbler-hero.jpg"
            # user.bio = form.bio.data

            db.session.commit()
            return redirect(f"/users/{user.id}")

        flash("Incorrect password, please try again", 'danger')

    return render_template('users/edit.html', form=form, user_id=user.id)
        
        

    


@app.route('/users/delete', methods=["POST"])
def delete_user():
    """Delete user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout()

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/signup")


##############################################################################
# Playlists routes:

@app.route('/playlists/new', methods=["GET", "POST"])
def playlists_add():
    """Add a playlist:

    Show form if GET. If valid, update playlist and redirect to user page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = NewPlaylistForm()
    user = g.user
    if form.validate_on_submit():
        playlist = Playlist(title=form.title.data, text=form.text.data,)
        user.playlists.append(playlist)
        db.session.add(playlist)
        db.session.commit()

        return redirect(f"/users/{user.id}")

    return render_template('playlists/new.html', form=form)



@app.route('/playlists/<int:playlist_id>', methods=["GET"])
def show_playlist_details(playlist_id):
    """Show a specific playlist."""

    playlist = Playlist.query.get_or_404(playlist_id)
    return render_template('playlists/show.html', playlist=playlist)



@app.route('/users/<int:user_id>/playlists', methods=["GET"])
def list_user_playlists(user_id):
    """Show a playlist."""
    
    user = User.query.get_or_404(user_id)

    playlist = (Playlist
                .query
                .filter(Playlist.user_id == user_id))
    
    return render_template('users/playlists.html', playlist=playlist, user=user)


@app.route('/playlists', methods=["GET"])
def playlists_show_all():
    """Show a playlist."""
    user = g.user
    playlist = Playlist.query.all()
    return render_template('playlists/index.html', playlist=playlist, user=user)


@app.route('/playlist/<int:playlist_id>/delete', methods=["POST"])
def playlists_delete(playlist_id):
    """Delete a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    playlist = Playlist.query.get(playlist_id)
    if playlist.user_id != g.user.id:
        flash("Access unauthorized.", "danger")
        return redirect ("/")

    db.session.delete(playlist)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")



##############################################################################
# Movie pages


@app.route('/movies/<string:s>/', methods=['GET'])
def show_search_results(s):
    """Logic for sending an API request and displaying the JSON response as an HTML. Expects a GET request."""
    form = SearchForm

    s = form.s

    results = requests.get(f"{API_BASE_URL}",params={"s": s}).json()

    # Using try/except to catch any errors that might occur while sending a request to API. Such as sending empty string, space, multiple spaces, unsupported character, etc.
    # try:
        # rendering a template and passing the json version of the result
    return render_template('movies/search_results.html', results = results)

    # except Exception as e:

    #     flash("Search criteria did not return any results. Please try searching again with a different keyword.", "warning")

    #     return redirect('/')



##############################################################################
# Homepage and error pages


@app.route('/')
def homepage():
    """Show homepage:

    """
    form = LikeAddForm()

    if g.user:

        playlist = (Playlist
                .query
                .filter(Playlist.user_id != g.user.id))
        # liked_playlist_ids = [playlist.id for playlist in g.user.likes]

        return render_template('home.html', playlist=playlist, form=form)

    else:
        return render_template('home-anon.html')


@app.errorhandler(404)
def page_not_found(e):
    """404 NOT FOUND page."""

    return render_template('404.html'), 404

##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@app.after_request
def add_header(req):
    """Add non-caching headers on every request."""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers['Cache-Control'] = 'public, max-age=0'
    return req
