# - * - coding=utf-8 - * -

# Copyright (c) 2015, Sergiusz Bazanski <q3k@q3k.org>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE 
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import sys, traceback
import datetime
import json
import requests
import re
from email.mime.text import MIMEText
from subprocess import Popen, PIPE

from webapp import app, forms, User, db, models, mc, cache_enabled, admin_required
from flask.ext.login import login_user, login_required, logout_user, current_user
from flask import request, redirect, flash, render_template, url_for, abort, g
import banking
import logic
import directory


@app.route('/')
def stats():
    return render_template('stats.html')

@app.route('/memberlist')
@login_required
def memberlist():
    cache_key = 'kasownik-view-memberlist'
    cache_data = mc.get(cache_key)
    if not cache_data or not cache_enabled:
        members = models.Member.get_members(True)
        cache_data = []
        for member in members:
            element = member.get_status()
            if not element['judgement']:
                continue
            cache_data.append(element)
        mc.set(cache_key, cache_data)
        return render_template('memberlist.html',
                           active_members=cache_data)

@app.route('/profile')
@login_required
def self_profile():
    member = models.Member.get_members(True).filter_by(ldap_username=current_user.username).first()
    if not member:
        abort(404)
    status = member.get_status()
    cn = directory.get_member_fields(g.ldap, member.ldap_username, 'cn')['cn']
    return render_template("admin_member.html", member=member, status=status,
                           cn=cn, admin=False)

@app.route("/admin")
@admin_required
@login_required
def admin_index():
    members = [m.get_status() for m in models.Member.get_members(True)]
    for member in members:
        due = member['months_due']
        if due < 1:
            member['color'] = "00FF00"
        elif due < 3:
            member['color'] = "E0941B"
        else:
            member['color'] = "FF0000"
    
    active_members = filter(lambda m: m['judgement'], members)
    inactive_members = filter(lambda m: not m['judgement'], members)

    return render_template("admin_index.html",
                           active_members=active_members,
                           inactive_members=inactive_members)

@app.route('/admin/member/<membername>')
@login_required
@admin_required
def admin_member(membername):
    member = models.Member.get_members(True).filter_by(ldap_username=membername).first()
    if not member:
        abort(404)
    status = member.get_status()
    cn = directory.get_member_fields(g.ldap, member.ldap_username, 'cn')['cn']
    return render_template("admin_member.html", member=member, status=status,
                           cn=cn, admin=True)

@app.route("/admin/member/<membername>/policy:<policy>")
@login_required
@admin_required
def admin_member_set_policy(membername,policy):
    member = models.Member.query.filter_by(ldap_username=membername).first()
    member.payment_policy = models.PaymentPolicy[policy].value
    db.session.add(member)
    db.session.commit()
    return redirect(request.referrer)

@app.route("/admin/member/<membername>/membership:<membershiptype>")
@login_required
@admin_required
def admin_member_set_membership(membername,membershiptype):
    member = models.Member.query.filter_by(ldap_username=membername).first()
    member.type = models.MembershipType[membershiptype].name
    db.session.add(member)
    db.session.commit()
    return redirect(request.referrer)


@app.route("/admin/member/add/<membershiptype>/<username>")
@login_required
@admin_required
def add_member(type, username):
    member = models.Member(None, username, models.MembershipType[membershiptype].name, True)
    db.session.add(member)
    db.session.commit()
    return "ok"

@app.route("/admin/fetch", methods=["GET", "POST"])
@login_required
@admin_required
def admin_fetch():
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
            return redirect(url_for("admin_fetch"))
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()

            flash("Error when fetching data. %s" % traceback.format_exception(exc_type, exc_value,exc_traceback))
            return redirect(url_for("admin_fetch"))

    logic.update_transfer_rows()
    transfers_unmatched = logic.get_unmatched_transfers()

    return render_template("fetch.html", form=form, transfers_unmatched=transfers_unmatched)


@app.route("/admin/match/auto", methods=["GET"])
@login_required
@admin_required
def admin_match_auto():
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
    flash("Matched %i, %i left" % (matched, left))
    return redirect(url_for("admin_fetch"))

