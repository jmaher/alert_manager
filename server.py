#!/usr/bin/env python

import os
import sys
import requests
from flask import Flask, request, jsonify
from datetime import date, timedelta
import MySQLdb
import ConfigParser
from optparse import OptionParser
import logging
from bug_check import *
from db import *


def run_query(where_clause):
    db = create_db_connnection()
    cursor = db.cursor()

    fields = ['id', 'branch', 'test', 'platform', 'percent', 'graphurl', 'changeset', 'keyrevision', 'bugcount', 'comment', 'bug', 'status', 'email', 'date', 'mergedfrom', 'duplicate', 'tbplurl']
    sql = "select %s from alerts %s;" %(','.join(fields), where_clause.strip())
    cursor.execute(sql)
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


@app.route('/conflicted_bugs')
def get_conflicting_alerts():
    alerts=[]
    bugs = get_conflicting_bugs()
    db = create_db_connnection()
    cursor = db.cursor()
    for bugid in bugs:
        query = "select bug,branch,test,platform,percent,graphurl,tbplurl,changeset,status,id,duplicate,mergedfrom from alerts  where bug = '%s'" % (bugid)     
        cursor.execute(query)
        search_results = cursor.fetchall()
        alerts.append(search_results)
    cursor.close()
    db.close()        
    return jsonify(bugs=alerts)


@app.route('/alert')
def run_alert_query():
    inputid = request.args['id']
    return jsonify(alerts=run_query("where id=%s" % inputid))

@app.route('/bugzilla_reports')
def run_bugzilla_query():

    query_dict = request.args.to_dict()
    date = query_dict['date']
    db = create_db_connnection()
    cursor = db.cursor()
    if date == "none":
        query = "select bug,status,resolution,date_opened,date_resolved from details"
    else:
        query = "select bug,status,resolution,date_opened,date_resolved from details  where date_opened > '%s'" % (date)    
    
    cursor.execute(query)
    search_results = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify(bugs=search_results)

@app.route('/graph/flot')
def run_graph_flot_query():
    query_dict = request.args.to_dict()
    startDate = query_dict['startDate']
    endDate = query_dict['endDate']
    if endDate != "none" and startDate == "none":
        dateElements = endDate.split('-')
        endDate = date(int(dateElements[0]), int(dateElements[1]), int(dateElements[2]))

    db = create_db_connnection()
    cursor = db.cursor()
    if endDate == "none":
        endDate = date.today()
    if startDate == "none":
        startDate = endDate - timedelta(days=84)
    query = "select date,bug from alerts where date > '%s' and date < '%s'" % (startDate, endDate)
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
    return jsonify(alerts=data)


@app.route('/mergedids')
def run_mergedids_query():
    # TODO: ensure we have the capability to view duplicate things by ignoring mergedfrom
    where_clause = "where mergedfrom!='' and (status='' or status='NEW' or status='Investigating') order by date DESC, keyrevision";
    return jsonify(alerts=run_query(where_clause))

#    for id, keyrevision, bugcount, bug, status, date, mergedfrom in alerts:

@app.route('/alertsbyrev')
def run_alertsbyrev_query():
    query_dict = request.args.to_dict()
    expired = query_dict.pop('expired')
    if 'rev' in query_dict:
        query_dict['keyrevision'] = query_dict.pop('rev')
    query = "where "
    flag = 0
    d = date.today() - timedelta(days=126)
    if any(query_dict):
        for key, val in query_dict.iteritems():
            if val:
                if flag:
                    query += "and %s='%s' " % (key, val)
                else:
                    query += "%s='%s' " % (key, val)
                    flag = 1
        if int(expired) == 1:
            query += "and date < '%s'" % str(d);
       
        return jsonify(alerts=run_query(query))
    
    if int(expired) == 1:
        comparator = "<"
    else:
        comparator = ">"
        
    where_clause = "where left(keyrevision, 1) <> '{' and mergedfrom = '' and (status='' or status='NEW' or status='Investigating') and date "+comparator+" '%s' order by date DESC, keyrevision" % str(d);    
    return jsonify(alerts=run_query(where_clause))


@app.route("/getvalues")
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

    return jsonify(**retVal)


@app.route("/mergedalerts")
def run_mergedalerts_query():
    keyrev = request.args['keyrev']

    where_clause = "where mergedfrom='%s' and (status='' or status='NEW' or status='Investigating') order by date,keyrevision ASC" % keyrev;
    return jsonify(alerts=run_query(where_clause))


@app.route("/submit", methods=['POST'])
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
    return jsonify(**retVal)


@app.route("/updatestatus", methods=['POST'])
def run_updatestatus_data():
    query_dict = request.args.to_dict()
    typeVal = "";
    if 'type' in query_dict:
        typeVal = query_dict.pop('type')
    retVal = {}
    data = request.form
    if typeVal == "duplicate":
        sql = "update alerts set status='%s', duplicate='%s' where id=%s;" % (data['status'], data['duplicate'], data['id'])
    elif typeVal == "bug":
        sql = "update alerts set status='%s', bug='%s' where id=%s;" % (data['status'], data['bug'], data['id'])
    elif typeVal == "tbpl":
        sql = "update alerts set tbplurl='%s' where id=%s;" % (data['tbplurl'], data['id'])
    else:
        sql = "update alerts set status='%s' where id=%s;" % (data['status'], data['id'])
    
    db = create_db_connnection()
    cursor = db.cursor()
    cursor.execute(sql)
    alerts = cursor.fetchall()

    #TODO: verify via return value in alerts
    return jsonify(**retVal)


if __name__ == '__main__':
    getConfig()
    logging.basicConfig(level=logging.DEBUG)
    app.run(host="0.0.0.0", port=8159)
