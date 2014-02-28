import re
import sys
import string
import mailbox
import MySQLdb
import datetime
import rfc822
import urllib
import base64
import os

trees = ['Mozilla-Inbound', 
         'Mozilla-Inbound-Non-PGO', 
         'Fx-Team',
         'Fx-Team-Non-PGO',
         'Firefox',
         'Firefox-Non-PGO', 
         'Mozilla-Aurora',
         'Mozilla-Aurora-Non-PGO',
         'Mozilla-Beta',
         'Mozilla-Beta-Non-PGO',
         'B2g-Inbound',
         'B2g-Inbound-Non-PGO',
         'mobile']

platforms = ['XP', 'Win7', 'Ubuntu HW 12.04 x64', 'Ubuntu HW 12.04', 'Linux',
             'WINNT 5.2', 'WINNT 6.1 (ix)', 'WINNT 6.2 x64', 'WINNT 5.1 (ix)',
# jmaher: I don't care too much about centOS- that is builders
#             'CentOS release 5 (Final)', 'CentOS (x86_64) release 5 (Final)',
             'MacOSX 10.7', 'MacOSX 10.8', 'MacOSX 10.6 (rev4)', 
             'Android 2.2 (Native)', 'Android 4.0.4']

tests = ['SVG No Chrome',
        'SVG Row Major',
        'SVG, Opacity Row Major',
        'Dromaeo (DOM)',
        'Dromaeo (CSS)',
        'Kraken Benchmark',
        'V8',
        'V8 Version 7',
        'Paint',
        'tscroll Row Major',
        'TResize',
        'Tp5 Optimized',
        'Tp5 Optimized (Private Bytes)',
        'Tp5 Optimized (Main RSS)',
        'Tp5 Optimized (Content RSS)',
        'Tp5 Optimized (%CPU)',
        'Tp5 No Network Row major MozAfterPaint (Main Startup File I/O Bytes)',
        'Tp5 No Network Row Major MozAfterPaint (Non-Main Startup File IO Bytes)',
        'Tp5 No Network Row Major MozAfterPaint (Non-Main Normal Network IO Bytes)',
        'Tp5 No Network Row Major MozAfterPaint (Main Normal File IO Bytes)',
        'Tp5 No Network Row Major MozAfterPaint (Main Startup File IO Bytes)',
        'Tp5 Optimized (Modified Page List Bytes)',
        'Tp5 Optimized Responsiveness',
        'Tp5 Optimized MozAfterPaint',
        'a11y Row Major MozAfterPaint',
        'Tp4 Mobile',
        'LibXUL Memory during link',
        'Ts, Paint',
        'Robocop Pan Benchmark',
        'Robocop Database Benchmark',
        'Robocop Checkerboarding No Snapshot Benchmark',
        'Robocop Checkerboarding Real User Benchmark',
        'Customization Animation Tests',
        'Latency Performance Tests',
        'WebRTC Media Performance Tests',
        'Tab Animation Test, NoChrome',
        'Tab Animation Test',
        'Canvasmark, NoChrome',
        'Canvasmark',
        'Tab Animation Test, NoChrome',
        'CanvasMark, NoChrome',
        'CanvasMark',
        'tscroll-ASAP',
        'SVG-ASAP, NoChrome',
        'SVG-ASAP',
        'V8 version 7',
        'tscroll-ASAP MozAfterPaint' ]

#subject = "(Improvement) Firefox-Non-PGO - Customization Animation Tests - WINNT 6.2 x64 - 5.84%"
subre = re.compile("^(<Regression>|\(Improvement\))(.*)")


subject_trans_table = string.maketrans("\t", " ")

