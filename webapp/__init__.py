import json
import hmac
from functools import wraps

from flask import Flask, request, abort
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager

app = Flask(__name__)
app.config.from_object("config.CurrentConfig")
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

import webapp.models


def api_method(path, private=True):
    """A decorator that decodes the POST body as JSON.
    The decoded body is stored as request.decoded.
    The resulting data is also JSON-encoded.

    It also that ensures that the request is authorized if 'private' is True.
    If so, it also adds a request.member object that points to a member if an
    API key should be limited to that member (for example, when handing over
    keys to normal members)."""
    def decorator(original):
        @wraps(original)
        def wrapper(*args, **kwargs):
            if private:
                if request.data.count(",") != 1:
                    abort(400)
                message64, mac64 = request.data.split(",")
                try:
                    message = message64.decode("base64")
                    mac = mac64.decode("base64")
                except:
                    abort(400)

                for key in webapp.models.APIKey.query.all():
                    mac_verify = hmac.new(key.secret.encode("utf-8"))
                    mac_verify.update(message)
                    if mac_verify.digest() == mac:
                        break
                else:
                    abort(403)
                if key.member:
                    request.member = key.member
                else:
                    request.member = None
            else:
                message = request.data
                request.member = None
            try:
                if request.data:
                    request.decoded = json.loads(request.data.decode("base64"))
                else:
                    request.decoded = {}
            except Exception as e:
                print request.data
                print e
                abort(400)

            return json.dumps(original(*args, **kwargs))
        return app.route("/api" + path, methods=["POST"] if private else ["POST", "GET"])(wrapper)
    return decorator


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


def init():
    pass

