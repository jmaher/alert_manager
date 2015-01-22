#!/usr/bin/env python

from datetime import date, timedelta
import logging

from flask import request, jsonify, render_template

from bug_check import *


DEBUG = True

@app.route('/alerts.html')
def home():
    return render_template('alerts.html')

@app.route('/expired.html')
def expired():
    return render_template('expired.html')


@app.route('/report.html')
def report():
    return render_template('report.html')


def run_query(where_clause):
    db = create_db_connnection()
    cursor = db.cursor()

    fields = ['id', 'branch', 'test', 'platform', 'percent', 'graphurl', 'changeset', 'keyrevision', 'bugcount', 'comment', 'bug', 'status', 'email', 'push_date', 'mergedfrom', 'duplicate', 'tbplurl', 'backout']
    sql = "select %s from alerts %s;" %(','.join(fields), where_clause.strip())
    cursor.execute(sql)
    alerts = cursor.fetchall()

    retVal = []
    for alert in alerts:
        data = {}
        i = 0
        while i < len(fields):
            data[fields[i]] = alert[i]
            if fields[i] == 'push_date':
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
    push_date = query_dict['date']
    db = create_db_connnection()
    cursor = db.cursor()
    if push_date == "none":
        query = "select bug,status,resolution,date_opened,date_resolved from details"
    else:
        query = "select bug,status,resolution,date_opened,date_resolved from details  where date_opened > '%s'" % (push_date)

    cursor.execute(query)
    search_results = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify(bugs=search_results)

@app.route('/update_rev')
def updateRev():
    query_dict = request.args.to_dict()      
    newVal = query_dict['newVal']
    oldVal = query_dict['oldVal']
    vals={}
    vals['newVal'] = newVal
    vals['oldval'] = oldVal
    db = create_db_connnection()
    cursor = db.cursor()
    sql = "update alerts set keyrevision='%s' where keyrevision='%s';" % (newVal,oldVal)
    cursor.execute(sql)
    return jsonify(data=vals)

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
        endDate = app.config["now"]()
    if startDate == "none":
        startDate = endDate - timedelta(days=84)
    query = "select push_date,bug from alerts where push_date > '%s' and push_date < '%s'" % (startDate, endDate)
    cursor.execute(query)
    query_results = cursor.fetchall()
    data = {}
    data['push_date'] = []
    data['bug'] = []
    data['begining'] = str(startDate)
    for i in query_results:
        data['push_date'].append(str(i[0]))
        data['bug'].append(i[1])
    cursor.close()
    db.close()
    return jsonify(alerts=data)

@app.route('/mergedids')
def run_mergedids_query():
    # TODO: ensure we have the capability to view duplicate things by ignoring mergedfrom
    where_clause = "where mergedfrom!='' and (status='' or status='NEW' or status='Investigating') order by push_date DESC, keyrevision";
    return jsonify(alerts=run_query(where_clause))

#    for id, keyrevision, bugcount, bug, status, date, mergedfrom in alerts:
@app.route('/alertsbyrev')
def run_alertsbyrev_query():
    query_dict = request.args.to_dict()
    expired = 0
    if 'expired' in query_dict:
        expired = query_dict.pop('expired')
    if 'rev' in query_dict:
        query_dict['keyrevision'] = query_dict.pop('rev')
    query = "where "
    flag = 0
    d = app.config["today"]() - timedelta(days=126)
    if any(query_dict):
        for key, val in query_dict.iteritems():
            if val:
                if flag:
                    query += "and %s='%s' " % (key, val)
                else:
                    query += "%s='%s' " % (key, val)
                    flag = 1
        if int(expired) == 1:
            query += "and push_date < '%s'" % str(d);

        return jsonify(alerts=run_query(query))

    if int(expired) == 1:
        comparator = "<"
    else:
        comparator = ">"

    where_clause = """
        where
            left(keyrevision, 1) <> '{' and
            mergedfrom = '' and
            (status='' or status='NEW' or status='Investigating') and
            push_date """+comparator+""" '%s'
        order by
            push_date DESC, keyrevision
        """ % str(d)
    return jsonify(alerts=run_query(where_clause))


