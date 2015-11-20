#!/usr/bin/env python2
# - * - coding=utf-8 - * -

import datetime
import re

from webapp import app,db


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
    transfers = db.relationship("MemberTransfer",order_by=[db.asc(MemberTransfer.year), db.asc(MemberTransfer.month)])
    active = db.Column(db.Boolean)
    api_keys = db.relationship("APIKey")
    join_year = db.Column(db.Integer)
    join_month = db.Column(db.Integer)

    def get_last_paid(self):
        year, month, oldest = 0, 0, 0
        for mt in self.transfers:
            if mt.transfer.uid == app.config["DUMMY_TRANSFER_UID"]:
                continue
            age = mt.year * 12 + (mt.month - 1)
            if age > oldest:
                oldest = age
                year = mt.year
                month = mt.month
        if year == 0:
            return None, None
        else:
            return year, month

    def get_next_unpaid(self):
        now_date = datetime.datetime.now()
        now = now_date.year * 12 + (now_date.month -1)
        del now_date

        if self.join_year is not None and self.join_month is not None:
            joined = self.join_year * 12 + (self.join_month - 1)
        else:
            joined = None

        year, month, oldest = 0, 0, 0
        

        for mt in self.transfers:
            age = mt.year * 12 + (mt.month - 1)
            if age > oldest:
                oldest = age
                if mt.transfer.uid == app.config["DUMMY_TRANSFER_UID"]:
                    year = 0
                    month = 0
                else:
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
        now_date = datetime.datetime.now()
        now = now_date.year * 12 + (now_date.month -1)
        del now_date

        if self.join_year is not None and self.join_month is not None:
            joined = self.join_year * 12 + (self.join_month - 1)
        else:
            joined = None

        unpaid_months = 0
        last_age = 0
        last_uid = None
        
        for mt in self.transfers:
            age = mt.year * 12 + (mt.month - 1)
            
            # First transfer, join date known
            if last_uid == None and joined is not None:
                unpaid_months = unpaid_months + (joined - age)
            
            # First transfer, join date not known, nothing to do here
            elif last_uid == None:
                pass

            # First transfer after a gap in membership
            elif last_uid == app.config["DUMMY_TRANSFER_UID"]:
                pass
            
            # Unpaid months between transfers
            elif age - last_age > 1:
                unpaid_months = unpaid_months + (age - last_age) - 1
            
            last_age = age
            last_uid = mt.transfer.uid

        # Not a member anymore
        if last_uid == app.config["DUMMY_TRANSFER_UID"]:
            pass

        # Never paid, known join date
        elif last_uid is None and joined is not None:
            unpaid_months = unpaid_months + (now - joined)

        # Never paid, unknown join date, WTF
        elif last_uid is None:
            pass

        # Is a member, has not paid recently
        else:
            unpaid_months = unpaid_months + (now - last_age)
        
        return unpaid_months 

    def __init__(self, _id, _username, _type, _active):
        self.id = _id
        self.username = _username
        self.type = _type
        self.active = _active
        now_date = datetime.datetime.now()
        self.join_year = now_date.year
        self.join_month = now_date.month

class Transfer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(128))
    account_from = db.Column(db.String(32))
    name_from = db.Column(db.String(256))
    amount = db.Column(db.Integer)
    title = db.Column(db.String(256))
    date = db.Column(db.Date)
    ignore = db.Column(db.Boolean)

    def __init__(self, _id, _uid, _account_from, _name_from, _amount, _title, _date, _ignore):
        self.id = _id
        self.uid = _uid
        self.account_from = _account_from
        self.name_from = _name_from
        self.amount = _amount
        self.title = _title
        self.date = _date
        self.ignore = _ignore

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
        
        if (title[1] == 'starving' and self.amount > 50) or (title[1] == 'fatty' and self.amount > 100):
            return self.MATCH_WRONG_TYPE, member

        if title[2]:
            return self.MATCH_WRONG_TYPE, member

        return self.MATCH_OK, member
