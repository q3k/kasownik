#!/usr/bin/env/python2
# -*- coding: utf-8 -*-

import csv
import datetime
import re
import hashlib
import StringIO
import requests
import bs4
import time

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
        c = csv.reader(snapshot, delimiter="|")
        for row in c:
            r = BRERow([r.decode("iso-8859-2") for r in row])
            r.parse_data()
            self.rows.append(r)

    def get_by_type(self, y):
        return [row for row in self.rows if row.type == y]


def guess_title(title):
    m = re.match(ur"^([a-z0-9\-_\.]+) *\- *(fatty|starving) *z\- *([0-9a-z\-_ąężźćóżłśń]+$)", title.strip().lower())
    if not m:
        return None, None, None
    member, _type, title = m.group(1), m.group(2), m.group(3)
    if title in [u"składka", u"opłata", u"opłata miesięczna", "skladka"]:
        return member, _type, None
    return member, _type, title

class BREFetcher(object):
    BASE = "https://www.ibre.com.pl/mt/"
    def __init__(self):
        self.uid = app.config["BRE_UID"]
        self.logging_token = None
        self.token = None
        self.s = requests.Session()

    def _get(self, page):
        url = self.BASE + page
        r = self.s.get(url)
        print "[i] GET {} -> {}".format(page, r.status_code)
        if r.status_code != 200:
            raise Exception("return code %i" % r.status_code)
        return bs4.BeautifulSoup(r.text)

    def _post(self, page, data):
        url = self.BASE + page
        mdata = {}
        mdata["screenWidth"] = 1337
        mdata["screenHeight"] = 1337
        mdata["LOGGING_TOKEN"] = self.logging_token
        mdata["lang"] = ""
        mdata.update(data)
        r = self.s.post(url, mdata)
        print "[i] POST {} -> {}".format(page, r.status_code)
        if r.status_code != 200:
            raise Exception("return code %i" % r.status_code)
        return bs4.BeautifulSoup(r.text)

    def _gettoken(self, soup):
        # print soup
        menulinks = soup.findAll("a", "menulink")
        onclick = menulinks[0]["onclick"]
        self.token = re.search(r"TOKEN=([a-z0-9]+)", onclick).group(1)
        print "[i] Token: {}".format(self.token)

    def login(self, username, token):
        main = self._get("fragments/cua/login.jsp")
        self.logging_token = main.find("input", type="hidden", attrs={"name": "LOGGING_TOKEN"})["value"]

        data = {}
        data["TARGET"] = "/cualogin.do"
        data["RAWPASSWORD"] = token
        data["loginType"] = "token"
        data["LOGIN_OR_ALIAS"] = username
        logged = self._post("fragments/cua/login.fcc", data)
        self._gettoken(logged)

    def create_report(self):
        reportpage = self._get("main/navigate.do?templateId={}&to=newReport&org.apache.struts.taglib.html.TOKEN={}".format(self.uid, self.token))
        self._gettoken(reportpage)

        def generate_command(command, commandlist):
            data = {
                "synchronous": "on",
                "pagerOffset": 0,
                "pager.page": 0,
                "pager.newPage": 0,
                "org.apache.struts.taglib.html.TOKEN": self.token,
                "filter.orderByColumn": None,
                "filter.orderByAscending": "false",
                "commandlist": commandlist,
                "command": command,
            }
            return data

        def setparameter(item, value, extra=None):
            data = generate_command("editItem", "generate")
            data["selectedItemKey"] = item

            generate = self._post("report/generate/submitParameterList.do", data)
            self._gettoken(generate)

            data = {}
            data["value"] = value
            data["org.apache.struts.taglib.html.TOKEN"] = self.token
            data["commandlist"] = "ok"
            data["command"] = "ok"
            if extra:
                data.update(extra)

            specify = self._post("report/specify/submitParameter.do", data)
            self._gettoken(specify)

        setparameter("{}.0[account]".format(self.uid), 1060690633)
        setparameter("{}.0[from_date]".format(self.uid), "01.01.2001 00:00", {"predefiniedValue.selectedKey": "@empty", "valueTimePart": "00:00", "valueDatePart": "01.01.2001"})
        setparameter("{}.0[to_date]".format(self.uid), "", {"predefiniedValue.selectedKey": "@currentday", "valueTimePart": "", "valueDatePart": ""})

        data = generate_command("generate", "generate")
        data["selectedItemKey"] = "{}.0[to_date]".format(self.uid)
        submit_parameter_list = self._post("report/generate/submitParameterList.do", data)
        self._gettoken(submit_parameter_list)
        print "[i] Waiting..."
        time.sleep(3)
        data = {}
        data["org.apache.struts.taglib.html.TOKEN"] = self.token
        data["commandlist"] = "showReport"
        data["command"] = "showReport"
        report = self._post("report/generate/submitPleaseWait.do", data)
        self._gettoken(report)

        data = generate_command("export", "export")
        report_ready = self._post("report/submitReportReady.do", data)
        self._gettoken(report_ready)

        data = generate_command("processExport", "processExport")
        data["format.selectedKey"] = "dat"
        data["fileName"] = "raport"
        data["encoding.selectedKey"] = "iso"
        export = self._post("report/submitExport.do", data)
        self._gettoken(export)
        dlurl = re.search(r'openPopup\("(.+)"\);', str(export)).group(1)
        print "[i] Download popup URL: {}".format(dlurl)
        page = dlurl.replace("/mt/", "")
        dlpage = self._get(page)
        fileurl = "report/downloadExport.do?command=download"
        f = self.s.post(self.BASE + fileurl, dict(FileNumber=0), stream=True)
        return f.raw


if __name__ == "__main__":
    f = BREFetcher()
    f.login(raw_input("[?] ID: "), raw_input("[?] Token: "))
    print f.create_report().read()
