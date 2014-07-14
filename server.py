#!/usr/bin/env python

import os
import json
import re
import sys
from datetime import datetime, timedelta
from itertools import groupby
from collections import Counter
from urlparse import urlparse, parse_qs
from wsgiref.simple_server import make_server
from wsgiref.util import request_uri
from datetime import date, timedelta

import MySQLdb
import ConfigParser
from optparse import OptionParser

global config

def create_db_connnection():
    global config
    try:
        print config
    except:
        getConfig()

    return MySQLdb.connect(host=config['host'],
                           user=config['username'],
                           passwd=config['password'],
                           db=config['database'])


def serialize_to_json(object):
    """Serialize class objects to json"""
    try:
        return object.__dict__
    except AttributeError:
        raise TypeError(repr(object) + 'is not JSON serializable')


def json_response(func):
    """Decorator: Serialize response to json"""
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

@json_response
def run_alert_query(query_dict, body): 
    inputid = query_dict['id']
    return { 'alerts': run_query("where id=%s" % inputid, True) }

@json_response
def run_graph_flot_query(query_dict, body):
   
    startDate = query_dict['startDate']
    endDate = query_dict['endDate']
    db = create_db_connnection()
    cursor = db.cursor()
    if startDate != "none" or endDate != "none":
        query = "select date,bug from alerts where date > '%s' and date < '%s'" % (startDate , endDate)
    else:
        d = date.today() - timedelta(days=91)
        query = "select date,bug from alerts where date > '%s'" %d
    cursor.execute(query)
    query_results = cursor.fetchall()
 
    data = {}
    data['date'] = []
    data['bug'] = []
    for i in query_results:
        data['date'].append(str(i[0]))
        data['bug'].append(i[1])
    cursor.close()
    db.close()
    return {'alerts': data} 

@json_response
def run_mergedids_query(query_dict, body):
    # TODO: ensure we have the capability to view duplicate things by ignoring mergedfrom
    where_clause = "where mergedfrom != '' and (status='' or status='Investigating') order by date DESC, keyrevision";
    return { 'alerts': run_query(where_clause) }

#    for id, keyrevision, bugcount, bug, status, date, mergedfrom in alerts:

@json_response
def run_alertsbyrev_query(query_dict, body):
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
    where_clause = "where mergedfrom = '' and (status='' or status='Investigating') order by date DESC, keyrevision";
    return { 'alerts': run_query(where_clause) }

@json_response
def run_values_query(query_dict,body):
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

@json_response
def run_mergedalerts_query(query_dict, body):
    keyrev = query_dict['keyrev']

    where_clause = "where mergedfrom='%s' and (status='' or status='Investigating') order by date,keyrevision ASC" % keyrev;
    return { 'alerts': run_query(where_clause) }

@json_response
def run_submit_data(query_dict, body):
    retVal = {}
    d = parse_qs(body)
    data = {}
    for item in d:
        data[item] = d[item][0]
    sql = "update alerts set comment='%s', status='%s', email='%s', bug='%s' where id=%s;" % (data['comment'][0], data['status'], data['email'], data['bug'], data['id'])

    db = create_db_connnection()
    cursor = db.cursor()
    cursor.execute(sql)
    alerts = cursor.fetchall()

    #TODO: verify via return value in alerts
    return retVal

@json_response
def run_updatestatus_data(query_dict, body):
    retVal = {}
    d = parse_qs(body)
    data = {}
    for item in d:
        data[item] = d[item][0]

    sql = "update alerts set status='%s' where id=%s;" % (data['status'], data['id'])

    db = create_db_connnection()
    cursor = db.cursor()
    cursor.execute(sql)
    alerts = cursor.fetchall()

    #TODO: verify via return value in alerts
    return retVal

@json_response
def run_submitduplicate_data(query_dict, body):
    retVal = {}
    d = parse_qs(body)
    data = {}
    for item in d:
        data[item] = d[item][0]

    sql = "update alerts set status='%s', duplicate='%s' where id=%s;" % (data['status'], data['duplicate'], data['id'])

    db = create_db_connnection()
    cursor = db.cursor()
    cursor.execute(sql)
    alerts = cursor.fetchall()

    #TODO: verify via return value in alerts
    return retVal

