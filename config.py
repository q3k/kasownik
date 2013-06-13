class Config(object):
    DEBUG = False
    TESTING = False
    CREATE_DATABASE = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///data.db"


class DevelopmentConfig(Config):
    CREATE_DATABASE = True
    DEBUG = True