def getRevisions(changeseturl):
    cpart = changeseturl.split('?')[-1].replace('&', '_')

    cacheFile = os.path.join(os.path.abspath('tmpcset'), cpart)
    if not os.path.exists(cacheFile):
        opener = urllib.FancyURLopener({})
        f = opener.open(changeseturl)
        data = f.read()
        f.close()
        with open(cacheFile, 'w+') as fHandle:
            fHandle.write(data)

    with open(cacheFile, 'r') as fHandle:
        data = fHandle.read()

    revisions = []
    #TODO: do we need to support other branches
    re_rev = re.compile(".*href=\"(\/integration)?\/(b2g-inbound|mozilla-central|mozilla-inbound|fx-team)\/rev\/([0-9a-f]+)\".*")
    for line in data.split('\n'):
        matches = re_rev.match(line)
        if matches:
            revisions.append(matches.group(3))

    return revisions

def getCSets():
    db = MySQLdb.connect(host="localhost",
                         user="root",
                         passwd="testing",
                         db="alerts")

    #TODO: optimize to last 2 weeks of data
    sql = "select id, keyrevision, changesets from alerts";
    cur = db.cursor()
    cur.execute(sql)

    results = []
    for row in cur.fetchall():
        results.append([int(row[0]), row[1], row[2].split(',')])
    cur.close()

    return results

def markMerged(id, originalKeyRevision):
    db = MySQLdb.connect(host="localhost",
                         user="root",
                         passwd="testing",
                         db="alerts")

    sql = "select mergedfrom from alerts where id=%s" % id;
    cur = db.cursor()
    cur.execute(sql)

    results = []
    setAsMerged = False
    for row in cur.fetchall():
        if row[0]:
            if row[0] != '':
                setAsMerged = True
                break
    cur.close()

    if not setAsMerged:
        sql = "update alerts set mergedfrom='%s' where id=%s" % (originalKeyRevision, id);
        cur = db.cursor()
        cur.execute(sql)
        cur.close()

def subject_of(msg):
    global subject_trans_table
    subject = msg.get('Subject')
    if subject is None:
        return subject
    return subject.translate(subject_trans_table, "\n")

def validSubject(subject):
    global trees, platforms, tests, subre
    match = subre.match(subject)
    if not match:
        return [None, None, None, None]

    if match.group(1) == "(Improvement)":
        sign = "+"
    else:
        sign = "-"

    parts = match.group(2).strip().split(' - ')
    if parts[0] not in trees:
        print "INVALID TREE: %s" % parts[0]
        return [None, None, None, None]

    if parts[2] not in platforms:
#        print "INVALID PLATFORM: '%s'" % parts[2]
        return [None, None, None, None]

    if parts[1] not in tests:
        print "INVALID TEST NAME: %s" % parts[1]
        return [None, None, None, None]

    return parts

#TODO: make this configurable
mbox_dir = '/var/spool/news/mozilla/dev/tree-management/new'
mbox = mailbox.MHMailbox(mbox_dir)

while 1:
    msg = mbox.next()
    if not msg:
        break
    parts = validSubject(subject_of(msg))

    if not parts[0]:
        continue

    branch = parts[0]
    test = parts[1]
    platform = parts[2]
    percent = parts[3]
    body = msg.fp.read()

    if not body:
        continue

    graphurl = None
    changeset = None
    keyrevision = None
    bugCount = 0
    bugsection = False

