""" Use python-ad and GSSAPI/Kerberos to connect to AD. """

# requires python-ad: https://github.com/sfu-rcg/python-ad
try:
    from ad import Client, Creds, activate
except ImportError:
    raise Exception("python-ad package required.")

try:
    import ldap
except ImportError:
    raise Exception("python-ldap package required.")



from amlib import conf

ad_user = conf.c['am_user']+'@'+conf.c['ad_domain']
ad_pass = conf.c['am_pass']
creds = Creds(conf.c['ad_domain'])

creds.acquire(principal=ad_user, password=ad_pass)
activate(creds)
c = Client(conf.c['ad_domain'])
