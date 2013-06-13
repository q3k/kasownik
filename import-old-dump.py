import re
import datetime

import webapp

# yes, I am in fact importing an old sqlite dump with regexp
# deal with it
f = open('olddata', 'r')
d = f.read()
f.close()

def fancysplit(s):
    parts = []
    part = ""
    pi = 0
    escaped = False
    for c in s:
        if pi == 0 and c == "'":
            escaped = True
        elif pi > 0 and c == "'":
            escaped = False
        elif not escaped and c == ",":
            parts.append(part)
            part = ""
            pi = -1
            escaped = False
        else:
            part += c
        pi += 1
    if part != "":
        parts.append(part)
    return parts


records = {}
for line in d.split("\n"):
    m = re.match(r'^INSERT INTO "([a-z_]+)" ', line)
    if m:
        table_name = m.group(1)
        if table_name not in records:
            records[table_name] = []
        m = re.search("VALUES\((.+)\);", line)
        values_s = m.group(1)
        values_r = [v.strip("'").decode("utf-8") for v in fancysplit(values_s)]
        values = []
        for v in values_r:
            try:
                vales.append(int(v))
            except:
                values.append(v)
        records[table_name].append(tuple(values))

for member_id, member_name, member_type, member_active in records["_members"]:
    m = webapp.models.Member(member_id, member_name, member_type, True if member_active == 1 else False)
    webapp.db.session.add(m)

for _id, uid, account_from, name_from, amount, title, date in records["_transfers"]:
    date = datetime.datetime.strptime(date, "20%y-%m-%d %H:%M:%S")
    t = webapp.models.Transfer(_id, uid, account_from, name_from, amount, title, date)
    webapp.db.session.add(t)

webapp.db.session.commit()

for _id, transfer_id, member_id, year, month in records["_member_transfer"]:
    member = webapp.models.Member.query.get(member_id)
    transfer = webapp.models.Transfer.query.get(transfer_id)
    mt = webapp.models.MemberTransfer(_id, year, month, transfer)
    member.transfers.append(mt)

webapp.db.session.commit()