import os
from ConfigParser import ConfigParser
from amlib import argp

tmp_conf = ConfigParser()
tmp_path = os.path.dirname(os.path.abspath(__file__))  # /base/lib/here
tmp_path = tmp_path.split('/')
conf_path = '/'.join(tmp_path[0:-1])   # /base/lib
tmp_conf.read(conf_path+'/ampush.conf')
c = {}
c.update(tmp_conf.items('default'))

# select target AD container: default or user-specified with --mode?
if argp.a['mode'] is not None:
    try:
        container_conf_key = 'am_container_' + argp.a['mode']
        c['am_container'] = c[container_conf_key]
    except KeyError:
        log_msg = 'Terminating. No such parameter in ampush.conf: ' + \
                  container_conf_key
        raise Exception(log_msg)
else:
    c['am_container'] = c['am_container_default']


# select alternate flat file automount maps: default or user-specified
# set passed via --source?
if argp.a['source'] is not None:
    try:
        ff_map_dir_conf_key = 'flat_file_map_dir_' + argp.a['source']
        c['flat_file_map_dir'] = c[ff_map_dir_conf_key]
    except KeyError:
        log_msg = 'Terminating. No such parameter in ampush.conf: ' + \
                  ff_map_dir_conf_key
        raise Exception(log_msg)
else:
    c['flat_file_map_dir'] = c['flat_file_map_dir_default']
