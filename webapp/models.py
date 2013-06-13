from webapp import db


class MemberTransfer(db.Model):
    __tablename__ = "member_transfer"
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"))
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
    type = db.Column(db.Enum("starving", "fatty"))
    transfers = db.relationship("MemberTransfer", backref="members")
    active = db.Column(db.Boolean)

    def __init__(self, _id, _username, _type, _active):
        self.id = _id
        self.username = _username
        self.type = _type
        self.active = _active


class Transfer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(16))
    account_from = db.Column(db.String(32))
    name_from = db.Column(db.String(64))
    amount = db.Column(db.Integer)
    title = db.Column(db.String(64))
    date = db.Column(db.Date)

    def __init__(self, _id, _uid, _account_from, _name_from, _amount, _title, _date):
        self.id = _id
        self.uid = _uid
        self.account_from = _account_from
        self.name_from = _name_from
        self.amount = _amount
        self.title = _title
        self.date = _date