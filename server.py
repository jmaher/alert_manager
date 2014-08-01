#!/usr/bin/env python

import os
import json
import sys
import requests
from flask import Flask, request
from functools import wraps
from datetime import date, timedelta
import MySQLdb
import ConfigParser
from optparse import OptionParser

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


def serialize_to_json(object):
    """Serialize class objects to json"""
    try:
        return object.__dict__
    except AttributeError:
        raise TypeError(repr(object) + 'is not JSON serializable')


def json_response(func):
    """Decorator: Serialize response to json"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        return json.dumps(result or {'error': 'No data found for your request'},
                          default=serialize_to_json)
    return wrapper


def run_query(where_clause, body=False):
    db = create_db_connnection()
    cursor = db.cursor()

    fields = ['id', 'branch', 'test', 'platform', 'percent', 'graphurl', 'changeset', 'keyrevision', 'bugcount', 'comment', 'bug', 'status', 'email', 'date', 'mergedfrom', 'duplicate', 'tbplurl']
    if body:
        fields.append('body')
    cursor.execute("""select %s from alerts %s;""" % (', '.join(fields), where_clause))

    alerts = cursor.fetchall()

    retVal = []
    for alert in alerts:
        data = {}
        i = 0
        while i < len(fields):
            data[fields[i]] = alert[i]
            if fields[i] == 'date':
                data[fields[i]] = str(alert[i])
            i += 1
        retVal.append(data)
    return retVal

@app.route('/alert')
@json_response
def run_alert_query():
    inputid = request.args['id']
    return { 'alerts': run_query("where id=%s" % inputid, True) }

@app.route('/bugzilla_reports')
@json_response
def run_bugzilla_query():
    query_dict = request.args.to_dict()
    date = query_dict['date']
    url = 'https://bugzilla.mozilla.org/rest/bug'
    if date == "none":
        u = url +"?whiteboard=[talos_regression]&status:RESOLVED&include_fields=id,status,resolution,creation_time,cf_last_resolved"
    else:
        u = url +"?whiteboard=[talos_regression]&status:RESOLVED&creation_time="+date+"&include_fields=id,status,resolution,creation_time,cf_last_resolved"
    search_results = requests.get(u)
    return { 'bugs': search_results.text }

@app.route('/graph/flot')
@json_response
def run_graph_flot_query():
    query_dict = request.args.to_dict()
    startDate = query_dict['startDate']
    endDate = query_dict['endDate']
    if endDate != "none" and startDate == "none":
        dateElements = endDate.split('-')
        endDate = date(int(dateElements[0]),int(dateElements[1]),int(dateElements[2]))

    db = create_db_connnection()
    cursor = db.cursor()
    if endDate == "none":
        endDate = date.today()
    if startDate == "none":
        startDate = endDate - timedelta(days=84)
    query = "select date,bug from alerts where date > '%s' and date < '%s'" % (startDate , endDate)
    cursor.execute(query)
    query_results = cursor.fetchall()
    data = {}
    data['date'] = []
    data['bug'] = []
    data['begining'] = str(startDate)
    for i in query_results:
        data['date'].append(str(i[0]))
        data['bug'].append(i[1])
    cursor.close()
    db.close()
    return {'alerts': data}

@app.route('/mergedids')
@json_response
def run_mergedids_query():
    # TODO: ensure we have the capability to view duplicate things by ignoring mergedfrom
    where_clause = "where mergedfrom != '' and (status='' or status='Investigating') order by date DESC, keyrevision";
    return { 'alerts': run_query(where_clause) }

#    for id, keyrevision, bugcount, bug, status, date, mergedfrom in alerts:
@app.route('/alertsbyexpiredrev')
@json_response
def run_alertsbyrev_expired_query():
    query_dict = request.args.to_dict()
    if 'rev' in query_dict:
        query_dict['keyrevision'] = query_dict.pop('rev')
    query = "where "
    flag = 0
    d=date.today()-timedelta(days=126)
    if any(query_dict):
        for key,val in query_dict.iteritems():
            if val:
                if flag:
                    query+= "and %s='%s' " %(key,val)
                else:
                    query+= "%s='%s' " %(key,val)
                    flag = 1
        query+= "and date < '%s'" %str(d);
        return { 'alerts': run_query(query, True) }
    where_clause = "where mergedfrom = '' and (status='' or status='Investigating') and date < '%s' order by date DESC, keyrevision" %str(d);
    return { 'alerts': run_query(where_clause) }

@app.route('/alertsbyrev')
@json_response
def run_alertsbyrev_query():
    query_dict = request.args.to_dict()
    if 'rev' in query_dict:
        query_dict['keyrevision'] = query_dict.pop('rev')
    query = "where "
    flag = 0
    if any(query_dict):
        for key,val in query_dict.iteritems():
            if val:
                if flag:
                    query+= "and %s='%s' " %(key,val)
                else:
                    query+= "%s='%s' " %(key,val)
                    flag = 1
        return { 'alerts': run_query(query, True) }
    where_clause = "where where date > NOW() - INTERVAL 127 DAY and mergedfrom = '' and (status='' or status='Investigating') order by date DESC, keyrevision";
    return { 'alerts': run_query(where_clause) }

@app.route("/getvalues")
@json_response
def run_values_query():
    db = create_db_connnection()
    cursor = db.cursor()

    retVal = {}
    retVal['test'] = []
    retVal['rev'] = []
    retVal['platform'] = []

    cursor.execute("select DISTINCT test from alerts;")
    tests = cursor.fetchall()
    for test in tests:
        retVal['test'].append(test)

    cursor.execute("select DISTINCT platform from alerts;")
    platforms = cursor.fetchall()

    for platform in platforms:
        retVal['platform'].append(platform)

    cursor.execute("select DISTINCT keyrevision from alerts;")
    revs = cursor.fetchall()

    for rev in revs:
        retVal['rev'].append(rev)


    return retVal

@app.route("/mergedalerts")
@json_response
def run_mergedalerts_query():
    keyrev = request.args['keyrev']

    where_clause = "where mergedfrom='%s' and (status='' or status='Investigating') order by date,keyrevision ASC" % keyrev;
    return { 'alerts': run_query(where_clause) }

@app.route("/submit", methods=['POST'])
@json_response
def run_submit_data():
    retVal = {}
    data = request.form
    comment = "[%s] %s" % (data['email'], data['comment'][0])
    sql = "update alerts set comment='%s', email='%s' where id=%s;" % (comment, data['email'], data['id'])

    db = create_db_connnection()
    cursor = db.cursor()
    cursor.execute(sql)
    alerts = cursor.fetchall()

    #TODO: verify via return value in alerts
    return retVal

@app.route("/updatestatus", methods=['POST'])
@json_response
def run_updatestatus_data():
    retVal = {}
    data = request.form

    sql = "update alerts set status='%s' where id=%s;" % (data['status'], data['id'])

    db = create_db_connnection()
    cursor = db.cursor()
    cursor.execute(sql)
    alerts = cursor.fetchall()

    #TODO: verify via return value in alerts
    return retVal

@app.route("/submitduplicate", methods=['POST'])
@json_response
def run_submitduplicate_data():
    retVal = {}
    data = request.form

    sql = "update alerts set status='%s', duplicate='%s' where id=%s;" % (data['status'], data['duplicate'], data['id'])

    db = create_db_connnection()
    cursor = db.cursor()
    cursor.execute(sql)
    alerts = cursor.fetchall()

    #TODO: verify via return value in alerts
    return retVal

@app.route("/submitbug", methods=['POST'])
@json_response
def run_submitbug_data():
    retVal = {}
    data = request.form

    sql = "update alerts set status='%s', bug='%s' where id=%s;" % (data['status'], data['bug'], data['id'])

    db = create_db_connnection()
    cursor = db.cursor()
    cursor.execute(sql)
    alerts = cursor.fetchall()

    #TODO: verify via return value in alerts
    return retVal

@app.route("/submittbpl", methods=['POST'])
@json_response
def run_submittbpl_data():
    retVal = {}
    data = request.form

    sql = "update alerts set tbplurl='%s' where id=%s;" % (data['tbplurl'], data['id'])

    db = create_db_connnection()
    cursor = db.cursor()
    cursor.execute(sql)
    alerts = cursor.fetchall()

    #TODO: verify via return value in alerts
    return retVal

def getConfig():
    op = OptionParser()
    op.add_option("--config",
                    action = "store", type = "string", dest = "config",
                    default = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini'),
                    help = "path to the config file [config.ini]")

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

if __name__ == '__main__':
    getConfig()
    app.run(host="0.0.0.0", port=8159)
