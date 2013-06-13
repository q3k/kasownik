from webapp import app, api_call


@app.route("/")
def root():
    return 'Hello.'

@app.route("/members")
@api_call()
def list_members():
    print "members!"
