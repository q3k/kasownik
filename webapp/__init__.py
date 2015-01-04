from functools import wraps

import memcache
import requests
import sqltap.wsgi

from flask import Flask, redirect
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager, AnonymousUserMixin, login_required, current_user
from flaskext.gravatar import Gravatar

app = Flask(__name__)
app.config.from_object("config.CurrentConfig")
app.wsgi_app = sqltap.wsgi.SQLTapMiddleware(app.wsgi_app)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
mc = memcache.Client(app.config['MEMCACHE_SERVERS'], debug=0)
cache_enabled = False
gravatar = Gravatar(app, size=256, rating='g', default='retro', force_default=False, use_ssl=True, base_url=None)


import webapp.models


class AnonymousUser(AnonymousUserMixin):
    def is_admin(self):
        return False


login_manager.anonymous_user = AnonymousUser


class User(object):
    def __init__(self, username):
        self.username = username.lower().strip()
        self._admin = None

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.username

    def is_admin(self):
        if not self.is_authenticated():
            return False
        if self._admin is None:
            r = requests.get('https://capacifier.hackerspace.pl/staff/'+
                             self.username)
            self._admin = r.status_code == 200
        return self._admin


@login_manager.user_loader
def load_user(username):
    return User(username)


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_admin():
            return login_manager.unauthorized()
        return f(*args, **kwargs)
    return wrapper

import webapp.views
import webapp.api

@login_manager.unauthorized_handler
def unauthorized():
    return redirect('/login')

def init():
    pass

