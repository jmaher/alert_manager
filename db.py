from flask import Flask
from pymysql import connect
from flask.ext.compress import Compress
from config import get_config

app = Flask(__name__, static_url_path='', static_folder='.')
Compress(app)


def create_db_connnection():
    try:
        app.config['host']
    except KeyError:
        getConfig()

    return connect(host=app.config['host'],
        user=app.config['username'],
        passwd=app.config['password'],
        db=app.config['database'])


def getConfig():
    configuration = get_config()

    app.config.update(configuration)




