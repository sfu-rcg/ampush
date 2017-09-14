import re
import ldap
from amlib import conf, utils, log, cnx

'''
Functions for parsing AD automount maps into a common dict format.
Part of ampush. https://github.com/sfu-rcg/ampush
Copyright (C) 2016-2017 Research Computing Group, Simon Fraser University.
'''


'''
adm = Active Directory automount map

Assuming a structure like this

{AD root}
{AD root}/OU=Unix
{AD root}/OU=Unix/CN=automounts
{AD root}/OU=Unix/CN=automounts/auto.master
{AD root}/OU=Unix/CN=automounts/auto.master/foobar
{AD root}/OU=Unix/CN=automounts/auto.foobar
{AD root}/OU=Unix/CN=automounts/auto.foobar/baz
                -nointr,tcp,bg,vers=3 baz.nfs.example.org:/supermnt


querying a list of nisMap/nisObjects from LDAP/AD should return results in
this format (extraneous fields removed):

[('CN=automounts,OU=Unix,DC=example,DC=org',
  {'cn': ['automounts'],
 ('CN=auto.foobar,CN=automounts,OU=Unix,DC=example,DC=org',
  {'cn': ['auto.foobar'],
   'nisMapName': ['auto.foobar'],
 ('CN=baz,CN=auto.foobar,CN=automounts,OU=Unix,DC=example,DC=org',
  {'cn': ['baz'],
   'nisMapEntry': ['-nointr,tcp,bg,vers=3 baz.nfs.example.org:/supermnt'],
   'nisMapName': ['baz'],
 ('CN=auto.master,CN=automounts,OU=Unix,DC=example,DC=org',
  {'cn': ['auto.master'],
   'nisMapName': ['auto.master'],
 ('CN=foobar,CN=auto.master,CN=automounts,OU=Unix,DC=example,DC=org',
  {'cn': ['foobar'],
   'nisMapEntry': ['auto.foobar'],
   'nisMapName': ['foobar'],})]
'''


def get_names():
    '''
Return a list of automount maps in AD/${conf/am_container} with auto.master
and auto.direct first.
    '''
    l_names, ad_map_names = [], []

    try:
        results = cnx.c.search(filter='(cn=*)', base=conf.c['am_container'],
                               scope=ldap.SCOPE_ONELEVEL)  # exclude parent cn
    except ldap.NO_SUCH_OBJECT:
        log_msg = "Can't find automount container in AD: {0}. Terminating."
        log_msg = log_msg.format(conf.c['am_container'])
        log.m.critical(log_msg)
        print(log_msg)
        exit(7)

    for obj in results:
        ad_map_names.append(obj[1]['cn'][0])

    l_names.append(conf.c['master_map_name'])

    try:
        ad_map_names.remove(conf.c['master_map_name'])
    except ValueError:
        log_msg = '{0} does not exist in AD. Terminating.'
        log_msg = log_msg.format(conf.c['master_map_name'])
        log.m.critical(log_msg)
        print(log_msg)
        exit(19)

    if conf.c['direct_map_name'] in ad_map_names:
        l_names.append(conf.c['direct_map_name'])
        ad_map_names.remove(conf.c['direct_map_name'])

    ad_map_names.sort()

    for map_name in ad_map_names:
        if re.match(r'^auto\.', map_name):
            l_names.append(map_name)

    return l_names


