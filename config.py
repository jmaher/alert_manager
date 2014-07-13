#!/usr/bin/env python

from optparse import OptionParser

filename = 'config.ini'
db_host = 'localhost'
db_name = 'alerts'
maildir = '/var/spool/news/mozilla/dev/tree-management'
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

if __name__ == '__main__':
    db_config()
