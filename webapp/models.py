#!/usr/bin/env python2
# - * - coding=utf-8 - * -

import datetime
import enum
import json
import re

from sqlalchemy.orm import subqueryload_all

from webapp import app, db, mc, cache_enabled


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


class PaymentStatus(enum.Enum):
    never_paid = 1 # never paid membership fees
    unpaid = 2 # more than 3 fees unapid
    okay = 3 # fees paid


class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True)
    type = db.Column(db.Enum("starving", "fatty", name="member_types"))
    transfers = db.relationship("MemberTransfer",order_by=[db.asc(MemberTransfer.year), db.asc(MemberTransfer.month)])
    active = db.Column(db.Boolean)
    api_keys = db.relationship("APIKey")
    join_year = db.Column(db.Integer)
    join_month = db.Column(db.Integer)

    @classmethod
    def get_members(kls, deep=False):
        """Gets all members as an SQLAlchemy query.
        @param(deep) - whether to do a subqueryload_all and load all transfer data
        """
        if deep:
            return kls.query.options(subqueryload_all(kls.transfers,
                MemberTransfer.transfer)).order_by(kls.username)
        else:
            return kls.query.order_by(kls.username)


    def _yearmonth_increment(self, ym):
        y, m = ym
        y2, m2 = y, m+1
        if m2 > 12:
            y2 += 1
            m2 = 1
        return (y2, m2)

    def _yearmonth_scalar(self, ym):
        y, m = ym
        return y * 12 + (m - 1)

    def _get_status_uncached(self):
        now_date = datetime.datetime.now()
        now = now_date.year * 12 + (now_date.month - 1)
        del now_date

        status = {}
        status['ldap_username'] = self.get_ldap_username()
        status['username'] = self.username
        status['type'] = self.type
        # First check - did we actually get any transfers?
        if not self.transfers or self.transfers[0].transfer.uid == app.config['DUMMY_TRANSFER_UID']:
            status['payment_status'] = PaymentStatus.never_paid
            status['months_due'] = None
            status['last_paid'] = (None, None)
            if self.join_year is not None and self.join_month is not None:
                status['joined'] = (self.join_year, self.join_month)
                status['next_unpaid'] = self._yearmonth_increment(status['joined'])
            else:
                status['joined'] = (None, None)
                status['next_unpaid'] = (None, None)
            return status

        # Use the join date from SQL, if available
        if self.join_year is not None and self.join_month is not None:
            joined = (self.join_year, self.join_month)
        else:
            joined = (self.transfers[0].year, self.transfers[0].month)
        joined_scalar = self._yearmonth_scalar(joined)
        status['joined'] = joined

        most_recent_transfer = (0, 0)
        unpaid_months = 0

        # Iterate over all payments and figure out how much months are unpaid
        previous_transfer = (0, 0)
        previous_uid = None
        active_payment = True

        for mt in self.transfers:
            this_transfer = (mt.year, mt.month)
            this_scalar = self._yearmonth_scalar(this_transfer)
            this_uid = mt.transfer.uid

            previous_scalar = self._yearmonth_scalar(previous_transfer)
            most_recent_scalar = self._yearmonth_scalar(most_recent_transfer)

            # Is this transfer a „not a member anymore” transfer?
            if this_uid == app.config['DUMMY_TRANSFER_UID']:
                active_payment = False
                continue

            # Is this the first transfer? See if it was done on time
            if previous_uid is None:
                unpaid_months += (this_scalar - joined_scalar)
                    
            # Apply any missing payments
            if active_payment and previous_uid is not None:
                unpaid_months += (this_scalar - previous_scalar) - 1

            # Is this the most recent payment?
            if this_scalar > most_recent_scalar:
                most_recent_scalar = this_scalar
                most_recent_transfer = this_transfer

            active_payment = True
            
            previous_transfer = this_transfer
            previous_uid = this_uid


        status['months_due'] = unpaid_months
        status['payment_status'] = PaymentStatus.okay if unpaid_months < 4 else PaymentStatus.unpaid
        status['last_paid'] = most_recent_transfer

        if not active_payment:
            status['next_unpaid'] = (None, None)
        else:
            status['next_unpaid'] = self._yearmonth_increment(status['last_paid'])

        return status


    def get_status(self):
        """It's better to call this after doing a full select of data."""
        cache_key = 'kasownik-payment_status-{}'.format(self.username)
        cache_data = mc.get(cache_key)
        if cache_data and cache_enabled:
            data = json.loads(cache_data)
            return data
        else:
            cache_data = self._get_status_uncached()
            mc.set(cache_key, json.dumps(cache_data))
        return cache_data

    def get_months_due(self):
        status = self.get_status()
        return status['months_due']

    def get_last_paid(self):
        status = self.get_status()
        return status['last_paid']

    def get_next_unpaid(self):
        status = self.get_status()
        return status['next_unpaid']


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
        
        if (title[1] == 'starving' and self.amount > 50) or (title[1] == 'fatty' and self.amount > 100):
            return self.MATCH_WRONG_TYPE, member

        if title[2]:
            return self.MATCH_WRONG_TYPE, member

        return self.MATCH_OK, member
