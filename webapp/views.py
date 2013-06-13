from webapp import app, api_call


@app.route("/")
def root():
    return 'Hello.'

@api_call("/members")
def list_members():
    return "members!"
