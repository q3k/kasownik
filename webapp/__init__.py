import json
import hmac

from flask import Flask, request
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object("config.DevelopmentConfig")
db = SQLAlchemy(app)

import webapp.models

def api_call(private=True):
    """A decorator that decodes the POST body as JSON.
    The decoded body is stored as request.decoded.

    It also that ensures that the request is authorized if 'private' is True.
    If so, it also adds a request.member object that points to a member if an
    API key should be limited to that member (for example, when handing over
    keys to normal members)."""
    def decorator(original):
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
                    mac_verify = hmac.new(key.secret)
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
                request.decoded = json.loads(message)
            except:
                abort(400)

            return original(*args, **wkargs)
        return wrapper
    return decorator

import webapp.views


def init():
    if app.config["DEBUG"]:
        if not webapp.models.APIKey.query.filter_by(secret="testkey"):
            key = webapp.models.APIKey()
            key.secret = "testkey"
            db.session.add(key)
            db.session.commit()
