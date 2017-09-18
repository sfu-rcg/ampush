import re
from amlib import argp, conf

'''
read data from flat file automount tables =>
  roll-your-own custom code for manipulating that data
  [you are here] => push data into AD

Part of ampush. https://github.com/sfu-rcg/ampush
Copyright (C) 2017 Research Computing Group, Simon Fraser University.
'''


def munge(map_name=None, map_meat=None):
    # do funky things with your automount maps here

    ''' IN:
    map_name = e.g., auto.software

    map_meat = whatever is in your flat file maps, in a dict--e.g.,
    {'docs': {'options': '-tcp,vers=3',
              'server_dir': '/exports/docs',
              'server_hostname': 'sparcstation20.example.com'},

     'installers': {'options': '-intr,vers=4,port=2049,timeo=10,sec=krb5i',
                    'server_dir': '/isos',
                    'server_hostname': 'svm-nfs1.example.com}, ...}
    '''
    return map_meat  # dict
