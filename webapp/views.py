import datetime
import requests

from webapp import app, api_method, models, login_manager, forms, User
from flask.ext.login import login_user, login_required, logout_user
from flask import request, abort, redirect, flash, render_template, url_for


@app.route("/")
@login_required
def index():
    return 'Hello.'

@api_method("/members")
def list_members():
    if request.member:
        abort(403)

    members = [member.username for member in models.Member.query.all()]
    return members

@api_method("/member_status")
def member_status():
    mid = request.decoded["member"]
    if request.member and request.member.username != mid:
        abort(403)

    member = models.Member.query.filter_by(username=mid).join(models.Member.\
        transfers).join(models.MemberTransfer.transfer).first()
    mts = member.transfers
    response = {}
    response["paid"] = []
    for mt in mts:
        t = {}
        t["year"] = mt.year
        t["month"] = mt.month
        transfer = {}
        transfer["uid"] = mt.transfer.uid
        transfer["amount"] = mt.transfer.amount
        transfer["title"] = mt.transfer.title
        transfer["account"] = mt.transfer.account_from
        transfer["from"] = mt.transfer.name_from
        t["transfer"] = transfer
        response["paid"].append(t)
    response["months_due"] = member.months_due()
    response["membership"] = member.type

    return response


@api_method("/mana", private=False)
def manamana():
    """To-odee doo-dee-doo!"""
    # TODO: export this to the config
    money_required = 4300
    money_paid = 0
    now = datetime.datetime.now()
    mts = models.MemberTransfer.query.filter_by(year=now.year, month=now.month).\
        join(models.MemberTransfer.transfer).all()
    for mt in mts:
        amount_all = mt.transfer.amount
        amount = amount_all / len(mt.transfer.member_transfers)
        money_paid += amount

    return dict(required=money_required, paid=money_paid/100)


@app.route("/login", methods=["POST", "GET"])
def login():
    form = forms.LoginForm(request.form)
    if request.method == "POST" and form.validate():
        if requests.get("https://capacifier.hackerspace.pl/staff/{}".format(form.username.data)).status_code == 200:
            if requests.post("https://auth.hackerspace.pl/",
                             dict(login=form.username.data, password=form.password.data)).status_code == 200:
                user = User(form.username.data)
                login_user(user)
                flash('Logged in succesfully')
                return redirect(request.args.get("next") or url_for("index"))
    return render_template("login.html", form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))