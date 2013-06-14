#!/usr/bin/env/python2
# -*- coding: utf-8 -*-

import csv
import datetime
import re
import hashlib
import StringIO

from webapp import app


class BREParseError(Exception):
    pass


class BRERow(object):
    BRE_IN = [772, 770]
    SECRET = app.config["SECRET"]

    def parse_data(self):
        datar = self.data_raw.split(";")
        data = {}
        for d in datar[1:]:
            kv = d.split(":")
            k = kv[0].strip()
            v = ":".join(kv[1:]).strip()
            data[k] = v

        if self._type in self.BRE_IN:
            # in
            self.type = "IN"
            self.from_name = data["od"]
            self.from_account = data["z rach."]
            self.title = data["tyt."].lower()
            self.tnr = int(data["TNR"].split(".")[0])

        self.olduid = hashlib.sha256(self.SECRET + ','.join(self.raw).encode("utf-8")).hexdigest()
        self.uid = hashlib.sha256(self.SECRET + data["TNR"]).hexdigest()

    def __init__(self, row):
        self.time = datetime.datetime.strptime(row[1], "%d/%m/%Y")
        self.account = row[2]
        # is this secure?
        self.amount = int(float(row[3].replace(",", ".").replace(" ", "")) * 100)
        self._type = int(row[6])
        self.data_raw = row[5]
        self.type = ""
        self.raw = row


class BREParser(object):
    def __init__(self):
        self.rows = []

    def parse(self, snapshot):
        c = csv.reader(StringIO.StringIO(snapshot), delimiter="|")
        for row in c:
            r = BRERow([r.decode("iso-8859-2") for r in row])
            r.parse_data()
            self.rows.append(r)

    def get_by_type(self, y):
        return [row for row in self.rows if row.type == "IN"]


def guess_title(title):
    m = re.match(ur"^([a-z0-9\-_\.]+) *\- *(fatty|starving) *z\- *([0-9a-z\-_ąężźćóżłśń]+$)", title.strip().lower())
    if not m:
        return None, None, None
    member, _type, title = m.group(1), m.group(2), m.group(3)
    if title in [u"składka", u"opłata", u"opłata miesięczna", "skladka"]:
        return member, _type, None
    return member, _type, title
