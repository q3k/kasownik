from webapp import app


@app.route("/")
def root():
    return 'Hello.'