@app.route("/getvalues")
def run_values_query():
    db = create_db_connnection()
    cursor = db.cursor()

    retVal = {
        'test': [],
        'rev': [],
        'platform': []
    }

    now = app.config["now"]()

    cursor.execute("""
        select DISTINCT 'test' AS name, test AS value FROM alerts WHERE push_date > %s - INTERVAL 127 DAY
        UNION ALL
        select DISTINCT 'platform' AS name, platform AS value FROM alerts WHERE push_date > %s - INTERVAL 127 DAY
        UNION ALL
        select DISTINCT 'rev' AS name, keyrevision AS value FROM alerts WHERE push_date > %s - INTERVAL 127 DAY
        """, (now,now,now))
    data = cursor.fetchall()
    for d in data:
        retVal[d[0]].append(d[1])
    return jsonify(**retVal)


@app.route("/mergedalerts")
def run_mergedalerts_query():
    keyrev = request.args['keyrev']

    where_clause = "where mergedfrom='%s' and (status='' or status='NEW' or status='Investigating') order by push_date,keyrevision ASC" % keyrev;
    return jsonify(alerts=run_query(where_clause))

@app.route("/win8only")
def run_win8only_query():
    where_clause = "where platform='WINNT 6.2 x64' and percent<0 and status!='Duplicate' and mergedfrom='' and status!='False Alarm' and status!='Not Tracking' and keyrevision not in (select distinct keyrevision from alerts where platform!='WINNT 6.2 x64') order by push_date,keyrevision ASC"
    return jsonify(alerts=run_query(where_clause))

@app.route("/submit", methods=['POST'])
def run_submit_data():
    '''
    To add comments

    '''

    retVal = {}
    data = request.form
    comment = "[%s] %s" % (data['email'], data['comment'])
    sql = "update alerts set comment='%s', email='%s' where id=%s;" % (comment, data['email'], data['id'])
    db = create_db_connnection()
    cursor = db.cursor()
    cursor.execute(sql)
    alerts = cursor.fetchall()

    #TODO: verify via return value in alerts
    return jsonify(**retVal)

@app.route("/updaterev", methods=['POST'])
def run_updatekeyrev_data():
    '''
    To change keyrevision of a particular alert

    '''
    retVal = {}
    data = request.form
    sql = "update alerts set keyrevision='%s' where id=%s;" % (data['revision'], data['id'])

    db = create_db_connnection()
    cursor = db.cursor()
    cursor.execute(sql)
    alerts = cursor.fetchall()

    return jsonify(**retVal)

@app.route("/updatefields", methods=['POST'])
def run_addfields_data():
    '''
    To Add comments, bugs to multiple alerts
    TODO: implemented only comments as of now

    '''
    sql=''
    query_dict = request.args.to_dict()
    typeVal = ""
    data = request.form
    retVal = {}

    if 'type' in query_dict:
        typeVal = query_dict.pop('type')

    if typeVal == "bug":
        sql = "update alerts set bug='%s' where id=%s;" %(data['BugID'], data['id'])

    if typeVal == "comment":
        pass


    db = create_db_connnection()
    cursor = db.cursor()
    cursor.execute(sql)
    alerts = cursor.fetchall()

    return jsonify(**retVal)

@app.route("/updatestatus", methods=['POST'])
def run_updatestatus_data():
    query_dict = request.args.to_dict()
    typeVal = ""
    if 'type' in query_dict:
        typeVal = query_dict.pop('type')
    retVal = {}
    data = request.form

    sql = """update alerts set status='%s'"""
    if typeVal != "":
        sql += """,%s='%s'"""
    sql += """ where id=%s;"""

    if typeVal == "duplicate":
        specific_data = data['duplicate']
    elif typeVal == "bug":
        specific_data = data['bug']
    elif typeVal == "tbplurl":
        specific_data = data['tbplurl']

    if typeVal != "":
        sql = sql % (data['status'],typeVal,specific_data,data['id'])
    else:
        sql = sql % (data['status'],data['id'])

    db = create_db_connnection()
    cursor = db.cursor()
    cursor.execute(sql)
    alerts = cursor.fetchall()
    #TODO: verify via return value in alerts

    return jsonify(**retVal)

@app.route('/shutdown', methods=['POST'])
def shutdown():
    # from http://flask.pocoo.org/snippets/67/
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        return {"response": 'Not running with the Werkzeug Server'}
    func()
    return jsonify(response='Server shutting down...')


if __name__ == '__main__':
    getConfig()
    logging.basicConfig(level=logging.DEBUG)
    app.run(host="0.0.0.0", port=8159)