def parse_submap(map_name=None, map_lines=None):
    '''
Ingest a list of automount map entries. Return a nice dict like this:

{'yuv': {'options':          '-intr,bg,tcp,vers=4',
         'server_dir':       '/yuv',
         'server_hostname':  'nfssrv01.example.com'},
 'luma': {'options':         '-nosuid,tcp,intr,bg,vers=3,rw',
          'server_dir':      '/exports/luma',
          'server_hostname': 'nfssrv02.example.com'}, ...}
    '''
    d_map = {}

    am_cn = 'cn={0},{1}'.format(map_name, conf.c['am_container'])
    log.m.debug('Reading ' + am_cn)

    try:
        results = (cnx.c.search(filter='(cn=*)',
                                base=am_cn,
                                scope=ldap.SCOPE_SUBTREE))
    except ldap.NO_SUCH_OBJECT:
        return None

    for row in results[1:]:  # skip the container itself
        if utils.has_slash_prefix(row[1]['cn'][0]) is True:
            log_msg = (
                'AD:{0}=>{1} has a leading slash in its CN. This is bad. '
                'Something has gone horribly wrong and you should file '
                'a bug. Please include your flat file automount maps '
                'with anonymized hostnames.'
            ).format(map_name, row[1]['cn'][0])
            log.m.critical(log_msg)
            print(log_msg)
            exit(5)

        '''
When providing a view of the AD map, use cn rather than nisMapName
to avoid returning a leading slash when parsing common maps.

For the direct map, which will have a leading slash in the flat
file equivalent, return nisMapName for easy comparison.
        '''
        if map_name == conf.c['direct_map_name']:
            am_key = row[1]['nisMapName'][0]
        else:
            am_key = row[1]['cn'][0]

        chunks = row[1]['nisMapEntry'][0].split()
        utils.validate_nis_map_entry(in_list=chunks,
                                     map_name=map_name,
                                     am_key=am_key,
                                     map_type='Active Directory')
        d_map[am_key] = {}

        '''
Consider these two valid automount entries:
    apps -tcp,vers=3 nfs-server1.example.com:/exports/apps
    data nfs-server2.example.com:/srv/data

If a third field exists, use it as the NFS path.
Otherwise use the second field as the NFS path.
        '''
        try:  # server:path pair with options
            server_hostname, server_dir = chunks[1].split(':')
            options = chunks[0]
            utils.validate_mount_options(opt_str=options,
                                         map_name=map_name,
                                         am_key=am_key)
            d_map[am_key] = {'options': options,
                             'server_hostname': server_hostname,
                             'server_dir': server_dir}
        except IndexError:  # without options
            server_hostname, server_dir = chunks[0].split(':')
            d_map[am_key] = {'options': None,
                             'server_hostname': server_hostname,
                             'server_dir': server_dir}
    return d_map


def parse_master():
    '''
Ingest master map from AD. Return a nice dict like this:

{'/-': {'map': 'auto.direct', 'options': '-rw,intr,soft,bg'},
 '/foo': {'map': 'auto.foo', 'options': '-rw,intr,soft,bg'},
 '/bar': {'map': 'auto.bar', 'options': '-rw,intr,soft,bg'},
 '/baz': {'map': 'auto.baz',
      'options': '-ro,int,soft,bg,fstype=nfs4,port=2049'},}

Note the leading slashes on the keys. We add them there for
easy comparison with the flat file master map. All map entries
outside of the master map should be returned without leading
slashes.
    '''
    map_name = conf.c['master_map_name']
    d_map = {}

    am_cn = 'cn={0},{1}'.format(map_name, conf.c['am_container'])
    log.m.debug('Reading ' + am_cn)

    try:
        results = (cnx.c.search(filter='(cn=*)',
                                base=am_cn,
                                scope=ldap.SCOPE_SUBTREE))
    except ldap.NO_SUCH_OBJECT:
        return None

    for row in results[1:]:  # skip the container itself
        am_key = row[1]['nisMapName'][0]
        chunks = row[1]['nisMapEntry'][0].split()
        d_map[am_key] = {}
        joined = '{0}:{1}'.format(am_key, row[1]['nisMapEntry'][0])
        '''
As with submaps the mount options field is optional.
1 field == automount entry without mount options.
        '''
        if len(chunks) == 1:
            d_map[am_key] = {'map': chunks[0]}
            log_msg = 'No mount options for {0} in {1}'
            log_msg = log_msg.format(am_key, conf.c['master_map_name'])
            log.m.info(log_msg)

        # 3 fields? automount directory + mapname + mount options
        elif len(chunks) == 2:
            d_map[am_key] = {'map': chunks[0],
                             'options': chunks[1]}

        else:
            log_msg = (
                'Terminating. Bad Active Directory master map format: '
                'unexpected number of fields in ' + joined
            )
            log.m.critical(log_msg)
            print(log_msg)
            exit(10)

    return d_map


def parse(map_name=None):
    '''
Read automount maps from Active Directory:${ampush.conf/am_container}
pass map names to parser_master_map or parse_submap.
    '''
    map_type = 'Active Directory'

    # different map types (master, direct, plain) == different sanity checks
    if map_name == conf.c['master_map_name']:
        d_map = parse_master()
        utils.master_map_sanity_checks(map_dict=d_map,
                                       map_type=map_type)
    else:
        d_map = parse_submap(map_name=map_name)
        utils.submap_sanity_checks(map_dict=d_map,
                                   map_name=map_name,
                                   map_type=map_type)
    return d_map
