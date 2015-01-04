"""An API to retrieve and set data in the Warsaw Hackerspce LDAP tree."""

import ldap

from flask import g

from webapp import mc, cache_enabled, app


def connect():
    c = ldap.initialize(app.config['LDAP_URI'])
    c.start_tls_s()
    c.simple_bind_s(app.config['LDAP_BIND_DN'],
                    app.config['LDAP_BIND_PASSWORD'])
    return c


@app.before_request
def _setup_ldap():
    g.ldap = connect()

@app.teardown_request
def _destroy_ldap(exception=None):
    g.ldap.unbind_s()

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