@app.route("/admin/match/manual", methods=["GET"])
@login_required
@admin_required
def match_manual():
    transfers_unmatched = logic.get_unmatched_transfers()
    return render_template("match_manual.html", transfers_unmatched=transfers_unmatched)

@app.route("/admin/match/<username>/<uid>/<int:months>")
@login_required
@admin_required
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


@app.route("/admin/match/", methods=["POST"])
@login_required
@admin_required
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

@app.route("/login", methods=["POST", "GET"])
def login():
    form = forms.LoginForm(request.form)
    if request.method == "POST" and form.validate():
        if requests.post("https://auth.hackerspace.pl/",
                         dict(login=form.username.data, password=form.password.data)).status_code == 200:
            user = User(form.username.data)
            login_user(user)
            flash('Logged in succesfully')
            if user.is_admin():
                return redirect(request.args.get("next") or url_for("admin_index"))
            else:
                return redirect(request.args.get("next") or url_for("self_profile"))
    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("stats"))


def sendspam():
    spam = []
    members = models.Member.query.filter_by(active=True).all()
    for member in members:
    	transfers = sorted(member.transfers, key=lambda mt: mt.year * 12 + (mt.month-1) )
        # quick hack for inactive members
        active_user = True
        for mt in transfers:
            if mt.transfer.date.year == 1:
                active_user = False
                break
        if not active_user:
            continue
        details = u"\n".join([u" - opłata za %02i/%i, pokryta przelewem za %.2f PLN w dniu %s" \
            % (mt.month, mt.year, mt.transfer.amount/100,  mt.transfer.date.strftime("%d/%m/%Y")) for mt in transfers])
        months_due = member.months_due()
        money_due = months_due * 10000 if member.type == 'fatty' else months_due * 5000
        due = "???"
        if months_due > 0:
            due = u"Jesteś %i składek (%i PLN) do tyłu. Kiepsko." % (months_due, money_due/100)
            if months_due < 5:
                due = u"Jesteś %i składki (%i PLN) do tyłu. Kiepsko." % (months_due, money_due/100)
            if months_due == 1:
                due = u"Jesteś o składkę (%i PLN) do tyłu." % (money_due/100)
            if months_due > 2:
                due += u"""\nZgodnie z regulaminem HS, trzymiesięczna zaległość w składkach oznacza automatyczne wykreślenie z listy członków i usunięcie karty z zamka.
Masz tydzień na uregulowanie składki od daty wysłania tego emaila."""
        elif months_due == 0:
            due = u"Jesteś na bieżąco ze składkami. Hura!"
        else:
            due = u"Jesteś do przodu ze składkami. Świetnie!"
        text = u"""Siemasz %s,

automatycznie wygenerowałem raport ze stanu składek dla Twojego konta.
Oto stan na dzień %s:

%s

Oto szczegółowe informacje o Twoich wpłatach:
%s

Jeśli coś się nie zgadza, odpisz na tego mejla z pretensjami - wiadomość trafi do naszego białkowego skarbnika który postara się ustalić, co poszło źle.
Jednocześnie przypominam, że trzymiesięczna zaległość w płaceniu oznacza wykreślenie z listy członków - automatyczną!

xoxoxoxo,
Hackerspace'owy Kasownik
--
„100 linii pythona!” - enki o skrypcie do składek""" % (member.username, datetime.datetime.now().strftime("%d/%m/%Y"), due, details)
        msg = MIMEText(text, "plain", "utf-8")
        msg["From"] = "Hackerspace'owy Kasownik <kasownik@hackerspace.pl>"
        msg["Subject"] = "Stan składek na dzień %s" % datetime.datetime.now().strftime("%d/%m/%Y")
        
        # I will replace this with python-ldap soon. I promise!
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
        spam.append(msg)

    for msg in spam:
    	#f = open("/tmp/spamspamspam", "a")
	#f.write(msg.as_string())
	#f.close()
        p = Popen(["/usr/sbin/sendmail", "-t"], stdin=PIPE)
        p.communicate(msg.as_string())
        pass
    return "done!"
