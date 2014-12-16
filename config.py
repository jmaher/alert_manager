#!/usr/bin/env python
import ConfigParser

from optparse import OptionParser
import os
import sys
from pyLibrary.cnv import CNV
from pyLibrary.struct import nvl
from pyLibrary.times.dates import Date

filename = 'config.ini'
db_host = 'database'
db_name = 'alerts'
maildir = 'var/spool/news/mozilla/dev/tree-management'
debug = 'true'
parser = OptionParser()
parser.add_option("-u", "--username",
                  type="string", default="root",
                  help="username for connecting to the sql server")
parser.add_option("-p", "--password",
                  type="string", default="",
                  help="password for connecting to the sql server")


def db_config():
    (opts, args) = parser.parse_args()
    with open(filename, 'w') as target:
        target.write("[alerts]\n")
        target.write("host = %s\n" % db_host)
        target.write("database = %s\n" % db_name)
        target.write("username = %s\n" % opts.username)
        target.write("password = %s\n" % opts.password)
        target.write("maildir = %s\n" % maildir)
        target.write("debug = %s\n" % debug)


def get_config():
    op = OptionParser()
    op.add_option("--config",
        action="store", type="string", dest="config",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini'),
        help="path to the config file [config.ini]")

    options, args = op.parse_args()

    if not os.path.exists(options.config):
        print "ERROR: %s doesn't exist" % (os.path.abspath(options.config))
        sys.exit(1)

    parser = ConfigParser.RawConfigParser(defaults={'debug': 'false'})
    parser.read(options.config)

    def now():
        return Date.eod().value

    def today():
        return Date.today().value

    try:
        const = CNV.string2datetime(parser.get('alerts', 'now'))

        def now():
            return const

        today = now
    except Exception:
        pass


    return {
        'username': parser.get('alerts', 'username'),
        'password': parser.get('alerts', 'password'),
        'host': parser.get('alerts', 'host'),
        'database': parser.get('alerts', 'database'),
        'maildir': parser.get('alerts', 'maildir'),
        'now': now,
        'today': today,
        'DEBUG': parser.getboolean('alerts', 'debug'),
    }




if __name__ == '__main__':
    db_config()
