from flask import Flask, request
from optparse import OptionParser
import MySQLdb
import ConfigParser
import os

app = Flask(__name__, static_url_path='', static_folder='.')
application = app


def create_db_connnection():
    try:
        app.config['host']
    except KeyError:
        getConfig()

    return MySQLdb.connect(host=app.config['host'],
        user=app.config['username'],
        passwd=app.config['password'],
        db=app.config['database'])
        
def getConfig():
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

    app.config.update({
        'username': parser.get('alerts', 'username'),
        'password': parser.get('alerts', 'password'),
        'host': parser.get('alerts', 'host'),
        'database': parser.get('alerts', 'database'),
        'maildir': parser.get('alerts', 'maildir'),
        'DEBUG': parser.getboolean('alerts', 'debug'),
    })




