import ldap
import conf, cnx, log, utils
import ldap.modlist as modlist

'''
Functions for manipulating AD objects with python-ad.
Part of ampush. https://github.com/sfu-rcg/ampush
Copyright (C) 2016 Research Computing Group, Simon Fraser University.
'''



def get(cn=None, scope=ldap.SCOPE_SUBTREE):
    ''' Return one or more objects from Active Directory. '''
    try:
        return cnx.c.search(base=cn)
    except ldap.NO_SUCH_OBJECT:
        return None
    return


def verify_am_container_exists():
    if get(conf.c['am_container']) is None:
        log_msg = 'Terminating. Automount container {0} does not exist in AD'
        log_msg = log_msg.foramt(conf.c['am_container'])
        log.m.critical(log_msg)
        print(log_msg)
        exit(11)
    return


def add_obj(dn=None, debug_attrs=None, attrs=None, dry_run=True):
    log_msg = 'ad_create ' + str(debug_attrs)
    log_msg = utils.dry_msg(log_msg, dry_run=dry_run)
    log.m.debug(log_msg)

    if dry_run is False:
        try:
            cnx.c.add(dn=dn, attrs=attrs)
        except ldap.ALREADY_EXISTS:
            log_msg = 'WARNING: Domain controller says {0} already exists'
            log_msg = log_msg.format(dn)
            log.m.warning(log_msg)
    return


def _del(cn=None, dry_run=True):
    log_msg = 'ad_delete ' + cn
    log_msg = utils.dry_msg(log_msg, dry_run=dry_run)
    log.m.info(log_msg)

    if dry_run is False:
        cnx.c.delete(dn=cn)
    return


def delete(cn=None, recurse=False, dry_run=True):
    if recurse is False:
        _del(cn=cn, dry_run=dry_run)
    else:
        '''
Delete contents of the auto.x container. Use SCOPE_ONELEVEL
because we want to delete the contents of the container first,
then the container itself.
        '''
        objs = get(cn=cn, scope=ldap.SCOPE_ONELEVEL)
        for obj in objs[1:]:  # skip parent container
            # obj[0] is e.g., 'cn=supermnt,cn=auto.foo,cn=automounts,...'

            # these are just here to make pretty logs.
            map_entry = utils.cn_split(obj[0])[0]
            map_name = utils.cn_split(obj[0])[1]
            log_msg = 'Delete {0} from AD:{1}'.format(map_entry, map_name)
            log_msg = utils.dry_msg(log_msg, dry_run=dry_run)
            log.m.info(log_msg)

            _del(cn=obj[0], dry_run=dry_run)

        # delete parent object
        map_name = utils.cn_split(cn)[0]
        log_msg = 'Delete AD:' + map_name
        log_msg = utils.dry_msg(log_msg, dry_run=dry_run)
        _del(cn=cn, dry_run=dry_run)
    return


def create_map_entry(map_name=None, entry_k=None, entry_v=None, dry_run=True):
    ''' Create a nisObject in AD. One nisObject = one automount entry. '''

    dn = 'cn={0},{1}'.format(utils.strip_slash(entry_k),
                             utils.map_cn(map_name))
    # log.m.debug('create nisObject: ' + dn)

    # Format nisMapEntry. new_opts => new_entry => nisMapEntry
    new_opts = ''
    if entry_v['options'] is not None:  # options are optional. go figure.
        new_opts = entry_v['options']
    if map_name == conf.c['master_map_name']:  # auto.net -rw,intr,bg
        new_entry = '{0} {1}'.format(entry_v['map'], new_opts)
    else:  # nisMapEntry: -nosuid,intr,bg,tcp,vers=3 server:path
        new_entry = '{0} {1}:{2}'.format(new_opts,
                                         entry_v['server_hostname'],
                                         entry_v['server_dir'])

    # Form LDIF.
    attrs = {}
    attrs['objectClass'] = ['top', conf.c['t_nisobj']]
    attrs['cn'] = [utils.strip_slash(entry_k)]
    attrs['name'] = [utils.strip_slash(entry_k)]
    attrs['nisMapName'] = [entry_k]
    attrs['nisMapEntry'] = [new_entry.strip()]

    '''
Master and direct map entries: leading slash in nisMapName. Nowhere else.
We will be passed one leading slash because that's what we read
from the flat file master map.

All other entries: sync.map_contents ensures that no slashes get passed here.
The ONLY place where a slash should appear is in the directory half of the
server:path pair.
    '''
    if map_name is not conf.c['master_map_name'] and \
       map_name is not conf.c['direct_map_name']:
        attrs['nisMapName'] = [utils.strip_slash(entry_k)]

    ml = modlist.addModlist(attrs)
    add_obj(dn=dn,
            debug_attrs=attrs,
            attrs=ml,
            dry_run=dry_run)
    return
