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


