from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager

app = Flask(__name__)
app.config.from_object("config.CurrentConfig")
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

import webapp.models


class User(object):
    def __init__(self, username):
        self.username = username

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.username


@login_manager.user_loader
def load_user(username):
    return User(username)


import webapp.views
import webapp.api


def init():
    pass

