import logging
from logging import handlers
import utils, conf
from datetime import datetime

# m = main log
m = logging.getLogger('main')
m_handler = logging.FileHandler(filename=conf.c['main_logfile'])
m.setLevel(int(conf.c['main_loglevel'])-1)  # INFO and above
fmt = logging.Formatter(fmt='%(asctime)s %(message)s',
                        datefmt='%b %e %Y %H:%M:%S')
m_handler.setFormatter(fmt)
m.addHandler(m_handler)
