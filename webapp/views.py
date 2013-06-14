import datetime

from webapp import app, api_method, models
from flask import request, abort


@app.route("/")
def root():
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