import os
import re
from amlib import conf, utils, log

'''
Functions for parsing AD automount maps into a common dict format.
Part of ampush. https://github.com/sfu-rcg/ampush
Copyright (C) 2016 Research Computing Group, Simon Fraser University.
'''

# ff = flat file automount map

def get_names():
    '''
Return a list of files in ${conf/flat_file_map_dir} with the master map and
(optional) direct map first.
    '''

    l_names, fs_map_names = [], []

    for root, dirs, filenames in os.walk(conf.c['flat_file_map_dir']):
        for map_name in filenames:
            fs_map_names.append(map_name)

    # ensure the master map and direct map (if one exists) are processed first
    l_names.append(conf.c['master_map_name'])

    try:
        fs_map_names.remove(conf.c['master_map_name'])
    except ValueError:
        log_msg = '{0} does not exist on the filesystem. Terminating.'
        log_msg = log_msg.format(conf.c['master_map_name'])
        log.m.critical(log_msg)
        print(log_msg)
        exit(6)

    if conf.c['direct_map_name'] in fs_map_names:
        l_names.append(conf.c['direct_map_name'])
        fs_map_names.remove(conf.c['direct_map_name'])

    fs_map_names.sort()

    for map_name in fs_map_names:
        if re.match(r'^auto\.', map_name):
            l_names.append(map_name)

    return l_names


def detect_orphans():
    '''
Return a list of maps that exist on the filesystem but are not mentioned
in auto.master.
    '''

    master_entries = parse(conf.c['master_map_name'])
    master_mapnames = []
    l_orphans = []

    for k, v in master_entries.items():
        master_mapnames.append(v['map'])

    for ff_mapname in get_names():
        # auto.master should not be listed in auto.master
        if (ff_mapname not in master_mapnames and
                ff_mapname != 'auto.master'):
            l_orphans.append(ff_mapname)

    if len(l_orphans) > 0:
        l_orphans.sort()
        log_msg = 'Found unused maps listed in {0}: {1}'
        log_msg = log_msg.format(conf.c['master_map_name'],
                                 ' '.join(l_orphans))
        log.m.warning(log_msg)
        print(log_msg)
    return


def parse_master(map_lines=None, map_name=None):
    '''
Ingest master map as a list of strings. Return a nice dict like this:
{'/-': {'map': 'auto.direct', 'options': '-rw,intr,soft,bg'},
 '/foo': {'map': 'auto.foo', 'options': '-rw,intr,soft,bg'},
 '/bar': {'map': 'auto.bar', 'options': '-rw,intr,soft,bg'},
 '/baz': {'map': 'auto.baz',
      'options': '-ro,int,soft,bg,fstype=nfs4,port=2049'},}
    '''
    d_map = {}

    for l in map_lines:
        chunks = l.split()
        am_key = chunks[0]
        joined = ' '.join(chunks)
        d_map[am_key] = {}
        '''
As with submaps the mount options field is optional.
2 fields == automount entry without mount options.
        '''
        if len(chunks) == 2:
            d_map[am_key] = {'map': chunks[1]}
            log_msg = 'No mount options for {0} in {1}'
            log_msg = log_msg.format(am_key, conf.c['master_map_name'])
            log.m.info(log_msg)

        # 3 fields? automount directory + mapname + mount options
        elif len(chunks) == 3:
            d_map[am_key] = {'map': chunks[1],
                             'options': chunks[2]}

        else:
            log_msg = (
                'Terminating. Bad flat file master map format: '
                'unexpected number of fields in ' + joined
            )
            log.m.critical(log_msg)
            print(log_msg)
            exit(11)
    return d_map


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

    log_msg = 'Reading {0}/{1}'.format(conf.c['flat_file_map_dir'],
                                       map_name)
    log.m.debug(log_msg)

    for l in map_lines:
        chunks = l.split()
        am_key = chunks[0]  # automount key
        utils.validate_nis_map_entry(in_list=chunks[1:],
                                     map_name=map_name,
                                     am_key=am_key,
                                     map_type='flat file')
        d_map[am_key] = {}

        '''
Consider these two valid automount entries:
    apps -tcp,vers=3 nfs-server1.example.com:/exports/apps
    data nfs-server2.example.com:/srv/data

If a third field exists, use it as the NFS path.
Otherwise use the second field as the NFS path.
        '''

        try:  # server:path pair with options
            server_hostname = chunks[2].split(':')[0]
            server_dir = chunks[2].split(':')[1]
            options = chunks[1]
            utils.validate_mount_options(opt_str=options,
                                         map_name=map_name,
                                         am_key=am_key)
            d_map[am_key] = {'server_hostname': server_hostname,
                             'server_dir': server_dir,
                             'options': options}
        except IndexError:  # without options
            server_hostname = chunks[1].split(':')[0]
            server_dir = chunks[1].split(':')[1]
            d_map[am_key] = {'server_hostname': server_hostname,
                             'server_dir': server_dir,
                             'options': None}
    return d_map


def parse(map_name=None):
    '''
Read flat file automount maps ${ampush.conf/flat_file_map_dir} and
pass map names to parser_master_map or parse_submap.
    '''

    map_pathname = conf.c['flat_file_map_dir'] + '/' + map_name
    map_lines = utils.ff_map_to_list(map_pathname)
    map_type = 'flat file'

    # different map types (master, direct, plain) == different sanity checks
    if map_name == conf.c['master_map_name']:
        d_map = parse_master(map_name=map_name,
                             map_lines=map_lines)
        utils.master_map_sanity_checks(map_dict=d_map,
                                       map_type=map_type)
    else:
        d_map = parse_submap(map_name=map_name,
                             map_lines=map_lines)
        utils.submap_sanity_checks(map_dict=d_map,
                                   map_type=map_type)
    return d_map
