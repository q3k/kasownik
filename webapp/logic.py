"""The 'business' logic of the whole thing.
It updates database transfer rows based on BRE snapshots, and it also
tries to match transfers onto members, updating their payment status."""

from webapp import app, db
import banking
import models


def update_transfer_rows():
    f = open(app.config["BRE_SNAPSHOT_PATH"])
    parser = banking.BREParser()
    parser.parse(f)
    f.close()

    for row in parser.get_by_type("IN"):
        transfer = models.Transfer.query.filter_by(uid=row.uid).first()
        if not transfer:
            transfer = models.Transfer(None, row.uid,
                                       row.from_account,
                                       row.from_name,
                                       row.amount, row.title,
                                       row.time)
            db.session.add(transfer)
            print row.title
    db.session.commit()


def get_unmatched_transfers():
    return models.Transfer.query.filter_by(member_transfers=None).all()
