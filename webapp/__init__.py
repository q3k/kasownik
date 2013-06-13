from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object("config.DevelopmentConfig")
db = SQLAlchemy(app)

import webapp.views
import webapp.models


def init():
    if app.config["CREATE_DATABASE"]:
        db.create_all()
