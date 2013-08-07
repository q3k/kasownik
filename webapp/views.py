# - * - coding=utf-8 - * -

import datetime
import requests
import os
import re
from email.mime.text import MIMEText
from subprocess import Popen, PIPE

from webapp import app, api_method, models, login_manager, forms, User, db
from flask.ext.login import login_user, login_required, logout_user
from flask import request, abort, redirect, flash, render_template, url_for
import banking
import logic


@app.route("/")
@login_required
def index():
    active_members = models.Member.query.order_by(models.Member.username).filter_by(active=True).all()
    inactive_members = models.Member.query.order_by(models.Member.username).filter_by(active=False).all()
    for member in active_members:
        due = member.months_due()
        if due < 1:
            member.color = "00FF00"
        elif due < 3:
            member.color = "E0941B"
        else:
            member.color = "FF0000"
    return render_template("index.html", active_members=active_members, inactive_members=inactive_members)


@api_method("/members")
def list_members():
    if request.member:
        abort(403)

    members = [member.username for member in models.Member.query.all()]
    return members


@api_method("/member_info")
def api_member_info():
    mid = request.decoded["member"]
    if request.member and request.member.username != mid:
        abort(403)

    member = models.Member.query.filter_by(username=mid).join(models.Member.transfers).\
        join(models.MemberTransfer.transfer).first()
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


@api_method("/month/<year>/<month>", private=False)
def api_month(year=None, month=None):
    # TODO: export this to the config
    money_required = 4300
    money_paid = 0
    mts = models.MemberTransfer.query.filter_by(year=year, month=month).\
        join(models.MemberTransfer.transfer).all()
    for mt in mts:
        amount_all = mt.transfer.amount
        amount = amount_all / len(mt.transfer.member_transfers)
        money_paid += amount

    return dict(required=money_required, paid=money_paid/100)

@api_method("/mana", private=False)
def manamana(year=None, month=None):
    """To-odee doo-dee-doo!"""
    now = datetime.datetime.now()
    return api_month(year=now.year, month=now.month)


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


@app.route("/member/<membername>/activate")
@login_required
def member_activate(membername):
    member = models.Member.query.filter_by(username=membername).first()
    member.active = True
    db.session.add(member)
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/member/<membername>/deactivate")
@login_required
def member_deactivate(membername):
    member = models.Member.query.filter_by(username=membername).first()
    member.active = False
    db.session.add(member)
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/fetch", methods=["GET", "POST"])
@login_required
def fetch():
    form = forms.BREFetchForm(request.form)
    if request.method == "POST" and form.validate():
        identifier = form.identifier.data
        token = form.token.data
        try:
            f = banking.BREFetcher()
            f.login(identifier, token)
            data = f.create_report().read()
            flash("Fetched data from BRE ({} rows)".format(data.count("\n")))
            f = open(app.config["BRE_SNAPSHOT_PATH"], "w")
            f.write(data)
            f.close()
            return redirect(url_for("fetch"))
        except:
            flash("Error when fetching data.")
            return redirect(url_for("fetch"))

    transfers_unmatched = logic.get_unmatched_transfers()

    return render_template("fetch.html", form=form, transfers_unmatched=transfers_unmatched)

@app.route("/match-easy", methods=["GET"])
@login_required
def match_easy():
    matched = 0
    left = 0
    transfers_unmatched = logic.get_unmatched_transfers()
    for transfer in transfers_unmatched:
        matchability, extra = transfer.get_matchability()
        if matchability == models.Transfer.MATCH_OK:
            member = extra
            if len(member.transfers) > 0:
                year, month = member.get_next_unpaid()
            else:
                year, month = transfer.date.year, transfer.date.month
            mt = models.MemberTransfer(None, year, month, transfer)
            member.transfers.append(mt)
            db.session.add(mt)
            matched += 1
        else:
            left += 1
    db.session.commit()

    return "okay: matched %i, %i left" % (matched, left)

