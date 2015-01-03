import hmac
import json
import datetime
from functools import wraps
from sqlalchemy import and_

from flask import request, abort, Response

from webapp import models, app, mc

class APIError(Exception):
    def __init__(self, message, code=500):
        self.message = message
        self.code = code


def _public_api_method(path):
    """A decorator that adds a public, GET based method at /api/<path>.json.

    The resulting data is JSON-serialized."""
    def decorator2(original):
        @wraps(original)
        def wrapper_json(*args, **kwargs):
            try:
                content = original(*args, **kwargs)
                status = "ok"
                code = 200
            except APIError as e:
                content = e.message
                code = e.code
                status = "error"
            except Exception as e:
                raise
                content = "Internal server error."
                code = 500
                status = "error"
            
            last_transfer = models.Transfer.query.order_by(models.Transfer.date.desc()).first()
            modified = str(last_transfer.date)

            r = {}
            r["status"] = status
            r["content"] = content
            r["modified"] = modified
            return Response(json.dumps(r), mimetype="application/json"), code
        return app.route("/api/" + path + ".json", methods=["GET"])(wrapper_json)
    return decorator2
            

def _private_api_method(path):
    """A decorator that adds a private, HMACed, POST based method at /api/path.
    The  JSON-decoded POSTbody is stored as request.decoded.
    The resulting data is also JSON-encoded.

    It also that ensures that the request is authorized if 'private' is True.
    If so, it also adds a request.api_member object that points to a member if an
    API key should be limited to that member (for example, when handing over
    keys to normal members)."""
    def decorator(original):
        @wraps(original)
        def wrapper(*args, **kwargs):
            if request.data.count(",") != 1:
                abort(400)
            message64, mac64 = request.data.split(",")
            try:
                message = message64.decode("base64")
                mac = mac64.decode("base64")
            except:
                abort(400)

            for key in models.APIKey.query.all():
                mac_verify = hmac.new(key.secret.encode("utf-8"))
                mac_verify.update(message)
                if mac_verify.digest() == mac:
                    break
            else:
                abort(403)

            if key.member:
                request.api_member = key.member
            else:
                request.api_member = None
            try:
                if request.data:
                    request.decoded = json.loads(request.data.decode("base64"))
                else:
                    request.decoded = {}
            except Exception as e:
                print request.data
                print e
                abort(400)

            return json.dumps(original(*args, **kwargs))
        return app.route("/api/" + path, methods=["POST"])(wrapper)
    return decorator

@_private_api_method("list_members")
def api_members():
    if request.api_member:
        abort(403)

    members = [member.username for member in models.Member.query.all()]
    return members


@_private_api_method("get_member_info")
def api_member():
    mid = request.decoded["member"]
    if request.api_member and request.api_member.username != mid:
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

def _stats_for_month(year, month):
    cache_key = 'kasownik-stats_for_month-{}-{}'.format(year, month)
    cache_data = mc.get(cache_key)
    if cache_data:
        cache_data = json.loads(cache_data)
        return cache_data[0], cache_data[1]
    # TODO: export this to the config
    money_required = 4800
    money_paid = 0
    mts = models.MemberTransfer.query.filter_by(year=year, month=month).\
        join(models.MemberTransfer.transfer).all()
    for mt in mts:
        amount_all = mt.transfer.amount
        amount = amount_all / len(mt.transfer.member_transfers)
        money_paid += amount
    mc.set(cache_key, json.dumps([money_required, money_paid/100]))
    return money_required, money_paid/100

@_public_api_method("month/<year>/<month>")
def api_month(year=None, month=None):
    money_required, money_paid = _stats_for_month(year, month)
    return dict(required=money_required, paid=money_paid)

@_public_api_method("mana")
def api_manamana(year=None, month=None):
    """To-odee doo-dee-doo!"""
    now = datetime.datetime.now()
    money_required, money_paid = _stats_for_month(now.year, now.month)
    return dict(required=money_required, paid=money_paid)

@_public_api_method("months_due/<membername>")
def api_months_due(membername):
    cache_key = 'kasownik-months_due-{}'.format(membername)
    cache_data = mc.get(cache_key)
    if cache_data:
        return cache_data
    member = models.Member.query.filter_by(username=membername).first()
    if not member:
        raise APIError("No such member.", 404)
    year, month = member.get_last_paid()
    if not year:
        raise APIError("Member never paid.", 402)
    if year and member.active == False:
        raise APIError("No longer a member.", 410)
    due = member.months_due()
    #now = datetime.datetime.now()
    #then_timestamp = year * 12 + (month-1)
    #now_timestamp = now.year * 12 + (now.month-1)
    mc.set(cache_key, due)
    return due

@_public_api_method("cashflow/<int:year>/<int:month>")
def api_cashflow(year, month):
    cache_key = 'kasownik-cashflow-{}-{}'.format(year, month)
    cache_data = mc.get(cache_key)
    if cache_data:
        amount_in = cache_data
    else:
        start = datetime.date(year=year, month=month, day=1)
        month += 1
        if month > 12:
            month = 1
            year += 1
        end = datetime.date(year=year, month=month, day=1)
        transfers = models.Transfer.query.filter(and_(models.Transfer.date >= start, models.Transfer.date < end)).all()
        amount_in = sum(t.amount for t in transfers)
        mc.set(cache_key, amount_in)
    return {"in": amount_in/100, "out": -1}
