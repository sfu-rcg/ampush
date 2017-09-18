import socket
import ldap
import os
import re

import conf, cnx, log

'''
Part of ampush. https://github.com/sfu-rcg/ampush
Copyright (C) 2016-2017 Research Computing Group, Simon Fraser University.
'''


def wait_for_replication(seconds=10):
    # cheap way to avoid duplicates (CNF:* objects)
    from time import sleep

    if conf.c['replication_wait_time']:
        seconds = float(conf.c['replication_wait_time'])

    log.m.debug('wait_for_replication: {0}s'.format(seconds))
    sleep(seconds)
    return


def check_hostname_resolves(hostname=None, map_name=None):
    try:
        socket.gethostbyname(hostname)
    except socket.error:
        log_msg = "Terminating. Can't resolve hostname {0} in {1}"
        log_msg = log_msg.format(hostname, map_name)
        log.m.critical(log_msg)
        exit(3)
    return


def file_exists(pathname=None):
    try:
        os.stat(pathname)
        return True
    except OSError:
        return False
    return


def verify_ff_am_dir_exists():
    t = conf.c['flat_file_map_dir']
    if file_exists(t) is not True:
        log_msg = 'Terminating. Flat file map directory {0} does not exist'
        log_msg = log_msg.format(t)
        log.m.critical(log_msg)
        print(log_msg)
        exit(12)
    return


def verify_ff_master_exists():
    t = '{0}/{1}'.format(conf.c['flat_file_map_dir'],
                         conf.c['master_map_name'])
    if file_exists(t) is not True:
        log_msg = 'Terminating. Master map {0} does not exist'.format(t)
        log.m.critical(log_msg)
        print(log_msg)
        exit(13)
    return


def cn_split(in_str):
    l_tmp = in_str.split(',')
    l_final = []
    for x in l_tmp:
        x = re.sub('^cn=', '', x)
        l_final.append(x)
    return l_final


def map_cn(in_str):
    return 'cn=' + in_str + ',' + conf.c['am_container']


def dry_msg(in_str=None, dry_run=None):
    ''' Prepend log messages with [dry run] if we're in dry run mode. '''
    if dry_run is None:
        raise Exception('dry_msg: dry_run arg is required')

    if dry_run is True:
        return '[dry run] ' + in_str
    else:
        return in_str


def validate_mount_options(opt_str=None, map_name=None, am_key=None):
    ''' Rudimentary validation. Tweak to taste. '''
    if not re.match(r'^-.*$', opt_str):
        log_msg = 'Terminating. Bad mount options in {0}/{1}: {2}'
        log_msg = log_msg.format(map_name, am_key, opt_str)
        log.m.critical(log_msg)
        print(log_msg)
        exit(9)
    return


def validate_nis_map_entry(in_list=None, am_key=None, map_name=None,
                           map_type=None):
    '''
Ensure that automount map entries have two components (key + server:path)
or three components (key + mount options + server:path).
    '''
    if len(in_list) < 1 and len(in_list) > 2:
        log_msg = "Terminating. Unexpected format in {0} map {1}: {2} - {3}"
        log_msg = log_msg.format(map_type, map_name, am_key, ' '.join(in_list))
        log.m.critical(log_msg)
        print(log_msg)
        exit(8)

    # the last chunk should contain a server:path pair
    if not re.match(r'.*:.*', in_list[-1]):
        log_msg = 'Terminating. No server:path specified in {0}:{1}'
        log_msg = log_msg.format(map_name, am_key)
        log.m.critical(log_msg)
        print(log_msg)
        exit(2)
    return


def strip_slash(in_str):
    ''' Strip leading slash from a string. '''
    return re.sub(r'^/', '', in_str)


def has_slash_prefix(in_str):
    if re.match(r'^/.*', in_str):
        return True
    else:
        return False


def master_map_sanity_checks(map_dict=None, map_type=None):
    ''' Screen master map for simple format errors. '''
    map_name = conf.c['master_map_name']

    if map_type == 'Active Directory':
        return

    for k, v in map_dict.items():
        joined = '{0} {1}'.format(k, v['map'])

        # required: leading slash for all entries
        if not re.match(r'^/', k):
            log_msg = 'Terminating. No leading slash in {1} {2}:{3}'
            log_msg = log_msg.format(map_type, map_name, joined)
            log.m.critical(log_msg)
            print(log_msg)
            exit(4)

    # all submaps mentioned here should exist on the filesystem
    submap_path = conf.c['flat_file_map_dir'] + '/' + map_name
    if file_exists(submap_path) is False:
        log_msg = 'Terminating. Master map refers to nonexistent file {0}'
        log_msg = log_msg.format(submap_path)
        log.m.critical(log_msg)
        exit(5)
    return


def submap_sanity_checks(map_dict=None, map_name=None, map_type=None):
    if map_dict is None:
        log_msg = 'Nonexistent {0} map {1}. Skipping validation.'
        log_msg = log_msg.format(map_type, map_name)
        log.m.debug(log_msg)
        return

    for k, v in map_dict.items():
        joined = '{0} {1}:{2}'.format(k, v['server_hostname'], v['server_dir'])

        if not re.match(r'.*\..*', v['server_hostname']):
            log.m.warning('Non-FQHN found: ' + joined)

        if 'options' not in v:
            log_msg = 'No mount options specified: ' + joined
            log.m.warning(log_msg)

        '''
direct map keys are absolute filesystem paths, so verify that a leading
slash is present
        '''
        if k == conf.c['direct_map_name']:
            if not re.match(r'^/', k):
                log_msg = 'Terminating. No leading slash in direct map key: ' \
                          + joined
                log.m.critical(log_msg)
                print(log_msg)
                exit(1)
    return


def map_to_text(in_d=None, map_name=None):
    l = []
    for k, v in in_d.items():
        if 'options' not in v:
            opts = ''
        else:
            opts = v['options']

        if map_name == conf.c['master_map_name']:
            s = "{0}\t\t{1}\t{2}"
            s = s.format(k,
                         v['map'],
                         opts)
        else:
            s = "{0}\t\t{1} {2}:{3}"
            s = s.format(k,
                         opts,
                         v['server_hostname'],
                         v['server_dir'])
        l.append(s)
    return l


def ff_map_to_list(pathname=None):
    out = []
    f = open(pathname)

    for l in f:
        l.rstrip()  # chomp
        # skip comments and blank lines
        if re.match(r'^#', l):
            continue
        if len(l) < 2:
            continue
        out.append(l)
    f.close()
    return out