# get these out of the body
#    Graph   : http://mzl.la/1iU7sbe
#Changeset range: http://hg.mozilla.org/integration/mozilla-inbound/pushloghtml?fromchange=1bb4238bdde3&tochange=89f9304ff4ba
    newbody = ""
    logbody = False

    for line in body.split('\n'):
        if line.strip().startswith('-----------------------------'):
            logbody = True

        try:
            line.strip().index('http://mzl.la/')
            graphurl = ':'.join(line.strip().split(':')[1:])
        except:
            pass

        try:
            line.strip().index('Changeset range')
            changeset = ':'.join(line.strip().split(':')[1:])
            parts = changeset.split('=')
            rawparts = []
            for p in parts:
                raw = p.split('&')
                for r in raw:
                   rawparts.append(r)
            rawparts[-1] = rawparts[-1].zfill(12)
            rawparts[-3] = rawparts[-3].zfill(12)
            changeset = "%s=%s&%s=%s" % (rawparts[0], rawparts[1], rawparts[2], rawparts[3])
        except:
            pass

        try:
            line.strip().index('since revision')
            keyrevision = line.strip().split(' ')[-1].strip()
            keyrevision = keyrevision.zfill(12)
        except:
            pass

        if bugsection:
            if line.strip().startswith('* http://bugzilla.mozilla.org/show_bug.cgi?id='):
                bugCount += 1
            if line.strip() == '':
                bugsection = None

        if line.strip().startswith('Bugs:'):
            bugsection = True

        if logbody:
            newbody += "%s\n" % line

    if not graphurl or not changeset:
        print "INVALID BODY: no graphurl or changeset"
        continue

    csets = getRevisions(changeset)

    date = msg.get('Date')
    parsed = rfc822.parsedate(date)

    merged = ''
    if bugCount > 10:
        # search for csets in existing 
        db_csets = getCSets()
        merged = ''
        for i, k, c in db_csets:
            if k in csets:
                merged = k
                # found the key revision in the merged changeset, see if others are there
                for originalrev in c:
                    if originalrev not in csets:
                        print "OH NO: found keyrevision %s, but not other cset: %s from original in current set: %s" % (k, originalrev, c)
                        print "       platform: %s, branch: %s, test %s, keyrevision %s, csets: %s\n" % (platform, branch, test, keyrevision, csets)
                        merged = ''
                        break

            if merged:
#                print "found original regression: keyrevision: %s, csets: %s" % (k, c)
                break

    datestring = "%s-%s-%s %s:%s:%s" % (str(parsed[0]).zfill(4), str(parsed[1]).zfill(2), str(parsed[2]).zfill(2), str(parsed[3]).zfill(2), str(parsed[4]).zfill(2), str(parsed[5]).zfill(2))

    db = MySQLdb.connect(host="localhost",
                         user="root",
                         passwd="testing",
                         db="alerts")

    # TODO: figure out if we should set these fields to a specific value
    comment = ''
    bug = ''
    status = ''
    body = MySQLdb.escape_string(newbody)

    foundDuplicate = False
    cur = db.cursor()
    sql = "select id from alerts where branch='%s' and test='%s' and platform='%s' and percent='%s'" % (branch, test, platform, percent)
    cur.execute(sql)
    for row in cur.fetchall():
        if row[0]:
          foundDuplicate = row[0]

    cur.close()
    if foundDuplicate:
        if merged:
            markMerged(foundDuplicate, merged)
        continue

    print "branch: %s" % branch
    print "test: %s" % test
    print "platform: %s" % platform
    print "percent: %s" % percent
    print "graphurl: %s" % graphurl
    print "changeset: %s" % changeset
    print "keyrevision: %s" % keyrevision
    print "bugcount: %s" % bugCount
    print "changesets: %s" % csets

    cur = db.cursor()
    sql = 'insert into alerts (branch, test, platform, percent, graphurl, changeset, keyrevision, bugcount, comment, bug, status, body, date, changesets, mergedfrom) values ('
    sql += "'%s'" % branch
    sql += ", '%s'" % test
    sql += ", '%s'" % platform
    sql += ", '%s'" % percent
    sql += ", '%s'" % graphurl
    sql += ", '%s'" % changeset
    sql += ", '%s'" % keyrevision
    sql += ", %s" % bugCount
    sql += ", '%s'" % comment
    sql += ", '%s'" % bug
    sql += ", '%s'" % status
    sql += ", '%s'" % body
    sql += ", '%s'" % datestring
    sql += ", '%s'" % ','.join(csets)
    sql += ", '%s'" % merged
    sql += ')'

    cur.execute(sql)
    cur.close()