@json_response
def run_submitbug_data(query_dict, body):
    retVal = {}
    d = parse_qs(body)
    data = {}
    for item in d:
        data[item] = d[item][0]

    sql = "update alerts set status='%s', bug='%s' where id=%s;" % (data['status'], data['bug'], data['id'])

    db = create_db_connnection()
    cursor = db.cursor()
    cursor.execute(sql)
    alerts = cursor.fetchall()

    #TODO: verify via return value in alerts
    return retVal

@json_response
def run_submittbpl_data(query_dict, body):
    retVal = {}
    d = parse_qs(body)
    data = {}
    for item in d:
        data[item] = d[item][0]

    sql = "update alerts set tbplurl='%s' where id=%s;" % (data['tbplurl'], data['id'])

    db = create_db_connnection()
    cursor = db.cursor()
    cursor.execute(sql)
    alerts = cursor.fetchall()

    #TODO: verify via return value in alerts
    return retVal

def handler404(start_response):
    status = "404 NOT FOUND"
    response_body = "Not found"
    response_headers = [("Content-Type", "text/html"),
                        ("Content-Length", str(len(response_body)))]
    start_response(status, response_headers)
    return response_body

def get_date_range(dates):
    if dates:
        return {'startDate': min(dates).strftime('%Y-%m-%d %H:%M'),
                'endDate': max(dates).strftime('%Y-%m-%d %H:%M')}

def application(environ, start_response):
    # get request path and request params
    request = urlparse(request_uri(environ))
    query_dict = parse_qs(request.query)

    for key, value in query_dict.items():
        if len(value) == 1:
            query_dict[key] = value[0]


    # get post data
    body = ''  # b'' for consistency on Python 3.0
    try:
        length = int(environ.get('CONTENT_LENGTH', '0'))
    except ValueError:
        length = 0

    if length != 0:
        body = environ['wsgi.input'].read(length)

    # map request handler to request path
    urlpatterns = (
        ('/data/alert(/)?$', run_alert_query),
        ('/graph/flot$', run_graph_flot_query),
        ('/data/submit$', run_submit_data),
        ('/data/updatestatus$', run_updatestatus_data),
        ('/data/submitduplicate$', run_submitduplicate_data),
        ('/data/submitbug$', run_submitbug_data),
        ('/data/submittbpl$', run_submittbpl_data),
        ('/data/alertsbyrev$', run_alertsbyrev_query),
        ('/data/mergedalerts$', run_mergedalerts_query),
        ('/data/mergedids$', run_mergedids_query),
        ('/data/getvalues$', run_values_query),
        )

    # dispatch request to request handler
    for pattern, request_handler in urlpatterns:
        if re.match(pattern, request.path, re.I):
            response_body = request_handler(query_dict, body)
            break
    else:
        # When running outside of Apache, we need to handle serving
        # static files as well. This can be removed when we move to Flask.
        # need to strip off leading '/' for relative path
        static_path = request.path[1:]
        if os.path.exists(static_path):
            with open(static_path, 'r') as f:
                response_body = f.read()
            status = "200 OK"
            response_headers = [("Content-Type", "html"),
                                ("Content-Length", str(len(response_body)))]
            start_response(status, response_headers)
            return response_body
        else:
            return handler404(start_response)

    status = "200 OK"
    response_headers = [("Content-Type", "application/json"),
                        ("Content-Length", str(len(response_body)))]
    start_response(status, response_headers)
    return response_body


def getConfig():
    global config
    op = OptionParser()
    op.add_option("--config",
                    action = "store", type = "string", dest = "config",
                    default = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini'),
                    help = "path to the config file [config.ini]")

    options, args = op.parse_args()

    if not os.path.exists(options.config):
        print "ERROR: %s doesn't exist" % (os.path.abspath(options.config))
        sys.exit(1)

    parser = ConfigParser.RawConfigParser()
    parser.read(options.config)

    config = {'username': parser.get('alerts', 'username'), 
              'password': parser.get('alerts', 'password'), 
              'host': parser.get('alerts', 'host'), 
              'database': parser.get('alerts', 'database'), 
              'maildir': parser.get('alerts', 'maildir')}

if __name__ == '__main__':
    getConfig()
    httpd = make_server("0.0.0.0", 8159, application)
    httpd.serve_forever()
