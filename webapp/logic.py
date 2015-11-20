# Copyright (c) 2015, Sergiusz Bazanski <q3k@q3k.org>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE 
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

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
                                       row.time,
                                       False)
            db.session.add(transfer)
    db.session.commit()


def get_unmatched_transfers():
    return models.Transfer.query.filter_by(member_transfers=None,ignore=False).all()
