#!/usr/bin/env python2
# - * - coding=utf-8 - * -

import datetime
import re

from webapp import db


class APIKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    secret = db.Column(db.String(64))
    member = db.Column(db.Integer, db.ForeignKey("member.id"))
    description = db.Column(db.Text)


class MemberTransfer(db.Model):
    __tablename__ = "member_transfer"
    id = db.Column(db.Integer, primary_key=True)
    member = db.Column(db.Integer, db.ForeignKey("member.id"))
    transfer_id = db.Column(db.Integer, db.ForeignKey("transfer.id"))
    year = db.Column(db.Integer)
    month = db.Column(db.Integer)
    transfer = db.relationship("Transfer", backref="member_transfers")

    def __init__(self, _id, year, month, transfer):
        self.id = _id
        self.year = year
        self.month = month
        self.transfer = transfer


class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True)
    type = db.Column(db.Enum("starving", "fatty", name="member_types"))
    transfers = db.relationship("MemberTransfer")
    active = db.Column(db.Boolean)
    api_keys = db.relationship("APIKey")

    def get_next_unpaid(self):
        year, month, oldest = 0, 0, 0
        for mt in self.transfers:
            age = mt.year * 12 + (mt.month - 1)
            if age > oldest:
                oldest = age
                year = mt.year
                month = mt.month
        if year == 0:
            # TODO: should be a member's join date rather than now
            now = datetime.datetime.now()
            return now.year, now.month
        else:
            month += 1
            if month > 12:
                month = 1
                year += 1
            return year, month


    def months_due(self):
        # TODO: fix if member hasn't paid yet...
        now = datetime.datetime.now()
        oldest = 0
        for mt in self.transfers:
            age = mt.year * 12 + (mt.month - 1)
            if age > oldest:
                oldest = age
        return (now.year * 12 + (now.month - 1)) - oldest

    def __init__(self, _id, _username, _type, _active):
        self.id = _id
        self.username = _username
        self.type = _type
        self.active = _active


class Transfer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(128))
    account_from = db.Column(db.String(32))
    name_from = db.Column(db.String(256))
    amount = db.Column(db.Integer)
    title = db.Column(db.String(256))
    date = db.Column(db.Date)

    def __init__(self, _id, _uid, _account_from, _name_from, _amount, _title, _date):
        self.id = _id
        self.uid = _uid
        self.account_from = _account_from
        self.name_from = _name_from
        self.amount = _amount
        self.title = _title
        self.date = _date

    def parse_title(self):
        m  = re.match(ur"^([a-z0-9\-_\.]+) *\- *(fatty|starving|superfatty) *\- *([0-9a-z\-_ąężźćóżłśń \(\),/\.]+$)", self.title.strip().lower())
        if not m:
            return (None, None, None)
        member, _type, title = m.group(1), m.group(2), m.group(3)
        if title in  [u"składka", u"opłata", u"opłata miesięczna", "skladka"]:
            return (member, _type, None)
        return member, _type, title

    MATCH_OK, MATCH_WRONG_TYPE, MATCH_NO_USER, MATCH_UNPARSEABLE = range(4)
    def get_matchability(self):
        title = self.parse_title()
        if not title[0]:
            return self.MATCH_UNPARSEABLE, self.title

        member_name = title[0]
        member = Member.query.filter_by(username=member_name).first()
        if not member:
            return self.MATCH_NO_USER, member_name
        
        if title[2]:
            return self.MATCH_WRONG_TYPE, member

        return self.MATCH_OK, member