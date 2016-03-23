from ConfigParser import ConfigParser

''' load config '''
tmp_conf = ConfigParser()
tmp_conf.read('ampush.conf')
c = {}

c.update(tmp_conf.items('default'))