@app.route("/match-manual", methods=["GET"])
@login_required
def match_manual():
    transfers_unmatched = logic.get_unmatched_transfers()
    return render_template("match_manual.html", transfers_unmatched=transfers_unmatched)

@app.route("/match/<username>/<uid>/<int:months>")
@login_required
def match(username, uid, months):
    member = models.Member.query.filter_by(username=username).first()
    if not member:
        return "no member"
    transfer = models.Transfer.query.filter_by(uid=uid).first()
    if not transfer:
        return "no transfer"

    for _ in range(months):
        year, month = member.get_next_unpaid()
        mt = models.MemberTransfer(None, year, month, transfer)
        member.transfers.append(mt)
        db.session.add(mt)

    db.session.commit()
    return "ok, %i PLN get!" % transfer.amount

@app.route("/member/<username>")
@login_required
def member_info(username):
    member = models.Member.query.filter_by(username=username).first()
    if not member:
        return "no such member! :("
    amount_due = 100 * member.months_due()
    if member.type == "starving":
        amount_due = 50 * member.months_due()
    return render_template("member_info.html", member=member, amount_due=amount_due)

@app.route("/add/<type>/<username>")
@login_required
def add_member(type, username):
    if type not in ["starving", "fatty"]:
        return "no such type"
    member = models.Member(None, username, type, True)
    db.session.add(member)
    db.session.commit()
    return "ok"

@app.route("/match/", methods=["POST"])
@login_required
def match_user_transfer():
    username = request.form["username"]
    uid = request.form["uid"]
    member = models.Member.query.filter_by(username=username).first()
    if not member:
        return "no such member! :("
    transfer = models.Transfer.query.filter_by(uid=uid).first()
    if not transfer:
        return "no transfer"

    return render_template("match_user_transfer.html", member=member, transfer=transfer)

@app.route("/spam", methods=["GET"])
@login_required
def sendspam():
    spam = []
    members = models.Member.query.all()
    for member in members:
        status = "\n".join([" - %02i/%i, covered by transaction uid %s for %.2f PLN from %s (%s) on %s" \
            % (mt.month, mt.year, mt.transfer.uid, mt.transfer.amount/100, mt.transfer.account_from, \
               mt.transfer.title, mt.transfer.date.strftime("%d/%m/%Y")) for mt in member.transfers])
        nag = ""
        text = u"""Siemasz %s,

automatycznie wygenerowałem raport ze stanu składek dla Twojego konta.
Oto stan na dzień %s:

%s
%s

Jeśli coś się nie zgadza, odpisz na tego mejla z pretensjami - wiadomość trafi do naszego białkowego skarbnika który postara się ustalić, co poszło źle.
Jednocześnie przypominam, że trzymiesięczna zaległość w płaceniu oznacza wykreślenie z listy członków - automatyczną!

xoxoxoxo,
Hackerspace'owy Faszysta
--
„100 linii pythona!” - enki o skrypcie do składek""" % (member.username, datetime.datetime.now().strftime("%d/%m/%Y"), status, nag)
        msg = MIMEText(text, "plain", "utf-8")
        msg["From"] = "Faszysta Hackerspace'owy <fascist@hackerspace.pl>"
        msg["Subject"] = "Stan składek na dzień %s" % datetime.datetime.now().strftime("%d/%m/%Y")
        spam.append(msg)
    for msg in spam:
        p = Popen(["ldapsearch", "-x", "-ZZ", "-b" "ou=People,dc=hackerspace,dc=pl", "uid=%s" % member.username], stdout=PIPE)
        lines = p.stdout.read()
        emails = ["%s@hackerspace.pl" % member.username ]
        for line in lines.split("\n"):
                m = re.match(r"^mail: (.*)$", line)
                if m:
                        email = m.group(1)
                        if not email.endswith("@hackerspace.pl"):
                                emails.append(email)
        msg["To"] = ", ".join(emails)

        p = Popen(["/usr/sbin/sendmail", "-t"], stdin=PIPE)
        p.communicate(msg.as_string())
    return "done!"
