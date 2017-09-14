import os
from ConfigParser import ConfigParser

''' load config '''
tmp_conf = ConfigParser()

tmp_path = os.path.dirname(os.path.abspath(__file__))  # /base/lib/here
tmp_path = tmp_path.split('/')
conf_path = '/'.join(tmp_path[0:-1])   # /base/lib
tmp_conf.read(conf_path+'/ampush.conf')

#tmp_conf.read('ampush.conf')
c = {}

c.update(tmp_conf.items('default'))
