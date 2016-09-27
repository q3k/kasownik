# Copyright (c) 2015, Sergiusz Bazanski
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

"""An API to retrieve and set data in the Warsaw Hackerspce LDAP tree."""

import ldap

from flask import g

from webapp import mc, cache_enabled, app


def connect():
    c = ldap.initialize(app.config['LDAP_URI'])
    if 'LDAP_CA_PATH' in app.config:
        ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, app.config['LDAP_CA_PATH'])
    c.start_tls_s()
    c.simple_bind_s(app.config['LDAP_BIND_DN'],
                    app.config['LDAP_BIND_PASSWORD'])
    return c


@app.before_request
def _setup_ldap():
    g.ldap = connect()

@app.teardown_request
def _destroy_ldap(exception=None):
    ldap = getattr(g, 'ldap', None)
    if ldap:
        ldap.unbind_s()

def get_member_fields(c, member, fields):
    if isinstance(fields, str):
        fields = [fields,]
    fields_needed = set(fields)
    fields_out = {}
    if cache_enabled:
        for field in fields:
            field_cache = mc.get('kasownik-ldap-member-{}/{}'
                                 .format(member, field))
            if field_cache is not None:
                fields_out[field] = field_cache
                fields_needed.remove(field)

    member = member.replace('(', '').replace(')', '')
    lfilter = '(&(uid={}){})'.format(member, app.config['LDAP_USER_FILTER'])
    data = c.search_s(app.config['LDAP_USER_BASE'], ldap.SCOPE_SUBTREE,
                      lfilter, tuple(fields))
    for dn, obj in data:
        for k, v in obj.iteritems():
            v = v[0].decode('utf-8')
            if k in fields_needed:
                fields_out[k] = v
                if cache_enabled:
                    mc.set('kasownik-ldap-member-{}/{}'
                           .format(member, field), v)

    for k in fields_needed - set(fields_out.keys()):
        fields_out[k] = None

    return fields_out
